"""Servidor MCP do Promessa Rastreável (transporte stdio).

Rodar: `uv run python -m promessa.mcp_server` (decisão D10).
SDK `mcp` 2.x: classe `MCPServer` (decisão D8).

Ferramentas finas (CONTEXTO 5, princípio 1): validam a entrada, abrem a sessão, chamam o
serviço e devolvem o modelo Pydantic. Erro de domínio sobe como `CODIGO: explicação`.
"""

import functools
import os
from collections.abc import Callable
from datetime import datetime
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from promessa.checker import service as checker_service
from promessa.checker.models import CheckResponse
from promessa.db.session import session_scope
from promessa.errors import DomainError
from promessa.facts import service as facts_service
from promessa.facts.service import FactsView, UpsertResult
from promessa.links import service as links_service
from promessa.links.service import LinkResponse
from promessa.refunds import service as refunds_service
from promessa.refunds.service import RefundResponse
from promessa.reports import explain as explain_service
from promessa.reports import service as reports_service
from promessa.reports.explain import Explanation
from promessa.reports.service import PromiseOutcomeReport
from promessa.review import service as review_service
from promessa.review.service import ReviewQueue, ReviewResult

VERSION = "0.1.0"

# PROMESSA_LOG_LEVEL=WARNING deixa o stderr do servidor quieto (a demo usa; D36)
mcp = MCPServer(
    "promessa-rastreavel",
    version=VERSION,
    log_level=os.environ.get("PROMESSA_LOG_LEVEL", "INFO").upper(),
)


def domain_errors[F: Callable[..., Any]](fn: F) -> F:
    """Converte `DomainError` em erro de ferramenta com a mensagem `CODIGO: explicação`."""

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except DomainError as e:
            raise ToolError(str(e)) from e

    return wrapper  # type: ignore[return-value]


@mcp.tool()
def ping() -> dict[str, object]:
    """Confere se o servidor está no ar."""
    return {"ok": True, "versao": VERSION}


@mcp.tool()
@domain_errors
def get_product_facts(product_id: str, version: int | None = None) -> FactsView:
    """Ficha de promessas do produto: condições da oferta, regras com fonte e o briefing para
    o creator. Sem `version`, devolve a versão vigente."""
    with session_scope() as session:
        return facts_service.get_product_facts(session, product_id, version)


@mcp.tool()
@domain_errors
def upsert_product_facts(
    product_id: str,
    guarantee_days: int,
    access_type: str,
    recurrence: str,
    created_by: str,
    access_months: int | None = None,
    auto_renewal: bool = False,
    bonuses: list[str] | None = None,
    extra_costs: list[dict[str, Any]] | None = None,
    brand_rules: list[dict[str, Any]] | None = None,
    valid_from: datetime | None = None,
) -> UpsertResult:
    """Cria uma nova versão da ficha (a anterior fica intacta) e devolve avisos.

    access_type: vitalicio | prazo (exige access_months) | assinatura | nao_aplica.
    recurrence: unica | mensal | anual. guarantee_days >= 7 (CDC art. 49).
    extra_costs: [{"descricao": str, "valor_mensal_cents": int}].
    brand_rules: [{"kind": "permitida"|"proibida", "text": str, "termos"?: [str],
    "output"?: "bloquear"|"revisar", "rule_key"?: "MARCA-..."}].
    """
    data = {
        "guarantee_days": guarantee_days,
        "access_type": access_type,
        "access_months": access_months,
        "recurrence": recurrence,
        "auto_renewal": auto_renewal,
        "bonuses": bonuses or [],
        "extra_costs": extra_costs or [],
        "brand_rules": brand_rules or [],
        "valid_from": valid_from,
    }
    with session_scope() as session:
        return facts_service.create_facts_version(session, product_id, data, created_by)


@mcp.tool()
@domain_errors
def check_content(
    product_id: str,
    creator_id: str,
    text: str,
    channel: str,
    submitted_by: str = "creator",
    published_since: str | None = None,
    parent_piece_id: str | None = None,
) -> CheckResponse:
    """Checa o texto de uma peça contra a ficha vigente do produto e grava a peça.

    Devolve, por trecho, `bloquear`, `revisar` ou `registrar`, com explicação e sugestão.
    channel: instagram | tiktok | youtube | whatsapp | outro. submitted_by: creator | marca.
    published_since: data ISO em que a peça entrou no ar (para urgência vencida).
    parent_piece_id: peça corrigida que esta substitui. `can_generate_link` diz se o link pode
    ser gerado (sem bloqueio pendente).
    """
    with session_scope() as session:
        return checker_service.check_content(
            session,
            product_id,
            creator_id,
            text,
            channel,
            submitted_by=submitted_by,
            published_since=published_since,
            parent_piece_id=parent_piece_id,
        )


@mcp.tool()
@domain_errors
def register_content_and_link(piece_id: str, actor_type: str = "humano") -> LinkResponse:
    """Gera o link rastreado de uma peça já checada e registra as promessas dela.

    Recusa com BLOQUEIO_PENDENTE (lista os trechos) se houver bloqueio não revertido, e com
    FICHA_DESATUALIZADA se a ficha mudou depois da checagem. actor_type: humano | agente.
    Chamar de novo para a mesma peça devolve o mesmo link.
    """
    with session_scope() as session:
        return links_service.register_content_and_link(session, piece_id, actor_type)


@mcp.tool()
@domain_errors
def list_review_queue(kind: str | None = None) -> ReviewQueue:
    """Pendências de decisão humana (para marca e Operações), com contexto e idade.

    kind: bloqueio (bloqueios contestados) | classificacao (devoluções com confiança baixa).
    """
    with session_scope() as session:
        return review_service.list_review_queue(session, kind)


@mcp.tool()
@domain_errors
def submit_review(
    target_type: str,
    target_id: str,
    action: str,
    actor: str,
    actor_role: str,
    note: str | None = None,
    payload: dict[str, Any] | None = None,
) -> ReviewResult:
    """Registra uma decisão humana.

    target_type: check_result | refund_classification.
    action: contestar (creator ou marca, só bloqueio) | manter | reverter | aprovar (trecho em
    revisão) | reclassificar (payload {"cause", "subcause"}). Só marca e Operações decidem.
    actor_role: creator | marca | operacoes.
    """
    with session_scope() as session:
        return review_service.submit_review(
            session, target_type, target_id, action, actor, actor_role, note, payload
        )


@mcp.tool()
@domain_errors
def classify_refund(sale_id: int, reason_text: str, type: str = "reembolso") -> RefundResponse:
    """Classifica o motivo de uma devolução e grava o evento (o motivo é limpo de dados pessoais).

    Devolve causa e subcausa da taxonomia, o que o comprador diz que foi prometido
    (buyer_belief), confiança e se precisa de revisão humana. type: reembolso | chargeback |
    ticket.
    """
    with session_scope() as session:
        return refunds_service.classify_refund(session, sale_id, reason_text, type)


@mcp.tool()
@domain_errors
def get_promise_outcome_report(
    creator_id: str | None = None,
    product_id: str | None = None,
    start: str = "2026-10-26",
    end: str = "2026-11-22",
) -> PromiseOutcomeReport:
    """Relatório de devoluções de um creator OU de um produto no período (AAAA-MM-DD).

    Taxas por causa, indicador de promessa confirmada (com mínimo de vendas), promessas mais
    contestadas, sinais para a marca (crenças que contradizem o registrado), cobertura,
    operação e integridade. Só dados agregados: nenhum texto de comprador.
    """
    with session_scope() as session:
        return reports_service.promise_outcome_report(session, creator_id, product_id, start, end)


@mcp.tool()
@domain_errors
def explain_refunds_to_creator(
    creator_id: str, start: str = "2026-10-26", end: str = "2026-11-22"
) -> Explanation:
    """Explicação curta, para o creator, de por que as vendas voltaram e qual trecho mudar.

    Gerada só de dados agregados (sem texto de comprador); `data_used` mostra os números usados.
    """
    with session_scope() as session:
        return explain_service.explain_refunds_to_creator(session, creator_id, start, end)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
