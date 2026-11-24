"""Explicação das devoluções para o creator (CONTEXTO 12.5; T13).

Gerada só de dados agregados (nunca do texto do comprador), até ~120 palavras, tom de ajuda.
Estrutura: o que voltou, por quê, o que não é com o creator, qual trecho mudar, lembrete de
#publi. Usa o modelo (`explainer_v1`); sem chave, com erro ou com texto fora das regras (longo
demais ou sem o trecho a mudar), usa o modelo de texto fixo.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from promessa.checker.service import disclosure_of
from promessa.config import get_settings, has_api_key
from promessa.db.models import ContentPiece, TrackedLink
from promessa.llm.client import LLMError, complete_json
from promessa.reports.service import promise_outcome_report

log = logging.getLogger(__name__)

PROMPT = "explainer_v1"
MAX_WORDS = 130  # ~120 com folga para pontuação


class ExplainerLLMOutput(BaseModel):
    text: str


class Explanation(BaseModel):
    text: str
    data_used: dict[str, Any]
    source: Literal["modelo", "modelo_de_texto"]


def explanation_data(
    session: Session, creator_id: str, start: str | date | datetime, end: str | date | datetime
) -> dict[str, Any]:
    """Só agregados: números por grupo de causa, trechos da peça a mudar, indicador, #publi."""
    report = promise_outcome_report(session, creator_id=creator_id, start=start, end=end)
    by_cause = {c.causa: c.devolucoes for c in report.causas}
    confirmed = report.indicador_creator.devolucoes_confirmadas if report.indicador_creator else 0
    promise_total = by_cause.get("promessa_explicita", 0)
    pieces = session.scalars(
        select(ContentPiece).where(
            ContentPiece.id.in_(
                select(TrackedLink.piece_id).where(TrackedLink.creator_id == creator_id)
            )
        )
    ).all()
    return {
        "periodo": report.periodo,
        "vendas": report.vendas,
        "devolucoes": report.devolucoes,
        "promessa_da_peca_cobrada": confirmed,
        "promessa_que_nao_veio_da_peca": promise_total - confirmed,
        "expectativa_ou_qualidade": by_cause.get("promessa_expectativa", 0),
        "nao_e_com_voce": {
            "acesso_ou_entrega": by_cause.get("acesso_entrega", 0),
            "cancelamento_ou_reembolso": by_cause.get("processo", 0),
            "cobranca_nao_reconhecida": by_cause.get("fraude", 0),
            "outros": by_cause.get("outros", 0),
        },
        "trechos_a_mudar": [
            {"trecho": p.trecho, "promessa": p.promessa, "devolucoes": p.devolucoes}
            for p in report.promessas_mais_contestadas
            if p.trecho
        ],
        "indicador": report.indicador_creator.status if report.indicador_creator else None,
        "taxa_promessa_confirmada": (
            report.indicador_creator.taxa_promessa_confirmada if report.indicador_creator else None
        ),
        "publi_faltando": any(not disclosure_of(p.text).present for p in pieces),
    }


def fixed_text(data: dict[str, Any]) -> str:
    """Modelo de texto fixo (sem modelo de linguagem), com os mesmos campos."""
    n, sales = data["devolucoes"], data["vendas"]
    if sales == 0:
        return "Não houve vendas pelos seus links neste período."
    parts = [f"Neste período, {n} das suas {sales} vendas voltaram."]
    if data["trechos_a_mudar"]:
        top = data["trechos_a_mudar"][0]
        parts.append(
            f"{data['promessa_da_peca_cobrada']} foram por uma promessa da sua peça que o "
            f'comprador cobrou: o trecho "{top["trecho"]}". Vale reescrever esse trecho sem '
            "prometer número ou prazo de resultado; fale do que o produto oferece."
        )
    else:
        parts.append("Nenhuma devolução veio de promessa da sua peça.")
    other = data["nao_e_com_voce"]
    not_yours = sum(other.values())
    if not_yours:
        parts.append(
            f"{not_yours} não têm a ver com você: {other['acesso_ou_entrega']} de acesso ou "
            f"entrega, {other['cancelamento_ou_reembolso']} de cancelamento ou reembolso e "
            f"{other['cobranca_nao_reconhecida']} de cobrança não reconhecida. Isso fica com a "
            "marca e a plataforma."
        )
    if data["promessa_que_nao_veio_da_peca"]:
        parts.append(
            f"{data['promessa_que_nao_veio_da_peca']} citaram uma promessa que não está na sua "
            "peça; a marca vai olhar de onde ela veio."
        )
    if data["indicador"] == "dados_insuficientes":
        parts.append("Ainda são poucas vendas para um indicador confiável.")
    if data["publi_faltando"]:
        parts.append("Lembre de identificar a publicidade com #publi.")
    return " ".join(parts)


def _acceptable(text: str, data: dict[str, Any]) -> bool:
    if not text.strip() or len(text.split()) > MAX_WORDS:
        return False
    return all(t["trecho"] in text for t in data["trechos_a_mudar"][:1])


def explain_refunds_to_creator(
    session: Session,
    creator_id: str,
    start: str | date | datetime = "2026-10-26",
    end: str | date | datetime = "2026-11-22",
    *,
    completer=None,
) -> Explanation:
    data = explanation_data(session, creator_id, start, end)
    settings = get_settings()
    if completer is not None or has_api_key(settings) or settings.llm_offline:
        try:
            result = (completer or complete_json)(
                PROMPT,
                {"dados": json.dumps(data, ensure_ascii=False, indent=1)},
                ExplainerLLMOutput,
                settings.explainer_model,
            )
            if _acceptable(result.data.text, data):
                return Explanation(text=result.data.text.strip(), data_used=data, source="modelo")
            log.info("explicação do modelo fora das regras (tamanho ou trecho); usando texto fixo")
        except LLMError as e:
            log.warning("explicador indisponível: %s", e)
    return Explanation(text=fixed_text(data), data_used=data, source="modelo_de_texto")
