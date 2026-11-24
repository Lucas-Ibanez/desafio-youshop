"""Painel do Vincula (promessa rastreável). Rodar: uv run python tasks.py painel

Ponto de entrada: monta o menu com os títulos das páginas (docs/BRAND.md, seção 5.2) com
st.navigation. As páginas ficam em app/inicio.py e app/pages/*.py; os endereços não mudaram.
"""

from pathlib import Path

import streamlit as st

APP = Path(__file__).resolve().parent

PAGES = [
    st.Page(APP / "inicio.py", title="Início", default=True),
    st.Page(APP / "pages/1_Ficha.py", title="Ficha do produto", url_path="Ficha"),
    st.Page(APP / "pages/2_Checador.py", title="Checar peça", url_path="Checador"),
    st.Page(
        APP / "pages/3_Fila_de_revisao.py", title="Fila de revisão", url_path="Fila_de_revisao"
    ),
    st.Page(APP / "pages/4_Relatorios.py", title="Devoluções e promessas", url_path="Relatorios"),
    st.Page(APP / "pages/5_Avaliacao.py", title="Teste dos agentes", url_path="Avaliacao"),
]

st.navigation(PAGES).run()
