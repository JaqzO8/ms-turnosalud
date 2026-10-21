# Tests de la API HTTP del harness con TestClient + fakes (sin red)
import pytest
from fakes import FakeCitaStore, crear_fakes
from fastapi.testclient import TestClient

import app.tools as tools
from app.config import CONFIG
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    store = FakeCitaStore()
    monkeypatch.setattr("app.main.REQUIRE_LOGIN", False)
    monkeypatch.setattr(tools, "EXECUTORS", crear_fakes(store))
    monkeypatch.setattr(CONFIG, "LOGS_DIR", str(tmp_path))
    return TestClient(app), store


def test_health(client):
    c, _ = client
    r = c.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["mock_llm"] is True
    assert body["fixed_today"] == "2026-11-02"


def test_chat_pregunta_datos_faltantes(client):
    c, _ = client
    r = c.post("/chat", json={"mensaje": "Hola, quiero una cita", "sesion_id": "api-1"})
    assert r.status_code == 200
    t = r.json()
    assert t["tools_usadas"] == []
    assert "¿" in t["respuesta"]
    assert t["sesion_id"] == "api-1"


def test_chat_reserva_completa(client):
    c, store = client
    r = c.post(
        "/chat",
        json={
            "mensaje": "Soy María Flores, documento 12345678. Quiero cita con pediatría el 2026-11-05 a las 10.",
            "sesion_id": "api-2",
        },
    )
    t = r.json()
    assert any(x["name"] == "reservar_cita" and x["ok"] for x in t["tools_usadas"])
    assert "CONFIRMADA" in t["respuesta"]
    assert store.citas, "la cita quedó en el store fake"


def test_evals_verdes(client):
    c, _ = client
    r = c.get("/evals")
    body = r.json()
    assert body["total"] == 7
    assert body["ok"] == 7, [x for x in body["resultados"] if not x["ok"]]


def test_ui_servida(client):
    c, _ = client
    r = c.get("/")
    assert r.status_code == 200
    assert "TURNO-SALUD" in r.text
