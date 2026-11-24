"""Página inicial do painel (o menu fica em app/painel.py)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st  # noqa: E402
from painel_comum import ROLES, sidebar  # noqa: E402
from ui.components import page_header  # noqa: E402
from ui.theme import apply_theme  # noqa: E402

apply_theme()
ctx = sidebar()
page_header(
    "Vincula",
    "A promessa que vende é a promessa que vincula.",
    "Cada promessa com o seu desfecho.",
)
st.markdown(
    "O Vincula liga **o que o produto pode prometer** (ficha da marca), **o que o creator "
    "prometeu** na peça que gerou a venda e **por que o comprador pediu o dinheiro de volta**."
)
st.markdown(
    """
| Página | Para quem | O que faz |
|---|---|---|
| Ficha do produto | marca | versões da ficha, condições, regras com fonte, nova versão |
| Checar peça | creator | briefing, checagem da peça, link rastreado, contestação |
| Fila de revisão | marca, Operações | bloqueios contestados e classificações com pouca confiança |
| Devoluções e promessas | todos | marca e Operações: por produto; creator: os próprios números e a explicação |
| Teste dos agentes | todos | o checador e o classificador contra os gabaritos |
"""
)
st.info(f"Você está vendo como **{ROLES[ctx['role']]}**. Troque o papel na barra lateral.")
