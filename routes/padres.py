from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from controllers.decorators import role_required, permission_required
from controllers.models import db, Usuario, Rol, Comunicacion

padre_bp = Blueprint('padre', __name__, url_prefix='/padre')

@padre_bp.route('/dashboard')
@login_required
@role_required('Padre')
def dashboard():
    """Muestra el panel principal del padre con un resumen del progreso del hijo/a."""
    return render_template('padres/dashboard.html')

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