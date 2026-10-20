# Turno-Salud Rural

Gestión de citas médicas para centros de salud rural con un recepcionista virtual IA y desarrollo guiado por especificaciones (SDD).

## Estado inicial

Repositorio preparado para trabajo colaborativo. Los servicios, tests y despliegue todavía están pendientes de implementación.

El [plan maestro](PLAN_EXAMEN_TURNO_SALUD.md) contiene el alcance, los contratos API, el modelo de datos, las evaluaciones del agente y el reparto de trabajo.

## Organización

| Carpeta | Responsabilidad según el plan |
|---|---|
| `specs/` | Especificaciones y decisiones compartidas |
| `ms-citas/` | José: FastAPI, reservas, cancelaciones e idempotencia |
| `ms-agenda/` | Josué: Express + TypeScript, médicos y franjas |
| `harness/` | Josué: agente, herramientas y evaluaciones |
| `deploy/` | José: futura infraestructura y despliegue EC2 |
| `docs/` | Evidencias y guion de demostración |

## Colaborar

1. Aceptar la invitación de GitHub y clonar `https://github.com/JaqzO8/ms-turnosalud.git`.
2. Revisar `specs/constitution.md` y completar las decisiones pendientes de `specs/001-turnosalud-rural/plan.md` antes de implementar.
3. Crear una rama personal `feat/<funcionalidad>` desde `main`.
4. Implementar las tareas de la carpeta asignada con sus pruebas y actualizar la trazabilidad.
5. Abrir un pull request para revisión del compañero antes de integrar a `main`.

No subir credenciales ni datos reales de pacientes. Cada servicio debe documentar sus variables en `.env.example` cuando se implemente.

## AWS

El destino previsto es EC2 con servicios systemd y CD por SSH desde GitHub Actions, según el plan adjunto. La configuración de AWS y el despliegue se realizarán en una fase posterior; este repositorio aún no contiene una aplicación ejecutable.
