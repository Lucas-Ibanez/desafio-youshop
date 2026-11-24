"""Gravação do painel: sobe o Streamlit, abre o Chromium gravando e conduz a barra lateral.

Uso (biblioteca):
    with Panel(run_dir / "painel.log"):
        with recording(run_dir / "passo_2.webm") as page:
            open_home(page)
            set_caption(page, "Passo 2: creator cola a peça")
            choose_role(page, "Creator")
            goto_page(page, "Checador")
            fill_text(page, "Texto da peça", "acesso vitalício e 30 dias para testar")
            click_button(page, "Checar")
    webm_to_mp4(run_dir / "passo_2.webm", run_dir / "passo_2.mp4")

O painel sobe com GEMINI_API_KEY vazia só no processo dele: a explicação ao creator sai pelo
texto fixo e o checador fica só com regras (sem gastar cota nem depender da rede ao vivo).
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

from common import ROOT, ffmpeg_exe

PORT = 8501
URL = f"http://localhost:{PORT}"
VIEWPORT = {"width": 1280, "height": 720}


# ── processo do painel ────────────────────────────────────────────────────────────────────


def port_in_use(port: int = PORT) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


class Panel:
    """`tasks.py painel` em subprocesso; `with Panel(log): ...` sobe, espera e encerra."""

    def __init__(self, log_path: str | Path, port: int = PORT, extra_env: dict | None = None):
        self.log_path = Path(log_path)
        self.port = port
        self.extra_env = extra_env or {}
        self.proc: subprocess.Popen | None = None

    def start(self, timeout: float = 90.0) -> None:
        if port_in_use(self.port):
            raise RuntimeError(f"a porta {self.port} já está em uso: feche o painel aberto")
        env = {
            **os.environ,
            "GEMINI_API_KEY": "",  # só neste processo: texto fixo, checador só com regras
            "STREAMLIT_SERVER_HEADLESS": "true",
            "STREAMLIT_SERVER_PORT": str(self.port),
            "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
            **self.extra_env,
        }
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log = self.log_path.open("w", encoding="utf-8")
        self.proc = subprocess.Popen(
            [sys.executable, "tasks.py", "painel"],
            cwd=ROOT,
            env=env,
            stdout=self._log,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if self.proc.poll() is not None:
                raise RuntimeError(
                    f"o painel saiu com código {self.proc.returncode}: {self.log_path}"
                )
            try:
                with urllib.request.urlopen(
                    f"http://localhost:{self.port}/_stcore/health", timeout=2
                ) as r:
                    if r.read().strip() == b"ok":
                        return
            except OSError:
                pass
            time.sleep(0.5)
        self.stop()
        raise TimeoutError(f"o painel não ficou pronto em {timeout:.0f} s: {self.log_path}")

    def stop(self) -> None:
        """Encerra a árvore (tasks.py → streamlit) e espera a porta liberar."""
        if self.proc is not None and self.proc.poll() is None:
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(self.proc.pid)], capture_output=True
            )
            self.proc.wait(timeout=10)
        self.proc = None
        if getattr(self, "_log", None):
            self._log.close()
        end = time.monotonic() + 10
        while port_in_use(self.port) and time.monotonic() < end:
            time.sleep(0.2)

    def __enter__(self) -> Panel:
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()


# ── navegador gravando ────────────────────────────────────────────────────────────────────

CAPTION_JS = """
text => {
  try { sessionStorage.setItem('ensaio-legenda', text); } catch (e) {}
  let el = document.getElementById('ensaio-legenda');
  if (!el) {
    el = document.createElement('div');
    el.id = 'ensaio-legenda';
    el.style.cssText = 'position:fixed;top:8px;left:50%;transform:translateX(-50%);'
      + 'z-index:2147483647;pointer-events:none;background:rgba(20,20,20,.78);color:#fff;'
      + 'font:600 15px/1.3 system-ui,sans-serif;padding:6px 14px;border-radius:6px;'
      + 'max-width:90%;text-align:center;box-shadow:0 2px 6px rgba(0,0,0,.25)';
    document.body.appendChild(el);
  }
  el.textContent = text;
  el.style.display = text ? 'block' : 'none';
}
"""
# Recoloca a legenda depois de um recarregamento completo da página.
CAPTION_RESTORE = (
    "window.addEventListener('DOMContentLoaded', () => { let t = null;"
    " try { t = sessionStorage.getItem('ensaio-legenda'); } catch (e) {}"
    " if (t) (" + CAPTION_JS + ")(t); });"
)


@contextmanager
def recording(video_path: str | Path, *, headless: bool = True, slow_mo: int = 120):
    """Chromium 1280x720 gravando; ao sair, o vídeo vai para `video_path` (.webm)."""
    from playwright.sync_api import sync_playwright

    video_path = Path(video_path)
    tmp_dir = video_path.parent / "_pw"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=slow_mo)
        context = browser.new_context(
            viewport=VIEWPORT, record_video_dir=str(tmp_dir), record_video_size=VIEWPORT,
            locale="pt-BR",
        )  # fmt: skip
        context.add_init_script(CAPTION_RESTORE)
        page = context.new_page()
        page.set_default_timeout(30_000)
        try:
            yield page
        finally:
            video = page.video
            page.close()
            if video:
                video.save_as(str(video_path))
                video.delete()
            context.close()
            browser.close()
    try:
        tmp_dir.rmdir()
    except OSError:
        pass


def set_caption(page, text: str) -> None:
    """Legenda discreta no topo (ex.: "Passo 2: creator cola a peça"). Texto vazio esconde."""
    page.evaluate(CAPTION_JS, text)


def webm_to_mp4(src: str | Path, dst: str | Path, *, keep_src: bool = False) -> Path:
    cmd = [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-an"]
    cmd += ["-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-preset", "veryfast"]
    cmd += ["-pix_fmt", "yuv420p", str(dst)]
    subprocess.run(cmd, check=True)
    if not keep_src:
        Path(src).unlink()
    return Path(dst)


# ── Streamlit: esperas e ações ────────────────────────────────────────────────────────────


def wait_idle(page, timeout: float = 60.0) -> None:
    """Espera o Streamlit terminar de rodar o script.

    Três pistas no DOM: o indicador "Running" (stStatusWidget) some, não sobra esqueleto de
    carregamento (stSkeleton) na área principal e o conteúdo dela fica igual em duas leituras
    seguidas (o indicador demora um pouco a aparecer em páginas lentas).
    """
    probe = (
        "() => { const s = document.querySelector('[data-testid=\"stStatusWidget\"]');"
        " const main = document.querySelector('[data-testid=stMain]');"
        " return { busy: !!(s && s.innerText.trim())"
        " || !!document.querySelector('[data-testid=stMain] [data-testid=stSkeleton]'),"
        " size: main ? main.querySelectorAll('*').length + ':' + main.innerText.length : '' }; }"
    )
    page.wait_for_timeout(250)
    end = time.monotonic() + timeout
    last, stable = None, 0
    while time.monotonic() < end:
        state = page.evaluate(probe)
        stable = stable + 1 if not state["busy"] and state["size"] == last else 0
        if stable >= 2:
            break
        last = state["size"]
        page.wait_for_timeout(200)
    page.wait_for_timeout(150)


def open_home(page, url: str = URL) -> None:
    page.goto(url)
    page.locator('[data-testid="stSidebar"]').wait_for()
    page.locator('[data-testid="stMain"], [data-testid="stAppViewContainer"]').first.wait_for()
    wait_idle(page)


def sidebar(page):
    return page.locator('[data-testid="stSidebar"]')


def selectbox(page, label: str, *, in_sidebar: bool = True):
    """Selectbox pelo rótulo exato (o texto do valor escolhido não conta)."""
    scope = sidebar(page) if in_sidebar else page.locator('[data-testid="stMain"]')
    label_el = page.locator('[data-testid="stWidgetLabel"]').filter(
        has_text=re.compile(rf"^\s*{re.escape(label)}\s*$")
    )
    return scope.locator('[data-testid="stSelectbox"]').filter(has=label_el).first


def select_option(
    page, label: str, option: str, *, in_sidebar: bool = True, exact: bool = True
) -> None:
    """Escolhe no selectbox `label` a opção `option` (exata, ou que contém o texto).

    Às vezes o primeiro clique só dá foco (a página acabou de rodar de novo) e a lista não
    abre: tenta abrir até três vezes, esperando as opções aparecerem.
    """
    box = selectbox(page, label, in_sidebar=in_sidebar).locator('[role="combobox"], input').first
    target = (
        page.get_by_role("option", name=option, exact=True)
        if exact
        else page.get_by_role("option").filter(has_text=option).first
    )
    for attempt in range(3):
        box.click()
        try:
            target.wait_for(state="visible", timeout=3_000)
            break
        except Exception:  # noqa: BLE001
            if attempt == 2:
                raise
            page.keyboard.press("Escape")
            wait_idle(page)
    target.click()
    wait_idle(page)


def choose_role(page, role_label: str) -> None:
    """Papel na barra lateral: "Marca", "Creator" ou "Operações".

    O seletor é um `st.segmented_control` ("Você está vendo como"): no DOM, botões
    `role="radio"` com `aria-checked` dentro de `[data-testid=stButtonGroup]`. Depois do clique,
    espera o campo próprio do papel aparecer (prova de que a página rodou de novo).
    """
    group = sidebar(page).locator('[data-testid="stButtonGroup"]').first
    button = group.get_by_role("radio", name=role_label, exact=True)
    if button.get_attribute("aria-checked") != "true":
        button.click()
    if role_label == "Creator":
        selectbox(page, "Creator").wait_for()
    else:
        sidebar(page).get_by_text("Seu nome (fica registrado nas decisões)").wait_for()
    wait_idle(page)


def choose_creator(page, creator_label: str) -> None:
    """Creator na barra lateral (papel creator), pelo nome ou @handle."""
    select_option(page, "Creator", creator_label, exact=False)


def goto_page(page, name: str) -> None:
    """Página da barra lateral pelo nome do menu (ex.: "Checar peça", "Teste dos agentes").

    Espera o título da página de destino (o h1 do cabeçalho tem o mesmo nome do menu) antes de
    esperar o fim da execução: sem isso, a espera pode terminar ainda na página anterior.
    """
    nav = page.locator('[data-testid="stSidebarNav"]')
    nav.get_by_role("link").filter(has_text=name).first.click()
    try:
        page.wait_for_function(
            "t => [...document.querySelectorAll('[data-testid=stMain] h1')]"
            ".some(h => h.innerText.trim() === t)",
            arg=name,
            timeout=15_000,
        )
    except Exception:  # noqa: BLE001  (página sem h1 com o nome do menu, ex.: Início)
        pass
    wait_idle(page)


def fill_text(page, label: str, text: str, *, typing_delay: int = 25) -> None:
    """Digita na caixa de texto de rótulo `label` (visível no vídeo) e confirma com Ctrl+Enter."""
    box = page.get_by_label(label, exact=True)
    box.click()
    box.fill("")
    box.press_sequentially(text, delay=typing_delay)
    box.press("Control+Enter")
    wait_idle(page)


def click_button(page, name: str) -> None:
    page.get_by_role("button", name=name, exact=True).first.click()
    wait_idle(page)


def pause(page, seconds: float) -> None:
    page.wait_for_timeout(seconds * 1000)
