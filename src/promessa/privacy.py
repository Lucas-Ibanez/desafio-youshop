"""Remoção de dados pessoais do motivo do comprador (CONTEXTO 15, LGPD).

`scrub` roda antes de gravar e antes de enviar ao modelo: e-mail → [EMAIL], CPF/CNPJ → [CPF],
telefone → [TELEFONE], cartão → [CARTAO]. Valores em reais ("R$ 1.297") e datas ficam.
"""

import re

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_CARD = re.compile(r"(?<![\d.,])(?:\d{4}[ -]?){3}\d{1,7}(?![\d,])")  # 13 a 19 dígitos
_CNPJ = re.compile(r"(?<![\d.])\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}(?![\d])")
_CPF = re.compile(r"(?<![\d.])\d{3}\.\d{3}\.\d{3}-?\d{2}(?![\d])")
_PHONE = re.compile(r"(?<![\d])(?:\+?55[\s.-]?)?\(?\d{2}\)?[\s.-]?9?\d{4}[\s.-]?\d{4}(?![\d])")
_ELEVEN = re.compile(r"(?<![\d.,])\d{11}(?![\d,])")
_CPF_HINT = re.compile(r"cpf\W{0,3}$", re.IGNORECASE)


def _luhn(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2:
            n = n * 2 - 9 if n > 4 else n * 2
        total += n
    return total % 10 == 0


def _card(m: re.Match[str]) -> str:
    digits = re.sub(r"\D", "", m.group())
    return "[CARTAO]" if 13 <= len(digits) <= 19 and _luhn(digits) else m.group()


def _eleven(text: str) -> str:
    """11 dígitos seguidos: CPF se vier depois de "cpf", senão telefone."""

    def repl(m: re.Match[str]) -> str:
        before = text[max(0, m.start() - 8) : m.start()]
        return "[CPF]" if _CPF_HINT.search(before) else "[TELEFONE]"

    return _ELEVEN.sub(repl, text)


def scrub(text: str | None) -> str:
    """Texto sem e-mail, CPF/CNPJ, telefone nem número de cartão."""
    if not text:
        return text or ""
    text = _EMAIL.sub("[EMAIL]", text)
    text = _CARD.sub(_card, text)
    text = _CNPJ.sub("[CPF]", text)
    text = _CPF.sub("[CPF]", text)
    text = _eleven(text)
    text = _PHONE.sub("[TELEFONE]", text)
    return text


def preview(text: str | None, limit: int = 80) -> str:
    """Até `limit` caracteres do texto já limpo (para log; CONTEXTO 15)."""
    clean = scrub(text)
    return clean if len(clean) <= limit else clean[: limit - 1] + "…"
