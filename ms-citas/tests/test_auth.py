import hashlib
import time
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from test_citas import payload

from app.auth import hash_password
from app.db import LoginSession, Usuario
from app.main import create_app


def test_account_lifecycle_and_ownership(env):
    _, _, engine = env

    class Agenda:
        def validate(self, *args):
            pass

    with TestClient(create_app(engine, Agenda())) as client:
        account = {"documento": "12345678", "nombre": "Paciente Demo", "password": "DemoTest!2026"}
        assert client.get("/api/v1/citas?documento=12345678").status_code == 401
        assert client.get("/auth/me").status_code == 401
        assert client.post("/auth/register", json=account).status_code == 201
        assert client.post("/auth/register", json=account).status_code == 409
        assert client.post("/auth/login", json={**account, "password": "incorrect"}).status_code == 401
        assert client.post("/auth/login", json={**account, "documento": "99999999"}).status_code == 401
        token = client.post("/auth/login", json=account).json()["token"]
        client.headers["Authorization"] = "Bearer " + token
        assert client.get("/auth/me").json()["documento"] == "12345678"
        assert client.get("/api/v1/citas?documento=87654321").status_code == 403
        wrong = payload(paciente={"nombre": "Otro", "documento": "87654321"})
        assert client.post("/api/v1/citas", json=wrong, headers={"Idempotency-Key": str(uuid4())}).status_code == 403
        result = client.post("/api/v1/citas", json=payload(), headers={"Idempotency-Key": str(uuid4())})
        assert result.status_code == 201
        cid = result.json()["cita"]["id"]
        assert client.get("/api/v1/citas?documento=12345678").json()["total"] == 1
        other = {**account, "documento": "87654321"}
        client.post("/auth/register", json=other)
        other_token = client.post("/auth/login", json=other).json()["token"]
        assert (
            client.post(f"/api/v1/citas/{cid}/cancelar", headers={"Authorization": "Bearer " + other_token}).status_code
            == 404
        )
        assert client.post(f"/api/v1/citas/{cid}/cancelar").status_code == 200
        assert client.post("/auth/logout").status_code == 200
        assert client.get("/auth/me").status_code == 401
        with Session(engine) as session:
            user = session.get(Usuario, "12345678")
            assert user.password_hash != account["password"]
            session.add(
                LoginSession(
                    token_hash=hashlib.sha256(b"expired").hexdigest(),
                    documento=user.documento,
                    expires=int(time.time()) - 1,
                )
            )
            session.commit()
        assert client.get("/auth/me", headers={"Authorization": "Bearer expired"}).status_code == 401


def test_legacy_registration_and_validation(env):
    old_client, _, engine = env
    old_client.post("/api/v1/citas", json=payload(), headers={"Idempotency-Key": str(uuid4())})
    with TestClient(create_app(engine)) as client:
        account = {"documento": "12345678", "nombre": "Demo", "password": "DemoTest!2026"}
        assert client.post("/auth/register", json=account).status_code == 409
        assert (
            client.post("/auth/register", json={**account, "documento": "87654321", "nombre": " "}).status_code == 422
        )
        assert client.post("/auth/register", json={**account, "password": "short"}).status_code == 422
    assert hash_password("same-password") != hash_password("same-password")
