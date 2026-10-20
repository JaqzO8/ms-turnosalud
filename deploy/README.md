# Integración y despliegue EC2

## Flujo

`feat/jose` y `feat/sebitas` → PR a `develop` → integración y correcciones → PR a `main` → CI verde → deploy EC2.

CI ejecuta citas en SQLite/PostgreSQL, lint, OpenAPI y build Docker. Prueba agenda/harness cuando se incorporan. En PR hacia main y push a main exige todos los componentes de release. Los workflows se activan al incorporarse en cada rama.

El check `quality-gate` exige cobertura >= 80%, pruebas, lint, formato, contrato y build aprobados. Los reportes están en Actions. Cuando el plan de GitHub lo permita, configurar protección de main/develop para exigir PR, revisión y quality-gate. La API devolvió 403 para la protección de este repositorio privado; los workflows no impiden por sí solos pushes directos o merges manuales con checks fallidos. Ver [política de calidad](../docs/calidad.md).

## Contrato de integración propuesto para Sebitas

- Agenda: Node 22, package-lock.json, scripts test (Vitest con coverage), lint, format:check y build, salida dist/server.js; /health en 3001; scripts/migrate.sh idempotente que consume sus variables de entorno. Cobertura sobre src/ >= 80% para líneas, funciones, ramas y sentencias.
- Harness: Python 3.13, requirements.lock con pytest y uvicorn, app.main:app, tests/ y /health en 3003; evaluaciones con MOCK_LLM=true.
- Revisar estos entrypoints en el PR antes de integrar. Las unidades systemd de esos módulos son plantillas pendientes de validar.

## Preparar EC2 (pendiente)

1. Instalar Python 3.13/venv, Node 22/npm, Git, curl, util-linux y PostgreSQL 16 (o BD externa). Ubuntu 24.04 requiere instalar Python 3.13 adicionalmente.
2. Crear usuario turnosalud, propietario de /opt/turno-salud/repo y /opt/turno-salud/releases. Clonar el repo privado en repo con deploy key de solo lectura y verificar host GitHub.
3. Crear agenda_db y citas_db, con credenciales separadas en producción, y configurar backups.
4. Crear /etc/turno-salud/{agenda,citas,harness}.env, formato shell KEY='value', permisos 640, grupo turnosalud. Citas: DATABASE_URL con postgresql+psycopg, AGENDA_URL=http://127.0.0.1:3001 y timeout. Harness: URLs y clave LLM.
5. Instalar las unidades de systemd/, ejecutar daemon-reload y habilitarlas. Autorizar al usuario de despliegue con sudo sin contraseña solo el comando de reinicio de las tres unidades; ajustar la ruta real de systemctl.
6. Configurar proxy HTTPS para el harness. Las unidades Python escuchan en loopback. Restringir SSH según conectividad del runner y no exponer la BD.
7. Crear environment production en GitHub; configurar aprobación si el plan lo admite.
8. Guardar secrets SSH_HOST, SSH_USER, SSH_KEY y SSH_KNOWN_HOSTS. Verificar la huella EC2 por un canal confiable antes de guardar known_hosts.
9. Activar variable de repositorio EC2_DEPLOY_ENABLED=true solo al completar la preparación.

## Comportamiento

El deploy usa el SHA exacto probado por CI y descarta ejecuciones antiguas si main avanzó. Instala una release, inicializa BD/migra agenda, cambia el enlace current, reinicia servicios y comprueba health en 3001/3002/3003. Si falla tras activar, intenta restaurar el código anterior. No revierte migraciones; deben ser compatibles con la versión anterior. El primer despliegue no tiene release de respaldo. No es un despliegue sin interrupciones.

Docker local: copiar .env.example a .env, ajustar contraseña y ejecutar docker compose up --build. Actualmente incluye solo BD/citas; la integración completa espera agenda/harness. AGENDA_URL debe ser alcanzable desde el contenedor.

No se ha creado ni desplegado EC2. Registrar URL, commit y ejecución de Actions en docs/ al validarlo.
