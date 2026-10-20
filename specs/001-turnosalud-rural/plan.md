# Plan técnico inicial

La arquitectura, los contratos y el modelo de datos están definidos en las secciones 2, 4 y 5 del [plan maestro](../../PLAN_EXAMEN_TURNO_SALUD.md). Esta referencia evita duplicar contratos durante la preparación inicial.

## Componentes previstos

- ms-agenda: Node + Express + TypeScript, puerto 3001, agenda_db.
- ms-citas: Python + FastAPI, puerto 3002, citas_db.
- harness: Python, interfaz CLI o HTTP en 3003, herramientas HTTP y modo mock.
- Integración local: Docker Compose y PostgreSQL 16.
- Producción futura: EC2 Ubuntu, systemd y GitHub Actions por SSH.

## Decisiones cerradas en T-01 (PR de decisiones)

- **D1 · Replay idempotente**: primera emisión → `201`. Replay con la misma
  `Idempotency-Key` y el mismo payload → `200` con el mismo body. Misma key con
  payload distinto → `409 IDEMPOTENCIA_CONFLICTO`. Se fija con pytest (replay,
  conflicto y concurrencia).
- **D2 · Sincronización agenda↔citas**: no existe. `ms-agenda` es dueño de la
  agenda_db (médicos + franjas base). La disponibilidad efectiva la calcula
  `ms-citas` con su índice único parcial sobre su citas_db (RF-4): al crear una
  cita valida que fecha/hora caiga en una franja del médico (422 si no) y que no
  exista otra cita CONFIRMADA (409 HORARIO_OCUPADO). En el contrato, `ms-agenda`
  devuelve las franjas base con `"disponible": true`; ese campo es informativo —
  la autoridad de ocupación es `ms-citas`.
- **D3 · Descubrimiento de médicos en el harness**: se agrega una **5ª tool**
  `listar_medicos` (GET /api/v1/medicos). Enmienda al plan maestro (§4/§6 ya
  actualizados en este mismo PR).
- **D4 · Cancelar por documento con varias citas**: el harness llama
  `listar_citas(documento)` y filtra CONFIRMADA. Si hay 1 → cancela directo;
  si hay varias → pregunta al usuario (médico/fecha/hora) y cancela la elegida;
  si hay 0 → informa que no hay citas activas. La API mantiene Cancelar por id.
- **D5 · PostgreSQL en producción**: PostgreSQL 16 instalado en la misma
  instancia EC2 (las migraciones corren en el job de deploy). El respaldo queda
  fuera de alcance del examen (decisión descartada, documentada).
- **D6 · Versiones y fechas reproducibles**: Node 20 LTS + TypeScript + Express
  + vitest/supertest; Python 3.11 + FastAPI 0.115 + pytest + httpx (versiones
  fijadas en los Dockerfiles y en los requirements/package.json de la entrega). Fechas reproducibles: env
  `FIXED_TODAY` (por defecto lunes `2026-11-02` = dia_semana 0) usado por el
  harness/evals y los fixtures de tests. Seed de franjas: lunes a viernes
  08:00-17:00 cada 30 min.

## Secuencia

Revisar las especificaciones juntos; implementar servicios con fakes; integrar; implementar el harness y las evaluaciones; agregar CI de pruebas; preparar CD y evidencias de AWS.
