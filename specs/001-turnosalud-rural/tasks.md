# Tareas y trazabilidad

Todas las pruebas indicadas son propuestas y aún no están implementadas.

| Estado | Tarea | Requisito | Responsable | Validación prevista |
|---|---|---|---|---|
| En curso | T-01 Revisar specs y cerrar decisiones | RF-1 a RF-6 | Ambos | PR feat/sebitas→main con D1-D6 (pendiente merge) |
| Completa | T-02 Médicos y disponibilidad | RF-3 | Josué | commit 7933fe8: 7 tests vitest+supertest verdes (health, contratos §4, 400/404) |
| Pendiente | T-03 Reservar e idempotencia | RF-1, RF-4 | José | pytest, replay D1, conflicto y concurrencia |
| Pendiente | T-04 Listar y cancelar citas | RF-2 | José | pytest, paginación, 404 y cancelación repetida |
| Pendiente | T-05 Manejar caída de agenda | RF-5 | José | pytest con timeout y error 503 |
| Pendiente | T-06 Docker Compose e integración | RF-1 a RF-5 | José | Smoke de reserva entre servicios; evals E-01..E-07 reales |
| Completa | T-07 Harness y transcripts | RF-1, RF-2, RF-6 | Josué | 5 tests pytest verdes con fakes (E-01..E-07, memoria multi-turno E-06/E-07, transcript JSONL, guardarráil). Verificación final contra MS reales en T-06 |
| Pendiente | T-08 CI de servicios y harness | RF-1 a RF-6 | José | GitHub Actions: vitest (ms-agenda) + pytest (ms-citas y harness) |
| Pendiente | T-09 EC2, systemd y CD | Despliegue | José | Health checks y evidencia del commit desplegado |
| Pendiente | T-10 Demo y evidencias | RF-1 a RF-6 | Ambos | Guion, video y resultados de evaluaciones |
