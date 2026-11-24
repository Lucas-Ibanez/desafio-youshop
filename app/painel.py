"""Painel do MVP Promessa Rastreável (T14). Rodar: uv run python tasks.py painel"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st  # noqa: E402
from painel_comum import ROLES, sidebar  # noqa: E402

st.set_page_config(page_title="Promessa Rastreável", page_icon="🔗", layout="wide")
ctx = sidebar()

st.title("Promessa Rastreável")
st.markdown(
    "Liga **o que o produto pode prometer** (ficha da marca), **o que o creator prometeu** na peça "
    "que gerou a venda e **por que o comprador pediu o dinheiro de volta**."
)
st.markdown(
    """
| Página | Para quem | O que faz |
|---|---|---|
| 1 · Ficha | marca | versões da ficha, condições, regras com fonte, nova versão |
| 2 · Checador | creator | briefing, checagem da peça, link rastreado, contestação |
| 3 · Fila de revisão | marca, Operações | bloqueios contestados e classificações com confiança baixa |
| 4 · Relatórios | todos | marca/Operações: por produto; creator: os próprios números e a explicação |
| 5 · Avaliação | todos | Teste 1 dos dois agentes contra os gabaritos |
"""
)
st.info(f"Você está como **{ROLES[ctx['role']]}**. Troque o papel na barra lateral.")
