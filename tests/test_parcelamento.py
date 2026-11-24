from datetime import date

import pytest

from app.modelos import Dinheiro, ErroDeNegocio, Parcelamento

R = Dinheiro.de_reais


def contrato(total=3500, parcelas=10, primeiro=date(2026, 8, 10)) -> Parcelamento:
    return Parcelamento("Moto", R(total), parcelas, primeiro)


def test_divide_igual_quando_exato():
    p = contrato()
    assert p.valor_da_parcela(1) == R(350)
    assert p.valor_da_parcela(10) == R(350)


def test_ultima_parcela_absorve_o_arredondamento():
    p = contrato(3500, 12)
    assert p.valor_da_parcela(1) == R(291.66)
    assert p.valor_da_parcela(12) == R(291.74)
    assert sum(x.valor for x in p.cronograma()) == R(3500)


def test_vencimentos_mes_a_mes():
    p = contrato()
    assert p.vencimento(1) == date(2026, 8, 10)
    assert p.vencimento(2) == date(2026, 9, 10)
    assert p.vencimento(6) == date(2027, 1, 10)


def test_dia_31_em_mes_curto():
    p = contrato(primeiro=date(2027, 1, 31))
    assert p.vencimento(2) == date(2027, 2, 28)
    assert p.vencimento(3) == date(2027, 3, 31)


def test_status_das_parcelas():
    p = contrato()
    p.pagar(1, date(2026, 8, 10))
    hoje = date(2026, 9, 15)
    cron = p.cronograma()
    assert [x.status(hoje) for x in cron[:3]] == ["paga", "atrasada", "pendente"]
    assert p.esta_atrasado(hoje)


def test_pagamento_fora_de_ordem_e_quitacao():
    p = contrato()
    p.pagar(3, date(2026, 8, 1))
    assert p.proxima_em_aberto() == 1
    for n in [1, 2, 4, 5, 6, 7, 8, 9, 10]:
        p.pagar(n, date(2026, 8, 1))
    assert p.quitado
    assert p.proxima_em_aberto() is None
    assert p.falta_pagar == Dinheiro.zero()


def test_regras_de_pagamento():
    p = contrato()
    p.pagar(1, date(2026, 8, 10))
    with pytest.raises(ErroDeNegocio):
        p.pagar(1, date(2026, 8, 10))  # já paga
    with pytest.raises(ErroDeNegocio):
        p.pagar(11, date(2026, 8, 10))  # não existe
    p.estornar(1)
    assert p.parcelas_pagas == 0
    with pytest.raises(ErroDeNegocio):
        p.estornar(1)


def test_validacoes_do_contrato():
    with pytest.raises(ErroDeNegocio):
        Parcelamento("", R(10), 1, date(2026, 1, 1))
    with pytest.raises(ErroDeNegocio):
        Parcelamento("X", Dinheiro.zero(), 1, date(2026, 1, 1))
    with pytest.raises(ErroDeNegocio):
        Parcelamento("X", R(10), 0, date(2026, 1, 1))


def test_ida_e_volta_pelo_dicionario():
    p = contrato()
    p.pagar(2, date(2026, 9, 9))
    copia = Parcelamento.de_dict(p.para_dict())
    assert copia.para_dict() == p.para_dict()
    assert copia.parcela(2).pago_em == date(2026, 9, 9)
