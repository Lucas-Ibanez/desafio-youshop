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
**Atualização (23/11/2026):** CONTEXTO seção 6 corrigida para `MCPServer` e `mcp.Client`. O comentário da árvore da seção 7 (`mcp_server.py # FastMCP + ferramentas`) e a linha `Makefile` da mesma árvore ficaram como estavam (edição não autorizada nesta rodada); leia `MCPServer` e `tasks.py`.
**Atualização (23/11/2026):** árvore da seção 7 corrigida (D15).

## D9 · `make` ausente na máquina de desenvolvimento (Windows) · 23/11/2026 · substituída pela D11
**Contexto:** o `Makefile` é a interface de comandos do projeto, mas `make` não está instalado e instalá-lo exige mudança global na máquina.
**Decisão:** manter o `Makefile` como fonte dos comandos, com receitas portáveis (operações de arquivo via `uv run python -c`). Até o `make` ser instalado, os alvos são verificados rodando os mesmos comandos `uv run ...`.
**Consequência:** nenhum alvo depende de ferramenta Unix além do shell que o `make` já usa.

## D10 · Launcher `promessa-mcp.exe` bloqueado pelo Windows · 23/11/2026
**Contexto:** `uv run promessa-mcp` falha com "Uma política de Controle de Aplicativo bloqueou este arquivo" (os error 4551). O Windows bloqueia o `.exe` não assinado que o uv gera em `.venv/Scripts/`. `uv run python -m promessa.mcp_server` executa o mesmo `main()` e funciona (responde ao `initialize` e fica aguardando em stdio).
**Decisão:** manter o script `promessa-mcp` no `pyproject.toml` e o alvo `make mcp` como especificados, sem mudar a política da máquina. Nesta máquina, a forma que funciona é `uv run python -m promessa.mcp_server`. Os testes por stdio já usam `python -m`. Pendente com o Lucas: trocar o alvo `make mcp` e o registro no Claude Code (T15) para `python -m`, ou liberar o executável na política do Windows.
**Consequência:** até decidir, `make mcp` falha nesta máquina; o servidor e os testes funcionam.
**Status (23/11/2026): resolvida.** O comando oficial do servidor passa a ser `uv run python -m promessa.mcp_server` (tarefa `mcp` do `tasks.py`, D11). O script `promessa-mcp` fica no `pyproject.toml` por não atrapalhar em outras máquinas, mas nenhum documento ou tarefa depende dele. PLANO T15 atualizado: registro no Claude Code com `uv run --directory <repo> python -m promessa.mcp_server`.

## D11 · `tasks.py` no lugar do `Makefile` · 23/11/2026
**Contexto:** `make` não existe na máquina de desenvolvimento (Windows) e não vamos instalar nada global (D9). Os `.exe` do `.venv` podem ser bloqueados (D10).
**Decisão:** `tasks.py` na raiz, em Python puro (só biblioteca padrão), com as mesmas tarefas da seção 17.2 do CONTEXTO mais `help`. Uso: `uv run python tasks.py <tarefa> [<tarefa> ...]`, em sequência, parando na primeira falha. Ferramentas Python sempre via `sys.executable -m <módulo>`; só `setup` chama o `uv`. Subprocessos recebem `PYTHONUTF8=1` e `PYTHONIOENCODING=utf-8`. `db-reset` usa `pathlib`. O `Makefile` foi apagado.
**Consequência:** nos documentos, `make <x>` significa `uv run python tasks.py <x>` (aviso na seção 17.2 do CONTEXTO e na seção 2 do PLANO). `test-llm` trata "nenhum teste coletado" (código 5 do pytest) como sucesso enquanto não houver testes com o modelo. O pytest ganhou `pythonpath = ["."]` para os testes importarem `tasks` e `tests.mcp_helpers`.

## D12 · `.gitattributes` e UTF-8 em todo lugar · 23/11/2026
**Contexto:** no Windows, o git convertia LF em CRLF (avisos em todo `git add`) e o console quebra acentos e símbolos.
**Decisão:** `.gitattributes` com `* text=auto eol=lf` e `git add --renormalize .`. Regras novas no CLAUDE.md: sempre abrir arquivos com `encoding='utf-8'` (inclusive CSV e YAML) e nunca chamar executáveis do `.venv` (usar `python -m`).
**Consequência:** o repositório fica em LF; `ruff format --check` continua limpo.

## D13 · `docs/fontes/` fora do git · 23/11/2026
**Contexto:** o guia do MVP e as validações H1–H4 têm nomes reais de anunciantes e pessoas, com vereditos de irregularidade.
**Decisão:** `.gitignore` ignora `docs/fontes/*`, exceto `docs/fontes/README.md`, que explica o motivo.
**Consequência:** quem clona o repositório precisa copiar as fontes à mão. Nada nos gabaritos versionados (`data/gold/`) pode depender de texto que só exista nas fontes.

## D14 · Modelo de linguagem: Gemini no lugar da API do Claude · 23/11/2026
**Contexto:** o Lucas decidiu usar a API do Gemini. A chave (`GEMINI_API_KEY`) é da Gemini API (AI Studio) e funciona com o SDK `google-genai` sem Vertex AI. A listagem de modelos da chave foi consultada em 23/11/2026.
**Decisão:** trocar o SDK `anthropic` pelo `google-genai` (3.6.1) e a variável `ANTHROPIC_API_KEY` por `GEMINI_API_KEY`. Saída estruturada passa a ser a nativa do Gemini (`response_mime_type="application/json"` + `response_schema` com o modelo Pydantic), no lugar de *tool use* forçado; temperatura 0 continua. Padrões, mantendo a divisão "checador mais capaz, classificador de volume": `CHECKER_MODEL=gemini-3.6-flash`, `CLASSIFIER_MODEL` e `EXPLAINER_MODEL=gemini-3.5-flash-lite`. Fumaça em 23/11: os dois responderam a chamada simples e a estruturada (`{"ok": true}`). Alternativas observadas: `gemini-3.7-flash` respondeu 503 (alta demanda) nas duas tentativas; `gemini-3.5-flash` funcionou; `gemini-2.5-flash` aparece na listagem mas devolve 404; os `gemini-4-*` (nomes-código) não foram usados por não indicarem versão estável.
**Consequência:** CONTEXTO (seções 5, 6, 7 e 17.1), PLANO (T00, T01 e T07), README, `.env.example`, `config.py`, testes e marcador `llm` atualizados. Claude Code e Claude Desktop continuam como ferramenta de desenvolvimento e cliente MCP; só o modelo dos agentes mudou. O retry da T07 precisa cobrir 503. A escolha final de cada modelo continua pelo split `dev` (CONTEXTO 18.2).

## D15 · Árvore da seção 7 do CONTEXTO alinhada ao repositório · 23/11/2026
**Contexto:** a árvore ainda mostrava `Makefile`, `FastMCP`, *tool use* e não tinha os arquivos criados na T01/T01b.
**Decisão:** raiz nomeada como o repositório (`desafio-youshop/`, projeto `promessa-rastreavel`); `Makefile` → `tasks.py`; `.python-version` e `.gitattributes` incluídos; `.gitignore` com `docs/fontes/`; `docs/fontes/` e `data/raw/` marcados fora do git, com os nomes dos CSV e do `anon_map.yaml`; `llm/client.py` com saída estruturada do Gemini; `mcp_server.py` com `MCPServer` e `python -m`; `tests/` com `mcp_helpers.py`, `test_config.py` e `test_tasks.py`.
**Consequência:** a árvore descreve o que existe hoje e o que as tasks vão criar, sem resíduos do Makefile e do FastMCP.
