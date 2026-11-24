"""Classificador do motivo de devolução (Agente 2; CONTEXTO 12.1 e 12.2). Sem banco.

`classify_text(text, product_category)` limpa o texto (LGPD), pede ao modelo causa, subcausa,
crença do comprador, canal, confiança e explicação, e valida o par causa/subcausa na
taxonomia (`taxonomia_devolucao.yaml`). Sem modelo, devolve `outros` com confiança 0 (vai
para a fila de revisão humana).
"""

from __future__ import annotations

import json
import logging
import random
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from promessa.config import get_settings, has_api_key
from promessa.llm.client import LLMError, complete_json
from promessa.privacy import preview, scrub
from promessa.rules.loader import load_rules

log = logging.getLogger(__name__)

PROMPT = "classifier_v1"
GOLD = Path(__file__).resolve().parents[3] / "data" / "gold"
EXAMPLE_SEED = 42
# Até 8 exemplos do split dev, balanceados por causa (CONTEXTO 12.2)
EXAMPLES_PER_CAUSE = {
    "promessa_explicita": 2,
    "promessa_expectativa": 1,
    "acesso_entrega": 2,
    "processo": 2,
    "fraude": 1,
}
MAIN_CAUSE = {  # as 5 classes da avaliação (CONTEXTO 14.2)
    "promessa_explicita": "promessa",
    "promessa_expectativa": "promessa",
    "acesso_entrega": "acesso",
    "processo": "processo",
    "fraude": "fraude",
    "outros": "outros",
}
Attribute = Literal["garantia", "acesso", "recorrencia", "bonus", "custo", "resultado", "outro"]


class BuyerBelief(BaseModel):
    attribute: Attribute
    value: str
    unit: str | None
    text: str


class ClassifierLLMOutput(BaseModel):
    cause: str
    subcause: str
    buyer_belief: BuyerBelief | None
    channel_mentioned: str | None
    confidence: float
    explanation: str


class Classification(BaseModel):
    cause: str
    subcause: str
    main_cause: str
    buyer_belief: BuyerBelief | None
    channel_mentioned: str | None
    confidence: float
    explanation: str
    model: str | None
    prompt_version: str | None
    corrected: bool = False  # a subcausa (ou a causa) do modelo foi corrigida
    source: Literal["modelo", "sem_modelo"] = "modelo"


# --- Exemplos (só do split dev) ----------------------------------------------------------


@lru_cache(maxsize=1)
def prompt_examples() -> tuple[dict, ...]:
    """Exemplos fixos do split `dev` da H1, balanceados por causa (semente fixa)."""
    splits = json.loads((GOLD / "splits.json").read_text(encoding="utf-8"))
    dev = set(splits["h1"]["dev"])
    with (GOLD / "h1_reclamacoes.jsonl").open(encoding="utf-8") as f:
        rows = [r for r in map(json.loads, f) if r["id"] in dev]
    rng = random.Random(EXAMPLE_SEED)
    chosen: list[dict] = []
    for cause, n in EXAMPLES_PER_CAUSE.items():
        pool = sorted((r for r in rows if r["causa"] == cause), key=lambda r: r["id"])
        chosen += rng.sample(pool, min(n, len(pool)))
    return tuple(chosen)


# --- Prompt ------------------------------------------------------------------------------


def prompt_variables(text: str, product_category: str | None) -> dict[str, str]:
    taxonomy = load_rules().taxonomy
    lines = []
    for c in taxonomy.causas:
        lines.append(f"- {c.causa} ({c.rotulo}): {c.nota}")
        lines += [f"  - {s.subcausa}: {s.definicao}" for s in c.subcausas]
    frontier = [
        f"- {b.situacao} → {b.causa}/{b.subcausa} ({b.motivo})" for b in taxonomy.casos_de_fronteira
    ]
    examples = [f'- "{r["texto"]}" → {r["causa"]}/{r["subcausa"]}' for r in prompt_examples()]
    return {
        "taxonomia": "\n".join(lines),
        "precedencia": " > ".join(taxonomy.precedencia),
        "fronteira": "\n".join(frontier),
        "exemplos": "\n".join(examples),
        "categoria": product_category or "não informada",
        "motivo": text,
    }


# --- Validação ---------------------------------------------------------------------------


def validate(raw: ClassifierLLMOutput) -> tuple[str, str, float, bool]:
    """Par causa/subcausa válido na taxonomia (CONTEXTO 12.2, item 3).

    Subcausa de outra causa → primeira subcausa válida da causa, confiança ≤ 0,5.
    Causa inexistente → outros/outros, confiança ≤ 0,5.
    """
    by_cause = load_rules().taxonomy.subcauses_by_cause()
    confidence = min(max(raw.confidence, 0.0), 1.0)
    if raw.cause not in by_cause:
        log.warning("classificador: causa inválida %r → outros", raw.cause)
        return "outros", "outros", min(confidence, 0.5), True
    if raw.subcause not in by_cause[raw.cause]:
        first = by_cause[raw.cause][0]
        log.warning("classificador: subcausa %r fora de %s → %s", raw.subcause, raw.cause, first)
        return raw.cause, first, min(confidence, 0.5), True
    return raw.cause, raw.subcause, confidence, False


def llm_available() -> bool:
    settings = get_settings()
    return has_api_key(settings) or settings.llm_offline


def classify_text(
    text: str,
    product_category: str | None = None,
    *,
    model: str | None = None,
    completer=None,
) -> Classification:
    """Classifica o motivo (já limpo aqui também). Sem modelo, `outros` com confiança 0."""
    clean = scrub(text)
    model = model or get_settings().classifier_model
    if completer is None and not llm_available():
        return _without_model("Sem modelo disponível; a classificação precisa de revisão humana.")
    try:
        result = (completer or complete_json)(
            PROMPT, prompt_variables(clean, product_category), ClassifierLLMOutput, model
        )
    except LLMError as e:
        log.warning("classificador indisponível (%s) para %r", e, preview(clean))
        return _without_model("O modelo não respondeu; a classificação precisa de revisão humana.")
    raw = result.data
    cause, subcause, confidence, corrected = validate(raw)
    return Classification(
        cause=cause,
        subcause=subcause,
        main_cause=MAIN_CAUSE[cause],
        buyer_belief=raw.buyer_belief,
        channel_mentioned=raw.channel_mentioned,
        confidence=confidence,
        explanation=raw.explanation,
        model=result.model,
        prompt_version=result.prompt_version,
        corrected=corrected,
    )


def _without_model(explanation: str) -> Classification:
    return Classification(
        cause="outros",
        subcause="outros",
        main_cause="outros",
        buyer_belief=None,
        channel_mentioned=None,
        confidence=0.0,
        explanation=explanation,
        model=None,
        prompt_version=None,
        source="sem_modelo",
    )
