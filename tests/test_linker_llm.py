"""Os 12 cenários da relação com classificador e linker de verdade (T11). `tasks.py test-llm`."""

import pytest

from promessa.config import get_settings, has_api_key
from promessa.refunds.classifier import classify_text
from promessa.refunds.linker import link, weighs_on_creator
from tests.test_linker import SCENARIOS, promise_objects

pytestmark = pytest.mark.llm


@pytest.fixture(autouse=True)
def _precisa_de_chave_ou_cache():
    settings = get_settings()
    if not (has_api_key(settings) or settings.llm_offline):
        pytest.skip("sem GEMINI_API_KEY e sem LLM_OFFLINE")


def run(sc):
    cls = classify_text(sc["motivo"], "infoproduto_outro")
    belief = cls.buyer_belief.model_dump() if cls.buyer_belief else None
    return cls, link(cls.cause, belief, sc["motivo"], promise_objects(sc["promessas"]))


def test_pelo_menos_11_de_12_cenarios():
    misses = []
    for sc in SCENARIOS:
        cls, result = run(sc)
        if result.relation.value != sc["relacao_esperada"]:
            misses.append(
                f"{sc['id']}: esperado {sc['relacao_esperada']}, veio {result.relation.value} "
                f"({cls.cause}/{cls.subcause}; {result.explanation})"
            )
    assert len(misses) <= 1, misses


def test_passo_4_do_guia():
    sc = next(s for s in SCENARIOS if s["id"] == "C03")
    cls, result = run(sc)
    assert (cls.cause, cls.subcause, result.relation.value) == (
        "promessa_explicita",
        "condicao_da_oferta",
        "contradiz",
    )
    assert not weighs_on_creator(cls.cause, result.relation, cls.confidence, "nao_aplicavel")


def test_resultado_em_revisao_confirma():
    sc = next(s for s in SCENARIOS if s["id"] == "C07")
    _, result = run(sc)
    assert result.relation.value == "confirma" and result.promise_id is not None
