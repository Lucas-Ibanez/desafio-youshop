# Decisões

Registro curto das decisões do MVP. Cada decisão segue o formato abaixo. Uma decisão revista
ganha um novo registro que cita a anterior; registros antigos não são apagados.

```
## D<n> · <título> · <data>
**Contexto:** o que levou à decisão.
**Decisão:** o que foi escolhido.
**Consequência:** o que muda no código ou no produto.
```

As decisões D1–D7 vêm da seção 18.1 do docs/CONTEXTO.md.

---

## D1 · A ficha é a fonte das condições do checkout · 23/11/2026
**Contexto:** não há integração com o checkout real da YouShop no MVP.
**Decisão:** a ficha de promessas é tratada como a fonte das condições da oferta.
**Consequência:** o checador compara a peça com a ficha. Em produção, a ficha seria comparada com a configuração do checkout.

## D2 · `revisar` não impede o link · 23/11/2026
**Contexto:** o guia diz que o creator vê a sugestão e a marca pode aprovar.
**Decisão:** trechos `revisar` não bloqueiam a geração do link; a promessa extraída vai como `em_revisao`.
**Consequência:** essas promessas ficam presas à venda e podem ser ligadas a uma devolução depois.

## D3 · Painel chama serviços direto; demo e Claude Code usam MCP · 23/11/2026
**Contexto:** velocidade de construção.
**Decisão:** o painel Streamlit importa os serviços; `demo_e2e.py` e o Claude Code passam pelo MCP.
**Consequência:** comportamento idêntico, pois ambos usam os mesmos serviços. Na fase 2, o painel pode virar cliente MCP.

## D4 · Regras oficiais copiadas para `claim_rule` em cada versão da ficha · 23/11/2026
**Contexto:** é preciso provar o que valia no dia da venda (CDC art. 30).
**Decisão:** ao criar uma versão da ficha, as regras oficiais da categoria são materializadas em `claim_rule`.
**Consequência:** mudar um YAML depois não altera o que valia para versões antigas.

## D5 · Identificação publicitária fora do `overall` · 23/11/2026
**Contexto:** todo anúncio da H2 já carregava "Patrocinado"; contar isso distorceria o Teste 1.
**Decisão:** a falta de `#publi` não entra no `overall`; aparece no briefing e no campo `disclosure`.
**Consequência:** evita falso positivo em massa.

## D6 · `bloquear` só com `rule_key` de lista ou ficha · 23/11/2026
**Contexto:** o guia define bloquear como "proibida em lista oficial ou condição contrária à ficha".
**Decisão:** o modelo sozinho no máximo sugere `revisar`; `bloquear` exige `rule_key` existente.
**Consequência:** regra de fusão em código na camada 2 do checador.

## D7 · Vendas e devoluções simuladas; avaliação com dados reais · 23/11/2026
**Contexto:** não há dado da YouShop até a H5.
**Decisão:** o simulador gera vendas e devoluções; o Teste 1 usa os gabaritos reais da H1 e da H2.
**Consequência:** as métricas dos agentes vêm de dados reais; os relatórios da demo, de dados sintéticos.

## D8 · SDK `mcp` 2.x: `FastMCP` virou `MCPServer` · 23/11/2026
**Contexto:** o CONTEXTO (seção 6) cita `FastMCP` em `mcp.server.fastmcp`. A versão estável instalada é `mcp` 2.3.0, em que esse módulo foi removido (importá-lo levanta `ModuleNotFoundError` com aviso de migração).
**Decisão:** seguir o pacote instalado, como manda o CONTEXTO: `from mcp.server.mcpserver import MCPServer`, `MCPServer("promessa-rastreavel", version=...)`, `@mcp.tool()` e `mcp.run(transport="stdio")`. Nos testes, o cliente é `mcp.Client`: recebe a instância do servidor (em memória; com `mode="legacy"` faz o handshake `initialize` e troca mensagens JSON-RPC) ou `StdioServerParameters` (subprocesso stdio).
**Consequência:** onde o CONTEXTO e o PLANO dizem `FastMCP`, leia `MCPServer`. A demo da T15 pode usar `mcp.Client(StdioServerParameters(...))` no lugar de montar `ClientSession` à mão.

## D9 · `make` ausente na máquina de desenvolvimento (Windows) · 23/11/2026
**Contexto:** o `Makefile` é a interface de comandos do projeto, mas `make` não está instalado e instalá-lo exige mudança global na máquina.
**Decisão:** manter o `Makefile` como fonte dos comandos, com receitas portáveis (operações de arquivo via `uv run python -c`). Até o `make` ser instalado, os alvos são verificados rodando os mesmos comandos `uv run ...`.
**Consequência:** nenhum alvo depende de ferramenta Unix além do shell que o `make` já usa.

## D10 · Launcher `promessa-mcp.exe` bloqueado pelo Windows · 23/11/2026
**Contexto:** `uv run promessa-mcp` falha com "Uma política de Controle de Aplicativo bloqueou este arquivo" (os error 4551). O Windows bloqueia o `.exe` não assinado que o uv gera em `.venv/Scripts/`. `uv run python -m promessa.mcp_server` executa o mesmo `main()` e funciona (responde ao `initialize` e fica aguardando em stdio).
**Decisão:** manter o script `promessa-mcp` no `pyproject.toml` e o alvo `make mcp` como especificados, sem mudar a política da máquina. Nesta máquina, a forma que funciona é `uv run python -m promessa.mcp_server`. Os testes por stdio já usam `python -m`. Pendente com o Lucas: trocar o alvo `make mcp` e o registro no Claude Code (T15) para `python -m`, ou liberar o executável na política do Windows.
**Consequência:** até decidir, `make mcp` falha nesta máquina; o servidor e os testes funcionam.
