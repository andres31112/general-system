#esta seccion se dividen los permisoso por roles
ROLE_PERMISSIONS = {
    # Permisos para el rol de Super Admin
    'Super Admin': [
        'gestion_usuarios', 'gestion_asignaturas', 'registro_calificaciones',
        'gestion_comunicados', 'gestion_inventario', 'gestion_matriculas',
        'gestion_electoral', 'crear_roles', 'ver_roles', 'editar_roles', 'eliminar_roles',
        'gestion_eventos','jornada_electoral', 'acceso_reportes'
    ],
    # permisos para el rol profesor
    'Profesor': [
        'ver_calificaciones_propias', 'ver_horario_clases', 'ver_lista_estudiantes',
        'registrar_calificaciones', 'gestion_comunicados_profesor', 'gestion_comunicaciones'
    ],
    # permisos para el rol estudiante
    'Estudiante': [
        'ver_calificaciones', 'ver_horario', 'ver_historial_academico',
        'inscripcion_materias', 'ver_comunicaciones_estudiante', 'ver_estado_cuenta',
        'editar_perfil', 'acceso_soporte', 'eleccion_electoral','ver.eventos', 'ver_equipos'
    ],
    # permisos para el rol padre
    'Padre': [
        'ver_calificaciones_hijo', 'ver_horario_hijo', 'ver_comunicaciones_padre',
        'gestion_comunicaciones', 'acceso_soporte'
    ]
}
