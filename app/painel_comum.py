"""Partes comuns do painel: barra lateral (papel, creator, revisor, período) e destaque de trechos.

O painel chama só serviços (decisão D3); não importa `promessa.db.models`.
"""

from __future__ import annotations

import html
from datetime import date
from typing import Any

import streamlit as st

from promessa.db.session import session_scope
from promessa.facts import service as facts_service

ROLES = {"marca": "Marca", "creator": "Creator", "operacoes": "Operações"}
COLORS = {"bloquear": "#f5b7b1", "revisar": "#fdebd0", "registrar": "#d5f5e3"}
LABELS = {
    "bloquear": "🔴 bloquear",
    "revisar": "🟡 revisar",
    "registrar": "🟢 registrar",
    "limpo": "⚪ limpo",
}
SEVERITY = {"registrar": 1, "revisar": 2, "bloquear": 3}
DEFAULT_START, DEFAULT_END = date(2026, 10, 26), date(2026, 11, 22)


def _remember(key: str, default: Any) -> Any:
    """Valor escolhido na barra lateral, mantido entre páginas."""
    return st.session_state.get(f"_{key}", default)


def sidebar() -> dict[str, Any]:
    """Seletor de papel, creator, nome do revisor e período. Devolve o contexto escolhido."""
    with session_scope() as session:
        creators = facts_service.list_creators(session)
    st.sidebar.title("Promessa Rastreável")
    role_keys = list(ROLES)
    role = st.sidebar.selectbox(
        "Papel",
        role_keys,
        index=role_keys.index(_remember("papel", "creator")),
        format_func=ROLES.get,
        key="papel",
    )
    st.session_state["_papel"] = role
    ctx: dict[str, Any] = {"role": role, "creator_id": None, "reviewer": None}
    if role == "creator":
        ids = [c.id for c in creators]
        names = {c.id: f"{c.display_name} ({c.handle})" for c in creators}
        current = _remember("creator", ids[0] if ids else None)
        ctx["creator_id"] = st.sidebar.selectbox(
            "Creator",
            ids,
            index=ids.index(current) if current in ids else 0,
            format_func=names.get,
            key="creator",
        )
        st.session_state["_creator"] = ctx["creator_id"]
    else:
        ctx["reviewer"] = st.sidebar.text_input(
            "Seu nome (fica registrado nas decisões)",
            value=_remember("revisor", f"{role}_demo"),
            key="revisor",
        ).strip()
        st.session_state["_revisor"] = ctx["reviewer"]
    start = st.sidebar.date_input(
        "Início do período", value=_remember("inicio", DEFAULT_START), key="inicio"
    )
    end = st.sidebar.date_input("Fim do período", value=_remember("fim", DEFAULT_END), key="fim")
    st.session_state["_inicio"], st.session_state["_fim"] = start, end
    ctx["start"], ctx["end"] = start.isoformat(), end.isoformat()
    st.sidebar.caption("Protótipo local. O papel é um parâmetro, não um login.")
    return ctx


def products() -> list:
    with session_scope() as session:
        return facts_service.list_products(session)


def product_select(label: str = "Produto", key: str = "produto") -> str:
    items = products()
    ids = [p.id for p in items]
    names = {p.id: f"{p.name} ({p.id})" for p in items}
    current = _remember(key, ids[0])
    chosen = st.selectbox(
        label,
        ids,
        index=ids.index(current) if current in ids else 0,
        format_func=names.get,
        key=key,
    )
    st.session_state[f"_{key}"] = chosen
    return chosen


def highlight(text: str, findings: list[dict]) -> str:
    """HTML do texto com cada trecho marcado pela cor da saída mais grave que o cobre."""
    level = [0] * len(text)
    output_at: list[str | None] = [None] * len(text)
    for f in findings:
        start, end = f["span"]
        sev = SEVERITY.get(f["output"], 0)
        for i in range(max(0, start), min(len(text), end)):
            if sev > level[i]:
                level[i], output_at[i] = sev, f["output"]
    parts, i = [], 0
    while i < len(text):
        j = i
        while j < len(text) and output_at[j] == output_at[i]:
            j += 1
        chunk = html.escape(text[i:j]).replace("\n", "<br>")
        out = output_at[i]
        parts.append(
            f'<span style="background:{COLORS[out]};padding:1px 2px;border-radius:3px">{chunk}</span>'
            if out
            else chunk
        )
        i = j
    return '<div style="line-height:1.9;font-size:1.05em">' + "".join(parts) + "</div>"


def domain_error(e: Exception) -> None:
    st.error(str(e))
