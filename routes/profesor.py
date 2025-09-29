from flask import Blueprint, render_template, session, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from controllers.models import db, Usuario, Asignatura, Clase, Matricula, Calificacion, Curso, Asistencia, CategoriaCalificacion, HorarioCompartido, HorarioCurso, HorarioGeneral, Salon,Evento
from datetime import datetime, date
import json

profesor_bp = Blueprint('profesor', __name__, url_prefix='/profesor')

# ============================================================================
# RUTAS PRINCIPALES - ACTUALIZADAS
# ============================================================================

@profesor_bp.route('/dashboard')
@login_required
def dashboard():
    """Panel principal del profesor con horarios compartidos"""
    curso_id = session.get('curso_seleccionado')
    curso_actual = Curso.query.get(curso_id) if curso_id else None
    
    # Obtener horarios compartidos detallados del profesor
    horarios_detallados = obtener_horarios_detallados_profesor(current_user.id_usuario)
    
    # Obtener clases (para compatibilidad)
    clases = Clase.query.filter_by(profesorId=current_user.id_usuario).all()
    
    return render_template('profesores/dashboard.html', 
                         clases=clases, 
                         curso_actual=curso_actual,
                         horarios_detallados=horarios_detallados)

@profesor_bp.route('/gestion-lc')
@login_required
def gestion_lc():
    """Página unificada de gestión de listas y calificaciones"""
    curso_id = session.get('curso_seleccionado')
    
    if not curso_id:
        flash('Primero debes seleccionar un curso', 'warning')
        return redirect(url_for('profesor.seleccionar_curso'))
    
    # Verificar que el profesor tenga acceso a este curso a través de horarios compartidos
    tiene_acceso = verificar_acceso_curso_profesor(current_user.id_usuario, curso_id)
    
    if not tiene_acceso:
        flash('No tienes acceso a este curso', 'error')
        return redirect(url_for('profesor.seleccionar_curso'))
    
    curso = Curso.query.get(curso_id)
    estudiantes = obtener_estudiantes_por_curso(curso_id)
    asignaturas = obtener_asignaturas_por_curso_y_profesor(curso_id, current_user.id_usuario)
    categorias = CategoriaCalificacion.query.all()
    calificaciones = obtener_calificaciones_por_curso(curso_id)
    
    return render_template('profesor/Gestion_LC.html',
                         curso=curso,
                         estudiantes=estudiantes,
                         asignaturas=asignaturas,
                         categorias=categorias,
                         calificaciones=calificaciones)

@profesor_bp.route('/seleccionar-curso')
@login_required
def seleccionar_curso():
    """Permite al profesor seleccionar un curso para trabajar"""
    cursos = obtener_cursos_del_profesor(current_user.id_usuario)
    return render_template('profesores/seleccionar_curso.html', cursos=cursos)

@profesor_bp.route('/guardar-curso-seleccionado', methods=['POST'])
@login_required
def guardar_curso_seleccionado():
    """Guarda el curso seleccionado en la sesión y redirige a gestión LC"""
    curso_id = request.form.get('curso_id')
    
    if not curso_id:
        flash('Por favor selecciona un curso', 'error')
        return redirect(url_for('profesor.seleccionar_curso'))
    
    # Verificar que el profesor tenga acceso a este curso a través de horarios compartidos
    tiene_acceso = verificar_acceso_curso_profesor(current_user.id_usuario, int(curso_id))
    
    if not tiene_acceso:
        flash('No tienes acceso a este curso', 'error')
        return redirect(url_for('profesor.seleccionar_curso'))
    
    session['curso_seleccionado'] = int(curso_id)
    curso = Curso.query.get(curso_id)
    flash(f'Curso "{curso.nombreCurso}" seleccionado correctamente', 'success')
    
    # Redirigir a la gestión de listas y calificaciones
    return redirect(url_for('profesor.gestion_lc'))

# ============================================================================
# RUTAS ACADÉMICAS (MANTENIDAS POR COMPATIBILIDAD)
# ============================================================================

@profesor_bp.route('/ver_lista_estudiantes')
@login_required
def ver_lista_estudiantes():
    """Muestra la lista de estudiantes del curso seleccionado"""
    curso_id = session.get('curso_seleccionado')
    
    if not curso_id:
        flash('Primero debes seleccionar un curso', 'warning')
        return redirect(url_for('profesor.seleccionar_curso'))
    
    # Verificar acceso
    if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
        flash('No tienes acceso a este curso', 'error')
        return redirect(url_for('profesor.seleccionar_curso'))
    
    estudiantes = obtener_estudiantes_por_curso(curso_id)
    curso = Curso.query.get(curso_id)
    
    return render_template('profesor/ver_lista_estudiantes.html', 
                         estudiantes=estudiantes, 
                         curso=curso)

@profesor_bp.route('/registrar_calificaciones')
@login_required
def registrar_calificaciones():
    """Permite al profesor registrar y editar calificaciones"""
    curso_id = session.get('curso_seleccionado')
    
    if not curso_id:
        flash('Primero debes seleccionar un curso', 'warning')
        return redirect(url_for('profesor.seleccionar_curso'))
    
    # Verificar acceso
    if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
        flash('No tienes acceso a este curso', 'error')
        return redirect(url_for('profesor.seleccionar_curso'))
    
    estudiantes = obtener_estudiantes_por_curso(curso_id)
    asignaturas = obtener_asignaturas_por_curso_y_profesor(curso_id, current_user.id_usuario)
    categorias = CategoriaCalificacion.query.all()
    calificaciones = obtener_calificaciones_por_curso(curso_id)
    curso = Curso.query.get(curso_id)
    
    return render_template('profesor/registrar_calificaciones.html',
                         estudiantes=estudiantes,
                         asignaturas=asignaturas,
                         categorias=categorias,
                         calificaciones=calificaciones,
                         curso=curso)

@profesor_bp.route('/asistencia')
@login_required
def asistencia():
    """Página para gestionar asistencias"""
    curso_id = session.get('curso_seleccionado')
    
    if not curso_id:
        flash('Primero debes seleccionar un curso', 'warning')
        return redirect(url_for('profesor.seleccionar_curso'))
    
    # Verificar acceso
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

# ============================================================================
# RUTAS SECUNDARIAS - ACTUALIZADAS
# ============================================================================

@profesor_bp.route('/ver_horario_clases')
@login_required
def ver_horario_clases():
    """Muestra el horario de clases del profesor (incluye horarios compartidos)"""
    # Obtener horarios compartidos con detalles
    horarios_detallados = obtener_horarios_detallados_profesor(current_user.id_usuario)
    
    # Obtener clases (para compatibilidad)
    clases = Clase.query.filter_by(profesorId=current_user.id_usuario).all()
    
    return render_template('profesores/HorarioC.html', 
                         horarios_detallados=horarios_detallados,
                         clases=clases)

@profesor_bp.route('/comunicaciones')
@login_required
def comunicaciones():
    """Página para ver y enviar comunicaciones a estudiantes y padres"""
    return render_template('profesor/comunicaciones.html')

@profesor_bp.route('/cursos')
@login_required
def cursos():
    """Página para gestionar cursos del profesor"""
    cursos = obtener_cursos_del_profesor(current_user.id_usuario)
    return render_template('profesores/cursos.html', cursos=cursos)

@profesor_bp.route('/asignaturas')
@login_required
def asignaturas():
    """Página para gestionar asignaturas del profesor"""
    asignaturas = obtener_asignaturas_del_profesor(current_user.id_usuario)
    return render_template('profesores/asignaturas.html', asignaturas=asignaturas)

@profesor_bp.route('/perfil')
@login_required
def perfil():
    """Página para que el profesor gestione la información de su perfil"""
    # Obtener estadísticas del profesor
    total_cursos = len(obtener_cursos_del_profesor(current_user.id_usuario))
    total_asignaturas = len(obtener_asignaturas_del_profesor(current_user.id_usuario))
    horarios_compartidos = len(obtener_horarios_compartidos_profesor(current_user.id_usuario))
    
    return render_template('profesor/perfil.html',
                         total_cursos=total_cursos,
                         total_asignaturas=total_asignaturas,
                         total_horarios=horarios_compartidos)

@profesor_bp.route('/soporte')
@login_required
def soporte():
    """Página de soporte para el profesor"""
    return render_template('profesor/soporte.html')

# ============================================================================
# APIs - HORARIOS COMPARTIDOS
# ============================================================================

@profesor_bp.route('/api/mis-horarios')
@login_required
def api_mis_horarios():
    """API para obtener los horarios compartidos del profesor con detalles completos"""
    try:
        horarios_detallados = obtener_horarios_detallados_profesor(current_user.id_usuario)
        
        return jsonify({
            'success': True, 
            'horarios': horarios_detallados,
            'total': len(horarios_detallados)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@profesor_bp.route('/api/mis-cursos')
@login_required
def api_mis_cursos():
    """API para obtener los cursos del profesor"""
    try:
        cursos = obtener_cursos_del_profesor(current_user.id_usuario)
        
        cursos_data = [{
            'id': curso.id,
            'nombre': curso.nombreCurso,
            'sede': curso.sede.nombre if curso.sede else 'N/A',
            'horario_general': curso.horario_general.nombre if curso.horario_general else 'No asignado',
            'total_estudiantes': len(obtener_estudiantes_por_curso(curso.id))
        } for curso in cursos]
        
        return jsonify({
            'success': True, 
            'cursos': cursos_data,
            'total': len(cursos_data)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# APIs - ASISTENCIAS
# ============================================================================

@profesor_bp.route('/api/guardar-asistencia', methods=['POST'])
@login_required
def guardar_asistencia():
    """API para guardar asistencias desde la interfaz"""
    try:
        data = request.get_json()
        fecha_str = data.get('fecha')
        asistencias = data.get('asistencias', [])
        curso_id = session.get('curso_seleccionado')
        
        if not curso_id:
            return jsonify({'success': False, 'message': 'No hay curso seleccionado'}), 400
        
        # Verificar acceso al curso
        if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes acceso a este curso'}), 403
        
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        clase_id = obtener_clase_para_asistencia(curso_id, current_user.id_usuario)
        
        if not clase_id:
            return jsonify({'success': False, 'message': 'No hay clases asignadas para este curso'}), 400
        
        for asistencia_data in asistencias:
            guardar_o_actualizar_asistencia(
                asistencia_data.get('estudiante_id'),
                clase_id,
                fecha,
                asistencia_data.get('estado')
            )
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Asistencias guardadas correctamente'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al guardar asistencias: {str(e)}'}), 500

@profesor_bp.route('/api/obtener-asistencias', methods=['GET'])
@login_required
def obtener_asistencias():
    """API para obtener asistencias de un mes específico"""
    try:
        curso_id = session.get('curso_seleccionado')
        año = request.args.get('año', type=int)
        mes = request.args.get('mes', type=int)
        
        if not curso_id:
            return jsonify({'success': False, 'message': 'No hay curso seleccionado'}), 400
        
        # Verificar acceso al curso
        if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes acceso a este curso'}), 403
        
        asistencias = Asistencia.query\
            .join(Clase, Asistencia.claseId == Clase.id)\
            .filter(
                Clase.cursoId == curso_id,
                Clase.profesorId == current_user.id_usuario,
                db.extract('year', Asistencia.fecha) == año,
                db.extract('month', Asistencia.fecha) == mes
            ).all()
        
        asistencias_data = [
            {
                'estudiante_id': asistencia.estudianteId,
                'fecha': asistencia.fecha.strftime('%Y-%m-%d'),
                'estado': asistencia.estado
            }
            for asistencia in asistencias
        ]
        
        return jsonify({'success': True, 'asistencias': asistencias_data})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener asistencias: {str(e)}'}), 500

# ============================================================================
# APIs - CALIFICACIONES
# ============================================================================

@profesor_bp.route('/api/guardar-calificacion', methods=['POST'])
@login_required
def guardar_calificacion():
    """API para guardar/actualizar calificaciones"""
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
        
        # Verificar acceso al curso
        if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes acceso a este curso'}), 403
        
        if not validar_estudiante_en_curso(estudiante_id, curso_id):
            return jsonify({'success': False, 'message': 'El estudiante no pertenece a este curso'}), 400
        
        # Verificar que el profesor tenga esta asignatura en el curso
        if not verificar_asignatura_profesor_en_curso(asignatura_id, current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes esta asignatura en el curso'}), 403
        
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

@profesor_bp.route('/api/obtener-calificaciones', methods=['GET'])
@login_required
def obtener_calificaciones_api():
    """API para obtener calificaciones del curso"""
    try:
        curso_id = session.get('curso_seleccionado')
        
        if not curso_id:
            return jsonify({'success': False, 'message': 'No hay curso seleccionado'}), 400
        
        # Verificar acceso al curso
        if not verificar_acceso_curso_profesor(current_user.id_usuario, curso_id):
            return jsonify({'success': False, 'message': 'No tienes acceso a este curso'}), 403
        
        calificaciones = obtener_calificaciones_por_curso(curso_id)
        
        calificaciones_data = [
            {
                'id': cal.id,
                'estudiante_id': cal.estudianteId,
                'estudiante_nombre': f"{cal.estudiante.nombre} {cal.estudiante.apellido}",
                'asignatura_id': cal.asignaturaId,
                'asignatura_nombre': cal.asignatura.nombre,
                'categoria_id': cal.categoriaId,
                'categoria_nombre': cal.categoria.nombre,
                'valor': float(cal.valor),
                'observaciones': cal.observaciones
            }
            for cal in calificaciones
        ]
        
        return jsonify({'success': True, 'calificaciones': calificaciones_data})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener calificaciones: {str(e)}'}), 500

@profesor_bp.route('/api/obtener-estadisticas-calificaciones', methods=['GET'])
@login_required
def obtener_estadisticas_calificaciones():
    """API para obtener estadísticas de calificaciones"""
    try:
        curso_id = session.get('curso_seleccionado')
        
        if not curso_id:
            return jsonify({'success': False, 'message': 'No hay curso seleccionado'}), 400
        
        # Verificar acceso al curso
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
        
        valores = [float(cal.valor) for cal in calificaciones]
        
        estadisticas = {
            'minima': min(valores),
            'maxima': max(valores),
            'promedio': round(sum(valores) / len(valores), 2),
            'total': len(valores)
        }
        
        return jsonify({'success': True, **estadisticas})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener estadísticas: {str(e)}'}), 500

# ============================================================================
# FUNCIONES AUXILIARES - ACTUALIZADAS
# ============================================================================

def obtener_cursos_del_profesor(profesor_id):
    """Obtiene todos los cursos únicos del profesor basado en horarios compartidos Y clases"""
    # Cursos a través de horarios compartidos (nuevo sistema)
    cursos_horarios = Curso.query.join(HorarioCompartido, Curso.id == HorarioCompartido.curso_id)\
        .filter(HorarioCompartido.profesor_id == profesor_id)\
        .distinct().all()
    
    # Cursos a través de clases (sistema antiguo - para compatibilidad)
    cursos_clases = Curso.query.join(Clase, Curso.id == Clase.cursoId)\
        .filter(Clase.profesorId == profesor_id)\
        .distinct().all()
    
    # Combinar y eliminar duplicados
    todos_cursos = list(set(cursos_horarios + cursos_clases))
    
    return todos_cursos

def obtener_horarios_compartidos_profesor(profesor_id):
    """Obtiene los horarios compartidos del profesor"""
    return HorarioCompartido.query.filter_by(profesor_id=profesor_id).all()

def obtener_horarios_detallados_profesor(profesor_id):
    """Obtiene horarios compartidos con detalles completos"""
    horarios_compartidos = HorarioCompartido.query.filter_by(profesor_id=profesor_id).all()
    
    horarios_detallados = []
    for hc in horarios_compartidos:
        # Obtener detalles del horario específico
        horarios_curso = HorarioCurso.query.filter_by(
            curso_id=hc.curso_id,
            asignatura_id=hc.asignatura_id,
            horario_general_id=hc.horario_general_id
        ).all()
        
        for horario_curso in horarios_curso:
            horarios_detallados.append({
                'curso_nombre': hc.curso.nombreCurso,
                'asignatura_nombre': hc.asignatura.nombre,
                'horario_general_nombre': hc.horario_general.nombre if hc.horario_general else 'Sin nombre',
                'fecha_compartido': hc.fecha_compartido.strftime('%d/%m/%Y'),
                'dia_semana': horario_curso.dia_semana,
                'hora_inicio': horario_curso.hora_inicio,
                'hora_fin': obtener_hora_fin_horario(horario_curso),
                'salon': horario_curso.salon.nombre if horario_curso.salon else 'No asignado',
                'sede': hc.curso.sede.nombre if hc.curso.sede else 'N/A'
            })
    
    return horarios_detallados

def obtener_hora_fin_horario(horario_curso):
    """Obtiene la hora de fin basada en el horario general"""
    if horario_curso.horario_general:
        # Buscar el bloque correspondiente en el horario general
        bloque = HorarioGeneral.query.get(horario_curso.horario_general_id)
        if bloque:
            return bloque.horaFin.strftime('%H:%M')
    return '--:--'

def verificar_acceso_curso_profesor(profesor_id, curso_id):
    """Verifica si el profesor tiene acceso a un curso específico"""
    # Verificar en horarios compartidos
    acceso_horarios = HorarioCompartido.query.filter_by(
        profesor_id=profesor_id,
        curso_id=curso_id
    ).first()
    
    # Verificar en clases tradicionales
    acceso_clases = Clase.query.filter_by(
        profesorId=profesor_id,
        cursoId=curso_id
    ).first()
    
    return acceso_horarios is not None or acceso_clases is not None

def verificar_asignatura_profesor_en_curso(asignatura_id, profesor_id, curso_id):
    """Verifica si el profesor tiene una asignatura específica en un curso"""
    # Verificar en horarios compartidos
    acceso_horarios = HorarioCompartido.query.filter_by(
        profesor_id=profesor_id,
        curso_id=curso_id,
        asignatura_id=asignatura_id
    ).first()
    
    # Verificar en clases tradicionales
    acceso_clases = Clase.query.filter_by(
        profesorId=profesor_id,
        cursoId=curso_id,
        asignaturaId=asignatura_id
    ).first()
    
    return acceso_horarios is not None or acceso_clases is not None

def obtener_estudiantes_por_curso(curso_id):
    """Obtiene estudiantes matriculados en un curso"""
    return Usuario.query.join(Matricula, Usuario.id_usuario == Matricula.estudianteId)\
        .filter(Matricula.cursoId == curso_id, Usuario.rol.has(nombre='Estudiante')).all()

def obtener_asignaturas_por_curso_y_profesor(curso_id, profesor_id):
    """Obtiene asignaturas del profesor en un curso específico (de horarios compartidos Y clases)"""
    # De horarios compartidos
    asignaturas_horarios = Asignatura.query.join(HorarioCompartido)\
        .filter(
            HorarioCompartido.curso_id == curso_id, 
            HorarioCompartido.profesor_id == profesor_id
        ).all()
    
    # De clases (sistema antiguo)
    asignaturas_clases = Asignatura.query.join(Clase)\
        .filter(Clase.cursoId == curso_id, Clase.profesorId == profesor_id).all()
    
    # Combinar y eliminar duplicados
    todas_asignaturas = list(set(asignaturas_horarios + asignaturas_clases))
    
    return todas_asignaturas

def obtener_asignaturas_del_profesor(profesor_id):
    """Obtiene todas las asignaturas del profesor"""
    # De horarios compartidos
    asignaturas_horarios = Asignatura.query.join(HorarioCompartido)\
        .filter(HorarioCompartido.profesor_id == profesor_id)\
        .distinct().all()
    
    # De clases (sistema antiguo)
    asignaturas_clases = Asignatura.query.join(Clase)\
        .filter(Clase.profesorId == profesor_id)\
        .distinct().all()
    
    # Combinar y eliminar duplicados
    todas_asignaturas = list(set(asignaturas_horarios + asignaturas_clases))
    
    return todas_asignaturas

def obtener_calificaciones_por_curso(curso_id):
    """Obtiene calificaciones de estudiantes de un curso"""
    return Calificacion.query\
        .join(Usuario, Calificacion.estudianteId == Usuario.id_usuario)\
        .join(Matricula, Usuario.id_usuario == Matricula.estudianteId)\
        .filter(Matricula.cursoId == curso_id).all()

def obtener_asistencias_por_curso(curso_id):
    """Obtiene asistencias de estudiantes de un curso"""
    return Asistencia.query\
        .join(Usuario, Asistencia.estudianteId == Usuario.id_usuario)\
        .join(Matricula, Usuario.id_usuario == Matricula.estudianteId)\
        .filter(Matricula.cursoId == curso_id).all()

def obtener_clase_para_asistencia(curso_id, profesor_id):
    """Obtiene una clase para registrar asistencia"""
    clases = Clase.query.filter_by(cursoId=curso_id, profesorId=profesor_id).all()
    return clases[0].id if clases else None

def guardar_o_actualizar_asistencia(estudiante_id, clase_id, fecha, estado):
    """Guarda o actualiza una asistencia"""
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
    """Valida que un estudiante pertenezca a un curso"""
    return Matricula.query.filter_by(
        estudianteId=estudiante_id,
        cursoId=curso_id
    ).first() is not None


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