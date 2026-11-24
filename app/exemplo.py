"""Dados de exemplo para demonstrar o sistema.

Uso:  python -m app.exemplo          (grava em dados/casa.json)
"""

import sys
from datetime import date, timedelta

from .config import CAMINHO_DOS_DADOS
from .modelos import Casa, Dinheiro
from .repositorio import RepositorioJson


def criar_casa_exemplo(hoje: date | None = None) -> Casa:
    hoje = hoje or date.today()
    casa = Casa("Nossa casa", dia_inicio_ciclo=1)
    ciclo = casa.ciclo_da_data(hoje)
    inicio = ciclo.inicio

    def dia(n: int) -> date:
        """n-ésimo dia do ciclo, sem passar de hoje."""
        return min(inicio + timedelta(days=n - 1), hoje)

    r = Dinheiro.de_reais
    aluguel = casa.criar_caixinha("conta_fixa", "Aluguel", r(1800), "🏠")
    internet = casa.criar_caixinha("conta_fixa", "Internet", r(120), "📶")
    luz = casa.criar_caixinha("conta_fixa", "Luz", r(180), "💡")
    mercado = casa.criar_caixinha("variavel", "Mercado", r(1200), "🛒")
    lazer = casa.criar_caixinha("variavel", "Lazer", None, "🎉")
    casa.criar_caixinha("reserva", "Reserva de emergência", r(400), "🛟")

    casa.lancar_entrada("Salário Ana", r(3200), dia(1))
    casa.lancar_entrada("Salário Bruno", r(2600), dia(1))
    casa.lancar_entrada("Freela de design", r(450), dia(9), natureza="extra")

    casa.lancar_gasto("Aluguel do mês", r(1800), dia(5), aluguel.id)
    casa.lancar_gasto("Internet fibra", r(119.90), dia(10), internet.id)
    casa.lancar_gasto("Conta de luz", r(203.47), dia(12), luz.id)
    casa.lancar_gasto("Compra do mês", r(486.32), dia(2), mercado.id)
    casa.lancar_gasto("Feira", r(74.50), dia(8), mercado.id)
    casa.lancar_gasto("Padaria", r(23.80), dia(14), mercado.id)
    casa.lancar_gasto("Pizza de sexta", r(89.90), dia(6), lazer.id)
    casa.lancar_gasto("Cinema", r(64.00), dia(13), lazer.id)
    casa.lancar_gasto("Farmácia", r(42.35), dia(11))

    geladeira = casa.criar_parcelamento("Geladeira", r(3500), 10, inicio.replace(day=10) - timedelta(days=62))
    geladeira.pagar(1, geladeira.vencimento(1))
    geladeira.pagar(2, geladeira.vencimento(2))
    casa.criar_parcelamento("Notebook", r(4299.90), 12, inicio + timedelta(days=19))

    casa.limpar_historico()  # o exemplo começa sem nada para desfazer
    return casa


def main() -> None:
    destino = RepositorioJson(CAMINHO_DOS_DADOS)
    if destino.caminho.exists() and "--forcar" not in sys.argv:
        print(f"{destino.caminho} já existe. Use --forcar para sobrescrever.")
        return
    destino.salvar(criar_casa_exemplo())
    print(f"Dados de exemplo gravados em {destino.caminho}")


if __name__ == "__main__":
    main()
