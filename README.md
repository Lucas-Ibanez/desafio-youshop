# Promessa Rastreável (MVP)

Servidor MCP com dois agentes de IA e um painel que ligam o que o produto pode prometer,
o que o creator prometeu na peça que gerou a venda e por que o comprador pediu o dinheiro de volta.
A devolução volta para quem prometeu, de forma automática e auditável.

## Requisitos

- [uv](https://docs.astral.sh/uv/) (instala o Python 3.12 do projeto, fixado em `.python-version`)
- Chave da API do Gemini no `.env` (copie de `.env.example`)

Não precisa de `make`: os comandos ficam em `tasks.py`, em Python puro.

## Começar

```bash
cp .env.example .env                       # depois preencha GEMINI_API_KEY
uv run python tasks.py setup               # instala as dependências (uv sync)
uv run python tasks.py lint test           # ruff e testes sem rede
uv run python tasks.py help                # lista todas as tarefas
```

Tarefas em sequência param na primeira falha: `uv run python tasks.py setup lint test`.
Nos documentos, `make <x>` significa `uv run python tasks.py <x>`.

| Tarefa | Faz |
|---|---|
| `setup` | `uv sync` |
| `lint` / `format` | ruff |
| `test` / `test-llm` | pytest sem modelo / só testes que chamam o Gemini |
| `db-reset` | apaga e recria `var/promessa.db` |
| `gold` | importa, anonimiza e confere os gabaritos (precisa de `data/raw/` e `docs/fontes/`) |
| `seed` | marcas, produtos, fichas v1 e creators fictícios |
| `simulate` | peças, links, 600 vendas e devoluções fictícias (`PROMESSA_SIMULATE_ARGS="--modo gabarito"` roda sem modelo) |
| `eval-checador` / `eval-classificador` / `eval` | Teste 1 dos agentes (relatórios em `eval/reports/`) |
| `demo` | exemplo do guia de ponta a ponta pelo protocolo MCP |
| `painel` | painel Streamlit (marca, creator, Operações) |
| `mcp` | sobe o servidor MCP em stdio |

Servidor MCP: `uv run python -m promessa.mcp_server` (o mesmo que `tasks.py mcp`).

## Demo de ponta a ponta

```bash
uv run python tasks.py demo
```

Sobe o servidor MCP como subprocesso stdio num banco só da demo (`var/demo.db`) e roda o exemplo do
guia: ficha do Treino em Casa (7 dias de garantia, 12 meses de acesso) → peça com "acesso vitalício
e 30 dias para testar" bloqueada → peça corrigida com o link gerado → devolução "perdi o acesso,
achei que era para sempre" classificada como promessa / condição da oferta, **contradiz**, sem pesar
na creator → relatório do produto com o sinal "acesso vitalício" para a marca. Termina com
"Demo concluída" (cerca de 5 s com cache).

## Conectar no Claude Code

```bash
claude mcp add promessa -- uv run --directory <caminho absoluto do repositório> python -m promessa.mcp_server
claude mcp list        # promessa: ... ✔ Connected
```

O servidor usa o banco de `PROMESSA_DB_URL` (padrão `var/promessa.db`); rode
`uv run python tasks.py db-reset seed simulate` antes para ter dados. São 9 ferramentas (e `ping`):
`get_product_facts`, `upsert_product_facts`, `check_content`, `register_content_and_link`,
`classify_refund`, `get_promise_outcome_report`, `explain_refunds_to_creator`, `list_review_queue`,
`submit_review`.

Três pedidos de exemplo (respostas reais de 24/11/2026, resumidas):

1. **"Confira esta legenda para o produto prod_magnesio, da creator cr_eli: 'Magnésio que seca barriga
   e turbina a imunidade! A vitamina B6 auxilia no funcionamento do sistema imune. Só hoje!'"**
   → bloqueada: tirar "seca barriga" (emagrecimento não tem alegação aprovada) e "turbina a
   imunidade"; manter a frase da IN 28 com as palavras exatas; confirmar se a oferta é mesmo só
   hoje; incluir #publi. Sugere uma legenda que passa.
2. **"Por que as vendas da cr_ana estão voltando neste mês?"** → 18 devoluções em 150 vendas: 7 pela
   promessa "Secar até 5KG EM 7 DIAS" (mudar o trecho); 3 esperavam "acesso vitalício", que não está
   na peça dela (sinal para a marca); 8 não têm a ver com ela (acesso, reembolso, cobrança).
3. **"Quais promessas sobre o prod_treino mais geram devolução?"** → da creator: "Secar até 5KG EM
   7 DIAS" (7, cr_ana); sinal para a marca: "acesso vitalício" (7 compradores de cr_ana e cr_bia
   acreditavam nisso sem estar nas peças; conferir o kit de divulgação); acesso e reembolso não pesam
   na creator.

## Notas para Windows

- **Executáveis do `.venv` bloqueados.** O Controle de Aplicativo do Windows pode bloquear os `.exe`
  que o uv gera em `.venv/Scripts/` (ex.: `promessa-mcp.exe`). Por isso o projeto sempre chama
  `python -m <módulo>` (`python -m pytest`, `python -m ruff`, `python -m promessa.mcp_server`).
  O script `promessa-mcp` continua no `pyproject.toml`, mas nada depende dele.
- **Acentos e símbolos no console.** O `tasks.py` passa `PYTHONUTF8=1` e `PYTHONIOENCODING=utf-8`
  aos subprocessos. Ao rodar Python fora dele, exporte as duas variáveis se a saída sair com
  caracteres trocados.
- **Fim de linha.** O `.gitattributes` fixa LF no repositório.

## Documentos

- [docs/CONTEXTO.md](docs/CONTEXTO.md): o que é, stack, modelo de dados, regras dos agentes
- [docs/PLANO.md](docs/PLANO.md): tasks em ordem
- [docs/decisoes.md](docs/decisoes.md): decisões registradas

## Status

T01 a T15 concluídas (andamento em [docs/PLANO.md](docs/PLANO.md)). Fechamento na T16.
