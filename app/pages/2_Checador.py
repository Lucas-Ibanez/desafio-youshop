"""Página 2 · Checador (creator): briefing, checagem da peça, link rastreado e contestação."""

import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from painel_comum import domain_error, highlight, product_name, product_select, sidebar  # noqa: E402
from ui.components import chip, dito, ident, page_header  # noqa: E402
from ui.theme import apply_theme  # noqa: E402

from promessa.checker import service as checker_service  # noqa: E402
from promessa.db.session import session_scope  # noqa: E402
from promessa.display import APPROVAL, PROMISE_TYPE, label, promise_label  # noqa: E402
from promessa.errors import DomainError  # noqa: E402
from promessa.facts import service as facts_service  # noqa: E402
from promessa.links import service as links_service  # noqa: E402
from promessa.review import service as review_service  # noqa: E402

TITLE = "Checar peça"
SUBTITLE = "Cole a legenda ou o roteiro. O Vincula compara com a ficha antes de gerar o link."

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
text = st.text_area("Texto da peça", height=140, key="texto_peca")
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
        state["checagem"] = {**resp.model_dump(mode="json"), "text": text, "product_id": product_id}
        state.pop("link", None)
        state["contestados"] = []
        last = state["checagem"]

if last and last["product_id"] == product_id:
    st.html(f'<h3 class="vc-resultado">Resultado {chip(last["overall"])}</h3>')
    st.caption(
        f"Peça {last['piece_id']} · ficha v{last['facts_version']} · camadas: {', '.join(last['layers_used'])}"
    )
    st.markdown(highlight(last["text"], last["findings"]), unsafe_allow_html=True)
    for note in last.get("notes", []):
        st.caption(note)
    if not last["disclosure"]["present"]:
        st.warning(last["disclosure"]["suggestion"])

    for f in last["findings"]:
        with st.container(border=True):
            st.html(f"{chip(f['output'])} {dito(f['excerpt'])} {ident(f['rule_key'] or 'modelo')}")
            st.write(f["explanation"])
            if f.get("suggestion"):
                st.caption(f"Sugestão: {f['suggestion']}")
            if f["output"] == "bloquear":
                if f["id"] in state.get("contestados", []):
                    st.info("Contestação enviada para a marca")
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
    can_try = last["can_generate_link"] or bool(state.get("contestados"))
    if not last["can_generate_link"]:
        pending = [
            f
            for f in last["findings"]
            if f["output"] == "bloquear" and f["id"] not in state.get("contestados", [])
        ]
        if pending:
            n = len(pending)
            st.error(
                f"Ainda há {n} {'trecho bloqueado' if n == 1 else 'trechos bloqueados'}. "
                "Ajuste o texto ou conteste o bloqueio."
            )
    if can_try and st.button("Gerar link", type="primary", key="gerar_link"):
        try:
            with session_scope() as session:
                link = links_service.register_content_and_link(session, last["piece_id"])
        except DomainError as e:
            domain_error(e)
        else:
            state["link"] = link.model_dump(mode="json")
    if state.get("link") and state["link"]["piece_id"] == last["piece_id"]:
        link = state["link"]
        st.success("Link gerado. As promessas ficaram registradas.")
        st.html(f"<p>Link: {ident(link['url'])}</p>")
        st.caption(link["disclosure_text"])
        if link["registered_promises"]:
            st.write("Promessas registradas na venda:")
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "promessa": promise_label(p["normalized_text"]),
                            "tipo": label(PROMISE_TYPE, p["type"]),
                            "situação": label(APPROVAL, p["approval"]),
                        }
                        for p in link["registered_promises"]
                    ]
                ),
                hide_index=True,
            )
elif not last:
    st.caption("Nenhuma peça checada ainda. Cole a legenda ou o roteiro acima para começar.")
