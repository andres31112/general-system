from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from controllers.models import db, Usuario, Clase, Matricula, Rol, Asignatura, Calificacion, Asistencia, CategoriaCalificacion, ConfiguracionCalificacion
from sqlalchemy import and_
from datetime import datetime
import json

profesor_bp = Blueprint('profesor', __name__, url_prefix='/profesor')

@profesor_bp.route('/gestion_asistencia_calificaciones/<int:clase_id>')
@login_required
def gestion_asistencia_calificaciones(clase_id):
    """Muestra la interfaz para gestionar asistencia y calificaciones de una clase"""
    clase = Clase.query.filter_by(id=clase_id, profesorId=current_user.id_usuario).first()
    if not clase:
        return "Clase no encontrada o no autorizada", 403

    estudiantes = (
        Usuario.query
        .join(Matricula, Usuario.id_usuario == Matricula.estudianteId)
        .join(Rol, Usuario.id_rol_fk == Rol.id_rol)
        .filter(
            and_(
                Matricula.cursoId == clase.cursoId,
                Rol.nombre == 'Estudiante'
            )
        )
        .order_by(Usuario.apellido.asc(), Usuario.nombre.asc())
        .all()
    )

    asignatura = Asignatura.query.get(clase.asignaturaId)
    configuracion = ConfiguracionCalificacion.query.first()  # Asumiendo una configuración global
    categorias = CategoriaCalificacion.query.all()

    return render_template(
        'profesor/gestion_asistencia_calificaciones.html',
        clase=clase,
        estudiantes=estudiantes,
        asignatura=asignatura,
        configuracion=configuracion,
        categorias=categorias
    )

@profesor_bp.route('/api/asistencia/<int:clase_id>/<string:fecha>', methods=['GET'])
@login_required
def obtener_asistencia(clase_id, fecha):
    """Obtiene los datos de asistencia para una fecha y clase específicas"""
    clase = Clase.query.filter_by(id=clase_id, profesorId=current_user.id_usuario).first()
    if not clase:
        return jsonify({'error': 'Clase no encontrada o no autorizada'}), 403

    try:
        fecha_dt = datetime.strptime(fecha, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Formato de fecha inválido'}), 400

    asistencias = Asistencia.query.filter_by(claseId=clase_id, fecha=fecha_dt).all()
    asistencia_data = {
        str(a.estudianteId): {
            'estado': a.estado,
            'comentario': a.comentario
        } for a in asistencias
    }

    estudiantes = (
        Usuario.query
        .join(Matricula, Usuario.id_usuario == Matricula.estudianteId)
        .filter(Matricula.cursoId == clase.cursoId, Rol.nombre == 'Estudiante')
        .all()
    )

    return jsonify({
        'estudiantes': [{'id': e.id_usuario, 'name': f'{e.nombre} {e.apellido}'} for e in estudiantes],
        'asistencia': asistencia_data
    })

@profesor_bp.route('/api/asistencia/<int:clase_id>', methods=['POST'])
@login_required
def guardar_asistencia(clase_id):
    """Guarda la asistencia para una clase en una fecha específica"""
    clase = Clase.query.filter_by(id=clase_id, profesorId=current_user.id_usuario).first()
    if not clase:
        return jsonify({'error': 'Clase no encontrada o no autorizada'}), 403

    data = request.get_json()
    fecha = data.get('fecha')
    asistencias = data.get('asistencias', {})

    try:
        fecha_dt = datetime.strptime(fecha, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Formato de fecha inválido'}), 400

    for estudiante_id, estado in asistencias.items():
        asistencia = Asistencia.query.filter_by(claseId=clase_id, estudianteId=estudiante_id, fecha=fecha_dt).first()
        if not asistencia:
            asistencia = Asistencia(claseId=clase_id, estudianteId=estudiante_id, fecha=fecha_dt)
        asistencia.estado = estado.get('estado', 'presente')
        asistencia.comentario = estado.get('comentario', '')
        db.session.add(asistencia)

    db.session.commit()
    return jsonify({'message': 'Asistencia guardada correctamente'})

@profesor_bp.route('/api/calificaciones/<int:clase_id>', methods=['GET'])
@login_required
def obtener_calificaciones(clase_id):
    """Obtiene las calificaciones de una clase"""
    clase = Clase.query.filter_by(id=clase_id, profesorId=current_user.id_usuario).first()
    if not clase:
        return jsonify({'error': 'Clase no encontrada o no autorizada'}), 403

    estudiantes = (
        Usuario.query
        .join(Matricula, Usuario.id_usuario == Matricula.estudianteId)
        .filter(Matricula.cursoId == clase.cursoId, Rol.nombre == 'Estudiante')
        .all()
    )

    categorias = CategoriaCalificacion.query.all()
    calificaciones = Calificacion.query.filter_by(asignaturaId=clase.asignaturaId).all()

    calificaciones_data = {}
    for estudiante in estudiantes:
        calificaciones_data[estudiante.id_usuario] = [
            next((c.valor for c in calificaciones if c.estudianteId == estudiante.id_usuario and c.categoriaId == cat.id), '')
            for cat in categorias
        ]

    return jsonify({
        'estudiantes': [{'id': e.id_usuario, 'name': f'{e.nombre} {e.apellido}'} for e in estudiantes],
        'categorias': [{'id': c.id, 'nombre': c.nombre, 'porcentaje': float(c.porcentaje)} for c in categorias],
        'calificaciones': calificaciones_data,
        'configuracion': {
            'notaMinima': float(ConfiguracionCalificacion.query.first().notaMinima),
            'notaMaxima': float(ConfiguracionCalificacion.query.first().notaMaxima),
            'notaMinimaAprobacion': float(ConfiguracionCalificacion.query.first().notaMinimaAprobacion)
        }
    })

@profesor_bp.route('/api/calificaciones/<int:clase_id>', methods=['POST'])
@login_required
def guardar_calificaciones(clase_id):
    """Guarda las calificaciones de una clase"""
    clase = Clase.query.filter_by(id=clase_id, profesorId=current_user.id_usuario).first()
    if not clase:
        return jsonify({'error': 'Clase no encontrada o no autorizada'}), 403

    data = request.get_json()
    calificaciones = data.get('calificaciones', {})
    categorias = CategoriaCalificacion.query.all()

    for estudiante_id, notas in calificaciones.items():
        for i, nota in enumerate(notas):
            if nota is not None and nota != '':
                calificacion = Calificacion.query.filter_by(
                    asignaturaId=clase.asignaturaId,
                    estudianteId=estudiante_id,
                    categoriaId=categorias[i].id
                ).first()
                if not calificacion:
                    calificacion = Calificacion(
                        asignaturaId=clase.asignaturaId,
                        estudianteId=estudiante_id,
                        categoriaId=categorias[i].id
                    )
                calificacion.valor = float(nota)
                db.session.add(calificacion)

    db.session.commit()
    return jsonify({'message': 'Calificaciones guardadas correctamente'})

@profesor_bp.route('/api/categorias/<int:clase_id>', methods=['POST'])
@login_required
def gestionar_categoria(clase_id):
    """Añade o edita una categoría de calificación"""
    clase = Clase.query.filter_by(id=clase_id, profesorId=current_user.id_usuario).first()
    if not clase:
        return jsonify({'error': 'Clase no encontrada o no autorizada'}), 403

    data = request.get_json()
    nombre = data.get('nombre')
    porcentaje = data.get('porcentaje')
    categoria_id = data.get('categoria_id')

    if categoria_id:
        categoria = CategoriaCalificacion.query.get(categoria_id)
        if not categoria:
            return jsonify({'error': 'Categoría no encontrada'}), 404
        categoria.nombre = nombre
        categoria.porcentaje = float(porcentaje)
    else:
        categoria = CategoriaCalificacion(
            nombre=nombre,
            color='blue',  # Ajusta según necesites
            porcentaje=float(porcentaje)
        )
        db.session.add(categoria)

    db.session.commit()
    return jsonify({'message': 'Categoría guardada correctamente', 'categoria': {'id': categoria.id, 'nombre': categoria.nombre, 'porcentaje': float(categoria.porcentaje)}})

@profesor_bp.route('/api/categorias/<int:clase_id>/<int:categoria_id>', methods=['DELETE'])
@login_required
def eliminar_categoria(clase_id, categoria_id):
    """Elimina una categoría de calificación"""
    clase = Clase.query.filter_by(id=clase_id, profesorId=current_user.id_usuario).first()
    if not clase:
        return jsonify({'error': 'Clase no encontrada o no autorizada'}), 403

    categoria = CategoriaCalificacion.query.get(categoria_id)
    if not categoria:
        return jsonify({'error': 'Categoría no encontrada'}), 404

    db.session.delete(categoria)
    db.session.commit()
    return jsonify({'message': 'Categoría eliminada correctamente'})