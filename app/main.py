"""Ponto de entrada do servidor web.

Rodar:  uvicorn app.main:app --reload
"""

from collections.abc import Callable
from datetime import date
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api import criar_rotas_api
from .config import CAMINHO_DOS_DADOS
from .estado import Estado
from .paginas import criar_rotas_paginas
from .repositorio import Repositorio, RepositorioJson


def criar_app(repositorio: Repositorio | None = None, hoje: Callable[[], date] = date.today) -> FastAPI:
    """Monta a aplicação. Os testes passam um repositório em memória e um "hoje" fixo."""
    estado = Estado(repositorio or RepositorioJson(CAMINHO_DOS_DADOS), hoje)
    app = FastAPI(
        title="Finança da Casa",
        description="Controle financeiro para casas compartilhadas: caixinhas, gastos, entradas e parcelas.",
        version="1.0.0",
    )
    app.state.estado = estado
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
    app.include_router(criar_rotas_api(estado))
    app.include_router(criar_rotas_paginas(estado))
    return app


app = criar_app()
