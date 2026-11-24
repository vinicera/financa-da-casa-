from datetime import date, timedelta

import pytest

from app.modelos import CicloFinanceiro


def intervalo(d: date, dia_inicio: int) -> tuple[str, str]:
    c = CicloFinanceiro.da_data(d, dia_inicio)
    return c.inicio.isoformat(), c.fim.isoformat()


def test_ciclo_que_comeca_no_dia_20():
    assert intervalo(date(2026, 10, 15), 20) == ("2026-09-20", "2026-10-19")
    assert intervalo(date(2026, 10, 19), 20) == ("2026-09-20", "2026-10-19")
    assert intervalo(date(2026, 10, 20), 20) == ("2026-10-20", "2026-11-19")


def test_dia_1_e_o_mes_do_calendario():
    assert intervalo(date(2026, 2, 10), 1) == ("2026-02-01", "2026-02-28")
    assert intervalo(date(2024, 2, 10), 1) == ("2024-02-01", "2024-02-29")
    assert intervalo(date(2026, 12, 31), 1) == ("2026-12-01", "2026-12-31")


def test_dia_31_em_fevereiro_vira_o_ultimo_dia():
    jan = CicloFinanceiro.da_data(date(2027, 1, 31), 31)
    assert (jan.inicio, jan.fim) == (date(2027, 1, 31), date(2027, 2, 27))
    assert jan.proximo().inicio == date(2027, 2, 28)


def test_virada_de_ano():
    assert intervalo(date(2027, 1, 5), 20) == ("2026-12-20", "2027-01-19")


@pytest.mark.parametrize("dia_inicio", [1, 5, 20, 28, 31])
def test_ciclos_sao_contiguos_e_anterior_desfaz_proximo(dia_inicio):
    c = CicloFinanceiro.da_data(date(2026, 1, 10), dia_inicio)
    for _ in range(24):
        n = c.proximo()
        assert n.inicio == c.fim + timedelta(days=1)  # sem buraco, sem sobreposição
        assert n.anterior() == c
        c = n


def test_total_de_dias():
    assert CicloFinanceiro.da_data(date(2026, 10, 31), 20).total_dias == 31
    assert CicloFinanceiro.da_data(date(2027, 2, 10), 1).total_dias == 28
    # 12 ciclos seguidos somam exatamente um ano.
    c = CicloFinanceiro.da_data(date(2026, 1, 25), 20)
    soma = 0
    for _ in range(12):
        soma += c.total_dias
        c = c.proximo()
    assert soma == 365


def test_dia_atual_e_dias_restantes():
    c = CicloFinanceiro.da_data(date(2026, 10, 31), 20)  # 20/10 a 19/11
    assert c.dia_atual(date(2026, 10, 31)) == 12
    assert c.dia_atual(date(2026, 11, 19)) == 31
    assert c.dia_atual(date(2026, 1, 1)) == 0
    assert c.dia_atual(date(2027, 1, 1)) == 31
    assert c.dias_restantes(date(2026, 11, 19)) == 1
    assert c.dias_restantes(date(2026, 10, 20)) == 31


def test_rotulos():
    assert CicloFinanceiro.da_data(date(2026, 4, 3), 1).rotulo == "Abr 2026"
    assert CicloFinanceiro.da_data(date(2026, 4, 25), 20).rotulo == "Abr/Mai 2026"
    assert CicloFinanceiro.da_data(date(2026, 12, 25), 20).rotulo == "Dez 2026/Jan 2027"
    assert CicloFinanceiro.da_data(date(2026, 4, 25), 20).intervalo == "20/04 a 19/05"


def test_dia_de_inicio_invalido():
    with pytest.raises(ValueError):
        CicloFinanceiro.da_data(date(2026, 1, 1), 0)
