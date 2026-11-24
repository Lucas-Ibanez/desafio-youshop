"""Devolução: grava o evento (motivo já limpo), a classificação (T10) e a ligação com a
promessa registrada na peça da venda (T11; CONTEXTO 12.2 e 12.3).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from promessa.config import get_settings
from promessa.db.enums import RefundType, Relation
from promessa.db.models import (
    Product,
    RefundClassification,
    RefundEvent,
    RegisteredPromise,
    Sale,
    TrackedLink,
)
from promessa.errors import ENTRADA_INVALIDA, VENDA_INEXISTENTE, DomainError
from promessa.privacy import preview, scrub
from promessa.refunds.classifier import classify_text
from promessa.refunds.linker import link as link_to_promise
from promessa.refunds.linker import weighs_on_creator

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
    weighs_on_creator: bool
    explanation: str
    relation_explanation: str
    notes: list[str]


def classify_refund(
    session: Session,
    sale_id: int,
    reason_text: str,
    type: str = "reembolso",
    *,
    completer=None,
    link_completer=None,
    at: datetime | None = None,
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
    # `at` data a devolução (simulador, T13); sem ele, agora
    event = RefundEvent(sale_id=sale.id, type=refund_type, reason_text=clean)
    if at is not None:
        event.created_at = at
    session.add(event)
    session.flush()

    link = session.get(TrackedLink, sale.link_id)
    product = session.get(Product, link.product_id)
    result = classify_text(clean, product.category.value, completer=completer)
    belief = result.buyer_belief.model_dump() if result.buyer_belief else None
    promises = list(
        session.scalars(
            select(RegisteredPromise)
            .where(RegisteredPromise.piece_id == link.piece_id)
            .order_by(RegisteredPromise.id)
        )
    )
    linked = link_to_promise(result.cause, belief, clean, promises, completer=link_completer)
    promise = next((p for p in promises if p.id == linked.promise_id), None)
    row = RefundClassification(
        refund_id=event.id,
        cause=result.cause,
        subcause=result.subcause,
        buyer_belief=belief,
        channel_mentioned=result.channel_mentioned,
        linked_promise_id=linked.promise_id,
        relation=linked.relation,
        confidence=result.confidence,
        explanation=result.explanation,
        model=result.model,
        prompt_version=result.prompt_version,
    )
    if at is not None:
        row.created_at = at
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
        linked_promise=None
        if promise is None
        else {
            "id": promise.id,
            "type": promise.type.value,
            "attribute": promise.attribute.value,
            "normalized_text": promise.normalized_text,
            "approval": promise.approval.value,
        },
        confidence=result.confidence,
        needs_review=result.confidence < get_settings().confidence_threshold,
        weighs_on_creator=weighs_on_creator(
            result.cause,
            row.relation,
            result.confidence,
            row.review_status.value if row.review_status else "nao_aplicavel",
        ),
        explanation=result.explanation,
        relation_explanation=linked.explanation,
        notes=notes,
    )
