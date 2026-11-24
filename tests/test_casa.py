from datetime import date

import pytest

from app.exemplo import criar_casa_exemplo
from app.modelos import Casa, Dinheiro, ErroDeNegocio, NaoEncontrado
from app.repositorio import RepositorioEmMemoria, RepositorioJson

R = Dinheiro.de_reais
HOJE = date(2026, 11, 16)


@pytest.fixture
def casa() -> Casa:
    c = Casa("Teste", dia_inicio_ciclo=1)
    c.lancar_entrada("Salário", R(5000), date(2026, 11, 1))
    return c


class TestResumo:
    def test_livre_desconta_aportes_e_gastos_sem_cobertura(self, casa):
        mercado = casa.criar_caixinha("variavel", "Mercado", R(1000))
        lazer = casa.criar_caixinha("variavel", "Lazer")  # sem aporte
        casa.criar_caixinha("reserva", "Emergência", R(500))
        casa.lancar_gasto("Compra", R(400), date(2026, 11, 3), mercado.id)
        casa.lancar_gasto("Pizza", R(80), date(2026, 11, 4), lazer.id)
        casa.lancar_gasto("Farmácia", R(20), date(2026, 11, 5))  # sem caixinha

        r = casa.resumo(HOJE)
        # 1000 (mercado) + 500 (reserva) + 80 (lazer sem aporte) + 20 (sem caixinha)
        assert r.alocado == R(1600)
        assert r.livre == R(3400)
        assert r.gasto_total == R(500)
        assert r.excedente == Dinheiro.zero()
        # 15 dias restantes (16 a 30 de novembro)
        assert r.livre_por_dia == Dinheiro(R(3400).centavos // 15)

    def test_excedente_quando_compromete_mais_do_que_entrou(self, casa):
        casa.criar_caixinha("conta_fixa", "Aluguel", R(6000))
        r = casa.resumo(HOJE)
        assert r.livre == Dinheiro.zero()
        assert r.excedente == R(1000)

    def test_gastos_de_outro_ciclo_nao_entram(self, casa):
        casa.lancar_gasto("Outubro", R(999), date(2026, 10, 31))
        casa.lancar_gasto("Dezembro", R(999), date(2026, 12, 1))
        casa.lancar_gasto("Novembro", R(10), date(2026, 11, 30))
        assert casa.resumo(HOJE).gasto_total == R(10)

    def test_ritmo(self, casa):
        mercado = casa.criar_caixinha("variavel", "Mercado", R(1000))
        casa.lancar_gasto("Compra grande", R(900), date(2026, 11, 2), mercado.id)
        r = casa.resumo(date(2026, 11, 6))  # dia 6 de 30 = 20%
        assert (r.pct_do_ciclo, r.pct_gasto, r.situacao) == (20, 90, "adiantado")
        r = casa.resumo(date(2026, 11, 28))  # 93% do ciclo
        assert r.situacao == "no_ritmo"


class TestDesfazer:
    def test_desfaz_na_ordem_inversa(self, casa):
        g1 = casa.lancar_gasto("A", R(10), date(2026, 11, 2))
        casa.lancar_gasto("B", R(20), date(2026, 11, 3))
        casa.remover_gasto(g1.id)
        ciclo = casa.ciclo_da_data(HOJE)
        assert [g.descricao for g in casa.gastos_do_ciclo(ciclo)] == ["B"]

        casa.desfazer()  # volta a exclusão de A
        assert {g.descricao for g in casa.gastos_do_ciclo(ciclo)} == {"A", "B"}
        casa.desfazer()  # tira B
        casa.desfazer()  # tira A
        casa.desfazer()  # tira a entrada do fixture
        assert casa.gastos_do_ciclo(ciclo) == []
        assert casa.desfazer() is None

    def test_desfaz_pagamento_de_parcela(self, casa):
        p = casa.criar_parcelamento("TV", R(1200), 3, date(2026, 11, 10))
        casa.pagar_parcela(p.id, 1, HOJE)
        assert p.parcelas_pagas == 1
        acao = casa.desfazer()
        assert p.parcelas_pagas == 0
        assert "parcela 1" in acao.descricao

    def test_acao_que_falha_nao_entra_na_pilha(self, casa):
        with pytest.raises(NaoEncontrado):
            casa.remover_gasto("nao-existe")
        assert casa.desfazer().descricao.startswith("entrada")


def test_gastos_ordenados_de_varios_jeitos(casa):
    casa.lancar_gasto("Banana", R(5), date(2026, 11, 3))
    casa.lancar_gasto("abacaxi", R(30), date(2026, 11, 1))
    casa.lancar_gasto("Caju", R(12), date(2026, 11, 2))
    ciclo = casa.ciclo_da_data(HOJE)

    def nomes(ordem: str) -> list[str]:
        return [g.descricao for g in casa.gastos_do_ciclo(ciclo, ordem)]

    assert nomes("recentes") == ["Banana", "Caju", "abacaxi"]
    assert nomes("antigos") == ["abacaxi", "Caju", "Banana"]
    assert nomes("maior_valor") == ["abacaxi", "Caju", "Banana"]
    assert nomes("menor_valor") == ["Banana", "Caju", "abacaxi"]
    assert nomes("descricao") == ["abacaxi", "Banana", "Caju"]


def test_proximos_vencimentos_vem_em_ordem_de_data(casa):
    a = casa.criar_parcelamento("A", R(300), 3, date(2026, 12, 20))
    casa.criar_parcelamento("B", R(200), 2, date(2026, 12, 5))
    casa.pagar_parcela(a.id, 1, HOJE)
    vencs = [(p.descricao, p.numero) for p in casa.proximos_vencimentos(4)]
    assert vencs == [("B", 1), ("B", 2), ("A", 2), ("A", 3)]


def test_nao_exclui_caixinha_com_gastos(casa):
    c = casa.criar_caixinha("variavel", "Mercado", R(100))
    casa.lancar_gasto("X", R(1), HOJE, c.id)
    with pytest.raises(ErroDeNegocio):
        casa.remover_caixinha(c.id)


def test_gasto_em_caixinha_inexistente(casa):
    with pytest.raises(NaoEncontrado):
        casa.lancar_gasto("X", R(1), HOJE, "fantasma")


@pytest.mark.parametrize("repo_cls", ["memoria", "json"])
def test_persistencia_ida_e_volta(repo_cls, tmp_path):
    original = criar_casa_exemplo(HOJE)
    repo = RepositorioEmMemoria() if repo_cls == "memoria" else RepositorioJson(tmp_path / "casa.json")
    repo.salvar(original)
    carregada = repo.carregar()
    assert carregada.para_dict() == original.para_dict()
    assert carregada.resumo(HOJE) .livre == original.resumo(HOJE).livre


def test_json_inexistente_comeca_vazio(tmp_path):
    casa = RepositorioJson(tmp_path / "nao_existe.json").carregar()
    assert casa.caixinhas == []
