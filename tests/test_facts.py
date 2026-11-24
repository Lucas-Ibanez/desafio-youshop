"""Ficha de promessas (T05): seeds, versões, regras materializadas, briefing e ferramentas MCP."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from promessa.db.enums import Category, RuleKind, RuleSource
from promessa.db.models import Brand, ClaimRule, Creator, Product, ProductFacts
from promessa.db.session import get_session
from promessa.errors import FICHA_INVALIDA, DomainError
from promessa.facts.seed import load_seed
from promessa.facts.service import (
    create_facts_version,
    get_product_facts,
    name_warnings,
    word_count,
)
from promessa.rules.loader import load_rules
from tests.mcp_helpers import ToolCallError, call_tool, list_tool_names

TREINO_V2 = {
    "product_id": "prod_treino",
    "guarantee_days": 14,
    "access_type": "prazo",
    "access_months": 12,
    "recurrence": "unica",
    "bonuses": ["E-book de receitas"],
    "created_by": "marca_teste",
}


@pytest.fixture
def s(seeded):
    with get_session(seeded) as session:
        yield session


# --- Seeds -------------------------------------------------------------------------------


def test_seed_carrega_5_de_cada(s):
    counts = {
        m.__tablename__: s.scalar(select(func.count()).select_from(m))
        for m in (Brand, Product, ProductFacts, Creator)
    }
    assert counts == {"brand": 5, "product": 5, "product_facts": 5, "creator": 5}
    assert {f.version for f in s.scalars(select(ProductFacts))} == {1}


def test_seed_e_idempotente(s):
    report = load_seed(s)
    assert (report.brands, report.products, report.facts, report.creators) == (0, 0, 0, 0)


def test_fichas_v1_do_plano(s):
    treino = get_product_facts(s, "prod_treino")
    assert (treino.guarantee_days, treino.access_type, treino.access_months) == (7, "prazo", 12)
    assert treino.bonuses == ["E-book de receitas"]
    canal = get_product_facts(s, "prod_canal")
    assert canal.extra_costs == [
        {"descricao": "ferramenta de voz e edição", "valor_mensal_cents": 9700}
    ]
    ingles = get_product_facts(s, "prod_ingles")
    assert (ingles.recurrence, ingles.auto_renewal) == ("mensal", True)


# --- Regras materializadas ---------------------------------------------------------------


def test_regras_oficiais_copiadas_por_categoria(s):
    keys = {
        p: {r.rule_key for r in get_product_facts(s, p).rules}
        for p in ("prod_magnesio", "prod_capilar", "prod_treino")
    }
    assert {"SUP-EMAG", "SUP-IMUN", "SUP-FOCO", "SUP-SEXUAL", "SUP-DOENCA"} <= keys["prod_magnesio"]
    assert {"IN28-MAG-01", "IN28-B6-08"} <= keys["prod_magnesio"]
    assert keys["prod_capilar"] == {"COS-TERAPEUTICA", "COS-ZONA-CINZENTA"}
    assert keys["prod_treino"] == set()


def test_regra_materializada_guarda_termos_e_referencia(s):
    rule = s.scalars(select(ClaimRule).where(ClaimRule.rule_key == "SUP-EMAG")).one()
    assert rule.reference == "suplemento_proibidas.yaml@2026-11-23.2"
    assert rule.source == RuleSource.ANVISA and rule.output == "bloquear"
    assert "seca barriga" in rule.payload["termos"]
    in28 = s.scalars(select(ClaimRule).where(ClaimRule.rule_key == "IN28-B6-02")).one()
    assert in28.kind == RuleKind.PERMITIDA and in28.source == RuleSource.IN28
    assert in28.text == "A vitamina B6 auxilia no funcionamento do sistema imune."


def test_regras_da_marca(s):
    result = create_facts_version(
        s,
        "prod_treino",
        {
            **{k: v for k, v in TREINO_V2.items() if k not in ("product_id", "created_by")},
            "brand_rules": [
                {"kind": "proibida", "text": "Treino que substitui academia"},
                {"kind": "permitida", "text": "Treinos de 20 minutos", "rule_key": "MARCA-20MIN"},
            ],
        },
        "marca_teste",
    )
    rules = {r.rule_key: r for r in get_product_facts(s, "prod_treino", result.version).rules}
    assert rules["MARCA-01"].source == RuleSource.MARCA and rules["MARCA-01"].output == "bloquear"
    assert rules["MARCA-20MIN"].kind == RuleKind.PERMITIDA and rules["MARCA-20MIN"].output is None


# --- Validação ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"guarantee_days": 5}, "CDC art. 49"),
        ({"access_months": None}, "quantos meses"),
        ({"access_type": "vitalicio"}, "só vale para acesso por prazo"),
        ({"auto_renewal": True}, "pagamento único"),
        ({"access_type": "pra_sempre"}, "Dados da ficha inválidos"),
        ({"valid_from": "2026-09-01T00:00:00Z"}, "precisa valer a partir de"),
    ],
)
def test_ficha_invalida(s, change, message):
    data = {k: v for k, v in TREINO_V2.items() if k not in ("product_id", "created_by")}
    with pytest.raises(DomainError, match=message) as exc:
        create_facts_version(s, "prod_treino", {**data, **change}, "marca_teste")
    assert exc.value.code == FICHA_INVALIDA


def test_nome_do_produto_que_ja_e_alegacao_gera_aviso(s):
    s.add(
        Product(
            id="prod_seca",
            brand_id="mk_vitalis",
            name="Seca Barriga Caps",
            category=Category.SUPLEMENTO,
        )
    )
    s.flush()
    result = create_facts_version(
        s,
        "prod_seca",
        {"guarantee_days": 7, "access_type": "nao_aplica", "recurrence": "unica"},
        "marca_teste",
    )
    assert [w.rule_key for w in result.warnings] == ["SUP-EMAG"]
    assert result.warnings[0].excerpt == "Seca Barriga"


def test_nomes_dos_seeds_nao_geram_aviso(s):
    """Os produtos fictícios foram escolhidos sem alegação no nome."""
    for p in s.scalars(select(Product)):
        assert name_warnings(p.name, p.category, load_rules()) == [], p.id


# --- Briefing ----------------------------------------------------------------------------


def test_briefing_do_treino(s):
    briefing = get_product_facts(s, "prod_treino").briefing
    for expected in (
        "7 dias",
        "12 meses",
        "#publi",
        "Condições exatas",
        "Pode dizer",
        "Não pode dizer",
    ):
        assert expected in briefing
    assert word_count(briefing) <= 150


@pytest.mark.parametrize(
    "product_id", ["prod_magnesio", "prod_capilar", "prod_canal", "prod_ingles"]
)
def test_briefing_dos_demais_ate_150_palavras(s, product_id):
    briefing = get_product_facts(s, product_id).briefing
    assert word_count(briefing) <= 150 and "#publi" in briefing


def test_briefing_mostra_custo_e_renovacao(s):
    assert "R$ 97/mês" in get_product_facts(s, "prod_canal").briefing
    assert "renovação automática" in get_product_facts(s, "prod_ingles").briefing
    assert "dose mínima" in get_product_facts(s, "prod_magnesio").briefing


# --- Pelo protocolo MCP ------------------------------------------------------------------


def test_ferramentas_listadas():
    assert {"ping", "get_product_facts", "upsert_product_facts"} <= list_tool_names()


def test_mcp_get_product_facts_magnesio(mcp_db):
    facts = call_tool("get_product_facts", {"product_id": "prod_magnesio"})
    sup = [r for r in facts["rules"] if r["rule_key"].startswith("SUP-")]
    assert {r["rule_key"] for r in sup} == {
        "SUP-EMAG",
        "SUP-IMUN",
        "SUP-FOCO",
        "SUP-SEXUAL",
        "SUP-DOENCA",
    }
    assert all(r["source"] and r["reference"] for r in sup)
    assert facts["version"] == 1 and facts["briefing"]


def test_mcp_upsert_cria_v2_e_v1_fica_intacta(mcp_db):
    v1_before = call_tool("get_product_facts", {"product_id": "prod_treino", "version": 1})
    result = call_tool("upsert_product_facts", TREINO_V2)
    assert result == {"product_id": "prod_treino", "version": 2, "warnings": []}
    assert call_tool("get_product_facts", {"product_id": "prod_treino", "version": 1}) == v1_before
    current = call_tool("get_product_facts", {"product_id": "prod_treino"})
    assert (current["version"], current["guarantee_days"]) == (2, 14)


def test_mcp_garantia_5_dias_recusada(mcp_db):
    with pytest.raises(ToolCallError, match=r"FICHA_INVALIDA: .*CDC art\. 49"):
        call_tool("upsert_product_facts", {**TREINO_V2, "guarantee_days": 5})
    assert call_tool("get_product_facts", {"product_id": "prod_treino"})["version"] == 1


@pytest.mark.parametrize(
    ("args", "code"),
    [
        ({"product_id": "prod_nao_existe"}, "PRODUTO_INEXISTENTE"),
        ({"product_id": "prod_treino", "version": 9}, "FICHA_INEXISTENTE"),
    ],
)
def test_mcp_erros_de_dominio(mcp_db, args, code):
    with pytest.raises(ToolCallError, match=code):
        call_tool("get_product_facts", args)


def test_mcp_aviso_de_nome(mcp_db):
    with get_session(mcp_db) as session:
        session.add(
            Product(
                id="prod_seca",
                brand_id="mk_vitalis",
                name="Seca Barriga Caps",
                category=Category.SUPLEMENTO,
            )
        )
        session.commit()
    result = call_tool(
        "upsert_product_facts",
        {
            "product_id": "prod_seca",
            "guarantee_days": 7,
            "access_type": "nao_aplica",
            "recurrence": "unica",
            "created_by": "marca_teste",
            "valid_from": datetime(2026, 11, 1, tzinfo=UTC).isoformat(),
        },
    )
    assert [w["rule_key"] for w in result["warnings"]] == ["SUP-EMAG"]
