"""Camada 1, condições da oferta × ficha (CONTEXTO 11.2, item 5).

Os extratores vêm de `condicoes_oferta.yaml`. Condição que contradiz a ficha → `bloquear`;
que bate → `registrar`. "N dias" só é garantia com contexto de garantia ou teste (o YAML garante).
Casamentos da mesma regra com o mesmo valor no mesmo trecho viram um achado só.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from promessa.checker.models import CheckContext, Finding
from promessa.checker.segment import Segment
from promessa.db.enums import AccessType, CheckOutput, PromiseAttribute, Recurrence
from promessa.rules.match import term_regex
from promessa.rules.normalize import normalize
from promessa.rules.schema import OfferConditionRule


@dataclass(frozen=True)
class _Claim:
    start: int
    end: int
    value: str
    unit: str | None


def _money(cents: int) -> str:
    reais = f"{cents / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {reais.removesuffix(',00')}"


def _extract(rule: OfferConditionRule, seg_norm: str) -> list[_Claim]:
    found: list[_Claim] = []
    for extractor in rule.extratores:
        for m in re.finditer(extractor.padrao, seg_norm):
            if extractor.valor is not None:
                value, unit = extractor.valor, None
            else:
                n = int(m.group("n"))
                unit_raw = (m.groupdict().get("unidade") or "").strip()
                if rule.atributo == PromiseAttribute.GARANTIA:
                    value, unit = str(n), "dias"
                elif unit_raw.startswith("ano"):
                    value, unit = str(n * 12), "meses"
                else:
                    value, unit = str(n), "meses"
            found.append(_Claim(m.start(), m.end(), value, unit))
    # remove sobreposições (fica o casamento mais longo)
    found.sort(key=lambda c: (c.start, -(c.end - c.start)))
    kept: list[_Claim] = []
    for c in found:
        if not any(c.start < k.end and k.start < c.end for k in kept):
            kept.append(c)
    return kept


def _facts_phrase(attr: PromiseAttribute, ctx: CheckContext) -> tuple[str, str | None]:
    """(como a ficha descreve a condição, frase sugerida para a peça)."""
    if attr == PromiseAttribute.GARANTIA:
        return f"garantia de {ctx.guarantee_days} dias", f"{ctx.guarantee_days} dias de garantia"
    if attr == PromiseAttribute.ACESSO:
        return {
            AccessType.VITALICIO: ("acesso vitalício", "acesso vitalício"),
            AccessType.PRAZO: (
                f"acesso por {ctx.access_months} meses",
                f"{ctx.access_months} meses de acesso",
            ),
            AccessType.ASSINATURA: (
                "acesso enquanto a assinatura estiver ativa",
                "acesso enquanto a assinatura estiver ativa",
            ),
            AccessType.NAO_APLICA: ("que não há acesso a conteúdo (produto físico)", None),
        }[ctx.access_type]
    if attr == PromiseAttribute.RECORRENCIA:
        billing = {
            Recurrence.UNICA: "pagamento único",
            Recurrence.MENSAL: "assinatura mensal",
            Recurrence.ANUAL: "assinatura anual",
        }[ctx.recurrence]
        if ctx.auto_renewal:
            billing += " com renovação automática"
        return billing, billing
    if attr == PromiseAttribute.BONUS:
        return ("bônus: " + ", ".join(ctx.bonuses) if ctx.bonuses else "nenhum bônus"), None
    costs = ", ".join(
        f"{c['descricao']} ({_money(c['valor_mensal_cents'])}/mês)" for c in ctx.extra_costs
    )
    return (f"custos extras: {costs}" if costs else "sem custos extras"), None


def _matches_facts(attr: PromiseAttribute, claim: _Claim, ctx: CheckContext) -> bool | None:
    """True = bate; False = contradiz; None = nada a registrar."""
    if attr == PromiseAttribute.GARANTIA:
        return int(claim.value) == ctx.guarantee_days
    if attr == PromiseAttribute.ACESSO:
        if claim.value == "vitalicio":
            return ctx.access_type == AccessType.VITALICIO
        return ctx.access_type == AccessType.PRAZO and ctx.access_months == int(claim.value)
    if attr == PromiseAttribute.RECORRENCIA:
        return ctx.recurrence == Recurrence.UNICA
    if attr == PromiseAttribute.BONUS:
        return bool(ctx.bonuses)
    if attr == PromiseAttribute.CUSTO:
        return False if ctx.extra_costs else None
    return None


def _bonus_value(seg_norm: str, ctx: CheckContext) -> str:
    """Nome do bônus da ficha citado no trecho, ou "citado"."""
    for bonus in ctx.bonuses:
        if term_regex(normalize(bonus).strip()).search(seg_norm):
            return bonus
    return "citado"


def condition_findings(
    text: str, seg: Segment, seg_norm: str, ctx: CheckContext, rules: list[OfferConditionRule]
) -> list[Finding]:
    findings: list[Finding] = []
    for rule in rules:
        groups: dict[tuple[str, str | None], list[_Claim]] = {}
        for claim in _extract(rule, seg_norm):
            groups.setdefault((claim.value, claim.unit), []).append(claim)
        for (value, unit), claims in groups.items():
            ok = _matches_facts(rule.atributo, claims[0], ctx)
            if ok is None:
                continue
            if rule.atributo == PromiseAttribute.BONUS:
                value = _bonus_value(seg_norm, ctx)
            facts_desc, phrase = _facts_phrase(rule.atributo, ctx)
            if ok:
                output, reason = CheckOutput.REGISTRAR, "condicao_igual_a_ficha"
                explanation = (
                    f"Bate com a ficha ({facts_desc}). Fica registrado como promessa da venda."
                )
                suggestion = None
            else:
                output, reason = CheckOutput.BLOQUEAR, "condicao_contraria_a_ficha"
                explanation = f"A ficha deste produto diz {facts_desc}. {rule.explicacao}"
                suggestion = f'Troque por "{phrase}".' if phrase else rule.sugestao
            start = seg.start + min(c.start for c in claims)
            end = seg.start + max(c.end for c in claims)
            findings.append(
                Finding(
                    excerpt=text[start:end],
                    span=(start, end),
                    output=output,
                    rule_key=rule.rule_key,
                    reason_type=reason,
                    explanation=explanation,
                    suggestion=suggestion,
                    extracted={
                        "type": "condicao_oferta",
                        "attribute": rule.atributo.value,
                        "value": value,
                        "unit": unit,
                    },
                )
            )
    return findings
