"""Página 4 · Devoluções e promessas: marca/Operações por produto; creator só os próprios números.

Na visão creator nenhum texto de comprador aparece (invariante 5): só agregados. O fio (BRAND,
5.5) mostra do lado direito só a promessa ou crença normalizada e agregada.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from painel_comum import domain_error, product_select, sidebar  # noqa: E402
from ui.components import cause_chart, dito, fio, md_label, metricas, page_header  # noqa: E402
from ui.labels import CAUSE, CAUSE_FOR_CREATOR  # noqa: E402
from ui.theme import apply_theme  # noqa: E402

from promessa.db.session import session_scope  # noqa: E402
from promessa.display import num, pct  # noqa: E402
from promessa.errors import DomainError  # noqa: E402
from promessa.reports import explain as explain_service  # noqa: E402
from promessa.reports import service as reports_service  # noqa: E402

apply_theme("Devoluções e promessas")
ctx = sidebar()


def _br(iso: str) -> str:
    return f"{iso[8:10]}/{iso[5:7]}"


page_header(
    "Devoluções e promessas",
    "Por que as vendas voltaram e o que cada lado pode mudar.",
    f"Vendas de {_br(ctx['start'])} a {_br(ctx['end'])} e as devoluções dessas vendas.",
)


def refunds(n: int) -> str:
    return f"{n} {'devolução' if n == 1 else 'devoluções'}"


def weighs_label(c) -> str:
    """Quantas devoluções da causa pesam de fato no creator (só `confirma`, D30)."""
    if not c.pesa_no_creator or c.pesam_no_creator == 0:
        return "não"
    if c.pesam_no_creator == c.devolucoes:
        return "sim"
    return f"{c.pesam_no_creator} de {c.devolucoes}"


def causes_table(report, labels: dict[str, str]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "causa": labels.get(c.causa, c.rotulo),
                "devoluções": c.devolucoes,
                "% das devoluções": pct(c.pct_devolucoes, 0),
                "% das vendas": pct(c.taxa_sobre_vendas),
                "pesa no creator": weighs_label(c),
            }
            for c in report.causas
            if c.devolucoes
        ]
    )


def causes_block(report, labels: dict[str, str]) -> None:
    if not report.devolucoes:
        st.info("Nenhuma devolução neste período. Tente um período maior.")
        return
    cause_chart(report.causas, labels)
    st.dataframe(causes_table(report, labels), hide_index=True)


def contested_threads(report, show_creators: bool) -> None:
    """Promessas cobradas (confirma): o trecho da peça ligado à promessa registrada."""
    for p in report.promessas_mais_contestadas:
        said = p.trecho or p.rotulo
        with st.expander(f"“{md_label(said)}” · {refunds(p.devolucoes)}"):
            extra = f" · {', '.join(p.creators)}" if show_creators else ""
            st.html(fio(dito(said), p.rotulo, "confirma", refunds(p.devolucoes) + extra))


try:
    if ctx["role"] == "creator":
        with session_scope() as session:
            report = reports_service.promise_outcome_report(
                session, creator_id=ctx["creator_id"], start=ctx["start"], end=ctx["end"]
            )
            explanation = explain_service.explain_refunds_to_creator(
                session, ctx["creator_id"], ctx["start"], ctx["end"]
            )
        st.subheader("O que aconteceu com as suas vendas")
        st.info(explanation.text)
        ind = report.indicador_creator
        insufficient = ind.status == "dados_insuficientes"
        st.html(
            metricas(
                [
                    ("Vendas", str(report.vendas), "no período"),
                    (
                        "Devoluções",
                        str(report.devolucoes),
                        f"{pct(report.taxa_devolucao)} das vendas",
                    ),
                    (
                        "Devoluções por promessa da sua peça",
                        None if insufficient else pct(ind.taxa_promessa_confirmada),
                        f"O indicador aparece a partir de {ind.minimo_vendas} vendas no período."
                        if insufficient
                        else f"{ind.devolucoes_confirmadas} de {ind.vendas} vendas",
                    ),
                ]
            )
        )
        st.subheader("Devoluções por causa")
        causes_block(report, CAUSE_FOR_CREATOR)
        if report.promessas_mais_contestadas:
            st.subheader("Trechos da sua peça que os compradores cobraram")
            st.caption("Abra um trecho para ver a promessa ligada ao que voltou.")
            contested_threads(report, show_creators=False)
    else:
        scope = st.radio("Ver por", ["produto", "creator"], horizontal=True, key="escopo")
        with session_scope() as session:
            if scope == "produto":
                product_id = product_select(key="produto_relatorio")
                report = reports_service.promise_outcome_report(
                    session, product_id=product_id, start=ctx["start"], end=ctx["end"]
                )
            else:
                from promessa.facts import service as facts_service

                creators = [c.id for c in facts_service.list_creators(session)]
                creator_id = st.selectbox("Creator", creators, key="creator_relatorio")
                report = reports_service.promise_outcome_report(
                    session, creator_id=creator_id, start=ctx["start"], end=ctx["end"]
                )
        st.html(
            metricas(
                [
                    ("Vendas", str(report.vendas), "no período"),
                    (
                        "Devoluções",
                        str(report.devolucoes),
                        f"{pct(report.taxa_devolucao)} das vendas",
                    ),
                    (
                        "Vendas com promessa registrada",
                        pct(report.cobertura["vendas_com_promessa_registrada"], 0),
                        None,
                    ),
                    (
                        "Condições contrárias barradas",
                        str(report.integridade["condicoes_contrarias_barradas"]),
                        "antes da venda",
                    ),
                ]
            )
        )
        st.subheader("Devoluções por causa")
        causes_block(report, CAUSE)
        if report.por_creator:
            st.subheader("Por creator")
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "creator": r.creator_id,
                            "vendas": r.vendas,
                            "devoluções": r.devolucoes,
                            "taxa de devolução": pct(r.taxa_devolucao),
                            "promessa confirmada": r.indicador.texto
                            if r.indicador.status == "dados_insuficientes"
                            else pct(r.indicador.taxa_promessa_confirmada),
                        }
                        for r in report.por_creator
                    ]
                ),
                hide_index=True,
            )
        if report.indicador_creator:
            st.caption(report.indicador_creator.texto)
        # as duas listas empilhadas: o fio precisa da largura toda (5.5)
        st.subheader("Promessas mais contestadas")
        st.caption("O comprador cobrou exatamente o que a peça prometeu.")
        contested_threads(report, show_creators=True)
        if not report.promessas_mais_contestadas:
            st.write("Nenhuma.")
        st.subheader("Sinais para a marca")
        st.caption("O comprador acreditava em algo que a peça não registrou.")
        for s in report.sinais_para_a_marca:
            with st.expander(f"“{md_label(s.rotulo)}” · {refunds(s.devolucoes)}"):
                st.html(
                    fio(
                        '<span class="vc-fio__fora">não está na peça</span>',
                        s.rotulo,
                        "contradiz",
                        f"{refunds(s.devolucoes)} · {', '.join(s.creators)}",
                    )
                )
                st.caption(s.texto)
        if not report.sinais_para_a_marca:
            st.write("Nenhum.")
        st.subheader("Cobertura e operação")
        horas = report.operacao["horas_medias_ate_classificar"]
        st.write(
            f"Devoluções classificadas: {pct(report.cobertura['devolucoes_classificadas'], 0)} · ligadas a uma promessa: "
            f"{pct(report.cobertura['devolucoes_ligadas_a_promessa'], 0)} · tempo médio até classificar: "
            + ("—" if horas is None else f"{num(horas, 1)} h")
        )
except DomainError as e:
    domain_error(e)
