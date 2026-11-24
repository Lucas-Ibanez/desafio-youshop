"""Teste rápido das ferramentas de gravação (clipes de ~5 s), sem gastar cota do Gemini.

Uso: uv run python scripts/ensaio/smoke.py
Grava em ensaio/teste/: painel (página inicial, papel "Creator"), terminal (print + sleep) e o
MP4 juntado; confere duração e se cada arquivo abre; confere que a porta 8501 ficou livre.
"""

from __future__ import annotations

import sys

from common import new_run_dir, video_info
from concat import concat
from rec_panel import (
    PORT,
    Panel,
    choose_role,
    open_home,
    pause,
    port_in_use,
    recording,
    set_caption,
    webm_to_mp4,
)
from rec_terminal import record_terminal
from timer import Timer

TERMINAL_CMD = [
    sys.executable,
    "-c",
    "import time\nfor i in range(4):\n    print(f'linha {i + 1}: acentuação ok', flush=True)\n"
    "    time.sleep(1)",
]


def main() -> int:
    run = new_run_dir("teste")
    timer = Timer(run)

    with timer.segment("painel") as seg, Panel(run / "painel.log"):
        with recording(run / "painel.webm") as page:
            open_home(page)
            set_caption(page, "Teste: painel, papel Creator")
            choose_role(page, "Creator")
            pause(page, 5)
        webm_to_mp4(run / "painel.webm", run / "painel.mp4")
        seg["clip"] = "painel.mp4"
    with timer.segment("terminal") as seg:
        result = record_terminal(TERMINAL_CMD, run / "terminal.mp4", hold=1.5)
        seg["clip"], seg["metodo"] = "terminal.mp4", result["method"]
    with timer.segment("concat") as seg:
        concat([run / "painel.mp4", run / "terminal.mp4"], run / "ensaio_completo.mp4")

    print("\nSegmentos:")
    timer.summary()
    print("\nVídeos:")
    ok = True
    for name in ("painel.mp4", "terminal.mp4", "ensaio_completo.mp4"):
        info = video_info(run / name)
        ok &= info["ok"]
        print(f"  {name:<22} {'ok ' if info['ok'] else 'ERR'} {info['seconds']:>5.1f} s  "
              f"{info['size']}  {info['bytes'] // 1024} KB")  # fmt: skip
    print(f"\nGravação do terminal: {result['method']}")
    free = not port_in_use(PORT)
    print(f"Porta {PORT} livre depois do teste: {'sim' if free else 'NÃO'}")
    return 0 if ok and free and result["exit_code"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
