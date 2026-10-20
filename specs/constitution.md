# Constitución del proyecto

- El plan maestro adjunto es la referencia inicial del alcance y los contratos.
- Seguir el flujo especificación → plan → tareas → tests → implementación → revisión.
- Mantener bases de datos separadas por servicio; la comunicación entre servicios es HTTP.
- Cambiar contratos mediante PR, actualizando el plan y las pruebas afectadas.
- Trabajar en ramas personales y revisar los PR entre compañeros.
- Respetar los responsables por carpeta definidos en el plan maestro.
- No versionar secretos, claves privadas, transcripts ni datos reales de pacientes.
- Verificar idempotencia y prevención de doble reserva con pruebas automatizadas.
- Registrar las decisiones pendientes antes de congelar contratos para implementar.
