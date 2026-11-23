"""Amostra cega para recodificação humana (T04, CONTEXTO 14.3).

Uso: uv run python scripts/blind_sample.py

Sorteia 20 anúncios (H2) e 20 reclamações (H1) do split `test`, semente 7, e grava CSV SEM
rótulos em data/gold/recodificacao/, com colunas vazias para o Lucas codificar sem olhar a
codificação original. `eval/agreement.py` (TP) compara as duas codificações.
"""

from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "data" / "gold"
OUT = GOLD / "recodificacao"
SEED = 7
N = 20

# Só o que o codificador precisa ler; nada de veredito, causa ou subcausa originais.
H2_SHOW = ["id", "tipo_produto", "texto"]
H2_CODE = ["veredito", "promessa_verificavel", "observacao"]
H1_SHOW = ["id", "titulo", "texto"]
H1_CODE = ["causa_principal", "subcausa", "observacao"]

INSTRUCOES = {
    "h2": "veredito: Conforme | Indício de irregularidade | Irregular evidente; "
    "promessa_verificavel: Sim | Não",
    "h1": "causa_principal: promessa | acesso | processo | fraude | outros; "
    "subcausa: ver data/rules/taxonomia_devolucao.yaml",
}


def read_jsonl(path: Path) -> dict[str, dict]:
    with path.open(encoding="utf-8") as f:
        return {r["id"]: r for r in map(json.loads, f)}


def sample(ids: list[str], seed: int) -> list[str]:
    return sorted(random.Random(seed).sample(sorted(ids), N))


def already_coded(path: Path, code: list[str]) -> bool:
    """True se o arquivo já tem alguma coluna de codificação preenchida (não sobrescrever)."""
    if not path.exists():
        return False
    with path.open(encoding="utf-8", newline="") as f:
        return any((row.get(c) or "").strip() for row in csv.DictReader(f) for c in code)


def write(path: Path, rows: list[dict], show: list[str], code: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=show + code)
        writer.writeheader()
        for r in rows:
            writer.writerow({**{k: r.get(k) or "" for k in show}, **dict.fromkeys(code, "")})


def main(argv: list[str] | None = None) -> int:
    force = "--force" in (sys.argv[1:] if argv is None else argv)
    splits = json.loads((GOLD / "splits.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    for key, file, show, code in [
        ("h2", "h2_anuncios.jsonl", H2_SHOW, H2_CODE),
        ("h1", "h1_reclamacoes.jsonl", H1_SHOW, H1_CODE),
    ]:
        path = OUT / f"{key}_recodificar.csv"
        if already_coded(path, code) and not force:
            print(f"{path.relative_to(ROOT).as_posix()}: já tem codificação; mantido (use --force)")
            continue
        records = read_jsonl(GOLD / file)
        chosen = sample(splits[key]["test"], SEED)
        write(path, [records[i] for i in chosen], show, code)
        print(f"{path.relative_to(ROOT).as_posix()}: {len(chosen)} linhas. {INSTRUCOES[key]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
