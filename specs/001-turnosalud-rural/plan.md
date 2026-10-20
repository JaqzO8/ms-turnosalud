# Plan técnico inicial

La arquitectura, los contratos y el modelo de datos están definidos en las secciones 2, 4 y 5 del [plan maestro](../../PLAN_EXAMEN_TURNO_SALUD.md). Esta referencia evita duplicar contratos durante la preparación inicial.

## Componentes previstos

- ms-agenda: Node + Express + TypeScript, puerto 3001, agenda_db.
- ms-citas: Python + FastAPI, puerto 3002, citas_db.
- harness: Python, interfaz CLI o HTTP en 3003, herramientas HTTP y modo mock.
- Integración local: Docker Compose y PostgreSQL 16.
- Producción futura: EC2 Ubuntu, systemd y GitHub Actions por SSH.

## Decisiones que debe cerrar el equipo antes de implementar

- Replay idempotente: 200 con respuesta original; implementado y probado en el PR de citas.
- Cómo refleja agenda las reservas de citas sin acceder a su base de datos; el contrato inicial no define esta sincronización.
- Cómo descubre el harness los médicos si su registro solo permite las cuatro herramientas del plan.
- Cómo identificar y confirmar la cita a cancelar cuando un documento tiene varias citas.
- Ubicación de PostgreSQL en producción, migraciones y respaldo.
- Versiones definitivas de runtimes y dependencias, y fixtures de fecha reproducibles para las evaluaciones.

## Secuencia

Revisar las especificaciones juntos; implementar servicios con fakes; integrar; implementar el harness y las evaluaciones; agregar CI de pruebas; preparar CD y evidencias de AWS.

## Decisiones de citas y CI para revisión en este PR

- Se agregan payload_hash y respuesta_original al modelo interno para replay estable aun después de cancelar; el listado refleja el estado actual.
- Fecha pasada: anterior al día actual en America/Lima. Documento de ocho dígitos, UUID obligatorio y hora HH:MM. Listado requiere documento; size 1–100.
- Agenda 400/404: 422 VALIDACION. Timeout/error/respuesta inválida: 503 sin reservar. Franja no disponible o índice ocupado: 409 HORARIO_OCUPADO.
- Índice parcial y clave única protegen concurrencia; cancelación con actualización condicional atómica.
- Inicialización de BD idempotente para SQLite/PostgreSQL; futuras evoluciones requieren migraciones. OpenAPI exportado y comprobado por CI.
- Flujo solicitado: feat/* → develop → main. Deploy después de CI verde en main y configuración EC2 habilitada. Contrato propuesto para los entrypoints de agenda/harness en deploy/README.md.
- Sincronización de disponibilidad, integración real y evaluaciones del agente siguen pendientes; los fakes no las sustituyen.
