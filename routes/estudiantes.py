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




# =======================
# Comunicaciones
# =======================
@estudiante_bp.route('/comunicaciones')
@login_required
@permission_required('ver_comunicaciones_estudiante')
def ver_comunicaciones():
    bandeja = Comunicacion.query.filter_by(destinatario_id=current_user.id_usuario, estado="inbox").count()
    enviados = Comunicacion.query.filter_by(remitente_id=current_user.id_usuario, estado="sent").count()
    borradores = Comunicacion.query.filter_by(remitente_id=current_user.id_usuario, estado="draft").count()
    eliminados = Comunicacion.query.filter_by(remitente_id=current_user.id_usuario, estado="deleted").count()

    return render_template(
        "estudiantes/comunicaciones/index.html",
        usuario=current_user,
        bandeja=bandeja,
        enviados=enviados,
        borradores=borradores,
        eliminados=eliminados
    )

# =======================
# API - Enviar correo
# =======================
@estudiante_bp.route('/comunicaciones/enviar', methods=['POST'])
@login_required
@permission_required('ver_comunicaciones_estudiante')
def enviar_correo():
    data = request.get_json()

    nuevo = Comunicacion(
        remitente_id=current_user.id_usuario,
        destinatario_id=data.get("destinatario"),
        asunto=data.get("asunto"),
        mensaje=data.get("mensaje"),
        estado="sent"
    )
    db.session.add(nuevo)
    db.session.commit()
    return jsonify({"ok": True, "msg": "Correo enviado con éxito"})

# =======================
# API - Guardar borrador
# =======================
@estudiante_bp.route('/comunicaciones/borrador', methods=['POST'])
@login_required
@permission_required('ver_comunicaciones_estudiante')
def guardar_borrador():
    data = request.get_json()

    borrador = Comunicacion(
        remitente_id=current_user.id_usuario,
        destinatario_id=data.get("destinatario"),
        asunto=data.get("asunto"),
        mensaje=data.get("mensaje"),
        estado="draft"
    )
    db.session.add(borrador)
    db.session.commit()
    return jsonify({"ok": True, "msg": "Borrador guardado"})


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