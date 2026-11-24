from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.exemplo import criar_casa_exemplo
from app.main import criar_app
from app.repositorio import RepositorioEmMemoria

HOJE = date(2026, 11, 16)


@pytest.fixture
def cliente() -> TestClient:
    repo = RepositorioEmMemoria(criar_casa_exemplo(HOJE))
    return TestClient(criar_app(repo, hoje=lambda: HOJE))


@pytest.mark.parametrize("url", ["/", "/gastos", "/entradas", "/caixinhas", "/parcelas", "/docs"])
def test_paginas_abrem(cliente, url):
    resposta = cliente.get(url)
    assert resposta.status_code == 200


def test_navega_entre_ciclos(cliente):
    resposta = cliente.get("/gastos?ciclo=2026-10-15")
    assert "Out 2026" in resposta.text
    assert "Nenhum gasto neste ciclo" in resposta.text


def test_lancar_gasto_pelo_formulario_e_desfazer(cliente):
    r = cliente.post(
        "/gastos",
        data={"descricao": "Sorvete", "valor": "12,50", "data": "2026-11-16", "caixinha_id": ""},
    )
    assert r.status_code == 200  # seguiu o redirecionamento
    assert "Sorvete" in r.text and "R$ 12,50" in r.text

    r = cliente.post("/desfazer", data={"voltar": "/gastos"})
    assert "Desfeito" in r.text
    assert "Sorvete" not in cliente.get("/gastos").text


def test_valor_invalido_mostra_erro(cliente):
    r = cliente.post("/gastos", data={"descricao": "X", "valor": "abc", "data": "2026-11-16"})
    assert "Valor inválido" in r.text


def test_redirecionamento_externo_e_bloqueado(cliente):
    r = cliente.post(
        "/gastos",
        data={"descricao": "X", "valor": "1", "data": "2026-11-16", "voltar": "//site-malicioso.com"},
        follow_redirects=False,
    )
    assert r.headers["location"].startswith("/gastos")


def test_api_resumo_e_gastos(cliente):
    resumo = cliente.get("/api/resumo").json()
    assert resumo["ciclo"]["rotulo"] == "Nov 2026"
    assert resumo["livre"]["centavos"] >= 0

    criado = cliente.post(
        "/api/gastos", json={"descricao": "Uber", "valor": 23.4, "data": "2026-11-16"}
    )
    assert criado.status_code == 201
    gid = criado.json()["id"]
    assert criado.json()["valor_centavos"] == 2340

    por_valor = cliente.get("/api/gastos?ordem=maior_valor").json()
    valores = [g["valor_centavos"] for g in por_valor]
    assert valores == sorted(valores, reverse=True)

    assert cliente.delete(f"/api/gastos/{gid}").status_code == 204
    assert cliente.delete(f"/api/gastos/{gid}").status_code == 404


def test_api_valida_entrada(cliente):
    r = cliente.post("/api/gastos", json={"descricao": "X", "valor": -5, "data": "2026-11-16"})
    assert r.status_code == 422


def test_pagar_parcela(cliente):
    parcelas = cliente.get("/api/parcelamentos").json()
    note = next(p for p in parcelas if p["descricao"] == "Notebook")
    r = cliente.post(f"/parcelas/{note['id']}/pagar", data={"numero": 1})
    assert "Parcela 1 marcada como paga" in r.text
