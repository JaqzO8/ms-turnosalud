# ms-agenda

Microservicio de médicos y franjas horarias. Dueño: **Josué** (Node 20 + Express + TypeScript, vitest + supertest). Puerto `3001`, base `agenda_db`. Contratos: §4 del plan maestro y `specs/001-turnosalud-rural/plan.md`.

## Endpoints
- `GET /health` → `{ "status": "ok" }`
- `GET /api/v1/medicos` → lista de médicos `{ id, nombre, especialidad, activo }`
- `GET /api/v1/medicos/{id}/disponibilidad?fecha=YYYY-MM-DD` → franjas base de 30 min (decisión D2: `disponible` informativo, la autoridad de ocupación es `ms-citas`)
- Errores con envolvente de clase: `{ status, code, message, correlation_id, timestamp }` + header `X-Correlation-Id`

## Tablas (agenda_db)
`medicos`, `franjas_horarias` — DDL + seed idempotente al arrancar (5 médicos, lunes-vie 08:00-17:00, slots de 30 min en runtime).

## Ejecutar
```bash
npm install
npm run dev        # DRIVER=memory si no hay DATABASE_URL (dev rápido)
npm test           # vitest + supertest (7 tests)
npm run build && npm start
```

Con Postgres: exporta `DATABASE_URL=postgresql://agenda:agenda@db:5432/agenda_db` y `DRIVER=pg`.
