from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash
from flask_login import login_required, current_user
from controllers.decorators import role_required, permission_required
from controllers.models import db, Usuario, Rol, Comunicacion, SolicitudConsulta, Asignatura

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
            
            if promedios_hijos:
                promedio_general = sum(promedios_hijos) / len(promedios_hijos)
            
            # Contar clases inscritas (matrículas activas)
            for hijo in hijos:
                matriculas_activas = Matricula.query.filter_by(estudianteId=hijo.id_usuario).all()
                total_clases_inscritas += len(matriculas_activas)
            
            # Contar mensajes de profesores (comunicaciones recibidas)
            mensajes_profesores = Comunicacion.query.filter(
                Comunicacion.destinatario_id == current_user.id_usuario,
                Comunicacion.estado == 'inbox'
            ).count()
            
            # Obtener calificaciones recientes de todos los hijos
            calificaciones_recientes = []
            for hijo in hijos:
                calificaciones = Calificacion.query.filter_by(estudianteId=hijo.id_usuario)\
                    .order_by(Calificacion.fecha_registro.desc()).limit(3).all()
                for cal in calificaciones:
                    if cal.asignatura and cal.valor:
                        calificaciones_recientes.append({
                            'asignatura': cal.asignatura.nombre,
                            'valor': float(cal.valor),
                            'hijo': hijo.nombre_completo,
                            'fecha': cal.fecha_registro.strftime('%Y-%m-%d') if cal.fecha_registro else ''
                        })
            
            # Ordenar por fecha y tomar las 3 más recientes
            calificaciones_recientes = sorted(calificaciones_recientes, 
                                            key=lambda x: x['fecha'], reverse=True)[:3]
            
            # Obtener anuncios importantes (comunicaciones recientes)
            anuncios = Comunicacion.query.filter(
                Comunicacion.destinatario_id == current_user.id_usuario
            ).order_by(Comunicacion.fecha_envio.desc()).limit(2).all()
            
            for anuncio in anuncios:
                anuncios_importantes.append({
                    'titulo': anuncio.asunto,
                    'mensaje': anuncio.mensaje[:100] + '...' if len(anuncio.mensaje) > 100 else anuncio.mensaje,
                    'fecha': anuncio.fecha_envio.strftime('%Y-%m-%d') if anuncio.fecha_envio else '',
                    'remitente': anuncio.remitente.nombre_completo if anuncio.remitente else 'Sistema'
                })
        
        # Pasar datos al template
        return render_template('padres/dashboard.html',
                             hijos=hijos,
                             total_hijos=total_hijos,
                             promedio_general=round(promedio_general, 1),
                             total_clases_inscritas=total_clases_inscritas,
                             mensajes_profesores=mensajes_profesores,
                             calificaciones_recientes=calificaciones_recientes,
                             anuncios_importantes=anuncios_importantes)
                             
    except Exception as e:
        print(f"Error en dashboard del padre: {str(e)}")
        # En caso de error, mostrar dashboard con datos por defecto
        return render_template('padres/dashboard.html',
                             hijos=[],
                             total_hijos=0,
                             promedio_general=0,
                             total_clases_inscritas=0,
                             mensajes_profesores=0,
                             calificaciones_recientes=[],
                             anuncios_importantes=[])

@padre_bp.route('/ver_calificaciones_hijo')
@login_required
@permission_required('ver_calificaciones_hijo')
def ver_calificaciones_hijo():
    """Permite al padre ver las calificaciones de su hijo/a."""
    return render_template('padre/ver_calificaciones_hijo.html')

@padre_bp.route('/ver_horario_hijo')
@login_required
@permission_required('ver_horario_hijo')
def ver_horario_hijo():
    """Muestra el horario de clases del hijo/a."""
    return render_template('padre/ver_horario_hijo.html')

@padre_bp.route('/comunicaciones')
@login_required
def comunicaciones():
    """Página para que el padre vea comunicados de la institución."""
    return render_template('padres/comunicaciones.html')

@padre_bp.route('/api/debug-comunicaciones')
@login_required
def debug_comunicaciones():
    """Ruta de debug para verificar comunicaciones."""
    try:
        # Verificar total de comunicaciones
        total = db.session.query(Comunicacion).count()
        
        # Verificar comunicaciones del usuario
        usuario_comunicaciones = db.session.query(Comunicacion).filter(
            (Comunicacion.remitente_id == current_user.id_usuario) | 
            (Comunicacion.destinatario_id == current_user.id_usuario)
        ).all()
        
        # Verificar todas las comunicaciones
        todas_comunicaciones = db.session.query(Comunicacion).all()
        
        debug_info = {
            'total_comunicaciones': total,
            'usuario_id': current_user.id_usuario,
            'comunicaciones_usuario': len(usuario_comunicaciones),
            'comunicaciones_detalle': [
                {
                    'id': c.id_comunicacion,
                    'remitente_id': c.remitente_id,
                    'destinatario_id': c.destinatario_id,
                    'asunto': c.asunto,
                    'estado': c.estado,
                    'fecha_envio': c.fecha_envio.isoformat() if c.fecha_envio else None,
                    'es_remitente': c.remitente_id == current_user.id_usuario,
                    'es_destinatario': c.destinatario_id == current_user.id_usuario
                } for c in usuario_comunicaciones
            ],
            'todas_comunicaciones': [
                {
                    'id': c.id_comunicacion,
                    'remitente_id': c.remitente_id,
                    'destinatario_id': c.destinatario_id,
                    'asunto': c.asunto,
                    'estado': c.estado,
                    'fecha_envio': c.fecha_envio.isoformat() if c.fecha_envio else None
                } for c in todas_comunicaciones
            ]
        }
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@padre_bp.route('/api/comunicaciones-test', methods=['GET'])
@login_required
def api_obtener_comunicaciones_test():
    """API de prueba para obtener TODAS las comunicaciones del padre sin filtros."""
    try:
        folder = request.args.get('folder', 'inbox')
        print(f"DEBUG TEST: Obteniendo TODAS las comunicaciones para folder: {folder}, usuario: {current_user.id_usuario}")
        
        # Obtener TODAS las comunicaciones del usuario sin filtros de estado
        if folder == 'inbox':
            # Todas las comunicaciones donde el padre es destinatario
            comunicaciones = db.session.query(Comunicacion).filter(
                Comunicacion.destinatario_id == current_user.id_usuario
            ).order_by(Comunicacion.fecha_envio.desc()).limit(50).all()
            
            print(f"DEBUG TEST: Encontradas {len(comunicaciones)} comunicaciones recibidas (SIN filtro de estado)")
            
        elif folder == 'sent':
            # Todas las comunicaciones donde el padre es remitente
            comunicaciones = db.session.query(Comunicacion).filter(
                Comunicacion.remitente_id == current_user.id_usuario
            ).order_by(Comunicacion.fecha_envio.desc()).limit(50).all()
            
            print(f"DEBUG TEST: Encontradas {len(comunicaciones)} comunicaciones enviadas (SIN filtro de estado)")
        else:
            comunicaciones = []
        
        # Convertir a diccionarios
        comunicaciones_data = []
        for com in comunicaciones:
            comunicaciones_data.append({
                'id': com.id_comunicacion,
                'remitente': com.remitente.nombre_completo if com.remitente else 'Desconocido',
                'remitente_nombre': com.remitente.nombre_completo if com.remitente else 'Desconocido',
                'destinatario': com.destinatario.nombre_completo if com.destinatario else 'Desconocido',
                'destinatario_nombre': com.destinatario.nombre_completo if com.destinatario else 'Desconocido',
                'asunto': com.asunto,
                'mensaje': com.mensaje,
                'fecha': com.fecha_envio.strftime('%Y-%m-%d %H:%M') if com.fecha_envio else '',
                'fecha_envio': com.fecha_envio.isoformat() if com.fecha_envio else '',
                'estado': com.estado,
                'tipo': 'recibida' if folder == 'inbox' else 'enviada'
            })
        
        response_data = {
            'success': True,
            'recibidas': comunicaciones_data if folder == 'inbox' else [],
            'enviadas': comunicaciones_data if folder == 'sent' else [],
            'data': comunicaciones_data if folder in ['draft', 'deleted'] else []
        }
        
        print(f"DEBUG TEST: Respuesta API - Folder: {folder}, Datos: {len(comunicaciones_data)} comunicaciones")
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error en API test: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error obteniendo comunicaciones: {str(e)}'
        }), 500

@padre_bp.route('/api/comunicaciones', methods=['GET'])
@login_required
def api_obtener_comunicaciones():
    """API para obtener comunicaciones del padre."""
    try:
        folder = request.args.get('folder', 'inbox')
        print(f"DEBUG: Obteniendo comunicaciones para folder: {folder}, usuario: {current_user.id_usuario}")
        
        # Verificar si existen comunicaciones en la base de datos
        total_comunicaciones = db.session.query(Comunicacion).count()
        print(f"DEBUG: Total de comunicaciones en la BD: {total_comunicaciones}")
        
        # Verificar comunicaciones del usuario actual
        comunicaciones_usuario = db.session.query(Comunicacion).filter(
            (Comunicacion.remitente_id == current_user.id_usuario) | 
            (Comunicacion.destinatario_id == current_user.id_usuario)
        ).count()
        print(f"DEBUG: Comunicaciones del usuario {current_user.id_usuario}: {comunicaciones_usuario}")
        
        # Obtener comunicaciones según la carpeta
        if folder == 'inbox':
            # Comunicaciones recibidas (donde el padre es destinatario)
            print(f"DEBUG: Buscando comunicaciones recibidas para usuario {current_user.id_usuario}")
            
            # Primero intentar con estado 'inbox'
            comunicaciones = db.session.query(Comunicacion).filter(
                Comunicacion.destinatario_id == current_user.id_usuario,
                Comunicacion.estado == 'inbox'
            ).order_by(Comunicacion.fecha_envio.desc()).limit(50).all()
            
            print(f"DEBUG: Encontradas {len(comunicaciones)} comunicaciones recibidas con estado 'inbox'")
            
            # Si no hay comunicaciones con estado 'inbox', buscar todas las recibidas
            if len(comunicaciones) == 0:
                print(f"DEBUG: No hay comunicaciones con estado 'inbox', buscando todas las recibidas...")
                comunicaciones = db.session.query(Comunicacion).filter(
                    Comunicacion.destinatario_id == current_user.id_usuario
                ).order_by(Comunicacion.fecha_envio.desc()).limit(50).all()
                
                print(f"DEBUG: Encontradas {len(comunicaciones)} comunicaciones recibidas (cualquier estado)")
                
                # Mostrar estados de las comunicaciones encontradas
                for com in comunicaciones:
                    print(f"DEBUG: Comunicación ID {com.id_comunicacion}, Estado: {com.estado}, Asunto: {com.asunto}")
            
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
            print(f"DEBUG: Buscando comunicaciones enviadas para usuario {current_user.id_usuario}")
            
            # Primero intentar con estado 'sent'
            comunicaciones = db.session.query(Comunicacion).filter(
                Comunicacion.remitente_id == current_user.id_usuario,
                Comunicacion.estado == 'sent'
            ).order_by(Comunicacion.fecha_envio.desc()).limit(50).all()
            
            print(f"DEBUG: Encontradas {len(comunicaciones)} comunicaciones enviadas con estado 'sent'")
            
            # Si no hay comunicaciones con estado 'sent', buscar todas las enviadas
            if len(comunicaciones) == 0:
                print(f"DEBUG: No hay comunicaciones con estado 'sent', buscando todas las enviadas...")
                comunicaciones = db.session.query(Comunicacion).filter(
                    Comunicacion.remitente_id == current_user.id_usuario
                ).order_by(Comunicacion.fecha_envio.desc()).limit(50).all()
                
                print(f"DEBUG: Encontradas {len(comunicaciones)} comunicaciones enviadas (cualquier estado)")
                
                # Mostrar estados de las comunicaciones encontradas
                for com in comunicaciones:
                    print(f"DEBUG: Comunicación ID {com.id_comunicacion}, Estado: {com.estado}, Asunto: {com.asunto}")
            
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
            # Borradores del padre
            comunicaciones = db.session.query(Comunicacion).filter(
                Comunicacion.remitente_id == current_user.id_usuario,
                Comunicacion.estado == 'draft'
            ).order_by(Comunicacion.fecha_envio.desc()).limit(50).all()
            
            comunicaciones_data = []
            for com in comunicaciones:
                comunicaciones_data.append({
                    'id': com.id_comunicacion,
                    'remitente': com.remitente.nombre_completo if com.remitente else 'Desconocido',
                    'remitente_nombre': com.remitente.nombre_completo if com.remitente else 'Desconocido',
                    'destinatario': com.destinatario.nombre_completo if com.destinatario else 'Desconocido',
                    'destinatario_nombre': com.destinatario.nombre_completo if com.destinatario else 'Desconocido',
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
                Comunicacion.remitente_id == current_user.id_usuario,
                Comunicacion.estado == 'deleted'
            ).order_by(Comunicacion.fecha_envio.desc()).limit(50).all()
            
            comunicaciones_data = []
            for com in comunicaciones:
                comunicaciones_data.append({
                    'id': com.id_comunicacion,
                    'remitente': com.remitente.nombre_completo if com.remitente else 'Desconocido',
                    'remitente_nombre': com.remitente.nombre_completo if com.remitente else 'Desconocido',
                    'destinatario': com.destinatario.nombre_completo if com.destinatario else 'Desconocido',
                    'destinatario_nombre': com.destinatario.nombre_completo if com.destinatario else 'Desconocido',
                    'asunto': com.asunto,
                    'mensaje': com.mensaje,
                    'fecha': com.fecha_envio.strftime('%Y-%m-%d %H:%M') if com.fecha_envio else '',
                    'fecha_envio': com.fecha_envio.isoformat() if com.fecha_envio else '',
                    'estado': com.estado,
                    'tipo': 'eliminada'
                })
        else:
            return jsonify({'success': False, 'message': 'Carpeta no válida'}), 400

        response_data = {
            'success': True,
            'recibidas': comunicaciones_data if folder == 'inbox' else [],
            'enviadas': comunicaciones_data if folder == 'sent' else [],
            'data': comunicaciones_data if folder in ['draft', 'deleted'] else []
        }
        
        print(f"DEBUG: Respuesta API - Folder: {folder}, Datos: {len(comunicaciones_data)} comunicaciones")
        print(f"DEBUG: Respuesta completa: {response_data}")
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error obteniendo comunicaciones: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error obteniendo comunicaciones: {str(e)}'
        }), 500

@padre_bp.route('/api/comunicaciones', methods=['POST'])
@login_required
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

@padre_bp.route('/api/comunicaciones/<int:comunicacion_id>/marcar-leida', methods=['PUT'])
@login_required
def api_marcar_comunicacion_leida(comunicacion_id):
    """API para marcar una comunicación como leída."""
    try:
        from controllers.models import Comunicacion
        
        comunicacion = Comunicacion.query.get(comunicacion_id)
        
        if not comunicacion:
            return jsonify({
                'success': False,
                'message': 'Comunicación no encontrada'
            }), 404
        
        if comunicacion.destinatario_id != current_user.id_usuario:
            return jsonify({
                'success': False,
                'message': 'No tienes permisos para esta comunicación'
            }), 403
        
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

@padre_bp.route('/api/comunicaciones/<int:comunicacion_id>', methods=['DELETE'])
@login_required
def api_eliminar_comunicacion(comunicacion_id):
    """API para eliminar una comunicación."""
    try:
        from controllers.models import Comunicacion
        
        comunicacion = Comunicacion.query.get(comunicacion_id)
        
        if not comunicacion:
            return jsonify({
                'success': False,
                'message': 'Comunicación no encontrada'
            }), 404
        
        # Verificar permisos: solo el remitente puede eliminar
        if comunicacion.remitente_id != current_user.id_usuario:
            return jsonify({
                'success': False,
                'message': 'No tienes permisos para eliminar esta comunicación'
            }), 403
        
        # Marcar como eliminada en lugar de borrar físicamente
        comunicacion.estado = 'deleted'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Comunicación eliminada'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error eliminando comunicación: {str(e)}'
        }), 500

@padre_bp.route('/api/comunicaciones/draft', methods=['POST'])
@login_required
def api_guardar_borrador():
    """API para guardar un borrador de comunicación."""
    try:
        from controllers.models import Comunicacion
        
        data = request.get_json()
        to_email = data.get('to')
        asunto = data.get('asunto')
        mensaje = data.get('mensaje')
        
        if not asunto and not mensaje:
            return jsonify({
                'success': False,
                'message': 'No hay contenido para guardar como borrador'
            }), 400
        
        # Buscar usuario destinatario si se especifica
        destinatario_id = None
        if to_email:
            destinatario = Usuario.query.filter_by(correo=to_email).first()
            if destinatario:
                destinatario_id = destinatario.id_usuario
        
        # Crear borrador
        borrador = Comunicacion(
            remitente_id=current_user.id_usuario,
            destinatario_id=destinatario_id or current_user.id_usuario,
            asunto=asunto or '(Sin asunto)',
            mensaje=mensaje or '',
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

@padre_bp.route('/api/usuarios/buscar')
@login_required
def api_buscar_usuarios():
    """API para buscar usuarios para el autocompletado."""
    try:
        from sqlalchemy import or_
        
        query = request.args.get('q', '').strip()
        
        if len(query) < 2:
            return jsonify([])
        
        # Buscar usuarios por nombre, apellido o correo (solo profesores y administradores)
        rol_profesor = Rol.query.filter_by(nombre='Profesor').first()
        rol_admin = Rol.query.filter_by(nombre='Super Admin').first()
        rol_admin_normal = Rol.query.filter_by(nombre='Admin').first()
        
        roles_ids = []
        if rol_profesor:
            roles_ids.append(rol_profesor.id_rol)
        if rol_admin:
            roles_ids.append(rol_admin.id_rol)
        if rol_admin_normal:
            roles_ids.append(rol_admin_normal.id_rol)
        
        if not roles_ids:
            return jsonify([])
        
        usuarios = Usuario.query.filter(
            or_(
                Usuario.nombre.contains(query),
                Usuario.apellido.contains(query),
                Usuario.correo.contains(query)
            ),
            Usuario.id_rol_fk.in_(roles_ids),
            Usuario.estado_cuenta == 'activa'
        ).limit(10).all()
        
        usuarios_data = []
        for usuario in usuarios:
            usuarios_data.append({
                'id': usuario.id_usuario,
                'nombre': usuario.nombre_completo,
                'email': usuario.correo,
                'correo': usuario.correo,
                'rol': usuario.rol_nombre
            })
        
        return jsonify(usuarios_data)
        
    except Exception as e:
        print(f"Error buscando usuarios: {str(e)}")
        return jsonify([]), 500

@padre_bp.route('/perfil')
@login_required
def perfil():
    """Página para que el padre gestione la información de su perfil."""
    return render_template('padre/perfil.html')

@padre_bp.route('/soporte')
@login_required
def soporte():
    """Página de soporte para el padre."""
    return render_template('padre/soporte.html')

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

@padre_bp.route('/api/obtener_hijos')
@login_required
@role_required('Padre')
def api_obtener_hijos():
    """API para obtener los hijos del padre usando la misma consulta que funciona en debug."""
    try:
        from sqlalchemy import text
        
        # Usar exactamente la misma consulta que funciona en debug
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
        
        # Debug info
        debug_info = {
            'padre_id': current_user.id_usuario,
            'padre_nombre': current_user.nombre_completo,
            'total_hijos': len(hijos_data),
            'hijos': [{'id': h['id'], 'nombre': h['nombre_completo'], 'documento': h['numero_documento'], 'estado': h['estado']} for h in hijos_data]
        }
        
        return jsonify({
            'success': True,
            'hijos': hijos_data,
            'debug': debug_info
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
        asignatura = Asignatura.query.get(asignatura_id)
        
        if not asignatura:
            return jsonify({
                'success': False,
                'message': 'Asignatura no encontrada'
            }), 404
        
        # Obtener profesores de la asignatura
        profesores = asignatura.profesores
        
        profesores_data = []
        for profesor in profesores:
            profesores_data.append({
                'id': profesor.id_usuario,
                'nombre_completo': profesor.nombre_completo,
                'correo': profesor.correo
            })
        
        return jsonify({
            'success': True,
            'profesores': profesores_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error obteniendo profesor: {str(e)}'
        }), 500

@padre_bp.route('/api/enviar_solicitud', methods=['POST'])
@login_required
@role_required('Padre')
def api_enviar_solicitud():
    """API para enviar una solicitud de consulta."""
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        required_fields = ['estudiante_id', 'asignatura_id', 'profesor_id', 'numero_documento_hijo', 'nombre_completo_hijo', 'justificacion']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'El campo {field} es requerido'
                }), 400
        
        # Verificar que el estudiante sea hijo del padre
        if not verificar_relacion_padre_hijo(current_user.id_usuario, data['estudiante_id']):
            return jsonify({
                'success': False,
                'message': 'El estudiante seleccionado no es tu hijo'
            }), 403
        
        # Crear solicitud
        nueva_solicitud = SolicitudConsulta(
            padre_id=current_user.id_usuario,
            estudiante_id=data['estudiante_id'],
            asignatura_id=data['asignatura_id'],
            profesor_id=data['profesor_id'],
            numero_documento_hijo=data['numero_documento_hijo'],
            nombre_completo_hijo=data['nombre_completo_hijo'],
            justificacion=data['justificacion'],
            estado='pendiente'
        )
        
        db.session.add(nueva_solicitud)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Solicitud enviada correctamente',
            'solicitud_id': nueva_solicitud.id_solicitud
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error enviando solicitud: {str(e)}'
        }), 500

@padre_bp.route('/api/solicitudes')
@login_required
@role_required('Padre')
def api_obtener_solicitudes():
    """API para obtener las solicitudes del padre."""
    try:
        solicitudes = SolicitudConsulta.query.filter_by(padre_id=current_user.id_usuario).order_by(SolicitudConsulta.fecha_solicitud.desc()).all()
        
        solicitudes_data = []
        for solicitud in solicitudes:
            solicitudes_data.append(solicitud.to_dict())
        
        return jsonify({
            'success': True,
            'solicitudes': solicitudes_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error obteniendo solicitudes: {str(e)}'
        }), 500

@padre_bp.route('/api/debug-base-datos')
@login_required
@role_required('Padre')
def api_debug_base_datos():
    """API de debug para verificar la base de datos directamente."""
    try:
        from sqlalchemy import text
        
        debug_info = {
            'padre_actual': {
                'id': current_user.id_usuario,
                'nombre': current_user.nombre_completo,
                'documento': current_user.no_identidad,
                'rol': current_user.rol_nombre
            }
        }
        
        # 1. Verificar si existe la tabla estudiante_padre
        try:
            tabla_existe = db.session.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = 'estudiante_padre'
            """)).scalar()
            debug_info['tabla_estudiante_padre_existe'] = tabla_existe > 0
        except Exception as e:
            debug_info['tabla_estudiante_padre_existe'] = False
            debug_info['error_tabla'] = str(e)
        
        # 2. Verificar todas las relaciones en la tabla estudiante_padre
        try:
            todas_relaciones = db.session.execute(text("""
                SELECT ep.padre_id, ep.estudiante_id, ep.fecha_asignacion,
                       up.nombre as padre_nombre, ue.nombre as estudiante_nombre,
                       ue.no_identidad as estudiante_documento
                FROM estudiante_padre ep 
                LEFT JOIN usuarios up ON ep.padre_id = up.id_usuario
                LEFT JOIN usuarios ue ON ep.estudiante_id = ue.id_usuario
                ORDER BY ep.padre_id, ue.nombre
            """)).fetchall()
            
            debug_info['todas_las_relaciones_en_bd'] = [
                {
                    'padre_id': row[0],
                    'estudiante_id': row[1],
                    'fecha_asignacion': row[2].isoformat() if row[2] else None,
                    'padre_nombre': row[3],
                    'estudiante_nombre': row[4],
                    'estudiante_documento': row[5]
                } for row in todas_relaciones
            ]
            debug_info['total_relaciones_en_bd'] = len(todas_relaciones)
        except Exception as e:
            debug_info['error_relaciones'] = str(e)
        
        # 3. Verificar relaciones específicas del padre actual
        try:
            relaciones_padre = db.session.execute(text("""
                SELECT ep.estudiante_id, u.nombre, u.apellido, u.no_identidad, u.estado_cuenta
                FROM estudiante_padre ep 
                JOIN usuarios u ON ep.estudiante_id = u.id_usuario 
                WHERE ep.padre_id = :padre_id
                ORDER BY u.nombre
            """), {'padre_id': current_user.id_usuario}).fetchall()
            
            debug_info['relaciones_del_padre_actual'] = [
                {
                    'estudiante_id': row[0],
                    'nombre': f"{row[1]} {row[2]}",
                    'documento': row[3],
                    'estado': row[4]
                } for row in relaciones_padre
            ]
            debug_info['total_relaciones_del_padre'] = len(relaciones_padre)
        except Exception as e:
            debug_info['error_relaciones_padre'] = str(e)
        
        # 4. Verificar si existe el estudiante 87654321
        try:
            estudiante_87654321 = db.session.execute(text("""
                SELECT id_usuario, nombre, apellido, no_identidad, estado_cuenta, id_rol_fk
                FROM usuarios 
                WHERE no_identidad = '87654321'
            """)).first()
            
            if estudiante_87654321:
                debug_info['estudiante_87654321'] = {
                    'id': estudiante_87654321[0],
                    'nombre': f"{estudiante_87654321[1]} {estudiante_87654321[2]}",
                    'documento': estudiante_87654321[3],
                    'estado': estudiante_87654321[4],
                    'rol_id': estudiante_87654321[5]
                }
            else:
                debug_info['estudiante_87654321'] = None
        except Exception as e:
            debug_info['error_estudiante_87654321'] = str(e)
        
        return jsonify({
            'success': True,
            'debug_info': debug_info
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error en debug: {str(e)}'
        }), 500

@padre_bp.route('/api/debug-estudiante-87654321')
@login_required
@role_required('Padre')
def api_debug_estudiante_especifico():
    """API de debug específica para el estudiante con documento 87654321 usando SQL directo como el admin."""
    try:
        from sqlalchemy import text
        
        # Buscar el estudiante específico
        estudiante = Usuario.query.filter_by(no_identidad='87654321').first()
        
        if not estudiante:
            return jsonify({
                'success': False,
                'message': 'Estudiante con documento 87654321 no encontrado'
            }), 404
        
        # Verificar relación usando SQL directo como el admin
        relacion_result = db.session.execute(text("""
            SELECT ep.padre_id, ep.estudiante_id, ep.fecha_asignacion
            FROM estudiante_padre ep 
            WHERE ep.padre_id = :padre_id AND ep.estudiante_id = :estudiante_id
        """), {
            'padre_id': current_user.id_usuario, 
            'estudiante_id': estudiante.id_usuario
        }).first()
        
        # También verificar todas las relaciones del padre actual
        todas_relaciones = db.session.execute(text("""
            SELECT ep.estudiante_id, u.nombre, u.apellido, u.no_identidad, u.estado_cuenta
            FROM estudiante_padre ep 
            JOIN usuarios u ON ep.estudiante_id = u.id_usuario 
            WHERE ep.padre_id = :padre_id
            ORDER BY u.nombre
        """), {'padre_id': current_user.id_usuario}).fetchall()
        
        debug_info = {
            'estudiante_87654321': {
                'id': estudiante.id_usuario,
                'nombre': estudiante.nombre_completo,
                'documento': estudiante.no_identidad,
                'correo': estudiante.correo,
                'estado_cuenta': estudiante.estado_cuenta,
                'rol': estudiante.rol_nombre
            },
            'padre_actual': {
                'id': current_user.id_usuario,
                'nombre': current_user.nombre_completo,
                'documento': current_user.no_identidad
            },
            'relacion_especifica': {
                'existe': relacion_result is not None,
                'fecha_asignacion': relacion_result[2].isoformat() if relacion_result and relacion_result[2] else None
            },
            'todas_las_relaciones_del_padre': [
                {
                    'estudiante_id': row[0],
                    'nombre': f"{row[1]} {row[2]}",
                    'documento': row[3],
                    'estado': row[4]
                } for row in todas_relaciones
            ],
            'total_relaciones': len(todas_relaciones)
        }
        
        return jsonify({
            'success': True,
            'debug_info': debug_info
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error en debug: {str(e)}'
        }), 500

@padre_bp.route('/api/debug-relaciones')
@login_required
@role_required('Padre')
def api_debug_relaciones():
    """API de debug para verificar las relaciones padre-hijo."""
    try:
        from controllers.models import estudiante_padre
        
        # Obtener todas las relaciones del padre actual
        relaciones = db.session.query(estudiante_padre).filter(
            estudiante_padre.c.padre_id == current_user.id_usuario
        ).all()
        
        # Buscar específicamente el estudiante con documento 87654321
        estudiante_especifico = Usuario.query.filter_by(no_identidad='87654321').first()
        
        debug_info = {
            'padre_id': current_user.id_usuario,
            'padre_nombre': current_user.nombre_completo,
            'total_relaciones': len(relaciones),
            'relaciones': [],
            'estudiante_87654321': {
                'existe': estudiante_especifico is not None,
                'datos': None
            }
        }
        
        if estudiante_especifico:
            debug_info['estudiante_87654321']['datos'] = {
                'id': estudiante_especifico.id_usuario,
                'nombre': estudiante_especifico.nombre_completo,
                'documento': estudiante_especifico.no_identidad,
                'estado': estudiante_especifico.estado_cuenta,
                'rol': estudiante_especifico.rol_nombre
            }
            
            # Verificar si este estudiante está vinculado al padre actual
            relacion_especifica = db.session.query(estudiante_padre).filter(
                estudiante_padre.c.padre_id == current_user.id_usuario,
                estudiante_padre.c.estudiante_id == estudiante_especifico.id_usuario
            ).first()
            
            debug_info['estudiante_87654321']['vinculado'] = relacion_especifica is not None
            if relacion_especifica:
                debug_info['estudiante_87654321']['fecha_vinculacion'] = relacion_especifica.fecha_asignacion.isoformat() if relacion_especifica.fecha_asignacion else None
        
        for relacion in relaciones:
            estudiante = Usuario.query.get(relacion.estudiante_id)
            if estudiante:
                debug_info['relaciones'].append({
                    'estudiante_id': estudiante.id_usuario,
                    'estudiante_nombre': estudiante.nombre_completo,
                    'estudiante_documento': estudiante.no_identidad,
                    'estudiante_estado': estudiante.estado_cuenta,
                    'fecha_asignacion': relacion.fecha_asignacion.isoformat() if relacion.fecha_asignacion else None
                })
        
        return jsonify({
            'success': True,
            'debug_info': debug_info
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error en debug: {str(e)}'
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

@padre_bp.route('/api/crear-relacion-manual', methods=['POST'])
@login_required
@role_required('Padre')
def api_crear_relacion_manual():
    """API para crear manualmente una relación padre-hijo si no existe."""
    try:
        from sqlalchemy import text
        
        data = request.get_json()
        estudiante_documento = data.get('estudiante_documento', '87654321')
        
        # Buscar el estudiante por documento
        estudiante = db.session.execute(text("""
            SELECT id_usuario, nombre, apellido, no_identidad, estado_cuenta
            FROM usuarios 
            WHERE no_identidad = :documento
        """), {'documento': estudiante_documento}).first()
        
        if not estudiante:
            return jsonify({
                'success': False,
                'message': f'Estudiante con documento {estudiante_documento} no encontrado'
            }), 404
        
        # Verificar si ya existe la relación
        relacion_existente = db.session.execute(text("""
            SELECT 1 FROM estudiante_padre 
            WHERE padre_id = :padre_id AND estudiante_id = :estudiante_id
        """), {
            'padre_id': current_user.id_usuario,
            'estudiante_id': estudiante[0]
        }).first()
        
        if relacion_existente:
            return jsonify({
                'success': True,
                'message': 'La relación ya existe',
                'relacion_existente': True
            })
        
        # Crear la relación
        db.session.execute(text("""
            INSERT INTO estudiante_padre (padre_id, estudiante_id, fecha_asignacion)
            VALUES (:padre_id, :estudiante_id, NOW())
        """), {
            'padre_id': current_user.id_usuario,
            'estudiante_id': estudiante[0]
        })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Relación creada exitosamente entre {current_user.nombre_completo} y {estudiante[1]} {estudiante[2]}',
            'relacion_creada': True,
            'estudiante': {
                'id': estudiante[0],
                'nombre': f"{estudiante[1]} {estudiante[2]}",
                'documento': estudiante[3],
                'estado': estudiante[4]
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error creando relación: {str(e)}'
        }), 500