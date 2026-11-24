"""Páginas HTML (formulários simples, sem JavaScript)."""

import math
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .estado import Estado
from .modelos import Caixinha, Casa, Dinheiro, Entrada, ErroDeNegocio, Resumo
from .modelos.casa import ORDENS_DE_GASTOS

PASTA_TEMPLATES = Path(__file__).parent / "templates"

NOMES_DAS_ORDENS = {
    "recentes": "Mais recentes",
    "antigos": "Mais antigos",
    "maior_valor": "Maior valor",
    "menor_valor": "Menor valor",
    "descricao": "Descrição (A-Z)",
}


COR_GASTO = "var(--gasto)"
COR_RESERVADO = "#8178e0"
COR_GUARDADO = "#ab8b22"
COR_LIVRE = "var(--primaria)"
RAIO_DO_ANEL = 100
VAO_ENTRE_FATIAS = 0.008  # fração da volta


def montar_anel(r: Resumo) -> dict[str, Any]:
    """Fatias do anel do dinheiro (SVG): gasto, reservado, guardado e livre."""
    fatias = [
        ("Já gasto", r.gasto_consumo, COR_GASTO),
        ("Nas caixinhas", r.reservado, COR_RESERVADO),
        ("Guardado", r.guardado, COR_GUARDADO),
        ("Livre", r.livre, COR_LIVRE),
    ]
    total = sum(v.centavos for _, v, _ in fatias if v.centavos > 0)
    visiveis = [f for f in fatias if f[1].centavos > 0]
    vao = VAO_ENTRE_FATIAS if len(visiveis) > 1 else 0
    circunferencia = 2 * math.pi * RAIO_DO_ANEL
    inicio = 0.0
    arcos = []
    for rotulo, valor, cor in visiveis:
        fracao = valor.centavos / total
        arcos.append(
            {
                "cor": cor,
                "traco": f"{circunferencia * max(0.0, fracao - vao):.2f} {circunferencia:.2f}",
                "giro": f"{-90 + (inicio + vao / 2) * 360:.2f}",
            }
        )
        inicio += fracao
    legenda = [
        {"rotulo": rotulo, "valor": valor, "cor": cor, "pct": round(valor.centavos * 100 / total) if total else 0}
        for rotulo, valor, cor in fatias
    ]
    return {"arcos": arcos, "legenda": legenda, "raio": RAIO_DO_ANEL}


def _destino_seguro(voltar: str | None, padrao: str) -> str:
    """Só aceita caminhos internos (evita redirecionar para outro site)."""
    if voltar and voltar.startswith("/") and not voltar.startswith("//"):
        return voltar
    return padrao


def _redirecionar(destino: str, **mensagem: str) -> RedirectResponse:
    separador = "&" if "?" in destino else "?"
    url = f"{destino}{separador}{urlencode(mensagem)}" if mensagem else destino
    return RedirectResponse(url, status_code=303)


def _data(texto: str) -> date:
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise ErroDeNegocio("Data inválida.") from None


def criar_rotas_paginas(estado: Estado) -> APIRouter:
    rotas = APIRouter(include_in_schema=False)
    templates = Jinja2Templates(directory=PASTA_TEMPLATES)
    templates.env.filters["data"] = lambda d: d.strftime("%d/%m/%Y") if d else ""
    templates.env.filters["dia_mes"] = lambda d: d.strftime("%d/%m") if d else ""

    def pagina(request: Request, nome: str, **contexto: Any) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            nome,
            {
                "casa": estado.casa,
                "hoje": estado.hoje(),
                "erro": request.query_params.get("erro"),
                "ok": request.query_params.get("ok"),
                "caminho": request.url.path,
                "url_atual": str(request.url.path)
                + (f"?ciclo={request.query_params['ciclo']}" if "ciclo" in request.query_params else ""),
                **contexto,
            },
        )

    def alterar(voltar: str | None, padrao: str, operacao: Callable[[Casa], Any], sucesso: str) -> RedirectResponse:
        destino = _destino_seguro(voltar, padrao)
        try:
            estado.alterar(operacao)
        except ErroDeNegocio as e:
            return _redirecionar(destino, erro=str(e))
        return _redirecionar(destino, ok=sucesso)

    # ---------------------------------------------------------------- resumo

    @rotas.get("/", response_class=HTMLResponse)
    def inicio(request: Request, ciclo: str | None = None) -> HTMLResponse:
        c = estado.ciclo(ciclo)
        r = estado.casa.resumo(estado.hoje(), c)
        return pagina(
            request,
            "resumo.html",
            r=r,
            anel=montar_anel(r),
            ciclo=c,
        )

    @rotas.post("/configuracao")
    def configuracao(nome: str = Form(...), dia_inicio: int = Form(...)) -> RedirectResponse:
        def aplicar(casa: Casa) -> None:
            casa.dia_inicio_ciclo = dia_inicio
            casa.nome = nome.strip() or casa.nome

        return alterar("/", "/", aplicar, "Configuração salva.")

    @rotas.post("/desfazer")
    def desfazer(voltar: str = Form("/")) -> RedirectResponse:
        acao = estado.alterar(lambda casa: casa.desfazer())
        destino = _destino_seguro(voltar, "/")
        if acao is None:
            return _redirecionar(destino, erro="Não há nada para desfazer.")
        return _redirecionar(destino, ok=f"Desfeito: {acao.descricao}.")

    # ---------------------------------------------------------------- gastos

    @rotas.get("/gastos", response_class=HTMLResponse)
    def gastos(request: Request, ciclo: str | None = None, ordem: str = "recentes") -> HTMLResponse:
        c = estado.ciclo(ciclo)
        ordem = ordem if ordem in ORDENS_DE_GASTOS else "recentes"
        lista = estado.casa.gastos_do_ciclo(c, ordem)
        return pagina(
            request,
            "gastos.html",
            ciclo=c,
            gastos=lista,
            total=sum((g.valor for g in lista), Dinheiro.zero()),
            ordem=ordem,
            ordens=NOMES_DAS_ORDENS,
        )

    @rotas.post("/gastos")
    def lancar_gasto(
        descricao: str = Form(...),
        valor: str = Form(...),
        data: str = Form(...),
        caixinha_id: str = Form(""),
        voltar: str = Form("/gastos"),
    ) -> RedirectResponse:
        return alterar(
            voltar,
            "/gastos",
            lambda casa: casa.lancar_gasto(descricao, Dinheiro.de_texto(valor), _data(data), caixinha_id or None),
            f"Gasto “{descricao.strip()}” lançado.",
        )

    @rotas.post("/gastos/{gasto_id}/excluir")
    def excluir_gasto(gasto_id: str, voltar: str = Form("/gastos")) -> RedirectResponse:
        return alterar(voltar, "/gastos", lambda casa: casa.remover_gasto(gasto_id), "Gasto excluído.")

    # ------------------------------------------------------------- caixinhas

    @rotas.get("/caixinhas", response_class=HTMLResponse)
    def caixinhas(request: Request) -> HTMLResponse:
        r = estado.casa.resumo(estado.hoje())
        return pagina(request, "caixinhas.html", r=r, tipos=Caixinha.tipos_disponiveis())

    @rotas.post("/caixinhas")
    def criar_caixinha(
        nome: str = Form(...),
        tipo: str = Form(...),
        aporte: str = Form(""),
        icone: str = Form("📦"),
    ) -> RedirectResponse:
        return alterar(
            "/caixinhas",
            "/caixinhas",
            lambda casa: casa.criar_caixinha(
                tipo, nome, Dinheiro.de_texto(aporte) if aporte.strip() else None, icone.strip()
            ),
            f"Caixinha “{nome.strip()}” criada.",
        )

    @rotas.post("/caixinhas/{caixinha_id}/excluir")
    def excluir_caixinha(caixinha_id: str) -> RedirectResponse:
        return alterar(
            "/caixinhas", "/caixinhas", lambda casa: casa.remover_caixinha(caixinha_id), "Caixinha excluída."
        )

    # -------------------------------------------------------------- entradas

    @rotas.get("/entradas", response_class=HTMLResponse)
    def entradas(request: Request, ciclo: str | None = None) -> HTMLResponse:
        c = estado.ciclo(ciclo)
        lista = estado.casa.entradas_do_ciclo(c)
        return pagina(
            request,
            "entradas.html",
            ciclo=c,
            entradas=lista,
            total=sum((e.valor for e in lista), Dinheiro.zero()),
            naturezas=Entrada.NATUREZAS,
        )

    @rotas.post("/entradas")
    def lancar_entrada(
        descricao: str = Form(...),
        valor: str = Form(...),
        data: str = Form(...),
        natureza: str = Form("renda"),
        voltar: str = Form("/entradas"),
    ) -> RedirectResponse:
        return alterar(
            voltar,
            "/entradas",
            lambda casa: casa.lancar_entrada(descricao, Dinheiro.de_texto(valor), _data(data), natureza),
            f"Entrada “{descricao.strip()}” lançada.",
        )

    @rotas.post("/entradas/{entrada_id}/excluir")
    def excluir_entrada(entrada_id: str, voltar: str = Form("/entradas")) -> RedirectResponse:
        return alterar(voltar, "/entradas", lambda casa: casa.remover_entrada(entrada_id), "Entrada excluída.")

    # -------------------------------------------------------------- parcelas

    @rotas.get("/parcelas", response_class=HTMLResponse)
    def parcelas(request: Request) -> HTMLResponse:
        return pagina(
            request,
            "parcelas.html",
            parcelamentos=estado.casa.parcelamentos,
            vencimentos=estado.casa.proximos_vencimentos(5),
            falta_formatada=sum((p.falta_pagar for p in estado.casa.parcelamentos), Dinheiro.zero()),
        )

    @rotas.post("/parcelas")
    def criar_parcelamento(
        descricao: str = Form(...),
        valor_total: str = Form(...),
        total_parcelas: int = Form(...),
        primeiro_vencimento: str = Form(...),
    ) -> RedirectResponse:
        return alterar(
            "/parcelas",
            "/parcelas",
            lambda casa: casa.criar_parcelamento(
                descricao, Dinheiro.de_texto(valor_total), total_parcelas, _data(primeiro_vencimento)
            ),
            f"Parcelamento “{descricao.strip()}” criado.",
        )

    @rotas.post("/parcelas/{parcelamento_id}/pagar")
    def pagar_parcela(
        parcelamento_id: str, numero: int = Form(...), voltar: str = Form("/parcelas")
    ) -> RedirectResponse:
        return alterar(
            voltar,
            "/parcelas",
            lambda casa: casa.pagar_parcela(parcelamento_id, numero, estado.hoje()),
            f"Parcela {numero} marcada como paga.",
        )

    return rotas
