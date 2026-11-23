"""Checador de conteúdo (Agente 1).

Parte 1 (T06): `build_context` lê a versão da ficha e as `claim_rule` materializadas;
`run_layer1` aplica as regras a um texto (sem modelo e sem banco).
Parte 2 (T07): `check_content` grava a peça, roda a camada 1 e, se ligada, a camada 2 (modelo),
grava os achados e responde no formato da seção 9 do CONTEXTO.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from promessa.checker.deterministic import h2_findings, permitted_findings, prohibited_findings
from promessa.checker.llm_layer import Completer, run_layer2
from promessa.checker.models import (
    SEVERITY,
    CheckContext,
    CheckResponse,
    Disclosure,
    Finding,
    Layer1Result,
    RuleSpec,
    StoredFinding,
    overall_of,
)
from promessa.checker.offer_conditions import condition_findings
from promessa.checker.segment import segment
from promessa.config import get_settings, has_api_key
from promessa.db.enums import Channel, SubmittedBy
from promessa.db.models import CheckResult, ContentPiece, Creator, utcnow
from promessa.errors import CREATOR_INEXISTENTE, ENTRADA_INVALIDA, PECA_INEXISTENTE, DomainError
from promessa.facts import service as facts_service
from promessa.llm.client import LLMError, complete_json
from promessa.rules.loader import RuleSet, load_rules
from promessa.rules.normalize import match_text, normalize

log = logging.getLogger(__name__)

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


# --- Parte 2 (T07): check_content com persistência e camada 2 ---------------------------


def _parse_datetime(value: datetime | str | None) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as e:
        raise DomainError(ENTRADA_INVALIDA, f"Data inválida em published_since: {value!r}.") from e
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _enum(enum_cls, value, field: str):
    try:
        return enum_cls(value)
    except ValueError as e:
        allowed = ", ".join(m.value for m in enum_cls)
        raise DomainError(ENTRADA_INVALIDA, f"{field} inválido: {value!r}. Use: {allowed}.") from e


def llm_enabled(use_llm: bool | None = None) -> bool:
    settings = get_settings()
    wanted = settings.checker_use_llm if use_llm is None else use_llm
    return wanted and (has_api_key(settings) or settings.llm_offline)


def check_content(
    session: Session,
    product_id: str,
    creator_id: str,
    text: str,
    channel: str,
    submitted_by: str = "creator",
    published_since: datetime | str | None = None,
    parent_piece_id: str | None = None,
    *,
    use_llm: bool | None = None,
    completer: Completer | None = None,
    url: str | None = None,
) -> CheckResponse:
    """Grava a peça (imutável) com a versão vigente da ficha, roda as camadas e grava os achados."""
    if not text or not text.strip():
        raise DomainError(ENTRADA_INVALIDA, "O texto da peça está vazio.")
    if session.get(Creator, creator_id) is None:
        raise DomainError(CREATOR_INEXISTENTE, f"O creator {creator_id!r} não existe.")
    channel_enum = _enum(Channel, channel, "channel")
    submitted_enum = _enum(SubmittedBy, submitted_by, "submitted_by")
    since = _parse_datetime(published_since)
    if parent_piece_id is not None:
        parent = session.get(ContentPiece, parent_piece_id)
        if parent is None:
            raise DomainError(PECA_INEXISTENTE, f"A peça {parent_piece_id!r} não existe.")
        if parent.product_id != product_id:
            raise DomainError(ENTRADA_INVALIDA, "A peça anterior é de outro produto.")

    ctx = build_context(session, product_id)  # versão vigente agora
    piece = ContentPiece(
        creator_id=creator_id,
        product_id=product_id,
        facts_id=ctx.facts_id,
        text=text,
        url=url,
        channel=channel_enum,
        published_since=since,
        submitted_by=submitted_enum,
        parent_piece_id=parent_piece_id,
    )
    session.add(piece)
    session.flush()

    layer1 = run_layer1(text, ctx, published_since=since)
    findings = list(layer1.findings)
    layers_used = ["regras"]
    notes: list[str] = []
    # completer injetado (testes) liga a camada 2 mesmo sem chave, salvo use_llm=False
    enabled = (use_llm is not False) if completer is not None else llm_enabled(use_llm)
    if enabled:
        model = get_settings().checker_model
        try:
            findings += run_layer2(
                text, segment(text), ctx, layer1.findings, model, completer or complete_json
            )
            layers_used.append("modelo")
        except LLMError as e:
            log.warning("camada 2 indisponível para a peça %s: %s", piece.id, e)
            notes.append("O modelo não respondeu; a checagem usou só as regras.")
    else:
        notes.append("Checagem só com regras (modelo desligado ou sem chave).")
    findings.sort(key=lambda f: (f.span[0], -SEVERITY[f.output.value], f.rule_key or ""))

    stored: list[StoredFinding] = []
    for f in findings:
        row = CheckResult(
            piece_id=piece.id,
            span_start=f.span[0],
            span_end=f.span[1],
            excerpt=f.excerpt,
            output=f.output,
            rule_key=f.rule_key,
            source=f.source,
            reason_type=f.reason_type,
            explanation=f.explanation,
            suggestion=f.suggestion,
            extracted=f.extracted,
            model=f.model,
            prompt_version=f.prompt_version,
        )
        session.add(row)
        session.flush()
        stored.append(StoredFinding(id=row.id, **f.model_dump()))
        log.info(
            "check piece=%s rule=%s output=%s source=%s model=%s",
            piece.id,
            f.rule_key,
            f.output.value,
            f.source.value,
            f.model,
        )

    overall = overall_of(findings)
    return CheckResponse(
        piece_id=piece.id,
        facts_version=ctx.version,
        overall=overall,
        findings=stored,
        disclosure=layer1.disclosure,
        can_generate_link=overall != "bloquear",
        layers_used=layers_used,
        notes=notes,
    )
