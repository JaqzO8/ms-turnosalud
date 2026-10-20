# harness — Recepcionista IA del centro de salud rural

Dueño: **Josué**. Python 3.11 + FastAPI + uvicorn (`app.main:app`). Puerto `3003`. Agente LLM con
*tool-calling* que reserva/consulta/cancela citas consumiendo los contratos §4 de `ms-agenda` (3001)
y `ms-citas` (3002). **Sirve un mini-frontend de chat en `GET /`** (la demo se muestra así).

## Estructura
```
app/
  config.py     # envs: GROQ_API_KEY, MOCK_LLM, MS_*_URL, MAX_TOOL_CALLS, FIXED_TODAY
  tools.py      # 5 tools (D3) con JSON Schema + envolvente de errores ToolError
  llm.py        # MockLLM determinístico (sin red) | GroqLLM (API OpenAI-compatible)
  agent.py      # loop + memoria conversacional por sesion_id + transcript JSONL
  evals.py      # eval suite E-01..E-07 (E2E del agente)
  main.py       # FastAPI: /health /chat /evals + UI estática en /
  static/index.html
tests/          # fakes.py + test_agente / test_api / test_tools_http / test_llm_groq
```

## Componentes del harness (definición formal)
1. **Registro de tools** (5): `listar_medicos`, `ver_disponibilidad`, `reservar_cita`, `cancelar_cita`, `listar_citas`
2. **Loop del agente**: interpretar → tool(s) → observar → responder, con **memoria por `sesion_id`** (multi-turno)
3. **Guardarráiles**: solo las 5 tools, `HTTP_TIMEOUT_MS`, máx. `MAX_TOOL_CALLS=5` por conversación
4. **Observabilidad**: transcript JSONL por sesión en `harness/logs/`
5. **Eval suite** (tests E2E del agente):
   - E-01 reserva completa → CONFIRMADA
   - E-02 doble reserva → 409, rehusa + alternativas
   - E-03 especialidad sin médico → respuesta honesta sin reservar
   - E-04 cancelación por documento → CANCELADA
   - E-05 fuera de dominio (clima) → sin tools
   - E-06 datos incompletos → **PREGUNTA** por el dato faltante (sin tools)
   - E-07 reserva multi-turno (4 rondas, misma sesión → CONFIRMADA)

## LLM
- **Groq** (key gratuita en **console.groq.com**); API compatible OpenAI — solo se cambia `LLM_BASE_URL`.
- **MOCK_LLM=true** (default): agente determinístico sin red; la demo nunca muere. Si faltan datos
  (especialidad → fecha → hora → nombre/documento; documento al cancelar) **pregunta** al usuario.

## Calidad (gate CI de José)
```
ruff check app tests --select E4,E7,E9,F,I,B,UP   → 0 errores
ruff format --check app tests                     → ok
python -m pytest -q --cov=app --cov-branch --cov-fail-under=80  → 26 tests, 83.7% ✓
```

## Ejecutar
```bash
pip install -r requirements.lock
python -m pytest -q                  # suite completa con fakes, sin red
uvicorn app.main:app --port 3003     # http://localhost:3003 → chat UI
# modo real: GROQ_API_KEY=tukey en .env (copiar .env.example) y MOCK_LLM=false
```

En compose (contenedor): `MOCK_LLM`, `MS_AGENDA_URL=http://ms-agenda:3001`,
`MS_CITAS_URL=http://ms-citas:3002` — **nunca** `localhost` entre contenedores.
