# Turno-Salud Rural

Gestión de citas médicas para centros de salud rural con un recepcionista virtual IA y desarrollo guiado por especificaciones (SDD).

## Estado inicial

ms-citas implementa reservas, cancelaciones, listado e idempotencia con pruebas automatizadas. Agenda y harness esperan integración. GitHub Actions valida el módulo y prepara el despliegue conjunto a EC2.

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
3. Trabajar en `feat/jose` o `feat/sebitas`, incorporando los avances de `develop`.
4. Implementar las tareas de la carpeta asignada con sus pruebas y actualizar la trazabilidad.
5. Abrir un PR hacia `develop`. Cuando el conjunto esté validado, abrir un PR `develop → main`.

No subir credenciales ni datos reales de pacientes. Cada servicio debe documentar sus variables en `.env.example` cuando se implemente.

## AWS

Ver [ejecución de citas](ms-citas/README.md) y [preparación de EC2 y flujo de despliegue](deploy/README.md). AWS aún no está configurado ni desplegado.
