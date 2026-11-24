"""Classe ``Dinheiro``: um valor monetário guardado em centavos inteiros.

Por que não usar ``float``? Porque ``0.1 + 0.2 == 0.30000000000000004``.
Em dinheiro, um centavo perdido no meio de uma soma vira uma diferença que
ninguém consegue explicar no fim do mês. Guardando centavos como ``int`` a
conta é sempre exata.

A classe é **imutável** (``frozen``): toda operação devolve um novo objeto.
Os operadores ``+``, ``-``, ``*``, ``<`` e ``str()`` são sobrecarregados para
o objeto se comportar como um número.
"""

from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal, InvalidOperation

from .erros import ErroDeNegocio


@dataclass(frozen=True, order=True, slots=True)
class Dinheiro:
    centavos: int = 0

    def __post_init__(self) -> None:
        if isinstance(self.centavos, bool) or not isinstance(self.centavos, int):
            raise TypeError("Dinheiro guarda centavos como int.")

    # -- construtores alternativos (métodos de classe) -----------------------

    @classmethod
    def zero(cls) -> "Dinheiro":
        return cls(0)

    @classmethod
    def de_reais(cls, reais: float | int | str | Decimal) -> "Dinheiro":
        """``Dinheiro.de_reais(45.9)`` -> 4590 centavos (nunca 4589)."""
        try:
            d = Decimal(str(reais).strip())
        except InvalidOperation as exc:
            raise ErroDeNegocio(f"Valor inválido: {reais!r}") from exc
        if not d.is_finite():
            raise ErroDeNegocio(f"Valor inválido: {reais!r}")
        # Arredonda meio centavo para cima (Decimal evita o erro do float).
        return cls(int((d * 100 + Decimal("0.5")).to_integral_value(rounding=ROUND_FLOOR)))

    @classmethod
    def de_texto(cls, texto: str) -> "Dinheiro":
        """Lê o que o usuário digitou: ``"45,90"``, ``"1.234,56"``, ``"R$ 10"``."""
        limpo = (texto or "").replace("R$", "").replace(" ", "").replace("\xa0", "")
        if not limpo:
            raise ErroDeNegocio("Informe um valor.")
        if "," in limpo:  # formato brasileiro: ponto = milhar, vírgula = decimal
            limpo = limpo.replace(".", "").replace(",", ".")
        return cls.de_reais(limpo)

    # -- sobrecarga de operadores ---------------------------------------------

    def __add__(self, outro: "Dinheiro") -> "Dinheiro":
        if not isinstance(outro, Dinheiro):
            return NotImplemented
        return Dinheiro(self.centavos + outro.centavos)

    def __radd__(self, outro: object) -> "Dinheiro":
        # Permite usar sum(lista_de_dinheiro), que começa somando 0 + item.
        if outro == 0:
            return self
        return NotImplemented

    def __sub__(self, outro: "Dinheiro") -> "Dinheiro":
        if not isinstance(outro, Dinheiro):
            return NotImplemented
        return Dinheiro(self.centavos - outro.centavos)

    def __neg__(self) -> "Dinheiro":
        return Dinheiro(-self.centavos)

    def __mul__(self, fator: int) -> "Dinheiro":
        if isinstance(fator, bool) or not isinstance(fator, int):
            return NotImplemented
        return Dinheiro(self.centavos * fator)

    __rmul__ = __mul__

    def __bool__(self) -> bool:
        return self.centavos != 0

    def __str__(self) -> str:
        """``"R$ 1.234,56"`` (negativo: ``"-R$ 1.234,56"``)."""
        sinal = "-" if self.centavos < 0 else ""
        reais, cent = divmod(abs(self.centavos), 100)
        return f"{sinal}R$ {reais:,}".replace(",", ".") + f",{cent:02d}"

    # -- consultas ------------------------------------------------------------

    @property
    def reais(self) -> float:
        """Valor em reais — só para exibição / JSON."""
        return self.centavos / 100

    def eh_positivo(self) -> bool:
        return self.centavos > 0

    def positivo_ou_zero(self) -> "Dinheiro":
        """``max(0, valor)``."""
        return self if self.centavos > 0 else Dinheiro.zero()

    def dividir_em(self, partes: int) -> list["Dinheiro"]:
        """Divide em partes iguais; a ÚLTIMA absorve a sobra do arredondamento.

        ``R$ 100,00`` em 3 -> 33,33 + 33,33 + 33,34 (a soma fecha exata).
        """
        if partes <= 0:
            return []
        base = self.centavos // partes
        valores = [base] * partes
        valores[-1] = self.centavos - base * (partes - 1)
        return [Dinheiro(v) for v in valores]
