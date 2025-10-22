# routes/estudiantes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from controllers.decorators import role_required, permission_required
from datetime import datetime, timedelta, time, date
from controllers.models import db, Usuario, Comunicacion,Evento ,Candidato, HorarioVotacion,Voto, Equipo

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
            "id": c.id,
            "nombre": c.nombre,
            "tarjeton": c.tarjeton,
            "propuesta": c.propuesta,
            "categoria": c.categoria,
            "foto": c.foto.split('/')[-1] if c.foto else None
        })

    return jsonify(data), 200


# 📌 Registrar voto
@estudiante_bp.route("/votar", methods=["POST"])
@login_required
def votar():
    data = request.get_json()
    estudiante_id = data.get("estudiante_id")
    votos = data.get("votos")  # dict {categoria: candidato_id}

    # --- Validar horario ---
    horario = HorarioVotacion.query.order_by(HorarioVotacion.id.desc()).first()
    if horario:
        ahora = datetime.now().time()
        if horario.inicio <= horario.fin:
            if not (horario.inicio <= ahora <= horario.fin):
                return jsonify({"error": "La votación no está abierta"}), 403
        else:
            if not (ahora >= horario.inicio or ahora <= horario.fin):
                return jsonify({"error": "La votación no está abierta"}), 403

    try:
        for categoria, candidato_id in votos.items():
            if candidato_id == "blanco":
                continue  # No se guarda nada en la tabla
               
            # Revisar si ya votó en esta categoría
            voto_existente = Voto.query.join(Candidato).filter(
                Voto.estudiante_id == estudiante_id,
                Candidato.categoria == categoria
            ).first()
            if voto_existente:
                return jsonify({"error": f"Ya votaste en {categoria}"}), 400

            # Registrar voto
            nuevo_voto = Voto(
                estudiante_id=estudiante_id,
                candidato_id=int(candidato_id)
            )
            db.session.add(nuevo_voto)

            # Sumar +1 al candidato
            candidato = Candidato.query.get(int(candidato_id))
            if candidato:
                if candidato.votos is None:
                    candidato.votos = 0
                candidato.votos += 1

        db.session.commit()
        return jsonify({"mensaje": "Voto registrado correctamente ✅"}), 201

    except Exception as e:
        db.session.rollback()
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
    return render_template('estudiantes/comunicaciones/index.html')

@estudiante_bp.route('/api/comunicaciones')
@login_required
def get_comunicaciones():
    folder = request.args.get('folder', 'inbox')
    user_id = current_user.id_usuario
    
    try:
        print(f"DEBUG: Obteniendo comunicaciones para usuario {user_id}, folder: {folder}")
        
        if folder == 'inbox':
            # Comunicaciones donde el usuario es el DESTINATARIO
            comunicaciones = Comunicacion.query.filter_by(
                destinatario_id=user_id, 
                estado='inbox'
            ).order_by(Comunicacion.fecha_envio.desc()).all()
            print(f"DEBUG: Encontradas {len(comunicaciones)} comunicaciones en inbox")
            
        elif folder == 'sent':
            # Comunicaciones donde el usuario es el REMITENTE
            comunicaciones = Comunicacion.query.filter_by(
                remitente_id=user_id, 
                estado='sent'
            ).order_by(Comunicacion.fecha_envio.desc()).all()
            print(f"DEBUG: Encontradas {len(comunicaciones)} comunicaciones en sent")
            
        elif folder == 'draft':
            # Borradores del usuario (como remitente)
            comunicaciones = Comunicacion.query.filter_by(
                remitente_id=user_id, 
                estado='draft'
            ).order_by(Comunicacion.fecha_envio.desc()).all()
            print(f"DEBUG: Encontradas {len(comunicaciones)} comunicaciones en draft")
            
        elif folder == 'deleted':
            # Comunicaciones eliminadas (solo las que el usuario envió)
            comunicaciones = Comunicacion.query.filter_by(
                remitente_id=user_id, 
                estado='deleted'
            ).order_by(Comunicacion.fecha_envio.desc()).all()
            print(f"DEBUG: Encontradas {len(comunicaciones)} comunicaciones en deleted")
            
        else:
            return jsonify([])
        
        # Debug: Mostrar detalles de cada comunicación
        for com in comunicaciones:
            print(f"DEBUG Comunicación: ID={com.id_comunicacion}, Remitente={com.remitente_id}, Destinatario={com.destinatario_id}, Estado={com.estado}")
        
        return jsonify([com.to_dict() for com in comunicaciones])
        
    except Exception as e:
        print(f"DEBUG: Error al obtener comunicaciones: {str(e)}")
        return jsonify({'error': str(e)}), 500

@estudiante_bp.route('/api/comunicaciones', methods=['POST'])
@login_required
def send_comunicacion():
    try:
        data = request.json
        user_id = current_user.id_usuario
        
        print(f"DEBUG: Enviando mensaje de {user_id} a {data.get('to')}")
        
        if not data.get('to') or not data.get('asunto') or not data.get('mensaje'):
            return jsonify({'error': 'Faltan campos requeridos'}), 400
        
        # Buscar usuario destinatario por correo
        destinatario = Usuario.query.filter_by(correo=data.get('to')).first()
        
        if not destinatario:
            print(f"DEBUG: Destinatario no encontrado con correo: {data.get('to')}")
            return jsonify({'error': 'Usuario destinatario no encontrado'}), 404
        
        print(f"DEBUG: Destinatario encontrado - ID: {destinatario.id_usuario}, Nombre: {destinatario.nombre_completo}")
        
        # Crear comunicación
        nueva_comunicacion = Comunicacion(
            remitente_id=user_id,
            destinatario_id=destinatario.id_usuario,
            asunto=data.get('asunto'),
            mensaje=data.get('mensaje'),
            estado='sent'
        )
        
        db.session.add(nueva_comunicacion)
        db.session.commit()
        
        print(f"DEBUG: Comunicación creada exitosamente - ID: {nueva_comunicacion.id_comunicacion}")
        
        return jsonify({
            'success': True, 
            'message': 'Mensaje enviado correctamente',
            'id': nueva_comunicacion.id_comunicacion
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG: Error al enviar comunicación: {str(e)}")
        return jsonify({'error': str(e)}), 500

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

@estudiante_bp.route('/api/comunicaciones/<int:comunicacion_id>')
@login_required
def get_comunicacion(comunicacion_id):
    try:
        comunicacion = Comunicacion.query.get_or_404(comunicacion_id)
        
        if comunicacion.remitente_id != current_user.id_usuario and comunicacion.destinatario_id != current_user.id_usuario:
            return jsonify({'error': 'No autorizado'}), 403
            
        return jsonify(comunicacion.to_dict())
        
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
        
        if comunicacion.remitente_id != current_user.id_usuario:
            return jsonify({'error': 'No autorizado'}), 403
        
        comunicacion.estado = 'deleted'
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Comunicación eliminada'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@estudiante_bp.route('/api/comunicaciones/<int:comunicacion_id>/restore', methods=['PUT'])
@login_required
def restore_comunicacion(comunicacion_id):
    try:
        comunicacion = Comunicacion.query.get_or_404(comunicacion_id)
        
        if comunicacion.remitente_id != current_user.id_usuario:
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

# Ruta para crear automáticamente comunicaciones de prueba
@estudiante_bp.route('/api/comunicaciones/crear-prueba')
@login_required
def crear_comunicacion_prueba():
    try:
        # Buscar otro usuario para enviarle un mensaje de prueba
        otros_usuarios = Usuario.query.filter(Usuario.id_usuario != current_user.id_usuario).limit(2).all()
        
        if not otros_usuarios:
            return jsonify({'error': 'No hay otros usuarios en el sistema'}), 400
        
        destinatario = otros_usuarios[0]
        
        # Crear comunicación de prueba
        comunicacion_prueba = Comunicacion(
            remitente_id=current_user.id_usuario,
            destinatario_id=destinatario.id_usuario,
            asunto='Mensaje de prueba',
            mensaje='Este es un mensaje de prueba para verificar que el sistema de comunicaciones funciona correctamente.',
            estado='sent'
        )
        
        db.session.add(comunicacion_prueba)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Mensaje de prueba enviado a {destinatario.nombre_completo}',
            'comunicacion_id': comunicacion_prueba.id_comunicacion
        })
        
    except Exception as e:
        db.session.rollback()
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

@estudiante_bp.route('/mi-equipo')
@login_required
@permission_required('ver_equipos')
def mi_equipo():
    """
    Vista HTML para que el estudiante vea su equipo asignado
    """
    return render_template('estudiantes/mi_equipo.html')


@estudiante_bp.route('/api/mi-equipo', methods=['GET'])
@login_required
def api_mi_equipo():
    """
    API para obtener el equipo asignado al estudiante logueado
    Busca en la tabla Equipo donde asignado_a coincida con el nombre del estudiante
    """
    try:
        user_id = current_user.id_usuario
        usuario = Usuario.query.get(user_id)
        
        if not usuario:
            return jsonify({
                'success': False,
                'error': 'Usuario no encontrado'
            }), 404
        
        # Buscar equipo asignado al estudiante por nombre completo
        nombre_completo = usuario.nombre_completo
        equipo = Equipo.query.filter_by(asignado_a=nombre_completo).first()
        
        if not equipo:
            # También intentar buscar solo por nombre o apellido
            equipo = Equipo.query.filter(
                (Equipo.asignado_a.ilike(f'%{usuario.nombre}%')) |
                (Equipo.asignado_a.ilike(f'%{usuario.apellido}%'))
            ).first()
        
        if equipo:
            # El estudiante tiene un equipo asignado
            equipo_data = equipo.to_dict()
            
            # Agregar información adicional si está disponible
            equipo_data['procesador'] = equipo_data.get('sistema_operativo', 'N/A')  # Puedes ajustar esto
            equipo_data['ultima_revision'] = None  # Conectar con tabla de mantenimiento si existe
            equipo_data['proximo_mantenimiento'] = None  # Conectar con tabla de mantenimiento si existe
            
            return jsonify({
                'success': True,
                'equipo': equipo_data
            }), 200
        else:
            # El estudiante no tiene equipo asignado
            return jsonify({
                'success': False,
                'message': 'No tienes equipo asignado actualmente'
            }), 200
            
    except Exception as e:
        print(f"ERROR en api_mi_equipo: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500