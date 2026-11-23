"""Carrega e valida os YAML de data/rules/ (CONTEXTO, seção 10).

CLI: `python -m promessa.rules.loader --check [--dir data/rules]` lista cada arquivo com versão
e número de regras e sai com código 1 se algum arquivo for inválido (inclusive sem `fonte` ou
`referencia`), se faltar arquivo ou se houver `rule_key` repetido entre arquivos.
"""

import argparse
import sys
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import ValidationError

from promessa.db.enums import Category
from promessa.rules.schema import (
    In28File,
    ListRule,
    ListRulesFile,
    NormalizationFile,
    OfferConditionsFile,
    PermittedClaim,
    RuleFileHeader,
    TaxonomyFile,
)

RULES_DIR = Path(__file__).resolve().parents[3] / "data" / "rules"

SCHEMAS: dict[str, type[RuleFileHeader]] = {
    "normalizacao": NormalizationFile,
    "suplemento_proibidas": ListRulesFile,
    "suplemento_in28_permitidas": In28File,
    "cosmetico_proibidas": ListRulesFile,
    "padroes_h2": ListRulesFile,
    "condicoes_oferta": OfferConditionsFile,
    "taxonomia_devolucao": TaxonomyFile,
}


class RulesError(Exception):
    """Um ou mais arquivos de regras inválidos. `errors` traz uma linha por problema."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("regras inválidas:\n" + "\n".join(f"- {e}" for e in errors))


@dataclass(frozen=True)
class RuleSet:
    """Todas as regras carregadas e validadas, por `id` do arquivo."""

    files: Mapping[str, RuleFileHeader] = field(default_factory=dict)

    def get(self, file_id: str) -> RuleFileHeader:
        return self.files[file_id]

    @property
    def normalization_map(self) -> Mapping[str, str]:
        return self.files["normalizacao"].mapa

    @property
    def taxonomy(self) -> TaxonomyFile:
        return self.files["taxonomia_devolucao"]

    @property
    def offer_conditions(self) -> OfferConditionsFile:
        return self.files["condicoes_oferta"]

    @property
    def h2_patterns(self) -> ListRulesFile:
        return self.files["padroes_h2"]

    def prohibited_files(self, category: Category) -> list[ListRulesFile]:
        """Listas proibidas da categoria (as que viram `claim_rule` com `kind = proibida`)."""
        return [
            f
            for fid, f in self.files.items()
            if fid.endswith("_proibidas") and f.categoria in (category, "todas")
        ]

    def prohibited_rules(self, category: Category) -> list[ListRule]:
        return [r for f in self.prohibited_files(category) for r in f.regras]

    def permitted_claims(self, category: Category) -> list[PermittedClaim]:
        """Alegações permitidas da categoria (viram `claim_rule` com `kind = permitida`)."""
        return [
            claim
            for f in self.files.values()
            if isinstance(f, In28File) and f.categoria in (category, "todas")
            for claim in f.permitted_claims()
        ]

    def all_rule_keys(self) -> list[str]:
        return [k for f in self.files.values() for k in f.rule_keys()]

    def all_terms(self) -> list[str]:
        """Todos os termos de listas e padrões (sem o `*` de prefixo)."""
        return [
            t.removesuffix("*")
            for f in self.files.values()
            if isinstance(f, ListRulesFile)
            for r in f.regras
            for t in r.termos
        ]


def load_file(path: Path) -> RuleFileHeader:
    """Lê e valida um arquivo. Erros sobem como `RulesError` com o nome do arquivo."""
    try:
        with path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as e:
        raise RulesError([f"{path.name}: não foi possível ler o YAML ({e})"]) from e
    if not isinstance(raw, dict):
        raise RulesError([f"{path.name}: o arquivo precisa ser um mapa YAML"])
    file_id = raw.get("id")
    if file_id != path.stem:
        raise RulesError([f"{path.name}: `id` ({file_id!r}) precisa ser igual ao nome do arquivo"])
    schema = SCHEMAS.get(file_id)
    if schema is None:
        raise RulesError([f"{path.name}: arquivo de regras desconhecido"])
    try:
        return schema.model_validate(raw)
    except ValidationError as e:
        raise RulesError(
            [
                f"{path.name}: {'.'.join(str(p) for p in err['loc']) or '(arquivo)'}: {err['msg']}"
                for err in e.errors()
            ]
        ) from e


def _load_each(rules_dir: Path) -> tuple[dict[str, RuleFileHeader], dict[str, list[str]]]:
    """Carrega cada arquivo esperado. Devolve (válidos, erros por nome de arquivo)."""
    files: dict[str, RuleFileHeader] = {}
    errors: dict[str, list[str]] = {}
    for file_id in SCHEMAS:
        path = rules_dir / f"{file_id}.yaml"
        if not path.exists():
            errors[path.name] = [f"{path.name}: arquivo ausente"]
            continue
        try:
            files[file_id] = load_file(path)
        except RulesError as e:
            errors[path.name] = e.errors
    return files, errors


def _cross_checks(rules_dir: Path, files: Mapping[str, RuleFileHeader]) -> list[str]:
    """Problemas entre arquivos: arquivo desconhecido e `rule_key` repetido."""
    errors = [
        f"{p.name}: arquivo de regras desconhecido"
        for p in sorted(rules_dir.glob("*.yaml"))
        if p.stem not in SCHEMAS
    ]
    keys = Counter(k for f in files.values() for k in f.rule_keys())
    dupes = sorted(k for k, n in keys.items() if n > 1)
    if dupes:
        errors.append(f"rule_key repetido entre arquivos: {', '.join(dupes)}")
    return errors


def _load(rules_dir: Path) -> RuleSet:
    files, per_file = _load_each(rules_dir)
    errors = [line for lines in per_file.values() for line in lines]
    errors += _cross_checks(rules_dir, files)
    if errors:
        raise RulesError(errors)
    return RuleSet(files)


@lru_cache(maxsize=8)
def _load_cached(rules_dir: str) -> RuleSet:
    return _load(Path(rules_dir))


def load_rules(rules_dir: Path | str | None = None) -> RuleSet:
    """Todas as regras, validadas. Carrega uma vez por diretório e reusa no processo."""
    return _load_cached(str(Path(rules_dir or RULES_DIR).resolve()))


def clear_cache() -> None:
    _load_cached.cache_clear()


def check(rules_dir: Path | str | None = None) -> int:
    """Valida e imprime um resumo por arquivo. Devolve 0 (ok) ou 1 (erro)."""
    rules_dir = Path(rules_dir or RULES_DIR)
    print(f"regras em {rules_dir}")
    files, per_file = _load_each(rules_dir)
    for file_id in SCHEMAS:
        name = f"{file_id}.yaml"
        if name in per_file:
            for line in per_file[name]:
                print(f"  ERRO {line}")
            continue
        f = files[file_id]
        extra = f"  status={f.status}" if isinstance(f, In28File) else ""
        print(f"  ok   {name:<32} versao={f.versao}  regras={f.rule_count()}{extra}")
    cross = _cross_checks(rules_dir, files)
    for line in cross:
        print(f"  ERRO {line}")
    ok = not per_file and not cross
    print("OK: regras válidas" if ok else "FALHOU: corrija os erros acima")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Valida as regras de data/rules/")
    parser.add_argument("--check", action="store_true", help="valida e lista os arquivos")
    parser.add_argument("--dir", default=None, help="diretório das regras (padrão: data/rules)")
    args = parser.parse_args(argv)
    if not args.check:
        parser.print_help()
        return 0
    return check(args.dir)


if __name__ == "__main__":
    sys.exit(main())
