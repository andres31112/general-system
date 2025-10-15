from flask import Blueprint, render_template, session, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from controllers.models import (
    db, Usuario, Asignatura, Clase, Matricula, Calificacion, Curso,
    Asistencia, CategoriaCalificacion, ConfiguracionCalificacion, HorarioCompartido, HorarioCurso,
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
            HorarioCompartido, HorarioCompartido.curso_id == Curso.id_curso
        ).filter(
            HorarioCompartido.profesor_id == profesor_id
        ).distinct().all()
    except Exception as e:
        flash(f'Error en la consulta de cursos por horario: {str(e)}', 'error')
        cursos_horarios = []

    # Cursos desde Clase - CORREGIDO
    try:
        cursos_clases = db.session.query(Curso).join(
            Clase, Clase.cursoId == Curso.id_curso
        ).filter(
            Clase.profesorId == profesor_id
        ).distinct().all()
    except Exception as e:
        flash(f'Error en la consulta de cursos por clase: {str(e)}', 'error')
        cursos_clases = []

    # Combinar y eliminar duplicados manteniendo objetos Curso
    todos = {c.id_curso: c for c in (cursos_horarios + cursos_clases)}.values()
    todos_cursos = list(todos)

    # Agregar total de estudiantes por curso
    for curso in todos_cursos:
        curso.total_estudiantes = len(obtener_estudiantes_por_curso(curso.id_curso))

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
            'curso_nombre': curso.nombreCurso if curso else 'N/A',
            'asignatura_nombre': asignatura.nombre if asignatura else 'N/A',
            'dia_semana': horario_curso.dia_semana if horario_curso and getattr(horario_curso, 'dia_semana', None) else (horario_general.nombre if horario_general else 'N/A'),
            'hora_inicio': (
                horario_curso.hora_inicio if horario_curso and getattr(horario_curso, 'hora_inicio', None)
                else (horario_general.horaInicio.strftime('%H:%M') if horario_general and horario_general.horaInicio else 'N/A')
            ),
            'hora_fin': (
                horario_curso.hora_fin if horario_curso and getattr(horario_curso, 'hora_fin', None)
                else (horario_general.horaFin.strftime('%H:%M') if horario_general and horario_general.horaFin else 'N/A')
            ),
            'salon': salon.nombre if salon else 'N/A',
            'sede': sede.nombre if sede else 'N/A',
            'origen_id_horario_curso': horario_curso.id_horario_curso if horario_curso else None
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
            Clase, Clase.asignaturaId == Asignatura.id_asignatura
        ).filter(
            Clase.cursoId == curso_id,
            Clase.profesorId == profesor_id
        ).distinct().all()
    except Exception as e:
        flash(f'Error al obtener asignaturas (clase): {str(e)}', 'error')
        asignaturas_clase = []

    # Unir y retornar sin duplicados
    asignaturas = {a.id_asignatura: a for a in (asignaturas_horario + asignaturas_clase)}.values()
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
            Clase, Clase.asignaturaId == Asignatura.id_asignatura
        ).filter(
            Clase.profesorId == profesor_id
        ).distinct().all()
    except Exception as e:
        flash(f'Error al obtener asignaturas del profesor (clase): {str(e)}', 'error')
        asignaturas_clase = []

    asignaturas = {a.id_asignatura: a for a in (asignaturas_horario + asignaturas_clase)}.values()
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
        Clase, Asistencia.claseId == Clase.id_clase
    ).filter(
        Clase.cursoId == curso_id
    ).all()
    return asistencias

def obtener_clase_para_asistencia(curso_id, profesor_id):
    """Obtiene el ID de una clase para registrar asistencia."""
    clase = Clase.query.filter_by(cursoId=curso_id, profesorId=profesor_id).first()
    return clase.id_clase if clase else None

def guardar_o_actualizar_asistencia(estudiante_id, clase_id, fecha, estado, excusa=False):
    """Guarda o actualiza una asistencia."""
    asistencia_existente = Asistencia.query.filter_by(
        estudianteId=estudiante_id,
        claseId=clase_id,
        fecha=fecha
    ).first()

    if asistencia_existente:
        asistencia_existente.estado = estado
        asistencia_existente.excusa = excusa
    else:
        nueva_asistencia = Asistencia(
            estudianteId=estudiante_id,
            claseId=clase_id,
            fecha=fecha,
            estado=estado,
            excusa=excusa
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
# CONTEXT PROCESSOR Y UTILIDADES PARA TEMPLATES
# ============================================================================ #
def _dia_semana_a_indice(nombre_dia):
    if not nombre_dia:
        return None
    m = nombre_dia.strip().lower()
    # Normalizar acentos y variantes
    mapping = {
        'lunes': 0, 'martes': 1, 'miercoles': 2, 'miércoles': 2,
        'jueves': 3, 'viernes': 4, 'sabado': 5, 'sábado': 5, 'domingo': 6
    }
    return mapping.get(m, None)

def _hora_a_minutos(hora_str):
    try:
        parts = hora_str.split(':')
        return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return 24 * 60  # valor alto si no se puede parsear

def obtener_proxima_clase(profesor_id):
    """Busca la próxima clase en la semana basándose en horarios compartidos.
    Retorna un dict con claves similares a las usadas en templates o None.
    """
    try:
        horarios = obtener_horarios_detallados_profesor(profesor_id)
        if not horarios:
            return None

        hoy_idx = datetime.today().weekday()  # 0=Monday
        candidatos = []
        for h in horarios:
            dia = h.get('dia_semana') or h.get('dia') or h.get('diaSemana')
            hora = h.get('hora_inicio') or h.get('horaInicio') or h.get('hora') or '23:59'
            dia_idx = _dia_semana_a_indice(dia)
            if dia_idx is None:
                continue
            dias_adelante = (dia_idx - hoy_idx) % 7
            minutos = _hora_a_minutos(hora)
            candidatos.append((dias_adelante, minutos, h))

        if not candidatos:
            return None

        candidatos.sort(key=lambda x: (x[0], x[1]))
        mejor = candidatos[0][2]
        # Normalizar salida
        return {
            'asignatura_nombre': mejor.get('asignatura_nombre') or mejor.get('asignatura') or mejor.get('asignatura_nombre', 'N/A'),
            'curso_nombre': mejor.get('curso_nombre') or mejor.get('curso') or mejor.get('curso_nombre', 'N/A'),
            'dia_semana': mejor.get('dia_semana') or mejor.get('dia') or 'N/A',
            'hora_inicio': mejor.get('hora_inicio') or mejor.get('horaInicio') or 'N/A',
            'hora_fin': mejor.get('hora_fin') or mejor.get('hora_fin') or 'N/A',
            'salon': mejor.get('salon') or 'N/A'
        }
    except Exception:
        return None


def generar_matriz_horario_profesor(profesor_id):
    """Genera una matriz (dias x horas) con listas de clases para el profesor.
    Retorna (dias, horas, matriz) donde:
      - dias: lista ordenada de nombres de día
      - horas: lista ordenada de horas de inicio ("HH:MM")
      - matriz: dict dia -> hora -> [entradas]
    Cada entrada es un dict con keys: curso_nombre, asignatura_nombre, hora_inicio, hora_fin, salon, sede, origen
    """
    entradas = []

    # 1) Entradas desde HorarioCompartido / HorarioCurso
    try:
        hcomps = HorarioCompartido.query.filter_by(profesor_id=profesor_id).all()
    except Exception:
        hcomps = []

    for hcomp in hcomps:
        horario_curso = None
        try:
            horario_curso = HorarioCurso.query.filter_by(
                curso_id=hcomp.curso_id,
                asignatura_id=hcomp.asignatura_id,
                horario_general_id=hcomp.horario_general_id
            ).first()
            if not horario_curso:
                horario_curso = HorarioCurso.query.filter_by(
                    curso_id=hcomp.curso_id,
                    asignatura_id=hcomp.asignatura_id
                ).first()
        except Exception:
            horario_curso = None

        curso = Curso.query.get(hcomp.curso_id)
        asignatura = Asignatura.query.get(hcomp.asignatura_id)
        horario_general = HorarioGeneral.query.get(hcomp.horario_general_id) if hcomp.horario_general_id else None

        dia = None
        hora_inicio = None
        hora_fin = None
        salon_nombre = None

        if horario_curso:
            dia = horario_curso.dia_semana
            hora_inicio = horario_curso.hora_inicio
            hora_fin = horario_curso.hora_fin
            salon_nombre = horario_curso.salon.nombre if getattr(horario_curso, 'salon', None) else None
        elif horario_general:
            # Si no hay horario_curso, intentar usar el horario_general (tomar horaInicio)
            dia = horario_general.nombre if horario_general else None
            hora_inicio = horario_general.horaInicio.strftime('%H:%M') if horario_general and horario_general.horaInicio else None
            hora_fin = horario_general.horaFin.strftime('%H:%M') if horario_general and horario_general.horaFin else None

        entradas.append({
            'curso_id': getattr(curso, 'id_curso', None),
            'curso_nombre': curso.nombreCurso if curso else 'N/A',
            'asignatura_id': getattr(asignatura, 'id_asignatura', None),
            'asignatura_nombre': asignatura.nombre if asignatura else 'N/A',
            'dia': dia or 'N/A',
            'hora_inicio': hora_inicio or 'N/A',
            'hora_fin': hora_fin or 'N/A',
            'salon': salon_nombre or 'N/A',
            'sede': curso.sede.nombre if getattr(curso, 'sede', None) else 'N/A',
            'origen': 'compartido'
        })

    # 2) Entradas desde Clase (sistema tradicional)
    try:
        clases = Clase.query.filter_by(profesorId=profesor_id).all()
    except Exception:
        clases = []

    for clase in clases:
        # Intentar localizar HorarioCurso asociado a la asignatura + curso
        horario_curso = HorarioCurso.query.filter_by(curso_id=clase.cursoId, asignatura_id=clase.asignaturaId).first()
        curso = Curso.query.get(clase.cursoId)
        asignatura = Asignatura.query.get(clase.asignaturaId)
        horario_general = HorarioGeneral.query.get(clase.horarioId) if getattr(clase, 'horarioId', None) else None

        dia = horario_curso.dia_semana if horario_curso and getattr(horario_curso, 'dia_semana', None) else (horario_general.nombre if horario_general else None)
        hora_inicio = horario_curso.hora_inicio if horario_curso and getattr(horario_curso, 'hora_inicio', None) else (horario_general.horaInicio.strftime('%H:%M') if horario_general and horario_general.horaInicio else None)
        hora_fin = horario_curso.hora_fin if horario_curso and getattr(horario_curso, 'hora_fin', None) else (horario_general.horaFin.strftime('%H:%M') if horario_general and horario_general.horaFin else None)
        salon_nombre = horario_curso.salon.nombre if horario_curso and getattr(horario_curso, 'salon', None) else None

        entradas.append({
            'curso_id': getattr(curso, 'id_curso', None),
            'curso_nombre': curso.nombreCurso if curso else 'N/A',
            'asignatura_id': getattr(asignatura, 'id_asignatura', None),
            'asignatura_nombre': asignatura.nombre if asignatura else 'N/A',
            'dia': dia or 'N/A',
            'hora_inicio': hora_inicio or 'N/A',
            'hora_fin': hora_fin or 'N/A',
            'salon': salon_nombre or 'N/A',
            'sede': curso.sede.nombre if getattr(curso, 'sede', None) else 'N/A',
            'origen': 'clase'
        })

    # Normalizar días y horas y construir matriz
    dias_set = set()
    horas_set = set()
    for e in entradas:
        d = e.get('dia')
        h = e.get('hora_inicio')
        if d and d != 'N/A':
            dias_set.add(d)
        if h and h != 'N/A':
            horas_set.add(h)

    # Ordenar días por índice si es posible (lunes->domingo)
    dias_list = sorted(list(dias_set), key=lambda x: (_dia_semana_a_indice(x) if _dia_semana_a_indice(x) is not None else 999, x))

    # Ordenar horas por minutos
    def hora_key(h):
        try:
            return _hora_a_minutos(h)
        except Exception:
            return 24*60

    horas_list = sorted(list(horas_set), key=hora_key)

    matriz = {}
    for d in dias_list:
        matriz[d] = {}
        for h in horas_list:
            matriz[d][h] = []

    for e in entradas:
        d = e.get('dia')
        h = e.get('hora_inicio')
        if d in matriz and h in matriz[d]:
            matriz[d][h].append(e)
        else:
            # si día o hora no está en listas (por datos raros), agregar entrada suelta en clave especial
            matriz.setdefault(d, {}).setdefault(h or 'N/A', []).append(e)

    return dias_list, horas_list, matriz


@profesor_bp.context_processor
def profesor_context():
    """Inyecta variables útiles en todas las plantillas bajo el blueprint profesor.
    Evita romper plantillas que esperan conteos/badges en el sidebar y dashboard.
    """
    try:
        user_id = current_user.id_usuario if current_user and getattr(current_user, 'id_usuario', None) else None
        curso_id = session.get('curso_seleccionado')
        asignaturas_count = len(obtener_asignaturas_del_profesor(user_id)) if user_id else 0
        # Estudiantes del curso seleccionado (si hay)
        estudiantes_count = len(obtener_estudiantes_por_curso(curso_id)) if curso_id else sum((getattr(c, 'total_estudiantes', 0) for c in obtener_cursos_del_profesor(user_id))) if user_id else 0
        pendientes_count = calcular_pendientes(user_id, curso_id) if user_id else 0
        unread_messages = 0
        proxima_clase = obtener_proxima_clase(user_id) if user_id else None
        return {
            'asignaturas_count': asignaturas_count,
            'estudiantes_count': estudiantes_count,
            'pendientes_count': pendientes_count,
            'unread_messages': unread_messages,
            'proxima_clase': proxima_clase
        }
    except Exception:
        return {}

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
    proxima = obtener_proxima_clase(current_user.id_usuario)

    # Devolver con nombres que usa la plantilla
    return render_template('profesores/dashboard.html',
                         clases=clases,
                         curso_actual=curso_actual,
                         horarios_detallados=horarios_detallados,
                         estudiantes_count=estudiantes_total,
                         asignaturas_count=asignaturas_total,
                         pendientes_count=pendientes_total,
                         unread_messages=mensajes_total,
                         proxima_clase=proxima)

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

        # Manejar redirección segura usando el parámetro next opcional
        destino = request.form.get('next') or request.args.get('next')
        if destino and isinstance(destino, str) and destino.startswith('/'):
            # evitar redirecciones externas
            return redirect(destino)
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
    # Preparar versiones serializables (dicts) para uso en JS dentro de la plantilla
    def _serialize_estudiante(e):
        return {
            'id': getattr(e, 'id_usuario', None) or getattr(e, 'id', None),
            'nombre': getattr(e, 'nombre', '') or '',
            'apellido': getattr(e, 'apellido', '') or ''
        }

    def _serialize_asignatura(a):
        return {
            'id': getattr(a, 'id_asignatura', None) or getattr(a, 'id', None),
            'nombre': getattr(a, 'nombre', '') or ''
        }

    def _serialize_calificacion(c):
        return {
            'id': getattr(c, 'id_calificacion', None),
            'estudiante_id': getattr(c, 'estudianteId', None) or getattr(c, 'estudiante_id', None),
            'asignatura_id': getattr(c, 'asignaturaId', None) or getattr(c, 'asignatura_id', None),
            'categoria_id': getattr(c, 'categoriaId', None) or getattr(c, 'categoria_id', None),
            'valor': float(c.valor) if getattr(c, 'valor', None) is not None else None,
            'observaciones': getattr(c, 'observaciones', '') or '',
            'nombre_calificacion': getattr(c, 'nombre_calificacion', '') or ''
        }

    estudiantes_json = [_serialize_estudiante(e) for e in estudiantes]
    asignaturas_json = [_serialize_asignatura(a) for a in asignaturas]
    calificaciones_json = [_serialize_calificacion(c) for c in calificaciones]
    # Enviar campos completos para que el frontend no tenga que volver a pedirlos
    categorias_json = [
        {
            'id': getattr(cat, 'id_categoria', None) or getattr(cat, 'id', None),
            'nombre': getattr(cat, 'nombre', '') or '',
            'color': getattr(cat, 'color', '') or '#cccccc',
            'porcentaje': float(getattr(cat, 'porcentaje', 0) or 0)
        }
        for cat in categorias
    ]

    # Limpiar flashes temporales en sesión
    session.pop('flash_messages', None)

    # Intentar inyectar datos directamente en la HTML renderizada sin modificar
    # el archivo de plantilla en disco. Esto permite que la versión actual de
    # `Gestion_LC.html` (que es un HTML estático con JS que busca elementos por
    # id) muestre datos iniciales del servidor.
    try:
        # Obtener la fuente cruda de la plantilla desde el loader de Jinja
        source = None
        try:
            source, filename, upt = current_app.jinja_loader.get_source(current_app.jinja_env, 'profesores/Gestion_LC.html')
        except Exception:
            # fallback: leer desde el sistema de archivos relativo al app root
            import os
            tpl_path = os.path.join(current_app.root_path, 'templates', 'profesores', 'Gestion_LC.html')
            with open(tpl_path, 'r', encoding='utf-8') as f:
                source = f.read()

        html = source

        # Valores simples a reemplazar en el HTML (reemplazo de los contenidos "Cargando..." y contadores)
        profesor_nombre = f"{getattr(current_user, 'nombre', '') or ''} {getattr(current_user, 'apellido', '') or ''}".strip() or 'Profesor'
        sede_nombre = 'N/A'
        try:
            if curso and getattr(curso, 'sede', None):
                sede_nombre = getattr(curso.sede, 'nombre', str(getattr(curso, 'sede', 'N/A')))
            elif curso and getattr(curso, 'sedeId', None):
                # intentar resolver por id
                sede_obj = Sede.query.get(getattr(curso, 'sedeId'))
                sede_nombre = sede_obj.nombre if sede_obj else 'N/A'
        except Exception:
            sede_nombre = 'N/A'

        course_info_text = f"{getattr(curso, 'nombreCurso', getattr(curso, 'nombre', 'Curso'))} - Director de Curso: {getattr(curso, 'director', 'No asignado')}"
        representative = getattr(curso, 'representante', None) or getattr(curso, 'representante_de_curso', None) or 'N/A'
        total_students = len(estudiantes)

        # Reemplazos sencillos (buscan las etiquetas donde el contenido por defecto es 'Cargando...' o '0')
        html = html.replace('<h2 id="professor-name">Cargando...</h2>', f'<h2 id="professor-name">{profesor_nombre}</h2>')
        html = html.replace('<p id="professor-campus">Cargando...</p>', f'<p id="professor-campus">{sede_nombre}</p>')
        html = html.replace('<p class="card-content" id="total-students">0</p>', f'<p class="card-content" id="total-students">{total_students}</p>')
        html = html.replace('<p class="mb-1" id="course-info">Cargando...</p>', f'<p class="mb-1" id="course-info">{course_info_text}</p>')
        html = html.replace('<p class="mb-0 text-muted small" id="course-representative">Cargando...</p>', f'<p class="mb-0 text-muted small" id="course-representative">{representative}</p>')

        # Añadir un bloque <script> con datos serializados expuestos en window.SERVER_DATA
        server_payload = {
            'profesor': {
                'nombre': profesor_nombre,
                'sede': sede_nombre
            },
            'curso': {
                'id': getattr(curso, 'id_curso', getattr(curso, 'id', None)),
                'nombre': getattr(curso, 'nombreCurso', getattr(curso, 'nombre', ''))
            },
            'estudiantes': estudiantes_json,
            'asignaturas': asignaturas_json,
            'calificaciones': calificaciones_json,
            'categorias': categorias_json
        }

        import json as _json
        script_block = f"\n<script>window.SERVER_DATA = {_json.dumps(server_payload)};</script>\n"

        # Insertar el script justo antes de </body>
        if '</body>' in html:
            html = html.replace('</body>', script_block + '</body>')
        else:
            html = html + script_block

        from flask import make_response
        resp = make_response(html)
        resp.headers['Content-Type'] = 'text/html; charset=utf-8'
        return resp
    except Exception as e:
        # Si algo falla al intentar inyectar, volver al render_template normal (seguro)
        try:
            return render_template('profesores/Gestion_LC.html',
                                 curso=curso,
                                 estudiantes=estudiantes,
                                 asignaturas=asignaturas,
                                 categorias=categorias,
                                 calificaciones=calificaciones,
                                 estudiantes_json=estudiantes_json,
                                 asignaturas_json=asignaturas_json,
                                 calificaciones_json=calificaciones_json)
        except Exception:
            # último recurso: redirigir a seleccionar curso
            flash(f'Error al renderizar la página: {str(e)}', 'error')
            return redirect(url_for('profesor.seleccionar_curso'))

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

    # Redirigir a la página unificada de gestión (listas y calificaciones)
    return redirect(url_for('profesor.gestion_lc'))

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

    # Generar matriz para la vista tipo grid
    try:
        dias, horas, matriz = generar_matriz_horario_profesor(current_user.id_usuario)
    except Exception:
        dias = []
        horas = []
        matriz = {}

    return render_template('profesores/HorarioC.html',
                         horarios_detallados=horarios_detallados,
                         clases=clases,
                         dias=dias,
                         horas=horas,
                         matriz=matriz)

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
            'id': curso.id_curso,
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
            Clase, Asistencia.claseId == Clase.id_clase
        ).filter(
            Clase.cursoId == curso_id,
            Clase.profesorId == current_user.id_usuario,
            db.extract('year', Asistencia.fecha) == año,
            db.extract('month', Asistencia.fecha) == mes
        ).all()

        asistencias_data = [{
            'estudiante_id': a.estudianteId,
            'fecha': a.fecha.strftime('%Y-%m-%d'),
            'estado': a.estado,
            'excusa': a.excusa
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
            excusa = asistencia_data.get('excusa', False)
            if not validar_estudiante_en_curso(estudiante_id, curso_id):
                continue
            guardar_o_actualizar_asistencia(estudiante_id, clase_id, fecha, estado, excusa)

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
            Asignatura, Asignatura.id_asignatura == Calificacion.asignaturaId
        ).join(
            CategoriaCalificacion, CategoriaCalificacion.id_categoria == Calificacion.categoriaId
        ).join(
            Clase, Clase.asignaturaId == Calificacion.asignaturaId
        ).filter(
            Clase.cursoId == curso_id
        ).all()

        calificaciones_data = []
        for cal, usuario, asign, cat in rows:
            calificaciones_data.append({
                'id': cal.id_calificacion,
                'estudiante_id': cal.estudianteId,
                'estudiante_nombre': f"{usuario.nombre} {usuario.apellido}",
                'asignatura_id': cal.asignaturaId,
                'asignatura_nombre': asign.nombre if asign else '',
                'categoria_id': cal.categoriaId,
                'categoria_nombre': cat.nombre if cat else '',
                'valor': float(cal.valor) if cal.valor is not None else None,
                'observaciones': cal.observaciones,
                'nombre_calificacion': getattr(cal, 'nombre_calificacion', None)
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
        nombre_calificacion = data.get('nombre_calificacion', '')
        curso_id = session.get('curso_seleccionado')

        if not curso_id:
            return jsonify({'success': False, 'message': 'No hay curso seleccionado'}), 400

        if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes acceso a este curso'}), 403

        if not validar_estudiante_en_curso(estudiante_id, curso_id):
            return jsonify({'success': False, 'message': 'El estudiante no pertenece a este curso'}), 400

        if not verificar_asignatura_profesor_en_curso(asignatura_id, current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes esta asignatura en el curso'}), 403

        # Buscar calificación existente
        calificacion_existente = Calificacion.query.filter_by(
            estudianteId=estudiante_id,
            asignaturaId=asignatura_id,
            categoriaId=categoria_id,
            nombre_calificacion=nombre_calificacion
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
                observaciones=observaciones,
                nombre_calificacion=nombre_calificacion
            )
            db.session.add(nueva_calificacion)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Calificación guardada correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al guardar calificación: {str(e)}'}), 500


@profesor_bp.route('/api/crear-asignacion', methods=['POST'])
@login_required
def api_crear_asignacion():
    """Crea una nueva asignación (placeholder de calificación) para todos los estudiantes del curso seleccionado.
    Body: { asignatura_id: int, nombre_calificacion: str, categoria_id: int }
    """
    try:
        data = request.get_json()
        asignatura_id = data.get('asignatura_id')
        nombre = data.get('nombre_calificacion')
        categoria_id = data.get('categoria_id')
        curso_id = session.get('curso_seleccionado')

        if not curso_id:
            return jsonify({'success': False, 'message': 'No hay curso seleccionado'}), 400

        if not verificar_asignatura_profesor_en_curso(asignatura_id, current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes acceso a esa asignatura en el curso'}), 403

        estudiantes = obtener_estudiantes_por_curso(curso_id)
        creadas = []
        for est in estudiantes:
            nueva = Calificacion(
                estudianteId=getattr(est, 'id_usuario', None),
                asignaturaId=asignatura_id,
                categoriaId=categoria_id or (CategoriaCalificacion.query.first().id_categoria if CategoriaCalificacion.query.first() else None),
                valor=None,
                observaciones='',
                nombre_calificacion=nombre
            )
            db.session.add(nueva)
            db.session.flush()
            creadas.append({'id': nueva.id_calificacion, 'estudiante_id': nueva.estudianteId})

        db.session.commit()
        return jsonify({'success': True, 'message': 'Asignación creada', 'creadas': creadas})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error creando asignación: {str(e)}'}), 500


@profesor_bp.route('/api/editar-asignacion', methods=['POST'])
@login_required
def api_editar_asignacion():
    """Editar nombre de asignación: body { nombre_antiguo, nombre_nuevo }
    Actualiza las calificaciones existentes que tienen nombre_calificacion igual al nombre_antiguo.
    """
    try:
        data = request.get_json() or {}
        nombre_ant = data.get('nombre_antiguo')
        nombre_new = data.get('nombre_nuevo')
        curso_id = session.get('curso_seleccionado')

        if not curso_id:
            return jsonify({'success': False, 'message': 'No hay curso seleccionado'}), 400
        if not nombre_ant or not nombre_new:
            return jsonify({'success': False, 'message': 'nombres requeridos'}), 400

        # Actualizar todas las calificaciones del curso con ese nombre
        rows = Calificacion.query.filter_by(nombre_calificacion=nombre_ant).all()
        for r in rows:
            r.nombre_calificacion = nombre_new
        db.session.commit()
        return jsonify({'success': True, 'message': 'Asignación renombrada'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error renombrando asignación: {str(e)}'}), 500


@profesor_bp.route('/api/eliminar-asignacion', methods=['POST'])
@login_required
def api_eliminar_asignacion():
    """Eliminar una asignación por nombre (elimina las calificaciones asociadas). Body: { nombre_calificacion }
    """
    try:
        data = request.get_json() or {}
        nombre = data.get('nombre_calificacion')
        curso_id = session.get('curso_seleccionado')

        if not curso_id:
            return jsonify({'success': False, 'message': 'No hay curso seleccionado'}), 400
        if not nombre:
            return jsonify({'success': False, 'message': 'nombre requerido'}), 400

        Calificacion.query.filter_by(nombre_calificacion=nombre).delete()
        db.session.commit()
        return jsonify({'success': True, 'message': 'Asignación eliminada'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error eliminando asignación: {str(e)}'}), 500


@profesor_bp.route('/api/categorias', methods=['GET', 'POST'])
@login_required
def api_categorias():
    if request.method == 'GET':
        cats = CategoriaCalificacion.query.all()
        data = [{'id': c.id_categoria, 'nombre': c.nombre, 'color': c.color, 'porcentaje': float(c.porcentaje)} for c in cats]
        return jsonify({'success': True, 'categorias': data})

    # POST: crear
    try:
        data = request.get_json()
        nombre = data.get('nombre')
        color = data.get('color', '#000000')
        porcentaje = data.get('porcentaje', 0)
        if not nombre:
            return jsonify({'success': False, 'message': 'Nombre requerido'}), 400
        nueva = CategoriaCalificacion(nombre=nombre, color=color, porcentaje=porcentaje)
        db.session.add(nueva)
        db.session.commit()
        return jsonify({'success': True, 'categoria': {'id': nueva.id_categoria, 'nombre': nueva.nombre, 'color': nueva.color, 'porcentaje': float(nueva.porcentaje)}})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error creando categoría: {str(e)}'}), 500


@profesor_bp.route('/api/categorias/<int:cat_id>', methods=['PUT', 'DELETE'])
@login_required
def api_categorias_modificar(cat_id):
    if request.method == 'DELETE':
        try:
            # Verificar si hay calificaciones asociadas a esta categoría
            calificaciones_asociadas = Calificacion.query.filter_by(categoriaId=cat_id).first()
            if calificaciones_asociadas:
                return jsonify({
                    'success': False, 
                    'message': 'No se puede eliminar la categoría porque tiene calificaciones asociadas. Elimine primero las calificaciones o cambie su categoría.'
                }), 400
            
            # Si no hay calificaciones asociadas, proceder con la eliminación
            categoria = CategoriaCalificacion.query.get(cat_id)
            if not categoria:
                return jsonify({'success': False, 'message': 'Categoría no encontrada'}), 404
                
            db.session.delete(categoria)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Categoría eliminada correctamente'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Error eliminando categoría: {str(e)}'}), 500

    # PUT: editar
    try:
        data = request.get_json()
        cat = CategoriaCalificacion.query.get(cat_id)
        if not cat:
            return jsonify({'success': False, 'message': 'Categoría no encontrada'}), 404
        cat.nombre = data.get('nombre', cat.nombre)
        cat.color = data.get('color', cat.color)
        cat.porcentaje = data.get('porcentaje', cat.porcentaje)
        db.session.commit()
        return jsonify({'success': True, 'categoria': {'id': cat.id_categoria, 'nombre': cat.nombre, 'color': cat.color, 'porcentaje': float(cat.porcentaje)}})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error actualizando categoría: {str(e)}'}), 500

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
        asignatura_id = nueva_asignatura.id_asignatura

        id_horario_general = data.get('horario_general_id')
        if not id_horario_general:
            horario_general = HorarioGeneral.query.first()
            if not horario_general:
                db.session.rollback()
                return jsonify({'success': False, 'message': 'No hay horarios generales disponibles'}), 400
            id_horario_general = horario_general.id_horario

        # Crear HorarioCurso - CORREGIDO
        horario_curso = HorarioCurso(
            curso_id=curso_id,
            asignatura_id=asignatura_id,
            horario_general_id=id_horario_general,
            dia_semana=data.get('dia_semana', 'Lunes'),
            hora_inicio=data.get('hora_inicio', '07:00'),
            hora_fin=data.get('hora_fin', '07:45'),
            id_salon_fk=data.get('id_salon_fk', None)
        )
        db.session.add(horario_curso)
        db.session.flush()

        # Crear HorarioCompartido para asociar al profesor
        horario_compartido = HorarioCompartido(
            profesor_id=current_user.id_usuario,
            curso_id=curso_id,
            asignatura_id=asignatura_id,
            horario_general_id=id_horario_general,
            fecha_compartido=datetime.utcnow()
        )
        db.session.add(horario_compartido)

        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Asignatura añadida correctamente',
            'asignatura_id': asignatura_id
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

        # Eliminar calificaciones relacionadas con esa asignatura
        Calificacion.query.filter_by(asignaturaId=asignatura_id).delete()

        # Eliminar entradas en HorarioCompartido y HorarioCurso para ese curso + asignatura
        HorarioCompartido.query.filter_by(asignatura_id=asignatura_id, curso_id=curso_id).delete()
        HorarioCurso.query.filter_by(asignatura_id=asignatura_id, curso_id=curso_id).delete()

        # Eliminar la asignatura
        Asignatura.query.filter_by(id_asignatura=asignatura_id).delete()

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
# APIs - CONFIGURACIÓN DE CALIFICACIONES
# ============================================================================ #
@profesor_bp.route('/api/configuracion-calificaciones', methods=['GET', 'POST'])
@login_required
def api_configuracion_calificaciones():
    """GET: devuelve la configuración (única fila esperada)
       POST: crea o actualiza la configuración con payload { notaMinima, notaMaxima, notaMinimaAprobacion }
    """
    try:
        if request.method == 'GET':
            cfg = ConfiguracionCalificacion.query.first()
            if not cfg:
                # valores por defecto
                return jsonify({'success': True, 'configuracion': {'notaMinima': 0, 'notaMaxima': 100, 'notaMinimaAprobacion': 60}})
            return jsonify({'success': True, 'configuracion': {'notaMinima': float(cfg.notaMinima), 'notaMaxima': float(cfg.notaMaxima), 'notaMinimaAprobacion': float(cfg.notaMinimaAprobacion)}})

        # POST: upsert
        data = request.get_json() or {}
        notaMinima = data.get('notaMinima', 0)
        notaMaxima = data.get('notaMaxima', 100)
        notaMinimaAprobacion = data.get('notaMinimaAprobacion', 60)

        cfg = ConfiguracionCalificacion.query.first()
        if cfg:
            cfg.notaMinima = notaMinima
            cfg.notaMaxima = notaMaxima
            cfg.notaMinimaAprobacion = notaMinimaAprobacion
        else:
            cfg = ConfiguracionCalificacion(notaMinima=notaMinima, notaMaxima=notaMaxima, notaMinimaAprobacion=notaMinimaAprobacion)
            db.session.add(cfg)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Configuración guardada'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error en configuración: {str(e)}'}), 500


# ============================================================================ #
# calendario
# ============================================================================ #
@profesor_bp.route("/calendario")
@login_required
def ver_eventos():
    return render_template("profesores/calendario.html")

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