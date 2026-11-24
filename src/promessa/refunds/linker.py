"""Ligação da devolução com a promessa registrada (CONTEXTO 12.2, item 4, e 12.3; T11).

- Causa diferente de `promessa_explicita` → `nao_aplicavel`.
- Crença sobre condição da oferta (garantia, acesso, recorrência, bônus, custo) → comparação
  determinística com a promessa registrada do mesmo atributo: igual = `confirma`,
  diferente = `contradiz`, nenhuma registrada = `sem_relacao`.
- Crença sobre resultado ou alegação → modelo (`linker_v1`), só se houver promessa desse tipo
  registrada; sem promessa assim, `sem_relacao` sem chamar o modelo.
- Invariante 4 (CONTEXTO 8.3): `confirma`/`contradiz` sempre com promessa ligada ou crença.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal, Protocol

from pydantic import BaseModel

from promessa.config import get_settings, has_api_key
from promessa.db.enums import Relation, ReviewStatus
from promessa.llm.client import LLMError, complete_json
from promessa.rules.normalize import normalize

log = logging.getLogger(__name__)

PROMPT = "linker_v1"
CONDITION_ATTRIBUTES = {"garantia", "acesso", "recorrencia", "bonus", "custo"}
FREE_TYPES = {"resultado", "alegacao"}


class PromiseLike(Protocol):
    id: int
    type: Any
    attribute: Any
    value: str | None
    unit: str | None
    normalized_text: str


class LinkResult(BaseModel):
    relation: Relation
    promise_id: int | None
    method: Literal["regra", "modelo", "nenhum"]
    explanation: str
    model: str | None = None
    prompt_version: str | None = None


class LinkerLLMOutput(BaseModel):
    relation: Literal["confirma", "contradiz", "sem_relacao"]
    promise_id: int | None
    explanation: str


def _v(x) -> str:
    return getattr(x, "value", x) or ""


def _norm(text: str | None) -> str:
    return re.sub(r"\s+", " ", normalize(str(text or ""))).strip()


def _months(value: str, unit: str | None) -> str:
    """Acesso normalizado: "vitalicio" ou número de meses ("1" ano → "12")."""
    v = _norm(value)
    if v in ("vitalicio", "para sempre", "ilimitado", "permanente"):
        return "vitalicio"
    digits = re.sub(r"\D", "", v)
    if not digits:
        return v
    n = int(digits)
    return str(n * 12) if _norm(unit).startswith("ano") else str(n)


def same_condition(attribute: str, belief: dict, promise: PromiseLike) -> bool:
    """A crença do comprador e a promessa registrada dizem a mesma coisa?"""
    b_value, p_value = belief.get("value"), promise.value
    if attribute == "garantia":
        return re.sub(r"\D", "", _norm(b_value)) == re.sub(r"\D", "", _norm(p_value))
    if attribute == "acesso":
        return _months(b_value, belief.get("unit")) == _months(p_value, promise.unit)
    if attribute == "bonus":
        b, p = _norm(b_value), _norm(p_value)
        return b in ("citado", "bonus") or (bool(b) and (b in p or p in b))
    return _norm(b_value) == _norm(p_value)


# --- Ligação -----------------------------------------------------------------------------


def _ensure_invariant(result: LinkResult, belief: dict | None) -> LinkResult:
    if (
        result.relation in (Relation.CONFIRMA, Relation.CONTRADIZ)
        and result.promise_id is None
        and not belief
    ):
        return LinkResult(
            relation=Relation.SEM_RELACAO,
            promise_id=None,
            method=result.method,
            explanation="Sem promessa ligada nem crença do comprador para comparar.",
        )
    return result


def link_condition(belief: dict, promises: list[PromiseLike]) -> LinkResult:
    attribute = belief["attribute"]
    same_attr = [p for p in promises if _v(p.attribute) == attribute]
    if not same_attr:
        return LinkResult(
            relation=Relation.SEM_RELACAO,
            promise_id=None,
            method="regra",
            explanation=(
                f"O comprador fala de {attribute}, mas a peça não registrou nada sobre isso."
            ),
        )
    match = next((p for p in same_attr if same_condition(attribute, belief, p)), None)
    if match is not None:
        return LinkResult(
            relation=Relation.CONFIRMA,
            promise_id=match.id,
            method="regra",
            explanation=(
                f"O comprador cobra a mesma condição registrada na peça ({match.normalized_text})."
            ),
        )
    first = same_attr[0]
    return LinkResult(
        relation=Relation.CONTRADIZ,
        promise_id=first.id,
        method="regra",
        explanation=(
            f"A peça registrou {first.normalized_text}, mas o comprador acredita em outra "
            f"coisa ({attribute}: {belief.get('value')}). A expectativa veio de outro lugar."
        ),
    )


def link_free(
    belief: dict,
    reason_text: str,
    promises: list[PromiseLike],
    *,
    completer=None,
    model: str | None = None,
) -> LinkResult:
    """Resultado ou alegação: compara com o modelo as promessas desse tipo."""
    candidates = [p for p in promises if _v(p.type) in FREE_TYPES]
    if not candidates:
        return LinkResult(
            relation=Relation.SEM_RELACAO,
            promise_id=None,
            method="regra",
            explanation=(
                "O comprador cobra um resultado, mas a peça não registrou promessa de resultado."
            ),
        )
    settings = get_settings()
    if completer is None and not (has_api_key(settings) or settings.llm_offline):
        return LinkResult(
            relation=Relation.SEM_RELACAO,
            promise_id=None,
            method="nenhum",
            explanation="Sem modelo para comparar o resultado; precisa de revisão humana.",
        )
    model = model or settings.classifier_model
    variables = {
        "crenca": (
            f'{belief.get("attribute")}: {belief.get("value")} (trecho: "{belief.get("text", "")}")'
        ),
        "motivo": reason_text,
        "promessas": "\n".join(f"- {p.id}: {_v(p.type)}; {p.normalized_text}" for p in candidates),
    }
    try:
        result = (completer or complete_json)(PROMPT, variables, LinkerLLMOutput, model)
    except LLMError as e:
        log.warning("linker indisponível: %s", e)
        return LinkResult(
            relation=Relation.SEM_RELACAO,
            promise_id=None,
            method="nenhum",
            explanation="O modelo não respondeu; a relação precisa de revisão humana.",
        )
    data = result.data
    valid_ids = {p.id for p in candidates}
    promise_id = data.promise_id if data.promise_id in valid_ids else None
    relation = Relation(data.relation)
    if relation == Relation.SEM_RELACAO:
        promise_id = None
    return LinkResult(
        relation=relation,
        promise_id=promise_id,
        method="modelo",
        explanation=data.explanation,
        model=result.model,
        prompt_version=result.prompt_version,
    )


def link(
    cause: str,
    belief: dict | None,
    reason_text: str,
    promises: list[PromiseLike],
    *,
    completer=None,
    model: str | None = None,
) -> LinkResult:
    """Relação entre a devolução e as promessas registradas na peça da venda."""
    if cause != "promessa_explicita":
        return LinkResult(
            relation=Relation.NAO_APLICAVEL,
            promise_id=None,
            method="nenhum",
            explanation="A causa não é promessa explícita.",
        )
    if not belief:
        return LinkResult(
            relation=Relation.SEM_RELACAO,
            promise_id=None,
            method="nenhum",
            explanation="O comprador não diz o que foi prometido.",
        )
    if belief.get("attribute") in CONDITION_ATTRIBUTES:
        result = link_condition(belief, promises)
    else:
        result = link_free(belief, reason_text, promises, completer=completer, model=model)
    return _ensure_invariant(result, belief)


def weighs_on_creator(
    cause: str,
    relation: Relation | str,
    confidence: float,
    review_status: ReviewStatus | str,
    threshold: float | None = None,
) -> bool:
    """A devolução conta no indicador do creator? (CONTEXTO 12.1, 12.3 e 12.4)

    Só promessa explícita que `confirma` a promessa registrada, com confiança alta e não
    revertida por revisão humana.
    """
    threshold = get_settings().confidence_threshold if threshold is None else threshold
    return (
        cause == "promessa_explicita"
        and _v(relation) == Relation.CONFIRMA.value
        and confidence >= threshold
        and _v(review_status) != ReviewStatus.REVERTIDO.value
    )
