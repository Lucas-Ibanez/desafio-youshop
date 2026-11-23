"""Casamento de termos e padrões das regras sobre texto (sintaxe da D20).

Termo: palavra ou frase inteira; terminado em `*`, prefixo. Espaços do termo casam com
qualquer sequência de espaços. Padrão: regex sobre o texto de `match_text` (normalizado e com
grafia disfarçada desfeita). Como `match_text` preserva o comprimento, os `span` devolvidos
valem para o texto original.
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from functools import lru_cache

from promessa.rules.normalize import match_text


@lru_cache(maxsize=2048)
def term_regex(term: str) -> re.Pattern[str]:
    prefix = term.endswith("*")
    words = [re.escape(w) for w in term.removesuffix("*").split()]
    tail = "" if prefix else r"(?!\w)"
    return re.compile(r"(?<!\w)" + r"\s+".join(words) + tail)


@dataclass(frozen=True)
class Hit:
    start: int
    end: int
    matched: str  # termo ou padrão que casou


def find_hits(
    text: str,
    termos: Iterable[str] = (),
    padroes: Iterable[str] = (),
    junto_de: Sequence[str] = (),
    *,
    prepared: str | None = None,
) -> list[Hit]:
    """Casamentos de `termos` e `padroes` em `text`, ordenados por posição.

    Com `junto_de`, só vale se algum desses termos também aparecer no texto (o chamador passa
    o trecho). `prepared` evita recalcular `match_text(text)`.
    """
    norm = prepared if prepared is not None else match_text(text)
    if junto_de and not any(term_regex(t).search(norm) for t in junto_de):
        return []
    hits = [Hit(m.start(), m.end(), t) for t in termos for m in term_regex(t).finditer(norm)]
    hits += [Hit(m.start(), m.end(), p) for p in padroes for m in re.finditer(p, norm)]
    return sorted(hits, key=lambda h: (h.start, -h.end))
