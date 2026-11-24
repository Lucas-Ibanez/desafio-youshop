"""Página 2 · Checar peça (creator): briefing, checagem, achados, link rastreado e contestação.

Identidade Vincula (docs/BRAND.md): texto checado com marca-texto (5.3), canhoto com carimbo
(5.4) e as duas animações, que só rodam na execução logo depois da ação (6, `vc_anim`).
"""

import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402
from painel_comum import domain_error, product_name, product_select, sidebar  # noqa: E402
from ui.components import (  # noqa: E402
    achado,
    canhoto,
    chip,
    ident,
    page_header,
    peca_marcada,
    sort_findings,
    when,
)
from ui.theme import apply_theme  # noqa: E402

from promessa.checker import service as checker_service  # noqa: E402
from promessa.db.session import session_scope  # noqa: E402
from promessa.display import promise_label  # noqa: E402
from promessa.errors import DomainError  # noqa: E402
from promessa.facts import service as facts_service  # noqa: E402
from promessa.links import service as links_service  # noqa: E402
from promessa.review import service as review_service  # noqa: E402

TITLE = "Checar peça"
SUBTITLE = "Cole a legenda ou o roteiro. O Vincula compara com a ficha antes de gerar o link."
# Notas do checador reescritas no tom do guia (7.4); as demais aparecem como vêm.
NOTES = {"Checagem só com regras": "Checagem feita só com as regras. O modelo está desligado."}


def note_text(note: str) -> str:
    return next((v for k, v in NOTES.items() if note.startswith(k)), note)


apply_theme(TITLE)
ctx = sidebar()
head = st.container()

if ctx["role"] != "creator":
    page_header(TITLE, SUBTITLE, container=head)
    st.info("Esta página é do creator. Troque o papel para **Creator** na barra lateral.")
    st.stop()

creator_id = ctx["creator_id"]
product_id = product_select(key="produto_checador")
with session_scope() as session:
    facts = facts_service.get_product_facts(session, product_id)
page_header(
    TITLE,
    SUBTITLE,
    f"{escape(product_name(product_id))}, ficha {ident(f'v{facts.version}')}",
    container=head,
)
with st.expander("Briefing do produto: o que você pode prometer", expanded=True):
    st.text(facts.briefing)

state = st.session_state
last = state.get("checagem")
last_blocked = bool(last and last["product_id"] == product_id and last["overall"] == "bloquear")

channel = st.selectbox(
    "Canal", ["instagram", "tiktok", "youtube", "whatsapp", "outro"], key="canal"
)
text = st.text_area("Texto da peça", height=190, key="texto_peca")
c1, c2 = st.columns(2)
is_fix = c1.checkbox(
    "Esta peça corrige a anterior (bloqueada)",
    value=last_blocked,
    disabled=not last_blocked,
    key=f"corrige_{last['piece_id'] if last_blocked else 'nenhuma'}",
)
use_llm = c2.checkbox(
    "Usar o modelo (camada 2)",
    value=False,
    key="usar_modelo",
    help="Desligado, a checagem usa só as regras (rápido e sem gastar cota).",
)

if st.button("Checar peça", type="primary", key="checar"):
    try:
        with session_scope() as session:
            resp = checker_service.check_content(
                session,
                product_id,
                creator_id,
                text,
                channel,
                parent_piece_id=last["piece_id"] if is_fix and last_blocked else None,
                use_llm=use_llm,
            )
    except DomainError as e:
        domain_error(e)
    else:
        state["checagem"] = {
            **resp.model_dump(mode="json"),
            "text": text,
            "product_id": product_id,
            "checked_at": when(),
        }
        state.pop("link", None)
        state["contestados"] = []
        state["vc_anim"] = ("peca", resp.piece_id)  # marca-texto só nesta execução
        last = state["checagem"]

if last and last["product_id"] == product_id:
    anim = state.pop("vc_anim", None)
    contested = state.get("contestados", [])

    st.html(f'<h3 class="vc-resultado">Resultado {chip(last["overall"])}</h3>')
    st.html(
        f'<p class="vc-pequeno">Peça {ident(last["piece_id"])}, ficha '
        f"{ident(f'v{last["facts_version"]}')}, checada em {escape(last.get('checked_at', ''))}</p>"
    )
    st.html(peca_marcada(last["text"], last["findings"], is_new=anim == ("peca", last["piece_id"])))
    for note in last.get("notes", []):
        st.caption(note_text(note))

    for f in sort_findings(last["findings"]):
        with st.container(key=f"vc_achado_{f['output']}_{f['id']}"):
            st.html(achado(f, last["facts_version"]))
            if f["output"] == "bloquear":
                if f["id"] in contested:
                    st.html('<p class="vc-pequeno">Contestação enviada para a marca</p>')
                elif st.button("Contestar bloqueio", key=f"contestar_{f['id']}"):
                    try:
                        with session_scope() as session:
                            review_service.submit_review(
                                session, "check_result", f["id"], "contestar", creator_id, "creator"
                            )
                    except DomainError as e:
                        domain_error(e)
                    else:
                        state.setdefault("contestados", []).append(f["id"])
                        st.rerun()

    st.divider()
    if not last["disclosure"]["present"]:  # não conta como achado (D5)
        st.html(
            '<p class="vc-publi">Falta identificar como publicidade. Inclua #publi na legenda.</p>'
        )
    can_try = last["can_generate_link"] or bool(contested)
    pending = [
        f for f in last["findings"] if f["output"] == "bloquear" and f["id"] not in contested
    ]
    b1, b2 = st.columns([1, 4], vertical_alignment="center")
    clicked = b1.button("Gerar link", type="primary", key="gerar_link", disabled=not can_try)
    if not can_try and pending:
        n = len(pending)
        b2.html(
            f'<p class="vc-motivo">Ainda há {n} {"trecho bloqueado" if n == 1 else "trechos bloqueados"}.'
            " Ajuste o texto ou conteste o bloqueio.</p>"
        )
    if clicked:
        try:
            with session_scope() as session:
                link = links_service.register_content_and_link(session, last["piece_id"])
        except DomainError as e:
            domain_error(e)
        else:
            state["link"] = link.model_dump(mode="json")
            anim = ("link", link.link_id)  # carimbo só nesta execução

    if state.get("link") and state["link"]["piece_id"] == last["piece_id"]:
        link = state["link"]
        st.success("Link gerado. As promessas ficaram registradas.")
        excerpts = {f["id"]: f["excerpt"] for f in last["findings"]}
        promises = [
            (
                excerpts.get(p["check_result_id"]) or promise_label(p["normalized_text"]),
                p["approval"],
            )
            for p in link["registered_promises"]
        ]
        meta = (
            f"Ficha {ident(f'v{link["facts_version"]}')} do {escape(product_name(product_id))}, "
            f"checada em {escape(last.get('checked_at', ''))}"
        )
        st.html(
            canhoto(
                promises,
                link["url"],
                link["link_id"],
                meta,
                is_new=anim == ("link", link["link_id"]),
            ),
            unsafe_allow_javascript=True,
        )
        st.caption(link["disclosure_text"])
elif not last:
    st.caption("Nenhuma peça checada ainda. Cole a legenda ou o roteiro acima para começar.")
