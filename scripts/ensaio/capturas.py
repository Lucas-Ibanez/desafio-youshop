"""Capturas das 5 páginas do painel nos papéis creator e marca (docs/BRAND.md, conferência visual).

Uso: uv run python scripts/ensaio/capturas.py docs/capturas/P0

Sobe o painel sem chave (só regras, texto fixo), abre o Chromium 1280 px de largura e salva cada
página inteira. No Streamlit quem rola é o `stMain`, não a janela: a altura da captura é a do
conteúdo dele. No papel creator, o checador é capturado com uma peça bloqueada (com um bloqueio
contestado, para a fila da marca ter um item) e depois com a peça corrigida e o link gerado.
Grava peças e uma contestação no banco local, como o ensaio.
"""

from __future__ import annotations

import sys
from pathlib import Path

from common import ROOT
from rec_panel import (
    Panel,
    choose_creator,
    choose_role,
    click_button,
    fill_text,
    goto_page,
    open_home,
    select_option,
    wait_idle,
)

PAGES = [
    ("1_ficha", "Ficha do produto"),
    ("2_checador", "Checar peça"),
    ("3_fila", "Fila de revisão"),
    ("4_relatorios", "Devoluções e promessas"),
    ("5_avaliacao", "Teste dos agentes"),
]
BAD = "Treino em casa com acesso vitalício e 30 dias para testar."
FIXED = "Treino em casa com 12 meses de acesso e 7 dias de garantia. #publi"
WIDTH = 1280


def shot(page, out: Path, name: str) -> Path:
    """Página inteira: a altura vem do conteúdo do stMain (ou da barra lateral, se maior)."""
    wait_idle(page)
    page.wait_for_timeout(700)  # animações de entrada (marca-texto, carimbo, fio)
    height = page.evaluate(
        "() => Math.max(document.querySelector('[data-testid=stMain]').scrollHeight,"
        " document.querySelector('[data-testid=stSidebarContent]')?.scrollHeight || 0)"
    )
    page.set_viewport_size({"width": WIDTH, "height": max(720, min(height + 40, 6000))})
    page.wait_for_timeout(400)
    path = out / f"{name}.png"
    page.screenshot(path=str(path))
    page.set_viewport_size({"width": WIDTH, "height": 720})
    return path


def product(page) -> None:
    select_option(page, "Produto", "prod_treino", in_sidebar=False, exact=False)


def run(out: Path) -> list[Path]:
    from playwright.sync_api import sync_playwright

    out.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": WIDTH, "height": 720}, locale="pt-BR")
        page.set_default_timeout(30_000)
        open_home(page)

        # creator (cr_ana)
        choose_role(page, "Creator")
        choose_creator(page, "Ana")
        for key, title in PAGES:
            goto_page(page, title)
            if key in ("1_ficha", "2_checador"):
                product(page)
            if key == "2_checador":
                fill_text(page, "Texto da peça", BAD, typing_delay=0)
                click_button(page, "Checar peça")
                saved.append(shot(page, out, f"creator_{key}_bloqueio"))
                click_button(page, "Contestar bloqueio")
                fill_text(page, "Texto da peça", FIXED, typing_delay=0)
                click_button(page, "Checar peça")
                click_button(page, "Gerar link")
                saved.append(shot(page, out, f"creator_{key}_link"))
                continue
            saved.append(shot(page, out, f"creator_{key}"))

        # marca
        choose_role(page, "Marca")
        for key, title in PAGES:
            goto_page(page, title)
            if key in ("1_ficha", "4_relatorios"):
                product(page)
            saved.append(shot(page, out, f"marca_{key}"))
        browser.close()
    return saved


def main(argv: list[str]) -> int:
    out = (ROOT / argv[0]) if argv else ROOT / "docs" / "capturas"
    with Panel(ROOT / "ensaio" / "capturas_painel.log"):
        saved = run(out)
    for path in saved:
        print(path.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
