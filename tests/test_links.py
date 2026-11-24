"""Promessa registrada, link rastreado e revisão de bloqueio (T09)."""

import re

import pytest
from sqlalchemy import select

from promessa.checker.service import check_content
from promessa.config import get_settings
from promessa.db.enums import RefundType, Relation
from promessa.db.models import (
    CheckResult,
    ContentPiece,
    RefundClassification,
    RefundEvent,
    ReviewEvent,
    Sale,
    TrackedLink,
    get_current_facts,
)
from promessa.db.session import get_session
from promessa.errors import DomainError
from promessa.facts.service import create_facts_version
from promessa.links.service import register_content_and_link
from promessa.review.service import list_review_queue, submit_review
from tests.mcp_helpers import ToolCallError, call_tool


@pytest.fixture
def s(seeded):
    with get_session(seeded) as session:
        yield session


def check(s, text, product="prod_treino", creator="cr_ana", parent=None):
    return check_content(s, product, creator, text, "instagram", parent_piece_id=parent)


def code_of(exc_info) -> str:
    return exc_info.value.code


def promises(link):
    return {
        (p.attribute.value, p.value, p.unit, p.approval.value) for p in link.registered_promises
    }


def block_id(resp, rule_key):
    return next(f.id for f in resp.findings if f.rule_key == rule_key)


# --- Exemplo do guia ---------------------------------------------------------------------


def test_exemplo_do_guia_bloqueio_e_correcao(s):
    blocked = check(s, "acesso vitalício e 30 dias para testar")
    with pytest.raises(DomainError) as exc:
        register_content_and_link(s, blocked.piece_id)
    assert code_of(exc) == "BLOQUEIO_PENDENTE"
    assert '"acesso vitalício" (COND-ACESSO' in exc.value.message
    assert '"30 dias para testar" (COND-GARANTIA' in exc.value.message

    fixed = check(s, "12 meses de acesso, 7 dias de garantia", parent=blocked.piece_id)
    link = register_content_and_link(s, fixed.piece_id)
    assert promises(link) == {
        ("acesso", "12", "meses", "registrada"),
        ("garantia", "7", "dias", "registrada"),
    }
    assert {p.normalized_text for p in link.registered_promises} == {
        "acesso 12 meses",
        "garantia 7 dias",
    }
    assert re.fullmatch(r"[a-z2-7]{8}", link.link_id)
    assert link.url == get_settings().link_base_url + link.link_id
    assert "#publi" in link.disclosure_text and link.facts_version == 1
    assert link.actor_type.value == "humano"


def test_resultado_em_revisao_e_garantia_registrada(s):
    resp = check(s, "Secar até 5KG EM 7 DIAS. 7 dias de garantia")
    assert resp.can_generate_link is True
    link = register_content_and_link(s, resp.piece_id, actor_type="agente")
    by_attr = {p.attribute.value: p for p in link.registered_promises}
    assert by_attr["resultado"].approval.value == "em_revisao"
    assert by_attr["resultado"].normalized_text == "5 kg em 7 dias"
    assert by_attr["resultado"].type.value == "resultado"
    assert by_attr["garantia"].approval.value == "registrada"
    assert link.actor_type.value == "agente"


def test_link_e_idempotente(s):
    resp = check(s, "12 meses de acesso, 7 dias de garantia")
    first = register_content_and_link(s, resp.piece_id)
    again = register_content_and_link(s, resp.piece_id)
    assert again.link_id == first.link_id
    assert len(again.registered_promises) == 2
    assert s.scalar(select(TrackedLink).where(TrackedLink.piece_id == resp.piece_id)) is not None


def test_publi_presente_muda_o_texto_de_identificacao(s):
    resp = check(s, "#publi 12 meses de acesso")
    link = register_content_and_link(s, resp.piece_id)
    assert "já tem identificação" in link.disclosure_text


# --- Contestação -------------------------------------------------------------------------


def test_contestacao_creator_marca_e_auditoria(s):
    blocked = check(s, "acesso vitalício")
    target = block_id(blocked, "COND-ACESSO")

    contested = submit_review(
        s,
        "check_result",
        target,
        "contestar",
        "cr_ana",
        "creator",
        note="o produto mudou para vitalício",
    )
    assert contested.review_status.value == "contestado"
    queue = list_review_queue(s, "bloqueio").items
    assert [(q.target_id, q.context["contest_note"]) for q in queue] == [
        (str(target), "o produto mudou para vitalício")
    ]

    with pytest.raises(DomainError) as exc:
        submit_review(s, "check_result", target, "reverter", "cr_ana", "creator")
    assert code_of(exc) == "PAPEL_NAO_AUTORIZADO"
    with pytest.raises(DomainError) as exc:
        register_content_and_link(s, blocked.piece_id)
    assert code_of(exc) == "BLOQUEIO_PENDENTE"

    reverted = submit_review(s, "check_result", target, "reverter", "marca_movimento", "marca")
    assert reverted.review_status.value == "revertido"
    assert list_review_queue(s, "bloqueio").items == []
    link = register_content_and_link(s, blocked.piece_id)
    assert promises(link) == {("acesso", "vitalicio", None, "registrada")}

    events = s.scalars(select(ReviewEvent).where(ReviewEvent.target_id == str(target))).all()
    assert [(e.action.value, e.actor, e.actor_role.value) for e in events] == [
        ("contestar", "cr_ana", "creator"),
        ("reverter", "marca_movimento", "marca"),
    ]
    result = s.get(CheckResult, target)
    assert (result.reviewed_by, result.reviewed_at is not None) == ("marca_movimento", True)


def test_manter_continua_bloqueado(s):
    blocked = check(s, "acesso vitalício")
    target = block_id(blocked, "COND-ACESSO")
    submit_review(s, "check_result", target, "contestar", "cr_ana", "creator")
    submit_review(s, "check_result", target, "manter", "ops_julia", "operacoes")
    with pytest.raises(DomainError) as exc:
        register_content_and_link(s, blocked.piece_id)
    assert code_of(exc) == "BLOQUEIO_PENDENTE"
    with pytest.raises(DomainError, match="já foi mantido"):
        submit_review(s, "check_result", target, "reverter", "marca_movimento", "marca")


@pytest.mark.parametrize(
    ("action", "actor", "role", "code"),
    [
        ("contestar", "cr_bia", "creator", "PAPEL_NAO_AUTORIZADO"),  # peça de outra creator
        ("contestar", "ops", "operacoes", "PAPEL_NAO_AUTORIZADO"),
        ("manter", "cr_ana", "creator", "PAPEL_NAO_AUTORIZADO"),
        ("reverter", "robo", "sistema", "PAPEL_NAO_AUTORIZADO"),
        ("reclassificar", "marca", "marca", "ENTRADA_INVALIDA"),
        ("aprovar", "marca", "marca", "ENTRADA_INVALIDA"),  # aprovar é para revisar
        ("pular", "marca", "marca", "ENTRADA_INVALIDA"),
        ("manter", "marca", "dono", "ENTRADA_INVALIDA"),
    ],
)
def test_permissoes(s, action, actor, role, code):
    blocked = check(s, "acesso vitalício")
    with pytest.raises(DomainError) as exc:
        submit_review(s, "check_result", block_id(blocked, "COND-ACESSO"), action, actor, role)
    assert code_of(exc) == code


def test_so_bloqueio_pode_ser_contestado_e_uma_vez(s):
    resp = check(s, "acesso vitalício. Secar até 5KG EM 7 DIAS")
    with pytest.raises(DomainError, match="Só um trecho bloqueado"):
        submit_review(
            s, "check_result", block_id(resp, "PRAZO-RESULTADO"), "contestar", "cr_ana", "creator"
        )
    target = block_id(resp, "COND-ACESSO")
    submit_review(s, "check_result", target, "contestar", "cr_ana", "creator")
    with pytest.raises(DomainError, match="já está contestado"):
        submit_review(s, "check_result", target, "contestar", "cr_ana", "creator")


def test_marca_aprova_trecho_em_revisao(s):
    resp = check(s, "Secar até 5KG EM 7 DIAS")
    link = register_content_and_link(s, resp.piece_id)
    assert promises(link) == {("resultado", "5 kg em 7 dias", None, "em_revisao")}
    submit_review(
        s, "check_result", block_id(resp, "PRAZO-RESULTADO"), "aprovar", "marca_movimento", "marca"
    )
    again = register_content_and_link(s, resp.piece_id)
    assert promises(again) == {("resultado", "5 kg em 7 dias", None, "registrada")}


# --- Ficha desatualizada -----------------------------------------------------------------


def test_nova_versao_da_ficha_depois_da_checagem(s):
    resp = check(s, "12 meses de acesso, 7 dias de garantia")
    create_facts_version(
        s,
        "prod_treino",
        {"guarantee_days": 14, "access_type": "prazo", "access_months": 12, "recurrence": "unica"},
        "marca",
    )
    with pytest.raises(DomainError) as exc:
        register_content_and_link(s, resp.piece_id)
    assert code_of(exc) == "FICHA_DESATUALIZADA" and "versão 1 → 2" in exc.value.message


def test_peca_inexistente(s):
    with pytest.raises(DomainError) as exc:
        register_content_and_link(s, "nao-existe")
    assert code_of(exc) == "PECA_INEXISTENTE"


# --- Invariantes 2 e 3 (CONTEXTO 8.3) ----------------------------------------------------


def test_invariantes_2_e_3(s):
    for text in [
        "12 meses de acesso, 7 dias de garantia",
        "Secar até 5KG EM 7 DIAS",
        "Ganhe o e-book de receitas de bônus",
    ]:
        register_content_and_link(s, check(s, text).piece_id)
    blocked = check(s, "acesso vitalício")
    target = block_id(blocked, "COND-ACESSO")
    submit_review(s, "check_result", target, "contestar", "cr_ana", "creator")
    submit_review(s, "check_result", target, "reverter", "marca", "marca")
    register_content_and_link(s, blocked.piece_id)
    check(s, "acesso vitalício e 30 dias para testar")  # bloqueada, sem link

    links = s.scalars(select(TrackedLink)).all()
    assert len(links) == 4
    for link in links:
        pending = s.scalars(
            select(CheckResult).where(
                CheckResult.piece_id == link.piece_id,
                CheckResult.output == "bloquear",
                CheckResult.review_status != "revertido",
            )
        ).all()
        assert pending == []  # invariante 2
        piece = s.get(ContentPiece, link.piece_id)
        assert link.facts_id == piece.facts_id  # invariante 3
        assert get_current_facts(s, link.product_id, at=link.created_at).id == link.facts_id


# --- Classificação na fila (preparo para T10) --------------------------------------------


def _classification(s, confidence):
    link = register_content_and_link(s, check(s, "12 meses de acesso").piece_id)
    sale = Sale(link_id=link.link_id, amount_cents=19700, commission_cents=3940)
    s.add(sale)
    s.flush()
    refund = RefundEvent(sale_id=sale.id, type=RefundType.REEMBOLSO, reason_text="x" * 200)
    s.add(refund)
    s.flush()
    c = RefundClassification(
        refund_id=refund.id,
        cause="processo",
        subcause="motivo_pessoal",
        relation=Relation.NAO_APLICAVEL,
        confidence=confidence,
        explanation="e",
    )
    s.add(c)
    s.flush()
    return c


def test_fila_e_reclassificacao(s):
    low, high = _classification(s, 0.5), _classification(s, 0.95)
    queue = list_review_queue(s, "classificacao").items
    assert [q.target_id for q in queue] == [str(low.id)]
    assert len(queue[0].context["reason_preview"]) == 80

    with pytest.raises(DomainError) as exc:
        submit_review(
            s,
            "refund_classification",
            low.id,
            "reclassificar",
            "cr_ana",
            "creator",
            payload={"cause": "fraude", "subcause": "golpe"},
        )
    assert code_of(exc) == "PAPEL_NAO_AUTORIZADO"
    with pytest.raises(DomainError, match="Par causa/subcausa"):
        submit_review(
            s,
            "refund_classification",
            low.id,
            "reclassificar",
            "ops",
            "operacoes",
            payload={"cause": "fraude", "subcause": "motivo_pessoal"},
        )
    res = submit_review(
        s,
        "refund_classification",
        low.id,
        "reclassificar",
        "ops",
        "operacoes",
        payload={"cause": "fraude", "subcause": "golpe"},
    )
    assert res.review_status.value == "revertido"
    assert (low.cause, low.subcause, low.reviewed_by) == ("fraude", "golpe", "ops")
    assert list_review_queue(s, "classificacao").items == []
    assert high.review_status.value == "nao_aplicavel"


def test_fila_kind_invalido(s):
    with pytest.raises(DomainError) as exc:
        list_review_queue(s, "outra")
    assert code_of(exc) == "ENTRADA_INVALIDA"


# --- Pelo protocolo MCP ------------------------------------------------------------------


def test_fluxo_completo_pelo_mcp(mcp_db):
    base = {"product_id": "prod_treino", "creator_id": "cr_ana", "channel": "instagram"}
    first = call_tool("check_content", {**base, "text": "acesso vitalício e 30 dias para testar"})
    with pytest.raises(ToolCallError, match="BLOQUEIO_PENDENTE"):
        call_tool("register_content_and_link", {"piece_id": first["piece_id"]})

    target = next(f["id"] for f in first["findings"] if f["rule_key"] == "COND-ACESSO")
    call_tool(
        "submit_review",
        {
            "target_type": "check_result",
            "target_id": str(target),
            "action": "contestar",
            "actor": "cr_ana",
            "actor_role": "creator",
        },
    )
    queue = call_tool("list_review_queue", {"kind": "bloqueio"})
    assert [i["target_id"] for i in queue["items"]] == [str(target)]
    with pytest.raises(ToolCallError, match="PAPEL_NAO_AUTORIZADO"):
        call_tool(
            "submit_review",
            {
                "target_type": "check_result",
                "target_id": str(target),
                "action": "reverter",
                "actor": "cr_ana",
                "actor_role": "creator",
            },
        )

    second = call_tool(
        "check_content",
        {
            **base,
            "text": "12 meses de acesso, 7 dias de garantia",
            "parent_piece_id": first["piece_id"],
        },
    )
    link = call_tool("register_content_and_link", {"piece_id": second["piece_id"]})
    assert {p["normalized_text"] for p in link["registered_promises"]} == {
        "acesso 12 meses",
        "garantia 7 dias",
    }
    assert all(p["approval"] == "registrada" for p in link["registered_promises"])
