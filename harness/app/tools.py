# Registro de tools (5, decisión D3) con JSON Schema para el LLM.
# Los URI (endpoints) nacen del contrato §4: mismo contrato que tests y ms-citas.
import time
import uuid
from contextvars import ContextVar
from typing import Any

import httpx

from app.config import CONFIG

# Hook para tests: inyectar httpx.MockTransport sin red (None = HTTP real)
_TRANSPORT: httpx.BaseTransport | None = None
AUTH_TOKEN: ContextVar[str] = ContextVar("auth_token", default="")


class ToolError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def _client() -> httpx.Client:
    # h11 rechaza "Bearer " (espacio final): omitir header si no hay token
    token = AUTH_TOKEN.get()
    headers = {"Authorization": "Bearer " + token} if token else {}
    return httpx.Client(
        timeout=CONFIG.HTTP_TIMEOUT_MS / 1000,
        transport=_TRANSPORT,
        headers=headers,
    )


def listar_medicos() -> list[dict[str, Any]]:
    with _client() as c:
        r = c.get(f"{CONFIG.MS_AGENDA_URL}/api/v1/medicos")
        if r.status_code != 200:
            raise ToolError(
                r.status_code, "AGENDA_NO_DISPONIBLE", "No se pudo listar médicos"
            )
        return r.json()


def ver_disponibilidad(medico_id: str, fecha: str) -> dict[str, Any]:
    with _client() as c:
        r = c.get(
            f"{CONFIG.MS_AGENDA_URL}/api/v1/medicos/{medico_id}/disponibilidad",
            params={"fecha": fecha},
        )
        if r.status_code != 200:
            body = r.json() if r.status_code < 500 else {}
            raise ToolError(
                r.status_code,
                body.get("code", "AGENDA_NO_DISPONIBLE"),
                body.get("message", "No se pudo consultar disponibilidad"),
            )
        return r.json()


def reservar_cita(
    paciente: dict[str, str], medico_id: str, fecha: str, hora: str
) -> dict[str, Any]:
    body = {
        "paciente": {"nombre": paciente["nombre"], "documento": paciente["documento"]},
        "medico_id": medico_id,
        "fecha": fecha,
        "hora": hora,
    }
    headers = {
        "Idempotency-Key": str(uuid.uuid4())
    }  # reintentos del agente no duplican
    with _client() as c:
        r = c.post(f"{CONFIG.MS_CITAS_URL}/api/v1/citas", json=body, headers=headers)
        payload = None
        try:
            payload = r.json()
        except Exception:
            payload = {}
        if r.status_code not in (200, 201):
            err = payload.get("error") or payload
            raise ToolError(
                r.status_code,
                err.get(
                    "code",
                    "AGENDA_NO_DISPONIBLE" if r.status_code >= 500 else "VALIDACION",
                ),
                err.get("message", "No se pudo reservar la cita"),
            )
        return payload


def cancelar_cita(cita_id: str) -> dict[str, Any]:
    with _client() as c:
        r = c.post(f"{CONFIG.MS_CITAS_URL}/api/v1/citas/{cita_id}/cancelar")
        try:
            payload = r.json()
        except Exception:
            payload = {}
        if r.status_code != 200:
            err = payload.get("error") or payload
            raise ToolError(
                r.status_code,
                err.get(
                    "code",
                    "AGENDA_NO_DISPONIBLE" if r.status_code >= 500 else "VALIDACION",
                ),
                err.get("message", "No se pudo cancelar la cita"),
            )
        return payload


def listar_citas(documento: str) -> dict[str, Any]:
    with _client() as c:
        r = c.get(
            f"{CONFIG.MS_CITAS_URL}/api/v1/citas", params={"documento": documento}
        )
        if r.status_code != 200:
            body = r.json() if r.status_code < 500 else {}
            raise ToolError(
                r.status_code,
                body.get("code", "AGENDA_NO_DISPONIBLE"),
                body.get("message", "No se pudo listar citas"),
            )
        return r.json()


EXECUTORS: dict[str, Any] = {
    "listar_medicos": listar_medicos,
    "ver_disponibilidad": ver_disponibilidad,
    "reservar_cita": reservar_cita,
    "cancelar_cita": cancelar_cita,
    "listar_citas": listar_citas,
}

# JSON Schemas entregados al LLM (openai-compatibles, ex. Groq)
TOOLS_SPEC: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "listar_medicos",
            "description": "Lista los médicos activos con su id, nombre y especialidad.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ver_disponibilidad",
            "description": "Consulta las franjas base de 30 min de un médico en una fecha YYYY-MM-DD.",
            "parameters": {
                "type": "object",
                "properties": {
                    "medico_id": {"type": "string", "description": "UUID del médico"},
                    "fecha": {"type": "string", "description": "Formato YYYY-MM-DD"},
                },
                "required": ["medico_id", "fecha"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reservar_cita",
            "description": "Reserva una cita para un paciente con un médico en fecha y hora (validada por ms-citas).",
            "parameters": {
                "type": "object",
                "properties": {
                    "paciente": {
                        "type": "object",
                        "properties": {
                            "nombre": {"type": "string"},
                            "documento": {"type": "string", "description": "8 dígitos"},
                        },
                        "required": ["nombre", "documento"],
                    },
                    "medico_id": {"type": "string"},
                    "fecha": {"type": "string", "description": "YYYY-MM-DD"},
                    "hora": {"type": "string", "description": "HH:MM"},
                },
                "required": ["paciente", "medico_id", "fecha", "hora"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancelar_cita",
            "description": "Cancela una cita por su id (obtenido previo de listar_citas).",
            "parameters": {
                "type": "object",
                "properties": {"cita_id": {"type": "string"}},
                "required": ["cita_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_citas",
            "description": "Lista las citas de un paciente por documento (para localizar y disambiguar).",
            "parameters": {
                "type": "object",
                "properties": {"documento": {"type": "string"}},
                "required": ["documento"],
            },
        },
    },
]

SYSTEM_PROMPT = """Eres el recepcionista virtual del centro de salud rural (hoy es {hoy}).
- Ayudas a los pacientes a reservar, consultar y cancelar citas, SOLO con las herramientas disponibles.
- Si al paciente le faltan datos para la cita (especialidad, fecha, hora, nombre, documento),
  PREGUNTÁNDOLOS uno a uno antes de usar herramientas. NUNCA inventes ni asumas datos faltantes.
- Nunca inventas datos: si una herramienta falla (p. ej. agenda no disponible), informa el problema con honestidad.
- No atiendes temas fuera del centro de salud (ni clima, ni recetas, ni diagnóstico). Responde con cortesía en español.
- Antes de reservar, consulta disponibilidad. Antes de cancelar, localiza la cita con el documento del paciente.
"""


def ejecutar_tool(nombre: str, args: dict[str, Any]) -> dict[str, Any]:
    """Ejecuta una tool y devuelve un resultado JSON-serializable (nunca lanza al loop)."""
    t0 = time.perf_counter()
    fn = EXECUTORS.get(nombre)
    if fn is None:
        return {
            "ok": False,
            "code": "TOOL_DESCONOCIDA",
            "message": f"Tool '{nombre}' no existe",
        }
    try:
        out = fn(**args)
        return {"ok": True, "result": out, "tool": nombre, "ms": _ms(t0)}
    except ToolError as e:
        return {
            "ok": False,
            "code": e.code,
            "message": e.message,
            "status": e.status,
            "tool": nombre,
            "ms": _ms(t0),
        }
    except Exception as e:  # httpx.TimeoutException, etc.
        return {
            "ok": False,
            "code": "HARNESS_TIMEOUT",
            "message": f"Error al ejecutar tool: {e}",
            "tool": nombre,
            "ms": _ms(t0),
        }


def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)
