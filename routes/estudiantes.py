# routes/estudiantes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from controllers.decorators import role_required, permission_required
from datetime import datetime, timedelta, time, date
from controllers.models import (
    db, Usuario, Comunicacion, Evento, Candidato, HorarioVotacion, Voto,
    Calificacion, Asistencia, CicloAcademico, PeriodoAcademico, Matricula, Curso, Notificacion,
    HorarioCurso, Asignatura, Salon, BloqueHorario, CategoriaCalificacion, SolicitudConsulta
)
from services.notification_service import (
    obtener_todas_notificaciones,
    marcar_notificacion_como_leida,
    contar_notificaciones_no_leidas
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
def ver_calificaciones():
    """Muestra calificaciones como la vista del padre, pero solo de solicitudes aceptadas."""
    try:
        if not current_user or not current_user.rol or current_user.rol.nombre.lower() != 'estudiante':
            flash('Acceso no autorizado.', 'danger')
            return redirect(url_for('auth.login'))

        estudiante = current_user
        asignatura_id = request.args.get('asignatura_id', type=int)

        # Buscar solicitudes aceptadas para este estudiante
        q_aceptadas = SolicitudConsulta.query.filter_by(estudiante_id=estudiante.id_usuario, estado='aceptada')\
            .order_by(SolicitudConsulta.fecha_respuesta.desc())

        if not asignatura_id:
            ultima = q_aceptadas.first()
            if ultima:
                asignatura_id = ultima.asignatura_id
        solicitud_sel = None
        if asignatura_id:
            solicitud_sel = q_aceptadas.filter_by(asignatura_id=asignatura_id).first()

        if not solicitud_sel:
            # No hay solicitud aceptada; mostrar página con mensaje y sin calificaciones
            return render_template(
                'estudiantes/calificaciones.html',
                estudiante=estudiante,
                asignatura=Asignatura.query.get(asignatura_id) if asignatura_id else None,
                ultima_fecha_reporte=None,
                calificaciones_por_categoria={},
                promedios_por_categoria={},
                promedio_general=0.0,
                aceptadas=q_aceptadas.all()
            )

        # Cargar calificaciones del estudiante para la asignatura
        califs = Calificacion.query.filter_by(estudianteId=estudiante.id_usuario, asignaturaId=asignatura_id).all()

        # Agrupar por categoría
        from collections import defaultdict
        por_cat = defaultdict(lambda: {'categoria': None, 'calificaciones': []})
        for c in califs:
            cat = CategoriaCalificacion.query.get(c.categoriaId) if getattr(c, 'categoriaId', None) else None
            key = c.categoriaId or 0
            if por_cat[key]['categoria'] is None:
                por_cat[key]['categoria'] = cat or type('obj', (), {'nombre': 'Sin categoría'})()
            por_cat[key]['calificaciones'].append(c)

        # Promedios por categoría y general
        proms_por_cat = {}
        valores_globales = []
        for key, data in por_cat.items():
            vals = [float(x.valor) for x in data['calificaciones'] if x.valor is not None]
            proms_por_cat[key] = (sum(vals)/len(vals)) if vals else 0.0
            valores_globales.extend(vals)
        promedio_general = round(sum(valores_globales)/len(valores_globales), 2) if valores_globales else 0.0

        asignatura = Asignatura.query.get(asignatura_id)
        ultima_fecha = solicitud_sel.fecha_respuesta

        return render_template(
            'estudiantes/calificaciones.html',
            estudiante=estudiante,
            asignatura=asignatura,
            ultima_fecha_reporte=ultima_fecha,
            calificaciones_por_categoria=por_cat,
            promedios_por_categoria=proms_por_cat,
            promedio_general=promedio_general,
            aceptadas=q_aceptadas.all()
        )
    except Exception as e:
        flash(f'Error cargando calificaciones: {str(e)}', 'danger')
        return redirect(url_for('estudiante.estudiante_panel'))

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
# Mi Horario (vista y API)
# =======================

@estudiante_bp.route('/mi-horario')
@login_required
def mi_horario():
    try:
        # Obtener matrícula más reciente del estudiante
        matricula = Matricula.query.filter_by(estudianteId=current_user.id_usuario)\
            .order_by(Matricula.fecha_matricula.desc()).first()
        curso = Curso.query.get(matricula.cursoId) if matricula else None
        return render_template('estudiantes/mi_horario.html', curso=curso)
    except Exception as e:
        flash(f'Error cargando Mi Horario: {str(e)}', 'error')
        return redirect(url_for('estudiante.estudiante_panel'))


@estudiante_bp.route('/api/mi-horario', methods=['GET'])
@login_required
def api_mi_horario():
    """Devuelve el horario del curso del estudiante autenticado."""
    try:
        # 1) Obtener matrícula actual
        matricula = Matricula.query.filter_by(estudianteId=current_user.id_usuario)\
            .order_by(Matricula.fecha_matricula.desc()).first()
        if not matricula:
            return jsonify({'success': True, 'horario': None, 'message': 'No hay matrícula activa'}), 200

        curso = Curso.query.get(matricula.cursoId)
        if not curso:
            return jsonify({'success': True, 'horario': None, 'message': 'Curso no encontrado'}), 200

        # Helpers
        def _normalizar_dia(dia_str):
            if not dia_str:
                return None
            d = str(dia_str).strip().lower()
            mapping = {
                'lunes': 'lunes',
                'martes': 'martes',
                'miercoles': 'miercoles',
                'miércoles': 'miercoles',
                'jueves': 'jueves',
                'viernes': 'viernes',
                'sabado': 'sabado',
                'sábado': 'sabado',
                'domingo': 'domingo'
            }
            return mapping.get(d, d)

        def _fmt_hora(val):
            try:
                if hasattr(val, 'strftime'):
                    return val.strftime('%H:%M')
                s = str(val).strip()
                if len(s) >= 5 and s[2] == ':':
                    return s[:5]
                if ':' in s:
                    parts = s.split(':')
                    h = int(parts[0]) if parts[0] else 0
                    m = int(parts[1]) if len(parts) > 1 and parts[1] else 0
                    return f"{h:02d}:{m:02d}"
            except Exception:
                pass
            return ''

        # 2) Consultar asignaciones de horario para el curso
        entradas = db.session.query(HorarioCurso, Asignatura, Usuario, Salon)\
            .join(Asignatura, HorarioCurso.asignatura_id == Asignatura.id_asignatura)\
            .outerjoin(Usuario, HorarioCurso.profesor_id == Usuario.id_usuario)\
            .outerjoin(Salon, HorarioCurso.id_salon_fk == Salon.id_salon)\
            .filter(HorarioCurso.curso_id == curso.id_curso)\
            .all()

        # Mapa por hora (compatibilidad) y expansión de rangos horarios a cada hora
        clases = {}
        for hc, asig, prof, salon in entradas:
            dia_norm = _normalizar_dia(hc.dia_semana)
            hora_ini = _fmt_hora(hc.hora_inicio)
            hora_fin = _fmt_hora(hc.hora_fin)
            if not dia_norm or not hora_ini:
                continue
            def _to_min(hhmm):
                try:
                    h, m = map(int, hhmm.split(':'))
                    return h*60 + m
                except Exception:
                    return None
            ini_min = _to_min(hora_ini)
            fin_min = _to_min(hora_fin) if hora_fin else None
            slots = []
            if fin_min is None or fin_min <= ini_min:
                slots = [hora_ini]
            else:
                start_hour = ini_min // 60
                end_hour = (fin_min + 59) // 60
                for h in range(start_hour, end_hour):
                    slots.append(f"{h:02d}:00")
            for slot in slots:
                clave = f"{dia_norm}_{slot}"
                if clave not in clases:
                    clases[clave] = {
                        'asignatura': asig.nombre if asig else 'N/A',
                        'profesor': prof.nombre_completo if prof else 'N/A',
                        'salon': salon.nombre if salon else 'N/A',
                        'hora_inicio': hora_ini,
                        'hora_fin': hora_fin or 'N/A'
                    }

        # 3) Bloques y descansos desde HorarioGeneral
        dias_list, bloques_list, matriz_bloques, clases_por_bloque = [], [], {}, {}
        hg = getattr(curso, 'horario_general', None)
        if hg:
            # Días (guardados como JSON en campo diasSemana)
            try:
                import json
                dias_list = json.loads(hg.diasSemana) if hg.diasSemana else []
            except Exception:
                dias_list = []
            # Bloques
            bloques = BloqueHorario.query.filter_by(horario_general_id=hg.id_horario).order_by(BloqueHorario.orden).all()
            for b in bloques:
                dia_b = _normalizar_dia(b.dia_semana)
                start = _fmt_hora(b.horaInicio)
                end = _fmt_hora(b.horaFin)
                if not start or not end:
                    continue
                bloque_key = f"{start}-{end}"
                if bloque_key not in bloques_list:
                    bloques_list.append(bloque_key)
                if dia_b:
                    matriz_bloques.setdefault(dia_b, {})[bloque_key] = {
                        'tipo': (b.tipo or '').lower(),
                        'nombre': b.nombre or '',
                        'break_type': (b.break_type or ''),
                        'class_type': (b.class_type or '')
                    }
                    clases_por_bloque.setdefault(dia_b, {})[bloque_key] = None

        # 4) Asignar cada HorarioCurso al/los bloques que se solapen
        def _minutos(hhmm):
            try:
                h, m = map(int, str(hhmm).split(':'))
                return h*60 + m
            except Exception:
                return None

        for hc, asig, prof, salon in entradas:
            dia_norm = _normalizar_dia(hc.dia_semana)
            ini = _fmt_hora(hc.hora_inicio)
            fin = _fmt_hora(hc.hora_fin)
            if not dia_norm or not ini or not fin:
                continue
            ini_m = _minutos(ini); fin_m = _minutos(fin)
            if ini_m is None or fin_m is None:
                continue
            for bloque_key, meta in (matriz_bloques.get(dia_norm, {}) or {}).items():
                b_ini, b_fin = [x.strip() for x in bloque_key.split('-')]
                b_ini_m = _minutos(b_ini); b_fin_m = _minutos(b_fin)
                if b_ini_m is None or b_fin_m is None:
                    continue
                if max(ini_m, b_ini_m) < min(fin_m, b_fin_m):
                    if meta.get('tipo', '') in ('break','descanso','receso'):
                        continue
                    clases_por_bloque[dia_norm][bloque_key] = {
                        'asignatura': asig.nombre if asig else 'N/A',
                        'profesor': prof.nombre_completo if prof else 'N/A',
                        'salon': salon.nombre if salon else 'N/A',
                        'hora_inicio': ini,
                        'hora_fin': fin
                    }

        horario_data = {
            'curso': curso.nombreCurso,
            'sede': curso.sede.nombre if getattr(curso, 'sede', None) else 'N/A',
            'clases': clases,
            'dias': dias_list,
            'bloques': bloques_list,
            'matriz_bloques': matriz_bloques,
            'clases_por_bloque': clases_por_bloque
        }

        return jsonify({'success': True, 'horario': horario_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


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

@estudiante_bp.route('/notificaciones')
@login_required
def notificaciones():
    try:
        # Enviar conteo no leídas al template si se requiere
        unread = contar_notificaciones_no_leidas(current_user.id_usuario)
    except Exception:
        unread = 0
    return render_template('estudiantes/notificaciones.html', unread=unread)

@estudiante_bp.route('/api/notificaciones', methods=['GET'])
@login_required
def api_listar_notificaciones():
    try:
        limite = request.args.get('limite', default=50, type=int)
        notifs = obtener_todas_notificaciones(current_user.id_usuario, limite=limite)
        data = []
        for n in notifs:
            data.append({
                'id': getattr(n, 'id_notificacion', None),
                'titulo': getattr(n, 'titulo', ''),
                'mensaje': getattr(n, 'mensaje', ''),
                'tipo': getattr(n, 'tipo', 'general'),
                'link': getattr(n, 'link', None),
                'leida': getattr(n, 'leida', False),
                'creada_en': n.creada_en.isoformat() if getattr(n, 'creada_en', None) else None
            })
        return jsonify({'success': True, 'notificaciones': data, 'total': len(data)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@estudiante_bp.route('/api/notificaciones/<int:notificacion_id>/leer', methods=['PUT'])
@login_required
def api_marcar_notificacion_leida(notificacion_id):
    try:
        ok = marcar_notificacion_como_leida(notificacion_id, current_user.id_usuario)
        return jsonify({'success': ok}) if ok else jsonify({'success': False, 'error': 'No encontrada'}), (200 if ok else 404)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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
    

   # 📌 RUTAS COMPLETAS PARA NOTIFICACIONES
@estudiante_bp.route("/notificaciones")
@login_required
def ver_notificaciones():
    """Página principal de notificaciones"""
    try:
        # Obtener todas las notificaciones del usuario
        notificaciones = Notificacion.query.filter_by(
            usuario_id=current_user.id_usuario
        ).order_by(Notificacion.creada_en.desc()).all()
        
        # Contar no leídas
        no_leidas = Notificacion.query.filter_by(
            usuario_id=current_user.id_usuario,
            leida=False
        ).count()
        
        return render_template(
            "estudiantes/notificaciones.html", 
            notificaciones=notificaciones,
            notificaciones_no_leidas=no_leidas
        )
        
    except Exception as e:
        flash(f"Error al cargar notificaciones: {str(e)}", "error")
        return redirect(url_for('estudiante.estudiante_panel'))  # ✅ CORREGIDO: Indentación

@estudiante_bp.route("/api/notificaciones")
@login_required
def obtener_notificaciones():
    """API para obtener notificaciones del estudiante"""
    try:
        # Obtener notificaciones del usuario actual
        notificaciones = Notificacion.query.filter_by(
            usuario_id=current_user.id_usuario
        ).order_by(Notificacion.creada_en.desc()).limit(10).all()
        
        notificaciones_data = []
        for notif in notificaciones:
            notificaciones_data.append({
                "id": notif.id_notificacion,
                "titulo": notif.titulo,
                "mensaje": notif.mensaje,
                "tipo": notif.tipo,
                "leida": notif.leida,
                "link": notif.link,
                "fecha_creacion": notif.creada_en.strftime('%d/%m/%Y %H:%M') if notif.creada_en else 'Reciente'
            })
        
        # Contar notificaciones no leídas
        no_leidas = Notificacion.query.filter_by(
            usuario_id=current_user.id_usuario,
            leida=False
        ).count()
        
        return jsonify({
            "notificaciones": notificaciones_data,
            "no_leidas": no_leidas
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@estudiante_bp.route("/api/notificaciones/<int:notificacion_id>/marcar-leida", methods=["POST"])
@login_required
def marcar_notificacion_leida(notificacion_id):
    """Marcar una notificación como leída"""
    try:
        notificacion = Notificacion.query.filter_by(
            id_notificacion=notificacion_id,
            usuario_id=current_user.id_usuario
        ).first()
        
        if not notificacion:
            return jsonify({"error": "Notificación no encontrada"}), 404
        
        notificacion.leida = True
        db.session.commit()
        
        return jsonify({"success": True}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@estudiante_bp.route("/api/notificaciones/marcar-todas-leidas", methods=["POST"])
@login_required
def marcar_todas_leidas():
    """Marcar todas las notificaciones como leídas"""
    try:
        Notificacion.query.filter_by(
            usuario_id=current_user.id_usuario,
            leida=False
        ).update({"leida": True})
        
        db.session.commit()
        return jsonify({"success": True}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@estudiante_bp.route("/api/notificaciones/<int:notificacion_id>/eliminar", methods=["DELETE"])
@login_required
def eliminar_notificacion(notificacion_id):
    """Eliminar una notificación"""
    try:
        notificacion = Notificacion.query.filter_by(
            id_notificacion=notificacion_id,
            usuario_id=current_user.id_usuario
        ).first()
        
        if not notificacion:
            return jsonify({"error": "Notificación no encontrada"}), 404
        
        db.session.delete(notificacion)
        db.session.commit()
        
        return jsonify({"success": True}), 200
        
    except Exception as e:
        db.session.rollback()
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