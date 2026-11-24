"""Painel do MVP Promessa Rastreável (T14). Rodar: uv run python tasks.py painel

Ponto de entrada: monta o menu com os nomes das páginas em português (st.navigation). As
páginas ficam em app/inicio.py e app/pages/*.py; os endereços são os mesmos de antes.
"""

from pathlib import Path

import streamlit as st

APP = Path(__file__).resolve().parent

PAGES = [
    st.Page(APP / "inicio.py", title="Início", icon="🔗", default=True),
    st.Page(APP / "pages/1_Ficha.py", title="Ficha", icon="📋", url_path="Ficha"),
    st.Page(APP / "pages/2_Checador.py", title="Checador", icon="🔎", url_path="Checador"),
    st.Page(
        APP / "pages/3_Fila_de_revisao.py",
        title="Fila de revisão",
        icon="📥",
        url_path="Fila_de_revisao",
    ),
    st.Page(APP / "pages/4_Relatorios.py", title="Relatórios", icon="📊", url_path="Relatorios"),
    st.Page(APP / "pages/5_Avaliacao.py", title="Avaliação", icon="🧪", url_path="Avaliacao"),
]

st.navigation(PAGES).run()
