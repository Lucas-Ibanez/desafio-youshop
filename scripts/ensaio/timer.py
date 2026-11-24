"""Cronômetro por segmento do ensaio. Grava <run>/segmentos.json a cada segmento fechado.

Uso:
    timer = Timer(run_dir)
    with timer.segment("passo_2_checador") as seg:
        ...
        seg["clip"] = "passo_2.mp4"   # opcional: o concat usa esta ordem
    timer.summary()
"""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


class Timer:
    def __init__(self, run_dir: str | Path):
        self.path = Path(run_dir) / "segmentos.json"
        self.segments: list[dict] = []

    @contextmanager
    def segment(self, name: str):
        seg: dict = {"nome": name, "inicio": datetime.now().isoformat(timespec="seconds")}
        start = time.perf_counter()
        try:
            yield seg
        finally:
            seg["fim"] = datetime.now().isoformat(timespec="seconds")
            seg["duracao_s"] = round(time.perf_counter() - start, 1)
            self.segments.append(seg)
            self.save()

    def total(self) -> float:
        return round(sum(s["duracao_s"] for s in self.segments), 1)

    def save(self) -> None:
        data = {"total_s": self.total(), "segmentos": self.segments}
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)

    def summary(self) -> str:
        lines = [f"  {s['nome']:<32} {s['duracao_s']:>6.1f} s" for s in self.segments]
        lines.append(f"  {'total':<32} {self.total():>6.1f} s")
        text = "\n".join(lines)
        print(text)
        return text


def load(run_dir: str | Path) -> dict:
    with (Path(run_dir) / "segmentos.json").open(encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    import sys

    data = load(sys.argv[1])
    for s in data["segmentos"]:
        print(f"{s['nome']:<32} {s['duracao_s']:>6.1f} s  {s.get('clip', '')}")
    print(f"{'total':<32} {data['total_s']:>6.1f} s")
