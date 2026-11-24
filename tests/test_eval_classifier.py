"""Avaliação do classificador (T12) sem rede: métricas, critério de corte e relatório."""

import json

import eval_classifier as ev
import pytest


@pytest.fixture(scope="module")
def rows():
    with (ev.GOLD / "h1_reclamacoes.jsonl").open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def perfect(rows):
    return {
        r["id"]: {
            "cause": r["causa"],
            "subcause": r["subcausa"],
            "main_cause": r["causa_principal"],
            "confidence": 0.9,
            "explanation": "",
            "source": "modelo",
            "buyer_belief": None,
        }
        for r in rows
    }


def test_subtipo():
    assert ev.subtype("promessa_explicita", "condicao_da_oferta") == "condicao_da_oferta"
    assert ev.subtype("promessa_expectativa", "qualidade_abaixo") == "expectativa"
    assert ev.subtype("acesso_entrega", "login_conta") == "nao_promessa"


def test_metricas_com_predicao_perfeita(rows):
    m = ev.metrics_for(rows, perfect(rows))
    assert (m["n"], m["acuracia"], m["kappa"]) == (172, 1.0, 1.0)
    assert m["subtipo"] == {"n": 44, "acuracia": 1.0}
    assert m["promessa_explicita"]["n_gold"] == 27 and m["promessa_explicita"]["precisao"] == 1.0
    assert m["corte"]["n"] == 59 + 55 + 44
    assert m["matriz"]["acesso"]["acesso"] == 59


def test_metricas_com_erro_de_promessa_para_acesso(rows):
    preds = perfect(rows)
    promise_ids = [r["id"] for r in rows if r["causa"] == "promessa_explicita"][:10]
    for i in promise_ids:
        preds[i].update(cause="acesso_entrega", subcause="acesso_nao_liberado", main_cause="acesso")
    m = ev.metrics_for(rows, preds)
    assert m["matriz"]["promessa"]["acesso"] == 10
    assert m["promessa_explicita"]["recall"] == pytest.approx(17 / 27)
    assert m["promessa_explicita"]["precisao"] == 1.0
    assert m["subtipo"]["acuracia"] == pytest.approx(34 / 44)


def test_criterio_de_corte(rows):
    verdict, text = ev.cut_verdict(ev.metrics_for(rows, perfect(rows)))
    assert verdict == "sim" and "100%" in text
    bad = perfect(rows)
    for r in rows:
        if r["causa_principal"] == "processo":
            bad[r["id"]].update(cause="acesso_entrega", subcause="login_conta", main_cause="acesso")
    verdict, _ = ev.cut_verdict(ev.metrics_for(rows, bad))
    assert verdict == "não"


def test_relatorio(rows):
    splits = json.loads((ev.GOLD / "splits.json").read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in rows}
    parts = {
        "dev": [by_id[i] for i in splits["h1"]["dev"]],
        "test": [by_id[i] for i in splits["h1"]["test"]],
        "total": rows,
    }
    preds = perfect(rows)
    metrics = {"parafrase": {s: ev.metrics_for(parts[s], preds) for s in ev.SPLITS}}
    report = {
        "data": "hoje",
        "rodada": {"versao": "v1", "mudancas": "primeira rodada"},
        "modelo": "m",
        "exemplos": ["H08"],
        "avisos": [],
        "metricas": json.loads(json.dumps(metrics, default=str)),
        "historico": [
            {
                "versao": "v1",
                "data": "hoje",
                "mudancas": "primeira rodada",
                "acuracia_test": 1.0,
                "kappa_test": 1.0,
            }
        ],
    }
    md = ev.render_md(report)
    for expected in (
        "Vazamentos conhecidos",
        "Critério de corte",
        "separa promessa de acesso e processo com acerto aceitável? SIM.**",
        "## Metas do guia",
        "Matriz de confusão",
        "| promessa | **",
        "precisão",
        "v1",
    ):
        assert expected in md
    assert "✅" in md


def test_sem_modelo_nao_grava(capsys):
    assert ev.main([]) == 1  # testes padrão: sem chave
    assert "precisa do modelo" in capsys.readouterr().out
