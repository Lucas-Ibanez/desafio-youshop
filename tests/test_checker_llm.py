"""Checador com o modelo de verdade (T07). Rodam só com `tasks.py test-llm`.

Usam a chave do .env e o cache em disco (`LLM_CACHE_DIR`). A segunda rodada com
`LLM_OFFLINE=true` precisa passar só com o cache.
"""

import pytest

from promessa.checker.service import check_content
from promessa.config import get_settings, has_api_key
from promessa.db.session import get_session
from tests.test_checker_deterministic import CASES

pytestmark = pytest.mark.llm

SEVERITY = {"limpo": 0, "registrar": 1, "revisar": 2, "bloquear": 3}


@pytest.fixture(autouse=True)
def _precisa_de_chave_ou_cache():
    settings = get_settings()
    if not (has_api_key(settings) or settings.llm_offline):
        pytest.skip("sem GEMINI_API_KEY e sem LLM_OFFLINE")
    if not settings.checker_use_llm:
        pytest.skip("CHECKER_USE_LLM=false")


@pytest.fixture
def s(seeded):
    with get_session(seeded) as session:
        yield session


def check(s, text, product, since=None):
    resp = check_content(s, product, "cr_ana", text, "instagram", published_since=since)
    assert resp.layers_used == ["regras", "modelo"], resp.notes
    return resp


def test_comparacao_implicita_com_medicamento(s):
    resp = check(s, "esse chá dispensa a caneta da farmácia", "prod_treino")
    med = [f for f in resp.findings if f.reason_type in ("med_comparacao",)]
    assert med and all(f.output.value == "revisar" for f in med)


def test_alegacao_fora_da_lista_permitida(s):
    resp = check(s, "acorda o seu metabolismo", "prod_magnesio")
    assert resp.overall == "revisar", [(f.output, f.reason_type, f.excerpt) for f in resp.findings]
    model = [f for f in resp.findings if f.source.value == "modelo"]
    assert model and model[0].model == get_settings().checker_model
    assert model[0].prompt_version == "checker_v1"


@pytest.mark.parametrize(
    ("text", "product", "since", "required", "forbidden"), CASES, ids=[c[0][:30] for c in CASES]
)
def test_casos_da_t06_mesma_saida_ou_mais_grave(s, text, product, since, required, forbidden):
    rules_only = check_content(
        s, product, "cr_ana", text, "instagram", published_since=since, use_llm=False
    )
    with_model = check(s, text, product, since)
    assert SEVERITY[with_model.overall] >= SEVERITY[rules_only.overall]
    layer1 = {(f.output.value, f.rule_key) for f in rules_only.findings}
    assert layer1 <= {(f.output.value, f.rule_key) for f in with_model.findings}
