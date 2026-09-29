-- Seed demo: datos de ejemplo para quien descargue el ZIP.
-- Uso: createdb demo && alembic upgrade head && psql demo < scripts/seed_demo.sql
-- Login: jefe.demo@upds.edu.bo / tecnico.demo@upds.edu.bo — password: demo1234

INSERT INTO "Usuarios" ("Email","PasswordHash","DisplayName","Role","EstadoActual","CanViewDashboard","Activo","TokenVersion")
VALUES
 ('jefe.demo@upds.edu.bo','$2b$12$q0Le5csR2G4Za7YJJyAPY.Rghd0DX//KCjsznzJ.4DqmxPTjCkX72','Jefe Demo','Jefe','Disponible',TRUE,TRUE,0),
 ('tecnico.demo@upds.edu.bo','$2b$12$q0Le5csR2G4Za7YJJyAPY.Rghd0DX//KCjsznzJ.4DqmxPTjCkX72','Técnico Demo','Tecnico','Disponible',FALSE,TRUE,0),
 ('wilmercito@sistema.upds.edu.bo',NULL,'Wilmercito','Tecnico','Disponible',FALSE,TRUE,0);

INSERT INTO "Atenciones" ("UsuarioId","AreaSolicitante","MedioSolicitud","UsuarioSolicitante","Categoria","Descripcion","Solucion","FueraDeTurno","FechaRegistro") VALUES
 (2,'Registro','Presencial','A. Vargas','Hardware','PC no enciende, fuente quemada','Se reemplazó la fuente de poder','f','2026-09-10'),
 (2,'Caja','WhatsApp','L. Prado','Software','Sistema de caja se cierra solo','Se reinstaló el cliente y se purgó caché','f','2026-09-11'),
 (2,'Aulas','Teléfono','M. Ríos','Redes/Conectividad','Sin internet en aula 4','Se reconectó el AP y se renovó DHCP','f','2026-09-12'),
 (2,'Dirección','Email','J. Paredes','Impresión','Impresora no imprime a doble cara','Se activó dúplex en el driver','f','2026-09-13'),
 (2,'Registro','Presencial','S. Montaño','Cuentas/Accesos','No puede entrar al sistema académico','Reset de contraseña + desbloqueo','f','2026-09-14'),
 (2,'Aulas','WhatsApp','D. Choque','Audio/Video','Proyector sin imagen HDMI','Cambio de cable HDMI','f','2026-09-15'),
 (2,'Biblioteca','Teléfono','R. Salas','Sistemas académicos','Error al inscribir materia','Se corrigió prerrequisito en el plan','f','2026-09-16'),
 (2,'Caja','Presencial','V. Lima','Otros','Solicitud de punto de red nuevo','Se cableó y certificó el punto','f','2026-09-17'),
 (2,'Aulas','Email','T. Flores','Hardware','Teclado con teclas muertas','Reemplazo de teclado','f','2026-09-18'),
 (2,'Dirección','WhatsApp','C. Rojas','Software','Excel se cuelga con planilla grande','Se reparó Office y se dividió el archivo','f','2026-09-19'),
 (2,'Registro','Teléfono','N. Aguil','Redes/Conectividad','WiFi lento en época de inscripciones','Se agregó AP temporal','f','2026-09-20'),
 (2,'Biblioteca','Presencial','P. Suárez','Impresión','Tóner agotado','Recambio de tóner','f','2026-09-21'),
 (2,'Caja','Email','H. Vedia','Cuentas/Accesos','Usuario nuevo sin acceso','Alta de cuenta y perfiles','f','2026-09-22'),
 (2,'Aulas','WhatsApp','E. Campos','Audio/Video','Micrófono con acople','Se ajustó ganancia y posición','f','2026-09-23'),
 (2,'Dirección','Teléfono','G. Ortiz','Otros','Respaldo mensual de actas','Respaldo verificado en disco externo','f','2026-09-24');
