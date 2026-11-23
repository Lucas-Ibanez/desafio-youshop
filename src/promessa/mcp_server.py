"""Servidor MCP do Promessa Rastreável (transporte stdio).

Rodar: `uv run python -m promessa.mcp_server` (decisão D10).
SDK `mcp` 2.x: classe `MCPServer` (decisão D8).

Ferramentas finas (CONTEXTO 5, princípio 1): validam a entrada, abrem a sessão, chamam o
serviço e devolvem o modelo Pydantic. Erro de domínio sobe como `CODIGO: explicação`.
"""

import functools
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

VERSION = "0.1.0"

mcp = MCPServer("promessa-rastreavel", version=VERSION)


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


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
