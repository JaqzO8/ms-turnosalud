# Cliente LLM: Groq (API compatible OpenAI) con fallback MOCK para demo sin red.
# Comportamiento pedido: si faltan datos (especialidad/fecha/hora/nombre/documento),
# el agente PREGUNTA antes de usar tools (multi-turno con memoria de sesión).
import json
import random
import re
from typing import Any

from config import CONFIG


class LLMRespuesta:
    def __init__(self, texto: str | None = None, tool_calls: list[dict[str, Any]] | None = None):
        self.texto = texto
        self.tool_calls = tool_calls or []


class MockLLM:
    """
    LLM determinístico (MOCK_LLM=true): heurística en español multivuelo.
    Pide datos faltantes de la cita en orden: especialidad -> fecha -> hora ->
    nombre/documento. Sin red. Para producción: GROQ_API_KEY + MOCK_LLM=false.
    """

    ESPECIALIDADES = {
        "pediatr": "PEDIATRIA",
        "medicina general": "MEDICINA_GENERAL",
        "odontolog": "ODONTOLOGIA",
    }

    PREG_ESP = "Claro que sí. ¿Con qué especialidad necesitas la cita: pediatría, medicina general u odontología?"
    PREG_FECHA = "Perfecto. ¿Para qué fecha necesitas la cita? (formato AAAA-MM-DD)"
    PREG_HORA = "¿A qué hora? Tenemos franjas de 30 minutos desde las 08:00."
    PREG_PACIENTE = "Para reservar necesito tu nombre completo y tu documento de identidad (8 dígitos)."
    PREG_DOC = "¿Cuál es tu documento de identidad (8 dígitos) para localizar tu cita?"

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LLMRespuesta:
        all_user = "\n".join(m["content"] for m in messages if m["role"] == "user")
        low = all_user.lower()
        tool_msgs = [m for m in messages if m["role"] == "tool"]
        last = json.loads(tool_msgs[-1]["content"]) if tool_msgs else None

        if "clima" in low:
            return LLMRespuesta(
                texto="Lo siento, solo puedo ayudarte con citas del centro de salud: reservar, consultar o cancelar."
            )

        # ---- CANCELAR: doc faltante -> PREGUNTA; luego listar_citas -> cancelar_cita
        if "cancelar" in low:
            if last is None:
                doc = re.search(r"\b(\d{8})\b", all_user)
                if not doc:
                    return LLMRespuesta(texto=self.PREG_DOC)
                return LLMRespuesta(tool_calls=[self._tc("listar_citas", {"documento": doc.group(1)})])
            if last.get("ok") and last.get("tool") == "cancelar_cita":
                cita = (last["result"] or {}).get("cita") or {}
                return LLMRespuesta(
                    texto=f"Listo, tu cita quedó {cita.get('estado')}. Si necesitas otra, dime el día y la hora y te reservo."
                )
            if last.get("ok"):
                activas = [c for c in (last["result"].get("items") or []) if c.get("estado") == "CONFIRMADA"]
                if activas:
                    c = activas[0]
                    return LLMRespuesta(tool_calls=[self._tc("cancelar_cita", {"cita_id": c["id"]})])
                return LLMRespuesta(texto="No encontré citas activas con ese documento. ¿Deseas reservar una nueva?")
            if last.get("code") == "AGENDA_NO_DISPONIBLE":
                return LLMRespuesta(texto="Ahora mismo no puedo consultar el sistema de citas. ¿Intentamos más tarde?")
            return LLMRespuesta(texto="No pude procesar la cancelación. Verifica tu documento.")

        # ---- RESERVAR: completar datos ANTES de tocar las tools
        if last is None:
            return self._si_faltan_datos(all_user) or LLMRespuesta(
                tool_calls=[self._tc("listar_medicos", {})]
            )

        if last.get("tool") == "listar_medicos":
            if not last.get("ok"):
                return LLMRespuesta(texto="No puedo consultar la lista de médicos en este momento (agenda no disponible).")
            esp = self._especialidad(all_user)
            medico = next((m for m in last["result"] if m["especialidad"] == esp), None)
            if not medico:
                return LLMRespuesta(
                    texto=f"No tengo hoy un médico de {esp or 'esa especialidad'}. ¿Deseas otra alternativa?"
                )
            m_fecha = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", all_user)
            fecha = m_fecha.group(1) if m_fecha else CONFIG.FIXED_TODAY
            return LLMRespuesta(
                tool_calls=[self._tc("ver_disponibilidad", {"medico_id": medico["id"], "fecha": fecha})]
            )

        if last.get("tool") == "ver_disponibilidad":
            if not last.get("ok"):
                if last.get("code") == "AGENDA_NO_DISPONIBLE":
                    return LLMRespuesta(texto="El sistema de agenda no responde en este momento. ¿Intentamos más tarde?")
                return LLMRespuesta(texto="No pude consultar la disponibilidad. Verifica los datos.")
            slots = last["result"].get("franjas") or []
            hora = self._hora(all_user)
            slot = next((s for s in slots if hora and s["inicio"].startswith(hora)), None)
            if not slot:
                hay = ", ".join(s["inicio"] for s in slots[:5]) or "ninguna"
                return LLMRespuesta(texto=f"Para esa fecha no hay franja a las {hora or 'esa hora'}. Franjas libres: {hay}...")
            nombre, doc = self._paciente(all_user)
            return LLMRespuesta(
                tool_calls=[
                    self._tc(
                        "reservar_cita",
                        {
                            "paciente": {"nombre": nombre, "documento": doc},
                            "medico_id": last["result"]["medico_id"],
                            "fecha": last["result"]["fecha"],
                            "hora": slot["inicio"],
                        },
                    )
                ]
            )

        if last.get("tool") == "reservar_cita":
            if last.get("ok"):
                cita = last["result"].get("cita") or {}
                return LLMRespuesta(
                    texto=f"Listo, tu cita quedó {cita.get('estado')} para el {cita.get('fecha')} a las {cita.get('hora')}. Código de cita: {cita.get('id')}."
                )
            if last.get("code") == "HORARIO_OCUPADO":
                return LLMRespuesta(texto="Esa franja acaba de ocuparse. ¿Te reservo otra hora disponible?")
            if last.get("code") == "AGENDA_NO_DISPONIBLE":
                return LLMRespuesta(texto="El sistema no está disponible ahora mismo. ¿Intentamos más tarde?")
            return LLMRespuesta(texto=f"No pude reservar la cita ({last.get('code', 'VALIDACION')}). Verifica los datos.")

        return LLMRespuesta(texto="¿Puedo ayudarte con una cita: reservar, consultar o cancelar?")

    # ---- helpers de datos
    def _si_faltan_datos(self, all_user: str) -> LLMRespuesta | None:
        if not self._especialidad(all_user):
            return LLMRespuesta(texto=self.PREG_ESP)
        if not re.search(r"\b(\d{4}-\d{2}-\d{2})\b", all_user):
            return LLMRespuesta(texto=self.PREG_FECHA)
        if not self._hora(all_user):
            return LLMRespuesta(texto=self.PREG_HORA)
        nombre, doc = self._paciente(all_user)
        if not doc:
            return LLMRespuesta(texto=self.PREG_PACIENTE)
        return None

    def _especialidad(self, all_user: str) -> str | None:
        low = all_user.lower()
        for k, v in self.ESPECIALIDADES.items():
            if k in low:
                return v
        return None

    def _hora(self, all_user: str) -> str | None:
        m = re.search(r"a las\s+(\d{1,2})(?::(\d{2}))?", all_user, re.IGNORECASE)
        if not m:
            return None
        h, mn = int(m.group(1)), m.group(2) or "00"
        return f"{h:02d}:{mn}"

    def _paciente(self, all_user: str) -> tuple[str, str]:
        m = re.search(r"soy\s+([A-ZÁÉÍÓÚÑa-záéíóúñ ]+?)\s*,?\s*documento\s+(\d{8})", all_user, re.IGNORECASE)
        if m:
            return m.group(1).strip(), m.group(2)
        generic = re.search(r"\b(\d{8})\b", all_user)
        return "Paciente Sin Nombre", (generic.group(1) if generic else "00000000")

    def _tc(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": f"call_{random.randint(1000, 9999)}",
            "type": "function",
            "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)},
        }


class GroqLLM:
    """LLM real (MOCK_LLM=false) vía API compatible OpenAI apuntada a Groq."""

    def __init__(self):
        if not CONFIG.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY no definida; usa MOCK_LLM=true o configura la key")
        from openai import OpenAI  # importación perezosa

        self._client = OpenAI(base_url=CONFIG.LLM_BASE_URL, api_key=CONFIG.GROQ_API_KEY)

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LLMRespuesta:
        resp = self._client.chat.completions.create(
            model=CONFIG.LLM_MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=600,
        )
        choice = resp.choices[0]
        tcs = []
        for call in getattr(choice.message, "tool_calls", None) or []:
            tcs.append(
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.function.name, "arguments": call.function.arguments},
                }
            )
        return LLMRespuesta(texto=choice.message.content, tool_calls=tcs)


def crear_llm():
    return MockLLM() if CONFIG.MOCK_LLM or not CONFIG.GROQ_API_KEY else GroqLLM()
