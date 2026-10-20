# API HTTP del harness (T-07). CLI alternativa: uvicorn app:app --port 3003
from fastapi import FastAPI
from pydantic import BaseModel
import threading

from config import CONFIG
from agent import Agente
from evals import correr_evals

app = FastAPI(title="harness-agent", version="0.1.0", description="Recepcionista IA del centro de salud rural (TURNO-SALUD)")

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
    return {"status": "ok", "mock_llm": CONFIG.MOCK_LLM, "fixed_today": CONFIG.FIXED_TODAY}


@app.post("/chat")
def chat(inp: ChatIn):
    turno = get_agent().responder(inp.mensaje, inp.sesion_id)
    return turno


@app.get("/evals")
def evals():
    resultados = correr_evals(get_agent())
    ok_count = sum(1 for r in resultados if r["ok"])
    return {
        "provider": "mock" if CONFIG.MOCK_LLM else f"groq:{CONFIG.LLM_MODEL}",
        "total": len(resultados),
        "ok": ok_count,
        "resultados": resultados,
    }
