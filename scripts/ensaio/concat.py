"""Junta os clipes de um run em um MP4 único, na ordem do roteiro.

Uso:
    uv run python scripts/ensaio/concat.py <run_dir>                 # ordem de segmentos.json
    uv run python scripts/ensaio/concat.py <run_dir> a.mp4 b.webm    # ordem explícita

Cada clipe é normalizado para 1280x720, 15 fps, H.264 (os do painel são webm 1280x720, os do
terminal têm o tamanho da janela) e depois concatenado sem nova codificação.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from common import ffmpeg_exe, video_info
from timer import load

W, H, FPS = 1280, 720, 15


def normalize(src: Path, dst: Path) -> None:
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
        f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,fps={FPS},format=yuv420p"
    )
    cmd = [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-an"]
    cmd += ["-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", str(dst)]
    subprocess.run(cmd, check=True)


def concat(clips: list[Path], out: Path) -> Path:
    if not clips:
        raise SystemExit("nenhum clipe para juntar")
    work = out.parent / "_norm"
    work.mkdir(exist_ok=True)
    parts = []
    for i, clip in enumerate(clips):
        part = work / f"{i:02d}_{clip.stem}.mp4"
        normalize(clip, part)
        parts.append(part)
    listing = work / "lista.txt"
    with listing.open("w", encoding="utf-8") as f:
        for part in parts:
            f.write(f"file '{part.resolve().as_posix()}'\n")
    cmd = [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0"]
    cmd += ["-i", str(listing), "-c", "copy", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    for part in parts:
        part.unlink()
    listing.unlink()
    work.rmdir()
    return out


def clips_from_segments(run_dir: Path) -> list[Path]:
    return [run_dir / s["clip"] for s in load(run_dir)["segmentos"] if s.get("clip")]


def main(argv: list[str]) -> int:
    run_dir = Path(argv[0])
    clips = [run_dir / c for c in argv[1:]] or clips_from_segments(run_dir)
    out = concat(clips, run_dir / "ensaio_completo.mp4")
    print(video_info(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
