"""Regras como dados (T03): normalização, carregador, consistência dos YAML."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from promessa.db.enums import Category
from promessa.rules.loader import RULES_DIR, RulesError, check, load_rules
from promessa.rules.normalize import deleet, match_text, normalize

ROOT = Path(__file__).resolve().parent.parent

# --- Normalização ------------------------------------------------------------------------


def test_normalize_minusculas_sem_acento_mesmo_comprimento():
    original = "Só HOJE!!"
    assert normalize(original) == "so hoje!!"
    assert len(normalize(original)) == len(original)


@pytest.mark.parametrize(
    "text",
    ["Ação, coração e pão", "ÇÃO É ÓTIMO", "Garantia de 7 dias ✅ 🚀", "İstanbul ß ﬁ", "R$ 5.000"],
)
def test_normalize_preserva_comprimento(text):
    assert len(normalize(text)) == len(text)


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("m0unj@r0", "mounjaro"),
        ("10K", "10k"),
        ("s3ca", "seca"),
        ("gr4tis", "gratis"),
        ("5KG", "5kg"),
        ("B6", "b6"),
        ("omega3", "omega3"),
        ("R$", "r$"),
        ("@perfil", "@perfil"),
        ("Vitalício", "vitalicio"),
    ],
)
def test_deleet(token, expected):
    assert deleet(token) == expected
    assert len(deleet(token)) == len(token)


def test_match_text_desfaz_disfarce_e_preserva_posicoes():
    text = "veja os resultados melhores que m0unj@r0!"
    out = match_text(text)
    assert out == "veja os resultados melhores que mounjaro!"
    assert len(out) == len(text)


# --- Carregador --------------------------------------------------------------------------


def test_carrega_os_7_arquivos():
    rules = load_rules()
    assert set(rules.files) == {
        "normalizacao",
        "suplemento_proibidas",
        "suplemento_in28_permitidas",
        "cosmetico_proibidas",
        "padroes_h2",
        "condicoes_oferta",
        "taxonomia_devolucao",
    }


def test_rule_key_unico_entre_arquivos():
    keys = load_rules().all_rule_keys()
    assert len(keys) == len(set(keys))
    for expected in [
        "SUP-EMAG",
        "SUP-IMUN",
        "COS-TERAPEUTICA",
        "URGENCIA-VENCIDA",
        "COND-GARANTIA",
    ]:
        assert expected in keys


def test_rule_key_repetido_falha(tmp_path):
    rules_dir = _copy_rules(tmp_path)
    path = rules_dir / "cosmetico_proibidas.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("COS-TERAPEUTICA", "SUP-EMAG"), encoding="utf-8"
    )
    with pytest.raises(RulesError, match="rule_key repetido"):
        load_rules(rules_dir)


@pytest.mark.parametrize("field", ["fonte", "referencia"])
def test_check_falha_sem_fonte_ou_referencia(tmp_path, capsys, field):
    rules_dir = _copy_rules(tmp_path)
    path = rules_dir / "padroes_h2.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    del data[field]
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    assert check(rules_dir) == 1
    out = capsys.readouterr().out
    assert f"padroes_h2.yaml: {field}" in out
    assert "FALHOU" in out


def test_check_ok_por_linha_de_comando():
    proc = subprocess.run(
        [sys.executable, "-m", "promessa.rules.loader", "--check"],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OK: regras válidas" in proc.stdout
    assert "suplemento_proibidas.yaml" in proc.stdout and "regras=5" in proc.stdout


def test_termo_nao_normalizado_e_recusado(tmp_path):
    rules_dir = _copy_rules(tmp_path)
    path = rules_dir / "suplemento_proibidas.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace('"glicose"', '"Glicose"'), encoding="utf-8"
    )
    with pytest.raises(RulesError, match="normalizado"):
        load_rules(rules_dir)


# --- Taxonomia ---------------------------------------------------------------------------

TAXONOMIA_CONTEXTO = {  # CONTEXTO, seção 12.1
    "promessa_explicita": [
        "diferente_do_anunciado",
        "condicao_da_oferta",
        "informacao_omitida",
        "resultado_prometido",
    ],
    "promessa_expectativa": ["qualidade_abaixo"],
    "acesso_entrega": [
        "acesso_nao_liberado",
        "fisico_nao_entregue",
        "servico_fora_do_ar",
        "login_conta",
        "conteudo_removido",
    ],
    "processo": [
        "arrependimento_sem_motivo",
        "renovacao_indesejada",
        "cancelamento_travado",
        "reembolso_nao_processado",
        "motivo_pessoal",
    ],
    "fraude": ["cobranca_nao_reconhecida", "pagamento_fora_do_checkout", "golpe"],
    "outros": ["outros"],
}


def test_taxonomia_igual_ao_contexto():
    assert load_rules().taxonomy.subcauses_by_cause() == TAXONOMIA_CONTEXTO


def test_toda_subcausa_pertence_a_uma_causa():
    taxonomy = load_rules().taxonomy
    owners: dict[str, list[str]] = {}
    for cause, subs in taxonomy.subcauses_by_cause().items():
        for sub in subs:
            owners.setdefault(sub, []).append(cause)
    assert all(len(causes) == 1 for causes in owners.values())
    for case in taxonomy.casos_de_fronteira:
        assert owners[case.subcausa] == [case.causa]


def test_so_promessa_explicita_pesa_no_creator():
    weighs = [c.causa for c in load_rules().taxonomy.causas if c.pesa_no_creator]
    assert weighs == ["promessa_explicita"]


# --- IN 28 -------------------------------------------------------------------------------

# Hash do texto das alegações conferido pelo Lucas (D17). Se mudar, foi edição do texto da norma:
# só atualize depois de conferir de novo contra o PDF.
IN28_TEXT_SHA256 = "db1972a21ee9e22ace73e15fefc5b600bdc4c863d108ece4a699e2ccf6968e73"


def test_in28_texto_nao_foi_alterado():
    with (RULES_DIR / "suplemento_in28_permitidas.yaml").open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    claims = [
        (
            c["nome"],
            c.get("alegacoes_permitidas"),
            c.get("alegacoes_de_conteudo"),
            c.get("condicao"),
        )
        for c in raw["constituintes"]
    ]
    digest = hashlib.sha256(json.dumps(claims, ensure_ascii=False).encode()).hexdigest()
    assert digest == IN28_TEXT_SHA256


def test_in28_transcrita_ou_pendente():
    in28 = load_rules().get("suplemento_in28_permitidas")
    assert in28.status in ("pendente_transcricao", "transcrito_a_conferir", "conferido")
    if in28.status != "pendente_transcricao":
        assert all(c.alegacoes_permitidas for c in in28.constituintes)


def test_in28_rule_keys_estaveis():
    claims = load_rules().permitted_claims(Category.SUPLEMENTO)
    keys = [c.rule_key for c in claims]
    assert keys == [f"IN28-MAG-{i:02d}" for i in range(1, 8)] + [
        f"IN28-B6-{i:02d}" for i in range(1, 9)
    ]
    by_key = {c.rule_key: c.texto for c in claims}
    assert by_key["IN28-B6-02"] == "A vitamina B6 auxilia no funcionamento do sistema imune."


def test_in28_so_vale_para_suplemento():
    assert load_rules().permitted_claims(Category.COSMETICO) == []


# --- Nenhum termo proibido no código -----------------------------------------------------


def _term_regex(term: str) -> re.Pattern[str]:
    body = re.escape(term.removesuffix("*"))
    tail = "" if term.endswith("*") else r"\b"
    return re.compile(rf"\b{body}{tail}")


def test_nenhum_termo_proibido_em_src():
    terms = load_rules().all_terms()
    assert len(terms) > 50
    hits = []
    for path in sorted((ROOT / "src").rglob("*.py")):
        source = normalize(path.read_text(encoding="utf-8"))
        for term in terms:
            if _term_regex(term).search(source):
                hits.append(f"{path.relative_to(ROOT).as_posix()}: {term}")
    assert hits == []


# --- Sanidade dos padrões (sem lógica de checagem; ela vem na T06) -----------------------


def _patterns(file_id: str, rule_key: str) -> list[str]:
    f = load_rules().get(file_id)
    rule = next(r for r in f.regras if r.rule_key == rule_key)
    return getattr(rule, "padroes", None) or [e.padrao for e in rule.extratores]


def _any_match(patterns: list[str], text: str) -> re.Match[str] | None:
    normalized = match_text(text)
    return next((m for p in patterns if (m := re.search(p, normalized))), None)


@pytest.mark.parametrize(
    ("text", "expected_n"),
    [
        ("acesso vitalício e 30 dias para testar", "30"),
        ("12 meses de acesso, 7 dias de garantia", "7"),
    ],
)
def test_garantia_extrai_dias(text, expected_n):
    assert _any_match(_patterns("condicoes_oferta", "COND-GARANTIA"), text)["n"] == expected_n


def test_5kg_em_7_dias_nao_e_garantia():
    assert (
        _any_match(_patterns("condicoes_oferta", "COND-GARANTIA"), "Secar até 5KG EM 7 DIAS")
        is None
    )
    assert _any_match(_patterns("padroes_h2", "PRAZO-RESULTADO"), "Secar até 5KG EM 7 DIAS")


@pytest.mark.parametrize(
    ("rule_key", "text"),
    [
        ("RENDA-NUMERO", "tenha uma RENDA EXTRA de 10K"),
        ("URGENCIA", "DESCONTO INÉDITO, Só hoje!!"),
        ("URGENCIA", "restam 3 vagas"),
        ("RESULTADO-GARANTIDO", "resultado 100% garantido"),
    ],
)
def test_padroes_h2_casam_exemplos_da_h2(rule_key, text):
    assert _any_match(_patterns("padroes_h2", rule_key), text)


@pytest.mark.parametrize(
    ("rule_key", "text"),
    [
        ("COND-ACESSO", "12 meses de acesso"),
        ("COND-ACESSO", "acesso vitalício"),
        ("COND-RECORRENCIA", "sem mensalidade, você paga uma vez só"),
        ("COND-BONUS", "Ganhe o e-book de receitas de bônus"),
        ("COND-CUSTO-OCULTO", "comece do zero, sem gastar nada"),
    ],
)
def test_condicoes_casam_exemplos(rule_key, text):
    assert _any_match(_patterns("condicoes_oferta", rule_key), text)


# --- Apoio -------------------------------------------------------------------------------


def _copy_rules(tmp_path: Path) -> Path:
    target = tmp_path / "rules"
    shutil.copytree(RULES_DIR, target)
    return target
