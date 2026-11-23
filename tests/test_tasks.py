"""Executor de tarefas (tasks.py)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

import tasks

ROOT = Path(__file__).resolve().parent.parent

EXPECTED = [
    "setup", "lint", "format", "test", "test-llm", "db-reset", "gold", "seed", "simulate",
    "eval-checador", "eval-classificador", "eval", "mcp", "demo", "painel",
]  # fmt: skip


def test_nomes_das_tarefas():
    assert list(tasks.TASKS) == EXPECTED


def test_help_lista_todas(capsys):
    assert tasks.main([]) == 0
    out = capsys.readouterr().out
    for name in EXPECTED:
        assert f"  {name} " in out


def test_tarefa_desconhecida_falha(capsys):
    assert tasks.main(["nao-existe"]) != 0
    assert "tarefa desconhecida" in capsys.readouterr().err


def test_sequencia_para_na_primeira_falha(monkeypatch):
    calls = []

    def fake(name, code):
        def action():
            calls.append(name)
            return code

        return tasks.Task(name, "T00", action)

    monkeypatch.setattr(
        tasks,
        "TASKS",
        {"a": fake("a", 0), "b": fake("b", 3), "c": fake("c", 0)},
    )
    assert tasks.main(["a", "b", "c"]) == 3
    assert calls == ["a", "b"]


def test_nao_implementada_sai_com_zero(capsys):
    assert tasks.main(["demo"]) == 0
    assert "ainda não implementado (T15)" in capsys.readouterr().out


@pytest.mark.parametrize("args", [["help"], []])
def test_cli_help_por_subprocesso(args):
    proc = subprocess.run(
        [sys.executable, "tasks.py", *args],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert proc.returncode == 0
    assert "eval-classificador" in proc.stdout
