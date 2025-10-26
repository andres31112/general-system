from flask import Blueprint, render_template, session, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from controllers.models import (
    db, Usuario, Asignatura, Clase, Matricula, Calificacion, Curso,
    Asistencia, CategoriaCalificacion, ConfiguracionCalificacion, HorarioCompartido, HorarioCurso,
    HorarioGeneral, Salon, Sede, Evento, ReporteCalificaciones, SolicitudConsulta
)
from datetime import datetime, date
import json
import os
from werkzeug.utils import secure_filename

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

def obtener_curso_actual_estudiante(estudiante_id):
    """Obtiene el curso actual de un estudiante basado en su matrícula más reciente."""
    try:
        matricula = db.session.query(Matricula).join(Curso).filter(
            Matricula.estudianteId == estudiante_id
        ).order_by(Matricula.fecha_matricula.desc()).first()
        
        if matricula:
            return matricula.curso
        return None
    except Exception as e:
        current_app.logger.error(f"Error obteniendo curso del estudiante {estudiante_id}: {e}")
        return None

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

def obtener_profesores_por_asignatura(asignatura_id):
    """✅ NUEVA FUNCIÓN: Obtiene todos los profesores asignados a una asignatura específica."""
    try:
        # Obtener profesores desde la tabla intermedia asignatura_profesor
        profesores = db.session.query(Usuario).join(
            Usuario.asignaturas
        ).filter(
            Asignatura.id_asignatura == asignatura_id,
            Usuario.id_rol_fk == 2  # Solo profesores (rol_id = 2)
        ).all()
        
        return [
            {
                'id_usuario': prof.id_usuario,
                'nombre_completo': prof.nombre_completo,
                'correo': prof.correo
            } for prof in profesores
        ]
    except Exception as e:
        print(f"Error obteniendo profesores por asignatura: {str(e)}")
        return []

def validar_profesor_asignatura(profesor_id, asignatura_id):
    """✅ NUEVA FUNCIÓN: Valida si un profesor está asignado a una asignatura específica."""
    try:
        asignacion = db.session.query(Usuario).join(
            Usuario.asignaturas
        ).filter(
            Usuario.id_usuario == profesor_id,
            Asignatura.id_asignatura == asignatura_id
        ).first()
        
        return asignacion is not None
    except Exception as e:
        print(f"Error validando profesor-asignatura: {str(e)}")
        return False

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
    entradas_unicas = set()  # Para evitar duplicados

    def _fmt_hora(val):
        try:
            if hasattr(val, 'strftime'):
                return val.strftime('%H:%M')
            s = str(val)
            return s[:5] if len(s) >= 5 and s[2] == ':' else s
        except Exception:
            return None

    # 1) Entradas desde HorarioCompartido / HorarioCurso (prioritario)
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
            hora_inicio = _fmt_hora(horario_curso.hora_inicio)
            hora_fin = _fmt_hora(horario_curso.hora_fin)
            salon_nombre = horario_curso.salon.nombre if getattr(horario_curso, 'salon', None) else None
        elif horario_general:
            # Si no hay horario_curso, intentar usar el horario_general (tomar horaInicio)
            dia = horario_general.nombre if horario_general else None
            hora_inicio = horario_general.horaInicio.strftime('%H:%M') if horario_general and horario_general.horaInicio else None
            hora_fin = horario_general.horaFin.strftime('%H:%M') if horario_general and horario_general.horaFin else None

        # Crear clave única para evitar duplicados
        clave_unica = f"{hcomp.curso_id}-{hcomp.asignatura_id}-{dia}-{hora_inicio}"
        if clave_unica not in entradas_unicas:
            entradas_unicas.add(clave_unica)
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

    # 2) Entradas desde Clase (sistema tradicional) - solo si no hay HorarioCompartido
    try:
        clases = Clase.query.filter_by(profesorId=profesor_id).all()
    except Exception:
        clases = []

    for clase in clases:
        # Verificar si ya existe una entrada de HorarioCompartido para esta combinación
        clave_clase = f"{clase.cursoId}-{clase.asignaturaId}"
        if any(e.get('curso_id') == clase.cursoId and e.get('asignatura_id') == clase.asignaturaId for e in entradas):
            continue  # Saltar si ya existe en HorarioCompartido
            
        # Intentar localizar HorarioCurso asociado a la asignatura + curso
        horario_curso = HorarioCurso.query.filter_by(curso_id=clase.cursoId, asignatura_id=clase.asignaturaId).first()
        curso = Curso.query.get(clase.cursoId)
        asignatura = Asignatura.query.get(clase.asignaturaId)
        horario_general = HorarioGeneral.query.get(clase.horarioId) if getattr(clase, 'horarioId', None) else None

        dia = horario_curso.dia_semana if horario_curso and getattr(horario_curso, 'dia_semana', None) else (horario_general.nombre if horario_general else None)
        hora_inicio = _fmt_hora(horario_curso.hora_inicio) if horario_curso and getattr(horario_curso, 'hora_inicio', None) else (horario_general.horaInicio.strftime('%H:%M') if horario_general and horario_general.horaInicio else None)
        hora_fin = _fmt_hora(horario_curso.hora_fin) if horario_curso and getattr(horario_curso, 'hora_fin', None) else (horario_general.horaFin.strftime('%H:%M') if horario_general and horario_general.horaFin else None)
        salon_nombre = horario_curso.salon.nombre if horario_curso and getattr(horario_curso, 'salon', None) else None

        # Crear clave única para evitar duplicados
        clave_unica = f"{clase.cursoId}-{clase.asignaturaId}-{dia}-{hora_inicio}"
        if clave_unica not in entradas_unicas:
            entradas_unicas.add(clave_unica)
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
# FUNCIONES PARA ESTADÍSTICAS Y DATOS DEL DASHBOARD
# ============================================================================ #

def calcular_estadisticas_asistencia_curso(profesor_id, curso_id):
    """Calcula estadísticas de asistencia para un curso específico."""
    try:
        if not curso_id:
            return {'promedio': 0, 'total_clases': 0, 'total_estudiantes': 0}
        
        # Obtener todas las clases del profesor en este curso
        clases = Clase.query.filter_by(
            profesorId=profesor_id, 
            cursoId=curso_id
        ).all()
        
        if not clases:
            return {'promedio': 0, 'total_clases': 0, 'total_estudiantes': 0}
        
        clase_ids = [clase.id_clase for clase in clases]
        
        # Obtener asistencias para estas clases
        asistencias = Asistencia.query.filter(
            Asistencia.claseId.in_(clase_ids)
        ).all()
        
        # Calcular estadísticas
        total_asistencias = len(asistencias)
        asistencias_presente = len([a for a in asistencias if a.estado == 'presente'])
        
        promedio = (asistencias_presente / total_asistencias * 100) if total_asistencias > 0 else 0
        
        # Obtener total de estudiantes
        total_estudiantes = len(obtener_estudiantes_por_curso(curso_id))
        
        return {
            'promedio': round(promedio, 2),
            'total_clases': len(clases),
            'total_estudiantes': total_estudiantes
        }
    except Exception as e:
        print(f"Error calculando estadísticas de asistencia: {e}")
        return {'promedio': 0, 'total_clases': 0, 'total_estudiantes': 0}

def calcular_estadisticas_calificaciones_curso(profesor_id, curso_id):
    """Calcula estadísticas de calificaciones para un curso específico."""
    try:
        if not curso_id:
            return {'promedio': 0, 'aprobacion': 0, 'total_calificaciones': 0}
        
        # Obtener calificaciones del curso
        calificaciones = obtener_calificaciones_por_curso(curso_id)
        
        if not calificaciones:
            return {'promedio': 0, 'aprobacion': 0, 'total_calificaciones': 0}
        
        # Filtrar calificaciones con valores numéricos
        calificaciones_con_valor = [c for c in calificaciones if c.valor is not None]
        
        if not calificaciones_con_valor:
            return {'promedio': 0, 'aprobacion': 0, 'total_calificaciones': 0}
        
        # Calcular promedio
        valores = [float(c.valor) for c in calificaciones_con_valor]
        promedio = sum(valores) / len(valores)
        
        # Obtener configuración de aprobación
        config = ConfiguracionCalificacion.query.first()
        nota_aprobacion = float(config.notaMinimaAprobacion) if config else 60.0
        
        # Calcular porcentaje de aprobación
        aprobados = len([v for v in valores if v >= nota_aprobacion])
        porcentaje_aprobacion = (aprobados / len(valores)) * 100
        
        return {
            'promedio': round(promedio, 2),
            'aprobacion': round(porcentaje_aprobacion, 2),
            'total_calificaciones': len(calificaciones_con_valor)
        }
    except Exception as e:
        print(f"Error calculando estadísticas de calificaciones: {e}")
        return {'promedio': 0, 'aprobacion': 0, 'total_calificaciones': 0}

def obtener_clase_actual(profesor_id):
    """Obtiene la clase actual en curso basada en la hora y día actual."""
    try:
        from datetime import datetime
        ahora = datetime.now()
        dia_actual = ahora.strftime('%A').lower()
        hora_actual = ahora.strftime('%H:%M')
        
        # Mapeo de días en español
        dias_espanol = {
            'monday': 'lunes',
            'tuesday': 'martes', 
            'wednesday': 'miércoles',
            'thursday': 'jueves',
            'friday': 'viernes',
            'saturday': 'sábado',
            'sunday': 'domingo'
        }
        
        dia_actual_es = dias_espanol.get(dia_actual, '')
        
        if not dia_actual_es:
            return None
        
        # Usar la matriz de horarios para obtener datos más precisos
        dias_semana, horas_semana, matriz_horario = generar_matriz_horario_profesor(profesor_id)
        
        # Buscar en la matriz del día actual
        if dia_actual_es in matriz_horario:
            for hora_inicio, entradas in matriz_horario[dia_actual_es].items():
                if entradas:  # Si hay entradas en esta hora
                    # Verificar si la hora actual está dentro del rango de la clase
                    for entrada in entradas:
                        hora_inicio_clase = entrada.get('hora_inicio', '')
                        hora_fin_clase = entrada.get('hora_fin', '')
                        
                        if hora_inicio_clase and hora_fin_clase:
                            # Convertir a minutos para comparación
                            def hora_a_minutos(hora_str):
                                try:
                                    h, m = map(int, hora_str.split(':'))
                                    return h * 60 + m
                                except:
                                    return 0
                            
                            hora_actual_min = hora_a_minutos(hora_actual)
                            hora_inicio_min = hora_a_minutos(hora_inicio_clase)
                            hora_fin_min = hora_a_minutos(hora_fin_clase)
                            
                            # Verificar si estamos dentro del rango de la clase
                            if hora_inicio_min <= hora_actual_min < hora_fin_min:
                                return {
                                    'asignatura_nombre': entrada.get('asignatura_nombre', 'N/A'),
                                    'curso_nombre': entrada.get('curso_nombre', 'N/A'),
                                    'hora_inicio': hora_inicio_clase,
                                    'hora_fin': hora_fin_clase,
                                    'salon': entrada.get('salon', 'N/A'),
                                    'sede': entrada.get('sede', 'N/A')
                                }
        
        return None
    except Exception as e:
        print(f"Error obteniendo clase actual: {e}")
        return None

def obtener_proxima_clase_mejorada(profesor_id):
    """Obtiene la próxima clase del profesor de manera más precisa."""
    try:
        from datetime import datetime, time
        ahora = datetime.now()
        dia_actual = ahora.strftime('%A').lower()
        hora_actual = ahora.time()
        
        # Mapeo de días en español
        dias_espanol = {
            'monday': 'lunes',
            'tuesday': 'martes', 
            'wednesday': 'miercoles',
            'thursday': 'jueves',
            'friday': 'viernes',
            'saturday': 'sabado',
            'sunday': 'domingo'
        }
        
        dia_actual_es = dias_espanol.get(dia_actual, '')
        
        # Obtener todos los horarios del profesor
        horarios = obtener_horarios_detallados_profesor(profesor_id)
        
        if not horarios:
            return None
        
        # Ordenar horarios por día y hora
        horarios_ordenados = []
        for horario in horarios:
            dia = horario.get('dia_semana', '').lower()
            hora_str = horario.get('hora_inicio', '00:00')
            
            # Convertir hora string a objeto time
            try:
                hora_obj = datetime.strptime(hora_str, '%H:%M').time()
            except:
                continue
            
            # Asignar peso numérico al día
            dias_semana = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
            peso_dia = dias_semana.index(dia) if dia in dias_semana else 999
            
            horarios_ordenados.append({
                'horario': horario,
                'dia': dia,
                'hora': hora_obj,
                'peso_dia': peso_dia
            })
        
        # Ordenar por día y hora
        horarios_ordenados.sort(key=lambda x: (x['peso_dia'], x['hora']))
        
        # Buscar la próxima clase
        for horario_info in horarios_ordenados:
            dia = horario_info['dia']
            hora = horario_info['hora']
            
            # Si es hoy y la hora es futura
            if dia == dia_actual_es and hora > hora_actual:
                return horario_info['horario']
            
            # Si es un día futuro
            if dia != dia_actual_es:
                peso_dia_actual = dias_semana.index(dia_actual_es) if dia_actual_es in dias_semana else -1
                peso_dia_clase = horario_info['peso_dia']
                
                # Si el día de la clase es después del día actual
                if peso_dia_clase > peso_dia_actual:
                    return horario_info['horario']
        
        # Si no hay clases futuras esta semana, tomar la primera del siguiente ciclo
        if horarios_ordenados:
            return horarios_ordenados[0]['horario']
        
        return None
        
    except Exception as e:
        print(f"Error obteniendo próxima clase: {e}")
        return None

def obtener_datos_grafico_asistencia(profesor_id, curso_id, meses=6):
    """Obtiene datos históricos de asistencia para el gráfico."""
    try:
        if not curso_id:
            return {'labels': [], 'data': []}
        
        # Obtener clases del profesor en este curso
        clases = Clase.query.filter_by(
            profesorId=profesor_id, 
            cursoId=curso_id
        ).all()
        
        if not clases:
            return {'labels': [], 'data': []}
        
        clase_ids = [clase.id_clase for clase in clases]
        
        # Obtener asistencias de los últimos meses
        from datetime import datetime, timedelta
        fecha_limite = datetime.now().replace(day=1)  # Primer día del mes actual
        for _ in range(meses-1):
            fecha_limite = (fecha_limite.replace(day=1) - timedelta(days=1)).replace(day=1)
        
        asistencias = Asistencia.query.filter(
            Asistencia.claseId.in_(clase_ids),
            Asistencia.fecha >= fecha_limite
        ).all()
        
        # Agrupar por mes
        datos_mensuales = {}
        for asistencia in asistencias:
            mes_key = asistencia.fecha.strftime('%Y-%m')
            if mes_key not in datos_mensuales:
                datos_mensuales[mes_key] = {'total': 0, 'presente': 0}
            
            datos_mensuales[mes_key]['total'] += 1
            if asistencia.estado == 'presente':
                datos_mensuales[mes_key]['presente'] += 1
        
        # Ordenar y formatear datos
        meses_ordenados = sorted(datos_mensuales.keys())
        labels = []
        data = []
        
        for mes in meses_ordenados:
            mes_datos = datos_mensuales[mes]
            porcentaje = (mes_datos['presente'] / mes_datos['total'] * 100) if mes_datos['total'] > 0 else 0
            
            # Formatear nombre del mes
            fecha = datetime.strptime(mes + '-01', '%Y-%m-%d')
            labels.append(fecha.strftime('%b').capitalize())
            data.append(round(porcentaje, 2))
        
        return {'labels': labels, 'data': data}
    except Exception as e:
        print(f"Error obteniendo datos de gráfico de asistencia: {e}")
        return {'labels': [], 'data': []}

def obtener_datos_grafico_calificaciones(profesor_id, curso_id):
    """Obtiene datos de calificaciones por asignatura para el gráfico."""
    try:
        if not curso_id:
            return {'labels': [], 'data': []}
        
        # Obtener asignaturas del profesor en este curso
        asignaturas = obtener_asignaturas_por_curso_y_profesor(curso_id, profesor_id)
        
        if not asignaturas:
            return {'labels': [], 'data': []}
        
        labels = []
        data = []
        
        for asignatura in asignaturas:
            # Obtener calificaciones para esta asignatura
            calificaciones = Calificacion.query.filter_by(
                asignaturaId=asignatura.id_asignatura
            ).all()
            
            calificaciones_con_valor = [c for c in calificaciones if c.valor is not None]
            
            if calificaciones_con_valor:
                promedio = sum(float(c.valor) for c in calificaciones_con_valor) / len(calificaciones_con_valor)
                labels.append(asignatura.nombre)
                data.append(round(promedio, 2))
        
        return {'labels': labels, 'data': data}
    except Exception as e:
        print(f"Error obteniendo datos de gráfico de calificaciones: {e}")
        return {'labels': [], 'data': []}

def obtener_notificaciones_profesor(profesor_id, curso_id):
    """Obtiene notificaciones específicas para el profesor."""
    try:
        notificaciones = []
        
        # Tareas pendientes (asistencias no registradas hoy)
        pendientes = calcular_pendientes(profesor_id, curso_id)
        if pendientes > 0:
            notificaciones.append({
                'tipo': 'tareas_pendientes',
                'mensaje': f'{pendientes} tareas pendientes',
                'icono': 'exclamation-triangle',
                'color': 'accent1'
            })
        
        # Estudiantes en riesgo (bajas calificaciones)
        if curso_id:
            estudiantes = obtener_estudiantes_por_curso(curso_id)
            estudiantes_riesgo = 0
            
            for estudiante in estudiantes:
                calificaciones = Calificacion.query.filter_by(
                    estudianteId=estudiante.id_usuario
                ).all()
                
                calificaciones_con_valor = [c for c in calificaciones if c.valor is not None]
                if calificaciones_con_valor:
                    promedio = sum(float(c.valor) for c in calificaciones_con_valor) / len(calificaciones_con_valor)
                    if promedio < 60:  # Umbral de riesgo
                        estudiantes_riesgo += 1
            
            if estudiantes_riesgo > 0:
                notificaciones.append({
                    'tipo': 'estudiantes_riesgo',
                    'mensaje': f'{estudiantes_riesgo} est. riesgo',
                    'icono': 'user-graduate',
                    'color': 'accent1'
                })
        
        # Mensajes no leídos (placeholder)
        mensajes_no_leidos = 0  # Esto debería venir de un modelo de mensajes
        if mensajes_no_leidos > 0:
            notificaciones.append({
                'tipo': 'mensajes',
                'mensaje': f'{mensajes_no_leidos} mensajes nuevos',
                'icono': 'envelope',
                'color': 'accent2'
            })
        
        # Eventos próximos
        from datetime import date
        hoy = date.today()
        eventos = Evento.query.filter(
            Evento.rol_destino == 'Profesor',
            Evento.fecha >= hoy
        ).order_by(Evento.fecha).limit(3).all()
        
        for evento in eventos:
            notificaciones.append({
                'tipo': 'evento',
                'mensaje': evento.nombre,
                'icono': 'calendar-event',
                'color': 'accent2'
            })
        
        return notificaciones
    except Exception as e:
        print(f"Error obteniendo notificaciones: {e}")
        return []

# ============================================================================ #
# RUTAS PRINCIPALES
# ============================================================================ #

@profesor_bp.route('/dashboard')
@login_required
def dashboard():
    """Panel principal del profesor con datos reales."""
    curso_id = session.get('curso_seleccionado')
    curso_actual = Curso.query.get(curso_id) if curso_id else None

    try:
        horarios_detallados = obtener_horarios_detallados_profesor(current_user.id_usuario)
    except Exception as e:
        flash(f'Error al cargar horarios: {str(e)}', 'error')
        horarios_detallados = []

    # Generar matriz semanal (días x horas) solo del profesor
    try:
        dias_semana, horas_semana, matriz_horario = generar_matriz_horario_profesor(current_user.id_usuario)
    except Exception:
        dias_semana, horas_semana, matriz_horario = [], [], {}

    # Fallback: si no se pudo construir con la matriz (por datos parciales), derivar de horarios_detallados
    if (not dias_semana or not horas_semana) and horarios_detallados:
        try:
            def _norm_dia(d):
                try:
                    return (d or '').strip()
                except Exception:
                    return d
            def _norm_h(h):
                try:
                    s = str(h or '')
                    # recorta a HH:MM
                    return s[:5] if len(s) >= 5 and s[2] == ':' else s
                except Exception:
                    return h
            dias_set_fb = set()
            horas_set_fb = set()
            matriz_fb = {}
            for h in horarios_detallados:
                d = _norm_dia(h.get('dia_semana') or h.get('dia') or h.get('diaSemana'))
                hi = _norm_h(h.get('hora_inicio') or h.get('horaInicio') or h.get('hora'))
                hf = _norm_h(h.get('hora_fin') or h.get('horaFin'))
                if d:
                    dias_set_fb.add(d)
                if hi:
                    horas_set_fb.add(hi)
                if d and hi:
                    matriz_fb.setdefault(d, {}).setdefault(hi, []).append({
                        'asignatura_nombre': h.get('asignatura_nombre') or h.get('asignatura', 'N/A'),
                        'curso_nombre': h.get('curso_nombre') or h.get('curso', 'N/A'),
                        'salon': h.get('salon') or 'N/A',
                        'hora_inicio': hi,
                        'hora_fin': hf or ''
                    })
            # ordenar usando utilidades existentes
            dias_semana = sorted(list(dias_set_fb), key=lambda x: (_dia_semana_a_indice(x) if _dia_semana_a_indice(x) is not None else 999, x))
            horas_semana = sorted(list(horas_set_fb), key=lambda hh: (_hora_a_minutos(hh)))
            matriz_horario = {d: {h: matriz_fb.get(d, {}).get(h, []) for h in horas_semana} for d in dias_semana}
        except Exception:
            pass

    # Calcular estadísticas reales
    estadisticas_asistencia = calcular_estadisticas_asistencia_curso(current_user.id_usuario, curso_id)
    estadisticas_calificaciones = calcular_estadisticas_calificaciones_curso(current_user.id_usuario, curso_id)
    
    # Obtener datos para gráficos
    datos_grafico_asistencia = obtener_datos_grafico_asistencia(current_user.id_usuario, curso_id)
    datos_grafico_calificaciones = obtener_datos_grafico_calificaciones(current_user.id_usuario, curso_id)
    
    # Obtener clase actual y notificaciones
    clase_actual = obtener_clase_actual(current_user.id_usuario)
    notificaciones = obtener_notificaciones_profesor(current_user.id_usuario, curso_id)
    
    # Usar la función mejorada para la próxima clase
    proxima_clase = obtener_proxima_clase_mejorada(current_user.id_usuario)
    
    cursos = obtener_cursos_del_profesor(current_user.id_usuario)

    return render_template('profesores/dashboard.html',
                           curso_actual=curso_actual,
                           horarios_detallados=horarios_detallados,
                           dias=dias_semana,
                           horas=horas_semana,
                           matriz=matriz_horario,
                           estadisticas_asistencia=estadisticas_asistencia,
                           estadisticas_calificaciones=estadisticas_calificaciones,
                           datos_grafico_asistencia=datos_grafico_asistencia,
                           datos_grafico_calificaciones=datos_grafico_calificaciones,
                           clase_actual=clase_actual,
                           notificaciones=notificaciones,
                           estudiantes_count=estadisticas_asistencia.get('total_estudiantes', 0) if estadisticas_asistencia else 0,
                           asignaturas_count=len(obtener_asignaturas_del_profesor(current_user.id_usuario)),
                           pendientes_count=calcular_pendientes(current_user.id_usuario, curso_id),
                           unread_messages=0,
                           proxima_clase=proxima_clase,  # Usar la función mejorada
                           cursos=cursos)
    """Panel principal del profesor con datos reales."""
    curso_id = session.get('curso_seleccionado')
    curso_actual = Curso.query.get(curso_id) if curso_id else None

    try:
        horarios_detallados = obtener_horarios_detallados_profesor(current_user.id_usuario)
    except Exception as e:
        flash(f'Error al cargar horarios: {str(e)}', 'error')
        horarios_detallados = []

    # Calcular estadísticas reales
    estadisticas_asistencia = calcular_estadisticas_asistencia_curso(current_user.id_usuario, curso_id)
    estadisticas_calificaciones = calcular_estadisticas_calificaciones_curso(current_user.id_usuario, curso_id)
    
    # Obtener datos para gráficos
    datos_grafico_asistencia = obtener_datos_grafico_asistencia(current_user.id_usuario, curso_id)
    datos_grafico_calificaciones = obtener_datos_grafico_calificaciones(current_user.id_usuario, curso_id)
    
    # Obtener clase actual y notificaciones
    clase_actual = obtener_clase_actual(current_user.id_usuario)
    notificaciones = obtener_notificaciones_profesor(current_user.id_usuario, curso_id)
    
    cursos = obtener_cursos_del_profesor(current_user.id_usuario)

    return render_template('profesores/dashboard.html',
                           curso_actual=curso_actual,
                           horarios_detallados=horarios_detallados,
                           estadisticas_asistencia=estadisticas_asistencia,
                           estadisticas_calificaciones=estadisticas_calificaciones,
                           datos_grafico_asistencia=datos_grafico_asistencia,
                           datos_grafico_calificaciones=datos_grafico_calificaciones,
                           clase_actual=clase_actual,
                           notificaciones=notificaciones,
                           estudiantes_count=estadisticas_asistencia.get('total_estudiantes', 0) if estadisticas_asistencia else 0,
                           asignaturas_count=len(obtener_asignaturas_del_profesor(current_user.id_usuario)),
                           pendientes_count=calcular_pendientes(current_user.id_usuario, curso_id),
                           unread_messages=0,  # Placeholder hasta implementar mensajes
                           proxima_clase=obtener_proxima_clase(current_user.id_usuario),
                           cursos=cursos)
    

@profesor_bp.route('/gestion-lc')
@login_required
def gestion_lc():
    """Página unificada de gestión de listas y calificaciones."""
    curso_id = session.get('curso_seleccionado')
    asignatura_id = session.get('asignatura_seleccionada')

    if not curso_id or not asignatura_id:
        flash('Primero debes seleccionar un curso y una asignatura', 'warning')
        return redirect(url_for('profesor.dashboard'))

    if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
        flash('No tienes acceso a este curso', 'error')
        return redirect(url_for('profesor.dashboard'))

    if not verificar_asignatura_profesor_en_curso(asignatura_id, current_user.id_usuario, curso_id):
        flash('No tienes acceso a esta asignatura en el curso', 'error')
        return redirect(url_for('profesor.dashboard'))

    curso = Curso.query.get(curso_id)
    asignatura = Asignatura.query.get(asignatura_id)
    estudiantes = obtener_estudiantes_por_curso(curso_id)
    # Solo mostrar la asignatura seleccionada
    asignaturas = [asignatura] if asignatura else []
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

        # Información del curso y asignatura seleccionada
        course_info_text = f"{getattr(curso, 'nombreCurso', getattr(curso, 'nombre', 'Curso'))} - {getattr(asignatura, 'nombre', 'Asignatura')}"
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
            'asignatura_seleccionada': {
                'id': getattr(asignatura, 'id_asignatura', getattr(asignatura, 'id', None)),
                'nombre': getattr(asignatura, 'nombre', '')
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

@profesor_bp.route('/api/comunicaciones', methods=['GET'])
@login_required
def api_obtener_comunicaciones():
    """API para obtener comunicaciones del profesor."""
    try:
        from controllers.models import Comunicacion
        
        folder = request.args.get('folder', 'inbox')
        
        # Obtener comunicaciones según la carpeta
        if folder == 'inbox':
            # Comunicaciones recibidas (donde el profesor es destinatario)
            comunicaciones = db.session.query(Comunicacion).filter(
                Comunicacion.destinatario_id == current_user.id_usuario,
                Comunicacion.estado == 'inbox'
            ).order_by(Comunicacion.fecha_envio.desc()).limit(50).all()
            
            # Convertir a diccionarios
            comunicaciones_data = []
            for com in comunicaciones:
                comunicaciones_data.append({
                    'id': com.id_comunicacion,
                    'remitente': com.remitente.nombre_completo if com.remitente else 'Desconocido',
                    'remitente_nombre': com.remitente.nombre_completo if com.remitente else 'Desconocido',
                    'remitente_email': com.remitente.correo if com.remitente else '',
                    'destinatario': com.destinatario.nombre_completo if com.destinatario else 'Desconocido',
                    'destinatario_nombre': com.destinatario.nombre_completo if com.destinatario else 'Desconocido',
                    'destinatario_email': com.destinatario.correo if com.destinatario else '',
                    'asunto': com.asunto,
                    'mensaje': com.mensaje,
                    'fecha': com.fecha_envio.strftime('%Y-%m-%d %H:%M') if com.fecha_envio else '',
                    'fecha_envio': com.fecha_envio.isoformat() if com.fecha_envio else '',
                    'estado': com.estado,
                    'tipo': 'recibida'
                })
                
        elif folder == 'sent':
            # Comunicaciones enviadas (donde el profesor es remitente)
            comunicaciones = db.session.query(Comunicacion).filter(
                Comunicacion.remitente_id == current_user.id_usuario,
                Comunicacion.estado.in_(['inbox', 'sent'])
            ).order_by(Comunicacion.fecha_envio.desc()).limit(50).all()
            
            # Agrupar comunicaciones por grupo_id (como Gmail)
            grupos = {}
            for com in comunicaciones:
                grupo_key = com.grupo_id or f"individual_{com.id_comunicacion}"
                if grupo_key not in grupos:
                    grupos[grupo_key] = {
                    'id': com.id_comunicacion,
                    'remitente': com.remitente.nombre_completo if com.remitente else 'Desconocido',
                    'remitente_nombre': com.remitente.nombre_completo if com.remitente else 'Desconocido',
                    'remitente_email': com.remitente.correo if com.remitente else '',
                    'asunto': com.asunto,
                    'mensaje': com.mensaje,
                    'fecha': com.fecha_envio.strftime('%Y-%m-%d %H:%M') if com.fecha_envio else '',
                    'fecha_envio': com.fecha_envio.isoformat() if com.fecha_envio else '',
                    'estado': com.estado,
                        'tipo': 'enviada',
                        'destinatarios': [],
                        'destinatarios_count': 0
                    }
                
                # Agregar destinatario al grupo
                destinatario_info = {
                    'nombre': com.destinatario.nombre_completo if com.destinatario else 'Desconocido',
                    'email': com.destinatario.correo if com.destinatario else '',
                    'id': com.destinatario.id_usuario if com.destinatario else None
                }
                grupos[grupo_key]['destinatarios'].append(destinatario_info)
                grupos[grupo_key]['destinatarios_count'] += 1
            
            # Convertir grupos a lista
            comunicaciones_data = []
            for grupo in grupos.values():
                # Crear texto de destinatarios múltiples
                if grupo['destinatarios_count'] > 1:
                    grupo['destinatario'] = f"{grupo['destinatarios'][0]['nombre']} y {grupo['destinatarios_count'] - 1} más"
                    grupo['destinatario_nombre'] = grupo['destinatario']
                else:
                    grupo['destinatario'] = grupo['destinatarios'][0]['nombre']
                    grupo['destinatario_nombre'] = grupo['destinatario']
                
                comunicaciones_data.append(grupo)
                
        elif folder == 'draft':
            # Borradores
            comunicaciones = db.session.query(Comunicacion).filter(
                Comunicacion.remitente_id == current_user.id_usuario,
                Comunicacion.estado == 'draft'
            ).order_by(Comunicacion.fecha_envio.desc()).limit(50).all()
            
            # Convertir a diccionarios
            comunicaciones_data = []
            for com in comunicaciones:
                comunicaciones_data.append({
                    'id': com.id_comunicacion,
                    'remitente': com.remitente.nombre_completo if com.remitente else 'Desconocido',
                    'remitente_nombre': com.remitente.nombre_completo if com.remitente else 'Desconocido',
                    'remitente_email': com.remitente.correo if com.remitente else '',
                    'destinatario': com.destinatario.nombre_completo if com.destinatario else 'Desconocido',
                    'destinatario_nombre': com.destinatario.nombre_completo if com.destinatario else 'Desconocido',
                    'destinatario_email': com.destinatario.correo if com.destinatario else '',
                    'asunto': com.asunto,
                    'mensaje': com.mensaje,
                    'fecha': com.fecha_envio.strftime('%Y-%m-%d %H:%M') if com.fecha_envio else '',
                    'fecha_envio': com.fecha_envio.isoformat() if com.fecha_envio else '',
                    'estado': com.estado,
                    'tipo': 'borrador'
                })
                
        elif folder == 'deleted':
            # Comunicaciones eliminadas
            comunicaciones = db.session.query(Comunicacion).filter(
                (Comunicacion.remitente_id == current_user.id_usuario) |
                (Comunicacion.destinatario_id == current_user.id_usuario),
                Comunicacion.estado == 'deleted'
            ).order_by(Comunicacion.fecha_envio.desc()).limit(50).all()
            
            # Convertir a diccionarios
            comunicaciones_data = []
            for com in comunicaciones:
                comunicaciones_data.append({
                    'id': com.id_comunicacion,
                    'remitente': com.remitente.nombre_completo if com.remitente else 'Desconocido',
                    'remitente_nombre': com.remitente.nombre_completo if com.remitente else 'Desconocido',
                    'remitente_email': com.remitente.correo if com.remitente else '',
                    'destinatario': com.destinatario.nombre_completo if com.destinatario else 'Desconocido',
                    'destinatario_nombre': com.destinatario.nombre_completo if com.destinatario else 'Desconocido',
                    'destinatario_email': com.destinatario.correo if com.destinatario else '',
                    'asunto': com.asunto,
                    'mensaje': com.mensaje,
                    'fecha': com.fecha_envio.strftime('%Y-%m-%d %H:%M') if com.fecha_envio else '',
                    'fecha_envio': com.fecha_envio.isoformat() if com.fecha_envio else '',
                    'estado': com.estado,
                    'tipo': 'eliminada'
                })
        else:
            comunicaciones_data = []
        
        # Estandarizar respuesta según la estructura del admin
        return jsonify({
            'success': True,
            'recibidas': comunicaciones_data if folder == 'inbox' else [],
            'enviadas': comunicaciones_data if folder == 'sent' else [],
            'data': comunicaciones_data if folder in ['draft', 'deleted'] else []
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error obteniendo comunicaciones: {str(e)}'
        }), 500

@profesor_bp.route('/api/comunicaciones/<int:comunicacion_id>/marcar-leida', methods=['PUT'])
@login_required
def api_marcar_comunicacion_leida(comunicacion_id):
    """API para marcar una comunicación como leída."""
    try:
        from controllers.models import Comunicacion
        
        comunicacion = Comunicacion.query.filter_by(
            id_comunicacion=comunicacion_id,
            destinatario_id=current_user.id_usuario
        ).first()
        
        if not comunicacion:
            return jsonify({
                'success': False,
                'message': 'Comunicación no encontrada'
            }), 404
        
        comunicacion.estado = 'sent'  # Cambiar de 'inbox' a 'sent' para indicar que fue leída
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Comunicación marcada como leída'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error marcando comunicación: {str(e)}'
        }), 500

@profesor_bp.route('/api/comunicaciones', methods=['POST'])
@login_required
def api_enviar_comunicacion():
    """API para enviar comunicaciones del profesor."""
    try:
        from controllers.models import Comunicacion
        
        data = request.get_json()
        to_email = data.get('to')
        asunto = data.get('asunto')
        mensaje = data.get('mensaje')
        
        if not all([to_email, asunto, mensaje]):
            return jsonify({
                'success': False,
                'message': 'Faltan campos requeridos'
            }), 400
        
        # Buscar usuario destinatario por correo
        destinatario = Usuario.query.filter_by(correo=to_email).first()
        
        if not destinatario:
            return jsonify({
                'success': False,
                'message': 'Usuario destinatario no encontrado'
            }), 404
        
        # Crear comunicación
        nueva_comunicacion = Comunicacion(
            remitente_id=current_user.id_usuario,
            destinatario_id=destinatario.id_usuario,
            asunto=asunto,
            mensaje=mensaje,
            estado='inbox'
        )
        
        db.session.add(nueva_comunicacion)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Mensaje enviado correctamente',
            'id': nueva_comunicacion.id_comunicacion
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error enviando comunicación: {str(e)}'
        }), 500
@profesor_bp.route('/api/comunicaciones/cleanup', methods=['POST'])
@login_required
def api_cleanup_comunicaciones():
    """API para limpiar comunicaciones automáticamente."""
    try:
        from controllers.models import Comunicacion
        from datetime import datetime, timedelta
        
        # Fecha actual
        now = datetime.utcnow()
        
        # Mensajes de más de 1 mes (30 días) - mover a papelera
        one_month_ago = now - timedelta(days=30)
        
        # Mensajes de más de 2 meses (60 días) en papelera - eliminar permanentemente
        two_months_ago = now - timedelta(days=60)
        
        # Mover mensajes antiguos a papelera
        mensajes_a_papelera = Comunicacion.query.filter(
            Comunicacion.estado.in_(['inbox', 'sent', 'draft']),
            Comunicacion.fecha_envio < one_month_ago
        ).all()
        
        moved_to_trash = 0
        for mensaje in mensajes_a_papelera:
            mensaje.estado = 'deleted'
            moved_to_trash += 1
        
        # Eliminar permanentemente mensajes muy antiguos en papelera
        mensajes_a_eliminar = Comunicacion.query.filter(
            Comunicacion.estado == 'deleted',
            Comunicacion.fecha_envio < two_months_ago
        ).all()
        
        permanently_deleted = 0
        for mensaje in mensajes_a_eliminar:
            db.session.delete(mensaje)
            permanently_deleted += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Limpieza completada: {moved_to_trash} mensajes movidos a papelera, {permanently_deleted} eliminados permanentemente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error en limpieza automática: {str(e)}'
        }), 500

@profesor_bp.route('/api/comunicaciones/draft', methods=['POST'])
@login_required
def api_guardar_borrador():
    """API para guardar borradores de comunicaciones."""
    try:
        from controllers.models import Comunicacion
        
        data = request.get_json()
        to_email = data.get('to', '')
        asunto = data.get('asunto', '(Sin asunto)')
        mensaje = data.get('mensaje', '')
        
        # Crear borrador (sin destinatario específico)
        borrador = Comunicacion(
            remitente_id=current_user.id_usuario,
            destinatario_id=current_user.id_usuario,  # Auto-enviado como borrador
            asunto=asunto,
            mensaje=mensaje,
            estado='draft'
        )
        
        db.session.add(borrador)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Borrador guardado correctamente',
            'id': borrador.id_comunicacion
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error guardando borrador: {str(e)}'
        }), 500

@profesor_bp.route('/api/comunicaciones/<int:comunicacion_id>', methods=['DELETE'])
@login_required
def api_eliminar_comunicacion(comunicacion_id):
    """API para eliminar una comunicación."""
    try:
        from controllers.models import Comunicacion
        
        comunicacion = Comunicacion.query.filter_by(
            id_comunicacion=comunicacion_id
        ).filter(
            (Comunicacion.remitente_id == current_user.id_usuario) |
            (Comunicacion.destinatario_id == current_user.id_usuario)
        ).first()
        
        if not comunicacion:
            return jsonify({
                'success': False,
                'message': 'Comunicación no encontrada'
            }), 404
        
        # Si ya está en papelera, eliminar permanentemente
        if comunicacion.estado == 'deleted':
            db.session.delete(comunicacion)
            message = 'Comunicación eliminada permanentemente'
        else:
            # Marcar como eliminada en lugar de eliminar físicamente
            comunicacion.estado = 'deleted'
            message = 'Comunicación movida a papelera'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error eliminando comunicación: {str(e)}'
        }), 500

@profesor_bp.route('/api/usuarios/buscar', methods=['GET'])
@login_required
def api_buscar_usuarios():
    """API para buscar usuarios por nombre o email."""
    try:
        query = request.args.get('q', '').strip()
        
        if len(query) < 2:
            return jsonify([])
        
        # Buscar usuarios que coincidan con el query
        usuarios = Usuario.query.filter(
            (Usuario.nombre.ilike(f'%{query}%')) |
            (Usuario.apellido.ilike(f'%{query}%')) |
            (Usuario.correo.ilike(f'%{query}%'))
        ).limit(10).all()
        
        usuarios_data = []
        for usuario in usuarios:
            usuarios_data.append({
                'id': usuario.id_usuario,
                'nombre': usuario.nombre_completo,
                'email': usuario.correo,
                'rol': usuario.rol_nombre
            })
        
        return jsonify(usuarios_data)
        
    except Exception as e:
        return jsonify({
            'error': f'Error buscando usuarios: {str(e)}'
        }), 500

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

@profesor_bp.route('/api/asignaturas-curso/<int:curso_id>')
@login_required
def api_asignaturas_curso(curso_id):
    """API para obtener las asignaturas de un curso específico del profesor."""
    try:
        if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes acceso a este curso'}), 403
        
        asignaturas = obtener_asignaturas_por_curso_y_profesor(curso_id, current_user.id_usuario)
        asignaturas_data = [{
            'id': asignatura.id_asignatura,
            'nombre': asignatura.nombre
        } for asignatura in asignaturas]
        
        return jsonify({
            'success': True,
            'asignaturas': asignaturas_data,
            'total': len(asignaturas_data)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener asignaturas: {str(e)}'}), 500

@profesor_bp.route('/api/seleccionar-curso-asignatura', methods=['POST'])
@login_required
def api_seleccionar_curso_asignatura():
    """API para seleccionar un curso y asignatura específicos."""
    try:
        data = request.get_json()
        curso_id = data.get('curso_id')
        asignatura_id = data.get('asignatura_id')

        if not curso_id or not asignatura_id:
            return jsonify({'success': False, 'message': 'Curso y asignatura son requeridos'}), 400

        # Verificar acceso al curso
        if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes acceso a este curso'}), 403

        # Verificar acceso a la asignatura en el curso
        if not verificar_asignatura_profesor_en_curso(asignatura_id, current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes esta asignatura en el curso'}), 403

        # Guardar en la sesión
        session['curso_seleccionado'] = curso_id
        session['asignatura_seleccionada'] = asignatura_id

        # Obtener información para la respuesta
        curso = Curso.query.get(curso_id)
        asignatura = Asignatura.query.get(asignatura_id)

        return jsonify({
            'success': True,
            'message': f'Seleccionado: {curso.nombreCurso} - {asignatura.nombre}',
            'curso': {
                'id': curso_id,
                'nombre': curso.nombreCurso
            },
            'asignatura': {
                'id': asignatura_id,
                'nombre': asignatura.nombre
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al seleccionar: {str(e)}'}), 500

@profesor_bp.route('/api/limpiar-seleccion', methods=['POST'])
@login_required
def api_limpiar_seleccion():
    """API para limpiar la selección actual de curso y asignatura."""
    try:
        session.pop('curso_seleccionado', None)
        session.pop('asignatura_seleccionada', None)
        return jsonify({'success': True, 'message': 'Selección limpiada correctamente'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al limpiar selección: {str(e)}'}), 500

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
# APIs - TAREAS ACADÉMICAS
# ============================================================================ #

# ============================================================================ #
# GESTIÓN DE TAREAS ACADÉMICAS
# ============================================================================ #

def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida."""
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'rar', 'ppt', 'pptx', 'xls', 'xlsx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@profesor_bp.route('/api/crear-tarea', methods=['POST'])
@login_required
def api_crear_tarea():
    """
    Crea y publica una nueva tarea académica como calificación para todos los estudiantes del curso.
    La tarea se crea como un registro de Calificacion con es_tarea_publicada=True.
    """
    try:
        # Verificar curso seleccionado
        curso_id = session.get('curso_seleccionado')
        if not curso_id:
            return jsonify({'success': False, 'message': 'No hay curso seleccionado'}), 400

        # Verificar acceso del profesor al curso
        if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes acceso a este curso'}), 403

        # Obtener datos del formulario
        titulo = request.form.get('titulo', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        asignatura_id = request.form.get('asignatura_id')
        categoria_id = request.form.get('categoria_id')
        fecha_vencimiento = request.form.get('fecha_vencimiento')

        # Validar campos requeridos
        if not titulo:
            return jsonify({'success': False, 'message': 'El título es requerido'}), 400
        
        if not descripcion:
            return jsonify({'success': False, 'message': 'La descripción es requerida'}), 400
            
        if not asignatura_id:
            return jsonify({'success': False, 'message': 'La asignatura es requerida'}), 400

        # Si no se especifica categoría, usar la primera disponible
        if not categoria_id:
            primera_categoria = CategoriaCalificacion.query.first()
            if primera_categoria:
                categoria_id = primera_categoria.id_categoria
            else:
                return jsonify({'success': False, 'message': 'No hay categorías de calificación configuradas'}), 400

        # Procesar archivo adjunto si existe
        archivo_url = None
        archivo_nombre = None
        if 'archivo' in request.files:
            archivo = request.files['archivo']
            if archivo and archivo.filename:
                if allowed_file(archivo.filename):
                    filename = secure_filename(archivo.filename)
                    # Agregar timestamp para evitar conflictos de nombres
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{timestamp}_{filename}"
                    
                    # Crear directorio si no existe
                    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'tareas')
                    os.makedirs(upload_folder, exist_ok=True)
                    
                    # Guardar archivo
                    filepath = os.path.join(upload_folder, filename)
                    archivo.save(filepath)
                    
                    archivo_url = f'/static/uploads/tareas/{filename}'
                    archivo_nombre = archivo.filename
                else:
                    return jsonify({'success': False, 'message': 'Tipo de archivo no permitido'}), 400

        # Convertir fecha de vencimiento si existe
        fecha_venc_dt = None
        if fecha_vencimiento:
            try:
                fecha_venc_dt = datetime.strptime(fecha_vencimiento, '%Y-%m-%dT%H:%M')
            except ValueError:
                return jsonify({'success': False, 'message': 'Formato de fecha inválido'}), 400

        # Obtener estudiantes del curso
        estudiantes = obtener_estudiantes_por_curso(curso_id)
        if not estudiantes:
            return jsonify({'success': False, 'message': 'No hay estudiantes matriculados en este curso'}), 400

        # Crear una calificación (tarea) para cada estudiante
        tareas_creadas = []
        asignatura = Asignatura.query.get(asignatura_id)
        
        for estudiante in estudiantes:
            est_id = getattr(estudiante, 'id_usuario', None)
            if est_id:
                nueva_tarea = Calificacion(
                    estudianteId=est_id,
                    asignaturaId=int(asignatura_id),
                    categoriaId=int(categoria_id),
                    nombre_calificacion=titulo,
                    descripcion_tarea=descripcion,
                    archivo_url=archivo_url,
                    archivo_nombre=archivo_nombre,
                    fecha_vencimiento=fecha_venc_dt,
                    es_tarea_publicada=True,
                    profesor_id=current_user.id_usuario,
                    valor=None,
                    observaciones=''
                )
                db.session.add(nueva_tarea)
                tareas_creadas.append(nueva_tarea)

        # Crear notificaciones (si el servicio está disponible)
        # Las notificaciones se agregan a la sesión pero NO se hace commit aún
        try:
            from services.notification_service import crear_notificacion
            
            for estudiante in estudiantes:
                est_id = getattr(estudiante, 'id_usuario', None)
                if not est_id:
                    continue
                
                # Notificar al estudiante (sin commit automático)
                try:
                    crear_notificacion(
                        usuario_id=est_id,
                        titulo='Nueva Tarea Publicada',
                        mensaje=f'Se ha publicado una nueva tarea "{titulo}" en {asignatura.nombre if asignatura else "tu curso"}',
                        tipo='tarea',
                        link='/estudiante/tareas',
                        auto_commit=False
                    )
                except Exception as e:
                    print(f'Error creando notificación para estudiante {est_id}: {str(e)}')
                
                # Notificar a los padres del estudiante (sin commit automático)
                try:
                    estudiante_obj = Usuario.query.get(est_id)
                    if estudiante_obj and hasattr(estudiante_obj, 'padres'):
                        # padres es un query dinámico, obtener todos los padres
                        padres_list = estudiante_obj.padres.all()
                        for padre in padres_list:
                            try:
                                crear_notificacion(
                                    usuario_id=padre.id_usuario,
                                    titulo='Nueva Tarea Asignada',
                                    mensaje=f'Nueva tarea "{titulo}" para {estudiante_obj.nombre_completo} en {asignatura.nombre if asignatura else "el curso"}',
                                    tipo='tarea',
                                    link=f'/padre/tareas/{est_id}',
                                    auto_commit=False
                                )
                            except Exception as e:
                                print(f'Error creando notificación para padre {padre.id_usuario}: {str(e)}')
                except Exception as e:
                    print(f'Error obteniendo padres del estudiante {est_id}: {str(e)}')
        except ImportError:
            print('Servicio de notificaciones no disponible')

        # Guardar todas las tareas y notificaciones en una sola transacción
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Tarea creada y publicada exitosamente para {len(tareas_creadas)} estudiantes',
            'total_estudiantes': len(tareas_creadas)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al crear tarea: {str(e)}'}), 500


@profesor_bp.route('/api/obtener-tareas', methods=['GET'])
@login_required
def api_obtener_tareas():
    """
    Obtiene las tareas publicadas del curso seleccionado.
    Retorna una lista sin duplicados (agrupadas por nombre_calificacion).
    """
    try:
        # Verificar curso seleccionado
        curso_id = session.get('curso_seleccionado')
        if not curso_id:
            return jsonify({'success': False, 'message': 'No hay curso seleccionado'}), 400

        # Verificar acceso del profesor al curso
        if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes acceso a este curso'}), 403

        asignatura_id = request.args.get('asignatura_id')
        
        # Obtener IDs de estudiantes del curso
        estudiantes = obtener_estudiantes_por_curso(curso_id)
        estudiantes_ids = [getattr(est, 'id_usuario', None) for est in estudiantes if hasattr(est, 'id_usuario')]
        
        if not estudiantes_ids:
            return jsonify({'success': True, 'tareas': []})
        
        # Consultar tareas publicadas
        query = db.session.query(Calificacion).filter(
            Calificacion.estudianteId.in_(estudiantes_ids),
            Calificacion.es_tarea_publicada == True,
            Calificacion.profesor_id == current_user.id_usuario
        )
        
        if asignatura_id:
            query = query.filter(Calificacion.asignaturaId == int(asignatura_id))
        
        tareas = query.order_by(Calificacion.fecha_registro.desc()).all()
        
        # Agrupar por nombre para evitar duplicados (una tarea por estudiante)
        tareas_unicas = {}
        for tarea in tareas:
            if tarea.nombre_calificacion not in tareas_unicas:
                tareas_unicas[tarea.nombre_calificacion] = tarea
        
        # Formatear respuesta
        tareas_data = []
        for tarea in tareas_unicas.values():
            tareas_data.append({
                'id_tarea': tarea.id_calificacion,
                'titulo': tarea.nombre_calificacion,
                'descripcion': tarea.descripcion_tarea or '',
                'archivo_url': tarea.archivo_url,
                'archivo_nombre': tarea.archivo_nombre,
                'asignatura_id': tarea.asignaturaId,
                'asignatura_nombre': tarea.asignatura.nombre if tarea.asignatura else 'N/A',
                'profesor_id': tarea.profesor_id,
                'profesor_nombre': tarea.profesor.nombre_completo if tarea.profesor else current_user.nombre_completo,
                'categoria_id': tarea.categoriaId,
                'categoria_nombre': tarea.categoria.nombre if tarea.categoria else 'N/A',
                'fecha_publicacion': tarea.fecha_registro.strftime('%Y-%m-%d %H:%M') if tarea.fecha_registro else None,
                'fecha_vencimiento': tarea.fecha_vencimiento.strftime('%Y-%m-%d %H:%M') if tarea.fecha_vencimiento else None,
                'publicada': tarea.es_tarea_publicada
            })
        
        return jsonify({
            'success': True,
            'tareas': tareas_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener tareas: {str(e)}'}), 500


@profesor_bp.route('/api/eliminar-tarea/<int:tarea_id>', methods=['DELETE'])
@login_required
def api_eliminar_tarea(tarea_id):
    """
    Elimina una tarea académica completamente.
    Elimina todas las copias de la tarea (una por cada estudiante) y el archivo adjunto si existe.
    """
    try:
        # Buscar la tarea
        tarea = Calificacion.query.get(tarea_id)
        
        if not tarea:
            return jsonify({'success': False, 'message': 'Tarea no encontrada'}), 404
        
        # Verificar que sea una tarea publicada
        if not tarea.es_tarea_publicada:
            return jsonify({'success': False, 'message': 'Este registro no es una tarea publicada'}), 400
        
        # Verificar que el profesor sea el dueño
        if tarea.profesor_id != current_user.id_usuario:
            return jsonify({'success': False, 'message': 'No tienes permiso para eliminar esta tarea'}), 403
        
        # Obtener todas las copias de la tarea (una por estudiante)
        nombre_tarea = tarea.nombre_calificacion
        tareas_relacionadas = Calificacion.query.filter_by(
            nombre_calificacion=nombre_tarea,
            es_tarea_publicada=True,
            profesor_id=current_user.id_usuario
        ).all()
        
        # Eliminar archivo adjunto si existe
        if tarea.archivo_url:
            try:
                # Construir la ruta completa del archivo
                filepath = os.path.join(current_app.root_path, tarea.archivo_url.lstrip('/'))
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception:
                pass  # Si falla la eliminación del archivo, continuar
        
        # Eliminar todas las tareas relacionadas
        for t in tareas_relacionadas:
            db.session.delete(t)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Tarea eliminada exitosamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al eliminar tarea: {str(e)}'}), 500


@profesor_bp.route('/tareas')
@login_required
def tareas_academicas():
    """Vista para gestionar tareas académicas."""
    curso_id = session.get('curso_seleccionado')
    if not curso_id:
        flash('Por favor, selecciona un curso primero', 'warning')
        return redirect(url_for('profesor.dashboard'))
    
    curso = Curso.query.get(curso_id)
    if not curso:
        flash('Curso no encontrado', 'error')
        return redirect(url_for('profesor.dashboard'))
    
    # Obtener asignaturas del profesor en este curso
    asignaturas = obtener_asignaturas_del_profesor_en_curso(current_user.id_usuario, curso_id)
    categorias = CategoriaCalificacion.query.all()
    
    return render_template('profesores/tareas.html', 
                         curso=curso, 
                         asignaturas=asignaturas,
                         categorias=categorias)

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
# API - RESUMEN DASHBOARD
# ============================================================================ #

@profesor_bp.route('/api/dashboard-resumen', methods=['GET'])
@login_required
def api_dashboard_resumen():
    """Devuelve datos consolidados para el dashboard del profesor."""
    try:
        curso_id = session.get('curso_seleccionado')

        # Horarios y próxima clase
        horarios = obtener_horarios_detallados_profesor(current_user.id_usuario)
        proxima = obtener_proxima_clase_mejorada(current_user.id_usuario)

        # KPIs
        estad_asist = calcular_estadisticas_asistencia_curso(current_user.id_usuario, curso_id)
        estad_calif = calcular_estadisticas_calificaciones_curso(current_user.id_usuario, curso_id)

        # Gráficos
        graf_asist = obtener_datos_grafico_asistencia(current_user.id_usuario, curso_id)
        graf_calif = obtener_datos_grafico_calificaciones(current_user.id_usuario, curso_id)

        # Cursos del profesor
        cursos = obtener_cursos_del_profesor(current_user.id_usuario)

        resp = {
            'success': True,
            'horarios': horarios,
            'proxima_clase': proxima,
            'kpis': {
                'cursos': len(cursos),
                'estudiantes_count': estad_asist.get('total_estudiantes', 0) if estad_asist else 0,
                'asistencia_promedio': estad_asist.get('promedio', 0) if estad_asist else 0,
                'aprobacion_promedio': estad_calif.get('aprobacion', 0) if estad_calif else 0,
                'horas': len(horarios) * 2 if horarios else 0,
                'tareas_pendientes': calcular_pendientes(current_user.id_usuario, curso_id) if curso_id else 0
            },
            'graficos': {
                'asistencia': graf_asist,
                'calificaciones': graf_calif
            }
        }
        return jsonify(resp)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error obteniendo resumen: {str(e)}'}), 500

# ============================================================================ #
# APIs - CONFIGURACIÓN DE CALIFICACIONES
# ============================================================================ #
@profesor_bp.route('/api/configuracion-calificaciones', methods=['GET', 'POST'])
@login_required
def api_configuracion_calificaciones():
    """GET: devuelve la configuración específica de la asignatura o global
       POST: crea o actualiza la configuración con payload { notaMinima, notaMaxima, notaMinimaAprobacion }
    """
    try:
        asignatura_id = session.get('asignatura_seleccionada')
        
        if request.method == 'GET':
            # Buscar configuración específica de la asignatura primero
            cfg = None
            if asignatura_id:
                cfg = ConfiguracionCalificacion.query.filter_by(asignatura_id=asignatura_id).first()
            
            # Si no hay configuración específica, usar la global
            if not cfg:
                cfg = ConfiguracionCalificacion.query.filter_by(asignatura_id=None).first()
            
            if not cfg:
                # valores por defecto
                return jsonify({
                    'success': True, 
                    'configuracion': {
                        'notaMinima': 0, 
                        'notaMaxima': 100, 
                        'notaMinimaAprobacion': 60,
                        'es_especifica': False
                    }
                })
            
            return jsonify({
                'success': True, 
                'configuracion': {
                    'notaMinima': float(cfg.notaMinima), 
                    'notaMaxima': float(cfg.notaMaxima), 
                    'notaMinimaAprobacion': float(cfg.notaMinimaAprobacion),
                    'es_especifica': cfg.asignatura_id is not None
                }
            })

        # POST: upsert
        data = request.get_json() or {}
        notaMinima = data.get('notaMinima', 0)
        notaMaxima = data.get('notaMaxima', 100)
        notaMinimaAprobacion = data.get('notaMinimaAprobacion', 60)

        # Validar rangos
        if notaMinima >= notaMaxima:
            return jsonify({'success': False, 'message': 'La nota mínima debe ser menor que la máxima'}), 400
        
        if notaMinimaAprobacion < notaMinima or notaMinimaAprobacion > notaMaxima:
            return jsonify({'success': False, 'message': 'La nota de aprobación debe estar entre la mínima y máxima'}), 400

        # Obtener o crear configuración específica de la asignatura
        cfg = None
        if asignatura_id:
            cfg = ConfiguracionCalificacion.query.filter_by(asignatura_id=asignatura_id).first()
        
        if not cfg:
            cfg = ConfiguracionCalificacion(asignatura_id=asignatura_id)
            db.session.add(cfg)
        
        cfg.notaMinima = notaMinima
        cfg.notaMaxima = notaMaxima
        cfg.notaMinimaAprobacion = notaMinimaAprobacion
        
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': 'Configuración guardada correctamente',
            'es_especifica': cfg.asignatura_id is not None
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error en configuración: {str(e)}'}), 500


# ============================================================================ #
# APIs - REPORTES DE CALIFICACIONES
# ============================================================================ #

@profesor_bp.route('/api/generar-reporte-calificaciones', methods=['POST'])
@login_required
def api_generar_reporte_calificaciones():
    """API para generar y enviar reporte de calificaciones al administrador."""
    try:
        curso_id = session.get('curso_seleccionado')
        asignatura_id = session.get('asignatura_seleccionada')
        
        if not curso_id or not asignatura_id:
            return jsonify({'success': False, 'message': 'No hay curso o asignatura seleccionada'}), 400

        if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes acceso a este curso'}), 403

        # Obtener datos del curso y asignatura
        curso = Curso.query.get(curso_id)
        asignatura = Asignatura.query.get(asignatura_id)
        
        if not curso or not asignatura:
            return jsonify({'success': False, 'message': 'Curso o asignatura no encontrados'}), 404

        # Obtener estudiantes del curso
        estudiantes = db.session.query(Usuario).join(Matricula).filter(
            Matricula.cursoId == curso_id,
            Usuario.id_rol_fk == 3  # Rol de estudiante
        ).all()

        if not estudiantes:
            return jsonify({'success': False, 'message': 'No hay estudiantes en este curso'}), 400

        # Obtener configuración de calificaciones específica por asignatura
        # Si no existe configuración específica, usar la global
        config_calificaciones = ConfiguracionCalificacion.query.filter_by(
            asignatura_id=asignatura_id
        ).first()
        
        if not config_calificaciones:
            config_calificaciones = ConfiguracionCalificacion.query.first()
        
        configuracion_notas = {
            'nota_minima': float(config_calificaciones.notaMinima) if config_calificaciones else 0,
            'nota_maxima': float(config_calificaciones.notaMaxima) if config_calificaciones else 100,
            'nota_aprobacion': float(config_calificaciones.notaMinimaAprobacion) if config_calificaciones else 60
        }

        # Obtener categorías de calificaciones específicas de esta asignatura
        # Primero obtener las categorías que se usan en esta asignatura
        categorias_usadas = db.session.query(CategoriaCalificacion).join(
            Calificacion, Calificacion.categoriaId == CategoriaCalificacion.id_categoria
        ).filter(
            Calificacion.asignaturaId == asignatura_id
        ).distinct().all()
        
        categorias_info = [{
            'id': cat.id_categoria,
            'nombre': cat.nombre,
            'color': getattr(cat, 'color', '#cccccc'),
            'porcentaje': float(getattr(cat, 'porcentaje', 0))
        } for cat in categorias_usadas]

        # Obtener todas las calificaciones únicas (asignaciones) para esta asignatura
        asignaciones_unicas = db.session.query(
            Calificacion.nombre_calificacion,
            Calificacion.categoriaId
        ).filter(
            Calificacion.asignaturaId == asignatura_id,
            Calificacion.nombre_calificacion.isnot(None)
        ).distinct().all()

        # Obtener calificaciones detalladas de cada estudiante
        datos_estudiantes = []
        calificaciones_totales = []
        
        for estudiante in estudiantes:
            # Obtener todas las calificaciones del estudiante en la asignatura
            calificaciones = db.session.query(Calificacion).filter(
                Calificacion.estudianteId == estudiante.id_usuario,
                Calificacion.asignaturaId == asignatura_id
            ).all()
            
            # Organizar calificaciones por asignación con detalles completos
            calificaciones_por_asignacion = {}
            for cal in calificaciones:
                if cal.nombre_calificacion:
                    categoria_info = next((cat for cat in categorias_info if cat['id'] == cal.categoriaId), None)
                    calificaciones_por_asignacion[cal.nombre_calificacion] = {
                        'valor': float(cal.valor) if cal.valor is not None else None,
                        'categoria_id': cal.categoriaId,
                        'categoria_nombre': categoria_info['nombre'] if categoria_info else 'Sin categoría',
                        'categoria_color': categoria_info['color'] if categoria_info else '#cccccc',
                        'categoria_porcentaje': categoria_info['porcentaje'] if categoria_info else 0,
                        'observaciones': cal.observaciones or '',
                        'fecha_registro': cal.fecha_registro.strftime('%Y-%m-%d %H:%M') if cal.fecha_registro else None
                    }
            
            # Calcular promedio del estudiante por categorías
            promedios_por_categoria = {}
            for cat in categorias_info:
                cat_id = cat['id']
                valores_categoria = []
                for cal in calificaciones:
                    if cal.categoriaId == cat_id and cal.valor is not None:
                        valores_categoria.append(float(cal.valor))
                
                if valores_categoria:
                    promedios_por_categoria[cat_id] = {
                        'promedio': round(sum(valores_categoria) / len(valores_categoria), 2),
                        'cantidad': len(valores_categoria),
                        'categoria_nombre': cat['nombre'],
                        'categoria_color': cat['color'],
                        'categoria_porcentaje': cat['porcentaje'],
                        'valores': valores_categoria
                    }
                else:
                    promedios_por_categoria[cat_id] = {
                        'promedio': 0,
                        'cantidad': 0,
                        'categoria_nombre': cat['nombre'],
                        'categoria_color': cat['color'],
                        'categoria_porcentaje': cat['porcentaje'],
                        'valores': []
                    }
            
            # Calcular promedio ponderado final
            promedio_ponderado = 0
            total_porcentaje = 0
            for cat_id, datos in promedios_por_categoria.items():
                if datos['cantidad'] > 0:
                    peso = float(datos['categoria_porcentaje']) / 100
                    promedio_ponderado += datos['promedio'] * peso
                    total_porcentaje += float(datos['categoria_porcentaje'])
            
            # Ajustar si el total de porcentajes no es 100%
            if total_porcentaje > 0 and total_porcentaje != 100:
                promedio_ponderado = (promedio_ponderado / total_porcentaje) * 100
            
            promedio_final = round(promedio_ponderado, 2)
            estado = 'Aprobado' if promedio_final >= configuracion_notas['nota_aprobacion'] else 'Reprobado'
            
            datos_estudiante = {
                'id': estudiante.id_usuario,
                'nombre': estudiante.nombre_completo,
                'correo': estudiante.correo,
                'calificaciones_por_asignacion': calificaciones_por_asignacion,
                'promedios_por_categoria': promedios_por_categoria,
                'promedio_final': promedio_final,
                'estado': estado,
                'total_asignaciones': len(calificaciones_por_asignacion),
                'asignaciones_completadas': len([c for c in calificaciones_por_asignacion.values() if c['valor'] is not None])
            }
            
            datos_estudiantes.append(datos_estudiante)
            calificaciones_totales.append(promedio_final)

        # Calcular estadísticas generales
        if calificaciones_totales:
            promedio_general = sum(calificaciones_totales) / len(calificaciones_totales)
            nota_mas_alta = max(calificaciones_totales)
            nota_mas_baja = min(calificaciones_totales)
        else:
            promedio_general = 0
            nota_mas_alta = 0
            nota_mas_baja = 0

        # Crear el reporte con información completa y detallada
        reporte_data = {
            'metadatos': {
                'profesor_id': current_user.id_usuario,
                'profesor_nombre': current_user.nombre_completo,
                'curso_id': curso_id,
                'curso_nombre': curso.nombreCurso,
                'asignatura_id': asignatura_id,
                'asignatura_nombre': asignatura.nombre,
                'fecha_generacion': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                'total_estudiantes': len(estudiantes)
            },
            'configuracion_notas': configuracion_notas,
            'categorias': categorias_info,
            'asignaciones': [{
                'nombre': a.nombre_calificacion, 
                'categoria_id': a.categoriaId,
                'categoria_nombre': next((cat['nombre'] for cat in categorias_info if cat['id'] == a.categoriaId), 'Sin categoría')
            } for a in asignaciones_unicas],
            'estudiantes': datos_estudiantes,
            'estadisticas_generales': {
                'promedio_general': round(promedio_general, 2),
                'nota_mas_alta': round(nota_mas_alta, 2),
                'nota_mas_baja': round(nota_mas_baja, 2),
                'total_estudiantes': len(estudiantes),
                'estudiantes_aprobados': len([e for e in datos_estudiantes if e['estado'] == 'Aprobado']),
                'estudiantes_reprobados': len([e for e in datos_estudiantes if e['estado'] == 'Reprobado']),
                'porcentaje_aprobacion': round((len([e for e in datos_estudiantes if e['estado'] == 'Aprobado']) / len(estudiantes)) * 100, 2) if estudiantes else 0
            },
            'resumen_por_categoria': {
                cat['id']: {
                    'nombre': cat['nombre'],
                    'color': cat['color'],
                    'porcentaje': cat['porcentaje'],
                    'promedio_general': round(sum([e['promedios_por_categoria'][cat['id']]['promedio'] for e in datos_estudiantes if cat['id'] in e['promedios_por_categoria']]) / len([e for e in datos_estudiantes if cat['id'] in e['promedios_por_categoria']]), 2) if any(cat['id'] in e['promedios_por_categoria'] for e in datos_estudiantes) else 0
                } for cat in categorias_info
            }
        }

        reporte = ReporteCalificaciones(
            profesor_id=current_user.id_usuario,
            curso_id=curso_id,
            asignatura_id=asignatura_id,
            nombre_curso=curso.nombreCurso,
            nombre_asignatura=asignatura.nombre,
            datos_estudiantes=reporte_data,
            promedio_general=round(promedio_general, 2),
            nota_mas_alta=round(nota_mas_alta, 2),
            nota_mas_baja=round(nota_mas_baja, 2),
            estado='pendiente'
        )
        
        db.session.add(reporte)
        db.session.commit()

        return jsonify({
            'success': True, 
            'message': 'Reporte generado y enviado al administrador correctamente',
            'reporte_id': reporte.id_reporte,
            'resumen': {
                'total_estudiantes': len(estudiantes),
                'estudiantes_aprobados': len([e for e in datos_estudiantes if e['estado'] == 'Aprobado']),
                'promedio_general': round(promedio_general, 2),
                'total_asignaciones': len(asignaciones_unicas),
                'total_categorias': len(categorias_info)
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error generando reporte: {str(e)}'}), 500


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


# ============================================================================ #
# SOLICITUDES DE CONSULTA
# ============================================================================ #

@profesor_bp.route('/solicitudes')
@login_required
def solicitudes():
    """Página para que el profesor vea y gestione las solicitudes de consulta."""
    # Obtener solicitudes pendientes del profesor
    solicitudes_pendientes = SolicitudConsulta.query.filter_by(
        profesor_id=current_user.id_usuario,
        estado='pendiente'
    ).order_by(SolicitudConsulta.fecha_solicitud.desc()).all()
    
    # Obtener todas las solicitudes del profesor
    todas_solicitudes = SolicitudConsulta.query.filter_by(
        profesor_id=current_user.id_usuario
    ).order_by(SolicitudConsulta.fecha_solicitud.desc()).all()
    
    # Agregar información del curso a cada solicitud
    for solicitud in solicitudes_pendientes:
        curso_estudiante = obtener_curso_actual_estudiante(solicitud.estudiante_id)
        solicitud.curso_estudiante = curso_estudiante
    
    for solicitud in todas_solicitudes:
        curso_estudiante = obtener_curso_actual_estudiante(solicitud.estudiante_id)
        solicitud.curso_estudiante = curso_estudiante
    
    return render_template('profesores/solicitudes.html', 
                         solicitudes_pendientes=len(solicitudes_pendientes),
                         solicitudes_pendientes_list=solicitudes_pendientes,
                         todas_solicitudes=todas_solicitudes)

@profesor_bp.route('/api/solicitudes')
@login_required
def api_obtener_solicitudes():
    """API para obtener las solicitudes del profesor."""
    try:
        solicitudes = SolicitudConsulta.query.filter_by(
            profesor_id=current_user.id_usuario
        ).order_by(SolicitudConsulta.fecha_solicitud.desc()).all()
        
        solicitudes_data = []
        for solicitud in solicitudes:
            solicitud_dict = solicitud.to_dict()
            
            # Obtener información del curso del estudiante
            curso_estudiante = obtener_curso_actual_estudiante(solicitud.estudiante_id)
            if curso_estudiante:
                solicitud_dict['curso_estudiante'] = {
                    'id': curso_estudiante.id_curso,
                    'nombre': curso_estudiante.nombreCurso
                }
            else:
                solicitud_dict['curso_estudiante'] = None
                
            solicitudes_data.append(solicitud_dict)
        
        return jsonify({
            'success': True,
            'solicitudes': solicitudes_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error obteniendo solicitudes: {str(e)}'
        }), 500

@profesor_bp.route('/api/solicitudes/<int:solicitud_id>/responder', methods=['POST'])
@login_required
def api_responder_solicitud(solicitud_id):
    """API para que el profesor responda a una solicitud."""
    try:
        data = request.get_json()
        accion = data.get('accion')  # 'aceptar' o 'denegar'
        respuesta = data.get('respuesta', '')
        
        if accion not in ['aceptar', 'denegar']:
            return jsonify({
                'success': False,
                'message': 'Acción no válida'
            }), 400
        
        # Obtener la solicitud
        solicitud = SolicitudConsulta.query.get(solicitud_id)
        
        if not solicitud:
            return jsonify({
                'success': False,
                'message': 'Solicitud no encontrada'
            }), 404
        
        # Verificar que el profesor es el destinatario
        if solicitud.profesor_id != current_user.id_usuario:
            return jsonify({
                'success': False,
                'message': 'No tienes permisos para responder esta solicitud'
            }), 403
        
        # Verificar que la solicitud esté pendiente
        if solicitud.estado != 'pendiente':
            return jsonify({
                'success': False,
                'message': 'Esta solicitud ya fue respondida'
            }), 400
        
        # Actualizar la solicitud
        solicitud.estado = 'aceptada' if accion == 'aceptar' else 'denegada'
        solicitud.respuesta_profesor = respuesta
        solicitud.fecha_respuesta = datetime.utcnow()
        
        db.session.commit()
        
        # Enviar notificación al padre
        from services.notification_service import notificar_respuesta_solicitud
        notificar_respuesta_solicitud(solicitud)
        
        response_data = {
            'success': True,
            'message': f'Solicitud {accion}da correctamente',
            'estado': solicitud.estado
        }
        
        # Si se acepta la solicitud, no redirigir (el profesor se queda en su panel)
        # La notificación se enviará al padre para que vea las calificaciones
        
        return jsonify(response_data)
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error respondiendo solicitud: {str(e)}'
        }), 500

@profesor_bp.route('/api/solicitudes/estadisticas')
@login_required
def api_estadisticas_solicitudes():
    """API para obtener estadísticas de las solicitudes del profesor."""
    try:
        total_solicitudes = SolicitudConsulta.query.filter_by(
            profesor_id=current_user.id_usuario
        ).count()
        
        solicitudes_pendientes = SolicitudConsulta.query.filter_by(
            profesor_id=current_user.id_usuario,
            estado='pendiente'
        ).count()
        
        solicitudes_aceptadas = SolicitudConsulta.query.filter_by(
            profesor_id=current_user.id_usuario,
            estado='aceptada'
        ).count()
        
        solicitudes_denegadas = SolicitudConsulta.query.filter_by(
            profesor_id=current_user.id_usuario,
            estado='denegada'
        ).count()
        
        return jsonify({
            'success': True,
            'estadisticas': {
                'total': total_solicitudes,
                'pendientes': solicitudes_pendientes,
                'aceptadas': solicitudes_aceptadas,
                'denegadas': solicitudes_denegadas
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error obteniendo estadísticas: {str(e)}'
        }), 500



# ============================================================================ #
# APIS - GESTIÓN DE PERIODOS ACADÉMICOS (PROFESORES)
# ============================================================================ #

@profesor_bp.route('/api/periodo-activo', methods=['GET'])
@login_required
def api_obtener_periodo_activo_profesor():
    """Obtiene el periodo académico activo actual."""
    try:
        from services.periodo_service import obtener_periodo_activo
        
        periodo = obtener_periodo_activo()
        
        if not periodo:
            return jsonify({
                'success': True,
                'periodo': None,
                'message': 'No hay periodo activo'
            })
        
        # Incluir información adicional útil para el profesor
        dias_restantes = periodo.dias_para_cierre()
        
        return jsonify({
            'success': True,
            'periodo': {
                **periodo.to_dict(),
                'dias_para_cierre': dias_restantes,
                'puede_modificar': periodo.puede_modificar_notas()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@profesor_bp.route('/api/periodos', methods=['GET'])
@login_required
def api_obtener_periodos_profesor():
    """Obtiene todos los periodos del ciclo activo."""
    try:
        from services.periodo_service import obtener_ciclo_activo, obtener_periodos_ciclo
        
        ciclo = obtener_ciclo_activo()
        if not ciclo:
            return jsonify({
                'success': True,
                'periodos': [],
                'message': 'No hay ciclo activo'
            })
        
        periodos = obtener_periodos_ciclo(ciclo.id_ciclo)
        
        return jsonify({
            'success': True,
            'periodos': [p.to_dict() for p in periodos]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
