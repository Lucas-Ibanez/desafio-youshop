"""Relatórios por creator e por produto (CONTEXTO 12.4; T13).

Coorte pela data da venda: entram as vendas do período e as devoluções dessas vendas.
Só dados agregados; nenhum texto do comprador sai daqui (invariante 5).
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from promessa.config import get_settings
from promessa.db.enums import CheckOutput, PromiseAttribute, PromiseType, Relation
from promessa.db.models import (
    CheckResult,
    ContentPiece,
    Creator,
    Product,
    RefundClassification,
    RefundEvent,
    RegisteredPromise,
    Sale,
    TrackedLink,
)
from promessa.errors import (
    CREATOR_INEXISTENTE,
    ENTRADA_INVALIDA,
    PERIODO_INVALIDO,
    PRODUTO_INEXISTENTE,
    DomainError,
)
from promessa.links.service import normalized_promise_text
from promessa.refunds.linker import weighs_on_creator
from promessa.rules.loader import load_rules

CAUSE_GROUP = {  # agrupamento para o creator (CONTEXTO 12.5)
    "promessa_explicita": "promessa",
    "promessa_expectativa": "expectativa",
    "acesso_entrega": "acesso",
    "processo": "processo",
    "fraude": "fraude",
    "outros": "outros",
}


class CauseRow(BaseModel):
    causa: str
    rotulo: str
    devolucoes: int
    pct_devolucoes: float
    taxa_sobre_vendas: float
    pesa_no_creator: bool


class Indicator(BaseModel):
    status: Literal["ok", "dados_insuficientes"]
    taxa_promessa_confirmada: float | None
    devolucoes_confirmadas: int
    vendas: int
    minimo_vendas: int
    texto: str


class ContestedPromise(BaseModel):
    promessa: str
    tipo: str
    devolucoes: int
    trecho: str | None
    creators: list[str]


class BrandSignal(BaseModel):
    crenca: str
    devolucoes: int
    creators: list[str]
    texto: str


class CreatorRow(BaseModel):
    creator_id: str
    vendas: int
    devolucoes: int
    taxa_devolucao: float
    indicador: Indicator


class PromiseOutcomeReport(BaseModel):
    escopo: dict[str, str]
    periodo: dict[str, str]
    vendas: int
    devolucoes: int
    taxa_devolucao: float
    causas: list[CauseRow]
    indicador_creator: Indicator | None
    por_creator: list[CreatorRow]
    promessas_mais_contestadas: list[ContestedPromise]
    sinais_para_a_marca: list[BrandSignal]
    cobertura: dict[str, float]
    operacao: dict[str, float | None]
    integridade: dict[str, int]
    notas: list[str]


# --- Período e dados ---------------------------------------------------------------------


def parse_period(
    start: str | date | datetime, end: str | date | datetime
) -> tuple[datetime, datetime]:
    """[início 00:00, fim 23:59:59] em UTC. Datas no formato AAAA-MM-DD."""

    def as_date(v) -> date:
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        try:
            return date.fromisoformat(str(v)[:10])
        except ValueError as e:
            raise DomainError(PERIODO_INVALIDO, f"Data inválida: {v!r}. Use AAAA-MM-DD.") from e

    s, e = as_date(start), as_date(end)
    if s > e:
        raise DomainError(PERIODO_INVALIDO, f"O início ({s}) é depois do fim ({e}).")
    return datetime.combine(s, time.min, UTC), datetime.combine(
        e + timedelta(days=1), time.min, UTC
    )


def _rows(session: Session, start: datetime, end: datetime, creator_id=None, product_id=None):
    stmt = (
        select(Sale, TrackedLink)
        .join(TrackedLink, Sale.link_id == TrackedLink.id)
        .where(Sale.created_at >= start, Sale.created_at < end)
    )
    if creator_id:
        stmt = stmt.where(TrackedLink.creator_id == creator_id)
    if product_id:
        stmt = stmt.where(TrackedLink.product_id == product_id)
    return session.execute(stmt).all()


def _classifications(
    session: Session, sale_ids: list[int]
) -> list[tuple[RefundEvent, RefundClassification | None]]:
    if not sale_ids:
        return []
    events = session.scalars(select(RefundEvent).where(RefundEvent.sale_id.in_(sale_ids))).all()
    out = []
    for ev in events:
        c = session.scalars(
            select(RefundClassification)
            .where(RefundClassification.refund_id == ev.id)
            .order_by(RefundClassification.id.desc())
        ).first()
        out.append((ev, c))
    return out


def _indicator(sales: int, confirmed: int) -> Indicator:
    minimum = get_settings().min_sales_for_indicator
    if sales < minimum:
        return Indicator(
            status="dados_insuficientes",
            taxa_promessa_confirmada=None,
            devolucoes_confirmadas=confirmed,
            vendas=sales,
            minimo_vendas=minimum,
            texto=f"Dados insuficientes: {sales} vendas no período (mínimo {minimum}).",
        )
    rate = confirmed / sales
    return Indicator(
        status="ok",
        taxa_promessa_confirmada=rate,
        devolucoes_confirmadas=confirmed,
        vendas=sales,
        minimo_vendas=minimum,
        texto=f"{confirmed} de {sales} vendas voltaram por promessa da peça ({rate:.1%}).",
    )


def belief_text(belief: dict[str, Any] | None) -> str | None:
    if not belief:
        return None
    attr = belief.get("attribute") or "outro"
    kind = (
        PromiseType.CONDICAO_OFERTA
        if attr in ("garantia", "acesso", "recorrencia", "bonus", "custo")
        else PromiseType.RESULTADO
    )
    try:
        attribute = PromiseAttribute(attr)
    except ValueError:
        attribute = PromiseAttribute.OUTRO
    return normalized_promise_text(kind, attribute, belief.get("value"), belief.get("unit"))


# --- Relatório ---------------------------------------------------------------------------


def promise_outcome_report(
    session: Session,
    creator_id: str | None = None,
    product_id: str | None = None,
    start: str | date | datetime = "2026-10-26",
    end: str | date | datetime = "2026-11-22",
) -> PromiseOutcomeReport:
    """Taxas por causa, indicador, promessas contestadas, sinais para a marca e cobertura."""
    if bool(creator_id) == bool(product_id):
        raise DomainError(ENTRADA_INVALIDA, "Informe creator_id ou product_id (um dos dois).")
    if creator_id and session.get(Creator, creator_id) is None:
        raise DomainError(CREATOR_INEXISTENTE, f"O creator {creator_id!r} não existe.")
    if product_id and session.get(Product, product_id) is None:
        raise DomainError(PRODUTO_INEXISTENTE, f"O produto {product_id!r} não existe.")
    s, e = parse_period(start, end)
    threshold = get_settings().confidence_threshold
    rows = _rows(session, s, e, creator_id, product_id)
    sale_link = {sale.id: link for sale, link in rows}
    pairs = _classifications(session, list(sale_link))
    n_sales, n_refunds = len(rows), len(pairs)

    taxonomy = load_rules().taxonomy
    by_cause = Counter(c.cause for _, c in pairs if c)
    causes = [
        CauseRow(
            causa=c.causa,
            rotulo=c.rotulo,
            devolucoes=by_cause.get(c.causa, 0),
            pct_devolucoes=by_cause.get(c.causa, 0) / n_refunds if n_refunds else 0.0,
            taxa_sobre_vendas=by_cause.get(c.causa, 0) / n_sales if n_sales else 0.0,
            pesa_no_creator=c.pesa_no_creator,
        )
        for c in taxonomy.causas
    ]

    def confirmed(c: RefundClassification | None) -> bool:
        return bool(c) and weighs_on_creator(
            c.cause, c.relation, c.confidence, c.review_status, threshold
        )

    # promessas mais contestadas (só confirma) e sinais para a marca (crenças em contradiz)
    contested: dict[str, dict] = {}
    signals: dict[str, dict] = {}
    for ev, c in pairs:
        if not c:
            continue
        creator = sale_link[ev.sale_id].creator_id
        if c.relation == Relation.CONFIRMA and c.linked_promise_id:
            p = session.get(RegisteredPromise, c.linked_promise_id)
            item = contested.setdefault(
                p.normalized_text, {"tipo": p.type.value, "n": 0, "creators": set(), "trecho": None}
            )
            item["n"] += 1
            item["creators"].add(creator)
            if item["trecho"] is None and p.check_result_id:
                cr = session.get(CheckResult, p.check_result_id)
                item["trecho"] = cr.excerpt if cr else None
        if c.relation == Relation.CONTRADIZ:
            text = belief_text(c.buyer_belief) or "crença não informada"
            item = signals.setdefault(text, {"n": 0, "creators": set()})
            item["n"] += 1
            item["creators"].add(creator)
    top_contested = [
        ContestedPromise(
            promessa=k,
            tipo=v["tipo"],
            devolucoes=v["n"],
            trecho=v["trecho"],
            creators=sorted(v["creators"]),
        )
        for k, v in sorted(contested.items(), key=lambda kv: (-kv[1]["n"], kv[0]))
    ]
    top_signals = [
        BrandSignal(
            crenca=k,
            devolucoes=v["n"],
            creators=sorted(v["creators"]),
            texto=(
                f'{v["n"]} comprador(es) acreditavam em "{k}", que não está no que a peça '
                "registrou: a expectativa veio de fora da peça (kit de divulgação, outra peça, "
                "boca a boca)."
            ),
        )
        for k, v in sorted(signals.items(), key=lambda kv: (-kv[1]["n"], kv[0]))
    ]

    # por creator (escopo produto) e indicador (escopo creator)
    per_creator: dict[str, dict] = {}
    for _sale, link in rows:
        entry = per_creator.setdefault(
            link.creator_id, {"vendas": 0, "devolucoes": 0, "confirmadas": 0}
        )
        entry["vendas"] += 1
    for ev, c in pairs:
        row = per_creator[sale_link[ev.sale_id].creator_id]
        row["devolucoes"] += 1
        row["confirmadas"] += confirmed(c)
    creators_table = [
        CreatorRow(
            creator_id=cid,
            vendas=v["vendas"],
            devolucoes=v["devolucoes"],
            taxa_devolucao=v["devolucoes"] / v["vendas"] if v["vendas"] else 0.0,
            indicador=_indicator(v["vendas"], v["confirmadas"]),
        )
        for cid, v in sorted(per_creator.items())
    ]
    indicator = _indicator(n_sales, sum(confirmed(c) for _, c in pairs)) if creator_id else None

    # cobertura, operação e integridade
    pieces = {link.piece_id for _, link in rows}
    with_promise = {
        pid
        for pid in pieces
        if session.scalar(
            select(RegisteredPromise.id).where(RegisteredPromise.piece_id == pid).limit(1)
        )
    }
    classified = [c for _, c in pairs if c]
    hours = [
        (c.created_at - ev.created_at).total_seconds() / 3600
        for ev, c in pairs
        if c and c.created_at and ev.created_at
    ]
    scope_pieces = select(CheckResult).where(
        CheckResult.output == CheckOutput.BLOQUEAR, CheckResult.rule_key.like("COND-%")
    )
    if creator_id or product_id:
        piece_q = select(ContentPiece.id)
        piece_q = (
            piece_q.where(ContentPiece.creator_id == creator_id)
            if creator_id
            else piece_q.where(ContentPiece.product_id == product_id)
        )
        scope_pieces = scope_pieces.where(CheckResult.piece_id.in_(piece_q))
    blocked_conditions = len(session.scalars(scope_pieces).all())

    notes = []
    if n_sales == 0:
        notes.append("Nenhuma venda no período.")
    return PromiseOutcomeReport(
        escopo={"creator_id": creator_id} if creator_id else {"product_id": product_id},
        periodo={"inicio": s.date().isoformat(), "fim": (e - timedelta(days=1)).date().isoformat()},
        vendas=n_sales,
        devolucoes=n_refunds,
        taxa_devolucao=n_refunds / n_sales if n_sales else 0.0,
        causas=causes,
        indicador_creator=indicator,
        por_creator=creators_table if product_id else [],
        promessas_mais_contestadas=top_contested[:5],
        sinais_para_a_marca=top_signals[:5],
        cobertura={
            "vendas_com_promessa_registrada": (
                sum(1 for _, link in rows if link.piece_id in with_promise) / n_sales
                if n_sales
                else 0.0
            ),
            "devolucoes_classificadas": len(classified) / n_refunds if n_refunds else 0.0,
            "devolucoes_ligadas_a_promessa": (
                sum(1 for c in classified if c.linked_promise_id) / n_refunds if n_refunds else 0.0
            ),
        },
        operacao={"horas_medias_ate_classificar": sum(hours) / len(hours) if hours else None},
        integridade={"condicoes_contrarias_barradas": blocked_conditions},
        notas=notes,
    )
