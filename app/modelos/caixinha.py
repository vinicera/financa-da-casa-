"""Caixinhas: envelopes de dinheiro com um propósito.

Hierarquia de classes (herança + polimorfismo):

    Caixinha (abstrata)
    ├── ContaFixa   — contas de valor previsível (aluguel, internet)
    ├── Variavel    — consumo que oscila (mercado, lazer)
    └── Reserva     — dinheiro guardado (emergência, viagem)

Cada subclasse responde do seu jeito às mesmas perguntas — "quanto você tira
da renda do mês?" e "seu saldo passa para o próximo ciclo?". Quem usa uma
caixinha não precisa saber de que tipo ela é: só chama o método.
"""

import uuid
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from .dinheiro import Dinheiro
from .erros import ErroDeNegocio


class Caixinha(ABC):
    """Classe base abstrata — não dá para criar uma ``Caixinha`` "pura"."""

    tipo: ClassVar[str]
    nome_do_tipo: ClassVar[str]
    _registro: ClassVar[dict[str, type["Caixinha"]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Cada subclasse se registra sozinha pelo ``tipo`` (usado em ``de_dict``)."""
        super().__init_subclass__(**kwargs)
        Caixinha._registro[cls.tipo] = cls

    def __init__(
        self,
        nome: str,
        aporte: Dinheiro | None = None,
        icone: str = "📦",
        id: str | None = None,
    ) -> None:
        self.id = id or uuid.uuid4().hex[:8]
        self.nome = nome  # passa pela validação do setter abaixo
        self.aporte = aporte
        self.icone = icone or "📦"

    # -- encapsulamento: atributos validados por propriedades ------------------

    @property
    def nome(self) -> str:
        return self._nome

    @nome.setter
    def nome(self, valor: str) -> None:
        valor = (valor or "").strip()
        if not valor:
            raise ErroDeNegocio("A caixinha precisa de um nome.")
        self._nome = valor

    @property
    def aporte(self) -> Dinheiro | None:
        """Quanto da renda é separado para a caixinha a cada ciclo.

        ``None`` = caixinha "sem aporte": os gastos saem direto do dinheiro livre.
        """
        return self._aporte

    @aporte.setter
    def aporte(self, valor: Dinheiro | None) -> None:
        if valor is not None and valor.centavos < 0:
            raise ErroDeNegocio("O aporte não pode ser negativo.")
        self._aporte = valor

    # -- comportamento comum ---------------------------------------------------

    def disponivel(self, gasto: Dinheiro) -> Dinheiro:
        """Quanto ainda dá para gastar no ciclo: aporte − gasto."""
        return (self.aporte or Dinheiro.zero()) - gasto

    def estourou(self, gasto: Dinheiro) -> bool:
        return self.aporte is not None and gasto > self.aporte

    def percentual_usado(self, gasto: Dinheiro) -> int:
        if not self.aporte:
            return 0
        return round(gasto.centavos * 100 / self.aporte.centavos)

    # -- comportamento que muda conforme o tipo (polimorfismo) -----------------

    def alocado_da_renda(self, gasto: Dinheiro) -> Dinheiro:
        """Quanto esta caixinha tira da renda do ciclo.

        Um real tem destino de duas formas: está **reservado** no aporte ou
        **já foi embora** (gasto além do aporte). Por padrão conta as duas.
        """
        aporte = self.aporte or Dinheiro.zero()
        vazou = (gasto - aporte).positivo_ou_zero()
        return aporte + vazou

    def entra_no_ritmo(self) -> bool:
        """O gasto desta caixinha é comparado com o tempo do ciclo?"""
        return True

    @abstractmethod
    def acumula_entre_ciclos(self) -> bool:
        """O saldo que sobrou passa para o próximo ciclo?"""

    @abstractmethod
    def dica(self, gasto: Dinheiro) -> str:
        """Uma frase curta sobre a situação da caixinha."""

    # -- conversão para/de dicionário (persistência em JSON) -------------------

    def para_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tipo": self.tipo,
            "nome": self.nome,
            "icone": self.icone,
            "aporte_centavos": None if self.aporte is None else self.aporte.centavos,
        }

    @classmethod
    def de_dict(cls, dados: dict[str, Any]) -> "Caixinha":
        """Fábrica: escolhe a subclasse certa pelo campo ``tipo``."""
        subclasse = cls._registro.get(dados.get("tipo", ""))
        if subclasse is None:
            raise ErroDeNegocio(f"Tipo de caixinha desconhecido: {dados.get('tipo')!r}")
        aporte = dados.get("aporte_centavos")
        return subclasse(
            nome=dados["nome"],
            aporte=None if aporte is None else Dinheiro(aporte),
            icone=dados.get("icone", "📦"),
            id=dados["id"],
        )

    @classmethod
    def criar(cls, tipo: str, nome: str, aporte: Dinheiro | None = None, icone: str = "📦") -> "Caixinha":
        subclasse = cls._registro.get(tipo)
        if subclasse is None:
            raise ErroDeNegocio(f"Tipo de caixinha desconhecido: {tipo!r}")
        return subclasse(nome=nome, aporte=aporte, icone=icone)

    @classmethod
    def tipos_disponiveis(cls) -> dict[str, str]:
        return {t: c.nome_do_tipo for t, c in cls._registro.items()}

    def __repr__(self) -> str:
        return f"{type(self).__name__}(nome={self.nome!r}, aporte={self.aporte})"


class ContaFixa(Caixinha):
    tipo = "conta_fixa"
    nome_do_tipo = "Conta fixa"

    def acumula_entre_ciclos(self) -> bool:
        return False

    def dica(self, gasto: Dinheiro) -> str:
        if self.aporte is None:
            return "Sem valor previsto."
        if gasto >= self.aporte:
            return "Paga." if gasto == self.aporte else f"Veio {gasto - self.aporte} acima do previsto."
        return "Ainda não paga." if not gasto else f"Faltam {self.aporte - gasto}."


class Variavel(Caixinha):
    tipo = "variavel"
    nome_do_tipo = "Variável"

    def acumula_entre_ciclos(self) -> bool:
        return False

    def dica(self, gasto: Dinheiro) -> str:
        if self.aporte is None:
            return f"Sem aporte: {gasto} saiu direto do livre." if gasto else "Sem aporte definido."
        if self.estourou(gasto):
            return f"Estourou {gasto - self.aporte}."
        return f"Restam {self.disponivel(gasto)}."


class Reserva(Caixinha):
    tipo = "reserva"
    nome_do_tipo = "Reserva"

    def acumula_entre_ciclos(self) -> bool:
        return True

    def entra_no_ritmo(self) -> bool:
        return False  # guardar não é consumo

    def alocado_da_renda(self, gasto: Dinheiro) -> Dinheiro:
        """Na reserva, só o que foi GUARDADO sai da renda.

        Sacar da reserva é usar dinheiro de ciclos anteriores, não a renda deste.
        """
        return self.aporte or Dinheiro.zero()

    def dica(self, gasto: Dinheiro) -> str:
        if gasto:
            return f"Saque de {gasto} neste ciclo."
        return f"Guardando {self.aporte} por ciclo." if self.aporte else "Nada guardado neste ciclo."
