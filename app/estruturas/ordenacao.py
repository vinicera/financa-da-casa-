"""Ordenação por intercalação (Merge Sort).

Estratégia "dividir para conquistar": divide a lista ao meio, ordena cada
metade recursivamente e intercala as duas metades já ordenadas.

- Complexidade: O(n log n) em todos os casos.
- Estável: itens com a mesma chave mantêm a ordem original. Isso importa na
  tela de gastos — ordenar por valor não embaralha gastos de mesmo valor.

Uso no sistema: ordenar a lista de gastos por data, valor ou descrição.
"""

from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


def merge_sort(itens: list[T], chave: Callable[[T], Any] = lambda x: x, decrescente: bool = False) -> list[T]:
    """Devolve uma NOVA lista ordenada (não altera a original)."""
    if len(itens) <= 1:
        return list(itens)
    meio = len(itens) // 2
    esquerda = merge_sort(itens[:meio], chave, decrescente)
    direita = merge_sort(itens[meio:], chave, decrescente)
    return _intercalar(esquerda, direita, chave, decrescente)


def _intercalar(a: list[T], b: list[T], chave: Callable[[T], Any], decrescente: bool) -> list[T]:
    resultado: list[T] = []
    i = j = 0
    while i < len(a) and j < len(b):
        ka, kb = chave(a[i]), chave(b[j])
        # Em empate pega da esquerda primeiro: é isso que garante a estabilidade.
        pega_da_esquerda = ka >= kb if decrescente else ka <= kb
        if pega_da_esquerda:
            resultado.append(a[i])
            i += 1
        else:
            resultado.append(b[j])
            j += 1
    resultado.extend(a[i:])
    resultado.extend(b[j:])
    return resultado
