import random

import pytest

from app.estruturas import (
    FilaDePrioridade,
    Pilha,
    fatia_por_intervalo,
    inserir_ordenado,
    limite_inferior,
    limite_superior,
    merge_sort,
)


class TestPilha:
    def test_ultimo_a_entrar_e_o_primeiro_a_sair(self):
        p = Pilha()
        for x in (1, 2, 3):
            p.empilhar(x)
        assert len(p) == 3
        assert p.topo() == 3
        assert [p.desempilhar(), p.desempilhar(), p.desempilhar()] == [3, 2, 1]
        assert p.esta_vazia()

    def test_iteracao_vai_do_topo_para_a_base(self):
        p = Pilha()
        for x in "abc":
            p.empilhar(x)
        assert list(p) == ["c", "b", "a"]

    def test_pilha_vazia_lanca_erro(self):
        with pytest.raises(IndexError):
            Pilha().desempilhar()
        with pytest.raises(IndexError):
            Pilha().topo()


class TestFilaDePrioridade:
    def test_sai_sempre_o_menor(self):
        fila = FilaDePrioridade()
        valores = [random.randint(-1000, 1000) for _ in range(300)]
        for v in valores:
            fila.inserir(v)
        assert len(fila) == 300
        saida = [fila.remover_minimo() for _ in range(300)]
        assert saida == sorted(valores)

    def test_usa_a_chave_e_desempata_pela_ordem_de_chegada(self):
        fila = FilaDePrioridade(chave=lambda t: t[0])
        for item in [(2, "b"), (1, "x"), (2, "a"), (1, "y")]:
            fila.inserir(item)
        assert fila.ver_minimo() == (1, "x")
        assert [fila.remover_minimo() for _ in range(4)] == [(1, "x"), (1, "y"), (2, "b"), (2, "a")]

    def test_vazia_lanca_erro(self):
        with pytest.raises(IndexError):
            FilaDePrioridade().remover_minimo()


class TestMergeSort:
    @pytest.mark.parametrize("tamanho", [0, 1, 2, 7, 100])
    def test_ordena_igual_ao_sorted(self, tamanho):
        dados = [random.randint(0, 50) for _ in range(tamanho)]
        assert merge_sort(dados) == sorted(dados)
        assert merge_sort(dados, decrescente=True) == sorted(dados, reverse=True)

    def test_nao_altera_a_lista_original(self):
        dados = [3, 1, 2]
        merge_sort(dados)
        assert dados == [3, 1, 2]

    def test_e_estavel(self):
        # Mesma chave: a ordem original precisa ser mantida.
        dados = [("b", 1), ("a", 2), ("c", 1), ("d", 2)]
        assert merge_sort(dados, chave=lambda t: t[1]) == [("b", 1), ("c", 1), ("a", 2), ("d", 2)]
        assert merge_sort(dados, chave=lambda t: t[1], decrescente=True) == [
            ("a", 2), ("d", 2), ("b", 1), ("c", 1)
        ]


class TestBuscaBinaria:
    dados = [1, 3, 3, 3, 5, 8, 13]

    def test_limites(self):
        assert limite_inferior(self.dados, 3) == 1
        assert limite_superior(self.dados, 3) == 4
        assert limite_inferior(self.dados, 4) == 4
        assert limite_inferior(self.dados, 0) == 0
        assert limite_superior(self.dados, 99) == len(self.dados)

    def test_fatia_por_intervalo_inclui_as_pontas(self):
        assert fatia_por_intervalo(self.dados, 3, 8) == [3, 3, 3, 5, 8]
        assert fatia_por_intervalo(self.dados, 9, 12) == []

    def test_inserir_ordenado_mantem_a_ordem(self):
        lista: list[int] = []
        for v in [5, 1, 4, 1, 9, 2]:
            inserir_ordenado(lista, v)
        assert lista == [1, 1, 2, 4, 5, 9]
