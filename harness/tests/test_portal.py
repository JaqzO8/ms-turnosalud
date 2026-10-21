import httpx
import pytest
from fastapi.testclient import TestClient

import app.tools as tools
from app.main import app
from app.portal import auth_headers


@pytest.fixture
def portal(monkeypatch):
    calls = []
    state = {"valid": True}

    def transport(request):
        calls.append(request)
        path = request.url.path
        if state.get("offline"):
            raise httpx.ConnectError("offline")
        if path == "/auth/me":
            if (
                not request.headers.get("Authorization", "").endswith("test-token")
                or not state["valid"]
            ):
                return httpx.Response(401, json={"message": "Inicia sesiÃ³n"})
            return httpx.Response(200, json={"nombre": "Demo", "documento": "12345678"})
        if path == "/auth/login":
            return httpx.Response(
                200, json={"token": "test-token", "usuario": {"nombre": "Demo"}}
            )
        if path == "/auth/register":
            return httpx.Response(201, json={"ok": True})
        if path == "/api/v1/citas":
            return httpx.Response(
                200, json={"items": [], "total": 0, "page": 1, "size": 10}
            )
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(tools, "_TRANSPORT", httpx.MockTransport(transport))
    return TestClient(app), calls, state


def test_portal_cookie_and_scope(portal):
    client, calls, _ = portal
    assert client.get("/portal/me").status_code == 401
    assert client.post("/portal/login", json={}).status_code == 403
    client.headers["X-Requested-With"] = "TurnoSalud"
    assert client.post("/portal/register", json={}).status_code == 201
    login = client.post("/portal/login", json={})
    assert "token" not in login.json()
    assert "HttpOnly" in login.headers["set-cookie"]
    assert client.get("/portal/me").json()["documento"] == "12345678"
    assert client.get("/portal/citas?documento=99999999").status_code == 200
    assert calls[-1].url.params["documento"] == "12345678"
    assert client.post("/portal/citas/one/cancelar").status_code == 200
    assert client.get("/evals").status_code == 403
    assert client.post("/portal/logout").status_code == 200
    assert "turnosalud_session" not in client.cookies


def test_sin_token_no_se_envia_bearer_vacio(portal):
    # h11 rechaza el header "Bearer " (regresion: 503 en EC2 con trafico real)
    client, calls, _ = portal
    client.get("/portal/me")
    assert "authorization" not in calls[0].headers
    with tools._client() as c:
        assert "authorization" not in c.headers


def test_con_token_se_envia_bearer(portal):
    token = tools.AUTH_TOKEN.set("abc")
    try:
        with tools._client() as c:
            assert c.headers["authorization"] == "Bearer abc"
        assert auth_headers("abc") == {"Authorization": "Bearer abc"}
        assert auth_headers("") == {}
    finally:
        tools.AUTH_TOKEN.reset(token)


def test_authenticated_chat_context(portal, monkeypatch):
    client, _, _ = portal
    client.headers["X-Requested-With"] = "TurnoSalud"
    client.post("/portal/login", json={})

    class Agent:
        def responder(self, message, session):
            assert "12345678" in message
            assert session != "chosen-session"
            assert tools.AUTH_TOKEN.get() == "test-token"
            return {"respuesta": "ok"}

    monkeypatch.setattr("app.main.get_agent", lambda: Agent())
    assert (
        client.post(
            "/chat", json={"mensaje": "Hola", "sesion_id": "chosen-session"}
        ).json()["respuesta"]
        == "ok"
    )
    assert tools.AUTH_TOKEN.get() == ""


def test_offline_and_anonymous_chat(portal):
    client, _, state = portal
    client.headers["X-Requested-With"] = "TurnoSalud"
    assert client.post("/chat", json={"mensaje": "Hola"}).status_code == 401
    state["offline"] = True
    assert client.get("/portal/me").status_code == 503
