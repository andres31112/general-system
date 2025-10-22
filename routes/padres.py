from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash, current_app
from flask_login import login_required, current_user
from controllers.decorators import role_required, permission_required
from controllers.models import (
    db, Usuario, Rol, Comunicacion, SolicitudConsulta, Asignatura,
    Calificacion, Asistencia, Clase, Matricula, Curso, HorarioCompartido, Salon, Sede
)

padre_bp = Blueprint('padre', __name__, url_prefix='/padre')

def verificar_relacion_padre_hijo(padre_id, hijo_id):
    """Verifica si existe una relación padre-hijo entre los usuarios dados usando SQL directo."""
    try:
        from sqlalchemy import text
        
        result = db.session.execute(text("""
            SELECT 1 FROM estudiante_padre 
            WHERE padre_id = :padre_id AND estudiante_id = :hijo_id
        """), {'padre_id': padre_id, 'hijo_id': hijo_id}).first()
        
        return result is not None
    except Exception as e:
        print(f"Error verificando relación padre-hijo: {e}")
        return False

@padre_bp.route('/dashboard')
@login_required
@role_required('Padre')
def dashboard():
    """Muestra el panel principal del padre con un resumen del progreso del hijo/a."""
    from controllers.models import Calificacion, Matricula, Asistencia, Clase
    from sqlalchemy import func, and_
    from datetime import datetime, timedelta
    
    try:
        # Obtener hijos del padre
        hijos = current_user.hijos.all()
        
        # Inicializar variables para estadísticas
        total_hijos = len(hijos)
        promedio_general = 0
        total_clases_inscritas = 0
        mensajes_profesores = 0
        calificaciones_recientes = []
        anuncios_importantes = []
        
        if hijos:
            # Calcular promedio general de todos los hijos
            promedios_hijos = []
            for hijo in hijos:
                # Obtener calificaciones del hijo
                calificaciones_hijo = Calificacion.query.filter_by(estudianteId=hijo.id_usuario).all()
                if calificaciones_hijo:
                    valores = [float(cal.valor) for cal in calificaciones_hijo if cal.valor is not None]
                    if valores:
                        promedio_hijo = sum(valores) / len(valores)
                        promedios_hijos.append(promedio_hijo)
                
                # Obtener clases inscritas del hijo
                clases_hijo = Matricula.query.filter_by(estudianteId=hijo.id_usuario).count()
                total_clases_inscritas += clases_hijo
                
                # Obtener calificaciones recientes (últimas 5)
                calificaciones_recientes_hijo = Calificacion.query.filter_by(estudianteId=hijo.id_usuario).order_by(Calificacion.fecha_registro.desc()).limit(5).all()
                calificaciones_recientes.extend(calificaciones_recientes_hijo)
            
            if promedios_hijos:
                promedio_general = sum(promedios_hijos) / len(promedios_hijos)
            
            # Obtener mensajes de profesores (comunicaciones donde el padre es destinatario)
            mensajes_profesores = Comunicacion.query.filter_by(destinatario_id=current_user.id_usuario).count()
            
            # Obtener anuncios importantes (comunicaciones del sistema)
            anuncios_importantes = Comunicacion.query.filter_by(remitente_id=None).order_by(Comunicacion.fecha_envio.desc()).limit(3).all()
        
        return render_template('padres/dashboard.html',
                             total_hijos=total_hijos,
                             promedio_general=promedio_general,
                             total_clases_inscritas=total_clases_inscritas,
                             mensajes_profesores=mensajes_profesores,
                             calificaciones_recientes=calificaciones_recientes,
                             anuncios_importantes=anuncios_importantes,
                             hijos=hijos)
    
    except Exception as e:
        flash(f'Error cargando el dashboard: {str(e)}', 'error')
        return render_template('padres/dashboard.html',
                             total_hijos=0,
                             promedio_general=0,
                             total_clases_inscritas=0,
                             mensajes_profesores=0,
                             calificaciones_recientes=[],
                             anuncios_importantes=[],
                             hijos=[])

@padre_bp.route('/comunicaciones')
@login_required
@role_required('Padre')
def comunicaciones():
    """Página para que el padre vea comunicados de la institución."""
    return render_template('padres/comunicaciones.html')

@padre_bp.route('/consultar_estudiante')
@login_required
@role_required('Padre')
def consultar_estudiante():
    """Página para que el padre envíe solicitudes de consulta de notas."""
    # Obtener asignaturas disponibles
    asignaturas = Asignatura.query.filter_by(estado='activa').all()
    
    # Obtener solicitudes previas del padre
    solicitudes = SolicitudConsulta.query.filter_by(padre_id=current_user.id_usuario).order_by(SolicitudConsulta.fecha_solicitud.desc()).all()
    
    return render_template('padres/consultar_estudiante.html', 
                         asignaturas=asignaturas, 
                         solicitudes=solicitudes)

@padre_bp.route('/notificaciones')
@login_required
@role_required('Padre')
def notificaciones():
    """Página de notificaciones para el padre."""
    return render_template('padres/notificaciones.html')

@padre_bp.route('/informacion_academica')
@login_required
@role_required('Padre')
def informacion_academica():
    """Página de información académica del padre."""
    # Obtener los hijos del padre usando la relación backref
    hijos = current_user.hijos.all()
    
    return render_template('padres/informacion_academica.html', hijos=hijos)

@padre_bp.route('/horario_clases')
@login_required
@role_required('Padre')
def horario_clases():
    """Página de horario de clases del padre."""
    # Obtener los hijos del padre usando la relación backref
    hijos = current_user.hijos.all()
    
    return render_template('padres/horario_clases.html', hijos=hijos)

# API Routes para Información Académica
@padre_bp.route('/api/estadisticas_estudiante/<int:estudiante_id>')
@login_required
@role_required('Padre')
def api_estadisticas_estudiante(estudiante_id):
    """API para obtener estadísticas generales de un estudiante."""
    try:
        # Verificar que el estudiante pertenece al padre
        estudiante = current_user.hijos.filter_by(id_usuario=estudiante_id).first()
        
        if not estudiante:
            return jsonify({'success': False, 'message': 'Estudiante no encontrado'}), 404
        
        # Calcular promedio general de todas las calificaciones
        from sqlalchemy import func
        calificaciones = Calificacion.query.filter_by(estudiante_id=estudiante_id).all()
        
        if calificaciones:
            suma_notas = sum([cal.nota for cal in calificaciones if cal.nota is not None])
            promedio_general = round(suma_notas / len(calificaciones), 2) if calificaciones else 0
        else:
            promedio_general = 0
        
        # Contar asistencias
        total_asistencias = Asistencia.query.filter_by(
            estudiante_id=estudiante_id,
            estado='presente'
        ).count()
        
        # Contar fallas
        total_fallas = Asistencia.query.filter_by(
            estudiante_id=estudiante_id,
            estado='falta'
        ).count()
        
        # Contar retardos
        total_retardos = Asistencia.query.filter_by(
            estudiante_id=estudiante_id,
            estado='retardo'
        ).count()
        
        estadisticas = {
            'promedio_general': promedio_general,
            'total_asistencias': total_asistencias,
            'total_fallas': total_fallas,
            'total_retardos': total_retardos
        }
        
        return jsonify({
            'success': True,
            'promedio_general': promedio_general,
            'total_asistencias': total_asistencias,
            'total_fallas': total_fallas,
            'total_retardos': total_retardos
        })
        
    except Exception as e:
        current_app.logger.error(f"Error obteniendo estadísticas: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@padre_bp.route('/api/promedios_estudiante/<int:estudiante_id>')
@login_required
@role_required('Padre')
def api_promedios_estudiante(estudiante_id):
    """API para obtener promedios por asignatura de un estudiante."""
    try:
        # Verificar que el estudiante pertenece al padre
        estudiante = current_user.hijos.filter_by(id_usuario=estudiante_id).first()
        
        if not estudiante:
            return jsonify({'success': False, 'message': 'Estudiante no encontrado'}), 404
        
        # Obtener calificaciones agrupadas por asignatura
        from sqlalchemy import func
        
        promedios_query = db.session.query(
            Asignatura.nombre,
            func.avg(Calificacion.nota).label('promedio'),
            func.count(Calificacion.id_calificacion).label('num_calificaciones')
        ).join(
            Calificacion, Calificacion.asignatura_id == Asignatura.id_asignatura
        ).filter(
            Calificacion.estudiante_id == estudiante_id
        ).group_by(
            Asignatura.id_asignatura, Asignatura.nombre
        ).all()
        
        promedios = []
        for asignatura_nombre, promedio, num_calificaciones in promedios_query:
            if promedio is not None:
                promedios.append({
                    'asignatura': asignatura_nombre,
                    'promedio': round(float(promedio), 2),
                    'num_calificaciones': num_calificaciones
                })
        
        return jsonify({
            'success': True,
            'promedios': promedios
        })
        
    except Exception as e:
        current_app.logger.error(f"Error obteniendo promedios: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@padre_bp.route('/api/asistencia_estudiante/<int:estudiante_id>')
@login_required
@role_required('Padre')
def api_asistencia_estudiante(estudiante_id):
    """API para obtener historial de asistencia de un estudiante."""
    try:
        # Verificar que el estudiante pertenece al padre
        estudiante = current_user.hijos.filter_by(id_usuario=estudiante_id).first()
        
        if not estudiante:
            return jsonify({'success': False, 'message': 'Estudiante no encontrado'}), 404
        
        # Obtener registros de asistencia con información de la clase y asignatura
        asistencias = db.session.query(
            Asistencia, Clase, Asignatura
        ).join(
            Clase, Asistencia.claseId == Clase.id_clase
        ).join(
            Asignatura, Clase.asignaturaId == Asignatura.id_asignatura
        ).filter(
            Asistencia.estudianteId == estudiante_id
        ).order_by(
            Asistencia.fecha.desc()
        ).limit(50).all()  # Limitar a las últimas 50 registros
        
        asistencia_list = []
        for asistencia, clase, asignatura in asistencias:
            asistencia_list.append({
                'fecha': asistencia.fecha.strftime('%Y-%m-%d') if asistencia.fecha else 'N/A',
                'asignatura': asignatura.nombre,
                'estado': asistencia.estado,
                'excusa': asistencia.excusa if asistencia.excusa else False
            })
        
        return jsonify({
            'success': True,
            'asistencia': asistencia_list
        })
        
    except Exception as e:
        current_app.logger.error(f"Error obteniendo asistencia: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@padre_bp.route('/api/horario_estudiante/<int:estudiante_id>')
@login_required
@role_required('Padre')
def api_horario_estudiante(estudiante_id):
    """API para obtener horario de clases de un estudiante."""
    try:
        # Verificar que el estudiante pertenece al padre
        estudiante = current_user.hijos.filter_by(id_usuario=estudiante_id).first()
        
        if not estudiante:
            return jsonify({'success': False, 'message': 'Estudiante no encontrado'}), 404
        
        # Obtener la matrícula actual del estudiante
        matricula = Matricula.query.filter_by(estudianteId=estudiante_id).order_by(Matricula.fecha_matricula.desc()).first()
        
        if not matricula:
            return jsonify({
                'success': True,
                'horario': None,
                'message': 'El estudiante no tiene matrícula activa'
            })
        
        curso = matricula.curso
        
        # Obtener horarios compartidos del curso
        horarios_compartidos = db.session.query(
            HorarioCompartido, Asignatura, Usuario, Salon, Sede
        ).join(
            Asignatura, HorarioCompartido.asignatura_id == Asignatura.id_asignatura
        ).join(
            Usuario, HorarioCompartido.profesor_id == Usuario.id_usuario
        ).outerjoin(
            Salon, HorarioCompartido.salon_id == Salon.id_salon
        ).outerjoin(
            Sede, Salon.sede_id == Sede.id_sede
        ).filter(
            HorarioCompartido.curso_id == curso.id_curso
        ).all()
        
        clases = {}
        for horario, asignatura, profesor, salon, sede in horarios_compartidos:
            clave = f"{horario.dia}_{horario.hora_inicio}"
            clases[clave] = {
                'asignatura': asignatura.nombre,
                'profesor': profesor.nombre_completo,
                'salon': salon.nombre if salon else 'N/A',
                'hora_inicio': str(horario.hora_inicio),
                'hora_fin': str(horario.hora_fin) if horario.hora_fin else 'N/A'
            }
        
        horario_data = {
            'curso': curso.nombreCurso,
            'sede': sede.nombre if sede else 'N/A',
            'clases': clases
        }
        
        return jsonify({
            'success': True,
            'horario': horario_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error obteniendo horario: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@padre_bp.route('/api/obtener_hijos')
@login_required
@role_required('Padre')
def api_obtener_hijos():
    """API para obtener los hijos del padre."""
    try:
        from sqlalchemy import text
        
        result = db.session.execute(text("""
            SELECT ep.estudiante_id, u.nombre, u.apellido, u.no_identidad, u.correo, u.estado_cuenta
            FROM estudiante_padre ep 
            JOIN usuarios u ON ep.estudiante_id = u.id_usuario 
            WHERE ep.padre_id = :padre_id
            ORDER BY u.nombre
        """), {'padre_id': current_user.id_usuario})
        
        hijos_data = []
        for row in result:
            hijos_data.append({
                'id': row[0],
                'nombre_completo': f"{row[1]} {row[2]}",
                'numero_documento': row[3],
                'correo': row[4],
                'estado': row[5]
            })
        
        return jsonify({
            'success': True,
            'hijos': hijos_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error obteniendo hijos: {str(e)}'
        }), 500

@padre_bp.route('/api/obtener_profesor_asignatura/<int:asignatura_id>')
@login_required
@role_required('Padre')
def api_obtener_profesor_asignatura(asignatura_id):
    """API para obtener el profesor de una asignatura específica."""
    try:
        from sqlalchemy import text
        
        # Buscar el profesor de la asignatura
        result = db.session.execute(text("""
            SELECT u.id_usuario, u.nombre, u.apellido, u.correo
            FROM usuarios u
            JOIN asignatura_profesor ap ON u.id_usuario = ap.profesor_id
            WHERE ap.asignatura_id = :asignatura_id
        """), {'asignatura_id': asignatura_id}).first()
        
        if result:
            return jsonify({
                'success': True,
                'profesor': {
                    'id': result[0],
                    'nombre_completo': f"{result[1]} {result[2]}",
                    'correo': result[3]
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No se encontró profesor para esta asignatura'
            }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error obteniendo profesor: {str(e)}'
        }), 500

@padre_bp.route('/api/enviar_solicitud', methods=['POST'])
@login_required
@role_required('Padre')
def api_enviar_solicitud():
    """API para enviar una solicitud de consulta de notas."""
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        if not all(key in data for key in ['estudiante_id', 'asignatura_id', 'numero_documento_hijo', 'nombre_completo_hijo', 'justificacion']):
            return jsonify({
                'success': False,
                'message': 'Faltan datos requeridos'
            }), 400
        
        # Verificar que el estudiante sea hijo del padre
        if not verificar_relacion_padre_hijo(current_user.id_usuario, data['estudiante_id']):
            return jsonify({
                'success': False,
                'message': 'No tienes permisos para consultar las notas de este estudiante'
            }), 403
        
        # Obtener el profesor de la asignatura
        from sqlalchemy import text
        profesor_result = db.session.execute(text("""
            SELECT profesor_id FROM asignatura_profesor WHERE asignatura_id = :asignatura_id
        """), {'asignatura_id': data['asignatura_id']}).first()
        
        if not profesor_result:
            return jsonify({
                'success': False,
                'message': 'No se encontró profesor para esta asignatura'
            }), 404
        
        # Crear la solicitud
        solicitud = SolicitudConsulta(
            padre_id=current_user.id_usuario,
            estudiante_id=data['estudiante_id'],
            asignatura_id=data['asignatura_id'],
            profesor_id=profesor_result[0],
            numero_documento_hijo=data['numero_documento_hijo'],
            nombre_completo_hijo=data['nombre_completo_hijo'],
            justificacion=data['justificacion']
        )
        
        db.session.add(solicitud)
        db.session.commit()
        
        # Enviar notificación al profesor
        from services.notification_service import notificar_nueva_solicitud
        notificar_nueva_solicitud(solicitud)
        
        return jsonify({
            'success': True,
            'message': 'Solicitud enviada correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error enviando solicitud: {str(e)}'
        }), 500

@padre_bp.route('/api/obtener_solicitudes')
@login_required
@role_required('Padre')
def api_obtener_solicitudes():
    """API para obtener las solicitudes del padre."""
    try:
        solicitudes = SolicitudConsulta.query.filter_by(padre_id=current_user.id_usuario).order_by(SolicitudConsulta.fecha_solicitud.desc()).all()
        
        solicitudes_data = []
        for solicitud in solicitudes:
            solicitudes_data.append({
                'id': solicitud.id_solicitud,
                'asignatura': solicitud.asignatura.nombre,
                'estudiante': solicitud.nombre_completo_hijo,
                'fecha_solicitud': solicitud.fecha_solicitud.isoformat(),
                'estado': solicitud.estado,
                'justificacion': solicitud.justificacion,
                'respuesta_profesor': solicitud.respuesta_profesor,
                'fecha_respuesta': solicitud.fecha_respuesta.isoformat() if solicitud.fecha_respuesta else None
            })
        
        return jsonify({
            'success': True,
            'solicitudes': solicitudes_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error obteniendo solicitudes: {str(e)}'
        }), 500

@padre_bp.route('/ver_calificaciones_estudiante/<int:estudiante_id>/<int:asignatura_id>')
@login_required
@role_required('Padre')
def ver_calificaciones_estudiante(estudiante_id, asignatura_id):
    """Página para mostrar las calificaciones de un estudiante específico cuando se acepta una solicitud."""
    from controllers.models import Calificacion, CategoriaCalificacion
    
    # Verificar que el estudiante sea hijo del padre
    if not verificar_relacion_padre_hijo(current_user.id_usuario, estudiante_id):
        flash('No tienes permisos para ver las calificaciones de este estudiante', 'error')
        return redirect(url_for('padre.consultar_estudiante'))
    
    estudiante = Usuario.query.get(estudiante_id)
    
    # Obtener calificaciones del estudiante en la asignatura
    calificaciones = Calificacion.query.filter_by(
        estudianteId=estudiante_id,
        asignaturaId=asignatura_id
    ).all()
    
    # Obtener categorías de calificación
    categorias = CategoriaCalificacion.query.all()
    
    # Organizar calificaciones por categoría
    calificaciones_por_categoria = {}
    for categoria in categorias:
        calificaciones_por_categoria[categoria.id_categoria] = {
            'categoria': categoria,
            'calificaciones': []
        }
    
    for calificacion in calificaciones:
        if calificacion.categoriaId in calificaciones_por_categoria:
            calificaciones_por_categoria[calificacion.categoriaId]['calificaciones'].append(calificacion)
    
    # Calcular promedios por categoría
    promedios_por_categoria = {}
    for categoria_id, data in calificaciones_por_categoria.items():
        calificaciones_cat = data['calificaciones']
        if calificaciones_cat:
            valores = [float(cal.valor) for cal in calificaciones_cat if cal.valor is not None]
            if valores:
                promedios_por_categoria[categoria_id] = sum(valores) / len(valores)
            else:
                promedios_por_categoria[categoria_id] = 0
        else:
            promedios_por_categoria[categoria_id] = 0
    
    # Calcular promedio general
    if promedios_por_categoria:
        promedio_general = sum(promedios_por_categoria.values()) / len(promedios_por_categoria)
    else:
        promedio_general = 0
    
    return render_template('padres/calificaciones_estudiante.html',
                         estudiante=estudiante,
                         asignatura=Asignatura.query.get(asignatura_id),
                         calificaciones_por_categoria=calificaciones_por_categoria,
                         promedios_por_categoria=promedios_por_categoria,
                         promedio_general=promedio_general)

# ==================== COMUNICACIONES PARA PADRES ====================

@padre_bp.route('/api/comunicaciones', methods=['GET'])
@login_required
@role_required('Padre')
def api_obtener_comunicaciones():
    """API para obtener comunicaciones del padre."""
    try:
        from controllers.models import Comunicacion
        
        folder = request.args.get('folder', 'inbox')
        
        # Obtener comunicaciones según la carpeta
        if folder == 'inbox':
            # Comunicaciones recibidas (donde el padre es destinatario)
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
            # Comunicaciones enviadas (donde el padre es remitente)
            comunicaciones = db.session.query(Comunicacion).filter(
                Comunicacion.remitente_id == current_user.id_usuario,
                Comunicacion.estado.in_(['inbox', 'sent'])
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
                    'tipo': 'enviada'
                })
                
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

@padre_bp.route('/api/comunicaciones/<int:comunicacion_id>/marcar-leida', methods=['PUT'])
@login_required
@role_required('Padre')
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

@padre_bp.route('/api/comunicaciones', methods=['POST'])
@login_required
@role_required('Padre')
def api_enviar_comunicacion():
    """API para enviar comunicaciones del padre."""
    try:
        from controllers.models import Comunicacion
        
        data = request.get_json()
        to_email = data.get('to')
        asunto = data.get('asunto')
        mensaje = data.get('mensaje')
        
        if not all([to_email, asunto, mensaje]):
            return jsonify({
                'success': False,
                'message': 'Faltan datos requeridos'
            }), 400
        
        # Buscar el destinatario por email
        destinatario = Usuario.query.filter_by(correo=to_email).first()
        if not destinatario:
            return jsonify({
                'success': False,
                'message': 'Usuario destinatario no encontrado'
            }), 404
        
        # Crear la comunicación
        comunicacion = Comunicacion(
            remitente_id=current_user.id_usuario,
            destinatario_id=destinatario.id_usuario,
            asunto=asunto,
            mensaje=mensaje,
            estado='inbox'
        )
        
        db.session.add(comunicacion)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Comunicación enviada correctamente',
            'comunicacion_id': comunicacion.id_comunicacion
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error enviando comunicación: {str(e)}'
        }), 500

@padre_bp.route('/api/comunicaciones/draft', methods=['POST'])
@login_required
@role_required('Padre')
def api_guardar_borrador():
    """API para guardar borradores de comunicaciones."""
    try:
        from controllers.models import Comunicacion
        
        data = request.get_json()
        to_email = data.get('to', '')
        asunto = data.get('asunto', '(Sin asunto)')
        mensaje = data.get('mensaje', '')
        
        # Buscar el destinatario por email si se proporciona
        destinatario_id = None
        if to_email:
            destinatario = Usuario.query.filter_by(correo=to_email).first()
            if destinatario:
                destinatario_id = destinatario.id_usuario
        
        # Crear el borrador
        comunicacion = Comunicacion(
            remitente_id=current_user.id_usuario,
            destinatario_id=destinatario_id,
            asunto=asunto,
            mensaje=mensaje,
            estado='draft'
        )
        
        db.session.add(comunicacion)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Borrador guardado correctamente',
            'comunicacion_id': comunicacion.id_comunicacion
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error guardando borrador: {str(e)}'
        }), 500

@padre_bp.route('/api/comunicaciones/<int:comunicacion_id>', methods=['DELETE'])
@login_required
@role_required('Padre')
def api_eliminar_comunicacion(comunicacion_id):
    """API para eliminar una comunicación."""
    try:
        from controllers.models import Comunicacion
        
        comunicacion = Comunicacion.query.filter(
            (Comunicacion.id_comunicacion == comunicacion_id),
            ((Comunicacion.remitente_id == current_user.id_usuario) |
             (Comunicacion.destinatario_id == current_user.id_usuario))
        ).first()
        
        if not comunicacion:
            return jsonify({
                'success': False,
                'message': 'Comunicación no encontrada'
            }), 404
        
        # Marcar como eliminada en lugar de eliminar físicamente
        comunicacion.estado = 'deleted'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Comunicación eliminada correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error eliminando comunicación: {str(e)}'
        }), 500

@padre_bp.route('/api/usuarios/buscar')
@login_required
@role_required('Padre')
def api_buscar_usuarios():
    """API para buscar usuarios para el autocompletado."""
    try:
        query = request.args.get('q', '')
        
        if len(query) < 2:
            return jsonify([])
        
        # Buscar usuarios que coincidan con el query
        usuarios = Usuario.query.filter(
            (Usuario.nombre.contains(query)) |
            (Usuario.apellido.contains(query)) |
            (Usuario.correo.contains(query))
        ).limit(10).all()
        
        usuarios_data = []
        for usuario in usuarios:
            usuarios_data.append({
                'id': usuario.id_usuario,
                'nombre': usuario.nombre_completo,
                'email': usuario.correo
            })
        
        return jsonify(usuarios_data)
        
    except Exception as e:
        return jsonify({
            'error': f'Error buscando usuarios: {str(e)}'
        }), 500

# ==================== NOTIFICACIONES PARA PADRES ====================

@padre_bp.route('/api/notificaciones')
@login_required
@role_required('Padre')
def api_obtener_notificaciones():
    """API para obtener las notificaciones del padre."""
    try:
        from services.notification_service import obtener_todas_notificaciones
        
        notificaciones = obtener_todas_notificaciones(current_user.id_usuario)
        
        notificaciones_data = []
        for notif in notificaciones:
            notificaciones_data.append({
                'id': notif.id_notificacion,
                'titulo': notif.titulo,
                'mensaje': notif.mensaje,
                'tipo': notif.tipo,
                'link': notif.link,
                'leida': notif.leida,
                'fecha': notif.creada_en.strftime('%Y-%m-%d %H:%M') if notif.creada_en else '',
                'fecha_iso': notif.creada_en.isoformat() if notif.creada_en else ''
            })
        
        return jsonify({
            'success': True,
            'notificaciones': notificaciones_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error obteniendo notificaciones: {str(e)}'
        }), 500

@padre_bp.route('/api/notificaciones/<int:notificacion_id>/marcar-leida', methods=['PUT'])
@login_required
@role_required('Padre')
def api_marcar_notificacion_leida(notificacion_id):
    """API para marcar una notificación como leída."""
    try:
        from services.notification_service import marcar_notificacion_como_leida
        
        if marcar_notificacion_como_leida(notificacion_id, current_user.id_usuario):
            return jsonify({
                'success': True,
                'message': 'Notificación marcada como leída'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Notificación no encontrada'
            }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error marcando notificación: {str(e)}'
        }), 500

@padre_bp.route('/api/notificaciones/contador')
@login_required
@role_required('Padre')
def api_contador_notificaciones():
    """API para obtener el contador de notificaciones no leídas."""
    try:
        from services.notification_service import contar_notificaciones_no_leidas
        
        contador = contar_notificaciones_no_leidas(current_user.id_usuario)
        
        return jsonify({
            'success': True,
            'contador': contador
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error obteniendo contador: {str(e)}'
        }), 500
