"""Forma de exibição em pt-BR (promessa.display)."""

import pytest

from promessa import display
from promessa.db.enums import AccessType, Recurrence


@pytest.mark.parametrize(
    ("value", "digits", "expected"),
    [(0.047, 1, "4,7%"), (0.12, 1, "12,0%"), (0.56, 0, "56%"), (None, 1, "—")],
)
def test_pct(value, digits, expected):
    assert display.pct(value, digits) == expected


def test_num_e_dinheiro():
    assert display.num(0.37) == "0,37"
    assert display.num(None) == "—"
    assert display.money(990) == "R$ 9,90"


def test_rotulos_de_valores_internos():
    assert display.label(display.ACCESS_TYPE, AccessType.PRAZO) == "por prazo"
    assert display.label(display.RECURRENCE, Recurrence.UNICA) == "pagamento único"
    assert display.label(display.PROMISE_TYPE, "condicao_oferta") == "condição da oferta"
    assert display.label(display.APPROVAL, "em_revisao") == "em revisão"
    assert display.label({}, "valor_novo") == "valor novo"  # sem rótulo: legível mesmo assim
    assert display.label({}, None) == "—"


@pytest.mark.parametrize(
    ("normalized", "shown"),
    [
        ("acesso vitalicio", "acesso vitalício"),
        ("bonus e-book de receitas", "bônus e-book de receitas"),
        ("acesso 12 meses", "acesso 12 meses"),
        ("5 kg em 7 dias", "5 kg em 7 dias"),
    ],
)
def test_promessa_com_acento(normalized, shown):
    assert display.promise_label(normalized) == shown


def test_juntar_em_portugues():
    assert display.join_pt([]) == ""
    assert display.join_pt(["a"]) == "a"
    assert display.join_pt(["a", "b", "c"]) == "a, b e c"
