"""Grava uma janela de console rodando um comando (ffmpeg gdigrab) e salva o log com horário.

Uso:
    uv run python scripts/ensaio/rec_terminal.py --out ensaio/x/demo.mp4 \
        -- uv run python tasks.py demo

Como funciona:
1. abre uma janela de console nova (conhost) com título fixo (ENSAIO_DEMO), sempre no topo;
2. o ffmpeg grava só essa janela: -f gdigrab -framerate 15 -i title=ENSAIO_DEMO;
3. a janela roda o comando, mostra a saída e grava <saida>.log com horário por linha;
4. ao terminar, a janela fica alguns segundos parada (`--hold`) e fecha; o ffmpeg para.
A janela precisa ficar visível (não minimizar). Se o gdigrab falhar, o plano B gera um vídeo que
reproduz o log no Chromium, com a legenda "reprodução do log, não é gravação do terminal".
"""

from __future__ import annotations

import argparse
import ctypes
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from common import ROOT, ffmpeg_exe, video_info

TITLE = "ENSAIO_DEMO"
FPS = 15
user32 = ctypes.windll.user32 if sys.platform == "win32" else None


# ── janela ────────────────────────────────────────────────────────────────────────────────


def find_window(title: str, timeout: float = 10.0) -> int:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        hwnd = user32.FindWindowW(None, title)
        if hwnd:
            return hwnd
        time.sleep(0.1)
    return 0


def place_window(hwnd: int, topmost: bool = True) -> None:
    """Restaura, põe no canto superior esquerdo e (opcionalmente) sempre no topo."""
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    insert_after = -1 if topmost else -2  # HWND_TOPMOST / HWND_NOTOPMOST
    flags = 0x0001 | 0x0040  # SWP_NOSIZE | SWP_SHOWWINDOW
    user32.SetWindowPos(hwnd, insert_after, 20, 20, 0, 0, flags)
    user32.SetForegroundWindow(hwnd)


# ── processo filho (roda dentro da janela) ────────────────────────────────────────────────


class _ConsoleFont(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("nFont", ctypes.c_ulong),
        ("dwFontSize", ctypes.c_short * 2),
        ("FontFamily", ctypes.c_uint),
        ("FontWeight", ctypes.c_uint),
        ("FaceName", ctypes.c_wchar * 32),
    ]


def set_console_font(height: int, face: str = "Consolas") -> None:
    """Fonte menor cabe mais linhas na tela (a saída da demo tem ~60 linhas)."""
    font = _ConsoleFont()
    font.cbSize = ctypes.sizeof(_ConsoleFont)
    font.dwFontSize[1] = height
    font.FontFamily = 54  # FF_MODERN | TMPF_TRUETYPE | TMPF_VECTOR
    font.FontWeight = 400
    font.FaceName = face
    handle = ctypes.windll.kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
    ctypes.windll.kernel32.SetCurrentConsoleFontEx(handle, False, ctypes.byref(font))


def child(args: argparse.Namespace) -> int:
    ctypes.windll.kernel32.SetConsoleTitleW(args.title)
    if args.font_size:
        set_console_font(args.font_size)
    os.system(f"mode con: cols={args.cols} lines={args.lines}")
    ctypes.windll.kernel32.SetConsoleTitleW(args.title)  # o `mode` pode trocar o título
    go, done, log_path = Path(args.go), Path(args.done), Path(args.log)
    end = time.monotonic() + 15
    while not go.exists() and time.monotonic() < end:
        time.sleep(0.05)
    env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    with log_path.open("w", encoding="utf-8") as log:

        def emit(line: str) -> None:
            print(line, flush=True)
            log.write(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} | {line}\n")
            log.flush()

        emit("$ " + " ".join(args.command))
        proc = subprocess.Popen(
            args.command,
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
        )
        for line in proc.stdout:
            emit(line.rstrip("\n"))
        code = proc.wait()
        emit(f"[saída {code}]")
    time.sleep(args.hold)
    done.write_text(str(code), encoding="utf-8")
    return code


# ── gravação ──────────────────────────────────────────────────────────────────────────────


def record_terminal(
    command: list[str],
    out: str | Path,
    *,
    title: str = TITLE,
    cols: int = 110,
    lines: int = 32,
    hold: float = 2.0,
    font_size: int = 0,
    timeout: float = 600.0,
    fallback: bool = True,
) -> dict:
    """Roda `command` numa janela nova e grava a janela. Devolve código, método, vídeo e log."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    log_path = out.with_suffix(".log")
    go, done = out.with_suffix(".go"), out.with_suffix(".done")
    for f in (go, done):
        f.unlink(missing_ok=True)
    # conhost.exe força a janela clássica de console, mesmo com o Windows Terminal como padrão
    child_cmd = [
        "conhost.exe", sys.executable, str(Path(__file__).resolve()), "--child",
        "--title", title, "--log", str(log_path), "--go", str(go), "--done", str(done),
        "--cols", str(cols), "--lines", str(lines), "--hold", str(hold),
        "--font-size", str(font_size), "--", *command,
    ]  # fmt: skip
    win = subprocess.Popen(child_cmd, cwd=ROOT, creationflags=subprocess.CREATE_NEW_CONSOLE)
    hwnd = find_window(title)
    method, ffmpeg, ff_log = "gdigrab", None, out.with_suffix(".ffmpeg.txt")
    if hwnd:
        place_window(hwnd)
        time.sleep(0.5)  # o `mode con` redimensiona a janela
        ff_cmd = [
            ffmpeg_exe(), "-hide_banner", "-y", "-f", "gdigrab", "-framerate", str(FPS),
            "-draw_mouse", "0", "-i", f"title={title}",
            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-preset", "veryfast",
            "-pix_fmt", "yuv420p", str(out),
        ]  # fmt: skip
        with ff_log.open("w", encoding="utf-8") as ff_err:
            ffmpeg = subprocess.Popen(ff_cmd, stdin=subprocess.PIPE, stderr=ff_err)
        time.sleep(1.0)
        if ffmpeg.poll() is not None:
            ffmpeg, method = None, "plano_b"
    else:
        method = "plano_b"
    go.touch()

    end = time.monotonic() + timeout
    while not done.exists() and win.poll() is None and time.monotonic() < end:
        time.sleep(0.2)
    code = int(done.read_text(encoding="utf-8")) if done.exists() else -1
    if ffmpeg is not None:
        try:
            ffmpeg.communicate(b"q", timeout=20)
        except subprocess.TimeoutExpired:
            ffmpeg.kill()
    try:
        win.wait(timeout=10)
    except subprocess.TimeoutExpired:
        win.kill()
    for f in (go, done):
        f.unlink(missing_ok=True)

    info = video_info(out) if out.exists() else {"ok": False}
    if method == "gdigrab" and not info["ok"]:
        method = "plano_b"
    if method == "plano_b" and fallback:
        replay_log(log_path, out)
        info = video_info(out)
    return {"exit_code": code, "method": method, "video": info, "log": str(log_path)}


# ── plano B: vídeo que reproduz o log ─────────────────────────────────────────────────────


def read_log(log_path: Path) -> list[tuple[float, str]]:
    """Linhas do log com o tempo (s) desde a primeira."""
    rows = []
    with log_path.open(encoding="utf-8") as f:
        for raw in f:
            stamp, _, text = raw.rstrip("\n").partition(" | ")
            t = datetime.strptime(stamp, "%H:%M:%S.%f")
            rows.append((t, text))
    if not rows:
        return []
    t0 = rows[0][0]
    return [((t - t0).total_seconds(), text) for t, text in rows]


def replay_log(log_path: str | Path, out: str | Path, hold: float = 2.0) -> Path:
    """Plano B: reproduz o log no Chromium, no ritmo original, e grava como MP4."""
    from rec_panel import recording, set_caption, webm_to_mp4

    rows = read_log(Path(log_path))
    out = Path(out)
    webm = out.with_suffix(".webm")
    page_html = (
        "<html><body style='margin:0;background:#0c0c0c'>"
        "<pre id='t' style='color:#ccc;font:15px Consolas,monospace;padding:48px 16px 0;"
        "white-space:pre-wrap'></pre></body></html>"
    )
    with recording(webm) as page:
        page.set_content(page_html)
        set_caption(page, "reprodução do log, não é gravação do terminal")
        start = time.monotonic()
        for t, text in rows:
            wait = t - (time.monotonic() - start)
            if wait > 0:
                page.wait_for_timeout(wait * 1000)
            page.evaluate(
                "line => { const t = document.getElementById('t'); t.textContent += line + '\\n';"
                " window.scrollTo(0, document.body.scrollHeight); }",
                text,
            )
        page.wait_for_timeout(hold * 1000)
    webm_to_mp4(webm, out)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--go", help=argparse.SUPPRESS)
    parser.add_argument("--done", help=argparse.SUPPRESS)
    parser.add_argument("--log", help=argparse.SUPPRESS)
    parser.add_argument("--out", help="MP4 de saída (o log fica ao lado, .log)")
    parser.add_argument("--title", default=TITLE)
    parser.add_argument("--cols", type=int, default=110)
    parser.add_argument("--lines", type=int, default=32)
    parser.add_argument("--hold", type=float, default=2.0)
    parser.add_argument("--font-size", type=int, default=0, help="altura da fonte (0 = padrão)")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("informe o comando depois de --")
    if args.child:
        return child(args)
    if not args.out:
        parser.error("--out é obrigatório")
    result = record_terminal(
        args.command,
        args.out,
        title=args.title,
        cols=args.cols,
        lines=args.lines,
        hold=args.hold,
        font_size=args.font_size,
    )
    print(result)
    return 0 if result["video"]["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
