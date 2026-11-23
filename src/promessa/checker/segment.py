"""Divide a peça em trechos (frases e linhas), com posição no texto original (CONTEXTO 11.2)."""

import re
from dataclasses import dataclass

# Fim de frase: . ! ? … (repetidos) seguidos de espaço; ou quebra de linha.
_BOUNDARY = re.compile(r"(?<=[.!?…])\s+|\n+")


@dataclass(frozen=True)
class Segment:
    start: int
    end: int
    text: str


def segment(text: str) -> list[Segment]:
    """Trechos sem espaços nas pontas. `text[s.start:s.end] == s.text` sempre."""
    segments: list[Segment] = []
    pos = 0
    for m in [*_BOUNDARY.finditer(text), None]:
        end = m.start() if m else len(text)
        chunk = text[pos:end]
        stripped = chunk.strip()
        if stripped:
            start = pos + (len(chunk) - len(chunk.lstrip()))
            segments.append(Segment(start, start + len(stripped), stripped))
        if m:
            pos = m.end()
    return segments
