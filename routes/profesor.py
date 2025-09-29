from flask import Blueprint, render_template, session, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from controllers.models import db, Usuario, Asignatura, Clase, Matricula, Calificacion, Curso, Asistencia, CategoriaCalificacion
from datetime import datetime, date
import json

profesor_bp = Blueprint('profesor', __name__, url_prefix='/profesor')

# ============================================================================
# RUTAS PRINCIPALES
# ============================================================================

@profesor_bp.route('/dashboard')
@login_required
def dashboard():
    """Panel principal del profesor"""
    curso_id = session.get('curso_seleccionado')
    curso_actual = Curso.query.get(curso_id) if curso_id else None
    
    clases = Clase.query.filter_by(profesorId=current_user.id_usuario).all()
    
    return render_template('profesores/dashboard.html', 
                         clases=clases, 
                         curso_actual=curso_actual)

@profesor_bp.route('/gestion-lc')
@login_required
def gestion_lc():
    """Página unificada de gestión de listas y calificaciones"""
    curso_id = session.get('curso_seleccionado')
    
    if not curso_id:
        flash('Primero debes seleccionar un curso', 'warning')
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
    
    # Verificar que el profesor realmente tenga acceso a este curso
    cursos_profesor = obtener_cursos_del_profesor(current_user.id_usuario)
    curso_valido = any(curso.id == int(curso_id) for curso in cursos_profesor)
    
    if not curso_valido:
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
# RUTAS SECUNDARIAS
# ============================================================================

@profesor_bp.route('/ver_horario_clases')
@login_required
def ver_horario_clases():
    """Muestra el horario de clases del profesor"""
    clases = Clase.query.filter_by(profesorId=current_user.id_usuario).all()
    return render_template('profesor/ver_horario_clases.html', clases=clases)

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
    return render_template('profesor/perfil.html')

@profesor_bp.route('/soporte')
@login_required
def soporte():
    """Página de soporte para el profesor"""
    return render_template('profesor/soporte.html')

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
        
        if not validar_estudiante_en_curso(estudiante_id, curso_id):
            return jsonify({'success': False, 'message': 'El estudiante no pertenece a este curso'}), 400
        
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
# FUNCIONES AUXILIARES
# ============================================================================

def obtener_cursos_del_profesor(profesor_id):
    """Obtiene todos los cursos únicos del profesor basado en sus asignaturas asignadas"""
    # Obtener cursos a través de las clases donde el profesor está asignado
    cursos = Curso.query.join(Clase, Curso.id == Clase.cursoId)\
        .filter(Clase.profesorId == profesor_id)\
        .distinct().all()
    
    return cursos

def obtener_estudiantes_por_curso(curso_id):
    """Obtiene estudiantes matriculados en un curso"""
    return Usuario.query.join(Matricula, Usuario.id_usuario == Matricula.estudianteId)\
        .filter(Matricula.cursoId == curso_id, Usuario.rol.has(nombre='Estudiante')).all()

def obtener_asignaturas_por_curso_y_profesor(curso_id, profesor_id):
    """Obtiene asignaturas del profesor en un curso específico"""
    return Asignatura.query.join(Clase)\
        .filter(Clase.cursoId == curso_id, Clase.profesorId == profesor_id).all()

def obtener_asignaturas_del_profesor(profesor_id):
    """Obtiene todas las asignaturas del profesor"""
    return Asignatura.query.join(Clase)\
        .filter(Clase.profesorId == profesor_id)\
        .distinct().all()

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