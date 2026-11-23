"""check_content (T07) sem rede: só regras, fusão com modelo simulado, persistência e MCP."""

import logging

import pytest
from sqlalchemy import select

from promessa.checker.llm_layer import CheckerLLMOutput, LLMFinding, LLMPromise
from promessa.checker.service import check_content
from promessa.db.models import CheckResult, ContentPiece
from promessa.db.session import get_session
from promessa.errors import DomainError
from promessa.llm.client import LLMError, LLMResult
from tests.mcp_helpers import ToolCallError, call_tool, list_tool_names


@pytest.fixture
def s(seeded):
    with get_session(seeded) as session:
        yield session


def fake_model(findings=(), promises=()):
    """Completer simulado: devolve sempre a mesma saída do 'modelo'."""

    def completer(prompt_name, variables, output_model, model):
        assert prompt_name == "checker_v1" and output_model is CheckerLLMOutput
        assert "[1]" in variables["trechos"]
        return LLMResult(
            CheckerLLMOutput(findings=list(findings), promises=list(promises)),
            model="modelo-simulado",
            prompt_version="checker_v1",
            cached=False,
        )

    return completer


def llm_finding(excerpt, output="revisar", rule_key=None, reason="med_comparacao", segment=1):
    return LLMFinding(
        segment=segment,
        excerpt=excerpt,
        output=output,
        rule_key=rule_key,
        reason_type=reason,
        explanation="explicação do modelo",
        suggestion="sugestão do modelo",
    )


def run(s, text, product="prod_treino", **kw):
    return check_content(s, product, "cr_ana", text, "instagram", **kw)


# --- Só regras ---------------------------------------------------------------------------


def test_sem_chave_funciona_so_com_regras(s):
    resp = run(s, "acesso vitalício e 30 dias para testar")
    assert resp.layers_used == ["regras"]
    assert resp.overall == "bloquear" and resp.can_generate_link is False
    assert resp.notes and "só com regras" in resp.notes[0]


def test_use_llm_false_ignora_o_modelo(s):
    resp = run(
        s,
        "esse chá dispensa a farmácia",
        use_llm=False,
        completer=fake_model([llm_finding("dispensa a farmácia")]),
    )
    assert resp.layers_used == ["regras"] and resp.findings == []


def test_grava_peca_e_achados(s):
    resp = run(s, "12 meses de acesso, 7 dias de garantia")
    piece = s.get(ContentPiece, resp.piece_id)
    assert piece.facts_id is not None and piece.creator_id == "cr_ana"
    rows = s.scalars(select(CheckResult).where(CheckResult.piece_id == resp.piece_id)).all()
    assert {(r.rule_key, r.output.value, r.source.value) for r in rows} == {
        ("COND-ACESSO", "registrar", "regra"),
        ("COND-GARANTIA", "registrar", "regra"),
    }
    assert [f.id for f in resp.findings] == [r.id for r in sorted(rows, key=lambda r: r.span_start)]
    assert rows[0].extracted["type"] == "condicao_oferta"


@pytest.mark.parametrize(
    ("product", "creator", "channel", "parent", "code"),
    [
        ("prod_treino", "cr_nao_existe", "instagram", None, "CREATOR_INEXISTENTE"),
        ("prod_x", "cr_ana", "instagram", None, "PRODUTO_INEXISTENTE"),
        ("prod_treino", "cr_ana", "orkut", None, "ENTRADA_INVALIDA"),
        ("prod_treino", "cr_ana", "instagram", "nao-existe", "PECA_INEXISTENTE"),
    ],
)
def test_erros_de_entrada(s, product, creator, channel, parent, code):
    with pytest.raises(DomainError) as exc:
        check_content(s, product, creator, "texto", channel, parent_piece_id=parent)
    assert exc.value.code == code


# --- Fusão com modelo simulado (sem rede) ------------------------------------------------


def test_modelo_bloquear_sem_rule_key_vira_revisar(s):
    resp = run(
        s,
        "esse chá dispensa a farmácia",
        completer=fake_model([llm_finding("dispensa a farmácia", output="bloquear")]),
    )
    (f,) = resp.findings
    assert (f.output.value, f.rule_key, f.source.value) == ("revisar", None, "modelo")
    assert resp.layers_used == ["regras", "modelo"]
    row = s.get(CheckResult, f.id)
    assert (row.output.value, row.model, row.prompt_version) == (
        "revisar",
        "modelo-simulado",
        "checker_v1",
    )


def test_modelo_bloquear_com_rule_key_valido_fica(s):
    resp = run(
        s,
        "deixa o corpo sequinho rapidinho",
        product="prod_magnesio",
        completer=fake_model(
            [llm_finding("corpo sequinho", "bloquear", "SUP-EMAG", "alegacao_proibida")]
        ),
    )
    (f,) = resp.findings
    assert (f.output.value, f.rule_key) == ("bloquear", "SUP-EMAG")
    assert resp.can_generate_link is False


def test_modelo_rule_key_de_outra_categoria_nao_bloqueia(s):
    resp = run(
        s,
        "deixa o corpo sequinho rapidinho",
        completer=fake_model([llm_finding("corpo sequinho", "bloquear", "SUP-EMAG")]),
    )
    assert [(f.output.value, f.rule_key) for f in resp.findings] == [("revisar", None)]


def test_excerpt_inexistente_e_descartado_e_logado(s, caplog):
    caplog.set_level(logging.WARNING, logger="promessa.checker.llm_layer")
    resp = run(
        s,
        "Treino de 20 minutos para fazer em casa",
        completer=fake_model([llm_finding("texto que não existe na peça")]),
    )
    assert resp.findings == [] and resp.overall == "limpo"
    assert "não está no texto" in caplog.text


def test_modelo_nao_rebaixa_bloquear_da_camada1(s):
    text = "acesso vitalício e 30 dias para testar"
    resp = run(
        s,
        text,
        completer=fake_model(
            [
                llm_finding("acesso vitalício", output="revisar", reason="outro"),
                llm_finding("acesso vitalício", output="registrar", reason="outro"),
            ]
        ),
    )
    keys = [(f.output.value, f.rule_key, f.source.value) for f in resp.findings]
    assert ("bloquear", "COND-ACESSO", "regra") in keys
    assert all(src == "regra" for *_, src in keys)
    assert resp.overall == "bloquear"


def test_promessa_de_resultado_do_modelo_vira_revisar(s):
    text = "Em 30 dias você vai transformar seu corpo."
    resp = run(
        s,
        text,
        completer=fake_model(
            promises=[
                LLMPromise(
                    excerpt="Em 30 dias você vai transformar seu corpo",
                    attribute="resultado",
                    value="transformar o corpo em 30 dias",
                    unit=None,
                ),
            ]
        ),
    )
    (f,) = resp.findings
    assert (f.output.value, f.reason_type, f.source.value) == (
        "revisar",
        "resultado_sem_numero",
        "modelo",
    )
    assert f.extracted["value"] == "transformar o corpo em 30 dias"


def test_promessa_anexada_ao_achado_do_modelo(s):
    text = "esse chá dispensa a farmácia"
    resp = run(
        s,
        text,
        completer=fake_model(
            [llm_finding("dispensa a farmácia")],
            [
                LLMPromise(
                    excerpt="dispensa a farmácia", attribute="outro", value="sem remédio", unit=None
                )
            ],
        ),
    )
    (f,) = resp.findings
    assert f.extracted["value"] == "sem remédio"


def test_erro_do_modelo_cai_para_so_regras(s):
    def broken(*args, **kwargs):
        raise LLMError("503 UNAVAILABLE")

    resp = run(s, "acesso vitalício e 30 dias para testar", completer=broken)
    assert resp.layers_used == ["regras"] and resp.overall == "bloquear"
    assert "não respondeu" in resp.notes[0]


# --- Pelo protocolo MCP ------------------------------------------------------------------


def test_check_content_listada():
    assert "check_content" in list_tool_names()


def test_exemplo_do_guia_pelo_mcp(mcp_db):
    first = call_tool(
        "check_content",
        {
            "product_id": "prod_treino",
            "creator_id": "cr_ana",
            "channel": "instagram",
            "text": "acesso vitalício e 30 dias para testar",
        },
    )
    assert first["can_generate_link"] is False and first["overall"] == "bloquear"
    assert {f["rule_key"] for f in first["findings"]} == {"COND-ACESSO", "COND-GARANTIA"}
    assert first["layers_used"] == ["regras"] and first["facts_version"] == 1

    second = call_tool(
        "check_content",
        {
            "product_id": "prod_treino",
            "creator_id": "cr_ana",
            "channel": "instagram",
            "text": "12 meses de acesso, 7 dias de garantia",
            "parent_piece_id": first["piece_id"],
        },
    )
    assert second["can_generate_link"] is True and second["overall"] == "registrar"
    with get_session(mcp_db) as session:
        assert session.get(ContentPiece, second["piece_id"]).parent_piece_id == first["piece_id"]


def test_mcp_canal_invalido(mcp_db):
    with pytest.raises(ToolCallError, match="ENTRADA_INVALIDA"):
        call_tool(
            "check_content",
            {"product_id": "prod_treino", "creator_id": "cr_ana", "channel": "orkut", "text": "oi"},
        )
