"""Promessa registrada e link rastreado (módulo 3, CONTEXTO 8 e 9; T09).

O link só nasce depois da checagem, sem bloqueio pendente e com a ficha ainda vigente. Cada
achado com promessa extraída vira `registered_promise`, presa à peça e, pela peça, à venda.
"""

from __future__ import annotations

import base64
import re
import secrets

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from promessa.checker.service import disclosure_of
from promessa.config import get_settings
from promessa.db.enums import (
    ActorType,
    Approval,
    CheckOutput,
    PromiseAttribute,
    PromiseType,
    ReviewStatus,
)
from promessa.db.models import (
    CheckResult,
    ContentPiece,
    ProductFacts,
    RegisteredPromise,
    TrackedLink,
    get_current_facts,
)
from promessa.errors import (
    BLOQUEIO_PENDENTE,
    ENTRADA_INVALIDA,
    FICHA_DESATUALIZADA,
    PECA_INEXISTENTE,
    DomainError,
)
from promessa.rules.normalize import normalize

DISCLOSURE_MISSING = (
    "Ao publicar com este link, identifique a publicidade: use #publi no começo do texto."
)
DISCLOSURE_OK = (
    "A peça já tem identificação publicitária. Mantenha o #publi ao publicar com este link."
)


class PromiseView(BaseModel):
    id: int
    check_result_id: int | None
    type: PromiseType
    attribute: PromiseAttribute
    value: str | None
    unit: str | None
    normalized_text: str
    approval: Approval


class LinkResponse(BaseModel):
    link_id: str
    url: str
    piece_id: str
    product_id: str
    creator_id: str
    facts_version: int
    actor_type: ActorType
    registered_promises: list[PromiseView]
    disclosure_text: str


# --- Promessas ---------------------------------------------------------------------------


def _promise_type(rule_key: str | None, extracted: dict) -> PromiseType:
    if extracted.get("type") in {t.value for t in PromiseType}:
        return PromiseType(extracted["type"])
    key = rule_key or ""
    if key.startswith("COND-"):
        return PromiseType.CONDICAO_OFERTA
    if key.startswith(("IN28-", "MARCA-")):
        return PromiseType.ALEGACAO
    return PromiseType.RESULTADO


def _attribute(extracted: dict) -> PromiseAttribute:
    try:
        return PromiseAttribute(extracted.get("attribute"))
    except ValueError:
        return PromiseAttribute.OUTRO


def normalized_promise_text(
    type_: PromiseType, attribute: PromiseAttribute, value: str | None, unit: str | None
) -> str:
    """Texto comparável da promessa (relatórios agrupam por ele): minúsculas, sem acento.

    Ex.: "garantia 7 dias", "acesso 12 meses", "acesso vitalicio", "5 kg em 7 dias".
    """
    value_n = re.sub(r"\s+", " ", normalize(value or "")).strip()
    if type_ != PromiseType.CONDICAO_OFERTA:
        return value_n or attribute.value
    return " ".join(p for p in (attribute.value, value_n, unit or "") if p)


def _approval(result: CheckResult) -> Approval | None:
    if result.output == CheckOutput.REGISTRAR:
        return Approval.REGISTRADA
    if result.output == CheckOutput.REVISAR:
        # aprovada pela marca (D2): vale como registrada
        return (
            Approval.REGISTRADA
            if result.review_status == ReviewStatus.MANTIDO
            else Approval.EM_REVISAO
        )
    if result.output == CheckOutput.BLOQUEAR and result.review_status == ReviewStatus.REVERTIDO:
        return Approval.REGISTRADA  # a marca reverteu o bloqueio: a condição vale
    return None


def build_promises(piece_id: str, results: list[CheckResult]) -> list[RegisteredPromise]:
    """Uma promessa por achado com `extracted`; repetidas (mesmo tipo/atributo/valor) viram uma."""
    seen: set[tuple] = set()
    promises: list[RegisteredPromise] = []
    for r in sorted(results, key=lambda r: r.span_start):
        approval = _approval(r)
        if not r.extracted or approval is None:
            continue
        type_ = _promise_type(r.rule_key, r.extracted)
        attribute = _attribute(r.extracted)
        value, unit = r.extracted.get("value"), r.extracted.get("unit")
        key = (type_, attribute, value, unit)
        if key in seen:
            continue
        seen.add(key)
        promises.append(
            RegisteredPromise(
                piece_id=piece_id,
                check_result_id=r.id,
                type=type_,
                attribute=attribute,
                value=None if value is None else str(value),
                unit=unit,
                normalized_text=normalized_promise_text(type_, attribute, value, unit),
                approval=approval,
            )
        )
    return promises


def _view(p: RegisteredPromise) -> PromiseView:
    return PromiseView(
        id=p.id,
        check_result_id=p.check_result_id,
        type=p.type,
        attribute=p.attribute,
        value=p.value,
        unit=p.unit,
        normalized_text=p.normalized_text,
        approval=p.approval,
    )


# --- Link --------------------------------------------------------------------------------


def new_link_id(session: Session) -> str:
    """Código curto base32 de 8 caracteres (40 bits aleatórios), minúsculo e único."""
    while True:
        code = base64.b32encode(secrets.token_bytes(5)).decode("ascii").lower()
        if session.get(TrackedLink, code) is None:
            return code


def _pending_blocks(results: list[CheckResult]) -> list[CheckResult]:
    return [
        r
        for r in results
        if r.output == CheckOutput.BLOQUEAR and r.review_status != ReviewStatus.REVERTIDO
    ]


def _response(session: Session, link: TrackedLink) -> LinkResponse:
    facts = session.get(ProductFacts, link.facts_id)
    promises = session.scalars(
        select(RegisteredPromise)
        .where(RegisteredPromise.piece_id == link.piece_id)
        .order_by(RegisteredPromise.id)
    ).all()
    return LinkResponse(
        link_id=link.id,
        url=link.url,
        piece_id=link.piece_id,
        product_id=link.product_id,
        creator_id=link.creator_id,
        facts_version=facts.version,
        actor_type=link.actor_type,
        registered_promises=[_view(p) for p in promises],
        disclosure_text=link.disclosure_text or "",
    )


def register_content_and_link(
    session: Session, piece_id: str, actor_type: str = "humano"
) -> LinkResponse:
    """Registra as promessas da peça e gera o link rastreado.

    Erros: `PECA_INEXISTENTE`; `BLOQUEIO_PENDENTE` (lista os trechos); `FICHA_DESATUALIZADA`
    (a ficha vigente mudou depois da checagem). Chamar de novo devolve o mesmo link.
    """
    try:
        actor = ActorType(actor_type)
    except ValueError as e:
        raise DomainError(
            ENTRADA_INVALIDA, f"actor_type inválido: {actor_type!r}. Use: humano, agente."
        ) from e
    piece = session.get(ContentPiece, piece_id)
    if piece is None:
        raise DomainError(PECA_INEXISTENTE, f"A peça {piece_id!r} não existe.")

    existing = session.scalars(select(TrackedLink).where(TrackedLink.piece_id == piece_id)).first()
    if existing is not None:
        return _response(session, existing)

    results = list(
        session.scalars(
            select(CheckResult)
            .where(CheckResult.piece_id == piece_id)
            .order_by(CheckResult.span_start)
        )
    )
    pending = _pending_blocks(results)
    if pending:
        listed = "; ".join(f'"{r.excerpt}" ({r.rule_key}, achado {r.id})' for r in pending)
        raise DomainError(
            BLOQUEIO_PENDENTE,
            f"Há {len(pending)} trecho(s) bloqueado(s): {listed}. Envie uma peça corrigida "
            "(com parent_piece_id) ou conteste o bloqueio para a marca decidir.",
        )

    current = get_current_facts(session, piece.product_id)
    if current is None or current.id != piece.facts_id:
        checked = session.get(ProductFacts, piece.facts_id)
        raise DomainError(
            FICHA_DESATUALIZADA,
            f"A ficha do produto mudou depois da checagem (versão {checked.version} → "
            f"{current.version if current else '?'}). Reenvie a peça para checar de novo.",
        )

    session.add_all(build_promises(piece_id, results))
    link_id = new_link_id(session)
    link = TrackedLink(
        id=link_id,
        creator_id=piece.creator_id,
        product_id=piece.product_id,
        piece_id=piece.id,
        facts_id=piece.facts_id,
        actor_type=actor,
        url=get_settings().link_base_url + link_id,
        disclosure_text=DISCLOSURE_OK if disclosure_of(piece.text).present else DISCLOSURE_MISSING,
    )
    session.add(link)
    session.flush()
    return _response(session, link)
