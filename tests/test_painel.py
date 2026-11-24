"""Painel (T14) com o AppTest do Streamlit, sem navegador e sem rede."""

import re
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import select
from streamlit.testing.v1 import AppTest

from promessa.checker.service import check_content
from promessa.db.models import ContentPiece, RefundEvent, RegisteredPromise, TrackedLink
from promessa.db.session import get_engine, get_session, init_db, set_default_engine
from promessa.facts.seed import load_seed
from promessa.review.service import submit_review
from tests.test_reports import simulate

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
PAGES = [
    "painel.py",
    "pages/1_Ficha.py",
    "pages/2_Checador.py",
    "pages/3_Fila_de_revisao.py",
    "pages/4_Relatorios.py",
    "pages/5_Avaliacao.py",
]


@pytest.fixture(scope="module")
def engine():
    eng = get_engine("sqlite://")
    init_db(eng)
    with get_session(eng) as s:
        load_seed(s)
        simulate.run_simulation(s, mode="gabarito")
        s.commit()
    set_default_engine(eng)
    yield eng
    set_default_engine(None)
    eng.dispose()


def app(page: str, role: str = "creator") -> AppTest:
    at = AppTest.from_file(str(APP / page), default_timeout=30)
    at.session_state["_papel"] = role
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def all_text(at: AppTest) -> str:
    parts = []
    for kind in (
        "markdown",
        "info",
        "success",
        "warning",
        "error",
        "caption",
        "title",
        "subheader",
        "text",
    ):
        parts += [str(e.value) for e in getattr(at, kind)]
    parts += [f"{m.label} {m.value}" for m in at.metric]
    parts += [e.value.to_string() for e in at.dataframe]
    return "\n".join(parts)


# --- Abre sem erro -----------------------------------------------------------------------


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("role", ["marca", "creator", "operacoes"])
def test_paginas_abrem_sem_erro(engine, page, role):
    app(page, role)


def test_app_nao_importa_db_models():
    sources = "\n".join(p.read_text(encoding="utf-8") for p in APP.rglob("*.py"))
    assert not re.search(r"^\s*(from|import)\s+promessa\.db\.models", sources, re.M)
    grep = subprocess.run(
        ["git", "grep", "-n", "import promessa.db.models", "--", "app"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert grep.stdout == ""


# --- Exemplo do guia pela interface ------------------------------------------------------


def test_exemplo_do_guia_pela_interface(engine):
    ficha = app("pages/1_Ficha.py", "marca")
    ficha.selectbox(key="produto").set_value("prod_treino").run()
    assert "12 meses" in all_text(ficha) and "7 dias" in all_text(ficha)

    at = app("pages/2_Checador.py", "creator")
    at.selectbox(key="produto_checador").set_value("prod_treino").run()
    at.text_area(key="texto_peca").input("acesso vitalício e 30 dias para testar").run()
    at.button(key="checar").click().run()
    assert not at.exception
    blocked = at.session_state["checagem"]
    assert blocked["overall"] == "bloquear"
    assert "Link bloqueado" in all_text(at)
    assert "gerar_link" not in [b.key for b in at.button]  # sem link enquanto bloqueado

    at.text_area(key="texto_peca").input("12 meses de acesso, 7 dias de garantia").run()
    at.button(key="checar").click().run()
    fixed = at.session_state["checagem"]
    assert fixed["overall"] == "registrar" and fixed["can_generate_link"]
    at.button(key="gerar_link").click().run()
    assert not at.exception
    link = at.session_state["link"]
    assert link["url"].endswith(link["link_id"]) and "Link gerado" in all_text(at)
    assert {p["normalized_text"] for p in link["registered_promises"]} == {
        "acesso 12 meses",
        "garantia 7 dias",
    }
    with get_session(engine) as s:
        assert s.get(ContentPiece, fixed["piece_id"]).parent_piece_id == blocked["piece_id"]


def test_contestacao_pela_interface(engine):
    at = app("pages/2_Checador.py", "creator")
    at.selectbox(key="produto_checador").set_value("prod_treino").run()
    at.text_area(key="texto_peca").input("acesso vitalício").run()
    at.button(key="checar").click().run()
    finding = at.session_state["checagem"]["findings"][0]
    at.button(key=f"contestar_{finding['id']}").click().run()
    assert "Contestação enviada" in all_text(at)

    fila = app("pages/3_Fila_de_revisao.py", "marca")
    assert f"reverter_{finding['id']}" in [b.key for b in fila.button]
    fila.button(key=f"reverter_{finding['id']}").click().run()
    assert not fila.exception and "revertido" in all_text(fila)

    at.button(key="gerar_link").click().run()
    assert at.session_state["link"]["registered_promises"][0]["approval"] == "registrada"


# --- Visão creator: nenhum texto de comprador --------------------------------------------


def _windows(text: str, n: int = 5) -> set[str]:
    words = re.findall(r"\w+", text.lower())
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


@pytest.mark.parametrize("creator", ["cr_ana", "cr_bia", "cr_caio", "cr_duda", "cr_eli"])
def test_visao_creator_sem_texto_de_comprador(engine, creator):
    at = AppTest.from_file(str(APP / "pages/4_Relatorios.py"), default_timeout=30)
    at.session_state["_papel"] = "creator"
    at.session_state["_creator"] = creator
    at.run()
    assert not at.exception
    shown = all_text(at)
    assert "O que aconteceu com as suas vendas" in shown
    with get_session(engine) as s:
        buyer = set().union(*(_windows(r) for r in s.scalars(select(RefundEvent.reason_text))))
        pieces = s.scalars(
            select(ContentPiece.text).where(ContentPiece.creator_id == creator)
        ).all()
        promises = s.scalars(
            select(RegisteredPromise.normalized_text)
            .join(TrackedLink, TrackedLink.piece_id == RegisteredPromise.piece_id)
            .where(TrackedLink.creator_id == creator)
        ).all()
    own = set().union(*(_windows(t) for t in [*pieces, *promises]))
    assert not (buyer & _windows(shown)) - own


def test_tabela_do_creator_diz_quantas_pesam(engine):
    """Ana: parte das promessas explícitas contradiz a peça e não pesa (D30)."""
    at = AppTest.from_file(str(APP / "pages/4_Relatorios.py"), default_timeout=30)
    at.session_state["_papel"] = "creator"
    at.session_state["_creator"] = "cr_ana"
    at.run()
    assert not at.exception
    table = at.dataframe[0].value.set_index("causa")["pesa no creator"]
    assert re.fullmatch(r"\d+ de \d+", table["Promessa explícita"])
    assert (table.drop("Promessa explícita") == "não").all()


def test_relatorio_da_marca_mostra_sinal_vitalicio(engine):
    at = app("pages/4_Relatorios.py", "marca")
    at.selectbox(key="produto_relatorio").set_value("prod_treino").run()
    shown = all_text(at)
    assert "acesso vitalicio" in shown and "Sinais para a marca" in shown


def test_avaliacao_mostra_metas(engine):
    shown = all_text(app("pages/5_Avaliacao.py"))
    assert "Critério de corte" in shown and "kappa do indício" in shown


def test_checador_nao_e_da_marca(engine):
    assert "Esta página é do creator" in all_text(app("pages/2_Checador.py", "marca"))


def test_fila_nao_e_do_creator(engine):
    with get_session(engine) as s:
        resp = check_content(s, "prod_treino", "cr_bia", "acesso vitalício", "instagram")
        s.commit()
    with get_session(engine) as s:
        submit_review(s, "check_result", resp.findings[0].id, "contestar", "cr_bia", "creator")
        s.commit()
    fila = app("pages/3_Fila_de_revisao.py", "creator")
    assert "A fila é da marca e de Operações" in all_text(fila)
