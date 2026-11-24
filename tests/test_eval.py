"""Avaliação (T08): métricas, rodadas versionadas e relatório do checador. Sem rede."""

import json

import eval_checker
import pytest
from metrics import accuracy, cohen_kappa, confusion, precision_recall, wilson

# --- Métricas ----------------------------------------------------------------------------


def test_acuracia_e_kappa():
    gold = [True, True, False, False]
    assert accuracy(gold, [True, False, False, False]) == 0.75
    assert cohen_kappa(gold, gold) == 1.0
    assert cohen_kappa(gold, [True, False, False, False]) == pytest.approx(0.5)
    assert cohen_kappa([True, True], [True, True]) is None  # indefinido


def test_precisao_recall_e_matriz():
    gold = [True, True, False, False]
    pred = [True, False, True, False]
    assert precision_recall(gold, pred, True) == (0.5, 0.5)
    assert precision_recall([False], [False], True) == (None, None)
    assert confusion(gold, pred, [True, False]) == {
        True: {True: 1, False: 1},
        False: {True: 1, False: 1},
    }


def test_wilson():
    lo, hi = wilson(9, 22)
    assert 0.23 < lo < 0.24 and 0.60 < hi < 0.62
    assert wilson(0, 0) is None


# --- Rodadas -----------------------------------------------------------------------------


def test_primeira_rodada_e_v1_e_mudanca_gera_v2():
    fp = {"data/rules/a.yaml": "111", "modelo": "m"}
    first = eval_checker.next_run([], fp, None)
    assert first == {"versao": "v1", "mudancas": "primeira rodada"}
    history = [{**first, "fingerprint": fp}]
    assert eval_checker.next_run(history, fp, None)["versao"] == "v1"  # nada mudou
    changed = eval_checker.next_run(history, {**fp, "data/rules/a.yaml": "222"}, "termo novo")
    assert changed["versao"] == "v2"
    assert "data/rules/a.yaml" in changed["mudancas"] and "termo novo" in changed["mudancas"]


def test_marcas_manuais_sobrevivem(tmp_path, monkeypatch):
    md = tmp_path / "checador_h2.md"
    md.write_text(
        "# x\n\n## Conferência manual (10 extrações sorteadas)\n\n"
        "| id | trecho do anúncio | extraído | certo ou errado |\n|---|---|---|---|\n"
        "| S04 | Secar até 5KG EM 7 DIAS | resultado=5 kg em 7 dias | certo |\n"
        "| R01 | renda | resultado=10k | errado |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(eval_checker, "MD", md)
    assert eval_checker.old_marks() == {"S04": "certo", "R01": "errado"}


# --- Avaliação só com regras (determinística) --------------------------------------------


@pytest.fixture(scope="module")
def gold():
    with (eval_checker.GOLD / "h2_anuncios.jsonl").open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f]
    splits = json.loads((eval_checker.GOLD / "splits.json").read_text(encoding="utf-8"))
    return rows, splits


def test_regras_bloqueiam_as_4_evidentes(gold):
    rows, splits = gold
    preds = eval_checker.predict(rows, with_model=False)
    m = eval_checker.metrics_for(rows, preds)
    assert m["sensibilidade"] == {"acertos": 4, "n": 4, "valor": 1.0}
    assert m["n"] == 60 and m["recall_verificavel"]["n"] == 22


def test_ficha_generica_so_registra_condicao(gold):
    rows, _ = gold
    preds = eval_checker.predict([r for r in rows if r["id"] == "O11"], with_model=False)
    (f,) = preds["O11"].findings
    assert (f["output"], f["rule_key"], f["extracted"]["value"]) == (
        "registrar",
        "COND-ACESSO",
        "vitalicio",
    )


def test_relatorio_mostra_metas_e_evidentes(gold, tmp_path, monkeypatch):
    rows, splits = gold
    for name in ("MD", "JSON", "CSV"):
        monkeypatch.setattr(eval_checker, name, tmp_path / getattr(eval_checker, name).name)
    monkeypatch.setattr(eval_checker, "REPORTS", tmp_path)
    assert eval_checker.main(["--sem-modelo"]) == 0
    md = (tmp_path / "checador_h2.md").read_text(encoding="utf-8")
    for expected in (
        "Vazamentos conhecidos",
        "## Metas do guia",
        "| S06 |",
        "| S22 |",
        "| S25 |",
        "| S26 |",
        "Conferência manual",
        "v1",
        "não rodou",
    ):
        assert expected in md
    assert "✅" in md and "❌" in md
    report = json.loads((tmp_path / "checador_h2.json").read_text(encoding="utf-8"))
    assert report["historico"][0]["versao"] == "v1"
    assert (tmp_path / "erros_checador.csv").exists()
