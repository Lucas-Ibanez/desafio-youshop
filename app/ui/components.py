"""Componentes visuais do Vincula (docs/BRAND.md, seção 5).

Só formatam o que os serviços devolvem: nenhuma regra de negócio aqui. Todo texto que vem de
usuário (peça, nomes, trechos) passa por `html.escape` antes de ir para `st.html`.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import streamlit as st

from ui.labels import APPROVAL, DECISION, SEVERITY, label, origin

TZ = ZoneInfo("America/Sao_Paulo")

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


# --- Formatação ----------------------------------------------------------------------------


def curly(text: str) -> str:
    """Aspas retas viram curvas (3.3): 'Troque por "x".' → 'Troque por “x”.'."""
    return re.sub(r'"([^"]*)"', r"“\1”", text)


def when(moment: datetime | None = None) -> str:
    """Data no formato do guia (3.3): "24/11 às 10:42", horário de São Paulo."""
    moment = (moment or datetime.now(TZ)).astimezone(TZ)
    return f"{moment:%d/%m} às {moment:%H:%M}"


# --- Texto checado com marca-texto (5.3) ---------------------------------------------------


def peca_marcada(text: str, findings: list[dict], *, is_new: bool = False) -> str:
    """Texto inteiro da peça com cada trecho pintado na cor da decisão mais grave que o cobre.

    Os trechos são numerados na ordem em que aparecem (`--i`), para a animação pintar da
    esquerda para a direita (6). Só formata: os trechos e as decisões vêm do checador.
    """
    output_at: list[str | None] = [None] * len(text)
    level = [0] * len(text)
    for f in findings:
        start, end = f["span"]
        sev = SEVERITY.get(f["output"], 0)
        for i in range(max(0, start), min(len(text), end)):
            if sev > level[i]:
                level[i], output_at[i] = sev, f["output"]
    parts, i, n = [], 0, 0
    while i < len(text):
        j = i
        while j < len(text) and output_at[j] == output_at[i]:
            j += 1
        chunk = escape(text[i:j]).replace("\n", "<br>")
        out = output_at[i]
        if out:
            parts.append(f'<mark class="vc-marca vc-marca--{out}" style="--i:{n}">{chunk}</mark>')
            n += 1
        else:
            parts.append(chunk)
        i = j
    cls = "vc-peca is-new" if is_new else "vc-peca"
    return f'<div class="{cls}"><p>{"".join(parts)}</p></div>'


def achado(f: dict, facts_version: int) -> str:
    """Um achado: chip + trecho, explicação, sugestão e a linha de rastro (rule_key + origem)."""
    parts = [
        f'<div class="vc-achado__topo">{chip(f["output"])} {dito(f["excerpt"])}</div>',
        f'<p class="vc-achado__explica">{escape(f["explanation"])}</p>',
    ]
    if f.get("suggestion"):
        parts.append(f'<p class="vc-achado__sugestao">{escape(curly(f["suggestion"]))}</p>')
    trail = origin(f.get("rule_key"), facts_version, f.get("prompt_version"))
    key = f"{ident(f['rule_key'])}, " if f.get("rule_key") else ""
    parts.append(f'<p class="vc-achado__rastro">{key}{escape(trail)}</p>')
    return "".join(parts)


def sort_findings(findings: list[dict]) -> list[dict]:
    """Ordem de gravidade (5.3); dentro da mesma decisão, a ordem do texto."""
    return sorted(findings, key=lambda f: (-SEVERITY.get(f["output"], 0), f["span"][0]))


# --- Canhoto (5.4) -------------------------------------------------------------------------


def canhoto(
    promises: list[tuple[str, str]],
    url: str,
    link_id: str,
    meta_html: str,
    *,
    is_new: bool = False,
) -> str:
    """O canhoto do link: promessas presas (dito + situação), picote, link, carimbo e cópia.

    `promises` = [(trecho dito, approval)]; `meta_html` já escapado por quem chama.
    O botão "Copiar link" usa um script curto (st.html com JavaScript ligado).
    """
    if promises:
        items = "".join(
            f"<li>{dito(text)}{chip(approval, APPROVAL)}</li>" for text, approval in promises
        )
        body = f'<ul class="vc-canhoto__lista">{items}</ul>'
    else:
        body = '<p class="vc-pequeno">Nenhuma promessa verificável nesta peça.</p>'
    head, _, code = url.rpartition("/")
    domain = head.split("://", 1)[-1]
    button_id = "vc-copiar-" + re.sub(r"[^A-Za-z0-9_-]", "", link_id)
    script = (
        "<script>(() => { const b = document.getElementById(" + json.dumps(button_id) + ");"
        " if (!b || b.dataset.ok) return; b.dataset.ok = '1';"
        " b.addEventListener('click', async () => {"
        " try { await navigator.clipboard.writeText(" + json.dumps(url).replace("</", "<\\/") + ");"
        " b.textContent = 'Link copiado'; }"
        " catch (e) { b.textContent = 'Não deu para copiar'; } }); })();</script>"
    )
    cls = "vc-canhoto is-new" if is_new else "vc-canhoto"
    return (
        f'<div class="{cls}">'
        '<div class="vc-canhoto__corpo">'
        '<h4 class="vc-canhoto__titulo">Promessas presas a este link</h4>'
        f"{body}"
        f'<p class="vc-canhoto__meta">{meta_html}</p>'
        "</div>"
        '<div class="vc-canhoto__picote" aria-hidden="true"></div>'
        '<div class="vc-canhoto__via">'
        '<p class="vc-canhoto__rotulo">Link</p>'
        f'<p class="vc-canhoto__link"><span class="vc-id">{escape(domain)}/</span>'
        f'<span class="vc-id vc-canhoto__codigo">{escape(code)}</span></p>'
        '<div class="vc-canhoto__carimbo"><span class="vc-carimbo">Registrada</span></div>'
        f'<button type="button" class="vc-botao-sec" id="{button_id}">Copiar link</button>'
        "</div></div>" + script
    )
