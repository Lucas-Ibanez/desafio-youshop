"""Modelo de dados e banco (T02): tabelas, imutabilidade, versão vigente da ficha."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from promessa.db.enums import Channel, ReviewAction, Role
from promessa.db.models import ContentPiece, ProductFacts, ReviewEvent, get_current_facts
from promessa.db.session import IMMUTABLE_TABLES
from tests.conftest import make_facts

TABLES = {
    "brand",
    "creator",
    "product",
    "product_facts",
    "claim_rule",
    "content_piece",
    "check_result",
    "registered_promise",
    "tracked_link",
    "sale",
    "refund_event",
    "refund_classification",
    "review_event",
}


def test_banco_de_teste_em_memoria(engine):
    assert engine.url.database in (None, "", ":memory:")


def test_cria_13_tabelas_e_triggers(engine):
    assert set(inspect(engine).get_table_names()) == TABLES
    with engine.connect() as conn:
        triggers = set(conn.scalars(text("SELECT name FROM sqlite_master WHERE type = 'trigger'")))
    assert triggers == {f"{t}_no_{op}" for t in IMMUTABLE_TABLES for op in ("update", "delete")}


# --- Ficha versionada --------------------------------------------------------------------


def test_v1_continua_legivel_depois_da_v2(session, facts_v1):
    v2 = make_facts("prod_teste", 2, datetime(2026, 11, 20, tzinfo=UTC), guarantee_days=30)
    session.add(v2)
    session.commit()
    session.expunge_all()

    rows = session.scalars(
        select(ProductFacts).where(ProductFacts.product_id == "prod_teste").order_by("version")
    ).all()
    assert [(f.version, f.guarantee_days) for f in rows] == [(1, 7), (2, 30)]


def test_versao_duplicada_falha(session, facts_v1):
    session.add(make_facts("prod_teste", 1, datetime(2026, 11, 5, tzinfo=UTC)))
    with pytest.raises(IntegrityError):
        session.commit()


def test_get_current_facts_respeita_valid_from(session, facts_v1):
    v2_from = datetime(2026, 11, 20, tzinfo=UTC)
    session.add(make_facts("prod_teste", 2, v2_from))
    session.commit()

    assert get_current_facts(session, "prod_teste", at=v2_from - timedelta(seconds=1)).version == 1
    assert get_current_facts(session, "prod_teste", at=v2_from).version == 2
    assert get_current_facts(session, "prod_teste", at=v2_from + timedelta(days=1)).version == 2
    assert get_current_facts(session, "prod_teste", at=datetime(2026, 10, 1, tzinfo=UTC)) is None


def test_get_current_facts_ignora_versao_futura(session, facts_v1):
    session.add(make_facts("prod_teste", 2, datetime.now(UTC) + timedelta(days=30)))
    session.commit()
    assert get_current_facts(session, "prod_teste").version == 1


def test_datas_voltam_em_utc(session, facts_v1):
    session.expunge_all()
    facts = session.get(ProductFacts, facts_v1.id)
    assert facts.valid_from == datetime(2026, 11, 1, tzinfo=UTC)
    assert facts.valid_from.tzinfo is UTC


# --- Imutabilidade garantida pelo banco (invariante 1) -----------------------------------


def _piece(session, facts):
    piece = ContentPiece(
        creator_id="cr_teste",
        product_id="prod_teste",
        facts_id=facts.id,
        text="Treino de 20 minutos para fazer em casa",
        channel=Channel.INSTAGRAM,
    )
    session.add(piece)
    session.commit()
    return piece


def _review_event(session):
    event = ReviewEvent(
        target_type="check_result",
        target_id="1",
        action=ReviewAction.CONTESTAR,
        actor="cr_teste",
        actor_role=Role.CREATOR,
    )
    session.add(event)
    session.commit()
    return event


def test_update_em_product_facts_falha(session, facts_v1):
    facts_v1.guarantee_days = 30
    with pytest.raises(IntegrityError, match="ficha é imutável"):
        session.commit()
    session.rollback()
    assert session.get(ProductFacts, facts_v1.id).guarantee_days == 7


def test_delete_em_product_facts_falha(session, facts_v1):
    with pytest.raises(IntegrityError, match="ficha é imutável"):
        session.execute(text("DELETE FROM product_facts"))


def test_delete_em_content_piece_falha(session, facts_v1):
    piece = _piece(session, facts_v1)
    session.delete(piece)
    with pytest.raises(IntegrityError, match="peça é imutável"):
        session.commit()


def test_update_em_content_piece_falha(session, facts_v1):
    _piece(session, facts_v1)
    with pytest.raises(IntegrityError, match="peça é imutável"):
        session.execute(text("UPDATE content_piece SET text = 'outro texto'"))


def test_update_em_review_event_falha(session, facts_v1):
    event = _review_event(session)
    event.note = "mudei de ideia"
    with pytest.raises(IntegrityError, match="só de inserção"):
        session.commit()


def test_delete_em_review_event_falha(session, facts_v1):
    _review_event(session)
    with pytest.raises(IntegrityError, match="só de inserção"):
        session.execute(text("DELETE FROM review_event"))


# --- Integridade -------------------------------------------------------------------------


def test_enum_invalido_e_recusado_pelo_banco(session, product):
    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO product (id, brand_id, name, category) "
                "VALUES ('p2', 'mk_teste', 'X', 'categoria_inexistente')"
            )
        )


def test_chave_estrangeira_e_verificada(session, product):
    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO product (id, brand_id, name, category) "
                "VALUES ('p3', 'marca_inexistente', 'X', 'suplemento')"
            )
        )
