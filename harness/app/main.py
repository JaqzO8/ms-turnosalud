# API HTTP del harness (T-07). Servida con uvicorn app.main:app en :3003 y sirve la UI de chat.
import hashlib
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.agent import Agente
from app.config import CONFIG
from app.evals import correr_evals
from app.portal import csrf, current_user, install_portal
from app.tools import AUTH_TOKEN

REQUIRE_LOGIN = True

app = FastAPI(
    title="harness-agent",
    version="0.1.0",
    description="Recepcionista IA del centro de salud rural (TURNO-SALUD)",
)

_lock = threading.Lock()
_agent: Agente | None = None


def get_agent() -> Agente:
    global _agent
    with _lock:
        if _agent is None:
            _agent = Agente()
        return _agent


class ChatIn(BaseModel):
    mensaje: str
    sesion_id: str | None = None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "mock_llm": CONFIG.MOCK_LLM,
        "fixed_today": CONFIG.FIXED_TODAY,
    }


@app.post("/chat")
def chat(inp: ChatIn, request: Request):
    if not REQUIRE_LOGIN:
        return get_agent().responder(inp.mensaje, inp.sesion_id)
    csrf(request)
    user = current_user(request)
    token = request.cookies.get("turnosalud_session", "")
    context = AUTH_TOKEN.set(token)
    try:
        session = hashlib.sha256(
            (token + (inp.sesion_id or "default")).encode()
        ).hexdigest()
        message = f"Usuario autenticado: {user['nombre']}, documento {user['documento']}. Solo puedes gestionar sus citas.\n{inp.mensaje}"
        return get_agent().responder(message, session)
    finally:
        AUTH_TOKEN.reset(context)


@app.get("/evals")
def evals():
    if REQUIRE_LOGIN:
        raise HTTPException(
            403,
            "Evaluaciones disponibles únicamente en tests, no en cuentas de usuarios.",
        )
    resultados = correr_evals(get_agent())
    ok_count = sum(1 for r in resultados if r["ok"])
    return {
        "provider": "mock" if CONFIG.MOCK_LLM else f"groq:{CONFIG.LLM_MODEL}",
        "total": len(resultados),
        "ok": ok_count,
        "resultados": resultados,
    }


# UI de chat (frontend ligero servido por el mismo harness en GET /)
_STATIC = Path(__file__).resolve().parent / "static"
install_portal(app)
app.mount("/", StaticFiles(directory=str(_STATIC), html=True), name="ui")
