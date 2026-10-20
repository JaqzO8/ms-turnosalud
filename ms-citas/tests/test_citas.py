import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Barrier
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agenda import AgendaClient
from app.db import Base, Cita, make_engine
from app.main import create_app

MEDICO = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def env(tmp_path):
    engine = make_engine(os.getenv("TEST_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}"))
    # TEST_DATABASE_URL must point to a disposable test database.
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    state = {"status": 200, "available": True, "calls": 0}

    def respond(request):
        state["calls"] += 1
        state["request"] = request
        if state.get("timeout"):
            raise httpx.ReadTimeout("timeout", request=request)
        if state.get("barrier"):
            state["barrier"].wait(timeout=10)
        data = {
            "medico_id": MEDICO,
            "fecha": "2030-01-02",
            "franjas": [
                {"inicio": h, "fin": f, "disponible": state["available"]}
                for h, f in [("08:00", "08:30"), ("08:30", "09:00"), ("09:00", "09:30")]
            ],
        }
        return httpx.Response(state["status"], json=state.get("data", data))

    with httpx.Client(base_url="http://agenda", transport=httpx.MockTransport(respond)) as remote:
        app = create_app(
            engine, AgendaClient(remote), clock=lambda: datetime(2030, 1, 1, tzinfo=ZoneInfo("America/Lima"))
        )
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client, state, engine
    Base.metadata.drop_all(engine)
    engine.dispose()


def payload(**changes):
    return {
        "paciente": {"nombre": "Paciente Ficticio", "documento": "12345678"},
        "medico_id": MEDICO,
        "fecha": "2030-01-02",
        "hora": "08:00",
        **changes,
    }


def reserve(client, body=None, key=None):
    return client.post("/api/v1/citas", json=body or payload(), headers={"Idempotency-Key": key or str(uuid4())})


def assert_error(response, status, code):
    assert response.status_code == status, response.text
    data = response.json()
    assert set(data) == {"status", "code", "message", "correlation_id", "timestamp"}
    assert data["code"] == code
    assert data["status"] == status
    assert data["correlation_id"] == response.headers["X-Correlation-ID"]


def test_reserva_replay_and_payload_conflict(env):
    client, state, _ = env
    key = str(uuid4())
    first = reserve(client, key=key)
    assert first.status_code == 201
    assert first.json()["cita"]["estado"] == "CONFIRMADA"
    state["timeout"] = True
    repeat = reserve(client, key=key)
    assert repeat.status_code == 200
    assert repeat.json() == first.json()
    assert state["calls"] == 1
    assert_error(reserve(client, payload(hora="08:30"), key), 409, "IDEMPOTENCIA_CONFLICTO")


def test_cancel_rebook_and_original_replay(env):
    client, _, _ = env
    key = str(uuid4())
    first = reserve(client, key=key)
    assert_error(reserve(client), 409, "HORARIO_OCUPADO")
    cid = first.json()["cita"]["id"]
    cancelled = client.post(f"/api/v1/citas/{cid}/cancelar")
    assert cancelled.status_code == 200
    assert cancelled.json()["cita"]["estado"] == "CANCELADA"
    assert_error(client.post(f"/api/v1/citas/{cid}/cancelar"), 409, "CITA_YA_CANCELADA")
    assert reserve(client, key=key).json() == first.json()
    assert reserve(client).status_code == 201
    assert_error(client.post(f"/api/v1/citas/{uuid4()}/cancelar"), 404, "CITA_NO_ENCONTRADA")


def test_list_filters_pagination_and_cancelled(env):
    client, _, _ = env
    first = reserve(client).json()["cita"]
    reserve(client, payload(hora="08:30"))
    reserve(client, payload(hora="09:00", paciente={"nombre": "Otro", "documento": "87654321"}))
    client.post(f"/api/v1/citas/{first['id']}/cancelar")
    page = client.get("/api/v1/citas?documento=12345678&page=1&size=1").json()
    assert page["total"] == 2 and len(page["items"]) == 1
    assert page["items"][0]["estado"] == "CANCELADA"
    assert client.get("/api/v1/citas?documento=12345678&page=2&size=1").json()["items"][0]["hora"] == "08:30"
    assert client.get("/api/v1/citas?documento=00000000").json()["total"] == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"fecha": "2029-12-31"},
        {"hora": "07:00"},
        {"hora": "25:00"},
        {"medico_id": "invalid"},
        {"paciente": {"nombre": " ", "documento": "12345678"}},
        {"paciente": {"nombre": "Test", "documento": "abc"}},
        {"fecha": "bad"},
    ],
)
def test_validation(env, changes):
    assert_error(reserve(env[0], payload(**changes)), 422, "VALIDACION")


@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/citas",
        "/api/v1/citas?documento=12345678&page=0",
        "/api/v1/citas?documento=12345678&size=101",
        "/api/v1/citas?documento=bad",
    ],
)
def test_query_validation(env, url):
    assert_error(env[0].get(url), 422, "VALIDACION")


def test_missing_key_and_body(env):
    assert_error(env[0].post("/api/v1/citas", json=payload()), 422, "VALIDACION")
    assert_error(env[0].post("/api/v1/citas", json={}, headers={"Idempotency-Key": str(uuid4())}), 422, "VALIDACION")


@pytest.mark.parametrize(
    "state,status,code",
    [
        ({"timeout": True}, 503, "AGENDA_NO_DISPONIBLE"),
        ({"status": 500}, 503, "AGENDA_NO_DISPONIBLE"),
        ({"data": {}}, 503, "AGENDA_NO_DISPONIBLE"),
        ({"status": 404}, 422, "VALIDACION"),
        ({"available": False}, 409, "HORARIO_OCUPADO"),
    ],
)
def test_agenda_failures_do_not_persist(env, state, status, code):
    client, config, engine = env
    config.update(state)
    assert_error(reserve(client), status, code)
    with Session(engine) as session:
        assert session.scalars(select(Cita)).all() == []


@pytest.mark.parametrize("same_key", [True, False])
def test_concurrent_reservations(env, same_key):
    client, state, _ = env
    state["barrier"] = Barrier(2)
    keys = [str(uuid4()), str(uuid4())]
    if same_key:
        keys[1] = keys[0]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda key: reserve(client, key=key), keys))
    assert sorted(r.status_code for r in results) == ([200, 201] if same_key else [201, 409])
    assert client.get("/api/v1/citas?documento=12345678").json()["total"] == 1


def test_concurrent_cancellation(env):
    client, _, _ = env
    cid = reserve(client).json()["cita"]["id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: client.post(f"/api/v1/citas/{cid}/cancelar"), range(2)))
    assert sorted(r.status_code for r in results) == [200, 409]


def test_health_docs_contract_and_correlation(env):
    client, state, _ = env
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/docs").status_code == 200
    contract = client.get("/openapi.json").json()
    assert "200" in contract["paths"]["/api/v1/citas"]["post"]["responses"]
    cid = str(uuid4())
    result = client.post(
        "/api/v1/citas", json=payload(), headers={"Idempotency-Key": str(uuid4()), "X-Correlation-ID": cid}
    )
    assert result.headers["X-Correlation-ID"] == cid
    assert state["request"].headers["X-Correlation-ID"] == cid
    assert state["request"].url.params["fecha"] == "2030-01-02"
    assert_error(client.get("/not-found"), 404, "HTTP_ERROR")
