# Login y Mis citas — integración conjunta

La funcionalidad cruza las responsabilidades de ambos módulos: ms-citas (José) mantiene usuarios, sesiones y autorización; el harness e interfaz (módulo de Sebastián) presentan registro, login, listado y chat autenticado. Esta integración no atribuye autoría de commits a otra persona.

- Crear cuenta con nombre, documento único de ocho dígitos y contraseña de 8–128 caracteres.
- Contraseñas derivadas con scrypt y salt aleatoria; tokens aleatorios guardados como hash, caducidad de ocho horas y revocación al salir.
- Cookie HttpOnly/SameSite=Strict; el token nunca llega al JavaScript ni al LLM. Las peticiones modificadoras requieren una cabecera propia contra CSRF.
- Reservas, listado y cancelación verifican el documento del usuario en ms-citas, incluso cuando el LLM intenta gestionar otro usuario. Sesiones conversacionales separadas por sesión autenticada.
- La vista muestra confirmadas y canceladas, diez por página; permite actualizar y cancelar. Se refresca después del chat.
- Las citas anónimas previas no se asignan automáticamente por documento: el administrador debe verificar identidad y crear la cuenta para ese documento mediante un proceso controlado. El registro público rechaza esos documentos. No se borran citas anteriores.
- Migración aditiva: app.db crea usuarios/login_sessions sin alterar ni eliminar la tabla citas.
- /evals público queda desactivado; las evaluaciones se mantienen en tests.

Demo HTTP: solo datos y contraseñas ficticios. Antes de pacientes reales, configurar HTTPS y COOKIE_SECURE=true. No incluye recuperación de contraseña, verificación de identidad ni MFA.

Pruebas: registro duplicado/legado, contraseña incorrecta, expiración/revocación, aislamiento entre usuarios, rechazo de acceso anónimo, cookies, CSRF, proxy y contexto autenticado del chat.
