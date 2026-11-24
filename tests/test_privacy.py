"""Remoção de dados pessoais do motivo (T10, CONTEXTO 15)."""

import pytest

from promessa.privacy import preview, scrub


def test_criterio_do_plano():
    out = scrub("meu cpf 123.456.789-00 e email ana@x.com")
    assert "123.456.789-00" not in out and "ana@x.com" not in out
    assert out == "meu cpf [CPF] e email [EMAIL]"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("cpf 12345678900", "cpf [CPF]"),
        ("CNPJ 12.345.678/0001-95", "CNPJ [CPF]"),
        ("liga (11) 91234-5678", "liga [TELEFONE]"),
        ("whats +55 11 912345678", "whats [TELEFONE]"),
        ("whats 11987654321", "whats [TELEFONE]"),
        ("cartão 4111 1111 1111 1111 cobrado", "cartão [CARTAO] cobrado"),
        ("cartão 4111-1111-1111-1111", "cartão [CARTAO]"),
        ("e-mail: joao.silva+compras@empresa.com.br", "e-mail: [EMAIL]"),
    ],
)
def test_dados_pessoais_saem(text, expected):
    assert scrub(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "paguei R$ 1.297,00 em 05/10/2026",
        "aparecem 139 parcelas em atraso",
        "pedido 123456789 e boleto de R$ 23.000",
        "garantia de 30 dias, 12 meses de acesso",
        "Contrato de R$ 23 mil fechado em 2026",
    ],
)
def test_valores_datas_e_numeros_comuns_ficam(text):
    assert scrub(text) == text


def test_preview_limita_e_limpa():
    text = "meu email ana@x.com " + "a" * 200
    out = preview(text)
    assert len(out) == 80 and "ana@x.com" not in out
    assert scrub(None) == "" and scrub("") == ""
