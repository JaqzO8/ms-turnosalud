# Especificación inicial

Derivada del [plan maestro](../../PLAN_EXAMEN_TURNO_SALUD.md), secciones 4–7. Pendiente de revisión conjunta.

| Requisito | Comportamiento esperado |
|---|---|
| RF-1 | Reservar una cita mediante lenguaje natural y obtener estado CONFIRMADA |
| RF-2 | Localizar y cancelar una cita mediante el documento del paciente |
| RF-3 | Consultar médicos y disponibilidad por fecha |
| RF-4 | Impedir doble reserva y soportar reintentos idempotentes |
| RF-5 | Devolver 503 controlado si agenda no está disponible |
| RF-6 | Registrar conversaciones, herramientas utilizadas y tiempos |

El harness tendrá cinco herramientas permitidas (`listar_medicos`, `ver_disponibilidad`, `reservar_cita`, `cancelar_cita`, `listar_citas`; decisión D3 de plan.md), con memoria conversacional por `sesion_id` (multi-turno), límites de llamadas, timeouts y evaluaciones E-01 a E-07 según el plan maestro. Comportamiento clave: si faltan datos de la cita (especialidad, fecha, hora, nombre/documento), el harness PREGUNTA por ellos antes de usar herramientas (E-06, E-07). El modo mock permitirá ejecutar las evaluaciones sin un proveedor LLM externo.

Fuera de alcance: JWT, pagos, entrenamiento de ML y Kubernetes.
