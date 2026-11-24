"""Demo de ponta a ponta do exemplo do guia, pelo protocolo MCP (T15).

Uso: uv run python tasks.py demo

Sobe o servidor MCP como subprocesso stdio (`python -m promessa.mcp_server`) sobre um banco só
da demo (var/demo.db, recriado e com seed a cada execução), lista as ferramentas e roda:
1. a marca declarou a ficha → get_product_facts
2. peça com "acesso vitalício e 30 dias para testar" → check_content (2 × bloquear)
3. peça corrigida → check_content (2 × registrar) → register_content_and_link (link)
4. venda + "perdi o acesso, achei que era para sempre" → classify_refund (contradiz)
5. relatório do produto → get_promise_outcome_report (sinal "vitalício" para a marca)
A venda do passo 4 é gravada direto no banco da demo: vendas vêm do pipeline, não do MCP.
"""

from __future__ import annotations

import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

import anyio
from mcp import Client, StdioServerParameters

from promessa.db.models import Sale
from promessa.db.session import get_session, reset_db
from promessa.facts.seed import load_seed

ROOT = Path(__file__).resolve().parent.parent
DEMO_DB = ROOT / "var" / "demo.db"
DEMO_URL = f"sqlite:///{DEMO_DB.as_posix()}"
EXPECTED_TOOLS = {
    "get_product_facts",
    "upsert_product_facts",
    "check_content",
    "register_content_and_link",
    "classify_refund",
    "get_promise_outcome_report",
    "explain_refunds_to_creator",
    "list_review_queue",
    "submit_review",
    "ping",
}

checks: list[tuple[str, bool]] = []


def title(n: int | str, text: str) -> None:
    print(f"\n━━ {n} · {text} " + "━" * max(3, 70 - len(text)))


def show_call(name: str, args: dict[str, Any]) -> None:
    short = ", ".join(f'{k}="{v}"' if isinstance(v, str) else f"{k}={v}" for k, v in args.items())
    print(f"  → {name}({short})")


def out(line: str) -> None:
    print(f"  ← {line}")


def check(label: str, ok: bool) -> None:
    checks.append((label, ok))
    print(f"    {'✅' if ok else '❌'} {label}")


async def call(client: Client, name: str, args: dict[str, Any]) -> dict:
    show_call(name, args)
    result = await client.call_tool(name, args)
    if result.is_error:
        text = "".join(getattr(b, "text", "") for b in result.content)
        out(f"ERRO: {text}")
        return {"_erro": text}
    return result.structured_content


def prepare_db() -> None:
    engine = reset_db(DEMO_URL)
    with get_session(engine) as session:
        load_seed(session)
        session.commit()
    engine.dispose()


def add_sale(link_id: str) -> int:
    from promessa.db.session import get_engine

    engine = get_engine(DEMO_URL)
    with get_session(engine) as session:
        sale = Sale(link_id=link_id, amount_cents=19700, commission_cents=5910)
        session.add(sale)
        session.commit()
        sale_id = sale.id
    engine.dispose()
    return sale_id


async def run() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "promessa.mcp_server"],
        cwd=str(ROOT),
        env={
            "PROMESSA_DB_URL": DEMO_URL,
            "PROMESSA_LOG_LEVEL": "WARNING",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
        },
    )
    async with Client(params) as client:
        title(0, "Servidor MCP promessa-rastreavel (stdio)")
        tools = sorted(t.name for t in (await client.list_tools()).tools)
        out(f"{len(tools)} ferramentas: {', '.join(tools)}")
        check("as 9 ferramentas da seção 9 e o ping", EXPECTED_TOOLS <= set(tools))

        title(1, "A marca declarou a ficha do Treino em Casa 12M")
        facts = await call(client, "get_product_facts", {"product_id": "prod_treino"})
        out(
            f"ficha v{facts['version']}: garantia {facts['guarantee_days']} dias · acesso por "
            f"{facts['access_months']} meses · bônus: {', '.join(facts['bonuses'])}"
        )
        check(
            "garantia 7 dias e acesso 12 meses",
            facts["guarantee_days"] == 7 and facts["access_months"] == 12,
        )
        print("  briefing para o creator:")
        for line in facts["briefing"].splitlines():
            print(f"    | {line}")

        title(2, "A creator cola a peça com a promessa errada")
        first = await call(
            client,
            "check_content",
            {
                "product_id": "prod_treino",
                "creator_id": "cr_ana",
                "channel": "instagram",
                "text": "acesso vitalício e 30 dias para testar",
            },
        )
        for f in first["findings"]:
            out(f'{f["output"].upper()} "{f["excerpt"]}" ({f["rule_key"]}): {f["explanation"]}')
            if f.get("suggestion"):
                print(f"      sugestão: {f['suggestion']}")
        blocks = [f["rule_key"] for f in first["findings"] if f["output"] == "bloquear"]
        check(
            "2 × bloquear (COND-ACESSO, COND-GARANTIA)",
            sorted(blocks) == ["COND-ACESSO", "COND-GARANTIA"],
        )
        refused = await call(client, "register_content_and_link", {"piece_id": first["piece_id"]})
        check(
            "link recusado com BLOQUEIO_PENDENTE", "BLOQUEIO_PENDENTE" in refused.get("_erro", "")
        )

        title(3, "Ela corrige a peça e gera o link")
        second = await call(
            client,
            "check_content",
            {
                "product_id": "prod_treino",
                "creator_id": "cr_ana",
                "channel": "instagram",
                "text": "12 meses de acesso, 7 dias de garantia",
                "parent_piece_id": first["piece_id"],
            },
        )
        for f in second["findings"]:
            out(f'{f["output"].upper()} "{f["excerpt"]}" ({f["rule_key"]})')
        regs = [f["rule_key"] for f in second["findings"] if f["output"] == "registrar"]
        check(
            "2 × registrar e pode gerar link",
            sorted(regs) == ["COND-ACESSO", "COND-GARANTIA"] and second["can_generate_link"],
        )
        link = await call(client, "register_content_and_link", {"piece_id": second["piece_id"]})
        out(
            f"link {link['url']} · promessas presas à venda: "
            + "; ".join(
                f"{p['normalized_text']} ({p['approval']})" for p in link["registered_promises"]
            )
        )
        check(
            "link com acesso 12 meses e garantia 7 dias registradas",
            {p["normalized_text"] for p in link["registered_promises"]}
            == {"acesso 12 meses", "garantia 7 dias"},
        )

        title(4, "Três semanas depois, a venda volta")
        sale_id = add_sale(link["link_id"])
        out(f"venda {sale_id} pelo link {link['link_id']} (gravada pelo pipeline simulado)")
        refund = await call(
            client,
            "classify_refund",
            {"sale_id": sale_id, "reason_text": "perdi o acesso, achei que era para sempre"},
        )
        if "_erro" not in refund:
            out(
                f"{refund['cause']} / {refund['subcause']} · "
                f"relação: {refund['relation'].upper()} · "
                f"pesa no creator: {'sim' if refund['weighs_on_creator'] else 'não'}"
            )
            out(refund["relation_explanation"])
            for note in refund.get("notes", []):
                print(f"      nota: {note}")
        check(
            "promessa explícita / condição da oferta, relação contradiz",
            refund.get("cause") == "promessa_explicita" and refund.get("relation") == "contradiz",
        )
        check("não pesa no creator", refund.get("weighs_on_creator") is False)

        title(5, "O retorno para a marca")
        period = {"start": "2026-10-26", "end": date.today().isoformat()}  # inclui a venda de hoje
        report = await call(
            client, "get_promise_outcome_report", {"product_id": "prod_treino", **period}
        )
        for s in report["sinais_para_a_marca"]:
            out(f'sinal: "{s["rotulo"]}" ({s["devolucoes"]}) · {s["texto"]}')
        barred = report["integridade"]["condicoes_contrarias_barradas"]
        out(
            f"vendas {report['vendas']} · devoluções {report['devolucoes']} · "
            f"condições contrárias barradas antes da venda: {barred}"
        )
        check(
            'sinal "acesso vitalício" para a marca',
            bool(report["sinais_para_a_marca"])
            and report["sinais_para_a_marca"][0]["crenca"] == "acesso vitalicio",
        )


def main() -> int:
    start = time.perf_counter()
    prepare_db()
    anyio.run(run)
    elapsed = time.perf_counter() - start
    failed = [label for label, ok in checks if not ok]
    print()
    if failed:
        print(
            f"Demo terminou com {len(failed)} verificação(ões) falhando: "
            f"{', '.join(failed)} ({elapsed:.0f} s)"
        )
        return 1
    print(f"Demo concluída em {elapsed:.0f} s ({len(checks)} verificações ok).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
