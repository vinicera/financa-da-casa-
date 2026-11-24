"""Parcelamento: uma compra dividida em N parcelas mensais.

O cronograma (valor e vencimento de cada parcela) é **calculado** a partir do
contrato — não é guardado. O que se guarda é só quais parcelas foram pagas,
num dicionário ``{número da parcela: data do pagamento}``.
"""

import calendar
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any

from .dinheiro import Dinheiro
from .erros import ErroDeNegocio


def _somar_meses(d: date, meses: int) -> date:
    """31/01 + 1 mês = 28/02 (último dia do mês quando o dia não existe)."""
    total = d.year * 12 + (d.month - 1) + meses
    ano, mes = total // 12, total % 12 + 1
    return date(ano, mes, min(d.day, calendar.monthrange(ano, mes)[1]))


@dataclass(frozen=True)
class Parcela:
    """Uma linha do cronograma (objeto de valor, somente leitura)."""

    parcelamento_id: str
    descricao: str
    numero: int
    total: int
    valor: Dinheiro
    vencimento: date
    pago_em: date | None

    def status(self, hoje: date) -> str:
        if self.pago_em is not None:
            return "paga"
        return "atrasada" if self.vencimento < hoje else "pendente"


class Parcelamento:
    def __init__(
        self,
        descricao: str,
        valor_total: Dinheiro,
        total_parcelas: int,
        primeiro_vencimento: date,
        pagamentos: dict[int, date] | None = None,
        id: str | None = None,
    ) -> None:
        descricao = (descricao or "").strip()
        if not descricao:
            raise ErroDeNegocio("Informe uma descrição.")
        if not valor_total.eh_positivo():
            raise ErroDeNegocio("O valor total precisa ser maior que zero.")
        if not 1 <= total_parcelas <= 420:
            raise ErroDeNegocio("O número de parcelas vai de 1 a 420.")
        self.id = id or uuid.uuid4().hex[:8]
        self.descricao = descricao
        self.valor_total = valor_total
        self.total_parcelas = total_parcelas
        self.primeiro_vencimento = primeiro_vencimento
        self._pagamentos: dict[int, date] = dict(pagamentos or {})

    # -- cronograma -----------------------------------------------------------

    def valor_da_parcela(self, n: int) -> Dinheiro:
        """A última parcela absorve a sobra do arredondamento."""
        self._validar_numero(n)
        return self.valor_total.dividir_em(self.total_parcelas)[n - 1]

    def vencimento(self, n: int) -> date:
        self._validar_numero(n)
        return _somar_meses(self.primeiro_vencimento, n - 1)

    def parcela(self, n: int) -> Parcela:
        return Parcela(
            parcelamento_id=self.id,
            descricao=self.descricao,
            numero=n,
            total=self.total_parcelas,
            valor=self.valor_da_parcela(n),
            vencimento=self.vencimento(n),
            pago_em=self._pagamentos.get(n),
        )

    def cronograma(self) -> list[Parcela]:
        return [self.parcela(n) for n in range(1, self.total_parcelas + 1)]

    def parcelas_em_aberto(self) -> list[Parcela]:
        return [p for p in self.cronograma() if p.pago_em is None]

    # -- pagamentos -----------------------------------------------------------

    def pagar(self, n: int, em: date) -> None:
        self._validar_numero(n)
        if n in self._pagamentos:
            raise ErroDeNegocio(f"A parcela {n} já está paga.")
        self._pagamentos[n] = em

    def estornar(self, n: int) -> None:
        if self._pagamentos.pop(n, None) is None:
            raise ErroDeNegocio(f"A parcela {n} não está paga.")

    def proxima_em_aberto(self) -> int | None:
        for n in range(1, self.total_parcelas + 1):
            if n not in self._pagamentos:
                return n
        return None

    @property
    def parcelas_pagas(self) -> int:
        return len(self._pagamentos)

    @property
    def quitado(self) -> bool:
        return self.parcelas_pagas >= self.total_parcelas

    @property
    def total_pago(self) -> Dinheiro:
        return sum((self.valor_da_parcela(n) for n in self._pagamentos), Dinheiro.zero())

    @property
    def falta_pagar(self) -> Dinheiro:
        return self.valor_total - self.total_pago

    def esta_atrasado(self, hoje: date) -> bool:
        return any(p.status(hoje) == "atrasada" for p in self.cronograma())

    def _validar_numero(self, n: int) -> None:
        if not 1 <= n <= self.total_parcelas:
            raise ErroDeNegocio(f"Parcela {n} não existe (vai de 1 a {self.total_parcelas}).")

    # -- persistência ---------------------------------------------------------

    def para_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "descricao": self.descricao,
            "valor_total_centavos": self.valor_total.centavos,
            "total_parcelas": self.total_parcelas,
            "primeiro_vencimento": self.primeiro_vencimento.isoformat(),
            "pagamentos": {str(n): d.isoformat() for n, d in sorted(self._pagamentos.items())},
        }

    @classmethod
    def de_dict(cls, d: dict[str, Any]) -> "Parcelamento":
        return cls(
            descricao=d["descricao"],
            valor_total=Dinheiro(d["valor_total_centavos"]),
            total_parcelas=d["total_parcelas"],
            primeiro_vencimento=date.fromisoformat(d["primeiro_vencimento"]),
            pagamentos={int(n): date.fromisoformat(v) for n, v in d.get("pagamentos", {}).items()},
            id=d["id"],
        )
