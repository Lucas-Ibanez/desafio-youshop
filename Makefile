.PHONY: setup lint format test test-llm db-reset gold seed simulate eval-checador \
	eval-classificador eval mcp demo painel

setup:
	uv sync

lint:
	uv run ruff check . && uv run ruff format --check .

format:
	uv run ruff format . && uv run ruff check --fix .

test:
	uv run pytest -q

test-llm:
	uv run pytest -q -m llm

# Por enquanto só garante var/ vazio; a criação das tabelas entra na T02.
db-reset:
	uv run python -c "import pathlib; d = pathlib.Path('var'); d.mkdir(exist_ok=True); (d / 'promessa.db').unlink(missing_ok=True)"

gold:
	@echo "ainda não implementado (T04)"

seed:
	@echo "ainda não implementado (T05)"

simulate:
	@echo "ainda não implementado (T13)"

eval-checador:
	@echo "ainda não implementado (T08)"

eval-classificador:
	@echo "ainda não implementado (T12)"

eval:
	@echo "ainda não implementado (T08 e T12)"

mcp:
	uv run promessa-mcp

demo:
	@echo "ainda não implementado (T15)"

painel:
	@echo "ainda não implementado (T14)"
