"""Página 5 · Avaliação: metas e resultados do Teste 1 (lê eval/reports/*.json)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from painel_comum import sidebar  # noqa: E402

REPORTS = Path(__file__).resolve().parents[2] / "eval" / "reports"

st.set_page_config(page_title="Avaliação", page_icon="🧪", layout="wide")
sidebar()
st.title("5 · Avaliação (Teste 1)")
st.caption(
    "Os dois agentes contra os gabaritos das validações. O split `test` é o principal; nada é escondido."
)


def load(name: str) -> dict | None:
    path = REPORTS / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def mark(value, goal) -> str:
    if value is None:
        return "—"
    return "✅" if value >= goal - 1e-9 else "❌"


def pct(v) -> str:
    return "—" if v is None else f"{v:.0%}"


def num(v) -> str:
    return "—" if v is None else f"{v:.2f}"


checker = load("checador_h2.json")
st.header("Checador (60 anúncios da H2)")
if not checker:
    st.info("Ainda sem relatório. Rode `uv run python tasks.py eval-checador`.")
else:
    run = checker["rodada"]
    st.caption(
        f"Rodada {run['versao']} · {checker['data']} · modelo {checker['modelo']} · {run['mudancas']}"
    )
    rows = []
    for cfg, label in (("regras", "só regras"), ("regras+modelo", "regras + modelo")):
        m = checker["metricas"].get(cfg)
        if not m:
            continue
        t = m["test"]
        rows += [
            {
                "configuração": label,
                "meta": "bloquear nas 4 irregulares evidentes (4 de 4)",
                "test": f"{t['sensibilidade']['acertos']}/{t['sensibilidade']['n']}",
                "total": f"{m['total']['sensibilidade']['acertos']}/4",
                "ok": mark(m["total"]["sensibilidade"]["valor"], 1.0),
            },
            {
                "configuração": label,
                "meta": "kappa do indício (≥ 0,6)",
                "test": num(t["kappa"]),
                "total": num(m["total"]["kappa"]),
                "ok": mark(t["kappa"], 0.6),
            },
            {
                "configuração": label,
                "meta": "promessa verificável extraída (≥ 80%)",
                "test": pct(t["recall_verificavel"]["valor"]),
                "total": pct(m["total"]["recall_verificavel"]["valor"]),
                "ok": mark(t["recall_verificavel"]["valor"], 0.8),
            },
        ]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.caption(
        "Vazamento conhecido: as regras foram escritas a partir desta mesma auditoria; o resultado é otimista."
    )

classifier = load("classificador_h1.json")
st.header("Classificador (172 compradores da H1)")
if not classifier:
    st.info("Ainda sem relatório. Rode `uv run python tasks.py eval-classificador`.")
else:
    run = classifier["rodada"]
    st.caption(
        f"Rodada {run['versao']} · {classifier['data']} · modelo {classifier['modelo']} · {run['mudancas']}"
    )
    m = classifier["metricas"]["parafrase"]
    t = m["test"]
    corte = t["corte"]
    ok_corte = (corte["acuracia"] or 0) >= 0.8 and (corte["kappa"] or 0) >= 0.6
    st.subheader(
        f"Critério de corte: separa promessa de acesso e processo? {'SIM' if ok_corte else 'NÃO'}"
    )
    st.caption(
        f"{pct(corte['acuracia'])} de acerto e kappa {num(corte['kappa'])} nas {corte['n']} reclamações do test de promessa, acesso ou processo."
    )
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "meta": "acurácia na causa principal (≥ 80%)",
                    "test": pct(t["acuracia"]),
                    "total": pct(m["total"]["acuracia"]),
                    "ok": mark(t["acuracia"], 0.8),
                },
                {
                    "meta": "kappa na causa principal (≥ 0,6)",
                    "test": num(t["kappa"]),
                    "total": num(m["total"]["kappa"]),
                    "ok": mark(t["kappa"], 0.6),
                },
                {
                    "meta": "subtipo nas reclamações de promessa (≥ 70%)",
                    "test": pct(t["subtipo"]["acuracia"]),
                    "total": pct(m["total"]["subtipo"]["acuracia"]),
                    "ok": mark(t["subtipo"]["acuracia"], 0.7),
                },
                {
                    "meta": "precisão de promessa explícita (pesa no creator)",
                    "test": pct(t["promessa_explicita"]["precisao"]),
                    "total": pct(m["total"]["promessa_explicita"]["precisao"]),
                    "ok": "—",
                },
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    labels = ["promessa", "acesso", "processo", "fraude", "outros"]
    st.write("Matriz de confusão (test): linhas = gabarito, colunas = predito")
    st.dataframe(pd.DataFrame(t["matriz"]).T.reindex(index=labels, columns=labels), width="stretch")
    st.caption(
        "Vazamento conhecido: o texto da H1 é uma paráfrase escrita por quem codificou; o resultado é otimista."
    )

st.divider()
st.caption(
    "Relatórios completos em eval/reports/checador_h2.md e eval/reports/classificador_h1.md."
)
