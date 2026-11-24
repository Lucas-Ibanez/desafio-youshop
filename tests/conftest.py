"""Fixtures compartilhadas: banco em memória (nunca toca var/) e dados mínimos de produto."""

from datetime import UTC, datetime

import pytest

from promessa.db.enums import AccessType, Category, Recurrence
from promessa.db.models import Brand, Creator, Product, ProductFacts
from promessa.db.session import get_engine, get_session, init_db, set_default_engine


@pytest.fixture(autouse=True)
def _sem_modelo_fora_dos_testes_llm(request, monkeypatch):
    """Testes padrão nunca chamam o Gemini: sem chave e com a camada 2 desligada.

    Testes `@pytest.mark.llm` usam o .env de verdade (chave, cache em disco, LLM_OFFLINE).
    """
    from promessa.config import get_settings

    if request.node.get_closest_marker("llm") is None:
        monkeypatch.setenv("GEMINI_API_KEY", "")
        monkeypatch.setenv("CHECKER_USE_LLM", "false")
        monkeypatch.setenv("LLM_OFFLINE", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def engine():
    eng = get_engine("sqlite://")
    init_db(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    with get_session(engine) as s:
        yield s


@pytest.fixture
def seeded(engine):
    """Banco em memória com os seeds (5 marcas, produtos, fichas v1, creators)."""
    from promessa.facts.seed import load_seed

    with get_session(engine) as s:
        load_seed(s)
        s.commit()
    return engine


@pytest.fixture
def mcp_db(seeded):
    """Faz as ferramentas MCP (via `session_scope`) usarem o banco em memória com seeds."""
    set_default_engine(seeded)
    yield seeded
    set_default_engine(None)


@pytest.fixture
def product(session):
    """Marca, creator e produto fictícios, sem ficha."""
    session.add_all(
        [
            Brand(id="mk_teste", name="Marca Teste"),
            Creator(id="cr_teste", handle="@teste", display_name="Creator Teste"),
            Product(
                id="prod_teste",
                brand_id="mk_teste",
                name="Produto Teste",
                category=Category.INFOPRODUTO_OUTRO,
            ),
        ]
    )
    session.commit()
    return session.get(Product, "prod_teste")


def make_facts(product_id: str, version: int, valid_from: datetime, **overrides) -> ProductFacts:
    """Ficha com valores neutros; `overrides` troca qualquer campo."""
    data = dict(
        product_id=product_id,
        version=version,
        guarantee_days=7,
        access_type=AccessType.PRAZO,
        access_months=12,
        recurrence=Recurrence.UNICA,
        bonuses=[],
        extra_costs=[],
        valid_from=valid_from,
        created_by="teste",
    )
    data.update(overrides)
    return ProductFacts(**data)


@pytest.fixture
def facts_v1(session, product):
    facts = make_facts(product.id, 1, datetime(2026, 11, 1, tzinfo=UTC))
    session.add(facts)
    session.commit()
    return facts


@pytest.fixture
def make_sale():
    """Cria peça checada, link e venda (para testar devoluções). Devolve a `Sale`."""
    from promessa.checker.service import check_content
    from promessa.db.models import Sale
    from promessa.links.service import register_content_and_link

    def _make(
        session,
        product_id="prod_treino",
        creator_id="cr_ana",
        text="12 meses de acesso, 7 dias de garantia",
        amount_cents=19700,
    ):
        resp = check_content(session, product_id, creator_id, text, "instagram")
        link = register_content_and_link(session, resp.piece_id)
        sale = Sale(
            link_id=link.link_id, amount_cents=amount_cents, commission_cents=amount_cents // 5
        )
        session.add(sale)
        session.flush()
        return sale

    return _make
