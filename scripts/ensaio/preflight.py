"""Confere o ambiente antes do ensaio. Não imprime chaves: só diz se estão definidas.

Uso: uv run python scripts/ensaio/preflight.py
Sai com código 1 se algo impede o ensaio (banco ausente, porta 8501 ocupada, ffmpeg ou Chromium
ausentes).
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from common import ROOT, ffmpeg_exe
from rec_panel import PORT, port_in_use

DAILY_LIMIT = 500  # plano gratuito, por modelo (README, Limites do MVP)


def quota_day_start() -> datetime:
    """A cota diária do Gemini reinicia à meia-noite do horário do Pacífico."""
    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("America/Los_Angeles")
    except Exception:  # noqa: BLE001  (sem base de fusos: usa UTC-8)
        tz = timezone(timedelta(hours=-8))
    now = datetime.now(tz)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def quota_estimate(cache_dir: Path) -> tuple[int, datetime]:
    """Respostas novas gravadas no cache desde o reinício da cota (o projeto não registra cota).

    Cada resposta nova do modelo vira um arquivo no cache; tentativas com erro não entram, então
    o número real pode ser um pouco maior.
    """
    start = quota_day_start()
    ts = start.timestamp()
    count = sum(1 for f in cache_dir.glob("*/*.json") if f.stat().st_mtime >= ts)
    return count, start


def db_path(url: str) -> Path | None:
    if not url.startswith("sqlite:///"):
        return None
    path = Path(url.removeprefix("sqlite:///"))
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    from promessa.config import get_settings, has_api_key

    problems: list[str] = []

    def line(ok: bool | None, label: str, detail: str = "") -> None:
        mark = {True: "ok ", False: "ERR", None: " - "}[ok]
        print(f"[{mark}] {label}{': ' + detail if detail else ''}")

    status = subprocess.run(
        ["git", "status", "--short"], cwd=ROOT, capture_output=True, encoding="utf-8"
    ).stdout.strip()
    head = subprocess.run(
        ["git", "log", "-1", "--format=%h %s"], cwd=ROOT, capture_output=True, encoding="utf-8"
    ).stdout.strip()
    line(
        True if not status else None,
        "git",
        f"limpo · {head}" if not status else f"alterações:\n{status}",
    )

    settings = get_settings()
    path = db_path(settings.promessa_db_url)
    if path and path.exists():
        with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as con:
            sales = con.execute("select count(*) from sale").fetchone()[0]
            refunds = con.execute("select count(*) from refund_event").fetchone()[0]
        detail = f"{path.relative_to(ROOT)} · {sales} vendas · {refunds} devoluções"
        line(sales > 0, "banco", detail)
        if not sales:
            problems.append("banco sem vendas: rode db-reset seed simulate")
    else:
        line(False, "banco", f"{path} não existe: rode db-reset seed simulate")
        problems.append("banco ausente")

    line((ROOT / ".env").exists(), ".env presente", "sim" if (ROOT / ".env").exists() else "não")
    line(None, "GEMINI_API_KEY definida", "sim" if has_api_key(settings) else "não")

    busy = port_in_use(PORT)
    line(not busy, f"porta {PORT}", "ocupada (feche o painel aberto)" if busy else "livre")
    if busy:
        problems.append(f"porta {PORT} ocupada")

    try:
        ff = ffmpeg_exe()
        line(True, "ffmpeg", Path(ff).name)
    except Exception as e:  # noqa: BLE001
        line(False, "ffmpeg", str(e))
        problems.append("ffmpeg ausente")

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            exe = Path(p.chromium.executable_path)
        line(exe.exists(), "Chromium (Playwright)", "instalado" if exe.exists() else "ausente")
        if not exe.exists():
            problems.append("rode: uv run python -m playwright install chromium")
    except Exception as e:  # noqa: BLE001
        line(False, "Chromium (Playwright)", str(e))
        problems.append("Playwright indisponível")

    cache_dir = Path(settings.llm_cache_dir)
    cache_dir = cache_dir if cache_dir.is_absolute() else ROOT / cache_dir
    used, since = quota_estimate(cache_dir)
    line(
        None,
        "cota do Gemini (estimativa)",
        f"≈ {used} de {DAILY_LIMIT} chamadas desde {since:%d/%m %H:%M} (Pacífico); "
        "conta as respostas novas no cache, não as tentativas com erro",
    )

    if problems:
        print("\nImpede o ensaio: " + "; ".join(problems))
        return 1
    print("\nPronto para o ensaio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
