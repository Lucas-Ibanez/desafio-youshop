"""Gabaritos (T04): import, anonimização, conferência, splits e amostra cega."""

import csv
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

from promessa.rules.loader import load_rules
from promessa.rules.normalize import normalize

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "data" / "gold"


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # @dataclass precisa do módulo registrado
    spec.loader.exec_module(module)
    return module


import_gold = _load_script("import_gold")
blind_sample = _load_script("blind_sample")


def _jsonl(name: str) -> list[dict]:
    with (GOLD / name).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


@pytest.fixture(scope="module")
def h2():
    return _jsonl("h2_anuncios.jsonl")


@pytest.fixture(scope="module")
def h1():
    return _jsonl("h1_reclamacoes.jsonl")


@pytest.fixture(scope="module")
def splits():
    return json.loads((GOLD / "splits.json").read_text(encoding="utf-8"))


# --- Conferência -------------------------------------------------------------------------


def test_conferencia_toda_ok(h2, h1):
    checks = import_gold.conference(h2, h1)
    assert [c.label for c in checks if not c.ok] == []
    assert len(checks) == 17


def test_contagem_divergente_aponta_linhas_e_nao_corrige(h2, h1, capsys):
    changed = [dict(r) for r in h2]
    first_ok = next(r for r in changed if not r["nao_conforme"])
    first_ok["nao_conforme"] = True
    checks = import_gold.conference(changed, h1)
    assert not import_gold.print_conference(checks)
    bad = next(c for c in checks if c.label == "H2 não conformes")
    assert (bad.expected, bad.obtained) == (33, 34)
    assert first_ok["id"] in bad.ids
    out = capsys.readouterr().out
    assert "DIVERGE" in out and "linhas do grupo para investigar" in out


# --- Conteúdo dos gabaritos --------------------------------------------------------------

H2_FIELDS = {
    "id", "familia", "tipo_anunciante", "tipo_produto", "categoria", "texto", "veredito",
    "nao_conforme", "irregular_evidente", "promessa_verificavel", "data_inicio",
}  # fmt: skip
H1_FIELDS = {
    "id", "amostra", "texto", "titulo", "causa", "causa_principal", "subcausa", "canal",
    "categoria_produto", "tipo_produto", "cita_anuncio",
}  # fmt: skip


def test_campos_dos_registros(h2, h1):
    assert all(set(r) == H2_FIELDS for r in h2)
    assert all(set(r) == H1_FIELDS for r in h1)


def test_h1_sem_excluidas(h1):
    ids = {r["id"] for r in h1}
    assert not ids & {"P74", "P81", "P90", "P50", "P54"}
    assert len(ids) == len(h1) == 172


def test_h1_causa_e_subcausa_da_taxonomia(h1):
    by_cause = load_rules().taxonomy.subcauses_by_cause()
    for r in h1:
        assert r["subcausa"] in by_cause[r["causa"]], r["id"]


def test_h2_categorias_mapeadas(h2):
    cats = {r["id"]: r["categoria"] for r in h2}
    assert set(cats.values()) <= {
        "suplemento",
        "cosmetico",
        "infoproduto_renda",
        "infoproduto_outro",
    }
    assert (
        cats["S06"] == "suplemento"
        and cats["S31"] == "cosmetico"
        and cats["R01"] == "infoproduto_renda"
    )
    assert all(cats[r["id"]] == "infoproduto_renda" for r in h2 if r["familia"] == "Renda")


# --- Anonimização ------------------------------------------------------------------------

NOMES = [  # 10 anunciantes e empresas dos apêndices da H2 e da H1, mais pessoas dos títulos
    "Renato Cariani", "Caroline Rafasky", "Seda", "Plantur", "Alpecin",
    "Hotmart", "Kiwify", "Eduzz", "Danki Code", "Clickmax", "Peter Jordan", "Bia Brigatto",
]  # fmt: skip


def _gold_text() -> str:
    parts = [p.read_text(encoding="utf-8") for p in GOLD.glob("*.jsonl")]
    parts += [p.read_text(encoding="utf-8") for p in (GOLD / "recodificacao").glob("*.csv")]
    return normalize("\n".join(parts))


@pytest.mark.parametrize("name", NOMES)
def test_nome_nao_aparece_nos_gabaritos(name):
    pattern = r"(?<!\w)" + r"\s+".join(map(re.escape, normalize(name).split())) + r"(?!\w)"
    assert not re.search(pattern, _gold_text())


def test_sem_links_nos_gabaritos():
    assert "http" not in _gold_text() and "reclameaqui" not in _gold_text()


def test_anonymizer_ignora_maiuscula_e_acento(tmp_path):
    path = tmp_path / "anon.yaml"
    path.write_text(
        'pessoas: ["Ana Lúcia"]\nmarcas: ["Hotmart", "Pai do Low Ticket"]\n', encoding="utf-8"
    )
    anon = import_gold.Anonymizer.from_file(path)
    text = "A ANA LUCIA comprou o curso Pai  do Low Ticket na hotmart; hotmartinho fica."
    assert anon(text) == "A [PESSOA] comprou o curso [MARCA] na [MARCA]; hotmartinho fica."
    assert anon(None) is None


@pytest.mark.skipif(
    not (ROOT / "data" / "raw" / "anon_map.yaml").exists(), reason="data/raw fora do git"
)
def test_import_completo_reproduz_os_gabaritos(h2, h1):
    anon = import_gold.Anonymizer.from_file(ROOT / "data" / "raw" / "anon_map.yaml")
    new_h1, errors = import_gold.build_h1(anon)
    assert errors == []
    assert import_gold.build_h2(anon) == h2
    assert new_h1 == h1


# --- Splits ------------------------------------------------------------------------------


@pytest.mark.parametrize(("key", "n_dev", "n_test"), [("h2", 20, 40), ("h1", 40, 132)])
def test_splits_tamanho_e_cobertura(splits, h2, h1, key, n_dev, n_test):
    rows = {"h2": h2, "h1": h1}[key]
    dev, test = set(splits[key]["dev"]), set(splits[key]["test"])
    assert (len(dev), len(test)) == (n_dev, n_test)
    assert not dev & test
    assert dev | test == {r["id"] for r in rows}


def test_splits_estratificados(splits, h1):
    dev = set(splits["h1"]["dev"])
    for causa in ("acesso", "processo", "promessa", "fraude"):
        group = [r for r in h1 if r["causa_principal"] == causa]
        share = sum(r["id"] in dev for r in group) / len(group)
        assert 0.15 <= share <= 0.32, causa  # 40/172 ≈ 0,23


def test_split_deterministico(h2, h1):
    assert import_gold.build_splits(h2, h1) == import_gold.build_splits(h2, h1)


# --- Amostra cega ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("file", "key", "show", "code"),
    [
        ("h2_recodificar.csv", "h2", blind_sample.H2_SHOW, blind_sample.H2_CODE),
        ("h1_recodificar.csv", "h1", blind_sample.H1_SHOW, blind_sample.H1_CODE),
    ],
)
def test_recodificacao_sem_rotulos(splits, file, key, show, code):
    with (GOLD / "recodificacao" / file).open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        header = reader.fieldnames
    assert header == show + code
    assert len(rows) == 20
    assert all(not row[c] for row in rows for c in code)
    assert {row["id"] for row in rows} <= set(splits[key]["test"])


def test_amostra_cega_nao_sobrescreve_codificacao(tmp_path, monkeypatch):
    monkeypatch.setattr(blind_sample, "OUT", tmp_path)
    monkeypatch.setattr(blind_sample, "ROOT", tmp_path)
    assert blind_sample.main([]) == 0
    path = tmp_path / "h1_recodificar.csv"
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    rows[0]["causa_principal"] = "promessa"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    before = path.read_text(encoding="utf-8")
    assert blind_sample.main([]) == 0
    assert path.read_text(encoding="utf-8") == before
