"""Carga dos dados fictícios de data/seeds/ (marcas, produtos, fichas v1, creators).

Idempotente: o que já existe no banco é mantido; a ficha v1 só é criada se o produto ainda não
tem ficha. Usado por `scripts/seed.py` e pelos testes.
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from promessa.db.enums import Category
from promessa.db.models import Brand, Creator, Product, ProductFacts
from promessa.facts.service import NameWarning, create_facts_version

SEEDS_DIR = Path(__file__).resolve().parents[3] / "data" / "seeds"


@dataclass
class SeedReport:
    brands: int = 0
    products: int = 0
    facts: int = 0
    creators: int = 0
    warnings: dict[str, list[NameWarning]] = field(default_factory=dict)


def _read(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_seed(session: Session, seeds_dir: Path | None = None) -> SeedReport:
    seeds_dir = seeds_dir or SEEDS_DIR
    report = SeedReport()
    catalog = _read(seeds_dir / "marcas_produtos.yaml")
    for brand in catalog["marcas"]:
        if session.get(Brand, brand["id"]) is None:
            session.add(Brand(id=brand["id"], name=brand["nome"]))
            report.brands += 1
        for prod in brand["produtos"]:
            if session.get(Product, prod["id"]) is None:
                session.add(
                    Product(
                        id=prod["id"],
                        brand_id=brand["id"],
                        name=prod["nome"],
                        category=Category(prod["categoria"]),
                    )
                )
                report.products += 1
            session.flush()
            has_facts = session.scalar(
                select(ProductFacts.id).where(ProductFacts.product_id == prod["id"]).limit(1)
            )
            if has_facts is None:
                result = create_facts_version(session, prod["id"], prod["ficha_v1"], "seed")
                report.facts += 1
                if result.warnings:
                    report.warnings[prod["id"]] = result.warnings
    for creator in _read(seeds_dir / "creators.yaml")["creators"]:
        if session.get(Creator, creator["id"]) is None:
            session.add(
                Creator(
                    id=creator["id"],
                    handle=creator["handle"],
                    display_name=creator["display_name"],
                )
            )
            report.creators += 1
    session.flush()
    return report
