# routes/estudiantes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from controllers.decorators import role_required, permission_required
from datetime import datetime, timedelta, time, date
from controllers.models import db, Usuario, Comunicacion,Evento ,Candidato, HorarioVotacion,Voto

# Se asume que tienes un nuevo Blueprint para las rutas de estudiante.
# Si no, puedes añadir esta ruta al Blueprint de 'admin' o crear uno nuevo llamado 'estudiante_bp'.
estudiante_bp = Blueprint('estudiante', __name__, url_prefix='/estudiante')

@estudiante_bp.route('/dashboard')
@login_required
def estudiante_panel():
    """
    Ruta para el dashboard del estudiante.
    Redirige a la página principal del panel de estudiante.
    """
    # Verifica si el usuario tiene rol 'Estudiante'
    if current_user.rol and current_user.rol.nombre.lower() == 'estudiante':
        return render_template('estudiantes/dashboard.html')
    else:
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('auth.login')) 

    
# --- Ejemplo de ruta para ver calificaciones ---
@estudiante_bp.route('/calificaciones')
@login_required
@permission_required('ver_calificaciones')
def ver_calificaciones():
    """
    Ruta para que el estudiante vea sus calificaciones.
    """
    # Aquí iría la lógica para obtener las calificaciones del estudiante.
    # Por ejemplo: calificaciones = Calificacion.query.filter_by(id_estudiante=current_user.id).all()
    # return render_template('estudiante/calificaciones.html', calificaciones=calificaciones)
    return render_template('estudiante/calificaciones.html')

# --- Ejemplo de ruta para ver horario ---
@estudiante_bp.route('/horario')
@login_required
@permission_required('ver_horario')
def ver_horario():
    """
    Ruta para que el estudiante vea su horario.
    """
    # Aquí iría la lógica para obtener el horario del estudiante.
    # Por ejemplo: horario = Horario.query.filter_by(id_estudiante=current_user.id).all()
    # return render_template('estudiante/horario.html', horario=horario)
    return render_template('estudiante/horario.html')



# =======================
# Sistema de votación
# =======================

# 📌 Estado de la votación
@estudiante_bp.route("/estado/<int:usuario_id>")
@login_required
def estado(usuario_id):
    try:
        horario = HorarioVotacion.query.first()
        if not horario:
            return jsonify({
                "votacion_abierta": False,
                "error": "No hay horario definido",
                "inicio": None,
                "fin": None,
                "ya_voto": False
            })

        hoy = datetime.now().date()
        inicio = datetime.combine(hoy, horario.inicio)
        fin = datetime.combine(hoy, horario.fin)
        ahora = datetime.now()

        if inicio > fin:  # horario cruza medianoche
            votacion_abierta = (ahora >= inicio or ahora <= fin)
        else:
            votacion_abierta = (inicio <= ahora <= fin)

        ya_voto = Voto.query.filter_by(estudiante_id=usuario_id).first() is not None

        return jsonify({
            "votacion_abierta": votacion_abierta,
            "inicio": str(horario.inicio),
            "fin": str(horario.fin),
            "ya_voto": ya_voto
        })

    except Exception as e:
        return jsonify({"error": str(e), "votacion_abierta": False}), 500


# 📌 Obtener candidatos por categoría
# 📌 Obtener candidatos por categoría
@estudiante_bp.route("/candidatos", methods=["GET"])
@login_required
def listar_candidatos():
    candidatos = Candidato.query.all()
    data = {}

    for c in candidatos:
        if c.categoria not in data:
            data[c.categoria] = []

        # Solo enviamos el nombre del archivo en "foto"
        data[c.categoria].append({
            "id": c.id_candidato,  # ✅ Campo corregido
            "nombre": c.nombre,
            "tarjeton": c.tarjeton,
            "propuesta": c.propuesta,
            "categoria": c.categoria,
            "foto": c.foto.split('/')[-1] if c.foto else None
        })

    return jsonify(data), 200



# 📌 Registrar voto
# 📌 Registrar voto
@estudiante_bp.route("/votar", methods=["POST"])
@login_required
def votar():
    data = request.get_json()
    estudiante_id = data.get("estudiante_id")
    votos = data.get("votos")  # dict {categoria: candidato_id}

    # --- Validar horario ---
    horario = HorarioVotacion.query.order_by(HorarioVotacion.id_horario_votacion.desc()).first()
    if horario:
        ahora = datetime.now().time()
        if horario.inicio <= horario.fin:
            if not (horario.inicio <= ahora <= horario.fin):
                return jsonify({"error": "⏰ La votación no está abierta"}), 403
        else:
            if not (ahora >= horario.inicio or ahora <= horario.fin):
                return jsonify({"error": "⏰ La votación no está abierta"}), 403

    try:
        for categoria, candidato_id in votos.items():
            if candidato_id == "blanco":
                continue  # No se guarda nada en la tabla

            # 🔍 Verificar si ya votó en esta categoría
            voto_existente = (
                Voto.query.join(Candidato, Voto.candidato_id == Candidato.id_candidato)
                .filter(
                    Voto.estudiante_id == estudiante_id,
                    Candidato.categoria == categoria
                )
                .first()
            )

            if voto_existente:
                return jsonify({"error": f"⚠️ Ya votaste en la categoría {categoria}"}), 400

            # 🗳️ Registrar el nuevo voto
            nuevo_voto = Voto(
                estudiante_id=estudiante_id,
                candidato_id=int(candidato_id)
            )
            db.session.add(nuevo_voto)

            # 🧮 Sumar 1 voto al candidato
            candidato = Candidato.query.filter_by(id_candidato=int(candidato_id)).first()
            if candidato:
                if candidato.votos is None:
                    candidato.votos = 0
                candidato.votos += 1

        db.session.commit()
        return jsonify({"mensaje": "✅ Voto registrado correctamente"}), 201

    except Exception as e:
        db.session.rollback()
        print("❌ Error al registrar voto:", e)
        return jsonify({"error": str(e)}), 400



# 📌 Vista principal de elecciones (HTML)
@estudiante_bp.route('/eleccion')
@login_required
def eleccion_electoral():
    return render_template(
        "estudiantes/votar.html",
        current_user_id=current_user.id_usuario
    )




@estudiante_bp.route('/comunicaciones')
@login_required
def comunicaciones():
    return render_template('estudiantes/comunicaciones.html')

@estudiante_bp.route('/api/comunicaciones')
@login_required
def get_comunicaciones():
    """API para obtener comunicaciones del estudiante."""
    try:
        folder = request.args.get('folder', 'inbox')
        
        # Obtener comunicaciones según la carpeta
        if folder == 'inbox':
            # Comunicaciones recibidas (donde el estudiante es destinatario)
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
            # Comunicaciones enviadas (donde el estudiante es remitente)
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
# Los estudiantes no pueden enviar comunicaciones, solo recibirlas

@estudiante_bp.route('/api/comunicaciones/draft', methods=['POST'])
@login_required
def save_draft():
    try:
        data = request.json
        user_id = current_user.id_usuario
        
        destinatario = None
        if data.get('to'):
            destinatario = Usuario.query.filter_by(correo=data.get('to')).first()
        
        nueva_comunicacion = Comunicacion(
            remitente_id=user_id,
            destinatario_id=destinatario.id_usuario if destinatario else user_id,
            asunto=data.get('asunto', '(Sin asunto)'),
            mensaje=data.get('mensaje', ''),
            estado='draft'
        )
        
        db.session.add(nueva_comunicacion)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Borrador guardado',
            'id': nueva_comunicacion.id_comunicacion
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@estudiante_bp.route('/api/comunicaciones/<int:comunicacion_id>', methods=['GET'])
@login_required
def get_comunicacion(comunicacion_id):
    """API para obtener una comunicación específica."""
    try:
        comunicacion = Comunicacion.query.get_or_404(comunicacion_id)
        
        # Verificar que el usuario sea remitente o destinatario
        if (comunicacion.remitente_id != current_user.id_usuario and 
            comunicacion.destinatario_id != current_user.id_usuario):
            return jsonify({'error': 'No autorizado'}), 403
        
        # Marcar como leída si es el destinatario
        if comunicacion.destinatario_id == current_user.id_usuario and comunicacion.estado == 'inbox':
            comunicacion.estado = 'read'
            db.session.commit()
        
        return jsonify({
            'id_comunicacion': comunicacion.id_comunicacion,
            'remitente_nombre': comunicacion.remitente.nombre_completo if comunicacion.remitente else 'Desconocido',
            'destinatario_nombre': comunicacion.destinatario.nombre_completo if comunicacion.destinatario else 'Desconocido',
            'asunto': comunicacion.asunto,
            'mensaje': comunicacion.mensaje,
            'fecha_envio': comunicacion.fecha_envio.isoformat() if comunicacion.fecha_envio else '',
            'estado': comunicacion.estado
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@estudiante_bp.route('/api/comunicaciones/<int:comunicacion_id>', methods=['PUT'])
@login_required
def update_comunicacion(comunicacion_id):
    try:
        data = request.json
        comunicacion = Comunicacion.query.get_or_404(comunicacion_id)
        
        if comunicacion.remitente_id != current_user.id_usuario and comunicacion.destinatario_id != current_user.id_usuario:
            return jsonify({'error': 'No autorizado'}), 403
        
        if 'estado' in data:
            if comunicacion.remitente_id == current_user.id_usuario:
                comunicacion.estado = data['estado']
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Comunicación actualizada'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@estudiante_bp.route('/api/comunicaciones/<int:comunicacion_id>', methods=['DELETE'])
@login_required
def delete_comunicacion(comunicacion_id):
    try:
        comunicacion = Comunicacion.query.get_or_404(comunicacion_id)
        
        # Verificar que el usuario sea remitente o destinatario
        if comunicacion.remitente_id != current_user.id_usuario and comunicacion.destinatario_id != current_user.id_usuario:
            return jsonify({'error': 'No autorizado'}), 403
        
        # Si ya está en papelera, eliminar permanentemente
        if comunicacion.estado == 'deleted':
            db.session.delete(comunicacion)
            message = 'Comunicación eliminada permanentemente'
        else:
            # Marcar como eliminada en lugar de eliminar físicamente
            comunicacion.estado = 'deleted'
            message = 'Comunicación movida a papelera'
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': message})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@estudiante_bp.route('/api/comunicaciones/<int:comunicacion_id>/restore', methods=['PUT'])
@login_required
def restore_comunicacion(comunicacion_id):
    try:
        comunicacion = Comunicacion.query.get_or_404(comunicacion_id)
        
        # Verificar que el usuario sea remitente o destinatario
        if comunicacion.remitente_id != current_user.id_usuario and comunicacion.destinatario_id != current_user.id_usuario:
            return jsonify({'error': 'No autorizado'}), 403
        
        # Restaurar el email cambiando su estado a 'inbox'
        comunicacion.estado = 'inbox'
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Comunicación restaurada'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@estudiante_bp.route('/api/usuarios/buscar')
@login_required
def buscar_usuarios():
    query = request.args.get('q', '')
    if not query or len(query) < 2:
        return jsonify([])
    
    try:
        print(f"DEBUG: Buscando usuarios con query: {query}")
        
        # Buscar usuarios por correo, nombre o apellido
        usuarios = Usuario.query.filter(
            (Usuario.correo.ilike(f'%{query}%')) |
            (Usuario.nombre.ilike(f'%{query}%')) |
            (Usuario.apellido.ilike(f'%{query}%'))
        ).filter(Usuario.estado_cuenta == 'activa').limit(10).all()
        
        print(f"DEBUG: Encontrados {len(usuarios)} usuarios")
        
        # Construir resultados de forma segura
        resultados = []
        for usuario in usuarios:
            user_data = {
                'id': usuario.id_usuario,
                'nombre': f"{usuario.nombre} {usuario.apellido}",
                'email': usuario.correo
            }
            resultados.append(user_data)
            print(f"DEBUG Usuario: {user_data}")
        
        return jsonify(resultados)
        
    except Exception as e:
        print(f"ERROR en buscar_usuarios: {str(e)}")
        return jsonify({'error': str(e)}), 500


    # 📌 Vista: calendario de eventos (solo ver)
@estudiante_bp.route("/eventos", methods=["GET"])
@login_required
def ver_eventos():
    return render_template("estudiantes/calendario/index.html")

# 📌 API: listar eventos SOLO del rol del estudiante
@estudiante_bp.route("/api/eventos", methods=["GET"])
@login_required
def api_eventos_estudiante():
    try:
        # Filtrar por rol del usuario logueado
        eventos = Evento.query.filter_by(rol_destino="Estudiante").all()

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