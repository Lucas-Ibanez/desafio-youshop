# Promessa Rastreável (MVP)

Servidor MCP com dois agentes de IA e um painel que ligam o que o produto pode prometer,
o que o creator prometeu na peça que gerou a venda e por que o comprador pediu o dinheiro de volta.
A devolução volta para quem prometeu, de forma automática e auditável.

## Requisitos

- [uv](https://docs.astral.sh/uv/) (instala o Python 3.12 do projeto, fixado em `.python-version`)
- `make` (no Windows, rode pelo Git Bash com o `make` instalado, ou use os comandos `uv run ...` do `Makefile`)
- Chave da API do Claude no `.env` (copie de `.env.example`)

## Começar

```bash
make setup   # instala as dependências (uv sync)
make test    # testes sem rede
make lint    # ruff
```

## Documentos

- [docs/CONTEXTO.md](docs/CONTEXTO.md): o que é, stack, modelo de dados, regras dos agentes
- [docs/PLANO.md](docs/PLANO.md): tasks em ordem
- [docs/decisoes.md](docs/decisoes.md): decisões registradas

## Status

T01 concluída.
