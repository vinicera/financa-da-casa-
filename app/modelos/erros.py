"""Exceções do sistema (hierarquia de classes de erro)."""


class ErroDeNegocio(Exception):
    """Uma regra do sistema foi violada (ex.: valor negativo)."""


class NaoEncontrado(ErroDeNegocio):
    """O item pedido não existe."""
