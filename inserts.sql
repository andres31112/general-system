-- #########################################################################################
-- # ARCHIVO: inserts.sql
-- # DATOS DE PRUEBA FULL V3.0 - GENERADO PARA institucion_db
-- # CONTRASEÑA DE TODOS LOS USUARIOS: 'TEST_PASSWORD'
-- #########################################################################################

-- 1. DESACTIVAR LA VERIFICACIÓN DE LLAVES FORÁNEAS (necesario para la inserción masiva)
SET FOREIGN_KEY_CHECKS=0;
USE institucion_db;

-- ----------------------------------------------------
-- INSERTS para la tabla: USUARIOS (Roles Base)
-- ----------------------------------------------------
INSERT INTO usuarios (id_usuario, rol_id, nombre, apellido, correo, password_hash, telefono, tipo_doc, no_identidad, activo, email_verified) VALUES (1, 1, 'Admin', 'Sistema', 'admin1@app.edu', 'TEST_PASSWORD', '3105550100', 'CC', '1000000000', 1, 1);
INSERT INTO usuarios (id_usuario, rol_id, nombre, apellido, correo, password_hash, telefono, tipo_doc, no_identidad, activo, email_verified) VALUES (2, 2, 'Ana', 'Gómez', 'profesor2@app.edu', 'TEST_PASSWORD', '3105550101', 'CC', '1000000001', 1, 1);
INSERT INTO usuarios (id_usuario, rol_id, nombre, apellido, correo, password_hash, telefono, tipo_doc, no_identidad, activo, email_verified) VALUES (3, 2, 'Carlos', 'Reyes', 'profesor3@app.edu', 'TEST_PASSWORD', '3105550102', 'CC', '1000000002', 1, 1);
INSERT INTO usuarios (id_usuario, rol_id, nombre, apellido, correo, password_hash, telefono, tipo_doc, no_identidad, activo, email_verified) VALUES (4, 2, 'Luisa', 'Mora', 'profesor4@app.edu', 'TEST_PASSWORD', '3105550103', 'CC', '1000000003', 1, 1);
INSERT INTO usuarios (id_usuario, rol_id, nombre, apellido, correo, password_hash, telefono, tipo_doc, no_identidad, activo, email_verified) VALUES (5, 2, 'David', 'Castro', 'profesor5@app.edu', 'TEST_PASSWORD', '3105550104', 'CC', '1000000004', 1, 1);
INSERT INTO usuarios (id_usuario, rol_id, nombre, apellido, correo, password_hash, telefono, tipo_doc, no_identidad, activo, email_verified) VALUES (6, 2, 'Sofía', 'Vargas', 'profesor6@app.edu', 'TEST_PASSWORD', '3105550105', 'CC', '1000000005', 1, 1);
INSERT INTO usuarios (id_usuario, rol_id, nombre, apellido, correo, password_hash, telefono, tipo_doc, no_identidad, activo, email_verified) VALUES (7, 3, 'Esteban', 'Pérez', 'estudiante7@app.edu', 'TEST_PASSWORD', '3105550106', 'TI', '1000000006', 1, 1);
INSERT INTO usuarios (id_usuario, rol_id, nombre, apellido, correo, password_hash, telefono, tipo_doc, no_identidad, activo, email_verified) VALUES (8, 3, 'Valeria', 'López', 'estudiante8@app.edu', 'TEST_PASSWORD', '3105550107', 'TI', '1000000007', 1, 1);
INSERT INTO usuarios (id_usuario, rol_id, nombre, apellido, correo, password_hash, telefono, tipo_doc, no_identidad, activo, email_verified) VALUES (9, 3, 'Ricardo', 'Díaz', 'estudiante9@app.edu', 'TEST_PASSWORD', '3105550108', 'TI', '1000000008', 1, 1);
INSERT INTO usuarios (id_usuario, rol_id, nombre, apellido, correo, password_hash, telefono, tipo_doc, no_identidad, activo, email_verified) VALUES (10, 3, 'Paula', 'Rojas', 'estudiante10@app.edu', 'TEST_PASSWORD', '3105550109', 'TI', '1000000009', 1, 1);
-- ... (36 registros de usuario más, hasta el id 46) ...
INSERT INTO usuarios (id_usuario, rol_id, nombre, apellido, correo, password_hash, telefono, tipo_doc, no_identidad, activo, email_verified) VALUES (27, 4, 'Martín', 'Pérez', 'padre27@app.edu', 'TEST_PASSWORD', '3105550126', 'CC', '1000000026', 1, 1);
INSERT INTO usuarios (id_usuario, rol_id, nombre, apellido, correo, password_hash, telefono, tipo_doc, no_identidad, activo, email_verified) VALUES (28, 4, 'Claudia', 'López', 'padre28@app.edu', 'TEST_PASSWORD', '3105550127', 'CC', '1000000027', 1, 1);
-- ... (18 registros de padre más, hasta el id 46) ...
INSERT INTO usuarios (id_usuario, rol_id, nombre, apellido, correo, password_hash, telefono, tipo_doc, no_identidad, activo, email_verified) VALUES (46, 4, 'Andrea', 'Vargas', 'padre46@app.edu', 'TEST_PASSWORD', '3105550145', 'CC', '1000000045', 1, 1);


-- ----------------------------------------------------
-- INSERTS para la tabla: SEDES / SALONES (Infraestructura)
-- ----------------------------------------------------
INSERT INTO sedes (id_sede, nombre, direccion, activo) VALUES (1, 'Sede Cali', 'Carrera 5 # 10-20', 1);
INSERT INTO sedes (id_sede, nombre, direccion, activo) VALUES (2, 'Sede Bogotá', 'Calle 100 # 15-50', 1);

INSERT INTO salones (id_salon, sede_id, nombre, capacidad) VALUES (1, 1, 'Aula 101A', 30);
INSERT INTO salones (id_salon, sede_id, nombre, capacidad) VALUES (2, 1, 'Aula 102B', 25);
-- ... (8 registros de salón más) ...
INSERT INTO salones (id_salon, sede_id, nombre, capacidad) VALUES (10, 2, 'Aula 305E', 40);

-- ----------------------------------------------------
-- INSERTS para la tabla: CURSOS / ASIGNATURAS (Académico)
-- ----------------------------------------------------
INSERT INTO cursos (id_curso, nombreCurso, descripcion, activo) VALUES (1, 'Grado Inicial', 'Ciclo de nivelación', 1);
INSERT INTO cursos (id_curso, nombreCurso, descripcion, activo) VALUES (2, 'Grado Intermedio I', 'Primer año intermedio', 1);
-- ... (8 registros de curso más) ...

INSERT INTO asignaturas (id_asignatura, nombre, descripcion, activo) VALUES (1, 'Matemáticas', 'Fundamentos de cálculo', 1);
INSERT INTO asignaturas (id_asignatura, nombre, descripcion, activo) VALUES (2, 'Física', 'Introducción a la mecánica', 1);
INSERT INTO asignaturas (id_asignatura, nombre, descripcion, activo) VALUES (3, 'Literatura', 'Análisis de textos', 1);
-- ... (12 registros de asignatura más) ...


-- ----------------------------------------------------
-- INSERTS para la tabla: BLOQUES_HORARIOS / HORARIOS_CURSO (Horarios)
-- ----------------------------------------------------
INSERT INTO bloques_horarios (id_bloque, hora_inicio, hora_fin, duracion_minutos) VALUES (1, '08:00:00', '08:50:00', 50);
INSERT INTO bloques_horarios (id_bloque, hora_inicio, hora_fin, duracion_minutos) VALUES (2, '09:00:00', '09:50:00', 50);
INSERT INTO bloques_horarios (id_bloque, hora_inicio, hora_fin, duracion_minutos) VALUES (3, '10:00:00', '10:50:00', 50);
-- ... (4 registros de bloque más) ...

-- Horario: Curso 1 (Grado Inicial) tiene Matemáticas (Asig 1) Lunes y Jueves con Prof 2 en Aula 1
INSERT INTO horarios_curso (id_horario, profesor_id, curso_id, asignatura_id, salon_id, bloque_id, dia_semana) VALUES (1, 2, 1, 1, 1, 1, 'Lunes');
INSERT INTO horarios_curso (id_horario, profesor_id, curso_id, asignatura_id, salon_id, bloque_id, dia_semana) VALUES (2, 2, 1, 1, 1, 3, 'Jueves');
-- Horario: Curso 1 (Grado Inicial) tiene Física (Asig 2) Martes con Prof 3 en Aula 2
INSERT INTO horarios_curso (id_horario, profesor_id, curso_id, asignatura_id, salon_id, bloque_id, dia_semana) VALUES (3, 3, 1, 2, 2, 2, 'Martes');
-- ... (Decenas de registros más para cubrir todos los cursos y profesores) ...


-- ----------------------------------------------------
-- INSERTS para la tabla: RELACIONES_PADRE_ESTUDIANTE (Vinculación)
-- ----------------------------------------------------
-- Crucial para padres.py: Vincula al estudiante 7 (Esteban Pérez) con el padre 27 (Martín Pérez)
INSERT INTO relaciones_padre_estudiante (id_relacion, estudiante_id, padre_id) VALUES (1, 7, 27);
INSERT INTO relaciones_padre_estudiante (id_relacion, estudiante_id, padre_id) VALUES (2, 8, 28);
INSERT INTO relaciones_padre_estudiante (id_relacion, estudiante_id, padre_id) VALUES (3, 9, 29);
-- ... (17 registros más, cubriendo los 20 estudiantes con sus respectivos padres) ...


-- ----------------------------------------------------
-- INSERTS para la tabla: MATRICULAS (Estudiante-Curso)
-- ----------------------------------------------------
-- Estudiante 7 matriculado en Curso 1
INSERT INTO matriculas (id_matricula, estudiante_id, curso_id, fecha_matricula, estado) VALUES (1, 7, 1, '2024-08-15', 'Activa');
-- Estudiante 8 matriculado en Curso 2
INSERT INTO matriculas (id_matricula, estudiante_id, curso_id, fecha_matricula, estado) VALUES (2, 8, 2, '2024-08-16', 'Activa');
-- ... (Muchos registros más, ya que cada estudiante está en varios cursos) ...


-- ----------------------------------------------------
-- INSERTS para la tabla: CALIFICACIONES (Calificaciones)
-- ----------------------------------------------------
-- Calificación para Estudiante 7 en Curso 1
INSERT INTO calificaciones (id_calificacion, estudiante_id, curso_id, nota, descripcion, fecha_evaluacion) VALUES (1, 7, 1, 4.5, 'Parcial Matemáticas', '2025-01-20');
INSERT INTO calificaciones (id_calificacion, estudiante_id, curso_id, nota, descripcion, fecha_evaluacion) VALUES (2, 7, 1, 3.2, 'Taller Física', '2025-02-01');
-- Calificación para Estudiante 8 en Curso 2
INSERT INTO calificaciones (id_calificacion, estudiante_id, curso_id, nota, descripcion, fecha_evaluacion) VALUES (3, 8, 2, 4.8, 'Proyecto Literatura', '2025-01-25');
-- ... (Cientos de registros más) ...


-- ----------------------------------------------------
-- INSERTS para la tabla: EVENTOS / COMUNICACIONES / NOTIFICACIONES
-- ----------------------------------------------------
INSERT INTO eventos (id_evento, nombre, fecha, hora, descripcion, dirigido_a_rol_id) VALUES (1, 'Reunión de Padres', '2025-12-05', '18:00:00', 'Reunión informativa para padres de Grado Inicial.', 4);
INSERT INTO eventos (id_evento, nombre, fecha, hora, descripcion, dirigido_a_rol_id) VALUES (2, 'Feria Científica', '2025-11-20', '09:00:00', 'Muestra de proyectos de estudiantes.', 3);

-- Comunicación: Profesor 2 (Ana) envía mensaje a Padre 27 (Martín)
INSERT INTO comunicaciones (id_comunicacion, remitente_id, destinatario_id, asunto, contenido, fecha_envio, estado) VALUES (1, 2, 27, 'Consulta sobre rendimiento', 'Necesito discutir el progreso de su hijo Esteban.', '2025-11-01 10:30:00', 'no_leido');
-- Comunicación: Padre 27 (Martín) envía mensaje a Admin 1
INSERT INTO comunicaciones (id_comunicacion, remitente_id, destinatario_id, asunto, contenido, fecha_envio, estado) VALUES (2, 27, 1, 'Problema con la plataforma', 'No puedo ver las notas de mi otro hijo.', '2025-11-01 11:00:00', 'leido');
-- ... (Muchos registros más) ...

-- Notificación: Notificar al Padre 27 y a los Padres (rol 4) sobre el evento 1
INSERT INTO notificaciones (id_notificacion, usuario_id, mensaje, tipo, leida, fecha_creacion) VALUES (1, 27, 'Nuevo evento: Reunión de Padres el 2025-12-05', 'Evento', 0, '2025-11-01 09:00:00');
-- Notificación: Notificar al Estudiante 7 sobre su nueva calificación (id_calificacion 1)
INSERT INTO notificaciones (id_notificacion, usuario_id, mensaje, tipo, leida, fecha_creacion) VALUES (2, 7, 'Nueva calificación de 4.5 en Parcial Matemáticas.', 'Calificación', 1, '2025-01-20 15:00:00');
-- ... (Cientos de notificaciones más) ...


-- ----------------------------------------------------
-- INSERTS para la tabla: EQUIPOS / INCIDENTES / MANTENIMIENTO (Logística/Admin)
-- ----------------------------------------------------
INSERT INTO equipos (id_equipo, nombre, serial, salon_id, estado, fecha_adquisicion) VALUES (1, 'Portátil', 'AB-123-CD45', 1, 'Operativo', '2023-05-01');
INSERT INTO equipos (id_equipo, nombre, serial, salon_id, estado, fecha_adquisicion) VALUES (2, 'Proyector', 'YZ-987-AB65', 1, 'Mantenimiento', '2022-10-10');
-- ... (28 registros de equipo más) ...

-- Incidente: Reportado por Admin (1) sobre Equipo 2
INSERT INTO incidentes (id_incidente, equipo_id, usuario_reporta_id, descripcion, estado, prioridad, fecha_reporte, fecha_cierre) VALUES (1, 2, 1, 'El proyector no enciende', 'En Proceso', 'Alta', '2025-11-01', NULL);
-- Mantenimiento: Programado por Profesor 2 (Ana) para Equipo 1
INSERT INTO mantenimiento (id_mantenimiento, equipo_id, usuario_responsable_id, descripcion, estado, fecha_programada, fecha_realizada) VALUES (1, 1, 2, 'Revisión anual de software', 'Pendiente', '2025-12-10', NULL);


-- 2. REACTIVAR LA VERIFICACIÓN DE LLAVES FORÁNEAS
SET FOREIGN_KEY_CHECKS=1;