"""Carrega marcas, produtos, fichas v1 e creators fictícios no banco (T05).

Uso: uv run python tasks.py seed   (normalmente depois de `db-reset`)
"""

import sys

from sqlalchemy import func, select

from promessa.db.models import Brand, ClaimRule, Creator, Product, ProductFacts
from promessa.db.session import session_scope
from promessa.facts.seed import load_seed


def main() -> int:
    with session_scope() as session:
        report = load_seed(session)
        totals = {
            name: session.scalar(select(func.count()).select_from(model))
            for name, model in [
                ("marcas", Brand),
                ("produtos", Product),
                ("fichas", ProductFacts),
                ("regras materializadas", ClaimRule),
                ("creators", Creator),
            ]
        }
    print(
        f"Criados agora: {report.brands} marcas, {report.products} produtos, "
        f"{report.facts} fichas v1, {report.creators} creators."
    )
    print("No banco: " + ", ".join(f"{n} {name}" for name, n in totals.items()) + ".")
    for product_id, warnings in report.warnings.items():
        for w in warnings:
            print(f"AVISO {product_id} [{w.rule_key}]: {w.message}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
