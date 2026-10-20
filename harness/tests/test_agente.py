# Tests del harness con fakes (sin red, sin MS reales): evals E-01..E-07 verdes,
# memoria de sesión, transcript y guardarrail de presupuesto de tools.
import json
import pathlib

import pytest
from fakes import FakeCitaStore, crear_fakes

import app.tools as tools
from app.agent import Agente
from app.config import CONFIG
from app.evals import correr_evals
from app.llm import LLMRespuesta, MockLLM


@pytest.fixture
def agente(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "EXECUTORS", crear_fakes(FakeCitaStore()))
    monkeypatch.setattr(CONFIG, "LOGS_DIR", str(tmp_path))
    return Agente(llm=MockLLM())


def test_evals_verdes(agente):
    res = correr_evals(agente)
    fallas = [r for r in res if not r["ok"]]
    assert not fallas, fallas
    assert [r["id"] for r in res] == [
        "E-01",
        "E-02",
        "E-03",
        "E-04",
        "E-05",
        "E-06",
        "E-07",
    ]


def test_e06_pregunta_sin_tools(agente):
    turno = agente.responder("Hola, quiero una cita.", "s-e06")
    assert turno["tools_usadas"] == []
    assert "¿" in turno["respuesta"]


def test_datos_paciente_obligatorios(agente):
    turno = agente.responder("pediatría el 2026-11-02 a las 08:00", "missing-patient")
    assert turno["tools_usadas"] == []
    assert "nombre" in turno["respuesta"]


def test_cancelar_despues_de_reservar_misma_sesion(agente):
    agente.responder(
        "pediatría el 2026-11-02 a las 08:00. Soy Test Paciente, documento 12345678",
        "same",
    )
    turno = agente.responder("cancelar mi cita documento 12345678", "same")
    assert "CANCELADA" in turno["respuesta"]


def test_e07_memoria_conversacional(agente):
    sesion = "s-e07"
    agente.responder("Hola, necesito una cita.", sesion)
    agente.responder("con odontología", sesion)
    agente.responder("el 2026-11-03", sesion)
    final = agente.responder(
        "a las 09:30. Soy Ramiro Sedano, documento 55778899", sesion
    )
    assert any(t["name"] == "reservar_cita" and t["ok"] for t in final["tools_usadas"])


def test_transcript_jsonl(agente, tmp_path):
    agente.responder("Hola", "s-tr")
    files = list(pathlib.Path(CONFIG.LOGS_DIR).glob("sesion-s-tr.jsonl"))
    assert files, "transcript fue escrito"
    reg = json.loads(files[0].read_text(encoding="utf-8").splitlines()[0])
    assert reg["sesion_id"] == "s-tr"
    assert "mensajes" in reg and "ms" in reg


def test_guardrail_presupuesto_tools(agente):
    class LLMCicloSinFin:
        def chat(self, messages, tools_spec):
            return LLMRespuesta(
                tool_calls=[
                    {
                        "id": "call-loop",
                        "type": "function",
                        "function": {"name": "listar_medicos", "arguments": "{}"},
                    }
                ]
            )

    agente.llm = LLMCicloSinFin()
    res = agente.responder("reservame una cita", "s-guard")
    assert len(res["tools_usadas"]) == CONFIG.MAX_TOOL_CALLS
    assert "agotaron" in res["respuesta"]
