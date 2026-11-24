import pytest

from app.modelos import Dinheiro, ErroDeNegocio


def test_converte_reais_sem_erro_de_float():
    assert Dinheiro.de_reais(45.9).centavos == 4590
    assert Dinheiro.de_reais(0.1).centavos == 10
    assert Dinheiro.de_reais("1234.56").centavos == 123456


def test_soma_exata_onde_float_erra():
    assert 0.1 + 0.2 != 0.3  # o problema
    assert Dinheiro.de_reais(0.1) + Dinheiro.de_reais(0.2) == Dinheiro.de_reais(0.3)  # a solução


def test_le_o_que_o_usuario_digita():
    assert Dinheiro.de_texto("45,90").centavos == 4590
    assert Dinheiro.de_texto("1.234,56").centavos == 123456
    assert Dinheiro.de_texto("R$ 10").centavos == 1000
    assert Dinheiro.de_texto("45.90").centavos == 4590
    with pytest.raises(ErroDeNegocio):
        Dinheiro.de_texto("abc")
    with pytest.raises(ErroDeNegocio):
        Dinheiro.de_texto("")


def test_formata_em_reais():
    assert str(Dinheiro(123456)) == "R$ 1.234,56"
    assert str(Dinheiro(5)) == "R$ 0,05"
    assert str(Dinheiro(-150000)) == "-R$ 1.500,00"
    assert str(Dinheiro(123456789)) == "R$ 1.234.567,89"


def test_operadores():
    a, b = Dinheiro(500), Dinheiro(150)
    assert a + b == Dinheiro(650)
    assert a - b == Dinheiro(350)
    assert b - a == Dinheiro(-350)
    assert -a == Dinheiro(-500)
    assert a * 3 == Dinheiro(1500) == 3 * a
    assert b < a and a > b
    assert sum([a, b, b]) == Dinheiro(800)
    assert not Dinheiro.zero() and a


def test_e_imutavel():
    d = Dinheiro(100)
    with pytest.raises(AttributeError):
        d.centavos = 5  # type: ignore[misc]


def test_so_aceita_inteiro():
    with pytest.raises(TypeError):
        Dinheiro(10.5)  # type: ignore[arg-type]


class TestDividirEm:
    def test_divide_igual_quando_fecha(self):
        assert Dinheiro(30000).dividir_em(3) == [Dinheiro(10000)] * 3

    def test_a_ultima_parte_absorve_a_sobra(self):
        assert [d.centavos for d in Dinheiro(10).dividir_em(3)] == [3, 3, 4]
        assert [d.centavos for d in Dinheiro(100).dividir_em(3)] == [33, 33, 34]

    @pytest.mark.parametrize("total", [1, 7, 100, 12345, 99999])
    def test_a_soma_sempre_fecha(self, total):
        assert sum(Dinheiro(total).dividir_em(7)) == Dinheiro(total)

    def test_partes_invalidas(self):
        assert Dinheiro(100).dividir_em(0) == []
