import pytest

from app.modelos import Caixinha, ContaFixa, Dinheiro, ErroDeNegocio, Reserva, Variavel

R = Dinheiro.de_reais


def test_classe_abstrata_nao_pode_ser_instanciada():
    with pytest.raises(TypeError):
        Caixinha("Qualquer")  # type: ignore[abstract]


def test_fabrica_cria_a_subclasse_certa():
    assert isinstance(Caixinha.criar("conta_fixa", "Aluguel", R(1800)), ContaFixa)
    assert isinstance(Caixinha.criar("variavel", "Mercado"), Variavel)
    assert isinstance(Caixinha.criar("reserva", "Emergência"), Reserva)
    with pytest.raises(ErroDeNegocio):
        Caixinha.criar("inexistente", "X")


def test_encapsulamento_valida_nome_e_aporte():
    with pytest.raises(ErroDeNegocio):
        Variavel("   ")
    c = Variavel("Mercado", R(100))
    with pytest.raises(ErroDeNegocio):
        c.aporte = Dinheiro(-1)
    c.nome = "  Feira  "
    assert c.nome == "Feira"


def test_disponivel_e_estouro():
    mercado = Variavel("Mercado", R(555))
    assert mercado.disponivel(R(226.12)) == R(328.88)
    assert not mercado.estourou(R(555))
    assert mercado.estourou(R(555.01))
    assert mercado.percentual_usado(R(277.50)) == 50


class TestPolimorfismoAlocado:
    """A mesma pergunta — "quanto você tira da renda?" — respondida por cada tipo."""

    def test_caixinha_comum_reserva_o_aporte(self):
        assert Variavel("Mercado", R(300)).alocado_da_renda(R(100)) == R(300)

    def test_gasto_acima_do_aporte_tambem_sai_da_renda(self):
        assert Variavel("Mercado", R(300)).alocado_da_renda(R(350)) == R(350)

    def test_sem_aporte_o_gasto_inteiro_sai_do_livre(self):
        assert Variavel("Lazer").alocado_da_renda(R(80)) == R(80)
        assert Variavel("Lazer").alocado_da_renda(Dinheiro.zero()) == Dinheiro.zero()

    def test_reserva_so_conta_o_que_foi_guardado(self):
        # Sacar da reserva usa dinheiro de ciclos anteriores, não a renda deste.
        assert Reserva("Emergência", R(400)).alocado_da_renda(R(1000)) == R(400)

    def test_so_reserva_atravessa_o_ciclo(self):
        assert Reserva("x").acumula_entre_ciclos()
        assert not Variavel("x").acumula_entre_ciclos()
        assert not ContaFixa("x").acumula_entre_ciclos()


def test_dicas_mudam_por_tipo():
    assert ContaFixa("Luz", R(180)).dica(R(180)) == "Paga."
    assert ContaFixa("Luz", R(180)).dica(R(200)) == "Veio R$ 20,00 acima do previsto."
    assert Variavel("Mercado", R(100)).dica(R(130)) == "Estourou R$ 30,00."
    assert Reserva("Viagem", R(200)).dica(Dinheiro.zero()) == "Guardando R$ 200,00 por ciclo."


def test_ida_e_volta_pelo_dicionario():
    original = Reserva("Viagem", R(250), "✈️")
    copia = Caixinha.de_dict(original.para_dict())
    assert type(copia) is Reserva
    assert (copia.id, copia.nome, copia.aporte, copia.icone) == (original.id, "Viagem", R(250), "✈️")
