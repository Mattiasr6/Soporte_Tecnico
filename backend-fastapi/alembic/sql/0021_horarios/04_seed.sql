-- GENERATED: catalog seed data (scripts 04, 23, 29, 33...) as left by the
-- Supabase scripts, without the 05 sample data. Timestamps replaced by now().

-- TABLE DATA: ambientes
INSERT INTO horarios.ambientes (id, codigo, nombre, tipo, capacidad, tipo_equipo, ubicacion, estado, color, orden, creado_en, actualizado_en) OVERRIDING SYSTEM VALUE VALUES (1, 'LAB-01', 'Laboratorio 1', 'laboratorio', 30, 'PC de escritorio', NULL, 'activo', '#2563eb', 1, now(), now());
INSERT INTO horarios.ambientes (id, codigo, nombre, tipo, capacidad, tipo_equipo, ubicacion, estado, color, orden, creado_en, actualizado_en) OVERRIDING SYSTEM VALUE VALUES (2, 'LAB-02', 'Laboratorio 2', 'laboratorio', 30, 'PC de escritorio', NULL, 'activo', '#0891b2', 2, now(), now());
INSERT INTO horarios.ambientes (id, codigo, nombre, tipo, capacidad, tipo_equipo, ubicacion, estado, color, orden, creado_en, actualizado_en) OVERRIDING SYSTEM VALUE VALUES (3, 'LAB-03', 'Laboratorio 3', 'laboratorio', 30, 'PC de escritorio', NULL, 'activo', '#059669', 3, now(), now());
INSERT INTO horarios.ambientes (id, codigo, nombre, tipo, capacidad, tipo_equipo, ubicacion, estado, color, orden, creado_en, actualizado_en) OVERRIDING SYSTEM VALUE VALUES (4, 'LAB-04', 'Laboratorio 4', 'laboratorio', 30, 'PC de escritorio', NULL, 'activo', '#65a30d', 4, now(), now());
INSERT INTO horarios.ambientes (id, codigo, nombre, tipo, capacidad, tipo_equipo, ubicacion, estado, color, orden, creado_en, actualizado_en) OVERRIDING SYSTEM VALUE VALUES (5, 'LAB-05', 'Laboratorio 5', 'laboratorio', 30, 'PC de escritorio', NULL, 'activo', '#ca8a04', 5, now(), now());
INSERT INTO horarios.ambientes (id, codigo, nombre, tipo, capacidad, tipo_equipo, ubicacion, estado, color, orden, creado_en, actualizado_en) OVERRIDING SYSTEM VALUE VALUES (6, 'LAB-06', 'Laboratorio 6', 'laboratorio', 30, 'PC de escritorio', NULL, 'activo', '#ea580c', 6, now(), now());
INSERT INTO horarios.ambientes (id, codigo, nombre, tipo, capacidad, tipo_equipo, ubicacion, estado, color, orden, creado_en, actualizado_en) OVERRIDING SYSTEM VALUE VALUES (7, 'LAB-07', 'Laboratorio 7', 'laboratorio', 30, 'PC de escritorio', NULL, 'activo', '#dc2626', 7, now(), now());
INSERT INTO horarios.ambientes (id, codigo, nombre, tipo, capacidad, tipo_equipo, ubicacion, estado, color, orden, creado_en, actualizado_en) OVERRIDING SYSTEM VALUE VALUES (8, 'LAB-08', 'Laboratorio 8', 'laboratorio', 30, 'PC de escritorio', NULL, 'activo', '#db2777', 8, now(), now());
INSERT INTO horarios.ambientes (id, codigo, nombre, tipo, capacidad, tipo_equipo, ubicacion, estado, color, orden, creado_en, actualizado_en) OVERRIDING SYSTEM VALUE VALUES (9, 'LAB-09', 'Laboratorio 9', 'laboratorio', 30, 'PC de escritorio', NULL, 'activo', '#9333ea', 9, now(), now());
INSERT INTO horarios.ambientes (id, codigo, nombre, tipo, capacidad, tipo_equipo, ubicacion, estado, color, orden, creado_en, actualizado_en) OVERRIDING SYSTEM VALUE VALUES (10, 'LAB-10', 'Laboratorio 10', 'laboratorio', 30, 'PC de escritorio', NULL, 'activo', '#4f46e5', 10, now(), now());

-- TABLE DATA: perfiles


-- TABLE DATA: ambiente_pcs


-- TABLE DATA: carreras
INSERT INTO horarios.carreras (id, nombre, sigla, color, activo, creado_en, actualizado_en) OVERRIDING SYSTEM VALUE VALUES (1, 'Ingeniería de Sistemas', 'SIS', '#2563eb', true, now(), now());
INSERT INTO horarios.carreras (id, nombre, sigla, color, activo, creado_en, actualizado_en) OVERRIDING SYSTEM VALUE VALUES (2, 'Ingeniería Industrial', 'IND', '#ca8a04', true, now(), now());
INSERT INTO horarios.carreras (id, nombre, sigla, color, activo, creado_en, actualizado_en) OVERRIDING SYSTEM VALUE VALUES (3, 'Ingeniería en Redes y Telecomunicaciones', 'RED', '#059669', true, now(), now());
INSERT INTO horarios.carreras (id, nombre, sigla, color, activo, creado_en, actualizado_en) OVERRIDING SYSTEM VALUE VALUES (4, 'Medicina', 'MED', '#dc2626', true, now(), now());
INSERT INTO horarios.carreras (id, nombre, sigla, color, activo, creado_en, actualizado_en) OVERRIDING SYSTEM VALUE VALUES (5, 'Derecho', 'DER', '#7c3aed', true, now(), now());
INSERT INTO horarios.carreras (id, nombre, sigla, color, activo, creado_en, actualizado_en) OVERRIDING SYSTEM VALUE VALUES (6, 'Psicología', 'PSI', '#db2777', true, now(), now());
INSERT INTO horarios.carreras (id, nombre, sigla, color, activo, creado_en, actualizado_en) OVERRIDING SYSTEM VALUE VALUES (7, 'Administración de Empresas', 'ADM', '#0d9488', true, now(), now());
INSERT INTO horarios.carreras (id, nombre, sigla, color, activo, creado_en, actualizado_en) OVERRIDING SYSTEM VALUE VALUES (8, 'Contaduría Pública', 'CON', '#64748b', true, now(), now());
INSERT INTO horarios.carreras (id, nombre, sigla, color, activo, creado_en, actualizado_en) OVERRIDING SYSTEM VALUE VALUES (9, 'Ingeniería Comercial', 'COM', '#ea580c', true, now(), now());
INSERT INTO horarios.carreras (id, nombre, sigla, color, activo, creado_en, actualizado_en) OVERRIDING SYSTEM VALUE VALUES (10, 'Ciencias de la Comunicación', 'CCS', '#0891b2', true, now(), now());
INSERT INTO horarios.carreras (id, nombre, sigla, color, activo, creado_en, actualizado_en) OVERRIDING SYSTEM VALUE VALUES (11, 'Ciencias de la Educación', 'EDU', '#65a30d', true, now(), now());

-- TABLE DATA: docentes


-- TABLE DATA: materias


-- TABLE DATA: sistemas_academicos
INSERT INTO horarios.sistemas_academicos (id, codigo, nombre, dias_permitidos, modo_fechas, meses_duracion, meses_maximo, dias_sugeridos, color, activo) OVERRIDING SYSTEM VALUE VALUES (1, 'MOD_PRES', 'Modular presencial', '{1,2,3,4,5}', 'dias', NULL, NULL, 20, '#2563eb', true);
INSERT INTO horarios.sistemas_academicos (id, codigo, nombre, dias_permitidos, modo_fechas, meses_duracion, meses_maximo, dias_sugeridos, color, activo) OVERRIDING SYSTEM VALUE VALUES (2, 'MOD_SEMI', 'Modular semipresencial', '{6}', 'dias', NULL, NULL, 4, '#d97706', true);
INSERT INTO horarios.sistemas_academicos (id, codigo, nombre, dias_permitidos, modo_fechas, meses_duracion, meses_maximo, dias_sugeridos, color, activo) OVERRIDING SYSTEM VALUE VALUES (3, 'SEMESTRAL', 'Semestral', '{1,2,3,4,5,6}', 'rango', 6, 7, NULL, '#0891b2', true);

-- TABLE DATA: asignaciones


-- TABLE DATA: asignacion_fechas


-- TABLE DATA: asignacion_horarios


-- TABLE DATA: turnos_trabajo


-- TABLE DATA: atenciones


-- TABLE DATA: bloques_horario
INSERT INTO horarios.bloques_horario (id, nombre, turno, hora_inicio, hora_fin, orden) OVERRIDING SYSTEM VALUE VALUES (1, 'Mañana', 'M', '07:30:00', '10:30:00', 1);
INSERT INTO horarios.bloques_horario (id, nombre, turno, hora_inicio, hora_fin, orden) OVERRIDING SYSTEM VALUE VALUES (2, 'Medio día', 'MD', '10:30:00', '13:30:00', 2);
INSERT INTO horarios.bloques_horario (id, nombre, turno, hora_inicio, hora_fin, orden) OVERRIDING SYSTEM VALUE VALUES (3, 'Tarde 1', 'T', '13:30:00', '16:00:00', 3);
INSERT INTO horarios.bloques_horario (id, nombre, turno, hora_inicio, hora_fin, orden) OVERRIDING SYSTEM VALUE VALUES (4, 'Tarde 2', 'T', '16:00:00', '19:00:00', 4);
INSERT INTO horarios.bloques_horario (id, nombre, turno, hora_inicio, hora_fin, orden) OVERRIDING SYSTEM VALUE VALUES (5, 'Noche', 'N', '19:00:00', '22:00:00', 5);

-- TABLE DATA: cesiones


-- TABLE DATA: cesion_fechas


-- TABLE DATA: docente_carreras


-- TABLE DATA: docente_materias


-- TABLE DATA: fallas_pc
INSERT INTO horarios.fallas_pc (id, nombre, categoria, activo, orden, creado_en) OVERRIDING SYSTEM VALUE VALUES (1, 'No enciende', 'hardware', true, 10, now());
INSERT INTO horarios.fallas_pc (id, nombre, categoria, activo, orden, creado_en) OVERRIDING SYSTEM VALUE VALUES (2, 'Fuente de poder', 'hardware', true, 11, now());
INSERT INTO horarios.fallas_pc (id, nombre, categoria, activo, orden, creado_en) OVERRIDING SYSTEM VALUE VALUES (3, 'Memoria RAM', 'hardware', true, 12, now());
INSERT INTO horarios.fallas_pc (id, nombre, categoria, activo, orden, creado_en) OVERRIDING SYSTEM VALUE VALUES (4, 'Disco duro', 'hardware', true, 13, now());
INSERT INTO horarios.fallas_pc (id, nombre, categoria, activo, orden, creado_en) OVERRIDING SYSTEM VALUE VALUES (5, 'Placa madre', 'hardware', true, 14, now());
INSERT INTO horarios.fallas_pc (id, nombre, categoria, activo, orden, creado_en) OVERRIDING SYSTEM VALUE VALUES (6, 'Sobrecalentamiento', 'hardware', true, 15, now());
INSERT INTO horarios.fallas_pc (id, nombre, categoria, activo, orden, creado_en) OVERRIDING SYSTEM VALUE VALUES (7, 'Windows no inicia', 'software', true, 20, now());
INSERT INTO horarios.fallas_pc (id, nombre, categoria, activo, orden, creado_en) OVERRIDING SYSTEM VALUE VALUES (8, 'Pantalla azul', 'software', true, 21, now());
INSERT INTO horarios.fallas_pc (id, nombre, categoria, activo, orden, creado_en) OVERRIDING SYSTEM VALUE VALUES (9, 'Lenta', 'software', true, 22, now());
INSERT INTO horarios.fallas_pc (id, nombre, categoria, activo, orden, creado_en) OVERRIDING SYSTEM VALUE VALUES (10, 'Virus', 'software', true, 23, now());
INSERT INTO horarios.fallas_pc (id, nombre, categoria, activo, orden, creado_en) OVERRIDING SYSTEM VALUE VALUES (11, 'Programa no abre', 'software', true, 24, now());
INSERT INTO horarios.fallas_pc (id, nombre, categoria, activo, orden, creado_en) OVERRIDING SYSTEM VALUE VALUES (12, 'Teclado', 'perifericos', true, 30, now());
INSERT INTO horarios.fallas_pc (id, nombre, categoria, activo, orden, creado_en) OVERRIDING SYSTEM VALUE VALUES (13, 'Mouse', 'perifericos', true, 31, now());
INSERT INTO horarios.fallas_pc (id, nombre, categoria, activo, orden, creado_en) OVERRIDING SYSTEM VALUE VALUES (14, 'Monitor', 'perifericos', true, 32, now());
INSERT INTO horarios.fallas_pc (id, nombre, categoria, activo, orden, creado_en) OVERRIDING SYSTEM VALUE VALUES (15, 'Cable', 'perifericos', true, 33, now());
INSERT INTO horarios.fallas_pc (id, nombre, categoria, activo, orden, creado_en) OVERRIDING SYSTEM VALUE VALUES (16, 'Sin internet', 'red', true, 40, now());

-- TABLE DATA: feriados
INSERT INTO horarios.feriados (fecha, descripcion) VALUES ('2026-01-01', 'Año Nuevo');
INSERT INTO horarios.feriados (fecha, descripcion) VALUES ('2026-01-22', 'Día del Estado Plurinacional');
INSERT INTO horarios.feriados (fecha, descripcion) VALUES ('2026-02-16', 'Carnaval');
INSERT INTO horarios.feriados (fecha, descripcion) VALUES ('2026-02-17', 'Carnaval');
INSERT INTO horarios.feriados (fecha, descripcion) VALUES ('2026-04-03', 'Viernes Santo');
INSERT INTO horarios.feriados (fecha, descripcion) VALUES ('2026-05-01', 'Día del Trabajo');
INSERT INTO horarios.feriados (fecha, descripcion) VALUES ('2026-06-04', 'Corpus Christi');
INSERT INTO horarios.feriados (fecha, descripcion) VALUES ('2026-06-21', 'Año Nuevo Andino');
INSERT INTO horarios.feriados (fecha, descripcion) VALUES ('2026-08-06', 'Día de la Independencia');
INSERT INTO horarios.feriados (fecha, descripcion) VALUES ('2026-11-02', 'Todos Santos');
INSERT INTO horarios.feriados (fecha, descripcion) VALUES ('2026-12-25', 'Navidad');

-- TABLE DATA: horarios_turno
INSERT INTO horarios.horarios_turno (turno, hora_inicio, hora_fin, actualizado_en, actualizado_por) VALUES ('M', '07:00:00', '12:00:00', now(), NULL);
INSERT INTO horarios.horarios_turno (turno, hora_inicio, hora_fin, actualizado_en, actualizado_por) VALUES ('MD', '12:00:00', '16:00:00', now(), NULL);
INSERT INTO horarios.horarios_turno (turno, hora_inicio, hora_fin, actualizado_en, actualizado_por) VALUES ('T', '14:30:00', '18:30:00', now(), NULL);
INSERT INTO horarios.horarios_turno (turno, hora_inicio, hora_fin, actualizado_en, actualizado_por) VALUES ('N', '18:00:00', '22:00:00', now(), NULL);

-- TABLE DATA: objetos_perdidos


-- TABLE DATA: reportes_turno


-- TABLE DATA: reporte_tareas


-- TABLE DATA: tipos_reserva
INSERT INTO horarios.tipos_reserva (id, codigo, nombre, prioridad, color) OVERRIDING SYSTEM VALUE VALUES (1, 'EVENTO', 'Evento', 100, '#dc2626');
INSERT INTO horarios.tipos_reserva (id, codigo, nombre, prioridad, color) OVERRIDING SYSTEM VALUE VALUES (2, 'DEFENSA', 'Defensa', 100, '#ea580c');
INSERT INTO horarios.tipos_reserva (id, codigo, nombre, prioridad, color) OVERRIDING SYSTEM VALUE VALUES (3, 'MANTENIMIENTO', 'Mantenimiento', 90, '#475569');

-- TABLE DATA: reservas


-- TABLE DATA: reserva_horarios


-- TABLE DATA: reubicaciones


-- TABLE DATA: rotacion_sabados


-- TABLE DATA: solicitudes_baja


-- TABLE DATA: turnos_programados


-- SEQUENCE SET: ambiente_pcs_id_seq
SELECT pg_catalog.setval('horarios.ambiente_pcs_id_seq', 1, false);

-- SEQUENCE SET: ambientes_id_seq
SELECT pg_catalog.setval('horarios.ambientes_id_seq', 10, true);

-- SEQUENCE SET: asignacion_horarios_id_seq
SELECT pg_catalog.setval('horarios.asignacion_horarios_id_seq', 1, false);

-- SEQUENCE SET: asignaciones_id_seq
SELECT pg_catalog.setval('horarios.asignaciones_id_seq', 1, false);

-- SEQUENCE SET: atenciones_id_seq
SELECT pg_catalog.setval('horarios.atenciones_id_seq', 1, false);

-- SEQUENCE SET: bloques_horario_id_seq
SELECT pg_catalog.setval('horarios.bloques_horario_id_seq', 5, true);

-- SEQUENCE SET: carreras_id_seq
SELECT pg_catalog.setval('horarios.carreras_id_seq', 11, true);

-- SEQUENCE SET: cesiones_id_seq
SELECT pg_catalog.setval('horarios.cesiones_id_seq', 1, false);

-- SEQUENCE SET: docentes_id_seq
SELECT pg_catalog.setval('horarios.docentes_id_seq', 1, false);

-- SEQUENCE SET: fallas_pc_id_seq
SELECT pg_catalog.setval('horarios.fallas_pc_id_seq', 16, true);

-- SEQUENCE SET: materias_id_seq
SELECT pg_catalog.setval('horarios.materias_id_seq', 1, false);

-- SEQUENCE SET: objetos_perdidos_id_seq
SELECT pg_catalog.setval('horarios.objetos_perdidos_id_seq', 1, false);

-- SEQUENCE SET: reporte_tareas_id_seq
SELECT pg_catalog.setval('horarios.reporte_tareas_id_seq', 1, false);

-- SEQUENCE SET: reportes_turno_id_seq
SELECT pg_catalog.setval('horarios.reportes_turno_id_seq', 1, false);

-- SEQUENCE SET: reserva_horarios_id_seq
SELECT pg_catalog.setval('horarios.reserva_horarios_id_seq', 1, false);

-- SEQUENCE SET: reservas_id_seq
SELECT pg_catalog.setval('horarios.reservas_id_seq', 1, false);

-- SEQUENCE SET: reubicaciones_id_seq
SELECT pg_catalog.setval('horarios.reubicaciones_id_seq', 1, false);

-- SEQUENCE SET: rotacion_sabados_id_seq
SELECT pg_catalog.setval('horarios.rotacion_sabados_id_seq', 1, false);

-- SEQUENCE SET: sistemas_academicos_id_seq
SELECT pg_catalog.setval('horarios.sistemas_academicos_id_seq', 3, true);

-- SEQUENCE SET: solicitudes_baja_id_seq
SELECT pg_catalog.setval('horarios.solicitudes_baja_id_seq', 1, false);

-- SEQUENCE SET: tipos_reserva_id_seq
SELECT pg_catalog.setval('horarios.tipos_reserva_id_seq', 3, true);

-- SEQUENCE SET: turnos_programados_id_seq
SELECT pg_catalog.setval('horarios.turnos_programados_id_seq', 1, false);

-- SEQUENCE SET: turnos_trabajo_id_seq
SELECT pg_catalog.setval('horarios.turnos_trabajo_id_seq', 1, false);


--
-- PostgreSQL database dump complete
--
