# ms-citas

Módulo de José implementado con FastAPI, SQLAlchemy, SQLite local y PostgreSQL 16 en CI.

## Ejecutar (Python 3.13, desde ms-citas)

```powershell
py -3.13 -m venv .venv
.venv/Scripts/python -m pip install -r requirements.lock
$env:DATABASE_URL = 'sqlite:///./citas.db'
$env:AGENDA_URL = 'http://localhost:3001'
.venv/Scripts/python -m app.db
.venv/Scripts/python -m uvicorn app.main:create_app --factory --port 3002
```

Linux: usar `.venv/bin/python`. Las variables se leen del entorno; `.env.example` no se carga automáticamente. Swagger en http://localhost:3002/docs y contrato versionado en [openapi.json](openapi.json). `/health` verifica conexión a BD.

## Funciones

- POST `/api/v1/citas`: requiere Idempotency-Key UUID; crea con 201. Cuerpo: paciente (nombre/documento), medico_id UUID, fecha YYYY-MM-DD y hora HH:MM.
- Replay: 200 con respuesta original incluso después de cancelar; consultar listado para estado actual. Misma clave con otros datos: 409 IDEMPOTENCIA_CONFLICTO.
- Índice único parcial impide doble reserva concurrente. Cancelar libera el horario.
- POST `/api/v1/citas/{id}/cancelar`: 200, 404 si no existe, 409 si ya cancelada.
- GET `/api/v1/citas?documento=12345678&page=1&size=10`: documento obligatorio, size 1–100, incluye canceladas, orden por fecha/hora/id.
- Validación: fecha no anterior al día actual en America/Lima, documento de ocho dígitos, nombre no vacío y hora al inicio de una franja de agenda.
- Agenda se consulta por HTTP con timeout. Ante caída o respuesta inválida: 503 sin persistir. No existe fallback que invente disponibilidad.
- Errores uniformes con correlation_id; X-Correlation-ID UUID se propaga a agenda.

## Pruebas

```powershell
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m ruff check app tests
```

Agenda HTTP simulada y reloj fijo, sin claves externas. CI repite la suite contra SQLite y PostgreSQL. TEST_DATABASE_URL debe señalar una BD desechable: las pruebas recrean las tablas.

requirements.lock fija las dependencias verificadas, incluidas herramientas de test. app.db inicializa el esquema; cambios futuros requieren migraciones versionadas. No usar datos reales de pacientes en esta demo sin autenticación.
