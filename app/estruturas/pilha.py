"""Pilha (LIFO) implementada com nós encadeados.

Uso no sistema: histórico de ações para o botão **Desfazer**. A última ação
feita é a primeira a ser desfeita — exatamente o comportamento de uma pilha.

Complexidade: empilhar, desempilhar e topo são O(1).
"""

from collections.abc import Iterator
from typing import Generic, TypeVar

T = TypeVar("T")


class _No(Generic[T]):
    """Nó da lista encadeada que guarda a pilha."""

    __slots__ = ("valor", "proximo")

    def __init__(self, valor: T, proximo: "_No[T] | None" = None) -> None:
        self.valor = valor
        self.proximo = proximo


class Pilha(Generic[T]):
    def __init__(self) -> None:
        self._topo: _No[T] | None = None
        self._tamanho = 0

    def empilhar(self, valor: T) -> None:
        """Coloca ``valor`` no topo. O(1)."""
        self._topo = _No(valor, self._topo)
        self._tamanho += 1

    def desempilhar(self) -> T:
        """Remove e devolve o topo. O(1). Lança ``IndexError`` se vazia."""
        if self._topo is None:
            raise IndexError("desempilhar de pilha vazia")
        no = self._topo
        self._topo = no.proximo
        self._tamanho -= 1
        return no.valor

    def topo(self) -> T:
        """Devolve o topo sem remover. O(1)."""
        if self._topo is None:
            raise IndexError("topo de pilha vazia")
        return self._topo.valor

    def esta_vazia(self) -> bool:
        return self._topo is None

    def __len__(self) -> int:
        return self._tamanho

    def __iter__(self) -> Iterator[T]:
        """Percorre do topo para a base."""
        atual = self._topo
        while atual is not None:
            yield atual.valor
            atual = atual.proximo

    def __repr__(self) -> str:
        return f"Pilha({list(self)!r})"
