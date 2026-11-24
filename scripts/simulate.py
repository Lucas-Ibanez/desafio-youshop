"""Simulador de peças, links, vendas e devoluções (T13), com dados fictícios de simulacao.yaml.

Uso: uv run python tasks.py db-reset seed simulate
     uv run python scripts/simulate.py [--modo modelo|gabarito] [--checador-com-modelo]

- Cada creator envia as peças pelo `check_content` real (camada 1; o modelo é opcional) e gera
  links pelo `register_content_and_link`; a cr_ana passa pelo bloqueio e pela correção.
- Vendas e devoluções com semente fixa, datadas no período da simulação.
- Modo `modelo` (padrão): devoluções classificadas pelo `classify_refund` real (com cache).
  Modo `gabarito`: usa a classificação pretendida de cada motivo, sem rede (testes e quando a
  cota do modelo acabou).
"""

from __future__ import annotations

import argparse
import random
import re
import sys
from collections import Counter
from datetime import UTC, datetime, time, timedelta
from pathlib import Path

import yaml
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from promessa.checker.service import check_content
from promessa.db.models import RefundClassification, Sale
from promessa.db.session import session_scope
from promessa.errors import DomainError
from promessa.links.service import register_content_and_link
from promessa.llm.client import LLMResult
from promessa.refunds.classifier import llm_available
from promessa.refunds.linker import LinkerLLMOutput
from promessa.refunds.service import classify_refund

ROOT = Path(__file__).resolve().parent.parent
SIM_FILE = ROOT / "data" / "seeds" / "simulacao.yaml"


def load_config(path: Path = SIM_FILE) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


# --- Modo gabarito: "modelo" que devolve a classificação pretendida ----------------------


def gabarito_completers(meta_by_text: dict[str, dict]):
    def classifier(prompt_name, variables, output_model, model):
        meta = meta_by_text[variables["motivo"]]
        c = meta["classificacao"]
        data = output_model(
            cause=c["cause"],
            subcause=c["subcause"],
            buyer_belief=c.get("buyer_belief"),
            channel_mentioned=None,
            confidence=0.9,
            explanation="classificação do gabarito da simulação",
        )
        return LLMResult(data, model="gabarito-simulacao", prompt_version=prompt_name, cached=False)

    def linker(prompt_name, variables, output_model, model):
        meta = meta_by_text[variables["motivo"]]
        first_id = int(re.search(r"^- (\d+):", variables["promessas"], re.M).group(1))
        relation = meta.get("relacao", "sem_relacao")
        data = LinkerLLMOutput(
            relation=relation,
            promise_id=None if relation == "sem_relacao" else first_id,
            explanation="relação do gabarito da simulação",
        )
        return LLMResult(data, model="gabarito-simulacao", prompt_version=prompt_name, cached=False)

    return classifier, linker


# --- Simulação ---------------------------------------------------------------------------


def _random_moment(rng: random.Random, start: datetime, end: datetime) -> datetime:
    return start + timedelta(seconds=rng.randint(0, int((end - start).total_seconds())))


def _publish(session: Session, creator_id: str, spec: dict, use_llm: bool) -> str:
    """Checa a peça (e a bloqueada antes, se houver) e gera o link. Devolve o link_id."""
    parent = None
    if spec.get("bloqueada"):
        blocked = check_content(
            session, spec["produto"], creator_id, spec["bloqueada"], spec["canal"], use_llm=use_llm
        )
        try:
            register_content_and_link(session, blocked.piece_id)
            raise RuntimeError(f"a peça bloqueada de {creator_id} não foi bloqueada")
        except DomainError as e:
            if e.code != "BLOQUEIO_PENDENTE":
                raise
        parent = blocked.piece_id
    resp = check_content(
        session,
        spec["produto"],
        creator_id,
        spec["texto"],
        spec["canal"],
        parent_piece_id=parent,
        use_llm=use_llm,
    )
    return register_content_and_link(session, resp.piece_id).link_id


def run_simulation(
    session: Session, mode: str = "modelo", checker_llm: bool = False, config: dict | None = None
) -> dict:
    """Roda a simulação inteira na sessão. Devolve o resumo (vendas, devoluções por causa)."""
    cfg = config or load_config()
    if session.scalar(select(func.count()).select_from(Sale)):
        raise SystemExit("Já existem vendas no banco. Rode `tasks.py db-reset seed simulate`.")
    if mode == "modelo" and not llm_available():
        raise SystemExit(
            "Modo modelo sem GEMINI_API_KEY (ou LLM_OFFLINE com cache). Use --modo gabarito."
        )
    rng = random.Random(cfg["semente"])
    start = datetime.combine(datetime.fromisoformat(cfg["periodo"]["inicio"]).date(), time.min, UTC)
    end = datetime.combine(datetime.fromisoformat(cfg["periodo"]["fim"]).date(), time.max, UTC)
    motives = cfg["motivos"]

    plan = []  # (sale, texto, meta)
    meta_by_text: dict[str, dict] = {}
    n_sales = 0
    for persona in cfg["personas"]:
        creator_id = persona["creator"]
        for spec in persona["pecas"]:
            link_id = _publish(session, creator_id, spec, checker_llm)
            price = cfg["precos_cents"][spec["produto"]]
            sales = []
            for _ in range(spec["vendas"]):
                sale = Sale(
                    link_id=link_id,
                    amount_cents=price,
                    commission_cents=price * cfg["comissao_pct"] // 100,
                    created_at=_random_moment(rng, start, end),
                )
                session.add(sale)
                sales.append(sale)
            session.flush()
            n_sales += len(sales)
            refunded = rng.sample(sales, sum(spec["devolucoes"].values()))
            i = 0
            for key, count in spec["devolucoes"].items():
                for _ in range(count):
                    meta = motives[key]
                    text = rng.choice(meta["textos"]) + rng.choice(cfg["variacoes"])
                    meta_by_text[text] = meta
                    plan.append((refunded[i], text, meta))
                    i += 1

    classifier, linker = gabarito_completers(meta_by_text) if mode == "gabarito" else (None, None)
    for sale, text, _meta in plan:
        at = min(
            sale.created_at + timedelta(days=rng.randint(1, 20), hours=rng.randint(0, 23)),
            end + timedelta(days=10),
        )
        classify_refund(session, sale.id, text, completer=classifier, link_completer=linker, at=at)
    session.flush()

    causes = Counter(session.scalars(select(RefundClassification.cause)).all())
    return {
        "vendas": n_sales,
        "devolucoes": len(plan),
        "por_causa": dict(causes.most_common()),
        "modo": mode,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Simulador do MVP (dados fictícios)")
    parser.add_argument("--modo", choices=["modelo", "gabarito"], default="modelo")
    parser.add_argument(
        "--checador-com-modelo", action="store_true", help="liga a camada 2 do checador"
    )
    args = parser.parse_args(argv)
    with session_scope() as session:
        summary = run_simulation(session, args.modo, args.checador_com_modelo)
    n, r = summary["vendas"], summary["devolucoes"]
    print(f"Simulação ({summary['modo']}): {n} vendas, {r} devoluções ({r / n:.1%}).")
    for cause, count in summary["por_causa"].items():
        print(f"  {cause:<22} {count:>3} ({count / r:.0%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
