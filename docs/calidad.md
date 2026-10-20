# Criterio de aceptación de cambios

El 80% significa cobertura automatizada del código de aplicación, no una calificación subjetiva ni que pueda fallar el 20% de los tests. Todos los tests y controles de buenas prácticas deben pasar.

| Control | Aceptación |
|---|---|
| Citas | Cobertura total de líneas y ramas combinadas >= 80%, en SQLite y PostgreSQL independientemente |
| Harness al integrarse | Cobertura total de líneas y ramas combinadas >= 80% sobre app/ |
| Agenda al integrarse | Líneas, funciones, ramas y sentencias >= 80% cada una sobre src/ con Vitest |
| Pruebas | Todas aprobadas |
| Buenas prácticas Python | Ruff: errores, imports, patrones de bugs y modernización; formato sin diferencias |
| Buenas prácticas agenda | npm run lint y npm run format:check exitosos |
| Contrato y construcción | OpenAPI actualizado, Docker, Compose y scripts válidos |

`quality-gate` reúne los checks y falla si cualquiera falla o se cancela. Los PR hacia develop pueden avanzar sin módulos aún no aportados, pero sus suites serán obligatorias al incorporarlos. Main requiere todos los componentes. No se mide únicamente el diff: se incluye todo el código de aplicación, incluso archivos no importados por tests.

En cada ejecución de citas, la pestaña Summary de Actions muestra la cobertura y los artifacts tests-citas-* incluyen XML, Markdown y reporte HTML por archivo. Localmente, ejecutar pytest desde ms-citas aplica el mismo umbral. Puede abrirse htmlcov/index.html después de correr la suite.

Sebitas deberá incorporar el proveedor de coverage de Vitest compatible con su versión, scripts lint/format:check y herramientas correspondientes en package-lock.json. El harness debe mantener código en app/ y tests en tests/. Estos acuerdos se revisan antes de integrar.

## Límite de la protección en GitHub

La API de GitHub devolvió HTTP 403 al consultar protección de develop: el repositorio privado requiere GitHub Pro o hacerlo público para esa función. No se cambió su visibilidad ni plan.

El workflow reporta fallos y evita el despliegue automático si no pasa CI, pero con el plan actual no puede impedir un push directo ni que un usuario con permisos fusione manualmente un PR fallido. Cuando el plan lo permita, proteger develop y main, exigir PR, revisión y el check quality-gate (sin bypass). Mientras tanto, integrar únicamente PR con todos los checks verdes.

La cobertura no sustituye la revisión funcional ni garantiza ausencia de errores. No excluir código de negocio para elevar artificialmente el porcentaje.
