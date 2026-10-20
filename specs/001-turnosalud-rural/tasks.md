# Tareas y trazabilidad

Las pruebas de citas están implementadas en ms-citas/tests/test_citas.py; la integración completa espera los módulos del compañero. El harness y ms-agenda incluyen suites propias; la verificación final de evals es contra los MS reales (T-06).

| Estado | Tarea | Requisito | Responsable | Validación prevista |
|---|---|---|---|---|
| En curso | T-01 Revisar specs y cerrar decisiones | RF-1 a RF-6 | Ambos | PR feat/sebitas→main con D1-D6 (pendiente merge) |
| Completa | T-02 Médicos y disponibilidad | RF-3 | Josué | commit 7933fe8: 7 tests vitest+supertest verdes (health, contratos §4, 400/404) |
| Implementado | T-03 Reservar e idempotencia | RF-1, RF-4 | José | test_reserva_replay_and_payload_conflict, test_concurrent_reservations |
| Implementado | T-04 Listar y cancelar citas | RF-2 | José | test_cancel_rebook_and_original_replay, test_list_filters_pagination_and_cancelled, test_concurrent_cancellation |
| Implementado | T-05 Manejar caída de agenda | RF-5 | José | test_agenda_failures_do_not_persist |
| Parcial | T-06 Docker Compose e integración | RF-1 a RF-5 | José | BD/citas configurados; pendiente smoke con agenda real y evals E-01..E-07 reales |
| Completa | T-07 Harness y transcripts | RF-1, RF-2, RF-6 | Josué | 5 tests pytest verdes con fakes (E-01..E-07, memoria multi-turno, transcript JSONL, guardarráil). Verificación final contra MS reales en T-06 |
| Parcial | T-08 CI de servicios y harness | RF-1 a RF-6 | José | CI citas SQLite/PostgreSQL, OpenAPI, lint y Docker; gate agenda/harness al integrar módulos |
| Preparado | T-09 EC2, systemd y CD | Despliegue | José | Workflow y unidades; pendientes servidor, secretos y validación real |
| Pendiente | T-10 Demo y evidencias | RF-1 a RF-6 | Ambos | Guion, video y resultados de evaluaciones |
