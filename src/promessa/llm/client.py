"""Cliente do modelo (Gemini) com saída estruturada, novas tentativas, cache e log (T07, D14).

`complete_json(prompt_name, variables, output_model, model)`:
- monta o texto a partir de `prompts/<prompt_name>.md`, trocando `{{variavel}}`;
- pede JSON no esquema do `output_model` (Pydantic) e valida a resposta com ele;
- temperatura 0; até 3 tentativas com espera crescente em rede, 429 e 5xx;
- cache em disco; com `LLM_OFFLINE=true`, só cache (erro claro se faltar);
- uma linha de log por chamada: modelo, versão do prompt, tokens, tempo, cache.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from promessa.config import Settings, get_settings, has_api_key
from promessa.llm.cache import DiskCache, cache_key

log = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
RETRY_CODES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3
MAX_RETRY_WAIT = 60.0  # segundos


class LLMError(Exception):
    """Falha ao obter resposta válida do modelo (a camada que chama decide o que fazer)."""


class LLMUnavailable(LLMError):
    """Sem chave da API ou modelo desligado."""


class LLMQuotaExhausted(LLMError):
    """A API pediu para esperar mais que `MAX_RETRY_WAIT` (ex.: cota diária): não repetir."""


class LLMOfflineMiss(LLMError):
    """`LLM_OFFLINE=true` e a resposta não está no cache."""


@dataclass
class LLMResult[T: BaseModel]:
    data: T
    model: str
    prompt_version: str
    cached: bool
    usage: dict[str, Any] = field(default_factory=dict)


def render_prompt(prompt_name: str, variables: dict[str, Any]) -> str:
    """Lê `prompts/<prompt_name>.md` e troca cada `{{nome}}` pelo valor."""
    path = PROMPTS_DIR / f"{prompt_name}.md"
    template = path.read_text(encoding="utf-8")
    missing = set(re.findall(r"\{\{(\w+)\}\}", template)) - set(variables)
    if missing:
        raise LLMError(f"variáveis faltando no prompt {prompt_name}: {sorted(missing)}")
    return re.sub(r"\{\{(\w+)\}\}", lambda m: str(variables[m.group(1)]), template)


_client = None


def _genai_client(settings: Settings):
    global _client
    if _client is None:
        from google import genai

        _client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
    return _client


def _call_gemini(model: str, rendered: str, output_model: type[BaseModel], settings: Settings):
    from google.genai import types

    response = _genai_client(settings).models.generate_content(
        model=model,
        contents=rendered,
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_schema=output_model,
        ),
    )
    usage = response.usage_metadata
    tokens = {
        "prompt": getattr(usage, "prompt_token_count", None),
        "output": getattr(usage, "candidates_token_count", None),
        "thoughts": getattr(usage, "thoughts_token_count", None),
    }
    return response.text or "", tokens


class RateLimiter:
    """Espaça o início das chamadas para não passar de `rpm` por minuto (entre threads)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self, rpm: int, clock=time.monotonic, sleep=time.sleep) -> None:
        if rpm <= 0:
            return
        with self._lock:
            now = clock()
            start = max(now, self._next)
            self._next = start + 60.0 / rpm
        if start > now:
            sleep(start - now)


_limiter = RateLimiter()


def retry_after(exc: Exception) -> float | None:
    """Segundos que a API pede para esperar ("Please retry in 19.7s" / retryDelay: '19s')."""
    m = re.search(r"retry in ([\d.]+)\s*s|retryDelay'?:\s*'?([\d.]+)s", str(exc))
    if not m:
        return None
    return float(m.group(1) or m.group(2))


def _short(exc: Exception, limit: int = 160) -> str:
    text = " ".join(str(exc).split())
    return text if len(text) <= limit else text[:limit] + "…"


def _is_retryable(exc: Exception) -> bool:
    code = getattr(exc, "code", None)
    if isinstance(code, int) and code in RETRY_CODES:
        return True
    try:
        import httpx

        return isinstance(exc, httpx.TransportError)
    except ImportError:  # pragma: no cover
        return False


def complete_json[T: BaseModel](
    prompt_name: str,
    variables: dict[str, Any],
    output_model: type[T],
    model: str,
    *,
    settings: Settings | None = None,
    sleep=time.sleep,
) -> LLMResult[T]:
    settings = settings or get_settings()
    rendered = render_prompt(prompt_name, variables)
    key = cache_key(model, prompt_name, rendered)
    cache = DiskCache(settings.llm_cache_dir)

    hit = cache.get(key)
    if hit is not None:
        data = output_model.model_validate(hit["response"])
        log.info("llm model=%s prompt=%s cache=hit", model, prompt_name)
        return LLMResult(data, model, prompt_name, cached=True, usage=hit.get("usage", {}))
    if settings.llm_offline:
        raise LLMOfflineMiss(
            f"LLM_OFFLINE=true e não há cache para {prompt_name} com {model} (chave {key[:12]})."
        )
    if not has_api_key(settings):
        raise LLMUnavailable("GEMINI_API_KEY vazia: a camada do modelo está desligada.")

    last: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        _limiter.wait(settings.llm_max_rpm, sleep=sleep)
        started = time.perf_counter()
        wait = 2 ** (attempt - 1)
        try:
            text, tokens = _call_gemini(model, rendered, output_model, settings)
            data = output_model.model_validate_json(text)
        except ValidationError as e:  # JSON fora do esquema: tenta de novo
            last = e
            log.warning(
                "llm model=%s prompt=%s tentativa=%d resposta inválida", model, prompt_name, attempt
            )
        except Exception as e:  # noqa: BLE001
            if not _is_retryable(e):
                raise LLMError(f"erro do modelo {model}: {_short(e)}") from e
            last = e
            asked = retry_after(e) or 0
            if asked > MAX_RETRY_WAIT:
                raise LLMQuotaExhausted(
                    f"cota do modelo {model} esgotada: a API pede esperar {asked / 3600:.1f} h"
                ) from e
            wait = max(wait, asked)
            log.warning(
                "llm model=%s prompt=%s tentativa=%d erro=%s",
                model,
                prompt_name,
                attempt,
                _short(e),
            )
        else:
            elapsed = int((time.perf_counter() - started) * 1000)
            log.info(
                "llm model=%s prompt=%s tokens=%s ms=%d cache=miss",
                model,
                prompt_name,
                tokens,
                elapsed,
            )
            cache.set(
                key,
                {
                    "model": model,
                    "prompt_version": prompt_name,
                    "response": data.model_dump(mode="json"),
                    "usage": tokens,
                },
            )
            return LLMResult(data, model, prompt_name, cached=False, usage=tokens)
        if attempt < MAX_ATTEMPTS:
            sleep(wait)
    raise LLMError(
        f"modelo {model} sem resposta válida após {MAX_ATTEMPTS} tentativas: {_short(last)}"
    )
