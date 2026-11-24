"""API JSON (documentação automática em /docs)."""

from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .estado import Estado
from .modelos import Dinheiro, ErroDeNegocio, NaoEncontrado
from .modelos.casa import ORDENS_DE_GASTOS


class NovoGasto(BaseModel):
    descricao: str = Field(min_length=1, examples=["Mercado"])
    valor: Decimal = Field(gt=0, description="Em reais", examples=[45.90])
    data: date
    caixinha_id: str | None = None


def _dinheiro(d: Dinheiro) -> dict[str, Any]:
    return {"centavos": d.centavos, "formatado": str(d)}


def _erro(e: ErroDeNegocio) -> HTTPException:
    return HTTPException(status_code=404 if isinstance(e, NaoEncontrado) else 422, detail=str(e))


def criar_rotas_api(estado: Estado) -> APIRouter:
    api = APIRouter(prefix="/api", tags=["API"])

    @api.get("/resumo")
    def resumo(ciclo: str | None = None) -> dict[str, Any]:
        r = estado.casa.resumo(estado.hoje(), estado.ciclo(ciclo))
        return {
            "ciclo": {"inicio": r.ciclo.inicio, "fim": r.ciclo.fim, "rotulo": r.ciclo.rotulo, "dia": r.dia},
            "entrou": _dinheiro(r.entrou),
            "gasto_total": _dinheiro(r.gasto_total),
            "alocado": _dinheiro(r.alocado),
            "livre": _dinheiro(r.livre),
            "livre_por_dia": _dinheiro(r.livre_por_dia),
            "excedente": _dinheiro(r.excedente),
            "ritmo": {"pct_do_ciclo": r.pct_do_ciclo, "pct_gasto": r.pct_gasto, "situacao": r.situacao},
            "caixinhas": [
                {
                    "id": l.caixinha.id,
                    "nome": l.caixinha.nome,
                    "tipo": l.caixinha.tipo,
                    "gasto": _dinheiro(l.gasto),
                    "disponivel": _dinheiro(l.disponivel),
                    "dica": l.dica,
                }
                for l in r.linhas
            ],
        }

    @api.get("/caixinhas")
    def caixinhas() -> list[dict[str, Any]]:
        return [c.para_dict() for c in estado.casa.caixinhas]

    @api.get("/gastos")
    def gastos(ciclo: str | None = None, ordem: str = "recentes") -> list[dict[str, Any]]:
        if ordem not in ORDENS_DE_GASTOS:
            raise HTTPException(422, f"ordem deve ser uma de: {', '.join(ORDENS_DE_GASTOS)}")
        return [g.para_dict() for g in estado.casa.gastos_do_ciclo(estado.ciclo(ciclo), ordem)]

    @api.post("/gastos", status_code=201)
    def lancar_gasto(novo: NovoGasto) -> dict[str, Any]:
        try:
            g = estado.alterar(
                lambda casa: casa.lancar_gasto(
                    novo.descricao, Dinheiro.de_reais(novo.valor), novo.data, novo.caixinha_id
                )
            )
        except ErroDeNegocio as e:
            raise _erro(e) from e
        return g.para_dict()

    @api.delete("/gastos/{gasto_id}", status_code=204)
    def excluir_gasto(gasto_id: str) -> None:
        try:
            estado.alterar(lambda casa: casa.remover_gasto(gasto_id))
        except ErroDeNegocio as e:
            raise _erro(e) from e

    @api.get("/parcelamentos")
    def parcelamentos() -> list[dict[str, Any]]:
        hoje = estado.hoje()
        return [
            {
                **p.para_dict(),
                "falta_pagar": _dinheiro(p.falta_pagar),
                "quitado": p.quitado,
                "atrasado": p.esta_atrasado(hoje),
            }
            for p in estado.casa.parcelamentos
        ]

    @api.post("/desfazer")
    def desfazer() -> dict[str, Any]:
        acao = estado.alterar(lambda casa: casa.desfazer())
        return {"desfeito": acao.descricao if acao else None}

    return api
