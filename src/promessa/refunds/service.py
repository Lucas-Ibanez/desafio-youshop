"""Devolução: grava o evento (motivo já limpo) e a classificação (CONTEXTO 12.2; T10).

A ligação com a promessa registrada (`relation`, `linked_promise_id`) entra na T11; aqui a
relação fica provisória em `nao_aplicavel`.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from promessa.config import get_settings
from promessa.db.enums import RefundType, Relation
from promessa.db.models import Product, RefundClassification, RefundEvent, Sale, TrackedLink
from promessa.errors import ENTRADA_INVALIDA, VENDA_INEXISTENTE, DomainError
from promessa.privacy import preview, scrub
from promessa.refunds.classifier import classify_text

log = logging.getLogger(__name__)


class RefundResponse(BaseModel):
    """Resposta de `classify_refund` (CONTEXTO, seção 9)."""

    refund_id: int
    classification_id: int
    cause: str
    subcause: str
    main_cause: str
    buyer_belief: dict[str, Any] | None
    channel_mentioned: str | None
    relation: Relation
    linked_promise: dict[str, Any] | None
    confidence: float
    needs_review: bool
    explanation: str
    notes: list[str]


def classify_refund(
    session: Session,
    sale_id: int,
    reason_text: str,
    type: str = "reembolso",
    *,
    completer=None,
) -> RefundResponse:
    """Grava o evento de devolução (motivo limpo) e a classificação do motivo."""
    sale = session.get(Sale, sale_id)
    if sale is None:
        raise DomainError(VENDA_INEXISTENTE, f"A venda {sale_id!r} não existe.")
    try:
        refund_type = RefundType(type)
    except ValueError as e:
        raise DomainError(
            ENTRADA_INVALIDA, f"type inválido: {type!r}. Use: reembolso, chargeback, ticket."
        ) from e
    if not reason_text or not reason_text.strip():
        raise DomainError(ENTRADA_INVALIDA, "O motivo da devolução está vazio.")

    clean = scrub(reason_text)
    event = RefundEvent(sale_id=sale.id, type=refund_type, reason_text=clean)
    session.add(event)
    session.flush()

    link = session.get(TrackedLink, sale.link_id)
    product = session.get(Product, link.product_id)
    result = classify_text(clean, product.category.value, completer=completer)
    belief = result.buyer_belief.model_dump() if result.buyer_belief else None
    row = RefundClassification(
        refund_id=event.id,
        cause=result.cause,
        subcause=result.subcause,
        buyer_belief=belief,
        channel_mentioned=result.channel_mentioned,
        linked_promise_id=None,
        relation=Relation.NAO_APLICAVEL,  # ligação na T11
        confidence=result.confidence,
        explanation=result.explanation,
        model=result.model,
        prompt_version=result.prompt_version,
    )
    session.add(row)
    session.flush()
    log.info(
        "refund=%s cause=%s/%s conf=%.2f model=%s motivo=%r",
        event.id,
        result.cause,
        result.subcause,
        result.confidence,
        result.model,
        preview(clean),
    )

    notes = []
    if result.source == "sem_modelo":
        notes.append(result.explanation)
    if result.corrected:
        notes.append(
            "A subcausa do modelo não pertencia à causa e foi corrigida; confiança reduzida."
        )
    return RefundResponse(
        refund_id=event.id,
        classification_id=row.id,
        cause=result.cause,
        subcause=result.subcause,
        main_cause=result.main_cause,
        buyer_belief=belief,
        channel_mentioned=result.channel_mentioned,
        relation=row.relation,
        linked_promise=None,
        confidence=result.confidence,
        needs_review=result.confidence < get_settings().confidence_threshold,
        explanation=result.explanation,
        notes=notes,
    )
