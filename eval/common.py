"""Partes comuns dos relatórios do Teste 1: rodadas versionadas e formatação."""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def next_run(history: list[dict], fp: dict[str, str], note: str | None) -> dict:
    """v1 na primeira rodada; mesma versão se nada mudou; senão a próxima, com o que mudou."""
    if not history:
        return {"versao": "v1", "mudancas": note or "primeira rodada"}
    last = history[-1]
    if last["fingerprint"] == fp:
        return {"versao": last["versao"], "mudancas": last["mudancas"]}
    changed = sorted(
        k for k in fp.keys() | last["fingerprint"].keys() if fp.get(k) != last["fingerprint"].get(k)
    )
    text = "mudou: " + ", ".join(changed) + (f". {note}" if note else "")
    return {"versao": f"v{int(last['versao'][1:]) + 1}", "mudancas": text}


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def pct(v: float | None) -> str:
    return "—" if v is None else f"{v:.0%}"


def num(v: float | None) -> str:
    return "—" if v is None else f"{v:.2f}"


def ok(value: float | None, goal: float) -> str:
    return "—" if value is None else ("✅" if value >= goal - 1e-9 else "❌")
