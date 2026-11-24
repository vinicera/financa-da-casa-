"""Configurações lidas do ambiente."""

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CAMINHO_DOS_DADOS = Path(os.environ.get("FINANCA_DADOS", RAIZ / "dados" / "casa.json"))
