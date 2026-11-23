"""Cliente do modelo (T07) sem rede: cache, modo offline, novas tentativas e validação."""

import pytest
from pydantic import BaseModel

from promessa.config import Settings
from promessa.llm import client as llm
from promessa.llm.client import LLMError, LLMOfflineMiss, LLMUnavailable, complete_json


class Out(BaseModel):
    ok: bool


class ApiError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(f"{code} erro simulado")


@pytest.fixture
def prompt(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "PROMPTS_DIR", tmp_path)
    (tmp_path / "teste_v1.md").write_text("Diga ok para {{coisa}}.", encoding="utf-8")
    return "teste_v1"


def settings(tmp_path, **kw):
    return Settings(
        _env_file=None, gemini_api_key="chave-falsa", llm_cache_dir=str(tmp_path / "cache"), **kw
    )


def fake_calls(monkeypatch, responses):
    calls = []

    def fake(model, rendered, output_model, s):
        calls.append(rendered)
        item = responses[len(calls) - 1]
        if isinstance(item, Exception):
            raise item
        return item, {"prompt": 10, "output": 2, "thoughts": None}

    monkeypatch.setattr(llm, "_call_gemini", fake)
    return calls


def test_render_troca_variaveis_e_acusa_faltantes(prompt):
    assert llm.render_prompt(prompt, {"coisa": "isto"}) == "Diga ok para isto."
    with pytest.raises(LLMError, match="coisa"):
        llm.render_prompt(prompt, {})


def test_segunda_chamada_vem_do_cache(prompt, tmp_path, monkeypatch):
    calls = fake_calls(monkeypatch, ['{"ok": true}'])
    s = settings(tmp_path)
    first = complete_json(prompt, {"coisa": "a"}, Out, "modelo-x", settings=s)
    second = complete_json(prompt, {"coisa": "a"}, Out, "modelo-x", settings=s)
    assert (first.cached, second.cached) == (False, True)
    assert second.data == Out(ok=True) and second.prompt_version == "teste_v1"
    assert len(calls) == 1


def test_cache_separa_modelo_e_entrada(prompt, tmp_path, monkeypatch):
    calls = fake_calls(monkeypatch, ['{"ok": true}'] * 3)
    s = settings(tmp_path)
    complete_json(prompt, {"coisa": "a"}, Out, "modelo-x", settings=s)
    complete_json(prompt, {"coisa": "b"}, Out, "modelo-x", settings=s)
    complete_json(prompt, {"coisa": "a"}, Out, "modelo-y", settings=s)
    assert len(calls) == 3


def test_offline_sem_cache_da_erro_claro(prompt, tmp_path, monkeypatch):
    calls = fake_calls(monkeypatch, [])
    with pytest.raises(LLMOfflineMiss, match="LLM_OFFLINE"):
        complete_json(
            prompt, {"coisa": "a"}, Out, "m", settings=settings(tmp_path, llm_offline=True)
        )
    assert calls == []


def test_sem_chave(prompt, tmp_path):
    s = Settings(_env_file=None, gemini_api_key="", llm_cache_dir=str(tmp_path))
    with pytest.raises(LLMUnavailable):
        complete_json(prompt, {"coisa": "a"}, Out, "m", settings=s)


def test_tenta_de_novo_em_503_e_429(prompt, tmp_path, monkeypatch):
    calls = fake_calls(monkeypatch, [ApiError(503), ApiError(429), '{"ok": false}'])
    waits = []
    result = complete_json(
        prompt, {"coisa": "a"}, Out, "m", settings=settings(tmp_path), sleep=waits.append
    )
    assert result.data == Out(ok=False) and len(calls) == 3
    assert waits == [1, 2]  # espera crescente


def test_desiste_depois_de_3_tentativas(prompt, tmp_path, monkeypatch):
    fake_calls(monkeypatch, [ApiError(503)] * 3)
    with pytest.raises(LLMError, match="3 tentativas"):
        complete_json(
            prompt, {"coisa": "a"}, Out, "m", settings=settings(tmp_path), sleep=lambda _: None
        )


def test_erro_nao_transitorio_nao_repete(prompt, tmp_path, monkeypatch):
    calls = fake_calls(monkeypatch, [ApiError(400)])
    with pytest.raises(LLMError, match="400"):
        complete_json(
            prompt, {"coisa": "a"}, Out, "m", settings=settings(tmp_path), sleep=lambda _: None
        )
    assert len(calls) == 1


def test_json_fora_do_esquema_tenta_de_novo(prompt, tmp_path, monkeypatch):
    calls = fake_calls(monkeypatch, ['{"nada": 1}', '{"ok": true}'])
    result = complete_json(
        prompt, {"coisa": "a"}, Out, "m", settings=settings(tmp_path), sleep=lambda _: None
    )
    assert result.data.ok is True and len(calls) == 2
