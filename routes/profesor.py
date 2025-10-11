from flask import Blueprint, render_template, session, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from controllers.models import (
    db, Usuario, Asignatura, Clase, Matricula, Calificacion, Curso,
    Asistencia, CategoriaCalificacion, HorarioCompartido, HorarioCurso,
    HorarioGeneral, Salon, Sede, Evento
)
from datetime import datetime, date
import json

profesor_bp = Blueprint('profesor', __name__, url_prefix='/profesor')

# ============================================================================ #
# FUNCIONES AUXILIARES
# ============================================================================ #

def obtener_cursos_del_profesor(profesor_id):
    """Obtiene todos los cursos únicos del profesor basado en horarios compartidos y clases."""
    try:
        # Cursos desde HorarioCompartido - CORREGIDO
        cursos_horarios = db.session.query(Curso).join(
            HorarioCompartido, HorarioCompartido.curso_id == Curso.id_curso  # ✅ id_curso en lugar de id
        ).filter(
            HorarioCompartido.profesor_id == profesor_id
        ).distinct().all()
    except Exception as e:
        flash(f'Error en la consulta de cursos por horario: {str(e)}', 'error')
        cursos_horarios = []

    # Cursos desde Clase - CORREGIDO
    try:
        cursos_clases = db.session.query(Curso).join(
            Clase, Clase.cursoId == Curso.id_curso  # ✅ id_curso en lugar de id
        ).filter(
            Clase.profesorId == profesor_id
        ).distinct().all()
    except Exception as e:
        flash(f'Error en la consulta de cursos por clase: {str(e)}', 'error')
        cursos_clases = []

    # Combinar y eliminar duplicados manteniendo objetos Curso
    todos = {c.id_curso: c for c in (cursos_horarios + cursos_clases)}.values()  # ✅ id_curso
    todos_cursos = list(todos)

    # Agregar total de estudiantes por curso
    for curso in todos_cursos:
        curso.total_estudiantes = len(obtener_estudiantes_por_curso(curso.id_curso))  # ✅ id_curso

    return todos_cursos
    """Obtiene todos los cursos únicos del profesor basado en horarios compartidos y clases."""
    try:
        # Cursos desde HorarioCompartido (más directo y sin ambigüedad)
        cursos_horarios = db.session.query(Curso).join(
            HorarioCompartido, HorarioCompartido.curso_id == Curso.id
        ).filter(
            HorarioCompartido.profesor_id == profesor_id
        ).distinct().all()
    except Exception as e:
        flash(f'Error en la consulta de cursos por horario: {str(e)}', 'error')
        cursos_horarios = []

    # Cursos desde Clase
    try:
        cursos_clases = db.session.query(Curso).join(
            Clase, Clase.cursoId == Curso.id
        ).filter(
            Clase.profesorId == profesor_id
        ).distinct().all()
    except Exception as e:
        flash(f'Error en la consulta de cursos por clase: {str(e)}', 'error')
        cursos_clases = []

    # Combinar y eliminar duplicados manteniendo objetos Curso
    todos = {c.id: c for c in (cursos_horarios + cursos_clases)}.values()
    todos_cursos = list(todos)

    # Agregar total de estudiantes por curso (atributo dinámico usado por templates)
    for curso in todos_cursos:
        curso.total_estudiantes = len(obtener_estudiantes_por_curso(curso.id))

    return todos_cursos

def obtener_horarios_detallados_profesor(profesor_id):
    """Obtiene horarios compartidos con detalles completos."""
    horarios = HorarioCompartido.query.filter_by(profesor_id=profesor_id).all()
    horarios_detallados = []

    for hcomp in horarios:
        # Buscar el HorarioCurso que coincida - CORREGIDO
        horario_curso = HorarioCurso.query.filter_by(
            curso_id=hcomp.curso_id,
            asignatura_id=hcomp.asignatura_id,
            horario_general_id=hcomp.horario_general_id
        ).first()

        # Fallback: si no existe una coincidencia exacta, intentar por curso + asignatura
        if not horario_curso:
            horario_curso = HorarioCurso.query.filter_by(
                curso_id=hcomp.curso_id,
                asignatura_id=hcomp.asignatura_id
            ).first()

        curso = Curso.query.get(hcomp.curso_id)
        asignatura = Asignatura.query.get(hcomp.asignatura_id)
        horario_general = HorarioGeneral.query.get(hcomp.horario_general_id) if hcomp.horario_general_id else None

        # Salon - CORREGIDO
        salon = None
        if horario_curso and getattr(horario_curso, 'id_salon_fk', None):
            salon = Salon.query.get(horario_curso.id_salon_fk)

        sede = None
        if curso and getattr(curso, 'sedeId', None):
            sede = Sede.query.get(curso.sedeId)

        horarios_detallados.append({
            'curso_nombre': curso.nombreCurso if curso else 'N/A',  # ✅ curso_nombre
            'asignatura_nombre': asignatura.nombre if asignatura else 'N/A',  # ✅ asignatura_nombre
            'dia_semana': horario_curso.dia_semana if horario_curso and getattr(horario_curso, 'dia_semana', None) else (horario_general.nombre if horario_general else 'N/A'),  # ✅ dia_semana
            'hora_inicio': (
                horario_curso.hora_inicio if horario_curso and getattr(horario_curso, 'hora_inicio', None)
                else (horario_general.horaInicio.strftime('%H:%M') if horario_general and horario_general.horaInicio else 'N/A')
            ),
            'hora_fin': (
                horario_curso.hora_fin if horario_curso and getattr(horario_curso, 'hora_fin', None)  # ✅ hora_fin de HorarioCurso
                else (horario_general.horaFin.strftime('%H:%M') if horario_general and horario_general.horaFin else 'N/A')
            ),
            'salon': salon.nombre if salon else 'N/A',
            'sede': sede.nombre if sede else 'N/A',
            'origen_id_horario_curso': horario_curso.id_horario_curso if horario_curso else None  # ✅ id_horario_curso
        })

    return horarios_detallados
    """Obtiene horarios compartidos con detalles completos."""
    horarios = HorarioCompartido.query.filter_by(profesor_id=profesor_id).all()
    horarios_detallados = []

    for hcomp in horarios:
        # Buscar el HorarioCurso que coincida en curso/asignatura/horario_general (si existe)
        horario_curso = HorarioCurso.query.filter_by(
            curso_id=hcomp.curso_id,
            asignatura_id=hcomp.asignatura_id,
            horario_general_id=hcomp.horario_general_id
        ).first()

        # Fallback: si no existe una coincidencia exacta, intentar por curso + asignatura
        if not horario_curso:
            horario_curso = HorarioCurso.query.filter_by(
                curso_id=hcomp.curso_id,
                asignatura_id=hcomp.asignatura_id
            ).first()

        curso = Curso.query.get(hcomp.curso_id)
        asignatura = Asignatura.query.get(hcomp.asignatura_id)
        horario_general = HorarioGeneral.query.get(hcomp.horario_general_id) if hcomp.horario_general_id else None

        # Salon: en HorarioCurso el campo es id_salon_fk
        salon = None
        if horario_curso and getattr(horario_curso, 'id_salon_fk', None):
            salon = Salon.query.get(horario_curso.id_salon_fk)

        sede = None
        if curso and getattr(curso, 'sedeId', None):
            sede = Sede.query.get(curso.sedeId)

        horarios_detallados.append({
            'curso': curso.nombreCurso if curso else 'N/A',
            'asignatura': asignatura.nombre if asignatura else 'N/A',
            'dia': horario_curso.dia_semana if horario_curso and getattr(horario_curso, 'dia_semana', None) else (horario_general.nombre if horario_general else 'N/A'),
            'hora_inicio': (
                horario_curso.hora_inicio if horario_curso and getattr(horario_curso, 'hora_inicio', None)
                else (horario_general.horaInicio.strftime('%H:%M') if horario_general and horario_general.horaInicio else 'N/A')
            ),
            'hora_fin': (
                horario_general.horaFin.strftime('%H:%M') if horario_general and horario_general.horaFin else 'N/A'
            ),
            'salon': salon.nombre if salon else 'N/A',
            'sede': sede.nombre if sede else 'N/A',
            'origen_id_horario_curso': horario_curso.id if horario_curso else None
        })

    return horarios_detallados

def verificar_acceso_curso_profesor(profesor_id, curso_id):
    """Verifica si el profesor tiene acceso a un curso específico (por HorarioCompartido o Clase)."""
    # Verificar en HorarioCompartido
    acceso_horario = HorarioCompartido.query.filter_by(
        profesor_id=profesor_id,
        curso_id=curso_id
    ).first()

    # Verificar en Clase
    acceso_clase = Clase.query.filter_by(profesorId=profesor_id, cursoId=curso_id).first()

    return bool(acceso_horario or acceso_clase)

def obtener_estudiantes_por_curso(curso_id):
    """Obtiene estudiantes matriculados en un curso."""
    if not curso_id:
        return []
    estudiantes = db.session.query(Usuario).join(
        Matricula, Matricula.estudianteId == Usuario.id_usuario
    ).filter(
        Matricula.cursoId == curso_id,
        Usuario.rol.has(nombre='Estudiante')
    ).order_by(Usuario.apellido, Usuario.nombre).all()
    return estudiantes

def obtener_asignaturas_por_curso_y_profesor(curso_id, profesor_id):
    """Obtiene asignaturas asignadas al profesor en un curso específico."""
    if not curso_id:
        return []

    try:
        # CORREGIDO: usar id_asignatura en lugar de id
        asignaturas_horario = db.session.query(Asignatura).join(
            HorarioCompartido, HorarioCompartido.asignatura_id == Asignatura.id_asignatura
        ).filter(
            HorarioCompartido.curso_id == curso_id,
            HorarioCompartido.profesor_id == profesor_id
        ).distinct().all()
    except Exception as e:
        flash(f'Error al obtener asignaturas (horario): {str(e)}', 'error')
        asignaturas_horario = []

    # Desde la tabla Clase - CORREGIDO
    try:
        asignaturas_clase = db.session.query(Asignatura).join(
            Clase, Clase.asignaturaId == Asignatura.id_asignatura  # ✅ id_asignatura
        ).filter(
            Clase.cursoId == curso_id,
            Clase.profesorId == profesor_id
        ).distinct().all()
    except Exception as e:
        flash(f'Error al obtener asignaturas (clase): {str(e)}', 'error')
        asignaturas_clase = []

    # Unir y retornar sin duplicados
    asignaturas = {a.id_asignatura: a for a in (asignaturas_horario + asignaturas_clase)}.values()  # ✅ id_asignatura
    return list(asignaturas)
    """Obtiene asignaturas asignadas al profesor en un curso específico."""
    if not curso_id:
        return []

    try:
        asignaturas_horario = db.session.query(Asignatura).join(
            HorarioCompartido, HorarioCompartido.asignatura_id == Asignatura.id
        ).filter(
            HorarioCompartido.curso_id == curso_id,
            HorarioCompartido.profesor_id == profesor_id
        ).distinct().all()
    except Exception as e:
        flash(f'Error al obtener asignaturas (horario): {str(e)}', 'error')
        asignaturas_horario = []

    # Desde la tabla Clase
    try:
        asignaturas_clase = db.session.query(Asignatura).join(
            Clase, Clase.asignaturaId == Asignatura.id
        ).filter(
            Clase.cursoId == curso_id,
            Clase.profesorId == profesor_id
        ).distinct().all()
    except Exception as e:
        flash(f'Error al obtener asignaturas (clase): {str(e)}', 'error')
        asignaturas_clase = []

    # Unir y retornar sin duplicados
    asignaturas = {a.id: a for a in (asignaturas_horario + asignaturas_clase)}.values()
    return list(asignaturas)

def obtener_asignaturas_del_profesor(profesor_id):
    """Obtiene todas las asignaturas del profesor (todas las sedes/ cursos)."""
    try:
        # CORREGIDO: usar id_asignatura
        asignaturas_horario = db.session.query(Asignatura).join(
            HorarioCompartido, HorarioCompartido.asignatura_id == Asignatura.id_asignatura
        ).filter(
            HorarioCompartido.profesor_id == profesor_id
        ).distinct().all()
    except Exception as e:
        flash(f'Error al obtener asignaturas del profesor (horario): {str(e)}', 'error')
        asignaturas_horario = []

    try:
        asignaturas_clase = db.session.query(Asignatura).join(
            Clase, Clase.asignaturaId == Asignatura.id_asignatura  # ✅ id_asignatura
        ).filter(
            Clase.profesorId == profesor_id
        ).distinct().all()
    except Exception as e:
        flash(f'Error al obtener asignaturas del profesor (clase): {str(e)}', 'error')
        asignaturas_clase = []

    asignaturas = {a.id_asignatura: a for a in (asignaturas_horario + asignaturas_clase)}.values()  # ✅ id_asignatura
    return list(asignaturas)
    """Obtiene todas las asignaturas del profesor (todas las sedes/ cursos)."""
    try:
        asignaturas_horario = db.session.query(Asignatura).join(
            HorarioCompartido, HorarioCompartido.asignatura_id == Asignatura.id
        ).filter(
            HorarioCompartido.profesor_id == profesor_id
        ).distinct().all()
    except Exception as e:
        flash(f'Error al obtener asignaturas del profesor (horario): {str(e)}', 'error')
        asignaturas_horario = []

    try:
        asignaturas_clase = db.session.query(Asignatura).join(
            Clase, Clase.asignaturaId == Asignatura.id
        ).filter(
            Clase.profesorId == profesor_id
        ).distinct().all()
    except Exception as e:
        flash(f'Error al obtener asignaturas del profesor (clase): {str(e)}', 'error')
        asignaturas_clase = []

    asignaturas = {a.id: a for a in (asignaturas_horario + asignaturas_clase)}.values()
    return list(asignaturas)

def obtener_calificaciones_por_curso(curso_id):
    """Obtiene todas las calificaciones de un curso (uniendo con Clase para filtrar por curso)."""
    if not curso_id:
        return []
    # Unir Calificacion con Clase por asignatura para determinar curso
    califs = db.session.query(Calificacion).join(
        Clase, Clase.asignaturaId == Calificacion.asignaturaId
    ).filter(
        Clase.cursoId == curso_id
    ).all()
    return califs

def obtener_asistencias_por_curso(curso_id):
    """Obtiene todas las asistencias de un curso (uniendo con Clase)."""
    if not curso_id:
        return []
    asistencias = db.session.query(Asistencia).join(
        Clase, Asistencia.claseId == Clase.id
    ).filter(
        Clase.cursoId == curso_id
    ).all()
    return asistencias

def obtener_clase_para_asistencia(curso_id, profesor_id):
    """Obtiene el ID de una clase para registrar asistencia."""
    clase = Clase.query.filter_by(cursoId=curso_id, profesorId=profesor_id).first()
    return clase.id if clase else None

def guardar_o_actualizar_asistencia(estudiante_id, clase_id, fecha, estado):
    """Guarda o actualiza una asistencia. Asistencia NO tiene campo curso_id en tu modelo."""
    asistencia_existente = Asistencia.query.filter_by(
        estudianteId=estudiante_id,
        claseId=clase_id,
        fecha=fecha
    ).first()

    if asistencia_existente:
        asistencia_existente.estado = estado
    else:
        nueva_asistencia = Asistencia(
            estudianteId=estudiante_id,
            claseId=clase_id,
            fecha=fecha,
            estado=estado
        )
        db.session.add(nueva_asistencia)

def validar_estudiante_en_curso(estudiante_id, curso_id):
    """Valida que un estudiante esté matriculado en un curso."""
    return Matricula.query.filter_by(
        estudianteId=estudiante_id,
        cursoId=curso_id
    ).first() is not None

def verificar_asignatura_profesor_en_curso(asignatura_id, profesor_id, curso_id):
    """Verifica si el profesor tiene una asignatura en un curso (por HorarioCompartido o Clase)."""
    acceso_horario = HorarioCompartido.query.filter_by(
        profesor_id=profesor_id,
        curso_id=curso_id,
        asignatura_id=asignatura_id
    ).first()

    acceso_clase = Clase.query.filter_by(
        profesorId=profesor_id,
        cursoId=curso_id,
        asignaturaId=asignatura_id
    ).first()

    return bool(acceso_horario or acceso_clase)

def calcular_pendientes(profesor_id, curso_id):
    """Calcula tareas pendientes (asistencias no registradas para hoy)."""
    if not curso_id:
        return 0
    today = date.today()
    estudiantes = obtener_estudiantes_por_curso(curso_id)
    clase_id = obtener_clase_para_asistencia(curso_id, profesor_id)
    if not clase_id:
        return 0
    asistencias_hoy = Asistencia.query.filter_by(
        claseId=clase_id,
        fecha=today
    ).count()
    return len(estudiantes) - asistencias_hoy

# ============================================================================ #
# RUTAS PRINCIPALES
# ============================================================================ #

@profesor_bp.route('/dashboard')
@login_required
def dashboard():
    """Panel principal del profesor con horarios compartidos."""
    curso_id = session.get('curso_seleccionado')
    curso_actual = Curso.query.get(curso_id) if curso_id else None

    try:
        horarios_detallados = obtener_horarios_detallados_profesor(current_user.id_usuario)
    except Exception as e:
        flash(f'Error al cargar horarios: {str(e)}', 'error')
        horarios_detallados = []

    clases = Clase.query.filter_by(profesorId=current_user.id_usuario).all()

    estudiantes_total = len(obtener_estudiantes_por_curso(curso_id)) if curso_id else 0
    asignaturas_total = len(obtener_asignaturas_del_profesor(current_user.id_usuario))
    pendientes_total = calcular_pendientes(current_user.id_usuario, curso_id)
    mensajes_total = 0  # Placeholder hasta implementar modelo de mensajes

    return render_template('profesores/dashboard.html',
                         clases=clases,
                         curso_actual=curso_actual,
                         horarios_detallados=horarios_detallados,
                         estudiantes_total=estudiantes_total,
                         asignaturas_total=asignaturas_total,
                         pendientes_total=pendientes_total,
                         mensajes_total=mensajes_total)

@profesor_bp.route('/seleccionar-curso')
@login_required
def seleccionar_curso():
    """Permite al profesor seleccionar un curso para trabajar."""
    try:
        cursos = obtener_cursos_del_profesor(current_user.id_usuario)
    except Exception as e:
        flash(f'Error al cargar cursos: {str(e)}', 'error')
        cursos = []
    return render_template('profesores/seleccionar_curso.html', cursos=cursos)

@profesor_bp.route('/guardar-curso-seleccionado', methods=['POST'])
@login_required
def guardar_curso_seleccionado():
    """Guarda el curso seleccionado en la sesión y redirige a gestión LC."""
    curso_id = request.form.get('curso_id')

    if not curso_id:
        flash('Por favor selecciona un curso', 'error')
        return redirect(url_for('profesor.seleccionar_curso'))

    curso_id = int(curso_id)
    try:
        if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
            flash('No tienes acceso a este curso', 'error')
            return redirect(url_for('profesor.seleccionar_curso'))

        session['curso_seleccionado'] = curso_id
        curso = Curso.query.get(curso_id)
        flash(f'Curso "{curso.nombreCurso}" seleccionado correctamente', 'success')
        return redirect(url_for('profesor.gestion_lc'))
    except Exception as e:
        flash(f'Error al seleccionar curso: {str(e)}', 'error')
        return redirect(url_for('profesor.seleccionar_curso'))

@profesor_bp.route('/gestion-lc')
@login_required
def gestion_lc():
    """Página unificada de gestión de listas y calificaciones."""
    curso_id = session.get('curso_seleccionado')

    if not curso_id:
        flash('Primero debes seleccionar un curso', 'warning')
        return redirect(url_for('profesor.seleccionar_curso'))

    if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
        flash('No tienes acceso a este curso', 'error')
        return redirect(url_for('profesor.seleccionar_curso'))

    curso = Curso.query.get(curso_id)
    estudiantes = obtener_estudiantes_por_curso(curso_id)
    asignaturas = obtener_asignaturas_por_curso_y_profesor(curso_id, current_user.id_usuario)
    categorias = CategoriaCalificacion.query.all()
    calificaciones = obtener_calificaciones_por_curso(curso_id)

    session.pop('flash_messages', None)
    return render_template('profesores/Gestion_LC.html',
                         curso=curso,
                         estudiantes=estudiantes,
                         asignaturas=asignaturas,
                         categorias=categorias,
                         calificaciones=calificaciones)

# ============================================================================ #
# RUTAS SECUNDARIAS
# ============================================================================ #

@profesor_bp.route('/ver_lista_estudiantes')
@login_required
def ver_lista_estudiantes():
    """Muestra la lista de estudiantes del curso seleccionado."""
    curso_id = session.get('curso_seleccionado')

    if not curso_id:
        flash('Primero debes seleccionar un curso', 'warning')
        return redirect(url_for('profesor.seleccionar_curso'))

    if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
        flash('No tienes acceso a este curso', 'error')
        return redirect(url_for('profesor.seleccionar_curso'))

    estudiantes = obtener_estudiantes_por_curso(curso_id)
    curso = Curso.query.get(curso_id)

    return render_template('profesores/ver_lista_estudiantes.html',
                         estudiantes=estudiantes,
                         curso=curso)

@profesor_bp.route('/registrar_calificaciones')
@login_required
def registrar_calificaciones():
    """Permite al profesor registrar y editar calificaciones."""
    curso_id = session.get('curso_seleccionado')

    if not curso_id:
        flash('Primero debes seleccionar un curso', 'warning')
        return redirect(url_for('profesor.seleccionar_curso'))

    if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
        flash('No tienes acceso a este curso', 'error')
        return redirect(url_for('profesor.seleccionar_curso'))

    estudiantes = obtener_estudiantes_por_curso(curso_id)
    asignaturas = obtener_asignaturas_por_curso_y_profesor(curso_id, current_user.id_usuario)
    categorias = CategoriaCalificacion.query.all()
    calificaciones = obtener_calificaciones_por_curso(curso_id)
    curso = Curso.query.get(curso_id)

    return render_template('profesores/registrar_calificaciones.html',
                         estudiantes=estudiantes,
                         asignaturas=asignaturas,
                         categorias=categorias,
                         calificaciones=calificaciones,
                         curso=curso)

@profesor_bp.route('/asistencia')
@login_required
def asistencia():
    """Página para gestionar asistencias."""
    curso_id = session.get('curso_seleccionado')

    if not curso_id:
        flash('Primero debes seleccionar un curso', 'warning')
        return redirect(url_for('profesor.seleccionar_curso'))

    if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
        flash('No tienes acceso a este curso', 'error')
        return redirect(url_for('profesor.seleccionar_curso'))

    estudiantes = obtener_estudiantes_por_curso(curso_id)
    clases = Clase.query.filter_by(cursoId=curso_id, profesorId=current_user.id_usuario).all()
    asistencias = obtener_asistencias_por_curso(curso_id)
    curso = Curso.query.get(curso_id)

    return render_template('profesores/asistencia.html',
                         estudiantes=estudiantes,
                         clases=clases,
                         asistencias=asistencias,
                         curso=curso)

@profesor_bp.route('/ver_horario_clases')
@login_required
def ver_horario_clases():
    """Muestra el horario de clases del profesor."""
    try:
        horarios_detallados = obtener_horarios_detallados_profesor(current_user.id_usuario)
    except Exception as e:
        flash(f'Error al cargar horarios: {str(e)}', 'error')
        horarios_detallados = []
    clases = Clase.query.filter_by(profesorId=current_user.id_usuario).all()

    return render_template('profesores/HorarioC.html',
                         horarios_detallados=horarios_detallados,
                         clases=clases)

@profesor_bp.route('/comunicaciones')
@login_required
def comunicaciones():
    """Página para ver y enviar comunicaciones a estudiantes y padres."""
    return render_template('profesores/comunicaciones.html')

@profesor_bp.route('/cursos')
@login_required
def cursos():
    """Página para gestionar cursos del profesor."""
    try:
        cursos = obtener_cursos_del_profesor(current_user.id_usuario)
    except Exception as e:
        flash(f'Error al cargar cursos: {str(e)}', 'error')
        cursos = []
    return render_template('profesores/cursos.html', cursos=cursos)

@profesor_bp.route('/asignaturas')
@login_required
def asignaturas():
    """Página para gestionar asignaturas del profesor."""
    try:
        asignaturas = obtener_asignaturas_del_profesor(current_user.id_usuario)
    except Exception as e:
        flash(f'Error al cargar asignaturas: {str(e)}', 'error')
        asignaturas = []
    return render_template('profesores/asignaturas.html', asignaturas=asignaturas)

@profesor_bp.route('/perfil')
@login_required
def perfil():
    """Página para gestionar la información del perfil del profesor."""
    try:
        total_cursos = len(obtener_cursos_del_profesor(current_user.id_usuario))
        total_asignaturas = len(obtener_asignaturas_del_profesor(current_user.id_usuario))
        total_horarios = len(HorarioCompartido.query.filter_by(profesor_id=current_user.id_usuario).all())
    except Exception as e:
        flash(f'Error al cargar datos del perfil: {str(e)}', 'error')
        total_cursos = total_asignaturas = total_horarios = 0

    return render_template('profesores/perfil.html',
                         total_cursos=total_cursos,
                         total_asignaturas=total_asignaturas,
                         total_horarios=total_horarios)

@profesor_bp.route('/soporte')
@login_required
def soporte():
    """Página de soporte para el profesor."""
    return render_template('profesores/soporte.html')

# ============================================================================ #
# APIs - HORARIOS Y CURSOS
# ============================================================================ #

@profesor_bp.route('/api/mis-horarios')
@login_required
def api_mis_horarios():
    """API para obtener los horarios compartidos del profesor."""
    try:
        horarios_detallados = obtener_horarios_detallados_profesor(current_user.id_usuario)
        return jsonify({
            'success': True,
            'horarios': horarios_detallados,
            'total': len(horarios_detallados)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener horarios: {str(e)}'}), 500


@profesor_bp.route('/api/mis-cursos')
@login_required
def api_mis_cursos():
    """API para obtener los cursos del profesor."""
    try:
        cursos = obtener_cursos_del_profesor(current_user.id_usuario)
        cursos_data = [{
            'id': curso.id_curso,  # ✅ id_curso en lugar de id
            'nombre': curso.nombreCurso,
            'sede': curso.sede.nombre if getattr(curso, 'sede', None) else 'N/A',
            'director': 'No asignado',
            'total_estudiantes': getattr(curso, 'total_estudiantes', 0)
        } for curso in cursos]
        return jsonify({
            'success': True,
            'cursos': cursos_data,
            'total': len(cursos_data)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener cursos: {str(e)}'}), 500

# ============================================================================ #
# APIs - ASISTENCIAS
# ============================================================================ #

@profesor_bp.route('/api/obtener-asistencias', methods=['GET'])
@login_required
def api_obtener_asistencias():
    """API para obtener asistencias de un mes específico."""
    try:
        curso_id = session.get('curso_seleccionado')
        año = request.args.get('año', type=int)
        mes = request.args.get('mes', type=int)

        if not curso_id:
            return jsonify({'success': False, 'message': 'No hay curso seleccionado'}), 400

        if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes acceso a este curso'}), 403

        asistencias = db.session.query(Asistencia).join(
            Clase, Asistencia.claseId == Clase.id
        ).filter(
            Clase.cursoId == curso_id,
            Clase.profesorId == current_user.id_usuario,
            db.extract('year', Asistencia.fecha) == año,
            db.extract('month', Asistencia.fecha) == mes
        ).all()

        asistencias_data = [{
            'estudiante_id': a.estudianteId,
            'fecha': a.fecha.strftime('%Y-%m-%d'),
            'estado': a.estado
        } for a in asistencias]

        return jsonify({'success': True, 'asistencias': asistencias_data})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener asistencias: {str(e)}'}), 500

@profesor_bp.route('/api/guardar-asistencia', methods=['POST'])
@login_required
def api_guardar_asistencia():
    """API para guardar asistencias."""
    try:
        data = request.get_json()
        fecha_str = data.get('fecha')
        asistencias = data.get('asistencias', [])
        curso_id = session.get('curso_seleccionado')

        if not curso_id:
            return jsonify({'success': False, 'message': 'No hay curso seleccionado'}), 400

        if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes acceso a este curso'}), 403

        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        clase_id = obtener_clase_para_asistencia(curso_id, current_user.id_usuario)

        if not clase_id:
            return jsonify({'success': False, 'message': 'No hay clases asignadas para este curso'}), 400

        for asistencia_data in asistencias:
            estudiante_id = asistencia_data.get('estudiante_id')
            estado = asistencia_data.get('estado')
            if not validar_estudiante_en_curso(estudiante_id, curso_id):
                continue
            guardar_o_actualizar_asistencia(estudiante_id, clase_id, fecha, estado)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Asistencias guardadas correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al guardar asistencias: {str(e)}'}), 500

# ============================================================================ #
# APIs - CALIFICACIONES
# ============================================================================ #

@profesor_bp.route('/api/obtener-calificaciones', methods=['GET'])
@login_required
def obtener_calificaciones_api():
    """API para obtener calificaciones del curso."""
    try:
        curso_id = session.get('curso_seleccionado')

        if not curso_id:
            return jsonify({'success': False, 'message': 'No hay curso seleccionado'}), 400

        if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes acceso a este curso'}), 403

        # Traer calificaciones que correspondan al curso uniendo por Clase -> asignatura
        rows = db.session.query(
            Calificacion, Usuario, Asignatura, CategoriaCalificacion
        ).join(
            Usuario, Usuario.id_usuario == Calificacion.estudianteId
        ).join(
            Asignatura, Asignatura.id == Calificacion.asignaturaId
        ).join(
            CategoriaCalificacion, CategoriaCalificacion.id == Calificacion.categoriaId
        ).join(
            Clase, Clase.asignaturaId == Calificacion.asignaturaId
        ).filter(
            Clase.cursoId == curso_id
        ).all()

        calificaciones_data = []
        for cal, usuario, asign, cat in rows:
            calificaciones_data.append({
                'id': cal.id,
                'estudiante_id': cal.estudianteId,
                'estudiante_nombre': f"{usuario.nombre} {usuario.apellido}",
                'asignatura_id': cal.asignaturaId,
                'asignatura_nombre': asign.nombre if asign else '',
                'categoria_id': cal.categoriaId,
                'categoria_nombre': cat.nombre if cat else '',
                'valor': float(cal.valor) if cal.valor is not None else None,
                'observaciones': cal.observaciones
            })

        return jsonify({'success': True, 'calificaciones': calificaciones_data})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener calificaciones: {str(e)}'}), 500

@profesor_bp.route('/api/guardar-calificacion', methods=['POST'])
@login_required
def guardar_calificacion():
    """API para guardar/actualizar calificaciones."""
    try:
        data = request.get_json()
        estudiante_id = data.get('estudiante_id')
        asignatura_id = data.get('asignatura_id')
        categoria_id = data.get('categoria_id')
        valor = data.get('valor')
        observaciones = data.get('observaciones', '')
        curso_id = session.get('curso_seleccionado')

        if not curso_id:
            return jsonify({'success': False, 'message': 'No hay curso seleccionado'}), 400

        if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes acceso a este curso'}), 403

        if not validar_estudiante_en_curso(estudiante_id, curso_id):
            return jsonify({'success': False, 'message': 'El estudiante no pertenece a este curso'}), 400

        if not verificar_asignatura_profesor_en_curso(asignatura_id, current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes esta asignatura en el curso'}), 403

        # Buscar calificación existente (sin curso_id porque el modelo no lo tiene)
        calificacion_existente = Calificacion.query.filter_by(
            estudianteId=estudiante_id,
            asignaturaId=asignatura_id,
            categoriaId=categoria_id
        ).first()

        if calificacion_existente:
            calificacion_existente.valor = valor
            calificacion_existente.observaciones = observaciones
        else:
            nueva_calificacion = Calificacion(
                estudianteId=estudiante_id,
                asignaturaId=asignatura_id,
                categoriaId=categoria_id,
                valor=valor,
                observaciones=observaciones
            )
            db.session.add(nueva_calificacion)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Calificación guardada correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al guardar calificación: {str(e)}'}), 500

# ============================================================================ #
# APIs - ASIGNATURAS
# ============================================================================ #

@profesor_bp.route('/api/agregar-asignatura', methods=['POST'])
@login_required
def agregar_asignatura():
    """API para agregar una nueva asignatura al curso."""
    try:
        data = request.get_json()
        curso_id = session.get('curso_seleccionado')
        nombre = data.get('nombre')

        if not curso_id:
            return jsonify({'success': False, 'message': 'No hay curso seleccionado'}), 400

        if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes acceso a este curso'}), 403

        if not nombre or not nombre.strip():
            return jsonify({'success': False, 'message': 'El nombre de la asignatura es requerido'}), 400

        # Crear nueva asignatura
        nueva_asignatura = Asignatura(nombre=nombre.strip())
        db.session.add(nueva_asignatura)
        db.session.flush()

        # Obtener el ID correcto de la asignatura - CORREGIDO
        asignatura_id = nueva_asignatura.id_asignatura  # ✅ id_asignatura

        id_horario_general = data.get('horario_general_id')
        if not id_horario_general:
            horario_general = HorarioGeneral.query.first()
            if not horario_general:
                db.session.rollback()
                return jsonify({'success': False, 'message': 'No hay horarios generales disponibles'}), 400
            id_horario_general = horario_general.id_horario  # ✅ id_horario

        # Crear HorarioCurso - CORREGIDO
        horario_curso = HorarioCurso(
            curso_id=curso_id,
            asignatura_id=asignatura_id,  # ✅ usar la variable correcta
            horario_general_id=id_horario_general,
            dia_semana=data.get('dia_semana', 'Lunes'),
            hora_inicio=data.get('hora_inicio', '07:00'),
            hora_fin=data.get('hora_fin', '07:45'),  # ✅ Asegurar que hora_fin tenga valor
            id_salon_fk=data.get('id_salon_fk', None)
        )
        db.session.add(horario_curso)
        db.session.flush()

        # Crear HorarioCompartido para asociar al profesor
        horario_compartido = HorarioCompartido(
            profesor_id=current_user.id_usuario,
            curso_id=curso_id,
            asignatura_id=asignatura_id,  # ✅ usar la variable correcta
            horario_general_id=id_horario_general,
            fecha_compartido=datetime.utcnow()
        )
        db.session.add(horario_compartido)

        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Asignatura añadida correctamente',
            'asignatura_id': asignatura_id  # ✅ id_asignatura
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al añadir asignatura: {str(e)}'}), 500
    
@profesor_bp.route('/api/editar-asignatura', methods=['POST'])
@login_required
def editar_asignatura():
    """API para editar el nombre de una asignatura."""
    try:
        data = request.get_json()
        asignatura_id = data.get('asignatura_id')
        nombre = data.get('nombre')
        curso_id = session.get('curso_seleccionado')

        if not curso_id:
            return jsonify({'success': False, 'message': 'No hay curso seleccionado'}), 400

        if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes acceso a este curso'}), 403

        if not verificar_asignatura_profesor_en_curso(asignatura_id, current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes esta asignatura en el curso'}), 403

        if not nombre or not nombre.strip():
            return jsonify({'success': False, 'message': 'El nombre de la asignatura es requerido'}), 400

        asignatura = Asignatura.query.get(asignatura_id)
        if not asignatura:
            return jsonify({'success': False, 'message': 'Asignatura no encontrada'}), 404

        asignatura.nombre = nombre.strip()
        db.session.commit()
        return jsonify({'success': True, 'message': 'Asignatura actualizada correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al actualizar asignatura: {str(e)}'}), 500

@profesor_bp.route('/api/eliminar-asignatura', methods=['POST'])
@login_required
def eliminar_asignatura():
    """API para eliminar una asignatura y sus calificaciones asociadas."""
    try:
        data = request.get_json()
        asignatura_id = data.get('asignatura_id')
        curso_id = session.get('curso_seleccionado')

        if not curso_id:
            return jsonify({'success': False, 'message': 'No hay curso seleccionado'}), 400

        if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes acceso a este curso'}), 403

        if not verificar_asignatura_profesor_en_curso(asignatura_id, current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes esta asignatura en el curso'}), 403

        # Eliminar calificaciones relacionadas con esa asignatura (sin filtrar por curso porque el modelo no tiene curso_id)
        Calificacion.query.filter_by(asignaturaId=asignatura_id).delete()

        # Eliminar entradas en HorarioCompartido y HorarioCurso para ese curso + asignatura
        HorarioCompartido.query.filter_by(asignatura_id=asignatura_id, curso_id=curso_id).delete()
        HorarioCurso.query.filter_by(asignatura_id=asignatura_id, curso_id=curso_id).delete()

        # Eliminar la asignatura
        Asignatura.query.filter_by(id=asignatura_id).delete()

        db.session.commit()
        return jsonify({'success': True, 'message': 'Asignatura eliminada correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al eliminar asignatura: {str(e)}'}), 500

# ============================================================================ #
# APIs - ESTADÍSTICAS
# ============================================================================ #

@profesor_bp.route('/api/obtener-estadisticas-calificaciones', methods=['GET'])
@login_required
def obtener_estadisticas_calificaciones():
    """API para obtener estadísticas de calificaciones."""
    try:
        curso_id = session.get('curso_seleccionado')

        if not curso_id:
            return jsonify({'success': False, 'message': 'No hay curso seleccionado'}), 400

        if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes acceso a este curso'}), 403

        calificaciones = obtener_calificaciones_por_curso(curso_id)

        if not calificaciones:
            return jsonify({
                'success': True,
                'minima': 0,
                'maxima': 0,
                'promedio': 0,
                'total': 0
            })

        valores = [float(cal.valor) for cal in calificaciones if cal.valor is not None]

        estadisticas = {
            'minima': min(valores) if valores else 0,
            'maxima': max(valores) if valores else 0,
            'promedio': round(sum(valores) / len(valores), 2) if valores else 0,
            'total': len(valores)
        }

        return jsonify({'success': True, **estadisticas})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener estadísticas: {str(e)}'}), 500


# ============================================================================ #
# calendario
# ============================================================================ #
@profesor_bp.route("/calendario")
@login_required
def ver_eventos():
    return render_template("profesores/calendario.html")
# 📌 API: listar eventos SOLO del rol del profesor
@profesor_bp.route("/api/eventos", methods=["GET"])
@login_required
def api_eventos_profesor():
    try:
        # Filtrar por rol del usuario logueado
        eventos = Evento.query.filter_by(rol_destino="Profesor").all()

        resultado = []
        for ev in eventos:
            resultado.append({
                "IdEvento": ev.id,
                "Nombre": ev.nombre,
                "Descripcion": ev.descripcion,
                "Fecha": ev.fecha.strftime("%Y-%m-%d"),
                "Hora": ev.hora.strftime("%H:%M:%S"),
                "RolDestino": ev.rol_destino
            })

        return jsonify(resultado), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500