"""Servidor MCP do Promessa Rastreável (transporte stdio).

SDK `mcp` 2.x: a classe `FastMCP` do CONTEXTO virou `MCPServer` (ver docs/decisoes.md, D8).
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
