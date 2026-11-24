"""Lançamentos: tudo que entra ou sai de dinheiro.

    Lancamento (abstrata)
    ├── Gasto    — dinheiro que saiu (pertence a uma caixinha, ou a nenhuma)
    └── Entrada  — dinheiro que entrou (salário, extra)
"""

import uuid
from abc import ABC, abstractmethod
from datetime import date
from typing import Any, ClassVar

from .dinheiro import Dinheiro
from .erros import ErroDeNegocio


class Lancamento(ABC):
    def __init__(self, descricao: str, valor: Dinheiro, data: date, id: str | None = None) -> None:
        descricao = (descricao or "").strip()
        if not descricao:
            raise ErroDeNegocio("Informe uma descrição.")
        if not valor.eh_positivo():
            raise ErroDeNegocio("O valor precisa ser maior que zero.")
        self.id = id or uuid.uuid4().hex[:8]
        self.descricao = descricao
        self.valor = valor
        self.data = data

    @property
    @abstractmethod
    def sinal(self) -> int:
        """+1 para entrada de dinheiro, −1 para saída."""

    def efeito_no_saldo(self) -> Dinheiro:
        """Quanto o lançamento muda o saldo (positivo ou negativo)."""
        return self.valor * self.sinal

    def para_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "descricao": self.descricao,
            "valor_centavos": self.valor.centavos,
            "data": self.data.isoformat(),
        }

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.descricao!r}, {self.valor}, {self.data:%d/%m/%Y})"


class Gasto(Lancamento):
    def __init__(
        self,
        descricao: str,
        valor: Dinheiro,
        data: date,
        caixinha_id: str | None = None,
        id: str | None = None,
    ) -> None:
        super().__init__(descricao, valor, data, id)
        self.caixinha_id = caixinha_id

    @property
    def sinal(self) -> int:
        return -1

    def para_dict(self) -> dict[str, Any]:
        return {**super().para_dict(), "caixinha_id": self.caixinha_id}

    @classmethod
    def de_dict(cls, d: dict[str, Any]) -> "Gasto":
        return cls(
            descricao=d["descricao"],
            valor=Dinheiro(d["valor_centavos"]),
            data=date.fromisoformat(d["data"]),
            caixinha_id=d.get("caixinha_id"),
            id=d["id"],
        )


class Entrada(Lancamento):
    NATUREZAS: ClassVar[dict[str, str]] = {"renda": "Renda", "extra": "Extra"}

    def __init__(
        self,
        descricao: str,
        valor: Dinheiro,
        data: date,
        natureza: str = "renda",
        id: str | None = None,
    ) -> None:
        super().__init__(descricao, valor, data, id)
        if natureza not in self.NATUREZAS:
            raise ErroDeNegocio(f"Natureza inválida: {natureza!r}")
        self.natureza = natureza

    @property
    def sinal(self) -> int:
        return +1

    def para_dict(self) -> dict[str, Any]:
        return {**super().para_dict(), "natureza": self.natureza}

    @classmethod
    def de_dict(cls, d: dict[str, Any]) -> "Entrada":
        return cls(
            descricao=d["descricao"],
            valor=Dinheiro(d["valor_centavos"]),
            data=date.fromisoformat(d["data"]),
            natureza=d.get("natureza", "renda"),
            id=d["id"],
        )
