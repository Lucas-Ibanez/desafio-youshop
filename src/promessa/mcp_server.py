"""Servidor MCP do Promessa Rastreável (transporte stdio).

Rodar: `uv run python -m promessa.mcp_server` (decisão D10).
SDK `mcp` 2.x: classe `MCPServer` (decisão D8).
"""

from mcp.server.mcpserver import MCPServer

VERSION = "0.1.0"

mcp = MCPServer("promessa-rastreavel", version=VERSION)


@mcp.tool()
def ping() -> dict[str, object]:
    """Confere se o servidor está no ar."""
    return {"ok": True, "versao": VERSION}


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
