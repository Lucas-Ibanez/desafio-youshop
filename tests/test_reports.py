"""Simulador, relatórios e explicação ao creator (T13), sem rede (simulação no modo gabarito)."""

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest
from sqlalchemy import select

from promessa.db.models import ContentPiece, RefundEvent, RegisteredPromise
from promessa.db.session import get_engine, get_session, init_db, set_default_engine
from promessa.errors import DomainError
from promessa.facts.seed import load_seed
from promessa.llm.client import LLMResult
from promessa.reports.explain import ExplainerLLMOutput, explain_refunds_to_creator
from promessa.reports.service import promise_outcome_report
from tests.mcp_helpers import ToolCallError, call_tool

ROOT = Path(__file__).resolve().parent.parent
CREATORS = ["cr_ana", "cr_bia", "cr_caio", "cr_duda", "cr_eli"]


def _load_simulate():
    spec = importlib.util.spec_from_file_location("simulate", ROOT / "scripts" / "simulate.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["simulate"] = module
    spec.loader.exec_module(module)
    return module


simulate = _load_simulate()


@pytest.fixture(scope="module")
def sim():
    engine = get_engine("sqlite://")
    init_db(engine)
    with get_session(engine) as s:
        load_seed(s)
        summary = simulate.run_simulation(s, mode="gabarito")
        s.commit()
    yield engine, summary
    engine.dispose()


@pytest.fixture
def s(sim):
    with get_session(sim[0]) as session:
        yield session


def reports(s):
    return {c: promise_outcome_report(s, creator_id=c) for c in CREATORS}


# --- Simulação ---------------------------------------------------------------------------


def test_resumo_da_simulacao(sim):
    summary = sim[1]
    assert summary["vendas"] == 600
    assert 0.10 <= summary["devolucoes"] / 600 <= 0.14
    share = {k: v / summary["devolucoes"] for k, v in summary["por_causa"].items()}
    assert 0.28 <= share["acesso_entrega"] <= 0.42 and 0.24 <= share["processo"] <= 0.38
    assert 0.20 <= share["promessa_explicita"] + share.get("promessa_expectativa", 0) <= 0.34
    assert share["fraude"] <= 0.10


def test_simulacao_nao_roda_duas_vezes(s):
    with pytest.raises(SystemExit, match="db-reset"):
        simulate.run_simulation(s, mode="gabarito")


# --- Personas (critérios do PLANO) -------------------------------------------------------


def test_ana_tem_o_maior_indicador_e_5kg_no_topo(s):
    r = reports(s)
    rates = {c: r[c].indicador_creator.taxa_promessa_confirmada or 0 for c in CREATORS}
    assert max(rates, key=rates.get) == "cr_ana" and rates["cr_ana"] > 0
    assert r["cr_ana"].promessas_mais_contestadas[0].promessa == "5 kg em 7 dias"
    assert r["cr_ana"].promessas_mais_contestadas[0].trecho == "Secar até 5KG EM 7 DIAS"


def test_prod_treino_sinal_vitalicio_para_a_marca(s):
    report = promise_outcome_report(s, product_id="prod_treino")
    assert report.sinais_para_a_marca[0].crenca == "acesso vitalicio"
    assert set(report.sinais_para_a_marca[0].creators) == {"cr_ana", "cr_bia"}
    assert {row.creator_id for row in report.por_creator} == {"cr_ana", "cr_bia"}


def test_caio_devolve_muito_mas_nao_e_promessa(s):
    r = reports(s)
    refund_rate = sorted(CREATORS, key=lambda c: -r[c].taxa_devolucao)
    assert refund_rate.index("cr_caio") <= 1
    indicator = {
        c: r[c].indicador_creator.taxa_promessa_confirmada for c in CREATORS if c != "cr_duda"
    }
    assert indicator["cr_caio"] == min(indicator.values())


def test_duda_dados_insuficientes(s):
    ind = promise_outcome_report(s, creator_id="cr_duda").indicador_creator
    assert ind.status == "dados_insuficientes" and ind.taxa_promessa_confirmada is None
    assert "Dados insuficientes" in ind.texto


def test_cobertura_operacao_e_integridade(s):
    report = promise_outcome_report(s, product_id="prod_treino")
    assert report.cobertura["vendas_com_promessa_registrada"] == 1.0
    assert report.cobertura["devolucoes_classificadas"] == 1.0
    assert 0 < report.cobertura["devolucoes_ligadas_a_promessa"] < 1
    assert report.integridade["condicoes_contrarias_barradas"] == 2  # vitalício + 30 dias (cr_ana)
    assert report.operacao["horas_medias_ate_classificar"] is not None


# --- Explicação ao creator ---------------------------------------------------------------


def test_explicacao_da_ana(s):
    e = explain_refunds_to_creator(s, "cr_ana")
    assert e.source == "modelo_de_texto"  # testes padrão: sem chave
    assert '"Secar até 5KG EM 7 DIAS"' in e.text
    assert "não têm a ver com você" in e.text
    assert len(e.text.split()) <= 120
    assert e.data_used["promessa_da_peca_cobrada"] == 7


def test_explicacao_da_bia_e_da_duda(s):
    assert (
        "Nenhuma devolução veio de promessa da sua peça"
        in explain_refunds_to_creator(s, "cr_bia").text
    )
    duda = explain_refunds_to_creator(s, "cr_duda").text
    assert "poucas vendas" in duda and "#publi" in duda  # peça da duda não tem #publi


def _fake_explainer(text):
    def completer(prompt_name, variables, output_model, model):
        assert prompt_name == "explainer_v1" and "Secar até" in variables["dados"]
        return LLMResult(
            ExplainerLLMOutput(text=text), model="m", prompt_version="explainer_v1", cached=False
        )

    return completer


def test_explicacao_do_modelo_aceita_ou_cai_para_o_texto_fixo(s):
    good = (
        'Suas vendas voltaram por causa do trecho "Secar até 5KG EM 7 DIAS". '
        "O resto não é com você."
    )
    assert (
        explain_refunds_to_creator(s, "cr_ana", completer=_fake_explainer(good)).source == "modelo"
    )
    no_excerpt = "Suas vendas voltaram por vários motivos."
    assert (
        explain_refunds_to_creator(s, "cr_ana", completer=_fake_explainer(no_excerpt)).source
        == "modelo_de_texto"
    )
    too_long = good + " palavra" * 150
    assert (
        explain_refunds_to_creator(s, "cr_ana", completer=_fake_explainer(too_long)).source
        == "modelo_de_texto"
    )


# --- Invariante 5: o creator nunca vê o comprador ----------------------------------------


def _windows(text: str, n: int = 5) -> set[str]:
    words = re.findall(r"\w+", text.lower())
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


def test_invariante_5_nada_do_comprador_para_o_creator(s):
    """Nenhuma sequência de 5 palavras do motivo do comprador aparece no que o creator vê.

    Descontam-se as sequências que estão na própria peça do creator (o comprador pode citar a
    promessa da peça, como "5 kg em 7 dias"; isso não é dado do comprador).
    """
    reasons = s.scalars(select(RefundEvent.reason_text)).all()
    assert len(reasons) == 76
    buyer = set().union(*(_windows(r) for r in reasons))
    for c in CREATORS:
        own_texts = s.scalars(select(ContentPiece.text).where(ContentPiece.creator_id == c)).all()
        own_promises = s.scalars(
            select(RegisteredPromise.normalized_text)
            .join(ContentPiece, RegisteredPromise.piece_id == ContentPiece.id)
            .where(ContentPiece.creator_id == c)
        ).all()
        own = set().union(*(_windows(x) for x in [*own_texts, *own_promises]))
        outputs = [
            explain_refunds_to_creator(s, c).text,
            json.dumps(
                promise_outcome_report(s, creator_id=c).model_dump(mode="json"), ensure_ascii=False
            ),
        ]
        for out in outputs:
            leaked = (buyer & _windows(out)) - own
            assert not leaked, (c, sorted(leaked)[:3])


# --- Entrada e MCP -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"creator_id": "cr_ana", "start": "2026-11-22", "end": "2026-10-26"}, "PERIODO_INVALIDO"),
        ({"creator_id": "cr_ana", "start": "ontem", "end": "2026-10-26"}, "PERIODO_INVALIDO"),
        ({"creator_id": "cr_ana", "product_id": "prod_treino"}, "ENTRADA_INVALIDA"),
        ({}, "ENTRADA_INVALIDA"),
        ({"creator_id": "cr_x"}, "CREATOR_INEXISTENTE"),
    ],
)
def test_erros_do_relatorio(s, kwargs, code):
    with pytest.raises(DomainError) as exc:
        promise_outcome_report(s, **kwargs)
    assert exc.value.code == code


def test_periodo_filtra_pela_data_da_venda(s):
    first_week = promise_outcome_report(
        s, creator_id="cr_caio", start="2026-10-26", end="2026-11-01"
    )
    full = promise_outcome_report(s, creator_id="cr_caio")
    assert 0 < first_week.vendas < full.vendas == 200


def test_ferramentas_pelo_mcp(sim):
    set_default_engine(sim[0])
    try:
        report = call_tool("get_promise_outcome_report", {"product_id": "prod_treino"})
        assert report["sinais_para_a_marca"][0]["crenca"] == "acesso vitalicio"
        explanation = call_tool("explain_refunds_to_creator", {"creator_id": "cr_ana"})
        assert "Secar até 5KG EM 7 DIAS" in explanation["text"]
        with pytest.raises(ToolCallError, match="PERIODO_INVALIDO"):
            call_tool(
                "get_promise_outcome_report", {"creator_id": "cr_ana", "start": "x", "end": "y"}
            )
    finally:
        set_default_engine(None)
