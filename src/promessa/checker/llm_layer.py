"""Camada 2 do checador: modelo de linguagem + regras de fusão em código (CONTEXTO 11.3).

Fusão (código, não prompt):
- `excerpt` que não é pedaço literal do texto é descartado (log);
- `bloquear` sem `rule_key` proibido da versão vira `revisar`;
- o modelo não rebaixa a camada 1: achado do modelo sobre um trecho já marcado pela camada 1
  com saída igual ou mais grave é ignorado;
- `registrar` é só da camada 1 (é ela que confere com a ficha); o do modelo é descartado;
- promessa de resultado extraída pelo modelo e sem achado vira `revisar` (resultado sem número).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel

from promessa.checker.models import SEVERITY, CheckContext, Finding
from promessa.checker.segment import Segment
from promessa.db.enums import CheckOutput, CheckSource
from promessa.llm.client import LLMResult, complete_json

log = logging.getLogger(__name__)

PROMPT = "checker_v1"


class LLMFinding(BaseModel):
    segment: int
    excerpt: str
    output: Literal["bloquear", "revisar", "registrar"]
    rule_key: str | None
    reason_type: str
    explanation: str
    suggestion: str | None


class LLMPromise(BaseModel):
    excerpt: str
    attribute: Literal["garantia", "acesso", "recorrencia", "bonus", "custo", "resultado", "outro"]
    value: str
    unit: str | None


class CheckerLLMOutput(BaseModel):
    findings: list[LLMFinding]
    promises: list[LLMPromise]


Completer = Callable[..., LLMResult[CheckerLLMOutput]]


# --- Entrada do prompt -------------------------------------------------------------------


def prompt_variables(
    text: str, segments: list[Segment], ctx: CheckContext, layer1: list[Finding]
) -> dict:
    access = {
        "vitalicio": "acesso vitalício",
        "prazo": f"acesso por {ctx.access_months} meses",
        "assinatura": "acesso enquanto a assinatura estiver ativa",
        "nao_aplica": "produto físico (sem acesso a conteúdo)",
    }[ctx.access_type.value]
    costs = ", ".join(
        f"{c['descricao']} ({c['valor_mensal_cents'] / 100:.2f} reais/mês)" for c in ctx.extra_costs
    )
    ficha = "\n".join(
        [
            f"- garantia: {ctx.guarantee_days} dias",
            f"- acesso: {access}",
            f"- cobrança: {ctx.recurrence.value}"
            + (" com renovação automática" if ctx.auto_renewal else ""),
            f"- bônus: {', '.join(ctx.bonuses) or 'nenhum'}",
            f"- custos extras: {costs or 'nenhum'}",
        ]
    )
    permitted = (
        "\n".join(f"- {r.rule_key}: {r.text}" for r in ctx.permitted) or "- (nenhuma lista oficial)"
    )
    prohibited = (
        "\n".join(f"- {r.rule_key}: {r.tema or r.text}; {r.output}" for r in ctx.prohibited)
        or "- (nenhuma)"
    )
    found = (
        "\n".join(f'- {f.output.value} {f.rule_key}: "{f.excerpt}"' for f in layer1) or "- (nada)"
    )
    numbered = "\n".join(f"[{i}] {s.text}" for i, s in enumerate(segments, start=1))
    return {
        "categoria": ctx.category.value,
        "ficha": ficha,
        "permitidas": permitted,
        "proibidas": prohibited,
        "achados_camada1": found,
        "trechos": numbered,
    }


# --- Fusão -------------------------------------------------------------------------------


def _locate(
    text: str, excerpt: str, segments: list[Segment], seg_no: int
) -> tuple[int, int] | None:
    """Posição literal do excerpt; prefere o trecho indicado pelo modelo."""
    if not excerpt.strip():
        return None
    if 1 <= seg_no <= len(segments):
        seg = segments[seg_no - 1]
        i = seg.text.find(excerpt)
        if i >= 0:
            return seg.start + i, seg.start + i + len(excerpt)
    i = text.find(excerpt)
    return (i, i + len(excerpt)) if i >= 0 else None


def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def merge(
    text: str,
    segments: list[Segment],
    ctx: CheckContext,
    layer1: list[Finding],
    result: LLMResult[CheckerLLMOutput],
) -> list[Finding]:
    """Achados novos do modelo, já filtrados pelas regras de fusão."""
    prohibited_keys = {r.rule_key for r in ctx.prohibited}
    added: list[Finding] = []

    def accept(
        span: tuple[int, int],
        output: CheckOutput,
        rule_key,
        reason,
        explanation,
        suggestion,
        extracted=None,
    ):
        for f in layer1 + added:
            if _overlaps(f.span, span) and SEVERITY[f.output.value] >= SEVERITY[output.value]:
                log.info(
                    "fusão: modelo ignorado em %r (já marcado como %s)",
                    text[span[0] : span[1]],
                    f.output.value,
                )
                return
        added.append(
            Finding(
                excerpt=text[span[0] : span[1]],
                span=span,
                output=output,
                rule_key=rule_key,
                source=CheckSource.MODELO,
                reason_type=reason,
                explanation=explanation,
                suggestion=suggestion,
                extracted=extracted,
                model=result.model,
                prompt_version=result.prompt_version,
            )
        )

    for item in result.data.findings:
        span = _locate(text, item.excerpt, segments, item.segment)
        if span is None:
            log.warning(
                "fusão: excerpt do modelo não está no texto, descartado: %r", item.excerpt[:80]
            )
            continue
        if item.output == "registrar":
            log.info(
                "fusão: registrar do modelo descartado (só a camada 1 registra): %r",
                item.excerpt[:80],
            )
            continue
        output = CheckOutput(item.output)
        rule_key = item.rule_key if item.rule_key in prohibited_keys else None
        if output == CheckOutput.BLOQUEAR and rule_key is None:
            log.info("fusão: bloquear sem rule_key válido (%r) virou revisar", item.rule_key)
            output = CheckOutput.REVISAR
        accept(span, output, rule_key, item.reason_type, item.explanation, item.suggestion)

    for promise in result.data.promises:
        span = _locate(text, promise.excerpt, segments, 0)
        if span is None:
            log.warning(
                "fusão: promessa do modelo fora do texto, descartada: %r", promise.excerpt[:80]
            )
            continue
        extracted = {
            "type": "resultado" if promise.attribute == "resultado" else "condicao_oferta",
            "attribute": promise.attribute,
            "value": promise.value,
            "unit": promise.unit,
        }
        target = next((f for f in added if _overlaps(f.span, span) and f.extracted is None), None)
        if target is not None:
            target.extracted = extracted
        elif promise.attribute == "resultado":
            accept(
                span,
                CheckOutput.REVISAR,
                None,
                "resultado_sem_numero",
                "Promessa de resultado que o comprador pode cobrar depois. "
                "Confirme que é possível cumprir.",
                "Fale do que o produto oferece sem prometer o resultado.",
                extracted,
            )
    return added


def run_layer2(
    text: str,
    segments: list[Segment],
    ctx: CheckContext,
    layer1: list[Finding],
    model: str,
    completer: Completer = complete_json,
) -> list[Finding]:
    """Chama o modelo e devolve os achados novos (já fundidos). Erros sobem como LLMError."""
    variables = prompt_variables(text, segments, ctx, layer1)
    result = completer(PROMPT, variables, CheckerLLMOutput, model)
    return merge(text, segments, ctx, layer1, result)
