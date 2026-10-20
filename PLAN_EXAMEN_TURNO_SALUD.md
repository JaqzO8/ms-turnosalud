# PLAN DE EXAMEN — TURNO-SALUD RURAL (con Harness de Agente IA)

> Examen práctico grupal · Metodología SDD (Spec-Driven Development) · Microservicios ·
> GitHub Actions · Despliegue en AWS EC2 · Agente IA con tool-calling

## 0. Cómo leer este documento
Este es el plan maestro del equipo. Cada estudiante trabaja **de forma independiente
en su carpeta**, dentro de la misma repo. Los contratos de API y las tablas aquí
definidos son la fuente de verdad: NO negociarlos informalmente, solo vía PR o
decisión documentada en `specs/`. Al final está el checklist de Definition of Done
por rol.

**Integrantes:** José (ms-citas + infra/CI) · JOSUÉ (ms-agenda + harness)

## 1. Concepto (pitch de demo)
Gestión de citas médicas para centros de salud rural con un **recepcionista virtual IA**:
un agente LLM con *tool-calling* que consulta disponibilidad y reserva citas en lenguaje
natural, consumiendo **los mismos contratos OpenAPI** que verifican los tests E2E.
Frase clave para la demo: *"SDD de extremo a extremo: el contrato sirve a 3 consumidores
— los tests, otro microservicio y el agente IA"*.

## 2. Arquitectura
```
Usuario (español natural)
   │
   ▼
┌────────────────┐  tools (HTTP)   ┌─────────────────────┐
│ HARNESS/AGENTE │◄───────────────►│ ms-citas  :3002     │  Python + FastAPI
│ Python         │                 │ Citas (propias)     │  pytest
└────────────────┘                 └─────────┬───────────┘
        │                                    │ valida disponibilidad
        │        ┌─────────────────────┐     │ (HTTP al crear cita)
        └───────►│ ms-agenda :3001     │◄────┘
   médicos /     │ Node 20 + Express   │  vitest + supertest
   franjas       └─────────────────────┘
```
- Red Docker compartida `turno-salud-net` (nunca `http://localhost` entre contenedores).
- Un contenedor `db` (Postgres 16, puerto host 5433, convención de clase) con
  **dos bases de datos**: `agenda_db` y `citas_db` (cada MS es dueño de la suya;
  jamás consulta tablas del otro — solo vía HTTP).
- Errores SIEMPRE con la envolvente de clase:
  `{ "status": <http>, "code": "<negocio>", "message": "...", "correlation_id": "...", "timestamp": "..." }`
- `/health` en ambos MS; `/docs` con Swagger.

### Despliegue (producción, patrón catarata)
- **1 instancia EC2** Ubuntu 24.04 (free tier) con los 3 procesos: `ms-agenda`,
  `ms-citas` y `harness`, cada uno como servicio **systemd** (`EnvironmentFile`,
  `WorkingDirectory`, `Restart=always`) — NO Docker en la instancia (decisión RAM,
  igual que se descartó en catarata).
- **CD por GitHub Actions por SSH**: en cada push a `main` → job `test` (pytest +
  vitest verde) → job `deploy` (SSH: `git pull` → instalar dependencias → correr
  migraciones/seed → `systemctl restart` de los servicios).
- Secretos en la instancia vía `EnvironmentFile` (`GROQ_API_KEY`, URLs de BD);
  secrets de GitHub para el deply SSH (`SSH_HOST`, `SSH_USER`, `SSH_KEY`).
- **Preparar ANTES del examen** (no gastar horas de clase en esto si es posible):
  instancia EC2 lanzada + key pair + security group (22, 3001, 3002, 3003) +
  secrets de GitHub configurados + `EnvironmentFile` listo.
- Evidencia en `docs/`: URL pública, commit y run de Actions que desplegó.

## 3. Estructura del repo (monorepo) y dueños
```
ms-turnosalud/
├── specs/
│   ├── constitution.md                 ← co-redactada (ambos)
│   └── 001-turnosalud-rural/
│       ├── spec.md                     ← co-redactada
│       ├── plan.md                     ← co-redactada (contratos §4 vivos aquí)
│       └── tasks.md                    ← co-redactada, trazabilidad RF→task→test
├── ms-citas/           ← DUEÑO: JOSÉ    (Python FastAPI, pytest, SQLite en tests)
├── harness/            ← DUEÑO: JOSUÉ   (agente IA Python)
├── ms-agenda/          ← DUEÑO: JOSUÉ   (Node 20 + Express + TS, vitest + supertest)
├── docker-compose.yml  ← DUEÑO: JOSÉ    (+ Dockerfiles de ambos MS)
├── deploy/             ← DUEÑO: JOSÉ    (units systemd: agenda.service, citas.service, harness.service)
├── .github/workflows/ci.yml ← DUEÑO: JOSÉ  (pytest + vitest, verde antes de merge; deploy SSH a EC2)
├── docs/               ← demo.md (guión demo oral), diagramas, video de respaldo
└── README.md           ← co-redactado
```
**Reglas de convivencia en la repo**
- Nada se toca fuera de la propia carpeta (mínimo vital: si necesitas un cambio del
  otro, se pide por PR o se documenta en `plan.md`).
- Los contratos §4 están congelados desde el inicio de la codificación. Cualquier
  cambio requiere actualizar (1) `plan.md` y (2) los tests del dueño del MS.
- Branches: `main` (nunca roto, CI verde) + ramas `feat/...` personales.
- Secretos (`GROQ_API_KEY`, claves DB) NUNCA en el repo: `.env` + `.env.example`.

## 4. Contratos API (fuente de verdad, congelados)
### ms-agenda (:3001)
```json
GET  /api/v1/medicos
→ 200 [ { "id":"<uuid>", "nombre":"Dra. Quispe", "especialidad":"PEDIATRIA", "activo":true } ]

GET /api/v1/medicos/{id}/disponibilidad?fecha=YYYY-MM-DD
→ 200 { "medico_id":"<uuid>", "fecha":"2026-10-22",
        "franjas":[ { "inicio":"08:00","fin":"08:30","disponible":true },
                    { "inicio":"08:30","fin":"09:00","disponible":false } ] }
→ 404 si médico no existe · 400 si fecha inválida

GET /health → { "status":"ok" }
```
### ms-citas (:3002)
```json
POST /api/v1/citas          (header: Idempotency-Key: <uuid> OBLIGATORIA)
{ "paciente": { "nombre":"María Flores", "documento":"12345678" },
  "medico_id":"<uuid>", "fecha":"2026-10-22", "hora":"08:00" }
→ 201 { "cita": { "id":"<uuid>", "estado":"CONFIRMADA",
                  "medico_id":"<uuid>","fecha":"2026-10-22","hora":"08:00",
                  "paciente_nombre":"María Flores","documento":"12345678" } }
- Replay de idempotencia con mismo payload → mismos datos (200 o 201, decidir en tests);
  misma key con payload distinto → 409 IDEMPOTENCIA_CONFLICTO
- 409 HORARIO_OCUPADO (medico_id + fecha + hora ya reservada y CONFIRMADA)
- 422 VALIDACION (fuera de franja del médico, fecha pasada, campos faltantes)
- 503 AGENDA_NO_DISPONIBLE (ms-agenda caído → fallback razonable documentado)

POST /api/v1/citas/{id}/cancelar
→ 200 { "cita": { ... "estado":"CANCELADA" } }   · 404 no existe · 409 ya cancelada

GET  /api/v1/citas?documento=12345678&page=1&size=10
→ 200 { "items":[...], "page":1, "size":10, "total":n }

GET /health, GET /docs
```
### harness (CLI o :3003)
```
POST /chat          { "mensaje":"...", "sesion_id":"..." } → { "respuesta":"...", "tools_usadas":[...] }
GET  /evals         → corre E-01..E-05 y devuelve [ { "id":"E-01", "prompt":"...", "esperado":"...", "obtenido":"...", "ok":true } ]
```

## 5. Modelo de datos (cada MS dueño de SUS tablas)
**ms-agenda (agenda_db)**
```sql
medicos ( id UUID PK, nombre TEXT NOT NULL, especialidad TEXT NOT NULL
          CHECK (especialidad IN ('PEDIATRIA','MEDICINA_GENERAL','ODONTOLOGIA')),
          activo BOOLEAN DEFAULT true );

franjas_horarias ( id UUID PK, medico_id UUID REFERENCES medicos(id),
                   dia_semana SMALLINT CHECK (dia_semana BETWEEN 0 AND 6), -- 0 = lunes
                   hora_inicio TIME, hora_fin TIME );  -- franjas de 30 min, según seed
```
**ms-citas (citas_db)**
```sql
citas ( id UUID PK,
        medico_id UUID NOT NULL,
        fecha DATE NOT NULL, hora TIME NOT NULL,
        estado TEXT NOT NULL DEFAULT 'CONFIRMADA'
          CHECK (estado IN ('CONFIRMADA','CANCELADA')),
        paciente_nombre TEXT NOT NULL, documento CHAR(8) NOT NULL,
        idempotency_key UUID NOT NULL UNIQUE,
        creado_en TIMESTAMPTZ DEFAULT now() );

CREATE UNIQUE INDEX uq_cita_medico_horario
  ON citas (medico_id, fecha, hora) WHERE estado = 'CONFIRMADA';
```
El índice único parcial es el guardián anti doble-reserva a nivel BD (el agente LLM
puede invocar la tool dos veces — la idempotencia lo absorbe). Demostrarlo en la demo.

## 6. Harness de agente IA (resumen formal)
- **LLM**: Groq (`console.groq.com`, key gratuita; API compatible con OpenAI →
  `base_url = https://api.groq.com/openai/v1`). Fallback: Gemini Flash (AI Studio).
  Plan B offline: `MOCK_LLM=true` (respuestas programadas, la demo no muere).
- **Componentes mínimos del harness** (definición formal para el docente):
  1. *Registro de tools* generado de los contratos §4 (JSON Schema por tool:
     `ver_disponibilidad`, `reservar_cita`, `cancelar_cita`, `listar_citas`)
  2. *Loop del agente*: interpretar → llamar tool(s) → observar resultado → responder
  3. *Guardrails*: solo esas 4 tools, timeouts HTTP, máx. 5 llamadas por conversación
  4. *Observabilidad*: transcript de cada conversación (mensajes + tools + ms) en `harness/logs/`
  5. *Eval suite* E-01..E-05:
     - E-01 "quiero cita con pediatría el jueves a las 8" → reserva CONFIRMADA
     - E-02 franja ya ocupada → no reserva y comunica alternativas
     - E-03 médico inexistente → no llama a la tool de reserva, respuesta honesta
     - E-04 cancela por documento → estado CANCELADA
     - E-05 pregunta fuera de dominio (ej. "¿clima?") → no llama a ninguna tool
  (La eval suite = tests E2E del agente; corre sin red si `MOCK_LLM=true`.)
- **Persona del agente**: "recepcionista del centro de salud rural", español, sin
  prometer datos clínicos que no existen en el sistema.

## 7. Historias de Usuario y RF (semilla para spec.md)
- HU-1 Como paciente, quiero pedir una cita por lenguaje natural → cita CONFIRMADA.
- HU-2 Como paciente, quiero cancelar mi cita con mi documento → CANCELADA.
- HU-3 Como recepcionista, quiero ver la disponibilidad de los médicos del día.
- HU-4 Como sistema, debo impedir doble reserva (409 + índice único).
- HU-5 Como sistema, debo tolerar que ms-agenda esté caído (503 controlado).
- HU-6 Como docente, quiero ver cada conversación del agente en un transcript.
- RF-1..RF-6 mapean a HU-1..HU-6 + trazabilidad RF→task→test en tasks.md.
- Fuera de alcance (decisiones descartadas): autenticación JWT, pagos, ML, kubernetes.

## 8. Fases y reparto
| Fase | Qué | Quién | Definition of Done |
|---|---|---|---|
| A | constitution + spec + contratos §4 | ambos | specs en `main` antes de codificar |
| B1 | ms-agenda + tests + fakes | JOSUÉ | vitest verde; contratos respetados |
| B2 | ms-citas (usa fakes de agenda) + tests | José | pytest verde; idempotencia demostrada |
| C | docker-compose integración real | José | smoke: crear cita real end-to-end |
| D | harness: loop + tools + evals | JOSUÉ | E-01..E-05 verdes (mock/real) |
| E | CI + demo.md + video de respaldo | José (CI), ambos (demo) | Actions verde; demo lista |
| F | EC2: systemd de los 3 procesos + CD por Actions (SSH) | José (deploy), ambos (verificación) | URL pública respondiendo; run verde de Actions con deploy; evidencia en `docs/` |

## 9. Guión demo oral (5 min)
1. SDD: constitution → spec → tasks + trazabilidad (90 s)
2. "El contrato sirve a 3 consumidores" (60 s)
3. Demo viva: prompt en español → tools → cita CONFIRMADA verificada en BD (90 s)
4. Casos negativos: franja ocupada → el agente ofrece alternativa (60 s)
5. Evals E-01..E-05 verdes + CI de GitHub Actions verde (60 s)
6. Cierre: push → Actions verde → app viva en la URL pública de EC2 (30 s)
