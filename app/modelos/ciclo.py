"""Ciclo financeiro: o "mês" do dinheiro da casa.

Quem recebe no dia 20 vive do dia 20 ao dia 19 do mês seguinte. O usuário
escolhe o dia de início e todo o sistema trabalha dentro desse ciclo. Com
início no dia 1, o ciclo é o próprio mês do calendário.

Os ciclos são contíguos: cada um termina no dia anterior ao início do
próximo, então nenhum dia fica sem ciclo.
"""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta

MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def _ultimo_dia(ano: int, mes: int) -> int:
    return calendar.monthrange(ano, mes)[1]


def _inicio_no_mes(ano: int, mes: int, dia_inicio: int) -> date:
    """Dia 31 em fevereiro vira 28 (ou 29)."""
    return date(ano, mes, min(dia_inicio, _ultimo_dia(ano, mes)))


def _somar_mes(ano: int, mes: int, delta: int) -> tuple[int, int]:
    total = ano * 12 + (mes - 1) + delta
    return total // 12, total % 12 + 1


@dataclass(frozen=True)
class CicloFinanceiro:
    inicio: date
    fim: date
    dia_inicio: int = 1

    @classmethod
    def da_data(cls, d: date, dia_inicio: int = 1) -> "CicloFinanceiro":
        """O ciclo que contém a data ``d``."""
        if not 1 <= dia_inicio <= 31:
            raise ValueError("O dia de início do ciclo vai de 1 a 31.")
        inicio = _inicio_no_mes(d.year, d.month, dia_inicio)
        if d < inicio:  # ainda não chegou o dia: o ciclo começou no mês anterior
            ano, mes = _somar_mes(d.year, d.month, -1)
            inicio = _inicio_no_mes(ano, mes, dia_inicio)
        ano, mes = _somar_mes(inicio.year, inicio.month, 1)
        fim = _inicio_no_mes(ano, mes, dia_inicio) - timedelta(days=1)
        return cls(inicio, fim, dia_inicio)

    def anterior(self) -> "CicloFinanceiro":
        return CicloFinanceiro.da_data(self.inicio - timedelta(days=1), self.dia_inicio)

    def proximo(self) -> "CicloFinanceiro":
        return CicloFinanceiro.da_data(self.fim + timedelta(days=1), self.dia_inicio)

    def contem(self, d: date) -> bool:
        return self.inicio <= d <= self.fim

    @property
    def total_dias(self) -> int:
        return (self.fim - self.inicio).days + 1

    def dia_atual(self, hoje: date) -> int:
        """Em que dia (1..total) do ciclo estamos. Passado -> total; futuro -> 0."""
        if hoje < self.inicio:
            return 0
        if hoje > self.fim:
            return self.total_dias
        return (hoje - self.inicio).days + 1

    def dias_restantes(self, hoje: date) -> int:
        """Dias que faltam contando hoje (mínimo 1 se o ciclo é o atual)."""
        if hoje > self.fim:
            return 0
        if hoje < self.inicio:
            return self.total_dias
        return (self.fim - hoje).days + 1

    @property
    def rotulo(self) -> str:
        """``"Nov 2026"`` ou ``"Nov/Dez 2026"``."""
        i, f = self.inicio, self.fim
        if (i.month, i.year) == (f.month, f.year):
            return f"{MESES[i.month - 1]} {i.year}"
        if i.year == f.year:
            return f"{MESES[i.month - 1]}/{MESES[f.month - 1]} {i.year}"
        return f"{MESES[i.month - 1]} {i.year}/{MESES[f.month - 1]} {f.year}"

    @property
    def intervalo(self) -> str:
        """``"20/10 a 19/11"``."""
        return f"{self.inicio:%d/%m} a {self.fim:%d/%m}"
