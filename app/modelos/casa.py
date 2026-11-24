"""A ``Casa``: o objeto principal, que reúne todos os outros (composição).

Estruturas de dados usadas aqui:

- **Tabela hash** (``dict``) para caixinhas e parcelamentos, indexados pelo
  id: achar uma caixinha é O(1), sem percorrer lista.
- **Lista ordenada por data** para gastos e entradas: a inserção usa busca
  binária para achar a posição, e a consulta "gastos do ciclo" usa duas
  buscas binárias (``estruturas/busca.py``).
- **Pilha** para o histórico de ações (botão Desfazer).
- **Heap / fila de prioridade** para os próximos vencimentos de parcelas.
- **Merge sort** para ordenar a lista de gastos na tela.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

from ..estruturas import FilaDePrioridade, Pilha, fatia_por_intervalo, inserir_ordenado, merge_sort
from .acoes import (
    Acao,
    AdicionarCaixinha,
    AdicionarEntrada,
    AdicionarGasto,
    AdicionarParcelamento,
    PagarParcela,
    RemoverCaixinha,
    RemoverEntrada,
    RemoverGasto,
)
from .caixinha import Caixinha
from .ciclo import CicloFinanceiro
from .dinheiro import Dinheiro
from .erros import ErroDeNegocio, NaoEncontrado
from .lancamento import Entrada, Gasto
from .parcelamento import Parcela, Parcelamento

MARGEM_DO_RITMO = 10
"""Pontos percentuais de tolerância. Gasto não é linear (mercado no início do
mês, contas no meio): sem margem, o aviso dispararia todo começo de ciclo."""

ORDENS_DE_GASTOS: dict[str, tuple[str, bool]] = {
    # nome na tela: (atributo, decrescente?)
    "recentes": ("data", True),
    "antigos": ("data", False),
    "maior_valor": ("valor", True),
    "menor_valor": ("valor", False),
    "descricao": ("descricao", False),
}


@dataclass(frozen=True)
class LinhaCaixinha:
    caixinha: Caixinha
    gasto: Dinheiro
    disponivel: Dinheiro
    percentual: int
    estourou: bool
    dica: str


@dataclass(frozen=True)
class Resumo:
    ciclo: CicloFinanceiro
    dia: int
    renda: Dinheiro
    extras: Dinheiro
    gasto_total: Dinheiro
    alocado: Dinheiro
    livre: Dinheiro
    excedente: Dinheiro
    livre_por_dia: Dinheiro
    gasto_sem_caixinha: Dinheiro
    linhas: list[LinhaCaixinha]
    previsto: Dinheiro
    gasto_no_previsto: Dinheiro
    pct_do_ciclo: int
    pct_gasto: int
    situacao: str
    """``"no_ritmo"``, ``"adiantado"`` ou ``"sobrando"``."""
    gasto_consumo: Dinheiro
    """Gasto fora das reservas (o que já saiu da renda)."""
    reservado: Dinheiro
    """Aporte das caixinhas de consumo que ainda não foi gasto."""
    guardado: Dinheiro
    """Aporte das reservas neste ciclo."""

    @property
    def entrou(self) -> Dinheiro:
        return self.renda + self.extras

    @property
    def estado(self) -> str:
        """Clima geral do ciclo: ``"ok"``, ``"atencao"`` ou ``"critico"``."""
        if self.excedente:
            return "critico"
        return "atencao" if self.situacao == "adiantado" else "ok"


class Casa:
    def __init__(self, nome: str = "Nossa casa", dia_inicio_ciclo: int = 1) -> None:
        self.nome = nome
        self.dia_inicio_ciclo = dia_inicio_ciclo
        self._caixinhas: dict[str, Caixinha] = {}
        self._parcelamentos: dict[str, Parcelamento] = {}
        self._gastos: list[Gasto] = []  # sempre ordenada por data
        self._entradas: list[Entrada] = []  # sempre ordenada por data
        self._historico: Pilha[Acao] = Pilha()

    # ======================================================================
    # Configuração
    # ======================================================================

    @property
    def dia_inicio_ciclo(self) -> int:
        return self._dia_inicio_ciclo

    @dia_inicio_ciclo.setter
    def dia_inicio_ciclo(self, dia: int) -> None:
        if not 1 <= int(dia) <= 31:
            raise ErroDeNegocio("O dia de início do ciclo vai de 1 a 31.")
        self._dia_inicio_ciclo = int(dia)

    def ciclo_da_data(self, d: date) -> CicloFinanceiro:
        return CicloFinanceiro.da_data(d, self.dia_inicio_ciclo)

    # ======================================================================
    # Operações públicas (todas passam pela pilha de desfazer)
    # ======================================================================

    def executar(self, acao: Acao) -> Acao:
        acao.executar(self)
        self._historico.empilhar(acao)
        return acao

    def desfazer(self) -> Acao | None:
        """Desfaz a última ação. Devolve a ação desfeita (ou ``None``)."""
        if self._historico.esta_vazia():
            return None
        acao = self._historico.desempilhar()
        acao.desfazer(self)
        return acao

    @property
    def pode_desfazer(self) -> bool:
        return not self._historico.esta_vazia()

    @property
    def ultima_acao(self) -> Acao | None:
        return None if self._historico.esta_vazia() else self._historico.topo()

    def limpar_historico(self) -> None:
        self._historico = Pilha()

    def criar_caixinha(self, tipo: str, nome: str, aporte: Dinheiro | None = None, icone: str = "📦") -> Caixinha:
        caixinha = Caixinha.criar(tipo, nome, aporte, icone)
        self.executar(AdicionarCaixinha(caixinha))
        return caixinha

    def remover_caixinha(self, caixinha_id: str) -> None:
        self.caixinha(caixinha_id)  # valida que existe
        if any(g.caixinha_id == caixinha_id for g in self._gastos):
            raise ErroDeNegocio("Esta caixinha tem gastos lançados. Exclua os gastos antes.")
        self.executar(RemoverCaixinha(caixinha_id))

    def lancar_gasto(self, descricao: str, valor: Dinheiro, data: date, caixinha_id: str | None = None) -> Gasto:
        if caixinha_id:
            self.caixinha(caixinha_id)  # valida que existe
        gasto = Gasto(descricao, valor, data, caixinha_id or None)
        self.executar(AdicionarGasto(gasto))
        return gasto

    def remover_gasto(self, gasto_id: str) -> None:
        self.executar(RemoverGasto(gasto_id))

    def lancar_entrada(self, descricao: str, valor: Dinheiro, data: date, natureza: str = "renda") -> Entrada:
        entrada = Entrada(descricao, valor, data, natureza)
        self.executar(AdicionarEntrada(entrada))
        return entrada

    def remover_entrada(self, entrada_id: str) -> None:
        self.executar(RemoverEntrada(entrada_id))

    def criar_parcelamento(
        self, descricao: str, valor_total: Dinheiro, total_parcelas: int, primeiro_vencimento: date
    ) -> Parcelamento:
        p = Parcelamento(descricao, valor_total, total_parcelas, primeiro_vencimento)
        self.executar(AdicionarParcelamento(p))
        return p

    def pagar_parcela(self, parcelamento_id: str, numero: int, em: date) -> None:
        self.executar(PagarParcela(parcelamento_id, numero, em))

    # ======================================================================
    # Operações internas (usadas pelas ações; não registram histórico)
    # ======================================================================

    def _inserir_caixinha(self, c: Caixinha) -> None:
        self._caixinhas[c.id] = c

    def _retirar_caixinha(self, caixinha_id: str) -> Caixinha:
        if caixinha_id not in self._caixinhas:
            raise NaoEncontrado("Caixinha não encontrada.")
        return self._caixinhas.pop(caixinha_id)

    def _inserir_gasto(self, g: Gasto) -> None:
        inserir_ordenado(self._gastos, g, chave=lambda x: x.data)

    def _retirar_gasto(self, gasto_id: str) -> Gasto:
        for i, g in enumerate(self._gastos):
            if g.id == gasto_id:
                return self._gastos.pop(i)
        raise NaoEncontrado("Gasto não encontrado.")

    def _inserir_entrada(self, e: Entrada) -> None:
        inserir_ordenado(self._entradas, e, chave=lambda x: x.data)

    def _retirar_entrada(self, entrada_id: str) -> Entrada:
        for i, e in enumerate(self._entradas):
            if e.id == entrada_id:
                return self._entradas.pop(i)
        raise NaoEncontrado("Entrada não encontrada.")

    def _inserir_parcelamento(self, p: Parcelamento) -> None:
        self._parcelamentos[p.id] = p

    def _retirar_parcelamento(self, parcelamento_id: str) -> Parcelamento:
        if parcelamento_id not in self._parcelamentos:
            raise NaoEncontrado("Parcelamento não encontrado.")
        return self._parcelamentos.pop(parcelamento_id)

    # ======================================================================
    # Consultas
    # ======================================================================

    def caixinha(self, caixinha_id: str) -> Caixinha:
        try:
            return self._caixinhas[caixinha_id]  # tabela hash: O(1)
        except KeyError:
            raise NaoEncontrado("Caixinha não encontrada.") from None

    def buscar_caixinha(self, caixinha_id: str | None) -> Caixinha | None:
        """Como ``caixinha()``, mas devolve ``None`` em vez de lançar erro."""
        return self._caixinhas.get(caixinha_id) if caixinha_id else None

    def parcelamento(self, parcelamento_id: str) -> Parcelamento:
        try:
            return self._parcelamentos[parcelamento_id]
        except KeyError:
            raise NaoEncontrado("Parcelamento não encontrado.") from None

    @property
    def caixinhas(self) -> list[Caixinha]:
        return list(self._caixinhas.values())

    @property
    def parcelamentos(self) -> list[Parcelamento]:
        return list(self._parcelamentos.values())

    def gastos_do_ciclo(self, ciclo: CicloFinanceiro, ordem: str = "recentes") -> list[Gasto]:
        """Gastos do ciclo: busca binária para recortar + merge sort para ordenar."""
        do_ciclo = fatia_por_intervalo(self._gastos, ciclo.inicio, ciclo.fim, chave=lambda g: g.data)
        atributo, decrescente = ORDENS_DE_GASTOS.get(ordem, ORDENS_DE_GASTOS["recentes"])
        if atributo == "descricao":
            return merge_sort(do_ciclo, chave=lambda g: g.descricao.casefold())
        return merge_sort(do_ciclo, chave=lambda g: getattr(g, atributo), decrescente=decrescente)

    def entradas_do_ciclo(self, ciclo: CicloFinanceiro) -> list[Entrada]:
        return fatia_por_intervalo(self._entradas, ciclo.inicio, ciclo.fim, chave=lambda e: e.data)

    def gasto_por_caixinha(self, ciclo: CicloFinanceiro) -> dict[str | None, Dinheiro]:
        """Soma dos gastos do ciclo agrupada por caixinha (``None`` = sem caixinha)."""
        totais: dict[str | None, Dinheiro] = {}
        for g in self.gastos_do_ciclo(ciclo, "antigos"):
            totais[g.caixinha_id] = totais.get(g.caixinha_id, Dinheiro.zero()) + g.valor
        return totais

    def proximos_vencimentos(self, quantidade: int = 5) -> list[Parcela]:
        """As ``quantidade`` parcelas em aberto que vencem primeiro (heap)."""
        fila: FilaDePrioridade[Parcela] = FilaDePrioridade(chave=lambda p: p.vencimento)
        for p in self._parcelamentos.values():
            for parcela in p.parcelas_em_aberto():
                fila.inserir(parcela)
        resultado = []
        while not fila.esta_vazia() and len(resultado) < quantidade:
            resultado.append(fila.remover_minimo())
        return resultado

    def resumo(self, hoje: date, ciclo: CicloFinanceiro | None = None) -> Resumo:
        """Tudo que a tela inicial mostra sobre um ciclo."""
        ciclo = ciclo or self.ciclo_da_data(hoje)
        entradas = self.entradas_do_ciclo(ciclo)
        renda = sum((e.valor for e in entradas if e.natureza == "renda"), Dinheiro.zero())
        extras = sum((e.valor for e in entradas if e.natureza == "extra"), Dinheiro.zero())

        gastos = self.gasto_por_caixinha(ciclo)
        sem_caixinha = gastos.get(None, Dinheiro.zero())

        linhas: list[LinhaCaixinha] = []
        alocado = sem_caixinha  # gasto sem caixinha sai direto do livre
        previsto = gasto_no_previsto = Dinheiro.zero()
        gasto_consumo, reservado, guardado = sem_caixinha, Dinheiro.zero(), Dinheiro.zero()
        for c in self.caixinhas:
            gasto = gastos.get(c.id, Dinheiro.zero())
            alocado += c.alocado_da_renda(gasto)  # polimorfismo: cada tipo calcula do seu jeito
            if c.acumula_entre_ciclos():
                guardado += c.aporte or Dinheiro.zero()
            else:
                gasto_consumo += gasto
                reservado += c.disponivel(gasto).positivo_ou_zero()
            if c.entra_no_ritmo() and c.aporte is not None:
                previsto += c.aporte
                gasto_no_previsto += gasto
            linhas.append(
                LinhaCaixinha(
                    caixinha=c,
                    gasto=gasto,
                    disponivel=c.disponivel(gasto),
                    percentual=c.percentual_usado(gasto),
                    estourou=c.estourou(gasto),
                    dica=c.dica(gasto),
                )
            )

        entrou = renda + extras
        livre = (entrou - alocado).positivo_ou_zero()
        excedente = (alocado - entrou).positivo_ou_zero()
        restantes = ciclo.dias_restantes(hoje)
        livre_por_dia = Dinheiro(livre.centavos // restantes) if restantes else Dinheiro.zero()

        dia = ciclo.dia_atual(hoje)
        pct_ciclo = round(dia * 100 / ciclo.total_dias)
        pct_gasto = round(gasto_no_previsto.centavos * 100 / previsto.centavos) if previsto else 0
        if pct_gasto > pct_ciclo + MARGEM_DO_RITMO:
            situacao = "adiantado"
        elif pct_gasto < pct_ciclo - MARGEM_DO_RITMO:
            situacao = "sobrando"
        else:
            situacao = "no_ritmo"

        return Resumo(
            ciclo=ciclo,
            dia=dia,
            renda=renda,
            extras=extras,
            gasto_total=sum(gastos.values(), Dinheiro.zero()),
            alocado=alocado,
            livre=livre,
            excedente=excedente,
            livre_por_dia=livre_por_dia,
            gasto_sem_caixinha=sem_caixinha,
            linhas=linhas,
            previsto=previsto,
            gasto_no_previsto=gasto_no_previsto,
            pct_do_ciclo=pct_ciclo,
            pct_gasto=pct_gasto,
            situacao=situacao,
            gasto_consumo=gasto_consumo,
            reservado=reservado,
            guardado=guardado,
        )

    # ======================================================================
    # Persistência
    # ======================================================================

    def para_dict(self) -> dict[str, Any]:
        return {
            "versao": 1,
            "nome": self.nome,
            "dia_inicio_ciclo": self.dia_inicio_ciclo,
            "caixinhas": [c.para_dict() for c in self._caixinhas.values()],
            "gastos": [g.para_dict() for g in self._gastos],
            "entradas": [e.para_dict() for e in self._entradas],
            "parcelamentos": [p.para_dict() for p in self._parcelamentos.values()],
        }

    @classmethod
    def de_dict(cls, dados: dict[str, Any]) -> "Casa":
        casa = cls(dados.get("nome", "Nossa casa"), dados.get("dia_inicio_ciclo", 1))
        for c in dados.get("caixinhas", []):
            casa._inserir_caixinha(Caixinha.de_dict(c))
        for g in dados.get("gastos", []):
            casa._inserir_gasto(Gasto.de_dict(g))
        for e in dados.get("entradas", []):
            casa._inserir_entrada(Entrada.de_dict(e))
        for p in dados.get("parcelamentos", []):
            casa._inserir_parcelamento(Parcelamento.de_dict(p))
        return casa
