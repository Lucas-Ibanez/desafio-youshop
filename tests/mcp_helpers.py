"""Helpers para chamar ferramentas MCP pelo protocolo nos testes."""

import json
from typing import Any

import anyio
from mcp import Client

from promessa.mcp_server import mcp


async def call_tool_async(name: str, arguments: dict[str, Any] | None = None) -> Any:
    """Abre um cliente MCP em memória (handshake `initialize` + JSON-RPC), chama a ferramenta
    e devolve o resultado desserializado. Erro da ferramenta vira `ToolCallError`."""
    async with Client(mcp, mode="legacy") as client:
        result = await client.call_tool(name, arguments or {})
    if result.is_error:
        raise ToolCallError(_text(result))
    if result.structured_content is not None:
        return result.structured_content
    return json.loads(_text(result))


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> Any:
    """Versão síncrona de `call_tool_async`."""
    return anyio.run(call_tool_async, name, arguments)


async def list_tool_names_async() -> set[str]:
    async with Client(mcp, mode="legacy") as client:
        tools = await client.list_tools()
    return {t.name for t in tools.tools}


def list_tool_names() -> set[str]:
    return anyio.run(list_tool_names_async)


class ToolCallError(Exception):
    """A ferramenta respondeu com `is_error` (ex.: `CODIGO: explicação`)."""


def _text(result: Any) -> str:
    return "".join(getattr(block, "text", "") for block in result.content)
