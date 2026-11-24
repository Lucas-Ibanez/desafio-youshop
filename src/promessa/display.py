"""Forma de exibição para pessoas (pt-BR): números com vírgula e rótulos de valores internos.

Os valores gravados (enums, texto normalizado das promessas) não mudam: relatórios agrupam por
eles e o MCP os devolve. Aqui só se decide como aparecem na tela e nos textos.
"""

from __future__ import annotations

import re

# palavras do vocabulário das condições da oferta que a normalização deixa sem acento
ACCENTED = {"vitalicio": "vitalício", "bonus": "bônus", "unica": "única"}

ACCESS_TYPE = {
    "vitalicio": "vitalício",
    "prazo": "por prazo",
    "assinatura": "por assinatura",
    "nao_aplica": "não se aplica",
}
RECURRENCE = {"unica": "pagamento único", "mensal": "mensal", "anual": "anual"}
PROMISE_TYPE = {
    "condicao_oferta": "condição da oferta",
    "resultado": "resultado",
    "alegacao": "alegação",
}
APPROVAL = {"registrada": "registrada", "em_revisao": "em revisão"}
# na visão do creator, a causa "fraude" é do comprador, não dele (mesmo termo da explicação)
CAUSE_FOR_CREATOR = {"fraude": "Cobrança não reconhecida"}


def label(mapping: dict[str, str], value) -> str:
    """Rótulo do valor interno; se não houver, o próprio valor com espaços."""
    raw = getattr(value, "value", value)
    if raw is None:
        return "—"
    return mapping.get(str(raw), str(raw).replace("_", " "))


def promise_label(normalized: str) -> str:
    """ "acesso vitalicio" → "acesso vitalício" (só o vocabulário das condições da oferta)."""
    return re.sub(r"[a-zç]+", lambda m: ACCENTED.get(m.group(0), m.group(0)), normalized)


def pct(value: float | None, digits: int = 1) -> str:
    """0.047 → "4,7%"."""
    if value is None:
        return "—"
    return f"{value * 100:.{digits}f}%".replace(".", ",")


def num(value: float | None, digits: int = 2) -> str:
    """0.37 → "0,37"."""
    if value is None:
        return "—"
    return f"{value:.{digits}f}".replace(".", ",")


def money(cents: int) -> str:
    """990 → "R$ 9,90"."""
    return f"R$ {cents / 100:.2f}".replace(".", ",")


def join_pt(items: list[str]) -> str:
    """["a", "b", "c"] → "a, b e c"."""
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " e " + items[-1]
