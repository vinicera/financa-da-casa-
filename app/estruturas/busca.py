"""Busca binária sobre listas ordenadas.

A cada passo a busca descarta metade da lista, então encontra a posição em
O(log n) — com 1 milhão de gastos, cerca de 20 comparações.

Uso no sistema: os gastos ficam guardados **ordenados por data**. Para
mostrar os gastos de um ciclo (ex.: 20/10 a 19/11), duas buscas binárias
acham onde o período começa e onde termina, sem percorrer a lista toda.
"""

from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


def limite_inferior(itens: list[T], alvo: Any, chave: Callable[[T], Any] = lambda x: x) -> int:
    """Primeira posição cujo item tem chave >= ``alvo``."""
    ini, fim = 0, len(itens)
    while ini < fim:
        meio = (ini + fim) // 2
        if chave(itens[meio]) < alvo:
            ini = meio + 1
        else:
            fim = meio
    return ini


def limite_superior(itens: list[T], alvo: Any, chave: Callable[[T], Any] = lambda x: x) -> int:
    """Primeira posição cujo item tem chave > ``alvo``."""
    ini, fim = 0, len(itens)
    while ini < fim:
        meio = (ini + fim) // 2
        if chave(itens[meio]) <= alvo:
            ini = meio + 1
        else:
            fim = meio
    return ini


def fatia_por_intervalo(itens: list[T], inicio: Any, fim: Any, chave: Callable[[T], Any] = lambda x: x) -> list[T]:
    """Itens com ``inicio <= chave <= fim`` numa lista ordenada por ``chave``. O(log n + k)."""
    return itens[limite_inferior(itens, inicio, chave) : limite_superior(itens, fim, chave)]


def inserir_ordenado(itens: list[T], item: T, chave: Callable[[T], Any] = lambda x: x) -> int:
    """Insere mantendo a ordem (depois dos iguais). Devolve a posição usada."""
    pos = limite_superior(itens, chave(item), chave)
    itens.insert(pos, item)
    return pos
