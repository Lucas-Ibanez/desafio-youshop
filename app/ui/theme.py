"""Tema Vincula: configuração da página e CSS (docs/BRAND.md, seção 8)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import streamlit as st

UI = Path(__file__).resolve().parent
FAVICON = UI.parent / "static" / "favicon.png"


@lru_cache(maxsize=1)
def _css() -> str:
    return (UI / "theme.css").read_text(encoding="utf-8")


def apply_theme(title: str | None = None) -> None:
    """Configura a aba (nome e favicon) e injeta o CSS. Chamar no início de cada página."""
    st.set_page_config(
        page_title=f"{title} · Vincula" if title else "Vincula",
        page_icon=str(FAVICON) if FAVICON.exists() else None,
        layout="wide",
    )
    st.html(f"<style>{_css()}</style>")
