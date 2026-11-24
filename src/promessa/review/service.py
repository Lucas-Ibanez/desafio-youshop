"""Fila de revisão e decisões humanas (CONTEXTO 13; T09).

Permissões:
- `contestar`: só `bloquear` ainda sem decisão; creator (só da própria peça) ou marca.
- `manter` / `reverter`: bloqueio (contestado ou não), só marca ou Operações. O creator não
  resolve a própria contestação.
- `aprovar`: achado `revisar` (D2), só marca ou Operações; a promessa `em_revisao` vira
  `registrada`.
- `manter` / `reclassificar` em classificação de devolução: só marca ou Operações.
Toda ação grava um `review_event` (só inserção) com ator e papel.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from promessa.config import get_settings
from promessa.db.enums import Approval, CheckOutput, ReviewAction, ReviewStatus, Role
from promessa.db.models import (
    CheckResult,
    ContentPiece,
    RefundClassification,
    RefundEvent,
    RegisteredPromise,
    ReviewEvent,
    utcnow,
)
from promessa.errors import ENTRADA_INVALIDA, PAPEL_NAO_AUTORIZADO, DomainError
from promessa.rules.loader import load_rules

TargetType = Literal["check_result", "refund_classification"]
DECIDERS = {Role.MARCA, Role.OPERACOES}
REASON_PREVIEW = 80  # caracteres do motivo do comprador na fila (CONTEXTO 15)


class QueueItem(BaseModel):
    kind: Literal["bloqueio", "classificacao"]
    target_type: TargetType
    target_id: str
    product_id: str | None
    creator_id: str | None
    summary: str
    context: dict[str, Any]
    since: datetime | None
    age_hours: float | None


class ReviewQueue(BaseModel):
    items: list[QueueItem]


class ReviewResult(BaseModel):
    target_type: TargetType
    target_id: str
    action: ReviewAction
    review_status: ReviewStatus
    event_id: int
    actor: str
    actor_role: Role


# --- Fila --------------------------------------------------------------------------------


def _last_event(session: Session, target_type: str, target_id: str) -> ReviewEvent | None:
    return session.scalars(
        select(ReviewEvent)
        .where(ReviewEvent.target_type == target_type, ReviewEvent.target_id == str(target_id))
        .order_by(ReviewEvent.id.desc())
    ).first()


def _age(since: datetime | None) -> float | None:
    return None if since is None else round((utcnow() - since).total_seconds() / 3600, 1)


def list_review_queue(session: Session, kind: str | None = None) -> ReviewQueue:
    """Pendências para marca e Operações: bloqueios contestados e classificações de baixa
    confiança, com o contexto para decidir e a idade do item."""
    if kind not in (None, "bloqueio", "classificacao"):
        raise DomainError(
            ENTRADA_INVALIDA, f"kind inválido: {kind!r}. Use: bloqueio, classificacao."
        )
    items: list[QueueItem] = []
    if kind in (None, "bloqueio"):
        contested = session.scalars(
            select(CheckResult).where(CheckResult.review_status == ReviewStatus.CONTESTADO)
        )
        for r in contested:
            piece = session.get(ContentPiece, r.piece_id)
            event = _last_event(session, "check_result", str(r.id))
            since = event.created_at if event else r.created_at
            items.append(
                QueueItem(
                    kind="bloqueio",
                    target_type="check_result",
                    target_id=str(r.id),
                    product_id=piece.product_id,
                    creator_id=piece.creator_id,
                    summary=f'Bloqueio contestado: "{r.excerpt}" ({r.rule_key})',
                    context={
                        "piece_id": piece.id,
                        "piece_text": piece.text,
                        "excerpt": r.excerpt,
                        "rule_key": r.rule_key,
                        "explanation": r.explanation,
                        "suggestion": r.suggestion,
                        "contest_note": event.note if event else None,
                        "contested_by": event.actor if event else None,
                    },
                    since=since,
                    age_hours=_age(since),
                )
            )
    if kind in (None, "classificacao"):
        threshold = get_settings().confidence_threshold
        low = session.scalars(
            select(RefundClassification).where(
                RefundClassification.review_status == ReviewStatus.NAO_APLICAVEL,
                RefundClassification.confidence < threshold,
            )
        )
        for c in low:
            refund = session.get(RefundEvent, c.refund_id)
            items.append(
                QueueItem(
                    kind="classificacao",
                    target_type="refund_classification",
                    target_id=str(c.id),
                    product_id=None,
                    creator_id=None,
                    summary=(
                        f"Classificação com confiança {c.confidence:.2f}: {c.cause}/{c.subcause}"
                    ),
                    context={
                        "refund_id": c.refund_id,
                        "cause": c.cause,
                        "subcause": c.subcause,
                        "relation": c.relation.value,
                        "confidence": c.confidence,
                        "explanation": c.explanation,
                        "reason_preview": (refund.reason_text or "")[:REASON_PREVIEW]
                        if refund
                        else None,
                    },
                    since=c.created_at,
                    age_hours=_age(c.created_at),
                )
            )
    items.sort(key=lambda i: i.since or utcnow())
    return ReviewQueue(items=items)


# --- Decisões ----------------------------------------------------------------------------


def _parse(enum_cls, value, field: str):
    try:
        return enum_cls(value)
    except ValueError as e:
        allowed = ", ".join(m.value for m in enum_cls)
        raise DomainError(ENTRADA_INVALIDA, f"{field} inválido: {value!r}. Use: {allowed}.") from e


def _deny(message: str) -> DomainError:
    return DomainError(PAPEL_NAO_AUTORIZADO, message)


def _review_check_result(
    session: Session, result: CheckResult, action: ReviewAction, actor: str, role: Role
) -> ReviewStatus:
    if action == ReviewAction.CONTESTAR:
        if result.output != CheckOutput.BLOQUEAR:
            raise DomainError(ENTRADA_INVALIDA, "Só um trecho bloqueado pode ser contestado.")
        if result.review_status != ReviewStatus.NAO_APLICAVEL:
            raise DomainError(
                ENTRADA_INVALIDA, f"Este bloqueio já está {result.review_status.value}."
            )
        if role == Role.CREATOR:
            piece = session.get(ContentPiece, result.piece_id)
            if actor != piece.creator_id:
                raise _deny("O creator só pode contestar bloqueios das próprias peças.")
        elif role != Role.MARCA:
            raise _deny("Contestar é ação do creator ou da marca.")
        result.review_status = ReviewStatus.CONTESTADO
        return result.review_status

    if action in (ReviewAction.MANTER, ReviewAction.REVERTER):
        if role not in DECIDERS:
            raise _deny(
                "Só a marca ou Operações decidem um bloqueio; "
                "o creator não resolve a própria contestação."
            )
        if result.output != CheckOutput.BLOQUEAR:
            raise DomainError(ENTRADA_INVALIDA, "Manter ou reverter vale só para trecho bloqueado.")
        if result.review_status in (ReviewStatus.MANTIDO, ReviewStatus.REVERTIDO):
            raise DomainError(
                ENTRADA_INVALIDA, f"Este bloqueio já foi {result.review_status.value}."
            )
        result.review_status = (
            ReviewStatus.MANTIDO if action == ReviewAction.MANTER else ReviewStatus.REVERTIDO
        )
    elif action == ReviewAction.APROVAR:
        if role not in DECIDERS:
            raise _deny("Só a marca ou Operações aprovam um trecho em revisão.")
        if result.output != CheckOutput.REVISAR:
            raise DomainError(ENTRADA_INVALIDA, "Aprovar vale só para trecho em revisão.")
        result.review_status = ReviewStatus.MANTIDO  # trecho aceito como está (D28)
        for promise in session.scalars(
            select(RegisteredPromise).where(RegisteredPromise.check_result_id == result.id)
        ):
            if promise.approval == Approval.EM_REVISAO:
                promise.approval = Approval.REGISTRADA
    else:
        raise DomainError(
            ENTRADA_INVALIDA, f"Ação {action.value!r} não vale para um achado do checador."
        )
    result.reviewed_by = actor
    result.reviewed_at = utcnow()
    return result.review_status


def _review_classification(
    classification: RefundClassification,
    action: ReviewAction,
    actor: str,
    role: Role,
    payload: dict[str, Any] | None,
) -> ReviewStatus:
    if role not in DECIDERS:
        raise _deny("Só a marca ou Operações revisam uma classificação de devolução.")
    if action == ReviewAction.MANTER:
        classification.review_status = ReviewStatus.MANTIDO
    elif action == ReviewAction.RECLASSIFICAR:
        cause = (payload or {}).get("cause")
        subcause = (payload or {}).get("subcause")
        valid = load_rules().taxonomy.subcauses_by_cause()
        if subcause not in valid.get(cause, ()):
            raise DomainError(
                ENTRADA_INVALIDA,
                f"Par causa/subcausa inválido: {cause}/{subcause}. Veja a taxonomia.",
            )
        classification.cause, classification.subcause = cause, subcause
        classification.review_status = ReviewStatus.REVERTIDO
    else:
        raise DomainError(
            ENTRADA_INVALIDA, f"Ação {action.value!r} não vale para uma classificação."
        )
    classification.reviewed_by = actor
    classification.reviewed_at = utcnow()
    return classification.review_status


def submit_review(
    session: Session,
    target_type: str,
    target_id: str | int,
    action: str,
    actor: str,
    actor_role: str,
    note: str | None = None,
    payload: dict[str, Any] | None = None,
) -> ReviewResult:
    """Registra uma decisão humana e atualiza o estado do alvo."""
    action_e = _parse(ReviewAction, action, "action")
    role = _parse(Role, actor_role, "actor_role")
    if role == Role.SISTEMA:
        raise _deny("Revisão é decisão humana; o papel sistema não revisa.")
    if not actor or not str(actor).strip():
        raise DomainError(ENTRADA_INVALIDA, "Informe quem decide (actor).")
    try:
        key = int(target_id)
    except (TypeError, ValueError) as e:
        raise DomainError(ENTRADA_INVALIDA, f"target_id inválido: {target_id!r}.") from e

    if target_type == "check_result":
        target = session.get(CheckResult, key)
        if target is None:
            raise DomainError(ENTRADA_INVALIDA, f"Achado {key} não existe.")
        status = _review_check_result(session, target, action_e, actor, role)
    elif target_type == "refund_classification":
        target = session.get(RefundClassification, key)
        if target is None:
            raise DomainError(ENTRADA_INVALIDA, f"Classificação {key} não existe.")
        status = _review_classification(target, action_e, actor, role, payload)
    else:
        raise DomainError(
            ENTRADA_INVALIDA, "target_type inválido. Use: check_result, refund_classification."
        )

    event = ReviewEvent(
        target_type=target_type,
        target_id=str(key),
        action=action_e,
        actor=actor,
        actor_role=role,
        note=note,
        payload=payload,
    )
    session.add(event)
    session.flush()
    return ReviewResult(
        target_type=target_type,
        target_id=str(key),
        action=action_e,
        review_status=status,
        event_id=event.id,
        actor=actor,
        actor_role=role,
    )
