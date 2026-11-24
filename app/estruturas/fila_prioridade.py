"""Fila de prioridade implementada com heap binário mínimo.

O heap é uma árvore binária completa guardada num vetor (lista): o filho
esquerdo do índice ``i`` fica em ``2i + 1``, o direito em ``2i + 2`` e o pai
em ``(i - 1) // 2``. Todo pai é menor ou igual aos filhos, então o menor
elemento está sempre na raiz (índice 0).

Uso no sistema: **próximos vencimentos** de parcelas — a parcela que vence
primeiro sai primeiro, mesmo que tenha sido cadastrada por último.

Complexidade: inserir e remover_minimo são O(log n); ver_minimo é O(1).
"""

from collections.abc import Callable
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class FilaDePrioridade(Generic[T]):
    def __init__(self, chave: Callable[[T], Any] = lambda x: x) -> None:
        """``chave`` diz o que comparar (ex.: a data de vencimento)."""
        self._dados: list[tuple[Any, int, T]] = []
        self._chave = chave
        self._contador = 0  # desempate estável: quem entrou antes sai antes

    def inserir(self, item: T) -> None:
        self._dados.append((self._chave(item), self._contador, item))
        self._contador += 1
        self._subir(len(self._dados) - 1)

    def remover_minimo(self) -> T:
        if not self._dados:
            raise IndexError("remover de fila de prioridade vazia")
        menor = self._dados[0]
        ultimo = self._dados.pop()
        if self._dados:
            self._dados[0] = ultimo
            self._descer(0)
        return menor[2]

    def ver_minimo(self) -> T:
        if not self._dados:
            raise IndexError("fila de prioridade vazia")
        return self._dados[0][2]

    def esta_vazia(self) -> bool:
        return not self._dados

    def __len__(self) -> int:
        return len(self._dados)

    # -- operações internas do heap ----------------------------------------

    def _menor(self, i: int, j: int) -> bool:
        return self._dados[i][:2] < self._dados[j][:2]

    def _trocar(self, i: int, j: int) -> None:
        self._dados[i], self._dados[j] = self._dados[j], self._dados[i]

    def _subir(self, i: int) -> None:
        """Sobe o elemento enquanto ele for menor que o pai."""
        while i > 0:
            pai = (i - 1) // 2
            if not self._menor(i, pai):
                break
            self._trocar(i, pai)
            i = pai

    def _descer(self, i: int) -> None:
        """Desce o elemento trocando com o menor filho até o heap ficar válido."""
        n = len(self._dados)
        while True:
            esq, dir_ = 2 * i + 1, 2 * i + 2
            menor = i
            if esq < n and self._menor(esq, menor):
                menor = esq
            if dir_ < n and self._menor(dir_, menor):
                menor = dir_
            if menor == i:
                return
            self._trocar(i, menor)
            i = menor
