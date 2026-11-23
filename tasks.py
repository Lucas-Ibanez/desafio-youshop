"""Executor de tarefas do projeto (substitui o Makefile; decisão D11).

Uso: uv run python tasks.py <tarefa> [<tarefa> ...]
Executa as tarefas em sequência e para na primeira que falhar.
Sem argumentos, mostra a ajuda.

Só biblioteca padrão. Ferramentas Python sempre via `sys.executable -m <módulo>`,
nunca pelos executáveis do .venv (o Windows pode bloqueá-los; decisão D10).
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def run(*args: str) -> int:
    """Roda um comando na raiz do projeto e devolve o código de saída.

    O eco do comando vai para stderr: na tarefa `mcp`, o stdout é o canal JSON-RPC."""
    print(f"$ {' '.join(args)}", file=sys.stderr, flush=True)
    return subprocess.call(list(args), cwd=ROOT, env=_env())


def py(*args: str) -> int:
    """Roda `python -m ...` com o mesmo interpretador deste processo."""
    return run(sys.executable, "-m", *args)


def not_implemented(task_id: str) -> Callable[[], int]:
    def action() -> int:
        print(f"ainda não implementado ({task_id})")
        return 0

    return action


def setup() -> int:
    return run("uv", "sync")


def lint() -> int:
    return py("ruff", "check", ".") or py("ruff", "format", "--check", ".")


def format_() -> int:
    return py("ruff", "format", ".") or py("ruff", "check", "--fix", ".")


def test() -> int:
    return py("pytest", "-q")


def test_llm() -> int:
    code = py("pytest", "-q", "-m", "llm")
    # 5 = nenhum teste coletado; aceitável enquanto não há testes com o modelo.
    return 0 if code == 5 else code


def db_reset() -> int:
    # Apaga e recria o banco de PROMESSA_DB_URL com tabelas e triggers (T02).
    return py("promessa.db.session", "--reset")


def gold() -> int:
    # Importa, anonimiza e confere os gabaritos; gera splits.json (T04).
    return run(sys.executable, "scripts/import_gold.py")


def mcp() -> int:
    return py("promessa.mcp_server")


@dataclass(frozen=True)
class Task:
    description: str
    plan_task: str
    action: Callable[[], int]


TASKS: dict[str, Task] = {
    "setup": Task("instala as dependências (uv sync)", "T01", setup),
    "lint": Task("ruff check e ruff format --check", "T01", lint),
    "format": Task("formata o código com ruff", "T01", format_),
    "test": Task("pytest sem modelo (sem rede)", "T01", test),
    "test-llm": Task("pytest só dos testes marcados com llm", "T01", test_llm),
    "db-reset": Task("apaga e recria var/promessa.db", "T02", db_reset),
    "gold": Task("importa e confere os gabaritos (scripts/import_gold.py)", "T04", gold),
    "seed": Task("marcas, produtos, fichas v1 e creators", "T05", not_implemented("T05")),
    "simulate": Task("peças, links, vendas e devoluções sintéticas", "T13", not_implemented("T13")),
    "eval-checador": Task("Teste 1 do checador (H2)", "T08", not_implemented("T08")),
    "eval-classificador": Task("Teste 1 do classificador (H1)", "T12", not_implemented("T12")),
    "eval": Task("Teste 1 dos dois agentes", "T08, T12", not_implemented("T08 e T12")),
    "mcp": Task("sobe o servidor MCP em stdio", "T01", mcp),
    "demo": Task("exemplo do guia de ponta a ponta via MCP", "T15", not_implemented("T15")),
    "painel": Task(
        "painel Streamlit (python -m streamlit run app/painel.py)", "T14", not_implemented("T14")
    ),
}


def help_() -> int:
    print("Uso: uv run python tasks.py <tarefa> [<tarefa> ...]\n")
    print("Tarefas:")
    width = max(len(name) for name in TASKS)
    for name, task in TASKS.items():
        print(f"  {name:<{width}}  {task.description} [{task.plan_task}]")
    print(f"  {'help':<{width}}  mostra esta ajuda")
    return 0


def main(argv: list[str] | None = None) -> int:
    names = sys.argv[1:] if argv is None else argv
    if not names or names == ["help"]:
        return help_()
    unknown = [n for n in names if n not in TASKS and n != "help"]
    if unknown:
        print(f"tarefa desconhecida: {', '.join(unknown)}", file=sys.stderr)
        help_()
        return 2
    for name in names:
        code = help_() if name == "help" else TASKS[name].action()
        if code != 0:
            print(f"tarefa '{name}' falhou (código {code})", file=sys.stderr)
            return code
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")  # console do Windows usa cp1252 por padrão
    sys.exit(main())
