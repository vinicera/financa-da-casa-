"""Estado compartilhado do servidor: a ``Casa`` carregada + o repositório."""

import threading
from collections.abc import Callable
from datetime import date
from typing import TypeVar

from .modelos import Casa, CicloFinanceiro
from .repositorio import Repositorio

T = TypeVar("T")


class Estado:
    """Mantém a ``Casa`` em memória e grava no repositório a cada alteração.

    O servidor atende requisições em paralelo; o ``Lock`` garante que duas
    alterações não aconteçam ao mesmo tempo sobre o mesmo objeto.
    """

    def __init__(self, repositorio: Repositorio, hoje: Callable[[], date] = date.today) -> None:
        self._repositorio = repositorio
        self._trava = threading.Lock()
        self.casa: Casa = repositorio.carregar()
        self.hoje = hoje

    def alterar(self, operacao: Callable[[Casa], T]) -> T:
        """Executa ``operacao(casa)`` com exclusividade e salva o resultado."""
        with self._trava:
            resultado = operacao(self.casa)
            self._repositorio.salvar(self.casa)
            return resultado

    def ciclo(self, chave: str | None) -> CicloFinanceiro:
        """O ciclo pedido na URL (``?ciclo=2026-11-01``), ou o atual."""
        d = self.hoje()
        if chave:
            try:
                d = date.fromisoformat(chave)
            except ValueError:
                pass
        return self.casa.ciclo_da_data(d)
