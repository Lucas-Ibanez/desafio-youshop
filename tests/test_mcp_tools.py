"""Ferramentas MCP chamadas pelo protocolo (cliente MCP), nunca pela função Python direto."""

import sys

import anyio
from mcp import Client, StdioServerParameters

from tests.mcp_helpers import call_tool, list_tool_names

PING_ESPERADO = {"ok": True, "versao": "0.1.0"}


def test_ping_em_memoria():
    assert "ping" in list_tool_names()
    assert call_tool("ping") == PING_ESPERADO


def test_ping_por_stdio():
    """Servidor como subprocesso (`python -m promessa.mcp_server`), MCP por stdin/stdout."""
    params = StdioServerParameters(command=sys.executable, args=["-m", "promessa.mcp_server"])

    async def run():
        async with Client(params) as client:
            tools = await client.list_tools()
            result = await client.call_tool("ping", {})
            return {t.name for t in tools.tools}, result

    names, result = anyio.run(run)
    assert "ping" in names
    assert not result.is_error
    assert result.structured_content == PING_ESPERADO
