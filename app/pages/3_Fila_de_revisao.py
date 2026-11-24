"""Página 3 · Fila de revisão (marca, Operações): decide bloqueios contestados e classificações."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402
from painel_comum import domain_error, sidebar  # noqa: E402
from ui.components import page_header  # noqa: E402
from ui.theme import apply_theme  # noqa: E402

from promessa.db.session import session_scope  # noqa: E402
from promessa.errors import DomainError  # noqa: E402
from promessa.review import service as review_service  # noqa: E402
from promessa.rules.loader import load_rules  # noqa: E402

apply_theme("Fila de revisão")
ctx = sidebar()
page_header(
    "Fila de revisão",
    "Bloqueios contestados e classificações com pouca confiança. A decisão é sua.",
)

if ctx["role"] not in ("marca", "operacoes"):
    st.info(
        "A fila é da marca e de Operações. O creator contesta pelo Checador e acompanha por lá."
    )
    st.stop()
if not ctx["reviewer"]:
    st.warning("Informe seu nome na barra lateral: ele fica registrado na decisão.")
    st.stop()

kind = st.radio(
    "Mostrar",
    ["todos", "bloqueio", "classificacao"],
    horizontal=True,
    key="tipo_fila",
    format_func={
        "todos": "tudo",
        "bloqueio": "bloqueios contestados",
        "classificacao": "classificações com confiança baixa",
    }.get,
)
with session_scope() as session:
    queue = review_service.list_review_queue(session, None if kind == "todos" else kind).items
if not queue:
    st.info("Nada esperando revisão agora.")


CONFIRMATION = {  # BRAND, seção 7.3
    ("check_result", "manter"): "Bloqueio mantido",
    ("check_result", "reverter"): "Bloqueio revertido",
    ("refund_classification", "manter"): "Classificação mantida",
    ("refund_classification", "reclassificar"): "Classificação atualizada",
}


def decide(target_type: str, target_id: str, action: str, payload=None) -> None:
    try:
        with session_scope() as session:
            result = review_service.submit_review(
                session,
                target_type,
                target_id,
                action,
                ctx["reviewer"],
                ctx["role"],
                payload=payload,
            )
    except DomainError as e:
        domain_error(e)
    else:
        st.session_state["ultima_decisao"] = CONFIRMATION.get(
            (target_type, action), f"{action}: {result.review_status.value}"
        )
        st.rerun()


if st.session_state.get("ultima_decisao"):
    st.success(st.session_state.pop("ultima_decisao"))

taxonomy = load_rules().taxonomy.subcauses_by_cause()
for item in queue:
    age = f"há {item.age_hours:.0f} h" if item.age_hours is not None else ""
    with st.container(border=True):
        st.markdown(f"**{item.summary}** · {age}")
        c = item.context
        if item.kind == "bloqueio":
            st.write(f"Peça de `{item.creator_id}` para `{item.product_id}`:")
            st.text(c["piece_text"])
            st.write(c["explanation"])
            if c.get("contest_note"):
                st.caption(f"Contestação de {c['contested_by']}: {c['contest_note']}")
            b1, b2 = st.columns(2)
            if b1.button("Manter bloqueio", key=f"manter_{item.target_id}"):
                decide(item.target_type, item.target_id, "manter")
            if b2.button("Reverter bloqueio", key=f"reverter_{item.target_id}"):
                decide(item.target_type, item.target_id, "reverter")
        else:
            st.write(f"Motivo (até 80 caracteres): {c['reason_preview']}")
            st.caption(c["explanation"])
            b1, b2, b3 = st.columns([1, 1, 2])
            if b1.button("Manter", key=f"manter_c_{item.target_id}"):
                decide(item.target_type, item.target_id, "manter")
            causes = list(taxonomy)
            cause = b3.selectbox(
                "Nova causa",
                causes,
                index=causes.index(c["cause"]) if c["cause"] in causes else 0,
                key=f"causa_{item.target_id}",
            )
            sub = b3.selectbox("Nova subcausa", taxonomy[cause], key=f"sub_{item.target_id}")
            if b2.button("Reclassificar", key=f"reclass_{item.target_id}"):
                decide(
                    item.target_type,
                    item.target_id,
                    "reclassificar",
                    {"cause": cause, "subcause": sub},
                )
