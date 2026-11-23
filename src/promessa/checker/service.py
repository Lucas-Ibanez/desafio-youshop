"""Checador de conteúdo (Agente 1). Parte 1 (T06): camada 1, sem modelo e sem banco.

`build_context` lê a versão da ficha e as `claim_rule` materializadas; `run_layer1` aplica as
regras a um texto e devolve achados, `overall` e `disclosure`. A persistência e a camada 2
(modelo) entram na T07.
"""

from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy.orm import Session

from promessa.checker.deterministic import h2_findings, permitted_findings, prohibited_findings
from promessa.checker.models import (
    SEVERITY,
    CheckContext,
    Disclosure,
    Finding,
    Layer1Result,
    RuleSpec,
    overall_of,
)
from promessa.checker.offer_conditions import condition_findings
from promessa.checker.segment import segment
from promessa.config import get_settings
from promessa.db.models import utcnow
from promessa.facts import service as facts_service
from promessa.rules.loader import RuleSet, load_rules
from promessa.rules.normalize import match_text, normalize

# Identificação publicitária (CONTEXTO 11.2, item 7). Não muda o `overall` (D5).
_DISCLOSURE = re.compile(r"(?<!\w)(?:#publi\w*|publi|publicidade|parceria paga|#ad)(?!\w)")
DISCLOSURE_SUGGESTION = "Identifique a publicidade: coloque #publi no começo do texto."


def build_context(session: Session, product_id: str, version: int | None = None) -> CheckContext:
    """Contexto da versão da ficha (a vigente, sem `version`) para a camada 1."""
    product = facts_service.get_product(session, product_id)
    facts = facts_service.get_facts(session, product_id, version)
    rules = facts_service.get_rules(session, facts)
    return CheckContext(
        product_id=product.id,
        category=product.category,
        facts_id=facts.id,
        version=facts.version,
        guarantee_days=facts.guarantee_days,
        access_type=facts.access_type,
        access_months=facts.access_months,
        recurrence=facts.recurrence,
        auto_renewal=facts.auto_renewal,
        bonuses=list(facts.bonuses),
        extra_costs=list(facts.extra_costs),
        rules=[
            RuleSpec(
                rule_key=r.rule_key,
                kind=r.kind.value,
                text=r.text,
                output=r.output.value if r.output else None,
                source=r.source.value,
                tema=(r.payload or {}).get("tema"),
                termos=(r.payload or {}).get("termos", []),
                padroes=(r.payload or {}).get("padroes", []),
                junto_de=(r.payload or {}).get("junto_de", []),
                sugestao=(r.payload or {}).get("sugestao"),
            )
            for r in rules
        ],
    )


def disclosure_of(text: str) -> Disclosure:
    present = bool(_DISCLOSURE.search(normalize(text)))
    return Disclosure(present=present, suggestion=None if present else DISCLOSURE_SUGGESTION)


def run_layer1(
    text: str,
    ctx: CheckContext,
    published_since: datetime | None = None,
    now: datetime | None = None,
    rules: RuleSet | None = None,
) -> Layer1Result:
    """Camada 1 inteira sobre o texto da peça. Não usa modelo nem banco."""
    rules = rules or load_rules()
    now = now or utcnow()
    stale_days = get_settings().urgency_stale_days
    norm = match_text(text, rules.normalization_map)

    findings: list[Finding] = []
    for seg in segment(text):
        seg_norm = norm[seg.start : seg.end]
        allowed, protected = permitted_findings(text, seg, seg_norm, ctx)
        findings += allowed
        findings += prohibited_findings(text, seg, seg_norm, ctx, protected)
        findings += condition_findings(text, seg, seg_norm, ctx, rules.offer_conditions.regras)
        findings += h2_findings(
            text, seg, seg_norm, rules.h2_patterns.regras, published_since, now, stale_days
        )
    findings.sort(key=lambda f: (f.span[0], -SEVERITY[f.output.value], f.rule_key or ""))
    return Layer1Result(
        findings=findings, overall=overall_of(findings), disclosure=disclosure_of(text)
    )
