"""Ligação devolução × promessa registrada (T11) sem rede."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from sqlalchemy import select

from promessa.db.enums import Approval, PromiseAttribute, PromiseType
from promessa.db.models import RefundClassification, RegisteredPromise
from promessa.db.session import get_session
from promessa.links.service import normalized_promise_text
from promessa.llm.client import LLMResult
from promessa.refunds.classifier import BuyerBelief, ClassifierLLMOutput
from promessa.refunds.linker import LinkerLLMOutput, link, weighs_on_creator
from promessa.refunds.service import classify_refund

SCENARIOS = yaml.safe_load(
    (Path(__file__).resolve().parents[1] / "data" / "seeds" / "cenarios_relacao.yaml").read_text(
        encoding="utf-8"
    )
)["cenarios"]


def promise_objects(specs):
    out = []
    for i, p in enumerate(specs, start=1):
        type_, attr = PromiseType(p["type"]), PromiseAttribute(p["attribute"])
        out.append(
            SimpleNamespace(
                id=100 + i,
                type=type_,
                attribute=attr,
                value=p["value"],
                unit=p.get("unit"),
                normalized_text=normalized_promise_text(type_, attr, p["value"], p.get("unit")),
                approval=Approval(p["approval"]),
            )
        )
    return out


def fake_linker(relation, promise_id):
    def completer(prompt_name, variables, output_model, model):
        assert prompt_name == "linker_v1" and output_model is LinkerLLMOutput
        assert variables["promessas"].startswith("- ")
        return LLMResult(
            LinkerLLMOutput(relation=relation, promise_id=promise_id, explanation="e"),
            model="modelo-simulado",
            prompt_version="linker_v1",
            cached=False,
        )

    return completer


def fake_classifier(cause, subcause, belief=None, confidence=0.9):
    def completer(prompt_name, variables, output_model, model):
        return LLMResult(
            ClassifierLLMOutput(
                cause=cause,
                subcause=subcause,
                buyer_belief=belief,
                channel_mentioned=None,
                confidence=confidence,
                explanation="e",
            ),
            model="modelo-simulado",
            prompt_version="classifier_v1",
            cached=False,
        )

    return completer


# --- Cenários ----------------------------------------------------------------------------


def test_doze_cenarios_cobrindo_as_relacoes():
    assert len(SCENARIOS) == 12
    assert {s["relacao_esperada"] for s in SCENARIOS} == {
        "confirma",
        "contradiz",
        "sem_relacao",
        "nao_aplicavel",
    }


@pytest.mark.parametrize("sc", [s for s in SCENARIOS if s["deterministico"]], ids=lambda s: s["id"])
def test_cenarios_deterministicos_sem_modelo(sc):
    c = sc["classificacao"]
    result = link(c["cause"], c.get("buyer_belief"), sc["motivo"], promise_objects(sc["promessas"]))
    assert result.relation.value == sc["relacao_esperada"], result.explanation
    assert result.method in ("regra", "nenhum")
    if result.relation.value in ("confirma", "contradiz"):
        assert result.promise_id is not None


@pytest.mark.parametrize(
    "sc", [s for s in SCENARIOS if not s["deterministico"]], ids=lambda s: s["id"]
)
def test_cenarios_de_resultado_usam_o_modelo(sc):
    c = sc["classificacao"]
    promises = promise_objects(sc["promessas"])
    result = link(
        c["cause"],
        c["buyer_belief"],
        sc["motivo"],
        promises,
        completer=fake_linker(sc["relacao_esperada"], promises[0].id),
    )
    assert (result.relation.value, result.method, result.promise_id) == (
        sc["relacao_esperada"],
        "modelo",
        promises[0].id,
    )


# --- Regras da ligação -------------------------------------------------------------------


def test_modelo_com_id_inventado_nao_liga_promessa():
    promises = promise_objects(
        [
            {
                "type": "resultado",
                "attribute": "resultado",
                "value": "5 kg em 7 dias",
                "approval": "em_revisao",
            }
        ]
    )
    belief = {"attribute": "resultado", "value": "5 kg", "text": "5 kg"}
    result = link(
        "promessa_explicita", belief, "m", promises, completer=fake_linker("confirma", 999)
    )
    assert (
        result.relation.value == "confirma" and result.promise_id is None
    )  # crença garante o invariante
    sem = link(
        "promessa_explicita",
        belief,
        "m",
        promises,
        completer=fake_linker("sem_relacao", promises[0].id),
    )
    assert sem.promise_id is None


def test_resultado_sem_modelo_fica_para_revisao():
    promises = promise_objects(
        [
            {
                "type": "resultado",
                "attribute": "resultado",
                "value": "5 kg em 7 dias",
                "approval": "em_revisao",
            }
        ]
    )
    result = link("promessa_explicita", {"attribute": "resultado", "value": "5 kg"}, "m", promises)
    assert (result.relation.value, result.method) == ("sem_relacao", "nenhum")


def test_sem_crenca_e_sem_relacao():
    promises = promise_objects(
        [
            {
                "type": "condicao_oferta",
                "attribute": "acesso",
                "value": "12",
                "unit": "meses",
                "approval": "registrada",
            }
        ]
    )
    assert link("promessa_explicita", None, "m", promises).relation.value == "sem_relacao"


@pytest.mark.parametrize(
    ("belief", "registered", "expected"),
    [
        ({"attribute": "acesso", "value": "1", "unit": "ano"}, ("12", "meses"), "confirma"),
        (
            {"attribute": "acesso", "value": "para sempre", "unit": None},
            ("vitalicio", None),
            "confirma",
        ),
        ({"attribute": "garantia", "value": "7 dias", "unit": None}, ("7", "dias"), "confirma"),
        ({"attribute": "garantia", "value": "15", "unit": "dias"}, ("7", "dias"), "contradiz"),
    ],
)
def test_normalizacao_das_condicoes(belief, registered, expected):
    attr = belief["attribute"]
    promises = promise_objects(
        [
            {
                "type": "condicao_oferta",
                "attribute": attr,
                "value": registered[0],
                "unit": registered[1],
                "approval": "registrada",
            }
        ]
    )
    assert link("promessa_explicita", belief, "m", promises).relation.value == expected


@pytest.mark.parametrize(
    ("cause", "relation", "conf", "status", "expected"),
    [
        ("promessa_explicita", "confirma", 0.9, "nao_aplicavel", True),
        ("promessa_explicita", "confirma", 0.7, "nao_aplicavel", False),  # confiança baixa
        ("promessa_explicita", "confirma", 0.9, "revertido", False),  # revertida
        ("promessa_explicita", "contradiz", 0.95, "nao_aplicavel", False),
        ("promessa_expectativa", "nao_aplicavel", 0.95, "nao_aplicavel", False),
        ("acesso_entrega", "nao_aplicavel", 0.95, "nao_aplicavel", False),
    ],
)
def test_o_que_pesa_no_creator(cause, relation, conf, status, expected):
    assert weighs_on_creator(cause, relation, conf, status, threshold=0.8) is expected


# --- Pelo serviço (com banco) ------------------------------------------------------------


@pytest.fixture
def s(seeded):
    with get_session(seeded) as session:
        yield session


def test_passo_4_do_guia_contradiz_e_nao_pesa(s, make_sale):
    sale = make_sale(s, text="12 meses de acesso, 7 dias de garantia")
    belief = BuyerBelief(
        attribute="acesso", value="vitalicio", unit=None, text="achei que era para sempre"
    )
    resp = classify_refund(
        s,
        sale.id,
        "perdi o acesso, achei que era para sempre",
        completer=fake_classifier("promessa_explicita", "condicao_da_oferta", belief),
    )
    assert (resp.cause, resp.subcause, resp.relation.value) == (
        "promessa_explicita",
        "condicao_da_oferta",
        "contradiz",
    )
    assert resp.linked_promise["normalized_text"] == "acesso 12 meses"
    assert resp.weighs_on_creator is False


def test_resultado_em_revisao_confirma(s, make_sale):
    sale = make_sale(s, text="Secar até 5KG EM 7 DIAS")
    belief = BuyerBelief(
        attribute="resultado", value="5 kg em 7 dias", unit=None, text="5 kg em uma semana"
    )
    promise = s.scalars(select(RegisteredPromise)).all()[-1]
    assert (promise.normalized_text, promise.approval.value) == ("5 kg em 7 dias", "em_revisao")
    resp = classify_refund(
        s,
        sale.id,
        "prometeram 5 kg em uma semana e não perdi nada",
        completer=fake_classifier("promessa_explicita", "resultado_prometido", belief),
        link_completer=fake_linker("confirma", promise.id),
    )
    assert (resp.relation.value, resp.linked_promise["id"]) == ("confirma", promise.id)
    assert resp.weighs_on_creator is True


def test_invariante_4(s, make_sale):
    cases = [
        (
            "12 meses de acesso",
            fake_classifier(
                "promessa_explicita",
                "condicao_da_oferta",
                BuyerBelief(attribute="acesso", value="12", unit="meses", text="12 meses"),
            ),
        ),
        (
            "12 meses de acesso",
            fake_classifier(
                "promessa_explicita",
                "condicao_da_oferta",
                BuyerBelief(attribute="acesso", value="vitalicio", unit=None, text="para sempre"),
            ),
        ),
        (
            "12 meses de acesso",
            fake_classifier("promessa_explicita", "diferente_do_anunciado", None),
        ),
        ("12 meses de acesso", fake_classifier("acesso_entrega", "acesso_nao_liberado", None)),
        (
            "Secar até 5KG EM 7 DIAS",
            fake_classifier(
                "promessa_explicita",
                "resultado_prometido",
                BuyerBelief(attribute="resultado", value="5 kg", unit=None, text="5 kg"),
            ),
        ),
    ]
    for text, classifier in cases:
        sale = make_sale(s, text=text)
        classify_refund(
            s, sale.id, "motivo", completer=classifier, link_completer=fake_linker("confirma", None)
        )
    rows = s.scalars(select(RefundClassification)).all()
    assert {r.relation.value for r in rows} >= {
        "confirma",
        "contradiz",
        "sem_relacao",
        "nao_aplicavel",
    }
    for r in rows:
        if r.relation.value in ("confirma", "contradiz"):
            assert r.linked_promise_id is not None or r.buyer_belief, r.id
