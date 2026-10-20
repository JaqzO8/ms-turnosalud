# Loop del agente: interpretar -> tool(s) -> observar -> responder.
# Guardarraíles: máx. MAX_TOOL_CALLS llamadas, transcript JSONL por sesión.
import json
import os
import re
import time
import uuid
from typing import Any

from app.config import CONFIG
from app.llm import LLMRespuesta, crear_llm
from app.tools import TOOLS_SPEC, ejecutar_tool


class Agente:
    def __init__(self, llm=None):
        self.llm = llm if llm is not None else crear_llm()
        # Memoria conversacional por sesión: {sesion_id: mensajes[]}
        self._sesiones: dict[str, list[dict[str, Any]]] = {}

    def responder(self, mensaje: str, sesion_id: str | None = None) -> dict[str, Any]:
        if sesion_id and not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", sesion_id):
            sesion_id = None
        nuevos = sesion_id is None or sesion_id not in self._sesiones
        sesion_id = sesion_id or str(uuid.uuid4())
        if nuevos:
            self._sesiones[sesion_id] = [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": mensaje},
            ]
        else:
            self._sesiones[sesion_id].append({"role": "user", "content": mensaje})

        mensajes = self._sesiones[sesion_id]
        tools_usadas: list[dict[str, Any]] = []
        respuesta = ""
        t0 = time.perf_counter()

        for _ in range(CONFIG.MAX_TOOL_CALLS):
            resp: LLMRespuesta = self.llm.chat(mensajes, TOOLS_SPEC)

            if resp.texto and not resp.tool_calls:
                respuesta = resp.texto
                mensajes.append({"role": "assistant", "content": resp.texto})
                break

            if resp.tool_calls:
                mensajes.append(
                    {
                        "role": "assistant",
                        "content": resp.texto or "",
                        "tool_calls": resp.tool_calls,
                    }
                )
                for call in resp.tool_calls:
                    nombre = call["function"]["name"]
                    try:
                        args = json.loads(call["function"].get("arguments") or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    resultado = ejecutar_tool(nombre, args)
                    tools_usadas.append(
                        {
                            "name": nombre,
                            "args": args,
                            "ok": resultado.get("ok", False),
                            "code": resultado.get("code"),
                        }
                    )
                    mensajes.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.get("id", "call_0"),
                            "content": json.dumps(resultado, ensure_ascii=False),
                        }
                    )
            else:
                respuesta = resp.texto or ""
                break
        else:
            # Guardarrail: se agotó el presupuesto de llamadas
            respuesta = "No pude completar tu solicitud: se agotaron las llamadas permitidas por conversación."

        turno = {
            "sesion_id": sesion_id,
            "respuesta": respuesta or "¿Puedo ayudarte con una cita?",
            "tools_usadas": tools_usadas,
            "ms": int((time.perf_counter() - t0) * 1000),
        }
        self._transcribir({**turno, "mensajes": mensajes})
        return turno

    def _system_prompt(self) -> str:
        from app.tools import SYSTEM_PROMPT

        return SYSTEM_PROMPT.replace("{hoy}", CONFIG.FIXED_TODAY)

    def _transcribir(self, registro: dict[str, Any]) -> None:
        """Observabilidad: un JSONL por sesión en harness/logs/."""
        try:
            os.makedirs(CONFIG.LOGS_DIR, exist_ok=True)
            path = os.path.join(
                CONFIG.LOGS_DIR, f"sesion-{registro['sesion_id']}.jsonl"
            )
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(registro, ensure_ascii=False) + "\n")
        except OSError:
            pass  # la demo no muere por un fallo de disco
