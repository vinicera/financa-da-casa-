"""Onde a ``Casa`` é guardada (abstração + duas implementações).

O resto do sistema só conhece a interface ``Repositorio`` (carregar/salvar).
Trocar o arquivo JSON por um banco de dados no futuro seria escrever outra
subclasse, sem mexer em nenhuma outra parte do código.
"""

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path

from .modelos import Casa


class Repositorio(ABC):
    @abstractmethod
    def carregar(self) -> Casa: ...

    @abstractmethod
    def salvar(self, casa: Casa) -> None: ...


class RepositorioEmMemoria(Repositorio):
    """Guarda só enquanto o programa roda — usado nos testes."""

    def __init__(self, casa: Casa | None = None) -> None:
        self._dados = (casa or Casa()).para_dict()

    def carregar(self) -> Casa:
        return Casa.de_dict(self._dados)

    def salvar(self, casa: Casa) -> None:
        self._dados = casa.para_dict()


class RepositorioJson(Repositorio):
    """Guarda a casa inteira num arquivo ``.json``."""

    def __init__(self, caminho: str | Path) -> None:
        self.caminho = Path(caminho)

    def carregar(self) -> Casa:
        if not self.caminho.exists():
            return Casa()
        with self.caminho.open(encoding="utf-8") as f:
            return Casa.de_dict(json.load(f))

    def salvar(self, casa: Casa) -> None:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        # Escreve num arquivo temporário e troca no fim: se o programa cair no
        # meio da gravação, o arquivo antigo continua inteiro.
        temporario = self.caminho.with_suffix(".tmp")
        with temporario.open("w", encoding="utf-8") as f:
            json.dump(casa.para_dict(), f, ensure_ascii=False, indent=2)
        os.replace(temporario, self.caminho)
