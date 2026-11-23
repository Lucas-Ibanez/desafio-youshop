"""Tabelas do MVP (CONTEXTO, seção 8): 10 entidades do guia + 3 de apoio.

Dinheiro em centavos (inteiro). Datas sempre em UTC (tipo `UTCDateTime`).
Imutabilidade de `product_facts`, `content_piece` e `review_event` é garantida por trigger
no banco (ver `session.py`), não só pelo ORM.
"""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
    select,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from promessa.db.enums import (
    AccessType,
    ActorType,
    Approval,
    Category,
    Channel,
    CheckOutput,
    CheckSource,
    PromiseAttribute,
    PromiseType,
    Recurrence,
    RefundType,
    Relation,
    ReviewAction,
    ReviewStatus,
    Role,
    RuleKind,
    RuleOutput,
    RuleSource,
    SubmittedBy,
)


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """Grava em UTC sem fuso (SQLite não guarda fuso) e devolve `datetime` com fuso UTC.

    `datetime` sem fuso na entrada é tratado como UTC.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is not None:
            value = value.astimezone(UTC)
        return value.replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC)


def enum_column(enum_cls: type[StrEnum]) -> SAEnum:
    """Enum guardado como texto, com CHECK no banco aceitando só os valores do enum."""
    return SAEnum(
        enum_cls,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda members: [m.value for m in members],
        length=max(len(m.value) for m in enum_cls),
    )


class Base(DeclarativeBase):
    type_annotation_map = {datetime: UTCDateTime(), dict[str, Any]: JSON, list[Any]: JSON}


# --- Apoio ---------------------------------------------------------------------------------


class Brand(Base):
    __tablename__ = "brand"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # ex.: mk_movimento
    name: Mapped[str] = mapped_column(String(200))


class Creator(Base):
    __tablename__ = "creator"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # ex.: cr_ana
    handle: Mapped[str] = mapped_column(String(100))
    display_name: Mapped[str] = mapped_column(String(200))


# --- Ficha de promessas ------------------------------------------------------------------


class Product(Base):
    __tablename__ = "product"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # ex.: prod_treino
    brand_id: Mapped[str] = mapped_column(ForeignKey("brand.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[Category] = mapped_column(enum_column(Category))


class ProductFacts(Base):
    """Versão da ficha. Imutável: mudança = nova versão (trigger no banco)."""

    __tablename__ = "product_facts"
    __table_args__ = (UniqueConstraint("product_id", "version", name="uq_product_facts_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("product.id"))
    version: Mapped[int] = mapped_column(Integer)
    guarantee_days: Mapped[int] = mapped_column(Integer)
    access_type: Mapped[AccessType] = mapped_column(enum_column(AccessType))
    access_months: Mapped[int | None] = mapped_column(Integer)
    recurrence: Mapped[Recurrence] = mapped_column(enum_column(Recurrence))
    auto_renewal: Mapped[bool] = mapped_column(default=False)
    bonuses: Mapped[list[Any]] = mapped_column(default=list)
    # lista de {descricao, valor_mensal_cents}
    extra_costs: Mapped[list[Any]] = mapped_column(default=list)
    valid_from: Mapped[datetime] = mapped_column(default=utcnow)
    created_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class ClaimRule(Base):
    """Regra aplicável àquela versão da ficha (cópia do YAML ou regra da marca; decisão D4)."""

    __tablename__ = "claim_rule"

    id: Mapped[int] = mapped_column(primary_key=True)
    facts_id: Mapped[int] = mapped_column(ForeignKey("product_facts.id"), index=True)
    rule_key: Mapped[str] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(Text)
    kind: Mapped[RuleKind] = mapped_column(enum_column(RuleKind))
    source: Mapped[RuleSource] = mapped_column(enum_column(RuleSource))
    reference: Mapped[str] = mapped_column(String(500))  # arquivo.yaml@versao ou URL
    output: Mapped[RuleOutput | None] = mapped_column(enum_column(RuleOutput))  # só proibidas
    # Cópia do que a camada 1 precisa para aplicar a regra (termos, padrões, junto_de, tema,
    # sugestão). Fica na versão da ficha para provar o que valia no dia da venda (D4, D22).
    payload: Mapped[dict[str, Any] | None]


# --- Checagem e registro -----------------------------------------------------------------


class ContentPiece(Base):
    """Peça enviada. Imutável: correção = nova peça com `parent_piece_id` (trigger no banco)."""

    __tablename__ = "content_piece"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    creator_id: Mapped[str] = mapped_column(ForeignKey("creator.id"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("product.id"), index=True)
    facts_id: Mapped[int] = mapped_column(ForeignKey("product_facts.id"))
    text: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(500))
    channel: Mapped[Channel] = mapped_column(enum_column(Channel))
    published_since: Mapped[datetime | None]
    submitted_by: Mapped[SubmittedBy] = mapped_column(
        enum_column(SubmittedBy), default=SubmittedBy.CREATOR
    )
    parent_piece_id: Mapped[str | None] = mapped_column(ForeignKey("content_piece.id"))
    submitted_at: Mapped[datetime] = mapped_column(default=utcnow)


class CheckResult(Base):
    __tablename__ = "check_result"

    id: Mapped[int] = mapped_column(primary_key=True)
    piece_id: Mapped[str] = mapped_column(ForeignKey("content_piece.id"), index=True)
    span_start: Mapped[int] = mapped_column(Integer)
    span_end: Mapped[int] = mapped_column(Integer)
    excerpt: Mapped[str] = mapped_column(Text)
    output: Mapped[CheckOutput] = mapped_column(enum_column(CheckOutput))
    rule_key: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[CheckSource] = mapped_column(enum_column(CheckSource))
    reason_type: Mapped[str] = mapped_column(String(64))
    explanation: Mapped[str] = mapped_column(Text)
    suggestion: Mapped[str | None] = mapped_column(Text)
    extracted: Mapped[dict[str, Any] | None]
    model: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(50))
    confidence: Mapped[float | None] = mapped_column(Float)
    review_status: Mapped[ReviewStatus] = mapped_column(
        enum_column(ReviewStatus), default=ReviewStatus.NAO_APLICAVEL
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(100))
    reviewed_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class RegisteredPromise(Base):
    __tablename__ = "registered_promise"

    id: Mapped[int] = mapped_column(primary_key=True)
    piece_id: Mapped[str] = mapped_column(ForeignKey("content_piece.id"), index=True)
    check_result_id: Mapped[int | None] = mapped_column(ForeignKey("check_result.id"))
    type: Mapped[PromiseType] = mapped_column(enum_column(PromiseType))
    attribute: Mapped[PromiseAttribute] = mapped_column(enum_column(PromiseAttribute))
    value: Mapped[str | None] = mapped_column(String(200))
    unit: Mapped[str | None] = mapped_column(String(50))
    normalized_text: Mapped[str] = mapped_column(Text)
    approval: Mapped[Approval] = mapped_column(enum_column(Approval))


class TrackedLink(Base):
    __tablename__ = "tracked_link"

    id: Mapped[str] = mapped_column(String(8), primary_key=True)  # código base32 (T09)
    creator_id: Mapped[str] = mapped_column(ForeignKey("creator.id"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("product.id"), index=True)
    piece_id: Mapped[str] = mapped_column(ForeignKey("content_piece.id"), index=True)
    facts_id: Mapped[int] = mapped_column(ForeignKey("product_facts.id"))
    actor_type: Mapped[ActorType] = mapped_column(enum_column(ActorType), default=ActorType.HUMANO)
    url: Mapped[str] = mapped_column(String(500))
    disclosure_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


# --- Venda e devolução -------------------------------------------------------------------


class Sale(Base):
    """Herda creator, peça e ficha pelo link."""

    __tablename__ = "sale"

    id: Mapped[int] = mapped_column(primary_key=True)
    link_id: Mapped[str] = mapped_column(ForeignKey("tracked_link.id"), index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    commission_cents: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class RefundEvent(Base):
    __tablename__ = "refund_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sale.id"), index=True)
    type: Mapped[RefundType] = mapped_column(enum_column(RefundType), default=RefundType.REEMBOLSO)
    reason_text: Mapped[str] = mapped_column(Text)  # já passou por privacy.scrub
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class RefundClassification(Base):
    __tablename__ = "refund_classification"

    id: Mapped[int] = mapped_column(primary_key=True)
    refund_id: Mapped[int] = mapped_column(ForeignKey("refund_event.id"), index=True)
    cause: Mapped[str] = mapped_column(String(64))  # taxonomia em YAML (T03)
    subcause: Mapped[str] = mapped_column(String(64))
    buyer_belief: Mapped[dict[str, Any] | None]
    channel_mentioned: Mapped[str | None] = mapped_column(String(50))
    linked_promise_id: Mapped[int | None] = mapped_column(ForeignKey("registered_promise.id"))
    relation: Mapped[Relation] = mapped_column(
        enum_column(Relation), default=Relation.NAO_APLICAVEL
    )
    confidence: Mapped[float] = mapped_column(Float)
    explanation: Mapped[str] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(50))
    review_status: Mapped[ReviewStatus] = mapped_column(
        enum_column(ReviewStatus), default=ReviewStatus.NAO_APLICAVEL
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(100))
    reviewed_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


# --- Auditoria ---------------------------------------------------------------------------


class ReviewEvent(Base):
    """Log de auditoria das decisões humanas. Só inserção (trigger no banco)."""

    __tablename__ = "review_event"
    __table_args__ = (Index("ix_review_event_target", "target_type", "target_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    target_type: Mapped[str] = mapped_column(String(50))  # ex.: check_result
    target_id: Mapped[str] = mapped_column(String(64))
    action: Mapped[ReviewAction] = mapped_column(enum_column(ReviewAction))
    actor: Mapped[str] = mapped_column(String(100))
    actor_role: Mapped[Role] = mapped_column(enum_column(Role))
    note: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any] | None]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


# --- Consultas ---------------------------------------------------------------------------


def get_current_facts(
    session: Session, product_id: str, at: datetime | None = None
) -> ProductFacts | None:
    """Versão da ficha vigente em `at` (padrão: agora): maior `valid_from ≤ at`.

    Empate em `valid_from` fica com a maior `version`. Sem versão vigente, devolve None.
    """
    at = at or utcnow()
    stmt = (
        select(ProductFacts)
        .where(ProductFacts.product_id == product_id, ProductFacts.valid_from <= at)
        .order_by(ProductFacts.valid_from.desc(), ProductFacts.version.desc())
        .limit(1)
    )
    return session.scalars(stmt).first()
