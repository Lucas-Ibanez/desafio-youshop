"""Camada 1, listas e padrões (CONTEXTO 11.2, itens 3 e 4; exceção da D18).

Ordem por trecho:
1. alegações permitidas da versão que aparecem literalmente → `registrar` (protege o trecho);
2. `claim_rule` proibidas da versão (listas oficiais e regras da marca) → saída da regra,
   descartando casamentos que caem inteiros dentro de um trecho protegido;
3. padrões da H2 (`padroes_h2.yaml`) → `revisar`; urgência numa peça antiga vira
   `URGENCIA-VENCIDA`; regras com `extrai: resultado` levam a promessa em `extracted`.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime

from promessa.checker.models import CheckContext, Finding, RuleSpec
from promessa.checker.segment import Segment
from promessa.db.enums import CheckOutput
from promessa.rules.match import Hit, find_hits, term_regex
from promessa.rules.normalize import normalize
from promessa.rules.schema import ListRule

log = logging.getLogger(__name__)

Span = tuple[int, int]


def _finding(text: str, start: int, end: int, **fields) -> Finding:
    return Finding(excerpt=text[start:end], span=(start, end), **fields)


def _inside(hit: Hit, protected: list[Span]) -> bool:
    return any(s <= hit.start and hit.end <= e for s, e in protected)


def _claim_regex(claim: str) -> re.Pattern[str]:
    """Alegação literal como frase inteira, ignorando a pontuação final."""
    return term_regex(normalize(claim).strip().rstrip(".!;").strip())


# --- 1. Alegações permitidas (D18) -------------------------------------------------------


def permitted_findings(
    text: str, seg: Segment, seg_norm: str, ctx: CheckContext
) -> tuple[list[Finding], list[Span]]:
    """Ocorrências literais das alegações permitidas. Devolve achados e trechos protegidos
    (relativos ao trecho)."""
    findings: list[Finding] = []
    protected: list[Span] = []
    for rule in ctx.permitted:
        for m in _claim_regex(rule.text).finditer(seg_norm):
            protected.append((m.start(), m.end()))
            from_brand = rule.source == "MARCA"
            findings.append(
                _finding(
                    text,
                    seg.start + m.start(),
                    seg.start + m.end(),
                    output=CheckOutput.REGISTRAR,
                    rule_key=rule.rule_key,
                    reason_type="alegacao_permitida",
                    explanation=(
                        "Frase aprovada pela marca na ficha."
                        if from_brand
                        else f"Alegação aprovada pela IN 28 ({rule.tema}). Só vale se o produto "
                        "tiver a dose mínima exigida pela IN 28 (Anexo III)."
                    ),
                    extracted={
                        "type": "alegacao",
                        "attribute": "outro",
                        "value": rule.text,
                        "unit": None,
                    },
                )
            )
    return findings, protected


# --- 2. Regras proibidas da versão -------------------------------------------------------


def prohibited_findings(
    text: str, seg: Segment, seg_norm: str, ctx: CheckContext, protected: list[Span]
) -> list[Finding]:
    findings: list[Finding] = []
    for rule in ctx.prohibited:
        hits = find_hits(seg.text, rule.termos, rule.padroes, rule.junto_de, prepared=seg_norm)
        kept = [h for h in hits if not _inside(h, protected)]
        if len(kept) < len(hits):
            log.info(
                "trecho permitido protege %s: %s",
                rule.rule_key,
                [h.matched for h in hits if h not in kept],
            )
        if not kept:
            continue
        findings.append(_rule_finding(text, seg, kept, rule))
    return findings


def _rule_finding(text: str, seg: Segment, hits: list[Hit], rule: RuleSpec) -> Finding:
    from_brand = rule.source == "MARCA"
    output = CheckOutput(rule.output or "bloquear")
    if from_brand:
        reason, explanation = "regra_da_marca", f'A marca proibiu isto na ficha: "{rule.text}".'
    elif output == CheckOutput.BLOQUEAR:
        reason, explanation = "alegacao_proibida", rule.text
    else:
        reason, explanation = "zona_cinzenta", rule.text
    return _finding(
        text,
        seg.start + min(h.start for h in hits),
        seg.start + max(h.end for h in hits),
        output=output,
        rule_key=rule.rule_key,
        reason_type=reason,
        explanation=explanation,
        suggestion=rule.sugestao or "Retire esse trecho.",
    )


# --- 3. Padrões da H2 --------------------------------------------------------------------

_AMOUNT = re.compile(r"(\d+(?:[.,]\d+)?)\s*(kgs?|kilos?|quilos?|medidas|cm)\b")
_PERIOD = re.compile(r"(\d+)\s*(dias?|semanas?|meses)\b")
_UNIT = {"kg": "kg", "kgs": "kg", "kilo": "kg", "kilos": "kg", "quilo": "kg", "quilos": "kg"}


def _result_value(excerpt_norm: str) -> str:
    """Promessa de resultado normalizada: "5 kg em 7 dias" quando dá; senão o trecho."""
    amount = _AMOUNT.search(excerpt_norm)
    period = _PERIOD.search(excerpt_norm, amount.end() if amount else 0)
    if amount:
        value = f"{amount.group(1)} {_UNIT.get(amount.group(2), amount.group(2))}"
        return f"{value} em {period.group(1)} {period.group(2)}" if period else value
    return re.sub(r"\s+", " ", excerpt_norm).strip()


def h2_findings(
    text: str,
    seg: Segment,
    seg_norm: str,
    rules: list[ListRule],
    published_since: datetime | None,
    now: datetime,
    stale_days: int,
) -> list[Finding]:
    findings: list[Finding] = []
    for rule in rules:
        hits = find_hits(seg.text, rule.termos, rule.padroes, rule.junto_de, prepared=seg_norm)
        if not hits:
            continue
        start, end = min(h.start for h in hits), max(h.end for h in hits)
        extracted = None
        if rule.extrai:
            for t in rule.junto_de:  # o trecho da promessa inclui o verbo ("secar", "renda")
                for m in term_regex(t).finditer(seg_norm):
                    start, end = min(start, m.start()), max(end, m.end())
            extracted = {
                "type": "resultado",
                "attribute": "resultado",
                "value": _result_value(seg_norm[start:end]),
                "unit": None,
            }
        rule_key, explanation, reason = rule.rule_key, rule.explicacao, _reason(rule.rule_key)
        if rule.rule_key_vencida and _is_stale(published_since, now, stale_days):
            rule_key, explanation = rule.rule_key_vencida, rule.explicacao_vencida
            reason = _reason(rule.rule_key_vencida)
        findings.append(
            _finding(
                text,
                seg.start + start,
                seg.start + end,
                output=CheckOutput(rule.saida.value),
                rule_key=rule_key,
                reason_type=reason,
                explanation=explanation,
                suggestion=rule.sugestao,
                extracted=extracted,
            )
        )
    return findings


def _reason(rule_key: str) -> str:
    return rule_key.lower().replace("-", "_")


def _is_stale(published_since: datetime | None, now: datetime, stale_days: int) -> bool:
    if published_since is None:
        return False
    if published_since.tzinfo is None:
        published_since = published_since.replace(tzinfo=UTC)
    return (now - published_since).days > stale_days
