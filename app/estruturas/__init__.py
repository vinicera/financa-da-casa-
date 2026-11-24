"""Estruturas de dados e algoritmos implementados do zero."""

from .busca import fatia_por_intervalo, inserir_ordenado, limite_inferior, limite_superior
from .fila_prioridade import FilaDePrioridade
from .ordenacao import merge_sort
from .pilha import Pilha

__all__ = [
    "FilaDePrioridade",
    "Pilha",
    "fatia_por_intervalo",
    "inserir_ordenado",
    "limite_inferior",
    "limite_superior",
    "merge_sort",
]
