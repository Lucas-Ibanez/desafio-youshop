# Promessa Rastreável (MVP)

Servidor MCP com dois agentes de IA e um painel que ligam o que o produto pode prometer,
o que o creator prometeu na peça que gerou a venda e por que o comprador pediu o dinheiro de volta.
A devolução volta para quem prometeu, de forma automática e auditável.

## Requisitos

- [uv](https://docs.astral.sh/uv/) (instala o Python 3.12 do projeto, fixado em `.python-version`)
- Chave da API do Claude no `.env` (copie de `.env.example`)

Não precisa de `make`: os comandos ficam em `tasks.py`, em Python puro.

## Começar

```bash
cp .env.example .env                       # depois preencha ANTHROPIC_API_KEY
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
| `test` / `test-llm` | pytest sem modelo / só testes que chamam o Claude |
| `db-reset` | apaga e recria `var/promessa.db` |
| `mcp` | sobe o servidor MCP em stdio |
| `gold`, `seed`, `simulate`, `eval-checador`, `eval-classificador`, `eval`, `demo`, `painel` | entram nas próximas tasks do plano |

Servidor MCP: `uv run python -m promessa.mcp_server` (o mesmo que `tasks.py mcp`).

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

T01 concluída.
