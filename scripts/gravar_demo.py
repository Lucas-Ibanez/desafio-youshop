"""Grava o vídeo de demonstração do slide 8 (sem áudio, 1920x1080, 5 clipes + concatenado).

Uso (depois de `uv run python tasks.py db-reset seed simulate`):
    uv run python scripts/gravar_demo.py

Sobe o painel em segundo plano na porta 8501 (sem chave: checador só com regras e explicação
pelo texto fixo), grava cada trecho num contexto novo do Chromium e corta o preparo do começo
(o vídeo do Playwright começa quando a página abre). O trecho 4 chama o servidor MCP de
verdade (SDK `mcp`, stdio) e mostra a saída numa página estilo terminal. Nada é escrito à mão:
os textos na tela vêm do painel ou das respostas do servidor.

Saída em out/demo/: demo_1_ficha.mp4 … demo_5_relatorio.mp4, demo_slide8.mp4, demo_marcas.txt.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "ensaio"))

from common import ffmpeg_exe, video_info  # noqa: E402
from rec_panel import URL, Panel, port_in_use, selectbox  # noqa: E402

OUT = ROOT / "out" / "demo"

# ── Ritmo (ajuste aqui) ─────────────────────────────────────────────────────────────────
TYPE_DELAY_MS = 47  # por caractere (40 a 55)
HOVER_S = 0.4  # mouse parado sobre o botão antes do clique
MOVE_STEPS = 16  # suavidade do movimento do mouse
SCROLL_MS = 700  # rolagens curtas
WAIT_MAX_S = 3.0  # limite de espera na gravação (acima disso, regravar com cache)
WAIT_TIMEOUT_MS = 20_000  # desiste de vez (erro) depois disso

T1_LOOK_HEADER_S = 2.8  # trecho 1: cabeçalho com "v1"
T1_SCROLL_MS = 2600  # rolagem lenta até o briefing e as regras
T1_LOOK_MIDDLE_S = 2.0
T1_HOLD_END_S = 1.5
T2_LOOK_TEXT_S = 0.8  # trecho 2: o marca-texto pinta antes da rolagem até o resultado
T2_HOLD_S = 5.0  # parado no bloqueio
T3_LOOK_RESULT_S = 0.6  # trecho 3: o resultado verde antes de gerar o link
T3_HOLD_S = 4.0  # parado no canhoto
T4_CALL_PAUSE_S = 0.9  # trecho 4: "rodando" antes da saída
T4_READ_1_S = 5.8  # leitura da saída do classify_refund
T4_READ_2_S = 4.2  # leitura da saída do relatório
T4_HOLD_END_S = 5.8  # destaque final
T4_LINE_MS = 28  # intervalo entre linhas da saída
T5_HOLD_FIO_S = 5.0  # trecho 5: parado no fio da marca
T5_CREATOR_S = 3.0  # parado no trecho a mudar da cr_ana
T5_HOLD_END_S = 2.0
TRIM_PAD_S = 0.12  # folga no corte do começo de cada clipe

# O Playwright grava o quadro no tamanho do viewport (o device_scale_factor não amplia o
# vídeo: com 1536x864 e vídeo 1920x1080 sobra uma faixa cinza) e zoom de CSS quebra a largura
# das tabelas e gráficos do Streamlit. Então: grava 1536x864 (o layout de 125% em 1920) e o
# ffmpeg amplia para 1920x1080 (lanczos) na conversão.
VIEWPORT = {"width": 1536, "height": 864}
VIDEO = {"width": 1920, "height": 1080}

BAD = "Treino em casa com acesso vitalício e 30 dias para testar."
FIXED = "Treino em casa com 12 meses de acesso e 7 dias de garantia."
REASON = "perdi o acesso, achei que era para sempre"

CLIPS = [
    ("demo_1_ficha", "Ficha do produto (Marca)"),
    ("demo_2_bloqueio", "Checar peça com bloqueio (Creator)"),
    ("demo_3_canhoto", "Correção, link e canhoto"),
    ("demo_4_mcp", "Servidor MCP: devolução que contradiz"),
    ("demo_5_relatorio", "Devoluções e promessas: sinal para a marca"),
]

# Cursor visível e legenda fixa. O Streamlit recria o HTML a cada interação: um
# MutationObserver recoloca os dois sempre que somem. A legenda só entra no painel.
INIT_SCRIPT = r"""
(() => {
  const PANEL = location.port === '8501';
  function ensure() {
    if (!document.body) return;
    if (PANEL && !document.getElementById('vc-cursor')) {  // no trecho 4 não há interação
      const c = document.createElement('div');
      c.id = 'vc-cursor';
      c.style.cssText = 'position:fixed;left:0;top:0;width:18px;height:18px;border-radius:50%;'
        + 'background:#4B2FA8;opacity:.6;pointer-events:none;z-index:2147483647;'
        + 'transform:translate(-200px,-200px)';
      if (window.__vcXY) c.style.transform = window.__vcXY;
      document.body.appendChild(c);
    }
    if (PANEL && !document.getElementById('vc-legenda-sim')) {
      const l = document.createElement('div');
      l.id = 'vc-legenda-sim';
      l.textContent = 'Dados de venda simulados';
      l.style.cssText = 'position:fixed;left:24px;bottom:20px;z-index:2147483646;'
        + 'pointer-events:none;font:600 18px/1.3 "Schibsted Grotesk",system-ui,sans-serif;'
        + 'color:#5C5770;background:rgba(255,255,255,.9);border:1px solid #DCD8E6;'
        + 'border-radius:6px;padding:8px 14px';
      document.body.appendChild(l);
    }
  }
  // `document` já existe quando o script roda; o <html> ainda não.
  new MutationObserver(ensure).observe(document, {childList: true, subtree: true});
  document.addEventListener('DOMContentLoaded', ensure);
  window.addEventListener('mousemove', e => {
    window.__vcXY = `translate(${e.clientX - 9}px, ${e.clientY - 9}px)`;
    const c = document.getElementById('vc-cursor');
    if (c) c.style.transform = window.__vcXY;
  }, true);
  ensure();
})();
"""

# Rolagem suave do contêiner que rola (no Streamlit é o stMain ou a barra lateral): leva o topo
# do elemento a `pos` (fração da altura visível) em `ms` milissegundos.
SCROLL_JS = r"""
(el, [pos, ms]) => new Promise(res => {
  let sc = el.parentElement;
  while (sc && !(sc.scrollHeight > sc.clientHeight + 2
                 && /(auto|scroll)/.test(getComputedStyle(sc).overflowY))) sc = sc.parentElement;
  if (!sc) { res(0); return; }
  const r = el.getBoundingClientRect(), s = sc.getBoundingClientRect();
  const k = s.height / sc.clientHeight || 1;  // zoom: medidas visuais ÷ medidas de layout
  const max = sc.scrollHeight - sc.clientHeight;
  const off = (r.top - s.top) / k - pos * sc.clientHeight;
  const target = Math.max(0, Math.min(max, sc.scrollTop + off));
  const from = sc.scrollTop, d = target - from, t0 = performance.now();
  if (Math.abs(d) < 3) { res(0); return; }
  const ease = t => t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
  const step = now => {
    const k = Math.min(1, (now - t0) / ms);
    sc.scrollTop = from + d * ease(k);
    if (k < 1) requestAnimationFrame(step); else res(d);
  };
  requestAnimationFrame(step);
})
"""

WAITS: list[tuple[str, str, float]] = []  # (trecho, o que, segundos)


# ── Ações com cara de pessoa ────────────────────────────────────────────────────────────


class Rec:
    """Um clipe: contexto novo gravando; `start()` marca onde o corte começa."""

    def __init__(self, browser, name: str):
        self.name = name
        self.ctx = browser.new_context(
            viewport=VIEWPORT,
            record_video_dir=str(OUT / "_webm"),
            record_video_size=VIEWPORT,
            locale="pt-BR",
        )
        self.ctx.add_init_script(INIT_SCRIPT)
        self.page = self.ctx.new_page()
        self.page.set_default_timeout(WAIT_TIMEOUT_MS)
        self.t0 = time.monotonic()
        self.cut_start = 0.0
        self.cut_end = None

    def start(self) -> None:
        self.page.mouse.move(VIEWPORT["width"] * 0.62, VIEWPORT["height"] * 0.55)
        self.page.wait_for_timeout(250)
        self.cut_start = time.monotonic() - self.t0

    def finish(self) -> Path:
        self.cut_end = time.monotonic() - self.t0
        video = self.page.video
        self.page.close()
        webm = OUT / "_webm" / f"{self.name}.webm"
        video.save_as(str(webm))
        video.delete()
        self.ctx.close()
        return to_mp4(webm, OUT / f"{self.name}.mp4", self.cut_start + TRIM_PAD_S, self.cut_end)


def to_mp4(src: Path, dst: Path, start: float, end: float) -> Path:
    cmd = [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(src)]
    cmd += ["-ss", f"{start:.3f}", "-to", f"{end:.3f}"]
    cmd += ["-vf", f"scale={VIDEO['width']}:{VIDEO['height']}:flags=lanczos"]
    cmd += ["-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p"]
    cmd += ["-r", "30", "-an", str(dst)]
    subprocess.run(cmd, check=True)
    return dst


def timed_wait(clip: str, what: str, fn) -> None:
    t = time.monotonic()
    fn()
    WAITS.append((clip, what, round(time.monotonic() - t, 2)))


def settle(page) -> None:
    """Fim da execução do Streamlit: sem "Running" e sem esqueleto, em duas leituras."""
    probe = (
        "() => { const s = document.querySelector('[data-testid=stStatusWidget]');"
        " return !(s && s.innerText.trim())"
        " && !document.querySelector('[data-testid=stMain] [data-testid=stSkeleton]'); }"
    )
    page.wait_for_timeout(120)
    ok = 0
    end = time.monotonic() + WAIT_TIMEOUT_MS / 1000
    while ok < 2 and time.monotonic() < end:
        ok = ok + 1 if page.evaluate(probe) else 0
        page.wait_for_timeout(120)


def scroll_to(page, locator, pos: float = 0.12, ms: int = SCROLL_MS) -> None:
    locator.evaluate(SCROLL_JS, [pos, ms])
    page.wait_for_timeout(60)


def human_click(page, locator, *, hover: float = HOVER_S) -> None:
    """Leva o mouse até o centro do elemento, para `hover` segundos e clica."""
    box = locator.bounding_box()
    if box is None or box["y"] < 40 or box["y"] + box["height"] > VIEWPORT["height"] - 70:
        scroll_to(page, locator, 0.4)
        box = locator.bounding_box()
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(x, y, steps=MOVE_STEPS)
    page.wait_for_timeout(int(hover * 1000))
    page.mouse.click(x, y)


def human_type(page, locator, text: str) -> None:
    human_click(page, locator, hover=0.2)
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    page.keyboard.type(text, delay=TYPE_DELAY_MS)
    page.keyboard.press("Control+Enter")  # o text_area do Streamlit confirma o valor assim
    settle(page)


def role(page, clip: str, label: str) -> None:
    button = page.locator('[data-testid="stSidebar"] [data-testid="stButtonGroup"]').get_by_role(
        "radio", name=label, exact=True
    )
    human_click(page, button)
    field = (
        selectbox(page, "Creator")
        if label == "Creator"
        else page.locator('[data-testid="stSidebar"]').get_by_text("Seu nome")
    )
    timed_wait(clip, f"papel {label}", lambda: (field.first.wait_for(), settle(page)))


def nav(page, clip: str, title: str) -> None:
    link = page.locator('[data-testid="stSidebarNav"]').get_by_role("link").filter(has_text=title)
    human_click(page, link.first)
    h1 = page.locator('[data-testid="stMain"] h1').filter(has_text=title)
    timed_wait(clip, f"página {title}", lambda: (h1.first.wait_for(), settle(page)))


def choose_product(page, clip: str, product: str = "prod_treino") -> None:
    box = selectbox(page, "Produto", in_sidebar=False).locator('[role="combobox"], input').first
    option = page.get_by_role("option").filter(has_text=product).first
    for attempt in range(3):
        human_click(page, box, hover=0.25)
        try:
            option.wait_for(state="visible", timeout=2_500)
            break
        except Exception:  # noqa: BLE001  (o primeiro clique às vezes só dá foco)
            if attempt == 2:
                raise
            page.keyboard.press("Escape")
            settle(page)
    human_click(page, option, hover=0.25)
    timed_wait(clip, "produto", lambda: settle(page))


# Preparo rápido (fica fora do corte): mesmas ações sem ritmo de pessoa.
def quick_setup(page, role_label: str, title: str | None, product: bool = False) -> None:
    page.goto(URL)
    page.locator('[data-testid="stSidebar"]').wait_for()
    settle(page)
    group = page.locator('[data-testid="stSidebar"] [data-testid="stButtonGroup"]')
    button = group.get_by_role("radio", name=role_label, exact=True)
    if button.get_attribute("aria-checked") != "true":
        button.click()
        settle(page)
    if title:
        page.locator('[data-testid="stSidebarNav"]').get_by_role("link").filter(
            has_text=title
        ).first.click()
        page.locator('[data-testid="stMain"] h1').filter(has_text=title).first.wait_for()
        settle(page)
    if product:
        box = selectbox(page, "Produto", in_sidebar=False).locator('[role="combobox"], input')
        option = page.get_by_role("option").filter(has_text="prod_treino").first
        for _ in range(3):
            box.first.click()
            try:
                option.wait_for(state="visible", timeout=2_500)
                break
            except Exception:  # noqa: BLE001
                page.keyboard.press("Escape")
                settle(page)
        option.click()
        settle(page)


def textarea(page):
    return page.get_by_label("Texto da peça", exact=True)


def button(page, name: str):
    return page.get_by_role("button", name=name, exact=True).first


# ── Trechos do painel ───────────────────────────────────────────────────────────────────


def clip_1(browser) -> Path:
    rec = Rec(browser, "demo_1_ficha")
    p = rec.page
    quick_setup(p, "Marca", None)
    rec.start()
    nav(p, "1", "Ficha do produto")
    current = selectbox(p, "Produto", in_sidebar=False).inner_text()
    if "prod_treino" not in current:
        choose_product(p, "1")
    p.wait_for_timeout(int(T1_LOOK_HEADER_S * 1000))
    scroll_to(p, p.get_by_text("Condições da oferta").first, 0.08, T1_SCROLL_MS // 2)
    p.wait_for_timeout(int(T1_LOOK_MIDDLE_S * 1000))
    scroll_to(p, p.get_by_text("Regras desta versão").first, 0.30, T1_SCROLL_MS // 2)
    p.wait_for_timeout(int(T1_HOLD_END_S * 1000))
    return rec.finish()


def clip_2(browser) -> Path:
    rec = Rec(browser, "demo_2_bloqueio")
    p = rec.page
    quick_setup(p, "Marca", "Ficha do produto", product=True)
    rec.start()
    role(p, "2", "Creator")
    nav(p, "2", "Checar peça")
    choose_product(p, "2")
    scroll_to(p, p.get_by_text("Texto da peça", exact=True).first, 0.30)
    human_type(p, textarea(p), BAD)
    human_click(p, button(p, "Checar peça"))
    timed_wait("2", "resultado", lambda: (p.locator(".vc-peca").first.wait_for(), settle(p)))
    p.wait_for_timeout(int(T2_LOOK_TEXT_S * 1000))
    scroll_to(p, p.locator(".vc-resultado").first, 0.06, 800)
    p.mouse.move(VIEWPORT["width"] * 0.9, VIEWPORT["height"] * 0.5, steps=MOVE_STEPS)
    p.wait_for_timeout(int(T2_HOLD_S * 1000))
    return rec.finish()


def clip_3(browser) -> Path:
    rec = Rec(browser, "demo_3_canhoto")
    p = rec.page
    quick_setup(p, "Creator", "Checar peça", product=True)
    textarea(p).fill(BAD)
    textarea(p).press("Control+Enter")
    settle(p)
    button(p, "Checar peça").click()
    p.locator(".vc-peca").first.wait_for()
    settle(p)
    p.get_by_text("Texto da peça", exact=True).first.evaluate(SCROLL_JS, [0.25, 10])
    p.wait_for_timeout(300)
    rec.start()
    human_type(p, textarea(p), FIXED)
    human_click(p, button(p, "Checar peça"))
    chip = p.locator(".vc-resultado .vc-chip--registrar")
    timed_wait("3", "resultado", lambda: (chip.first.wait_for(), settle(p)))
    p.wait_for_timeout(int(T3_LOOK_RESULT_S * 1000))
    scroll_to(p, button(p, "Gerar link"), 0.30, 800)
    human_click(p, button(p, "Gerar link"))
    timed_wait("3", "canhoto", lambda: p.locator(".vc-canhoto").first.wait_for())
    p.wait_for_timeout(450)  # o carimbo cai (~0,5 s)
    scroll_to(p, p.locator(".vc-canhoto").first, 0.28, 600)
    p.mouse.move(VIEWPORT["width"] * 0.93, VIEWPORT["height"] * 0.22, steps=MOVE_STEPS)
    p.wait_for_timeout(int(T3_HOLD_S * 1000))
    return rec.finish()


def open_thread(p, clip: str, label: str, anchor: str) -> None:
    """Abre o expander do fio; antes, rola até `anchor` (título acima) para o quadro começar
    numa borda limpa."""
    summary = p.locator('[data-testid="stMain"] [data-testid="stExpander"] summary').filter(
        has_text=label
    )
    scroll_to(p, p.get_by_text(anchor, exact=True).first, 0.04, 650)
    human_click(p, summary.first)
    fio = p.locator('[data-testid="stExpander"]').filter(has_text=label).locator(".vc-fio")
    timed_wait(clip, f"fio {label}", lambda: fio.first.wait_for())
    p.wait_for_timeout(650)  # a linha se desenha (~0,5 s) e o rótulo aparece


def clip_5(browser) -> Path:
    rec = Rec(browser, "demo_5_relatorio")
    p = rec.page
    quick_setup(p, "Marca", "Devoluções e promessas", product=True)
    p.get_by_text("Sinais para a marca").first.evaluate(SCROLL_JS, [0.12, 10])
    p.wait_for_timeout(300)
    rec.start()
    open_thread(p, "5", "acesso vitalício", "Promessas mais contestadas")
    p.mouse.move(VIEWPORT["width"] * 0.93, VIEWPORT["height"] * 0.2, steps=MOVE_STEPS)
    p.wait_for_timeout(int(T5_HOLD_FIO_S * 1000))
    role(p, "5", "Creator")
    open_thread(p, "5", "5KG", "Devoluções por causa")
    p.wait_for_timeout(int(T5_CREATOR_S * 1000))
    role(p, "5", "Marca")
    open_thread(p, "5", "acesso vitalício", "Promessas mais contestadas")
    p.mouse.move(VIEWPORT["width"] * 0.93, VIEWPORT["height"] * 0.2, steps=MOVE_STEPS)
    p.wait_for_timeout(int(T5_HOLD_END_S * 1000))
    return rec.finish()


# ── Trecho 4: servidor MCP de verdade ───────────────────────────────────────────────────


def add_simulated_sale() -> tuple[int, str]:
    """Venda simulada no link gerado no trecho 3 (vendas vêm do pipeline, não do MCP)."""
    from sqlalchemy import select

    from promessa.db.models import Sale, TrackedLink
    from promessa.db.session import get_engine, get_session

    engine = get_engine(f"sqlite:///{(ROOT / 'var' / 'promessa.db').as_posix()}")
    with get_session(engine) as s:
        link = s.scalars(
            select(TrackedLink)
            .where(TrackedLink.creator_id == "cr_ana", TrackedLink.product_id == "prod_treino")
            .order_by(TrackedLink.created_at.desc())
        ).first()
        if link is None:
            raise RuntimeError("nenhum link do trecho 3 no banco")
        sale = Sale(link_id=link.id, amount_cents=19700, commission_cents=5910)
        s.add(sale)
        s.commit()
        sale_id, link_id = sale.id, link.id
    engine.dispose()
    return sale_id, link_id


def mcp_calls(sale_id: int) -> list[tuple[str, dict, dict]]:
    import anyio
    from mcp import Client, StdioServerParameters

    calls = [
        ("classify_refund", {"sale_id": sale_id, "reason_text": REASON}),
        ("get_promise_outcome_report", {"product_id": "prod_treino"}),
    ]
    results: list[tuple[str, dict, dict]] = []

    async def run() -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "promessa.mcp_server"],
            cwd=str(ROOT),
            env={"PROMESSA_LOG_LEVEL": "WARNING", "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
        )
        async with Client(params) as client:
            for name, args in calls:
                res = await client.call_tool(name, args)
                if res.is_error:
                    text = "".join(getattr(b, "text", "") for b in res.content)
                    raise RuntimeError(f"{name}: {text}")
                results.append((name, args, res.structured_content))

    # O Playwright (API síncrona) mantém um laço de eventos nesta thread: o cliente MCP roda
    # na sua própria thread.
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(anyio.run, run).result()
    return results


def fmt_value(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def terminal_lines(results: list[tuple[str, dict, dict]]) -> list[list[tuple[str, str]]]:
    """Blocos de linhas [(classe, texto)] a partir das respostas reais do servidor."""
    blocks = []
    (n1, a1, r1), (n2, a2, r2) = results
    # classify_refund: todos os campos, na ordem da resposta
    head = f"● promessa · {n1}(" + ", ".join(f"{k}={fmt_value(v)}" for k, v in a1.items()) + ")"
    out = []
    for k, v in r1.items():
        if isinstance(v, dict):
            v = {kk: vv for kk, vv in v.items()}
        out.append(("k", f"  {k}: {fmt_value(v)}"))
    blocks.append([("call", head)] + out)
    # relatório: totais, sinais para a marca e promessas cobradas (causas e cobertura: painel)
    head2 = f"● promessa · {n2}(" + ", ".join(f"{k}={fmt_value(v)}" for k, v in a2.items()) + ")"
    out2 = [
        ("k", f"  periodo: {fmt_value(r2['periodo'])}"),
        ("k", f"  vendas: {r2['vendas']}   devolucoes: {r2['devolucoes']}"),
        ("k", "  sinais_para_a_marca:"),
    ]
    for s in r2["sinais_para_a_marca"]:
        out2.append(("k", f"    - crenca: {fmt_value(s['crenca'])}  devolucoes: {s['devolucoes']}"
                          f"  creators: {fmt_value(s['creators'])}"))  # fmt: skip
    out2.append(("k", "  promessas_mais_contestadas:"))
    for c in r2["promessas_mais_contestadas"]:
        line = f"    - promessa: {fmt_value(c['promessa'])}  devolucoes: {c['devolucoes']}"
        out2.append(("k", line + f"  trecho: {fmt_value(c['trecho'])}"))
    out2.append(("dim", "  (causas, cobertura e operação: no painel)"))
    blocks.append([("call", head2)] + out2)
    # destaque final, com os valores da resposta do classify_refund
    blocks.append(
        [
            ("hl", f"causa   = {r1['cause']} / {r1['subcause']}"),
            ("hl", f'relação = "{r1["relation"]}"'),
            (
                "hl",
                "não pesa no creator"
                if r1["weighs_on_creator"] is False
                else f"weighs_on_creator = {r1['weighs_on_creator']}",
            ),  # fmt: skip
        ]
    )
    return blocks


TERMINAL_HTML = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<style>
@font-face {{ font-family: "IBM Plex Mono"; src: url("{font_r}") format("woff2");
  font-weight: 400; }}
@font-face {{ font-family: "IBM Plex Mono"; src: url("{font_m}") format("woff2");
  font-weight: 500; }}
html, body {{ margin: 0; height: 100%; background: #1E1A2E; }}
body {{ color: #E9E6F2; font: 400 22px/1.32 "IBM Plex Mono", ui-monospace, monospace; }}
#topo {{ padding: 18px 40px 10px; color: #9A95AB; font-size: 17px;
  border-bottom: 1px solid #3A3450; }}
#t {{ padding: 14px 40px 56px; height: calc(100% - 116px); overflow: hidden; }}
.l {{ white-space: pre-wrap; word-break: break-word; display: none; }}
.l.on {{ display: block; }}  /* linha escondida não ocupa espaço: a rolagem segue o que já saiu */
.call {{ color: #C9BCFF; font-weight: 500; margin-top: 18px; }}
.k {{ color: #E9E6F2; }}
.dim {{ color: #9A95AB; }}
.wait {{ color: #9A95AB; }}
#hl {{ margin: 22px 0 0; padding: 16px 22px; border: 2px solid #8CE0DF; border-radius: 10px;
       background: rgba(14,124,123,.18); display: none; }}
#hl.on {{ display: block; }}
#hl .l {{ color: #FFFFFF; font-weight: 500; font-size: 26px; }}
#rodape {{ position: fixed; left: 40px; bottom: 16px; color: #9A95AB; font-size: 15px; }}
</style></head><body>
<div id="topo">cliente MCP → servidor promessa-rastreavel (stdio)</div>
<div id="t">{body}<div id="hl">{hl}</div></div>
<div id="rodape">Saída real do servidor MCP</div>
<script>
window.showLine = id => {{ const e = document.getElementById(id); if (e) e.classList.add('on');
  const t = document.getElementById('t'); t.scrollTop = t.scrollHeight; }};
window.showHl = () => {{ const h = document.getElementById('hl'); h.classList.add('on');
  h.querySelectorAll('.l').forEach(e => e.classList.add('on'));
  const t = document.getElementById('t'); t.scrollTop = t.scrollHeight; }};
</script></body></html>"""


def clip_4(browser, results) -> Path:
    blocks = terminal_lines(results)
    calls, highlight = blocks[:2], blocks[2]
    body, ids = [], []
    for b, block in enumerate(calls):
        group = []
        for i, (cls, text) in enumerate(block):
            lid = f"b{b}l{i}"
            body.append(f'<div class="l {cls}" id="{lid}">{escape(text)}</div>')
            group.append(lid)
        body.append(f'<div class="l wait" id="w{b}">  … chamando a ferramenta</div>')
        ids.append(group)
    hl = "".join(f'<div class="l">{escape(t)}</div>' for _, t in highlight)
    fonts = ROOT / "app" / "static" / "fonts"
    html = TERMINAL_HTML.format(
        font_r=(fonts / "IBMPlexMono-Regular.woff2").as_uri(),
        font_m=(fonts / "IBMPlexMono-Medium.woff2").as_uri(),
        body="\n".join(body),
        hl=hl,
    )
    page_file = OUT / "_mcp.html"
    page_file.write_text(html, encoding="utf-8")

    rec = Rec(browser, "demo_4_mcp")
    p = rec.page
    p.goto(page_file.as_uri())
    p.evaluate("() => document.fonts.ready")
    p.wait_for_timeout(300)
    rec.start()
    reads = [T4_READ_1_S, T4_READ_2_S]
    for b, group in enumerate(ids):
        p.evaluate("id => window.showLine(id)", group[0])  # a chamada
        p.evaluate("id => window.showLine(id)", f"w{b}")
        p.wait_for_timeout(int(T4_CALL_PAUSE_S * 1000))
        p.evaluate(
            "id => { const e = document.getElementById(id); e.style.display = 'none'; }", f"w{b}"
        )
        for lid in group[1:]:
            p.evaluate("id => window.showLine(id)", lid)
            p.wait_for_timeout(T4_LINE_MS)
        p.wait_for_timeout(int(reads[b] * 1000))
    p.evaluate("() => window.showHl()")
    p.wait_for_timeout(int(T4_HOLD_END_S * 1000))
    return rec.finish()


# ── Concatenação e marcas ───────────────────────────────────────────────────────────────


def concat(clips: list[Path]) -> Path:
    listing = OUT / "_lista.txt"
    listing.write_text(
        "".join(f"file '{c.resolve().as_posix()}'\n" for c in clips), encoding="utf-8"
    )
    final = OUT / "demo_slide8.mp4"
    cmd = [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0"]
    cmd += ["-i", str(listing), "-c", "copy", "-movflags", "+faststart", str(final)]
    subprocess.run(cmd, check=True)
    listing.unlink()
    return final


def write_marks(clips: list[Path], final: Path) -> str:
    lines, t = [], 0.0
    for (name, title), clip in zip(CLIPS, clips, strict=True):
        d = video_info(clip)["seconds"]
        lines.append(f"{name}  {t:6.2f} s → {t + d:6.2f} s  ({d:5.2f} s)  {title}")
        t += d
    info = video_info(final)
    lines.append(f"total  {info['seconds']:.2f} s  ·  {info['size']}  ·  30 fps")
    text = "\n".join(lines) + "\n"
    (OUT / "demo_marcas.txt").write_text(text, encoding="utf-8")
    return text


def warm_up(browser) -> None:
    """Visita as páginas uma vez antes de gravar (fora do vídeo): a primeira abertura de cada
    página depois de subir o painel carrega os módulos e passa de 3 s."""
    ctx = browser.new_context(viewport=VIEWPORT)
    page = ctx.new_page()
    page.set_default_timeout(WAIT_TIMEOUT_MS)
    quick_setup(page, "Marca", "Ficha do produto", product=True)
    for title in ("Devoluções e promessas", "Checar peça"):
        page.locator('[data-testid="stSidebarNav"]').get_by_role("link").filter(
            has_text=title
        ).first.click()
        page.locator('[data-testid="stMain"] h1').filter(has_text=title).first.wait_for()
        settle(page)
    ctx.close()


def main() -> int:
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "_webm").mkdir(exist_ok=True)
    if port_in_use():
        print("a porta 8501 está em uso: feche o painel aberto")
        return 1
    clips: list[Path] = []
    with Panel(OUT / "_painel.log"):
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            warm_up(browser)
            clips.append(clip_1(browser))
            clips.append(clip_2(browser))
            clips.append(clip_3(browser))
            sale_id, link_id = add_simulated_sale()
            results = mcp_calls(sale_id)
            (OUT / "_mcp_saida.json").write_text(
                json.dumps(
                    {"venda": sale_id, "link": link_id, "chamadas": results},
                    ensure_ascii=False,
                    indent=1,
                ),
                encoding="utf-8",
            )
            clips.append(clip_4(browser, results))
            clips.append(clip_5(browser))
            browser.close()
    final = concat(clips)
    print(write_marks(clips, final))
    slow = [w for w in WAITS if w[2] > WAIT_MAX_S]
    print("esperas na gravação (s):", ", ".join(f"T{c} {w} {s}" for c, w, s in WAITS))
    if slow:
        print("ESPERAS ACIMA DE", WAIT_MAX_S, "s:", slow)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
