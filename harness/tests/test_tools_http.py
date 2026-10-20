# Tests HTTP de las tools con httpx.MockTransport (sin red, sin MS reales)
import httpx
import pytest

import app.tools as tools
from app.tools import ToolError, ejecutar_tool


def _transport(handler):
    return httpx.MockTransport(handler)


@pytest.fixture
def usar_transport(monkeypatch):
    def set_(handler):
        monkeypatch.setattr(tools, "_TRANSPORT", _transport(handler))

    return set_


def test_listar_medicos_ok(usar_transport):
    usar_transport(
        lambda req: httpx.Response(
            200,
            json=[{"id": "m1", "nombre": "Dra. Quispe", "especialidad": "PEDIATRIA"}],
        )
    )
    out = tools.listar_medicos()
    assert out[0]["id"] == "m1"


def test_ver_disponibilidad_404_mapea(usar_transport):
    usar_transport(
        lambda req: httpx.Response(
            404, json={"code": "MEDICO_NO_ENCONTRADO", "message": "no existe"}
        )
    )
    with pytest.raises(ToolError) as e:
        tools.ver_disponibilidad("abc", "2026-11-02")
    assert e.value.code == "MEDICO_NO_ENCONTRADO"
    assert e.value.status == 404


def test_reservar_201_ok(usar_transport):
    usar_transport(
        lambda req: httpx.Response(
            201, json={"cita": {"id": "c1", "estado": "CONFIRMADA"}}
        )
    )
    out = tools.reservar_cita(
        {"nombre": "M", "documento": "12345678"}, "m1", "2026-11-02", "08:00"
    )
    assert out["cita"]["estado"] == "CONFIRMADA"


def test_reservar_409_ocupado(usar_transport):
    usar_transport(
        lambda req: httpx.Response(
            409, json={"error": {"code": "HORARIO_OCUPADO", "message": "ocupada"}}
        )
    )
    with pytest.raises(ToolError) as e:
        tools.reservar_cita(
            {"nombre": "M", "documento": "12345678"}, "m1", "2026-11-02", "08:00"
        )
    assert e.value.code == "HORARIO_OCUPADO"


def test_reservar_503_agenda_caida(usar_transport):
    usar_transport(lambda req: httpx.Response(503))
    with pytest.raises(ToolError) as e:
        tools.reservar_cita(
            {"nombre": "M", "documento": "12345678"}, "m1", "2026-11-02", "08:00"
        )
    assert e.value.code == "AGENDA_NO_DISPONIBLE"


def test_reservar_body_no_json_503(usar_transport):
    usar_transport(lambda req: httpx.Response(500, content=b"no-es-json"))
    with pytest.raises(ToolError) as e:
        tools.reservar_cita(
            {"nombre": "M", "documento": "12345678"}, "m1", "2026-11-02", "08:00"
        )
    assert e.value.code == "AGENDA_NO_DISPONIBLE"


def test_cancelar_ok_y_404(usar_transport):
    usar_transport(
        lambda req: httpx.Response(
            200, json={"cita": {"estado": "CANCELADA", "id": "c1"}}
        )
    )
    assert tools.cancelar_cita("c1")["cita"]["estado"] == "CANCELADA"

    usar_transport(
        lambda req: httpx.Response(
            404, json={"code": "CITA_NO_ENCONTRADA", "message": "no"}
        )
    )
    with pytest.raises(ToolError) as e:
        tools.cancelar_cita("nope")
    assert e.value.code == "CITA_NO_ENCONTRADA"


def test_listar_citas_500(usar_transport):
    usar_transport(lambda req: httpx.Response(500))
    with pytest.raises(ToolError) as e:
        tools.listar_citas("12345678")
    assert e.value.code == "AGENDA_NO_DISPONIBLE"


def test_ver_disponibilidad_500_error_envuelve(usar_transport):
    usar_transport(lambda req: httpx.Response(502))
    with pytest.raises(ToolError) as e:
        tools.ver_disponibilidad("m1", "2026-11-02")
    assert e.value.code == "AGENDA_NO_DISPONIBLE"


def test_ejecutar_tool_desconocida():
    res = ejecutar_tool("no_existe", {})
    assert res["ok"] is False and res["code"] == "TOOL_DESCONOCIDA"


def test_ejecutar_tool_timeout(monkeypatch):
    def boom():
        raise httpx.ConnectTimeout("timeout")

    monkeypatch.setitem(tools.EXECUTORS, "boom", boom)
    res = ejecutar_tool("boom", {})
    assert res["ok"] is False and res["code"] == "HARNESS_TIMEOUT"


def test_ejecutar_tool_toolerror(monkeypatch):
    def fail_tool():
        raise ToolError(400, "X", "datos malos")

    monkeypatch.setitem(tools.EXECUTORS, "fail_tool", fail_tool)
    res = ejecutar_tool("fail_tool", {})
    assert res["ok"] is False and res["code"] == "X"
