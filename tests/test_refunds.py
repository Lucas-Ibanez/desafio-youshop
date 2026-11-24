"""Classificador de devolução e classify_refund (T10) sem rede."""

import json

import pytest
from sqlalchemy import select

from promessa.db.models import RefundClassification, RefundEvent
from promessa.db.session import get_session
from promessa.errors import DomainError
from promessa.llm.client import LLMError, LLMResult
from promessa.refunds.classifier import (
    GOLD,
    BuyerBelief,
    ClassifierLLMOutput,
    classify_text,
    prompt_examples,
    prompt_variables,
)
from promessa.refunds.service import classify_refund
from tests.mcp_helpers import ToolCallError, call_tool


@pytest.fixture
def s(seeded):
    with get_session(seeded) as session:
        yield session


def fake_model(cause, subcause, confidence=0.9, belief=None, channel=None):
    seen = {}

    def completer(prompt_name, variables, output_model, model):
        assert prompt_name == "classifier_v1" and output_model is ClassifierLLMOutput
        seen.update(variables)
        return LLMResult(
            ClassifierLLMOutput(
                cause=cause,
                subcause=subcause,
                buyer_belief=belief,
                channel_mentioned=channel,
                confidence=confidence,
                explanation="explicação do modelo",
            ),
            model="modelo-simulado",
            prompt_version="classifier_v1",
            cached=False,
        )

    completer.seen = seen
    return completer


# --- Exemplos do prompt ------------------------------------------------------------------


def test_exemplos_do_prompt_so_do_split_dev():
    splits = json.loads((GOLD / "splits.json").read_text(encoding="utf-8"))
    ids = [r["id"] for r in prompt_examples()]
    assert 0 < len(ids) <= 8
    assert set(ids) <= set(splits["h1"]["dev"])
    assert not set(ids) & set(splits["h1"]["test"])


def test_exemplos_balanceados_por_causa():
    causes = [r["causa"] for r in prompt_examples()]
    assert set(causes) == {
        "promessa_explicita",
        "promessa_expectativa",
        "acesso_entrega",
        "processo",
        "fraude",
    }
    assert max(causes.count(c) for c in set(causes)) <= 2


def test_prompt_tem_taxonomia_precedencia_e_fronteira():
    v = prompt_variables("motivo", "infoproduto_outro")
    assert (
        "condicao_da_oferta" in v["taxonomia"] and "fraude > promessa_explicita" in v["precedencia"]
    )
    assert "Perdi o acesso, achei que era para sempre" in v["fronteira"]
    assert v["exemplos"].count("\n") == len(prompt_examples()) - 1


# --- Validação da subcausa ---------------------------------------------------------------


def test_subcausa_invalida_e_corrigida_e_confianca_cai():
    result = classify_text("texto", completer=fake_model("processo", "golpe", confidence=0.95))
    assert (result.cause, result.subcause, result.corrected) == (
        "processo",
        "arrependimento_sem_motivo",
        True,
    )
    assert result.confidence <= 0.5


def test_causa_invalida_vira_outros():
    result = classify_text(
        "texto", completer=fake_model("reclamacao_generica", "x", confidence=0.9)
    )
    assert (result.cause, result.subcause, result.main_cause) == ("outros", "outros", "outros")
    assert result.confidence <= 0.5


def test_par_valido_mantem_confianca_e_crenca():
    belief = BuyerBelief(
        attribute="acesso", value="vitalicio", unit=None, text="achei que era para sempre"
    )
    result = classify_text(
        "perdi o acesso",
        completer=fake_model("promessa_explicita", "condicao_da_oferta", 0.92, belief),
    )
    assert (result.main_cause, result.confidence, result.corrected) == ("promessa", 0.92, False)
    assert result.buyer_belief.value == "vitalicio" and result.model == "modelo-simulado"


def test_texto_vai_limpo_para_o_modelo():
    model = fake_model("fraude", "cobranca_nao_reconhecida")
    classify_text("não reconheço, meu cpf 123.456.789-00 e email ana@x.com", completer=model)
    assert "123.456.789-00" not in model.seen["motivo"] and "[CPF]" in model.seen["motivo"]


def test_sem_modelo_vai_para_revisao():
    result = classify_text("texto qualquer")  # testes padrão: sem chave
    assert (result.cause, result.confidence, result.source) == ("outros", 0.0, "sem_modelo")


def test_modelo_com_erro_vai_para_revisao():
    def broken(*args, **kwargs):
        raise LLMError("503")

    result = classify_text("texto", completer=broken)
    assert result.source == "sem_modelo" and "não respondeu" in result.explanation


# --- classify_refund ---------------------------------------------------------------------


def test_grava_evento_limpo_e_classificacao(s, make_sale):
    sale = make_sale(s)
    resp = classify_refund(
        s,
        sale.id,
        "Perdi o acesso, achei que era para sempre. Meu email: ana@x.com",
        completer=fake_model(
            "promessa_explicita",
            "condicao_da_oferta",
            0.9,
            BuyerBelief(attribute="acesso", value="vitalicio", unit=None, text="para sempre"),
        ),
    )
    event = s.get(RefundEvent, resp.refund_id)
    assert "ana@x.com" not in event.reason_text and "[EMAIL]" in event.reason_text
    row = s.get(RefundClassification, resp.classification_id)
    assert (row.cause, row.subcause, row.relation.value) == (
        "promessa_explicita",
        "condicao_da_oferta",
        "contradiz",  # T11: registrado "acesso 12 meses", comprador acha que era vitalício
    )
    assert row.buyer_belief["value"] == "vitalicio" and row.prompt_version == "classifier_v1"
    assert (resp.needs_review, resp.main_cause, resp.weighs_on_creator) == (
        False,
        "promessa",
        False,
    )
    assert resp.linked_promise["normalized_text"] == "acesso 12 meses"
    assert row.linked_promise_id == resp.linked_promise["id"]


def test_confianca_baixa_entra_na_fila(s, make_sale):
    from promessa.review.service import list_review_queue

    sale = make_sale(s)
    resp = classify_refund(s, sale.id, "não sei", completer=fake_model("outros", "outros", 0.4))
    assert resp.needs_review is True
    assert [i.target_id for i in list_review_queue(s, "classificacao").items] == [
        str(resp.classification_id)
    ]


def test_sem_modelo_grava_outros_para_revisao(s, make_sale):
    sale = make_sale(s)
    resp = classify_refund(s, sale.id, "Me arrependi, quero cancelar")
    assert (resp.cause, resp.needs_review) == ("outros", True)
    assert resp.notes and "revisão humana" in resp.notes[0]


@pytest.mark.parametrize(
    ("sale_id", "reason", "type_", "code"),
    [
        (999, "motivo", "reembolso", "VENDA_INEXISTENTE"),
        (None, "motivo", "estorno", "ENTRADA_INVALIDA"),
        (None, "   ", "reembolso", "ENTRADA_INVALIDA"),
    ],
)
def test_erros(s, make_sale, sale_id, reason, type_, code):
    sale_id = sale_id or make_sale(s).id
    with pytest.raises(DomainError) as exc:
        classify_refund(s, sale_id, reason, type_)
    assert exc.value.code == code


def test_classify_refund_pelo_mcp(mcp_db, make_sale):
    with get_session(mcp_db) as session:
        sale_id = make_sale(session).id
        session.commit()
    resp = call_tool(
        "classify_refund",
        {"sale_id": sale_id, "reason_text": "meu cpf 123.456.789-00", "type": "chargeback"},
    )
    assert resp["relation"] == "nao_aplicavel" and resp["needs_review"] is True
    with get_session(mcp_db) as session:
        event = session.scalars(select(RefundEvent)).one()
        assert event.reason_text == "meu cpf [CPF]" and event.type.value == "chargeback"
    with pytest.raises(ToolCallError, match="VENDA_INEXISTENTE"):
        call_tool("classify_refund", {"sale_id": 999, "reason_text": "x"})
