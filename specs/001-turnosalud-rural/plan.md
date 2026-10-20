# Plan técnico inicial

La arquitectura, los contratos y el modelo de datos están definidos en las secciones 2, 4 y 5 del [plan maestro](../../PLAN_EXAMEN_TURNO_SALUD.md). Esta referencia evita duplicar contratos durante la preparación inicial.

## Componentes previstos

- ms-agenda: Node + Express + TypeScript, puerto 3001, agenda_db.
- ms-citas: Python + FastAPI, puerto 3002, citas_db.
- harness: Python, interfaz CLI o HTTP en 3003, herramientas HTTP y modo mock.
- Integración local: Docker Compose y PostgreSQL 16.
- Producción futura: EC2 Ubuntu, systemd y GitHub Actions por SSH.

## Decisiones que debe cerrar el equipo antes de implementar

- Respuesta del replay idempotente: elegir 200 o 201 y fijarla en tests.
- Cómo refleja agenda las reservas de citas sin acceder a su base de datos; el contrato inicial no define esta sincronización.
- Cómo descubre el harness los médicos si su registro solo permite las cuatro herramientas del plan.
- Cómo identificar y confirmar la cita a cancelar cuando un documento tiene varias citas.
- Ubicación de PostgreSQL en producción, migraciones y respaldo.
- Versiones definitivas de runtimes y dependencias, y fixtures de fecha reproducibles para las evaluaciones.

## Secuencia

Revisar las especificaciones juntos; implementar servicios con fakes; integrar; implementar el harness y las evaluaciones; agregar CI de pruebas; preparar CD y evidencias de AWS.
