"""Classificador de devolução com o modelo de verdade (T10). Rodam com `tasks.py test-llm`."""

import pytest

from promessa.config import get_settings, has_api_key
from promessa.refunds.classifier import classify_text

pytestmark = pytest.mark.llm

CASES = [
    ("Não reconheço essa cobrança no meu cartão", "fraude", "cobranca_nao_reconhecida", None),
    (
        "Paguei há 5 dias e até hoje não liberaram o acesso",
        "acesso_entrega",
        "acesso_nao_liberado",
        None,
    ),
    ("Me arrependi, quero cancelar", "processo", "arrependimento_sem_motivo", None),
    (
        "Anunciaram garantia de 30 dias, mas só aceitam pedido em 7",
        "promessa_explicita",
        "condicao_da_oferta",
        ("garantia", "30"),
    ),
    ("O curso é fraco, esperava mais", "promessa_expectativa", "qualidade_abaixo", None),
    (
        "Perdi o acesso, achei que era para sempre",
        "promessa_explicita",
        "condicao_da_oferta",
        ("acesso", "vitalicio"),
    ),
    (
        "Cobraram renovação que ninguém me avisou na compra",
        "promessa_explicita",
        "informacao_omitida",
        None,
    ),
]


@pytest.fixture(autouse=True)
def _precisa_de_chave_ou_cache():
    settings = get_settings()
    if not (has_api_key(settings) or settings.llm_offline):
        pytest.skip("sem GEMINI_API_KEY e sem LLM_OFFLINE")


@pytest.mark.parametrize(
    ("text", "cause", "subcause", "belief"), CASES, ids=[c[0][:30] for c in CASES]
)
def test_classificacao(text, cause, subcause, belief):
    result = classify_text(text, "infoproduto_outro")
    assert result.source == "modelo", result.explanation
    assert (result.cause, result.subcause) == (cause, subcause), result.explanation
    if belief:
        assert result.buyer_belief is not None
        assert (result.buyer_belief.attribute, result.buyer_belief.value) == belief
