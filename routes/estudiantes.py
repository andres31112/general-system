# routes/estudiantes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from controllers.decorators import role_required, permission_required
from datetime import datetime, timedelta, time, date
from controllers.models import (
    db, Usuario, Comunicacion, Evento, Candidato, HorarioVotacion, Voto,
    Calificacion, Asistencia, CicloAcademico, PeriodoAcademico, Matricula, Curso
)
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

# 📌 Estado de la votación - VERSIÓN CORREGIDA
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

        # Usar el campo voto_registrado
        estudiante = Usuario.query.get(usuario_id)
        ya_voto = estudiante.voto_registrado if estudiante else False

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



# 📌 Registrar voto - CON MÁS LOGGING
@estudiante_bp.route("/votar", methods=["POST"])
@login_required
def votar():
    try:
        print("🎯 ===== VOTACIÓN INICIADA =====")
        
        # Verificar método y datos
        print(f"📨 Método: {request.method}")
        print(f"📦 Content-Type: {request.content_type}")
        print(f"📊 Datos crudos: {request.get_data()}")
        
        data = request.get_json()
        print(f"📋 JSON recibido: {data}")
        
        if not data:
            return jsonify({"error": "No se recibieron datos"}), 400
            
        estudiante_id = data.get("estudiante_id")
        votos = data.get("votos", {})
        
        print(f"👤 Estudiante ID: {estudiante_id}")
        print(f"🗳️ Votos recibidos: {votos}")

        # Validar estudiante
        estudiante = Usuario.query.get(estudiante_id)
        if not estudiante:
            print("❌ Estudiante no encontrado en BD")
            return jsonify({"error": "Estudiante no encontrado"}), 400

        print(f"👤 Estudiante encontrado: {estudiante.nombre}")

        # Verificar si ya votó
        if estudiante.voto_registrado:
            print("❌ ESTUDIANTE YA VOTÓ - voto_registrado=True")
            return jsonify({"error": "Ya has votado anteriormente"}), 400

        print("✅ Estudiante puede votar - voto_registrado=False")

        # Procesar cada voto
        votos_registrados = 0
        for categoria, candidato_id in votos.items():
            print(f"📝 Procesando voto: {categoria} -> {candidato_id}")
            
            if candidato_id == "blanco" or not candidato_id:
                print(f"⚪ Voto en blanco para {categoria}")
                continue

            # Verificar candidato
            candidato = Candidato.query.get(int(candidato_id))
            if not candidato:
                print(f"❌ Candidato {candidato_id} no encontrado")
                continue

            # Registrar voto
            nuevo_voto = Voto(
                estudiante_id=estudiante_id,
                candidato_id=int(candidato_id)
            )
            db.session.add(nuevo_voto)

            # Incrementar contador
            candidato.votos += 1
            votos_registrados += 1
            print(f"✅ VOTO REGISTRADO: {candidato.nombre} ahora tiene {candidato.votos} votos")

        if votos_registrados == 0:
            print("⚠️ No se registraron votos válidos")
            return jsonify({"error": "No se seleccionaron candidatos válidos"}), 400

        # Marcar estudiante
        estudiante.voto_registrado = True
        print(f"🎓 ESTUDIANTE MARCADO: {estudiante.nombre} -> voto_registrado=True")

        # Commit final
        db.session.commit()
        print("💾 COMMIT EXITOSO - Todos los cambios guardados")
        print("✅ ===== VOTACIÓN FINALIZADA CON ÉXITO =====")
        
        return jsonify({"mensaje": "✅ Voto registrado correctamente"}), 201

    except Exception as e:
        db.session.rollback()
        print(f"❌ ===== ERROR EN VOTACIÓN =====")
        print(f"❌ Tipo de error: {type(e).__name__}")
        print(f"❌ Mensaje: {str(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Error interno del servidor"}), 500


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


# ============================================================================
# RUTAS API - PERIODOS ACADÉMICOS
# ============================================================================

@estudiante_bp.route('/api/periodo-activo', methods=['GET'])
@login_required
def api_periodo_activo():
    """API para obtener el periodo académico activo."""
    try:
        from services.periodo_service import obtener_periodo_activo
        
        periodo = obtener_periodo_activo()
        if periodo:
            return jsonify({
                'success': True,
                'periodo': periodo.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No hay periodo activo'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error obteniendo periodo activo: {str(e)}'
        }), 500

@estudiante_bp.route('/api/periodos', methods=['GET'])
@login_required
def api_periodos():
    """API para obtener todos los periodos del ciclo activo."""
    try:
        from services.periodo_service import obtener_ciclo_activo, obtener_periodos_ciclo
        
        ciclo = obtener_ciclo_activo()
        if not ciclo:
            return jsonify({
                'success': False,
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
            'message': f'Error obteniendo periodos: {str(e)}'
        }), 500

@estudiante_bp.route('/api/mis-calificaciones', methods=['GET'])
@login_required
def api_mis_calificaciones():
    """API para obtener las calificaciones del estudiante, opcionalmente filtradas por periodo."""
    try:
        periodo_id = request.args.get('periodo_id', type=int)
        
        # Construir query base
        query = Calificacion.query.filter_by(estudianteId=current_user.id_usuario)
        
        # Filtrar por periodo si se especifica
        if periodo_id:
            query = query.filter_by(periodo_academico_id=periodo_id)
        
        calificaciones = query.order_by(Calificacion.fecha_registro.desc()).all()
        
        calificaciones_data = []
        for cal in calificaciones:
            cal_dict = {
                'id': cal.id_calificacion,
                'asignatura': cal.asignatura.nombre_asignatura if cal.asignatura else 'N/A',
                'valor': float(cal.valor) if cal.valor else None,
                'fecha': cal.fecha_registro.strftime('%Y-%m-%d') if cal.fecha_registro else None,
                'observaciones': cal.observaciones,
                'periodo_id': cal.periodo_academico_id
            }
            calificaciones_data.append(cal_dict)
        
        return jsonify({
            'success': True,
            'calificaciones': calificaciones_data
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error obteniendo calificaciones: {str(e)}'
        }), 500

@estudiante_bp.route('/api/mis-asistencias', methods=['GET'])
@login_required
def api_mis_asistencias():
    """API para obtener las asistencias del estudiante, opcionalmente filtradas por periodo."""
    try:
        periodo_id = request.args.get('periodo_id', type=int)
        
        # Construir query base
        query = Asistencia.query.filter_by(estudianteId=current_user.id_usuario)
        
        # Filtrar por periodo si se especifica
        if periodo_id:
            query = query.filter_by(periodo_academico_id=periodo_id)
        
        asistencias = query.order_by(Asistencia.fecha.desc()).all()
        
        # Calcular estadísticas
        total = len(asistencias)
        presentes = sum(1 for a in asistencias if a.estado == 'Presente')
        ausentes = sum(1 for a in asistencias if a.estado == 'Ausente')
        tardes = sum(1 for a in asistencias if a.estado == 'Tarde')
        porcentaje = round((presentes / total * 100) if total > 0 else 0, 2)
        
        asistencias_data = []
        for asist in asistencias:
            asist_dict = {
                'id': asist.id_asistencia,
                'fecha': asist.fecha.strftime('%Y-%m-%d') if asist.fecha else None,
                'estado': asist.estado,
                'clase_id': asist.claseId,
                'periodo_id': asist.periodo_academico_id
            }
            asistencias_data.append(asist_dict)
        
        return jsonify({
            'success': True,
            'asistencias': asistencias_data,
            'estadisticas': {
                'total': total,
                'presentes': presentes,
                'ausentes': ausentes,
                'tardes': tardes,
                'porcentaje_asistencia': porcentaje
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error obteniendo asistencias: {str(e)}'
        }), 500

# ============================================================================
# RUTAS - TAREAS ACADÉMICAS
# ============================================================================

@estudiante_bp.route('/tareas')
@login_required
def ver_tareas():
    """Vista para que el estudiante vea las tareas publicadas."""
    try:
        # Obtener el curso del estudiante
        matricula = Matricula.query.filter_by(estudianteId=current_user.id_usuario).first()
        
        if not matricula:
            flash('No estás matriculado en ningún curso', 'warning')
            return redirect(url_for('estudiante.estudiante_panel'))
        
        curso = Curso.query.get(matricula.cursoId)
        
        return render_template('estudiantes/tareas.html', curso=curso)
    
    except Exception as e:
        flash(f'Error al cargar tareas: {str(e)}', 'error')
        return redirect(url_for('estudiante.estudiante_panel'))


@estudiante_bp.route('/tareas/<int:tarea_id>')
@login_required
def ver_detalle_tarea(tarea_id):
    """Vista para ver el detalle de una tarea específica."""
    try:
        tarea = TareaAcademica.query.get_or_404(tarea_id)
        
        # Verificar que el estudiante esté en el curso de la tarea
        matricula = Matricula.query.filter_by(
            estudianteId=current_user.id_usuario,
            cursoId=tarea.curso_id
        ).first()
        
        if not matricula:
            flash('No tienes acceso a esta tarea', 'error')
            return redirect(url_for('estudiante.ver_tareas'))
        
        return render_template('estudiantes/detalle_tarea.html', tarea=tarea)
    
    except Exception as e:
        flash(f'Error al cargar tarea: {str(e)}', 'error')
        return redirect(url_for('estudiante.ver_tareas'))


@estudiante_bp.route('/api/mis-tareas', methods=['GET'])
@login_required
def api_mis_tareas():
    """
    Obtiene todas las tareas publicadas asignadas al estudiante actual.
    """
    try:
        # Consultar tareas del estudiante
        tareas = Calificacion.query.filter_by(
            estudianteId=current_user.id_usuario,
            es_tarea_publicada=True
        ).order_by(Calificacion.fecha_registro.desc()).all()
        
        # Formatear respuesta
        tareas_data = []
        for tarea in tareas:
            tareas_data.append({
                'id_tarea': tarea.id_calificacion,
                'titulo': tarea.nombre_calificacion,
                'descripcion': tarea.descripcion_tarea or '',
                'archivo_url': tarea.archivo_url,
                'archivo_nombre': tarea.archivo_nombre,
                'asignatura_id': tarea.asignaturaId,
                'asignatura_nombre': tarea.asignatura.nombre if tarea.asignatura else 'N/A',
                'profesor_id': tarea.profesor_id,
                'profesor_nombre': tarea.profesor.nombre_completo if tarea.profesor else 'N/A',
                'categoria_id': tarea.categoriaId,
                'categoria_nombre': tarea.categoria.nombre if tarea.categoria else 'N/A',
                'fecha_publicacion': tarea.fecha_registro.strftime('%Y-%m-%d %H:%M') if tarea.fecha_registro else None,
                'fecha_vencimiento': tarea.fecha_vencimiento.strftime('%Y-%m-%d %H:%M') if tarea.fecha_vencimiento else None,
                'valor': float(tarea.valor) if tarea.valor else None,
                'calificada': tarea.valor is not None
            })
        
        return jsonify({
            'success': True,
            'tareas': tareas_data
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error al obtener tareas: {str(e)}'
        }), 500


@estudiante_bp.route('/api/tareas/<int:tarea_id>', methods=['GET'])
@login_required
def api_obtener_tarea(tarea_id):
    """
    Obtiene el detalle completo de una tarea específica.
    """
    try:
        tarea = Calificacion.query.get(tarea_id)
        
        if not tarea:
            return jsonify({
                'success': False,
                'message': 'Tarea no encontrada'
            }), 404
        
        # Verificar que sea una tarea publicada
        if not tarea.es_tarea_publicada:
            return jsonify({
                'success': False,
                'message': 'Este registro no es una tarea publicada'
            }), 400
        
        # Verificar que la tarea pertenezca al estudiante actual
        if tarea.estudianteId != current_user.id_usuario:
            return jsonify({
                'success': False,
                'message': 'No tienes acceso a esta tarea'
            }), 403
        
        # Formatear respuesta
        tarea_data = {
            'id_tarea': tarea.id_calificacion,
            'titulo': tarea.nombre_calificacion,
            'descripcion': tarea.descripcion_tarea or '',
            'archivo_url': tarea.archivo_url,
            'archivo_nombre': tarea.archivo_nombre,
            'asignatura_id': tarea.asignaturaId,
            'asignatura_nombre': tarea.asignatura.nombre if tarea.asignatura else 'N/A',
            'profesor_id': tarea.profesor_id,
            'profesor_nombre': tarea.profesor.nombre_completo if tarea.profesor else 'N/A',
            'categoria_id': tarea.categoriaId,
            'categoria_nombre': tarea.categoria.nombre if tarea.categoria else 'N/A',
            'fecha_publicacion': tarea.fecha_registro.strftime('%Y-%m-%d %H:%M') if tarea.fecha_registro else None,
            'fecha_vencimiento': tarea.fecha_vencimiento.strftime('%Y-%m-%d %H:%M') if tarea.fecha_vencimiento else None,
            'valor': float(tarea.valor) if tarea.valor else None,
            'calificada': tarea.valor is not None,
            'observaciones': tarea.observaciones or ''
        }
        
        return jsonify({
            'success': True,
            'tarea': tarea_data
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error al obtener tarea: {str(e)}'
        }), 500

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
    Busca en la tabla AsignacionEquipo por el ID del estudiante
    """
    try:
        from controllers.models import AsignacionEquipo, Equipo, Mantenimiento, Incidente
        
        user_id = current_user.id_usuario
        usuario = Usuario.query.get(user_id)
        
        if not usuario:
            return jsonify({
                'success': False,
                'error': 'Usuario no encontrado'
            }), 404
        
        # Buscar asignación activa del estudiante
        asignacion = AsignacionEquipo.query.filter_by(
            estudiante_id=user_id,
            estado_asignacion='activa'
        ).first()
        
        if not asignacion:
            # El estudiante no tiene equipo asignado
            return jsonify({
                'success': False,
                'message': 'No tienes equipo asignado actualmente'
            }), 200
        
        # Obtener el equipo
        equipo = asignacion.equipo
        
        if equipo:
            # Buscar incidentes activos del equipo
            incidentes_activos = Incidente.query.filter_by(
                equipo_id=equipo.id_equipo,
                estado='reportado'
            ).order_by(Incidente.fecha.desc()).all()
            
            tiene_incidentes = len(incidentes_activos) > 0
            
            # Preparar información de incidentes
            incidentes_info = []
            for inc in incidentes_activos:
                incidentes_info.append({
                    'id_incidente': inc.id_incidente,
                    'descripcion': inc.descripcion,
                    'prioridad': inc.prioridad,
                    'fecha': inc.fecha.strftime('%d %b %Y') if inc.fecha else None,
                    'estado': inc.estado
                })
            
            # Preparar datos del equipo
            equipo_data = {
                'id_equipo': equipo.id_equipo,
                'id_referencia': equipo.id_referencia,
                'nombre': equipo.nombre,
                'tipo': equipo.tipo,
                'estado': equipo.estado,
                'sistema_operativo': equipo.sistema_operativo or 'N/A',
                'ram': equipo.ram or 'N/A',
                'disco_duro': equipo.disco_duro or 'N/A',
                'procesador': equipo.sistema_operativo or 'N/A',
                'descripcion': equipo.descripcion or '',
                'observaciones': equipo.observaciones or '',
                'salon': equipo.salon.nombre if equipo.salon else 'N/A',
                'sede_nombre': equipo.salon.sede.nombre if equipo.salon and equipo.salon.sede else 'N/A',
                
                # ✅ FECHA DE ASIGNACIÓN (desde la tabla AsignacionEquipo)
                'fecha_asignacion': asignacion.fecha_asignacion.strftime('%d %b %Y') if asignacion.fecha_asignacion else 'N/A',
                'fecha_adquisicion': asignacion.fecha_asignacion.strftime('%d %b %Y') if asignacion.fecha_asignacion else 'N/A',
                
                'observaciones_asignacion': asignacion.observaciones or '',
                
                # ✅ INFORMACIÓN DE INCIDENTES
                'tiene_incidentes': tiene_incidentes,
                'total_incidentes': len(incidentes_activos),
                'incidentes': incidentes_info
            }
            
            # Buscar último mantenimiento
            ultimo_mantenimiento = Mantenimiento.query.filter_by(
                equipo_id=equipo.id_equipo,
                estado='realizado'
            ).order_by(Mantenimiento.fecha_realizada.desc()).first()
            
            # Buscar próximo mantenimiento programado
            proximo_mantenimiento = Mantenimiento.query.filter_by(
                equipo_id=equipo.id_equipo,
                estado='pendiente'
            ).order_by(Mantenimiento.fecha_programada.asc()).first()
            
            equipo_data['ultima_revision'] = ultimo_mantenimiento.fecha_realizada.strftime('%d %b %Y') if ultimo_mantenimiento and ultimo_mantenimiento.fecha_realizada else None
            equipo_data['proximo_mantenimiento'] = proximo_mantenimiento.fecha_programada.strftime('%d %b %Y') if proximo_mantenimiento and proximo_mantenimiento.fecha_programada else None
            
            return jsonify({
                'success': True,
                'equipo': equipo_data
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Error al obtener información del equipo'
            }), 500
            
    except Exception as e:
        print(f"ERROR en api_mi_equipo: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
@estudiante_bp.route('/api/usuario-actual', methods=['GET'])
@login_required
def api_usuario_actual():
    """
    API para obtener información básica del usuario actual
    """
    try:
        usuario = current_user
        
        return jsonify({
            'success': True,
            'usuario': {
                'id_usuario': usuario.id_usuario,
                'nombre': usuario.nombre,
                'apellido': usuario.apellido,
                'nombre_completo': usuario.nombre_completo,
                'correo': usuario.correo,
                'rol': usuario.rol_nombre if hasattr(usuario, 'rol_nombre') else None
            }
        }), 200
            
    except Exception as e:
        print(f"ERROR en api_usuario_actual: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500