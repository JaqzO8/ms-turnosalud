# ms-agenda — Médicos y disponibilidad

Dueño: **Josué**. Node 20 LTS + Express + TypeScript. Puerto `3001`, base `agenda_db`.
Contratos: §4 del plan maestro y `specs/001-turnosalud-rural/plan.md`. Estructura `src/`, tests en `tests/` (vitest + supertest).

## Estado (T-02 completa)
- **7/7 tests verdes**, cobertura **98.7% líneas** (gate CI ≥ 80%)
- `npm run lint` (eslint typescript) y `npm run format:check` (prettier) ✓
- `npm run build` → `dist/server.js` (lo exige el CI) ✓

## Endpoints
- `GET /health` → `{ "status": "ok" }`
- `GET /api/v1/medicos` → `{ id, nombre, especialidad, activo }[]`
- `GET /api/v1/medicos/{id}/disponibilidad?fecha=YYYY-MM-DD` → franjas base de 30 min
  (decisión D2: `disponible` informativo; la autoridad de ocupación es `ms-citas` — índice único)
- Errores con envolvente de clase `{ status, code, message, correlation_id, timestamp }` + header `X-Correlation-Id`

## Tablas (agenda_db)
`medicos`, `franjas_horarias`. Seed idempotente: 5 médicos (Pediatria / Medicina General ×2 / Odontología ×2),
lunes-viernes 08:00-17:00, slots de 30 min calculados en runtime.

## Ejecutar
```bash
npm install
npm run dev          # sin DATABASE_URL arranca DRIVER=memory (sin BD)
npm test             # vitest + supertest
npm run lint         # eslint
npm run format:check # prettier
./scripts/migrate.sh # DDL + seed contra DATABASE_URL (pedida por el release gate)
npm run build && npm start
```

Docker: `ms-agenda/Dockerfile` (node:20-alpine, build → `node dist/server.js`), listo para que
José lo monte en `docker-compose.yml` como `ms-agenda` en `:3001` con `DATABASE_URL=postgresql://turnosalud:<pw>@db:5432/agenda_db`.
