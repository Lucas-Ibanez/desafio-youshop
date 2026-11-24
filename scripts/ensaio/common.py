"""Partes comuns das ferramentas de ensaio: caminhos, ffmpeg e duração de vídeo.

O ffmpeg vem do pacote imageio-ffmpeg (dependência de desenvolvimento): não há ffmpeg no sistema
e assim todos usam o mesmo binário, com gdigrab e libx264.
"""

from __future__ import annotations

import re
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENSAIO_DIR = ROOT / "ensaio"  # saídas (fora do git)


def ffmpeg_exe() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def new_run_dir(name: str | None = None) -> Path:
    """Pasta de um run: ensaio/<nome ou data-hora>/."""
    path = ENSAIO_DIR / (name or datetime.now().strftime("%Y%m%d-%H%M%S"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def video_info(path: str | Path) -> dict:
    """Decodifica o vídeo inteiro com ffmpeg (prova que abre) e devolve duração e tamanho.

    O imageio-ffmpeg não traz ffprobe; `ffmpeg -i x -f null -` cumpre o mesmo papel.
    """
    proc = subprocess.run(
        [ffmpeg_exe(), "-hide_banner", "-i", str(path), "-f", "null", "-"],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    err = proc.stderr
    size = re.search(r"Video: .*?, (\d{2,5})x(\d{2,5})", err)
    times = re.findall(r"time=(\d+):(\d+):(\d+\.\d+)", err)
    seconds = 0.0
    if times:
        h, m, s = times[-1]
        seconds = int(h) * 3600 + int(m) * 60 + float(s)
    return {
        "path": str(path),
        "ok": proc.returncode == 0 and seconds > 0,
        "seconds": round(seconds, 2),
        "size": f"{size.group(1)}x{size.group(2)}" if size else None,
        "bytes": Path(path).stat().st_size if Path(path).exists() else 0,
    }
