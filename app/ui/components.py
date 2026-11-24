"""Componentes visuais do Vincula (docs/BRAND.md, seção 5).

Só formatam o que os serviços devolvem: nenhuma regra de negócio aqui. Todo texto que vem de
usuário (peça, nomes, trechos) passa por `html.escape` antes de ir para `st.html`.
"""

from __future__ import annotations

from html import escape

import streamlit as st

from ui.labels import DECISION, label

# O fio (5.1): ponto cheio (prometido) → traço → ponto vazado (desfecho). O `st.html` remove
# <svg> embutido (conferido no DOM), então o símbolo é servido como arquivo estático.
FIO_IMG = '<img src="/app/static/fio.svg" width="40" height="16" alt="" aria-hidden="true">'


def wordmark_html() -> str:
    return (
        f'<div class="vc-wordmark">{FIO_IMG}<span class="vc-wordmark__nome">vincula</span></div>'
        '<div class="vc-wordmark__desc">promessa rastreável</div>'
    )


def dito(text: str) -> str:
    """O que alguém disse: Newsreader itálico entre aspas curvas."""
    return f'<span class="vc-dito">“{escape(text)}”</span>'


def ident(text: str) -> str:
    """Identificador que se copia ou confere (rule_key, versão, id do link)."""
    return f'<span class="vc-id">{escape(str(text))}</span>'


def chip(value: str, mapping: dict[str, str] = DECISION) -> str:
    raw = getattr(value, "value", value)
    return f'<span class="vc-chip vc-chip--{escape(str(raw))}">{escape(label(mapping, raw))}</span>'


def page_header(title: str, subtitle: str, meta: str | None = None, *, container=None) -> None:
    """Título (display), linha de apoio (corpo, grafite) e metadado opcional (pequeno).

    `meta` já vem em HTML (pode ter `ident(...)`); quem chama escapa os textos de usuário.
    """
    parts = [
        '<header class="vc-header">',
        f'<h1 class="vc-h1">{escape(title)}</h1>',
        f'<p class="vc-header__apoio">{escape(subtitle)}</p>',
    ]
    if meta:
        parts.append(f'<p class="vc-header__meta">{meta}</p>')
    parts.append("</header>")
    (container or st).html("".join(parts))
