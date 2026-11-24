"""Ações que podem ser desfeitas (padrão de projeto *Command*).

Cada operação que muda os dados vira um objeto com dois métodos:
``executar`` e ``desfazer``. A ``Casa`` guarda as ações executadas numa
**pilha**; o botão "Desfazer" desempilha a última e chama ``desfazer()``.

Graças ao polimorfismo, a ``Casa`` não precisa saber QUAL ação está
desfazendo — cada classe sabe se reverter.
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import TYPE_CHECKING

from .caixinha import Caixinha
from .lancamento import Entrada, Gasto
from .parcelamento import Parcelamento

if TYPE_CHECKING:
    from .casa import Casa


class Acao(ABC):
    @abstractmethod
    def executar(self, casa: "Casa") -> None: ...

    @abstractmethod
    def desfazer(self, casa: "Casa") -> None: ...

    @property
    @abstractmethod
    def descricao(self) -> str:
        """Texto curto para a mensagem "Desfeito: ..."."""


class AdicionarGasto(Acao):
    def __init__(self, gasto: Gasto) -> None:
        self.gasto = gasto

    def executar(self, casa: "Casa") -> None:
        casa._inserir_gasto(self.gasto)

    def desfazer(self, casa: "Casa") -> None:
        casa._retirar_gasto(self.gasto.id)

    @property
    def descricao(self) -> str:
        return f"gasto “{self.gasto.descricao}” ({self.gasto.valor})"


class RemoverGasto(Acao):
    def __init__(self, gasto_id: str) -> None:
        self.gasto_id = gasto_id
        self.gasto: Gasto | None = None

    def executar(self, casa: "Casa") -> None:
        self.gasto = casa._retirar_gasto(self.gasto_id)

    def desfazer(self, casa: "Casa") -> None:
        assert self.gasto is not None
        casa._inserir_gasto(self.gasto)

    @property
    def descricao(self) -> str:
        return f"exclusão do gasto “{self.gasto.descricao if self.gasto else self.gasto_id}”"


class AdicionarEntrada(Acao):
    def __init__(self, entrada: Entrada) -> None:
        self.entrada = entrada

    def executar(self, casa: "Casa") -> None:
        casa._inserir_entrada(self.entrada)

    def desfazer(self, casa: "Casa") -> None:
        casa._retirar_entrada(self.entrada.id)

    @property
    def descricao(self) -> str:
        return f"entrada “{self.entrada.descricao}” ({self.entrada.valor})"


class RemoverEntrada(Acao):
    def __init__(self, entrada_id: str) -> None:
        self.entrada_id = entrada_id
        self.entrada: Entrada | None = None

    def executar(self, casa: "Casa") -> None:
        self.entrada = casa._retirar_entrada(self.entrada_id)

    def desfazer(self, casa: "Casa") -> None:
        assert self.entrada is not None
        casa._inserir_entrada(self.entrada)

    @property
    def descricao(self) -> str:
        return f"exclusão da entrada “{self.entrada.descricao if self.entrada else self.entrada_id}”"


class AdicionarCaixinha(Acao):
    def __init__(self, caixinha: Caixinha) -> None:
        self.caixinha = caixinha

    def executar(self, casa: "Casa") -> None:
        casa._inserir_caixinha(self.caixinha)

    def desfazer(self, casa: "Casa") -> None:
        casa._retirar_caixinha(self.caixinha.id)

    @property
    def descricao(self) -> str:
        return f"caixinha “{self.caixinha.nome}”"


class RemoverCaixinha(Acao):
    def __init__(self, caixinha_id: str) -> None:
        self.caixinha_id = caixinha_id
        self.caixinha: Caixinha | None = None

    def executar(self, casa: "Casa") -> None:
        self.caixinha = casa._retirar_caixinha(self.caixinha_id)

    def desfazer(self, casa: "Casa") -> None:
        assert self.caixinha is not None
        casa._inserir_caixinha(self.caixinha)

    @property
    def descricao(self) -> str:
        return f"exclusão da caixinha “{self.caixinha.nome if self.caixinha else self.caixinha_id}”"


class AdicionarParcelamento(Acao):
    def __init__(self, parcelamento: Parcelamento) -> None:
        self.parcelamento = parcelamento

    def executar(self, casa: "Casa") -> None:
        casa._inserir_parcelamento(self.parcelamento)

    def desfazer(self, casa: "Casa") -> None:
        casa._retirar_parcelamento(self.parcelamento.id)

    @property
    def descricao(self) -> str:
        return f"parcelamento “{self.parcelamento.descricao}”"


class PagarParcela(Acao):
    def __init__(self, parcelamento_id: str, numero: int, em: date) -> None:
        self.parcelamento_id = parcelamento_id
        self.numero = numero
        self.em = em
        self._nome = ""

    def executar(self, casa: "Casa") -> None:
        p = casa.parcelamento(self.parcelamento_id)
        p.pagar(self.numero, self.em)
        self._nome = p.descricao

    def desfazer(self, casa: "Casa") -> None:
        casa.parcelamento(self.parcelamento_id).estornar(self.numero)

    @property
    def descricao(self) -> str:
        return f"pagamento da parcela {self.numero} de “{self._nome}”"
