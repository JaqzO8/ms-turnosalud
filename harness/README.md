# harness — Recepcionista IA del centro de salud rural

Dueño: **Josué**. Python 3.11 + FastAPI. Puerto `3003`. Agente LLM con *tool-calling* que
reserva/consulta/cancela citas consumiendo los contratos §4 de `ms-agenda` (3001) y `ms-citas` (3002).

## Componentes del harness (definición formal)
1. **Registro de tools** (5, decisión D3): `listar_medicos`, `ver_disponibilidad`, `reservar_cita`,
   `cancelar_cita`, `listar_citas` — JSON Schemas en `tools.py`, generados del contrato §4
2. **Loop del agente** (`agent.py`): interpretar → tool(s) → observar → responder, con
   **memoria conversacional por `sesion_id`** (multi-turno)
3. **Guardarráiles**: solo las 5 tools, timeout HTTP configurable, máx. `MAX_TOOL_CALLS=5` llamadas/conversación
4. **Observabilidad**: transcript JSONL por sesión en `harness/logs/`
5. **Eval suite** (`evals.py`, tests E2E del agente):
   - E-01 reserva exitosa → CONFIRMADA
   - E-02 doble reserva → reusa la franja ocupada (409) y ofrece alternativas
   - E-03 especialidad sin médico → respuesta honesta, sin reservar
   - E-04 cancelación por documento → CANCELADA
   - E-05 fuera de dominio (clima) → sin tools
   - E-06 datos incompletos → **PREGUNTA** por el dato faltante (sin tools)
   - E-07 reserva multi-turno con memoria de sesión (4 rondas → CONFIRMADA)

## LLM
- **Groq** (key gratuita en **console.groq.com**); API compatible con OpenAI: solo se cambia
  `LLM_BASE_URL`. Modelo por defecto `llama-3.3-70b-versatile` (soporta tool-calling).
- **MOCK_LLM=true** (default): agente determinístico multivuelo sin red — la demo no muere si falla internet.
  Flujo: si faltan datos (especialidad → fecha → hora → nombre/documento; documento al cancelar) PREGUNTA.

## API HTTP
```
GET  /health                          → {status, mock_llm, fixed_today}
POST /chat { "mensaje", "sesion_id" } → { respuesta, tools_usadas, sesion_id, ms }
GET  /evals                           → { provider, total, ok, resultados[E-01..E-07] }
```

## Ejecutar
```bash
pip install -r requirements.txt
python -m pytest tests -q          # 5 tests con fakes, sin red: SHOULDS pass
uvicorn app:app --port 3003        # API del agente
# modo real: GROQ_API_KEY=tukey, MOCK_LLM=false (o .env)
```

En compose: `MOCK_LLM` + `MS_AGENDA_URL=http://ms-agenda:3001`, `MS_CITAS_URL=http://ms-citas:3002`
(nunca `localhost` entre contenedores).
