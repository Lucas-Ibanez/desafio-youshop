"""Normalização de texto que preserva posições (CONTEXTO, seção 11.2).

Toda função aqui devolve texto com o **mesmo comprimento** da entrada, para que um casamento
no texto normalizado aponte o mesmo `span` no texto original.

Limitação: o texto deve chegar em NFC (acentos compostos). Um acento já decomposto
(letra + marca combinante) fica como está, para não mudar o comprimento.
"""

import re
import unicodedata
from collections.abc import Mapping

_TOKEN = re.compile(r"\S+")


def _fold_char(ch: str) -> str:
    """Minúscula e sem acento, sempre com 1 caractere (se não der, devolve o original)."""
    lower = ch.lower()
    if len(lower) != 1:
        lower = ch
    base = "".join(c for c in unicodedata.normalize("NFD", lower) if not unicodedata.combining(c))
    return base if len(base) == 1 else lower


def normalize(text: str) -> str:
    """Minúsculas e sem acento, caractere a caractere. `len(normalize(t)) == len(t)`."""
    return "".join(_fold_char(ch) for ch in text)


def _default_map() -> Mapping[str, str]:
    from promessa.rules.loader import load_rules  # import tardio: o loader usa normalize()

    return load_rules().normalization_map


def deleet(token: str, mapping: Mapping[str, str] | None = None) -> str:
    """Desfaz grafia disfarçada num token, sem mudar o comprimento.

    Só troca quando o token tem um caractere do mapa **entre duas letras** (sinal de disfarce);
    aí troca todos os caracteres do mapa no token. Números com unidade (`10k`, `5kg`),
    nomes com número no fim (`b6`, `omega3`), moeda (`r$`) e menções (`@perfil`) ficam iguais.
    Sempre devolve em minúsculas e sem acento.
    """
    mapping = _default_map() if mapping is None else mapping
    folded = normalize(token)
    disguised = any(
        ch in mapping and folded[i - 1].isalpha() and folded[i + 1].isalpha()
        for i, ch in enumerate(folded)
        if 0 < i < len(folded) - 1
    )
    if not disguised:
        return folded
    return "".join(mapping.get(ch, ch) for ch in folded)


def match_text(text: str, mapping: Mapping[str, str] | None = None) -> str:
    """Texto pronto para casar regras: `normalize` + `deleet` em cada token. Mesmo comprimento."""
    mapping = _default_map() if mapping is None else mapping
    folded = normalize(text)
    return _TOKEN.sub(lambda m: deleet(m.group(), mapping), folded)
