"""Padrões da seção 17.1 do CONTEXTO, sem .env e sem variáveis de ambiente."""

from promessa.config import Settings, has_api_key


def test_padroes_sem_env(monkeypatch, tmp_path):
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
    monkeypatch.chdir(tmp_path)  # nenhum .env neste diretório

    s = Settings(_env_file=None)

    assert s.gemini_api_key.get_secret_value() == ""
    assert not has_api_key(s)
    assert s.promessa_db_url == "sqlite:///var/promessa.db"
    assert s.checker_model == "gemini-3.6-flash"
    assert s.classifier_model == "gemini-3.5-flash-lite"
    assert s.explainer_model == "gemini-3.5-flash-lite"
    assert s.checker_use_llm is True
    assert s.llm_offline is False
    assert s.llm_cache_dir == ".cache/llm"
    assert s.confidence_threshold == 0.8
    assert s.min_sales_for_indicator == 30
    assert s.urgency_stale_days == 7
    assert s.link_base_url == "https://youshop.example/l/"


def test_env_sobrescreve(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CHECKER_USE_LLM", "false")
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0.9")

    s = Settings(_env_file=None)

    assert s.checker_use_llm is False
    assert s.confidence_threshold == 0.9
