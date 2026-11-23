"""Ferramentas MCP chamadas pelo protocolo (cliente MCP), nunca pela função Python direto."""

import sys

import anyio
from mcp import Client, StdioServerParameters

from promessa.mcp_server import mcp

PING_ESPERADO = {"ok": True, "versao": "0.1.0"}


async def _list_and_ping(client: Client) -> tuple[set[str], object]:
    tools = await client.list_tools()
    result = await client.call_tool("ping", {})
    assert not result.is_error
    return {t.name for t in tools.tools}, result.structured_content


def test_ping_em_memoria():
    """Cliente em memória com handshake `initialize` e mensagens JSON-RPC (mode="legacy")."""

    async def run():
        async with Client(mcp, mode="legacy") as client:
            return await _list_and_ping(client)

    names, payload = anyio.run(run)
    assert "ping" in names
    assert payload == PING_ESPERADO


def test_ping_por_stdio():
    """Servidor como subprocesso, falando MCP por stdin/stdout (mesmo caminho do Claude Code)."""
    params = StdioServerParameters(command=sys.executable, args=["-m", "promessa.mcp_server"])

    async def run():
        async with Client(params) as client:
            return await _list_and_ping(client)

    names, payload = anyio.run(run)
    assert "ping" in names
    assert payload == PING_ESPERADO
