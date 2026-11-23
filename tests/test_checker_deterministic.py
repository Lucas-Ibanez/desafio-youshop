"""Checador, camada 1 (T06): listas, padrões da H2 e condições da oferta × ficha."""

import time
from datetime import UTC, datetime

import pytest

from promessa.checker.segment import segment
from promessa.checker.service import build_context, run_layer1
from promessa.db.session import get_engine, get_session, init_db
from promessa.facts.seed import load_seed

PRODUCTS = ["prod_treino", "prod_magnesio", "prod_capilar", "prod_canal", "prod_ingles"]


@pytest.fixture(scope="module")
def contexts():
    engine = get_engine("sqlite://")
    init_db(engine)
    with get_session(engine) as s:
        load_seed(s)
        s.commit()
        ctxs = {p: build_context(s, p) for p in PRODUCTS}
    engine.dispose()
    return ctxs


def check(contexts, text, product, published_since=None):
    return run_layer1(text, contexts[product], published_since=published_since)


# (texto, produto, published_since, achados exigidos [(saida, rule_key)], rule_keys proibidos)
CASES = [
    ("acesso vitalício e 30 dias para testar", "prod_treino", None,
     [("bloquear", "COND-ACESSO"), ("bloquear", "COND-GARANTIA")], []),
    ("12 meses de acesso, 7 dias de garantia", "prod_treino", None,
     [("registrar", "COND-ACESSO"), ("registrar", "COND-GARANTIA")], []),
    ("Secar até 5KG EM 7 DIAS", "prod_treino", None,
     [("revisar", "PRAZO-RESULTADO")], ["COND-GARANTIA"]),
    ("veja os resultados melhores que m0unj@r0", "prod_treino", None,
     [("revisar", "MED-COMPARACAO")], []),
    ("bloqueador de açúcar que seca barriga e firma pele em tempo recorde", "prod_magnesio", None,
     [("bloquear", "SUP-EMAG")], []),
    ("Imunidade Forte: nutrientes que blindam sua saúde", "prod_magnesio", None,
     [("bloquear", "SUP-IMUN")], []),
    ("A vitamina B6 auxilia no funcionamento do sistema imune.", "prod_magnesio", None,
     [("registrar", "IN28-B6-02")], ["SUP-IMUN"]),
    ("Vitamina B6 que turbina a sua imunidade", "prod_magnesio", None,
     [("bloquear", "SUP-IMUN")], []),
    ("previne a queda hereditária", "prod_capilar", None,
     [("bloquear", "COS-TERAPEUTICA")], []),
    ("tenha uma RENDA EXTRA de 10K", "prod_canal", None,
     [("revisar", "RENDA-NUMERO")], []),
    ("comece do zero, sem gastar nada", "prod_canal", None,
     [("bloquear", "COND-CUSTO-OCULTO")], []),
    ("sem mensalidade, você paga uma vez só", "prod_ingles", None,
     [("bloquear", "COND-RECORRENCIA")], []),
    ("DESCONTO INÉDITO, Só hoje!!", "prod_ingles", datetime(2026, 1, 8, tzinfo=UTC),
     [("revisar", "URGENCIA-VENCIDA")], ["URGENCIA"]),
    ("Ganhe o e-book de receitas de bônus", "prod_treino", None,
     [("registrar", "COND-BONUS")], []),
    ("Treino de 20 minutos para fazer em casa", "prod_treino", None, [], []),
]  # fmt: skip
IDS = [c[0][:30] for c in CASES]


@pytest.mark.parametrize(("text", "product", "since", "required", "forbidden"), CASES, ids=IDS)
def test_casos_do_plano(contexts, text, product, since, required, forbidden):
    result = check(contexts, text, product, since)
    got = {(f.output.value, f.rule_key) for f in result.findings}
    assert set(required) <= got, got
    assert not {k for _, k in got} & set(forbidden), got
    if not required:
        assert result.findings == [] and result.overall == "limpo"


def _by_key(result):
    return {f.rule_key: f for f in result.findings}


def test_bloqueado_no_exemplo_do_guia(contexts):
    result = check(contexts, "acesso vitalício e 30 dias para testar", "prod_treino")
    assert result.overall == "bloquear"
    acesso = _by_key(result)["COND-ACESSO"]
    assert acesso.excerpt == "acesso vitalício"
    assert acesso.extracted == {"type": "condicao_oferta", "attribute": "acesso",
                                "value": "vitalicio", "unit": None}  # fmt: skip
    assert (
        "12 meses" in acesso.explanation and acesso.suggestion == 'Troque por "12 meses de acesso".'
    )
    assert _by_key(result)["COND-GARANTIA"].suggestion == 'Troque por "7 dias de garantia".'


def test_registrar_extrai_acesso_e_garantia(contexts):
    result = check(contexts, "12 meses de acesso, 7 dias de garantia", "prod_treino")
    assert result.overall == "registrar"
    found = _by_key(result)
    assert (found["COND-ACESSO"].extracted["value"], found["COND-ACESSO"].extracted["unit"]) == (
        "12",
        "meses",
    )
    assert (
        found["COND-GARANTIA"].extracted["value"],
        found["COND-GARANTIA"].extracted["unit"],
    ) == ("7", "dias")


def test_prazo_resultado_extrai_5kg_em_7_dias(contexts):
    finding = _by_key(check(contexts, "Secar até 5KG EM 7 DIAS", "prod_treino"))["PRAZO-RESULTADO"]
    assert finding.extracted["value"] == "5 kg em 7 dias"
    assert finding.extracted["type"] == "resultado"


def test_renda_extrai_promessa(contexts):
    finding = _by_key(check(contexts, "tenha uma RENDA EXTRA de 10K", "prod_canal"))["RENDA-NUMERO"]
    assert finding.excerpt == "RENDA EXTRA de 10K"
    assert finding.extracted["value"] == "renda extra de 10k"


def test_d18_alegacao_literal_registrada_sem_sup_imun(contexts):
    result = check(
        contexts, "A vitamina B6 auxilia no funcionamento do sistema imune.", "prod_magnesio"
    )
    assert [(f.output.value, f.rule_key) for f in result.findings] == [("registrar", "IN28-B6-02")]
    assert "dose mínima" in result.findings[0].explanation


def test_d18_parafrase_bloqueada_com_sugestao_literal(contexts):
    result = check(contexts, "Vitamina B6 que turbina a sua imunidade", "prod_magnesio")
    imun = _by_key(result)["SUP-IMUN"]
    assert "A vitamina B6 auxilia no funcionamento do sistema imune." in imun.suggestion


def test_d18_protecao_so_dentro_do_trecho_permitido(contexts):
    text = "A vitamina B6 auxilia no funcionamento do sistema imune. Imunidade blindada!"
    found = {
        (f.output.value, f.rule_key, f.excerpt)
        for f in check(contexts, text, "prod_magnesio").findings
    }
    assert (
        "registrar",
        "IN28-B6-02",
        "A vitamina B6 auxilia no funcionamento do sistema imune",
    ) in found
    assert ("bloquear", "SUP-IMUN", "Imunidade") in found


def test_urgencia_sem_data_e_recente(contexts):
    sem_data = _by_key(check(contexts, "Só hoje!!", "prod_ingles"))
    assert "URGENCIA" in sem_data and "confirme" in sem_data["URGENCIA"].explanation.lower()
    recente = check(contexts, "Só hoje!!", "prod_ingles", published_since=datetime.now(UTC))
    assert "URGENCIA" in _by_key(recente)


def test_bonus_registra_nome_da_ficha(contexts):
    bonus = _by_key(check(contexts, "Ganhe o e-book de receitas de bônus", "prod_treino"))[
        "COND-BONUS"
    ]
    assert bonus.extracted["value"] == "E-book de receitas"
    sem_bonus = _by_key(check(contexts, "Ganhe um bônus exclusivo", "prod_magnesio"))["COND-BONUS"]
    assert sem_bonus.output.value == "bloquear"


def test_recorrencia_vira_um_achado_so(contexts):
    result = check(contexts, "sem mensalidade, você paga uma vez só", "prod_ingles")
    assert [f.rule_key for f in result.findings] == ["COND-RECORRENCIA"]
    assert "assinatura mensal com renovação automática" in result.findings[0].suggestion


# --- Critérios gerais --------------------------------------------------------------------


def test_todo_bloquear_tem_rule_key_da_versao_ou_cond(contexts):
    for text, product, since, *_ in CASES:
        keys = {r.rule_key for r in contexts[product].rules}
        for f in check(contexts, text, product, since).findings:
            if f.output.value == "bloquear":
                assert f.rule_key in keys or f.rule_key.startswith("COND-"), (text, f.rule_key)


def test_span_recorta_o_excerpt(contexts):
    for text, product, since, *_ in CASES:
        for f in check(contexts, text, product, since).findings:
            assert text[f.span[0] : f.span[1]] == f.excerpt, (text, f)


def test_disclosure(contexts):
    for text, product, since, *_ in CASES:
        result = check(contexts, text, product, since)
        assert result.disclosure.present is False and "#publi" in result.disclosure.suggestion
        with_tag = check(contexts, text + " #publi", product, since)
        assert with_tag.disclosure.present is True and with_tag.disclosure.suggestion is None
        assert with_tag.overall == result.overall  # D5: não muda o overall


def test_camada1_em_menos_de_50ms_por_peca(contexts):
    texts = [(c[0], c[1], c[2]) for c in CASES]
    long_text = " ".join(t for t, *_ in texts)  # uma peça com todos os casos
    texts.append((long_text, "prod_treino", None))
    check(contexts, "aquecimento", "prod_treino")  # compila regex e carrega regras
    for text, product, since in texts:
        start = time.perf_counter()
        check(contexts, text, product, since)
        assert (time.perf_counter() - start) * 1000 < 50, text[:40]


def test_overall_e_o_mais_grave(contexts):
    result = check(contexts, "12 meses de acesso. Secar até 5KG EM 7 DIAS", "prod_treino")
    assert result.overall == "revisar"
    assert result.layers_used == ["regras"]


# --- Segmentação -------------------------------------------------------------------------


def test_segmenta_por_frase_e_linha_com_posicoes():
    text = "Primeira frase. Segunda!!  Terceira?\nQuarta linha\n\n  R$ 5.000 por mês"
    segs = segment(text)
    assert [s.text for s in segs] == [
        "Primeira frase.", "Segunda!!", "Terceira?", "Quarta linha", "R$ 5.000 por mês",
    ]  # fmt: skip
    assert all(text[s.start : s.end] == s.text for s in segs)
