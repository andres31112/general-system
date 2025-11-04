from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime
from controllers.decorators import role_required, permission_required
from controllers.models import (
    db, Usuario, Rol, Comunicacion, SolicitudConsulta, Asignatura,
    Calificacion, Asistencia, Clase, Matricula, Curso, HorarioCompartido, HorarioCurso, Salon, Sede,
    CicloAcademico, PeriodoAcademico, CategoriaCalificacion, Notificacion, Evento
    )


padre_bp = Blueprint('padre', __name__, url_prefix='/padre')
# ========== FUNCIÓN AUXILIAR CORREGIDA ==========
def get_sidebar_counts():
    """Función auxiliar para obtener los contadores del sidebar"""
    from datetime import datetime
    
    try:
        # DEBUG: Ver qué valores de estado existen
        estados = db.session.query(Comunicacion.estado).distinct().all()
        estados_lista = [e[0] for e in estados]
        print("🔍 VALORES DE 'estado' EN COMUNICACIONES:", estados_lista)
    except Exception as e:
        print("❌ Error en debug de estados:", e)
        estados_lista = []
    
    # Determinar el valor correcto para mensajes no leídos
    estado_no_leido = 'inbox'  # Valor por defecto común
    
    # Probar diferentes valores comunes
    if 'no_leido' in estados_lista:
        estado_no_leido = 'no_leido'
    elif 'unread' in estados_lista:
        estado_no_leido = 'unread'
    elif 'pendiente' in estados_lista:
        estado_no_leido = 'pendiente'
    elif 'nuevo' in estados_lista:
        estado_no_leido = 'nuevo'
    
    print(f"🎯 Usando estado: '{estado_no_leido}' para mensajes no leídos")
    
    # Mensajes no leídos (para comunicaciones)
    unread_messages = Comunicacion.query.filter_by(
        destinatario_id=current_user.id_usuario, 
        estado=estado_no_leido
    ).count()
    
    # Notificaciones no leídas (para notificaciones)
    unread_notifications = Notificacion.query.filter_by(
        usuario_id=current_user.id_usuario,
        leida=False
    ).count()
    
    # ✅ VERSIÓN CORREGIDA: Eventos próximos con filtro más estricto
    hoy = datetime.now().date()
    
    # Obtener TODOS los eventos para debug
    todos_eventos = Evento.query.all()
    print(f"📋 TODOS LOS EVENTOS EN BD ({len(todos_eventos)} total):")
    for evento in todos_eventos:
        print(f"   - ID: {evento.id}, Nombre: '{evento.nombre}', Fecha: {evento.fecha}, Rol: {evento.rol_destino}")
    
    # Eventos que cumplen el filtro estricto
    eventos_filtrados = Evento.query.filter(
        Evento.fecha.isnot(None),  # Excluir eventos sin fecha
        Evento.fecha >= hoy        # Solo eventos de hoy en adelante
    ).all()
    
    print(f"🎯 EVENTOS FILTRADOS (fecha >= {hoy} y fecha NOT NULL): {len(eventos_filtrados)} eventos")
    for evento in eventos_filtrados:
        print(f"   ✅ INCLUIDO - ID: {evento.id}, Nombre: '{evento.nombre}', Fecha: {evento.fecha}")
    
    upcoming_events = len(eventos_filtrados)
    
    print(f"📊 RESUMEN CONTADORES - Mensajes: {unread_messages}, Notificaciones: {unread_notifications}, Eventos: {upcoming_events}")
    
    return {
        'unread_messages': unread_messages,
        'unread_notifications': unread_notifications,
        'upcoming_events': upcoming_events
    }
# ========== FIN FUNCIÓN AUXILIAR ==========

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
                    try:
                        valores = [float(cal.valor) for cal in calificaciones_hijo if cal.valor is not None and cal.valor != '']
                        if valores:
                            promedio_hijo = sum(valores) / len(valores)
                            promedios_hijos.append(promedio_hijo)
                    except (ValueError, TypeError) as e:
                        print(f"Error calculando promedio para hijo {hijo.id_usuario}: {e}")
                        continue
         
                # Obtener clases inscritas del hijo
                clases_hijo = Matricula.query.filter_by(estudianteId=hijo.id_usuario).count()
                total_clases_inscritas += clases_hijo
                
                # Obtener calificaciones recientes (últimas 5)
                calificaciones_recientes_hijo = Calificacion.query.filter_by(
                    estudianteId=hijo.id_usuario
                ).order_by(Calificacion.fecha_registro.desc()).limit(5).all()
                calificaciones_recientes.extend(calificaciones_recientes_hijo)
            
            if promedios_hijos:
                promedio_general = round(sum(promedios_hijos) / len(promedios_hijos), 2)
                 
            # Obtener mensajes de profesores (comunicaciones donde el padre es destinatario)
            mensajes_profesores = Comunicacion.query.filter_by(destinatario_id=current_user.id_usuario).count()
            
            # Obtener anuncios importantes (comunicaciones del sistema)
            anuncios_importantes = Comunicacion.query.filter_by(remitente_id=None).order_by(Comunicacion.fecha_envio.desc()).limit(3).all()
        
        # OBTENER CONTADORES DEL SIDEBAR USANDO LA FUNCIÓN
        counts = get_sidebar_counts()
        
        return render_template('padres/dashboard.html',
                             total_hijos=total_hijos,
                             promedio_general=promedio_general,
                             total_clases_inscritas=total_clases_inscritas,
                             mensajes_profesores=mensajes_profesores,
                             calificaciones_recientes=calificaciones_recientes,
                             anuncios_importantes=anuncios_importantes,
                             hijos=hijos,
                             # ✅ VARIABLES CORREGIDAS PARA EL TEMPLATE BASE
                             unread_messages=counts['unread_messages'],
                             unread_notifications=counts['unread_notifications'],
                             upcoming_events=counts['upcoming_events'])
    
    except Exception as e:
        flash(f'Error cargando el dashboard: {str(e)}', 'error')
        # OBTENER CONTADORES INCLUSO EN CASO DE ERROR
        counts = get_sidebar_counts()
        return render_template('padres/dashboard.html',
                             total_hijos=0,
                             promedio_general=0,
                             total_clases_inscritas=0,
                             mensajes_profesores=0,
                             calificaciones_recientes=[],
                             anuncios_importantes=[],
                             hijos=[],
                             # ✅ VARIABLES CORREGIDAS PARA EL TEMPLATE BASE
                             unread_messages=counts['unread_messages'],
                             unread_notifications=counts['unread_notifications'],
                             upcoming_events=counts['upcoming_events'])

@padre_bp.route('/comunicaciones')
@login_required
@role_required('Padre')
def comunicaciones():
    """Página para que el padre vea comunicados de la institución."""
    # OBTENER CONTADORES DEL SIDEBAR
    counts = get_sidebar_counts()
    return render_template('padres/comunicaciones.html',
                         # ✅ VARIABLES CORREGIDAS PARA EL TEMPLATE BASE
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])

@padre_bp.route('/consultar_estudiante')
@login_required
@role_required('Padre')
def consultar_estudiante():
    """Página para que el padre envíe solicitudes de consulta de notas."""
    # Obtener asignaturas disponibles
    asignaturas = Asignatura.query.filter_by(estado='activa').all()
    
    # Obtener solicitudes previas del padre
    solicitudes = SolicitudConsulta.query.filter_by(padre_id=current_user.id_usuario).order_by(SolicitudConsulta.fecha_solicitud.desc()).all()
    
    # OBTENER CONTADORES DEL SIDEBAR
    counts = get_sidebar_counts()
    
    return render_template('padres/consultar_estudiante.html', 
                         asignaturas=asignaturas, 
                         solicitudes=solicitudes,
                         # ✅ VARIABLES CORREGIDAS PARA EL TEMPLATE BASE
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])

@padre_bp.route('/notificaciones')
@login_required
@role_required('Padre')
def notificaciones():
    """Página de notificaciones para el padre."""
    try:
        # OBTENER CONTADORES DEL SIDEBAR
        counts = get_sidebar_counts()
        
        # Obtener todas las notificaciones del usuario padre para la página
        notificaciones_list = Notificacion.query.filter_by(
            usuario_id=current_user.id_usuario
        ).order_by(Notificacion.creada_en.desc()).all()
        
        return render_template(
            "padres/notificaciones.html", 
            notificaciones=notificaciones_list,
            notificaciones_no_leidas=counts['unread_notifications'],
            # ✅ VARIABLES CORREGIDAS PARA EL TEMPLATE BASE
            unread_messages=counts['unread_messages'],
            unread_notifications=counts['unread_notifications'],
            upcoming_events=counts['upcoming_events']
        )
        
    except Exception as e:
        flash(f"Error al cargar notificaciones: {str(e)}", "error")
        # OBTENER CONTADORES INCLUSO EN CASO DE ERROR
        counts = get_sidebar_counts()
        return render_template(
            "padres/notificaciones.html",
            notificaciones=[],
            notificaciones_no_leidas=counts['unread_notifications'],
            unread_messages=counts['unread_messages'],
            unread_notifications=counts['unread_notifications'],
            upcoming_events=counts['upcoming_events']
        )

@padre_bp.route('/informacion_academica')
@login_required
@role_required('Padre')
def informacion_academica():
    """Página de información académica del padre."""
    # Obtener los hijos del padre usando la relación backref
    hijos = current_user.hijos.all()
    
    # OBTENER CONTADORES DEL SIDEBAR
    counts = get_sidebar_counts()
    
    return render_template('padres/informacion_academica.html', 
                         hijos=hijos,
                         # ✅ VARIABLES CORREGIDAS PARA EL TEMPLATE BASE
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])

@padre_bp.route('/horario_clases')
@login_required
@role_required('Padre')
def horario_clases():
    """Página de horario de clases del padre."""
    # Obtener los hijos del padre usando la relación backref
    hijos = current_user.hijos.all()
    
    # OBTENER CONTADORES DEL SIDEBAR
    counts = get_sidebar_counts()
    
    return render_template('padres/horario_clases.html', 
                         hijos=hijos,
                         # ✅ VARIABLES CORREGIDAS PARA EL TEMPLATE BASE
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])

@padre_bp.route('/estudiante/<int:estudiante_id>/detalle')
@login_required
@role_required('Padre')
def detalle_estudiante(estudiante_id):
    """Página con detalle completo del estudiante: calendario, asistencias, tareas y consultas."""
    # Verificar que el estudiante pertenece al padre
    if not verificar_relacion_padre_hijo(current_user.id_usuario, estudiante_id):
        flash('No tienes permisos para acceder a este estudiante', 'danger')
        return redirect(url_for('padre.informacion_academica'))
    
    estudiante = Usuario.query.get_or_404(estudiante_id)
    
    # OBTENER CONTADORES DEL SIDEBAR
    counts = get_sidebar_counts()
    
    return render_template('padres/detalle_estudiante.html', 
                         estudiante=estudiante,
                         # ✅ VARIABLES CORREGIDAS PARA EL TEMPLATE BASE
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])

@padre_bp.route('/estudiante/<int:estudiante_id>/calificaciones')
@login_required
@role_required('Padre')
def ver_calificaciones_hijo(estudiante_id):
    """Redirige a las calificaciones del estudiante (primera asignatura disponible)."""
    from controllers.models import Calificacion
    
    # Verificar que el estudiante pertenece al padre
    if not verificar_relacion_padre_hijo(current_user.id_usuario, estudiante_id):
        flash('No tienes permisos para acceder a este estudiante', 'danger')
        return redirect(url_for('padre.informacion_academica'))
    
    # Obtener la primera asignatura con calificaciones para este estudiante
    primera_calificacion = Calificacion.query.filter_by(estudianteId=estudiante_id).first()
    
    if primera_calificacion and primera_calificacion.asignaturaId:
        # Redirigir a ver las calificaciones de la primera asignatura
        return redirect(url_for('padre.ver_calificaciones_estudiante', 
                              estudiante_id=estudiante_id, 
                              asignatura_id=primera_calificacion.asignaturaId))
    else:
        # Si no hay calificaciones, mostrar mensaje
        flash('Aún no hay calificaciones registradas para este estudiante', 'info')
        return redirect(url_for('padre.detalle_estudiante', estudiante_id=estudiante_id))

@padre_bp.route('/estudiante/<int:estudiante_id>/calificaciones/detalle', endpoint='ver_calificaciones_historial')
@login_required
@role_required('Padre')
def ver_calificaciones_historial(estudiante_id):
    """Muestra calificaciones del estudiante filtradas por consultas aceptadas (historial)."""
    try:
        # Verificar relación padre-hijo
        if not verificar_relacion_padre_hijo(current_user.id_usuario, estudiante_id):
            flash('No tienes permisos para acceder a este estudiante', 'danger')
            return redirect(url_for('padre.informacion_academica'))

        estudiante = Usuario.query.get_or_404(estudiante_id)
        asignatura_id = request.args.get('asignatura_id', type=int)

        # Historial de solicitudes aceptadas
        q_aceptadas = SolicitudConsulta.query.filter_by(padre_id=current_user.id_usuario, estudiante_id=estudiante_id, estado='aceptada')\
            .order_by(SolicitudConsulta.fecha_respuesta.desc())

        if not asignatura_id:
            ultima = q_aceptadas.first()
            if ultima:
                asignatura_id = ultima.asignatura_id

        solicitud_sel = None
        if asignatura_id:
            solicitud_sel = q_aceptadas.filter_by(asignatura_id=asignatura_id).first()

        if not solicitud_sel:
            # Sin solicitud aceptada para esa asignatura
            return render_template(
                'padres/calificaciones_estudiante.html',
                estudiante=estudiante,
                asignatura=Asignatura.query.get(asignatura_id) if asignatura_id else None,
                ultima_fecha_reporte=None,
                calificaciones_por_categoria={},
                promedios_por_categoria={},
                promedio_general=0.0,
                aceptadas=q_aceptadas.all()
            )

        # Calificaciones del estudiante en la asignatura seleccionada
        califs = Calificacion.query.filter_by(estudianteId=estudiante_id, asignaturaId=asignatura_id).all()

        from collections import defaultdict
        por_cat = defaultdict(lambda: {'categoria': None, 'calificaciones': []})
        for c in califs:
            cat = CategoriaCalificacion.query.get(getattr(c, 'categoriaId', None)) if getattr(c, 'categoriaId', None) else None
            key = c.categoriaId or 0
            if por_cat[key]['categoria'] is None:
                por_cat[key]['categoria'] = cat or type('obj', (), {'nombre': 'Sin categoría'})()
            por_cat[key]['calificaciones'].append(c)

        proms_por_cat = {}
        valores_globales = []
        for key, data in por_cat.items():
            vals = [float(x.valor) for x in data['calificaciones'] if x.valor is not None]
            proms_por_cat[key] = (sum(vals) / len(vals)) if vals else 0.0
            valores_globales.extend(vals)
        promedio_general = round(sum(valores_globales) / len(valores_globales), 2) if valores_globales else 0.0

        asignatura = Asignatura.query.get(asignatura_id)
        ultima_fecha = solicitud_sel.fecha_respuesta

        return render_template(
            'padres/calificaciones_estudiante.html',
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
        return redirect(url_for('padre.detalle_estudiante', estudiante_id=estudiante_id))

# API Routes para Información Académica
@padre_bp.route('/api/estadisticas_estudiante/<int:estudiante_id>')
@login_required
@role_required('Padre')
def api_estadisticas_estudiante(estudiante_id):
    """API para obtener estadísticas generales de un estudiante."""
    try:
        # Verificar que el estudiante pertenece al padre
        if not verificar_relacion_padre_hijo(current_user.id_usuario, estudiante_id):
            return jsonify({'success': False, 'message': 'No tienes permisos'}), 403
        
        # Calcular promedio general de todas las calificaciones
        from sqlalchemy import func
        calificaciones = Calificacion.query.filter_by(estudianteId=estudiante_id).filter(Calificacion.valor.isnot(None)).all()
        
        if calificaciones:
            suma_notas = sum([float(cal.valor) for cal in calificaciones if cal.valor is not None])
            promedio_general = round(suma_notas / len(calificaciones), 2) if calificaciones else 0
        else:
            promedio_general = 0
        
        # Contar asistencias
        total_asistencias = Asistencia.query.filter_by(
            estudianteId=estudiante_id,
            estado='presente'
        ).count()
        
        # Contar fallas
        total_fallas = Asistencia.query.filter_by(
            estudianteId=estudiante_id,
            estado='falta'
        ).count()
        
        # Contar retardos
        total_retardos = Asistencia.query.filter_by(
            estudianteId=estudiante_id,
            estado='retardo'
        ).count()
        
        # Contar tareas pendientes
        tareas_pendientes = Calificacion.query.filter_by(
            estudianteId=estudiante_id,
            es_tarea_publicada=True
        ).filter(Calificacion.valor.is_(None)).count()
        
        return jsonify({
            'success': True,
            'promedio_general': promedio_general,
            'total_asistencias': total_asistencias,
            'total_fallas': total_fallas,
            'total_retardos': total_retardos,
            'tareas_pendientes': tareas_pendientes
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
        if not verificar_relacion_padre_hijo(current_user.id_usuario, estudiante_id):
            return jsonify({'success': False, 'message': 'No tienes permisos'}), 403
        
        # Obtener calificaciones agrupadas por asignatura
        from sqlalchemy import func
        
        promedios_query = db.session.query(
            Asignatura.id_asignatura,
            Asignatura.nombre,
            func.avg(Calificacion.valor).label('promedio'),
            func.count(Calificacion.id_calificacion).label('num_calificaciones')
        ).join(
            Calificacion, Calificacion.asignaturaId == Asignatura.id_asignatura
        ).filter(
            Calificacion.estudianteId == estudiante_id,
            Calificacion.valor.isnot(None)
        ).group_by(
            Asignatura.id_asignatura, Asignatura.nombre
        ).all()
        
        promedios = []
        for asignatura_id, asignatura_nombre, promedio, num_calificaciones in promedios_query:
            if promedio is not None:
                promedios.append({
                    'asignatura_id': asignatura_id,
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

@padre_bp.route('/api/asistencia_mes/<int:estudiante_id>')
@login_required
@role_required('Padre')
def api_asistencia_mes(estudiante_id):
    """API para obtener asistencias de un estudiante por mes (para calendario)."""
    try:
        # Verificar que el estudiante pertenece al padre
        if not verificar_relacion_padre_hijo(current_user.id_usuario, estudiante_id):
            return jsonify({'success': False, 'message': 'No tienes permisos'}), 403
        
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        
        if not year or not month:
            from datetime import datetime
            now = datetime.now()
            year = now.year
            month = now.month
        
        # Obtener asistencias del mes con información de asignatura
        from datetime import datetime
        fecha_inicio = datetime(year, month, 1)
        if month == 12:
            fecha_fin = datetime(year + 1, 1, 1)
        else:
            fecha_fin = datetime(year, month + 1, 1)
        
        asistencias = db.session.query(
            Asistencia, Clase, Asignatura, Usuario, HorarioCurso, Salon
        ).join(
            Clase, Asistencia.claseId == Clase.id_clase
        ).join(
            Asignatura, Clase.asignaturaId == Asignatura.id_asignatura
        ).join(
            Usuario, Clase.profesorId == Usuario.id_usuario
        ).outerjoin(
            HorarioCurso, 
            db.and_(
                HorarioCurso.curso_id == Clase.cursoId,
                HorarioCurso.asignatura_id == Clase.asignaturaId
            )
        ).outerjoin(
            Salon, HorarioCurso.id_salon_fk == Salon.id_salon
        ).filter(
            Asistencia.estudianteId == estudiante_id,
            Asistencia.fecha >= fecha_inicio,
            Asistencia.fecha < fecha_fin
        ).order_by(Asistencia.fecha).all()
        
        # Agrupar por día
        asistencias_por_dia = {}
        for asistencia, clase, asignatura, profesor, horario_curso, salon in asistencias:
            fecha_key = asistencia.fecha.strftime('%Y-%m-%d')
            
            if fecha_key not in asistencias_por_dia:
                asistencias_por_dia[fecha_key] = []
            
            # Obtener hora del horario_curso si existe, sino usar valores por defecto
            hora_inicio = horario_curso.hora_inicio if horario_curso else '--'
            hora_fin = horario_curso.hora_fin if horario_curso else '--'
            salon_nombre = salon.nombre if salon else 'Sin asignar'
            
            asistencias_por_dia[fecha_key].append({
                'asignatura': asignatura.nombre,
                'estado': asistencia.estado,
                'excusa': asistencia.excusa if asistencia.excusa else False,
                'observaciones': getattr(asistencia, 'observaciones', ''),
                'hora_inicio': hora_inicio,
                'hora_fin': hora_fin,
                'profesor': profesor.nombre_completo if profesor else 'Sin asignar',
                'salon': salon_nombre
            })
        
        return jsonify({
            'success': True,
            'asistencias_por_dia': asistencias_por_dia
        })
        
    except Exception as e:
        current_app.logger.error(f"Error obteniendo asistencias del mes: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@padre_bp.route('/api/tareas_estudiante/<int:estudiante_id>')
@login_required
@role_required('Padre')
def api_tareas_estudiante(estudiante_id):
    """API para obtener tareas asignadas al estudiante."""
    try:
        # Verificar que el estudiante pertenece al padre
        if not verificar_relacion_padre_hijo(current_user.id_usuario, estudiante_id):
            return jsonify({'success': False, 'message': 'No tienes permisos'}), 403
        
        # Obtener tareas publicadas (calificaciones con es_tarea_publicada=True)
        tareas = db.session.query(
            Calificacion, Asignatura
        ).join(
            Asignatura, Calificacion.asignaturaId == Asignatura.id_asignatura
        ).filter(
            Calificacion.estudianteId == estudiante_id,
            Calificacion.es_tarea_publicada == True
        ).order_by(
            Calificacion.fecha_vencimiento.desc().nullslast(),
            Calificacion.fecha_registro.desc()
        ).all()
        
        current_app.logger.info(f"Buscando tareas para estudiante {estudiante_id}")
        current_app.logger.info(f"Tareas encontradas: {len(tareas)}")
        
        tareas_list = []
        for tarea, asignatura in tareas:
            tareas_list.append({
                'id_tarea': tarea.id_calificacion,
                'titulo': tarea.nombre_calificacion,
                'nombre_calificacion': tarea.nombre_calificacion,
                'asignatura': asignatura.nombre,
                'asignatura_id': asignatura.id_asignatura,
                'descripcion_tarea': tarea.descripcion_tarea,
                'fecha_vencimiento': tarea.fecha_vencimiento.isoformat() if tarea.fecha_vencimiento else None,
                'archivo_url': tarea.archivo_url,
                'archivo_nombre': tarea.archivo_nombre,
                'completada': tarea.valor is not None,
                'calificacion': float(tarea.valor) if tarea.valor else None,
                'fecha_registro': tarea.fecha_registro.isoformat() if tarea.fecha_registro else None
            })
        
        return jsonify({
            'success': True,
            'tareas': tareas_list
        })
        
    except Exception as e:
        current_app.logger.error(f"Error obteniendo tareas: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@padre_bp.route('/api/consultas_estudiante/<int:estudiante_id>')
@login_required
@role_required('Padre')
def api_consultas_estudiante(estudiante_id):
    """API para obtener consultas realizadas sobre un estudiante."""
    try:
        # Verificar que el estudiante pertenece al padre
        if not verificar_relacion_padre_hijo(current_user.id_usuario, estudiante_id):
            return jsonify({'success': False, 'message': 'No tienes permisos'}), 403
        
        # Obtener consultas del estudiante
        consultas = db.session.query(
            SolicitudConsulta, Asignatura, Usuario
        ).join(
            Asignatura, SolicitudConsulta.asignatura_id == Asignatura.id_asignatura
        ).join(
            Usuario, SolicitudConsulta.profesor_id == Usuario.id_usuario
        ).filter(
            SolicitudConsulta.estudiante_id == estudiante_id,
            SolicitudConsulta.padre_id == current_user.id_usuario
        ).order_by(
            SolicitudConsulta.fecha_solicitud.desc()
        ).all()
        
        consultas_list = []
        for consulta, asignatura, profesor in consultas:
            consultas_list.append({
                'id_solicitud': consulta.id_solicitud,
                'asignatura': asignatura.nombre,
                'asignatura_id': asignatura.id_asignatura,
                'profesor_nombre': profesor.nombre_completo,
                'justificacion': consulta.justificacion,
                'estado': consulta.estado,
                'respuesta_profesor': consulta.respuesta_profesor,
                'fecha_solicitud': consulta.fecha_solicitud.isoformat() if consulta.fecha_solicitud else None,
                'fecha_respuesta': consulta.fecha_respuesta.isoformat() if consulta.fecha_respuesta else None
            })
        
        return jsonify({
            'success': True,
            'consultas': consultas_list
        })
        
    except Exception as e:
        current_app.logger.error(f"Error obteniendo consultas: {e}")
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
            # Retornar estructura vacía para que el frontend muestre tabla vacía
            horario_data = {
                'curso': None,
                'sede': 'N/A',
                'clases': {}
            }
            return jsonify({
                'success': True,
                'horario': horario_data,
                'message': 'El estudiante no tiene matrícula activa'
            })
        
        curso = matricula.curso
        
        # Helpers para normalizar día y hora al formato esperado por el frontend
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
                # soporta time, datetime o string
                if hasattr(val, 'strftime'):
                    return val.strftime('%H:%M')
                s = str(val).strip()
                # Si viene como HH:MM:SS -> tomar HH:MM
                if len(s) >= 5 and s[2] == ':':
                    return s[:5]
                # Si viene como H:MM -> normalizar a HH:MM
                if ':' in s:
                    parts = s.split(':')
                    h = int(parts[0]) if parts[0] else 0
                    m = int(parts[1]) if len(parts) > 1 and parts[1] else 0
                    return f"{h:02d}:{m:02d}"
                # Intentar parseo directo
                from datetime import datetime
                try:
                    return datetime.strptime(s, '%H:%M').strftime('%H:%M')
                except Exception:
                    pass
            except Exception:
                pass
            return ''

        # Construir a partir de HorarioCurso (fuente con día/hora)
        clases = {}

        # Complementar con HorarioCurso (usado por profesor/estudiante)
        horarios_curso = db.session.query(HorarioCurso, Asignatura, Usuario, Salon).join(
            Asignatura, HorarioCurso.asignatura_id == Asignatura.id_asignatura
        ).join(
            Usuario, HorarioCurso.profesor_id == Usuario.id_usuario
        ).outerjoin(
            Salon, HorarioCurso.id_salon_fk == Salon.id_salon
        ).filter(
            HorarioCurso.curso_id == curso.id_curso
        ).all()

        for hc, asignatura, profesor, salon in horarios_curso:
            dia_norm = _normalizar_dia(getattr(hc, 'dia_semana', None))
            hora_ini = _fmt_hora(getattr(hc, 'hora_inicio', ''))
            hora_fin = _fmt_hora(getattr(hc, 'hora_fin', ''))
            if not dia_norm or not hora_ini:
                continue
            # Expandir a todos los bloques de hora completa cubiertos por el rango [inicio, fin)
            def _to_min(hhmm):
                try:
                    h, m = map(int, hhmm.split(':'))
                    return h*60 + m
                except Exception:
                    return None
            ini_min = _to_min(hora_ini)
            fin_min = _to_min(hora_fin) if hora_fin else None
            if ini_min is None:
                continue
            # Si no hay hora_fin válida, sólo marcar la hora de inicio
            slots = []
            if fin_min is None or fin_min <= ini_min:
                slots = [hora_ini]
            else:
                # tomar horas enteras desde floor(inicio a la hora) hasta fin exclusiva, paso 60
                from math import floor
                start_hour = ini_min // 60
                end_hour = (fin_min + 59) // 60  # cubrir la última hora iniciada antes de fin
                for h in range(start_hour, end_hour):
                    slots.append(f"{h:02d}:00")
            for slot in slots:
                clave = f"{dia_norm}_{slot}"
                if clave not in clases:
                    clases[clave] = {
                        'asignatura': asignatura.nombre,
                        'profesor': profesor.nombre_completo,
                        'salon': salon.nombre if salon else 'N/A',
                        'hora_inicio': hora_ini,
                        'hora_fin': hora_fin or 'N/A'
                    }

        # Incorporar bloques y días desde HorarioGeneral (para mostrar rangos y descansos)
        dias_list = []
        bloques_list = []
        matriz_bloques = {}  # dia -> { "HH:MM-HH:MM": {tipo, nombre} }
        clases_por_bloque = {}  # dia -> { "HH:MM-HH:MM": clase }
        try:
            hg = getattr(curso, 'horario_general', None)
            if hg:
                # Días
                try:
                    import json
                    dias_list = json.loads(hg.diasSemana) if hg.diasSemana else []
                except Exception:
                    dias_list = []
                # Bloques
                from controllers.models import BloqueHorario
                bloques = BloqueHorario.query.filter_by(horario_general_id=hg.id_horario).order_by(BloqueHorario.orden).all()
                for b in bloques:
                    dia_norm_b = _normalizar_dia(b.dia_semana)
                    start = _fmt_hora(b.horaInicio)
                    end = _fmt_hora(b.horaFin)
                    if not start or not end:
                        continue
                    bloque_key = f"{start}-{end}"
                    if bloque_key not in bloques_list:
                        bloques_list.append(bloque_key)
                    if dia_norm_b:
                        matriz_bloques.setdefault(dia_norm_b, {})[bloque_key] = {
                            'tipo': (b.tipo or '').lower(),
                            'nombre': b.nombre or '',
                            'break_type': (b.break_type or ''),
                            'class_type': (b.class_type or '')
                        }
                        clases_por_bloque.setdefault(dia_norm_b, {})[bloque_key] = None
        except Exception:
            pass

        # Determinar sede del curso
        sede_nombre = 'N/A'
        try:
            if hasattr(curso, 'sede') and curso.sede:
                sede_nombre = curso.sede.nombre
            elif hasattr(curso, 'sedeId') and curso.sedeId:
                sede_obj = Sede.query.get(curso.sedeId)
                if sede_obj:
                    sede_nombre = sede_obj.nombre
        except Exception:
            pass

        # Construir clases_por_bloque: asignar cada HorarioCurso a los bloques que se solapan
        def _minutos(hhmm):
            try:
                h, m = map(int, str(hhmm).split(':'))
                return h*60 + m
            except Exception:
                return None

        for hc, asignatura, profesor, salon in horarios_curso:
            dia_norm = _normalizar_dia(getattr(hc, 'dia_semana', None))
            ini = _fmt_hora(getattr(hc, 'hora_inicio', ''))
            fin = _fmt_hora(getattr(hc, 'hora_fin', ''))
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
                # Solapamiento si max(inicio) < min(fin)
                if max(ini_m, b_ini_m) < min(fin_m, b_fin_m):
                    # Evitar marcar bloques de descanso como clase
                    if meta.get('tipo', '') in ('break','descanso','receso'):
                        continue
                    clases_por_bloque[dia_norm][bloque_key] = {
                        'asignatura': asignatura.nombre,
                        'profesor': profesor.nombre_completo,
                        'salon': salon.nombre if salon else 'N/A',
                        'hora_inicio': ini,
                        'hora_fin': fin
                    }

        horario_data = {
            'curso': getattr(curso, 'nombreCurso', 'N/A'),
            'sede': sede_nombre,
            'clases': clases,
            'dias': dias_list,
            'bloques': bloques_list,
            'matriz_bloques': matriz_bloques,
            'clases_por_bloque': clases_por_bloque
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
    from datetime import datetime

    # Verificar que el estudiante sea hijo del padre
    if not verificar_relacion_padre_hijo(current_user.id_usuario, estudiante_id):
        flash('No tienes permisos para ver las calificaciones de este estudiante', 'error')
        return redirect(url_for('padre.consultar_estudiante'))
    
    estudiante = Usuario.query.get(estudiante_id)
    
    # Obtener calificaciones del estudiante en la asignatura
    calificaciones = Calificacion.query.filter_by(
        estudianteId=estudiante_id,
        asignaturaId=asignatura_id
    ).order_by(Calificacion.fecha_registro.desc()).all()
    
    # Obtener la última fecha de registro de calificaciones
    ultima_fecha_reporte = None
    if calificaciones:
        for cal in calificaciones:
            if cal.fecha_registro:
                ultima_fecha_reporte = cal.fecha_registro
                break
    
    # Obtener TODAS las categorías de calificación
    categorias = CategoriaCalificacion.query.all()
    
    # Organizar calificaciones por categoría (TODAS las categorías, incluso sin calificaciones)
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
    
    # Calcular promedio general (solo de categorías con calificaciones)
    promedios_con_valores = [p for p in promedios_por_categoria.values() if p > 0]
    if promedios_con_valores:
        promedio_general = sum(promedios_con_valores) / len(promedios_con_valores)
    else:
        promedio_general = 0
    
    # OBTENER CONTADORES DEL SIDEBAR
    counts = get_sidebar_counts()
    
    return render_template('padres/calificaciones_estudiante.html',
                         estudiante=estudiante,
                         asignatura=Asignatura.query.get(asignatura_id),
                         calificaciones_por_categoria=calificaciones_por_categoria,
                         promedios_por_categoria=promedios_por_categoria,
                         promedio_general=promedio_general,
                         ultima_fecha_reporte=ultima_fecha_reporte,
                         # ✅ VARIABLES CORREGIDAS PARA EL TEMPLATE BASE
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])

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

# ============================================================================
# RUTAS API - PERIODOS ACADÉMICOS
# ============================================================================

@padre_bp.route('/api/periodo-activo', methods=['GET'])
@login_required
@role_required('Padre')
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

@padre_bp.route('/api/periodos', methods=['GET'])
@login_required
@role_required('Padre')
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

@padre_bp.route('/api/hijo/<int:hijo_id>/calificaciones', methods=['GET'])
@login_required
@role_required('Padre')
def api_calificaciones_hijo_por_periodo(hijo_id):
    """API para obtener calificaciones de un hijo, opcionalmente filtradas por periodo."""
    try:
        # Verificar relación padre-hijo
        if not verificar_relacion_padre_hijo(current_user.id_usuario, hijo_id):
            return jsonify({
                'success': False,
                'message': 'No autorizado para ver las calificaciones de este estudiante'
            }), 403
        
        periodo_id = request.args.get('periodo_id', type=int)
        
        # Construir query base
        query = Calificacion.query.filter_by(estudianteId=hijo_id)
        
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

@padre_bp.route('/api/hijo/<int:hijo_id>/asistencias', methods=['GET'])
@login_required
@role_required('Padre')
def api_asistencias_hijo_por_periodo(hijo_id):
    """API para obtener asistencias de un hijo, opcionalmente filtradas por periodo."""
    try:
        # Verificar relación padre-hijo
        if not verificar_relacion_padre_hijo(current_user.id_usuario, hijo_id):
            return jsonify({
                'success': False,
                'message': 'No autorizado para ver las asistencias de este estudiante'
            }), 403
        
        periodo_id = request.args.get('periodo_id', type=int)
        
        # Construir query base
        query = Asistencia.query.filter_by(estudianteId=hijo_id)
        
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

@padre_bp.route('/tareas/<int:hijo_id>')
@login_required
@role_required('Padre')
def ver_tareas_hijo(hijo_id):
    """Vista para que el padre vea las tareas de su hijo/a."""
    try:
        # Verificar relación padre-hijo
        if not verificar_relacion_padre_hijo(current_user.id_usuario, hijo_id):
            flash('No tienes autorización para ver las tareas de este estudiante', 'error')
            return redirect(url_for('padre.dashboard'))
        
        hijo = Usuario.query.get_or_404(hijo_id)
        
        # Obtener el curso del hijo
        matricula = Matricula.query.filter_by(estudianteId=hijo_id).first()
        
        if not matricula:
            flash('El estudiante no está matriculado en ningún curso', 'warning')
            return redirect(url_for('padre.dashboard'))
        
        curso = Curso.query.get(matricula.cursoId)
        
        # OBTENER CONTADORES DEL SIDEBAR
        counts = get_sidebar_counts()
        
        return render_template('padres/tareas.html', 
                             hijo=hijo, 
                             curso=curso,
                             # ✅ VARIABLES CORREGIDAS PARA EL TEMPLATE BASE
                             unread_messages=counts['unread_messages'],
                             unread_notifications=counts['unread_notifications'],
                             upcoming_events=counts['upcoming_events'])
    
    except Exception as e:
        flash(f'Error al cargar tareas: {str(e)}', 'error')
        return redirect(url_for('padre.dashboard'))

@padre_bp.route('/tareas/<int:hijo_id>/<int:tarea_id>')
@login_required
@role_required('Padre')
def ver_detalle_tarea_hijo(hijo_id, tarea_id):
    """Vista para que el padre vea el detalle de una tarea de su hijo/a."""
    try:
        # Verificar relación padre-hijo
        if not verificar_relacion_padre_hijo(current_user.id_usuario, hijo_id):
            flash('No tienes autorización para ver esta información', 'error')
            return redirect(url_for('padre.dashboard'))
        
        hijo = Usuario.query.get_or_404(hijo_id)
        tarea = TareaAcademica.query.get_or_404(tarea_id)
        
        # Verificar que el hijo esté en el curso de la tarea
        matricula = Matricula.query.filter_by(
            estudianteId=hijo_id,
            cursoId=tarea.curso_id
        ).first()
        
        if not matricula:
            flash('El estudiante no tiene acceso a esta tarea', 'error')
            return redirect(url_for('padre.ver_tareas_hijo', hijo_id=hijo_id))
        
        # OBTENER CONTADORES DEL SIDEBAR
        counts = get_sidebar_counts()
        
        return render_template('padres/detalle_tarea.html', 
                             hijo=hijo, 
                             tarea=tarea,
                             # ✅ VARIABLES CORREGIDAS PARA EL TEMPLATE BASE
                             unread_messages=counts['unread_messages'],
                             unread_notifications=counts['unread_notifications'],
                             upcoming_events=counts['upcoming_events'])
    
    except Exception as e:
        flash(f'Error al cargar tarea: {str(e)}', 'error')
        return redirect(url_for('padre.ver_tareas_hijo', hijo_id=hijo_id))

@padre_bp.route('/api/hijo/<int:hijo_id>/tareas', methods=['GET'])
@login_required
@role_required('Padre')
def api_tareas_hijo(hijo_id):
    """
    Obtiene todas las tareas publicadas de un hijo específico.
    """
    try:
        # Verificar relación padre-hijo
        if not verificar_relacion_padre_hijo(current_user.id_usuario, hijo_id):
            return jsonify({
                'success': False,
                'message': 'No autorizado para ver las tareas de este estudiante'
            }), 403
        
        # Consultar tareas del hijo
        tareas = Calificacion.query.filter_by(
            estudianteId=hijo_id,
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

@padre_bp.route('/api/hijo/<int:hijo_id>/tareas/<int:tarea_id>', methods=['GET'])
@login_required
@role_required('Padre')
def api_obtener_tarea_hijo(hijo_id, tarea_id):
    """
    Obtiene el detalle completo de una tarea específica de un hijo.
    """
    try:
        # Verificar relación padre-hijo
        if not verificar_relacion_padre_hijo(current_user.id_usuario, hijo_id):
            return jsonify({
                'success': False,
                'message': 'No autorizado para ver esta información'
            }), 403
        
        # Buscar la tarea
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
        
        # Verificar que la tarea pertenezca al hijo
        if tarea.estudianteId != hijo_id:
            return jsonify({
                'success': False,
                'message': 'La tarea no pertenece a este estudiante'
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


  # ========== SERVICIO DE NOTIFICACIONES AUTOMÁTICAS ==========
def crear_notificacion_evento_padres(evento):
    """Crear notificaciones para todos los padres cuando se publica un nuevo evento"""
    try:
        from sqlalchemy import text
        
        # Buscar todos los padres usando la tabla estudiante_padre
        padres_query = db.session.execute(text("""
            SELECT DISTINCT padre_id 
            FROM estudiante_padre
        """))
        
        padres_ids = [row[0] for row in padres_query]
        
        for padre_id in padres_ids:
            notificacion = Notificacion(
                usuario_id=padre_id,
                titulo=f"📅 Nuevo evento: {evento.nombre}",
                mensaje=f"{evento.descripcion}. Fecha: {evento.fecha.strftime('%d/%m/%Y')} a las {evento.hora.strftime('%H:%M')}",
                tipo="evento",
                leida=False,
                link="/padre/eventos"
            )
            db.session.add(notificacion)
        
        db.session.commit()
        print(f"✅ Notificaciones de evento creadas para {len(padres_ids)} padres")
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error creando notificaciones: {e}")
        return False

def crear_notificacion_general(usuario_id, titulo, mensaje, tipo="sistema", link=None):
    """Crear una notificación general para un usuario específico"""
    try:
        notificacion = Notificacion(
            usuario_id=usuario_id,
            titulo=titulo,
            mensaje=mensaje,
            tipo=tipo,
            leida=False,
            link=link
        )
        db.session.add(notificacion)
        db.session.commit()
        print(f"✅ Notificación creada para usuario {usuario_id}")
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error creando notificación: {e}")
        return False
# ========== FIN SERVICIO DE NOTIFICACIONES ==========

# ========== RUTAS PARA PADRES ==========
@padre_bp.route("/api/sidebar/contadores")
@login_required
@role_required('Padre')
def api_sidebar_contadores():
    """API para obtener los contadores del sidebar"""
    try:
        counts = get_sidebar_counts()
        return jsonify({
            'success': True,
            'unread_messages': counts['unread_messages'],
            'unread_notifications': counts['unread_notifications'],
            'upcoming_events': counts['upcoming_events']
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': str(e),
            'unread_messages': 0,
            'unread_notifications': 0,
            'upcoming_events': 0
        })

@padre_bp.route("/api/eventos/crear", methods=["POST"])
@login_required
@role_required('Padre')
def crear_evento_con_notificacion():
    """Crear un nuevo evento y notificar a los padres"""
    try:
        from datetime import datetime
        data = request.get_json()
        
        # Crear el evento
        nuevo_evento = Evento(
            nombre=data['nombre'],
            descripcion=data['descripcion'],
            fecha=datetime.strptime(data['fecha'], '%Y-%m-%d').date(),
            hora=datetime.strptime(data['hora'], '%H:%M').time(),
            rol_destino="Estudiante"
        )
        
        db.session.add(nuevo_evento)
        db.session.commit()
        
        # Crear notificaciones para todos los padres
        crear_notificacion_evento_padres(nuevo_evento)
        
        return jsonify({
            "success": True,
            "message": "Evento creado y notificaciones enviadas",
            "evento_id": nuevo_evento.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@padre_bp.route("/eventos", methods=["GET"])
@login_required
@role_required('Padre')
def ver_eventos():
    """Vista del calendario de eventos para padres"""
    counts = get_sidebar_counts()
    return render_template("padres/calendario/index.html",
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])

@padre_bp.route('/api/eventos/contador')
@login_required
@role_required('Padre')
def api_eventos_contador():
    """API para obtener el contador de eventos próximos"""
    try:
        from datetime import datetime
        hoy = datetime.now().date()
        count = Evento.query.filter(
            Evento.fecha.isnot(None),
            Evento.fecha >= hoy
        ).count()
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        return jsonify({'success': False, 'count': 0})

@padre_bp.route("/api/eventos", methods=["GET"])
@login_required
@role_required('Padre')
def api_eventos_padre():
    """API para listar eventos del rol estudiante"""
    try:
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

@padre_bp.route("/api/notificaciones")
@login_required
@role_required('Padre')
def api_obtener_notificaciones_padre():
    """API para obtener notificaciones del padre con paginación"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        filtro = request.args.get('filtro', 'todas')
        
        query = Notificacion.query.filter_by(usuario_id=current_user.id_usuario)
        
        if filtro == 'pendientes':
            query = query.filter_by(leida=False)
        elif filtro == 'leidas':
            query = query.filter_by(leida=True)
        
        pagination = query.order_by(Notificacion.creada_en.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        notificaciones_data = []
        for notif in pagination.items:
            notificaciones_data.append({
                "id": notif.id_notificacion,
                "titulo": notif.titulo,
                "mensaje": notif.mensaje,
                "tipo": notif.tipo,
                "leida": notif.leida,
                "link": notif.link,
                "fecha_creacion": notif.creada_en.strftime('%d/%m/%Y %H:%M') if notif.creada_en else 'Reciente',
                "creada_en": notif.creada_en.isoformat() if notif.creada_en else None
            })
        
        return jsonify({
            "success": True,
            "data": {
                "notificaciones": notificaciones_data,
                "total": pagination.total,
                "pages": pagination.pages,
                "current_page": pagination.page,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@padre_bp.route("/api/notificaciones/marcar-leidas", methods=["POST"])
@login_required
@role_required('Padre')
def api_marcar_notificaciones_leidas_padre():
    """Marcar notificaciones como leídas"""
    try:
        data = request.get_json()
        notificacion_ids = data.get('notificacion_ids', [])
        
        if notificacion_ids:
            Notificacion.query.filter(
                Notificacion.id_notificacion.in_(notificacion_ids),
                Notificacion.usuario_id == current_user.id_usuario
            ).update({"leida": True})
        else:
            Notificacion.query.filter_by(
                usuario_id=current_user.id_usuario,
                leida=False
            ).update({"leida": True})
        
        db.session.commit()
        return jsonify({"success": True}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@padre_bp.route("/api/notificaciones/eliminar", methods=["POST"])
@login_required
@role_required('Padre')
def api_eliminar_notificaciones_padre():
    """Eliminar notificaciones"""
    try:
        data = request.get_json()
        notificacion_ids = data.get('notificacion_ids', [])
        eliminar_todas = data.get('eliminar_todas', False)
        
        if eliminar_todas:
            Notificacion.query.filter_by(usuario_id=current_user.id_usuario).delete()
        elif notificacion_ids:
            Notificacion.query.filter(
                Notificacion.id_notificacion.in_(notificacion_ids),
                Notificacion.usuario_id == current_user.id_usuario
            ).delete()
        
        db.session.commit()
        return jsonify({"success": True}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

def get_sidebar_counts():
    """Función auxiliar para obtener los contadores del sidebar"""
    from datetime import datetime
    
    try:
        estados = db.session.query(Comunicacion.estado).distinct().all()
        estados_lista = [e[0] for e in estados]
        
        estado_no_leido = 'inbox'
        if 'no_leido' in estados_lista:
            estado_no_leido = 'no_leido'
        elif 'unread' in estados_lista:
            estado_no_leido = 'unread'
        elif 'pendiente' in estados_lista:
            estado_no_leido = 'pendiente'
        elif 'nuevo' in estados_lista:
            estado_no_leido = 'nuevo'
        
        # Mensajes no leídos
        unread_messages = Comunicacion.query.filter_by(
            destinatario_id=current_user.id_usuario, 
            estado=estado_no_leido
        ).count()
        
        # Notificaciones no leídas
        unread_notifications = Notificacion.query.filter_by(
            usuario_id=current_user.id_usuario,
            leida=False
        ).count()
        
        # Eventos próximos
        hoy = datetime.now().date()
        eventos_proximos = Evento.query.filter(Evento.fecha >= hoy).all()
        upcoming_events = len(eventos_proximos)
        
        return {
            'unread_messages': unread_messages,
            'unread_notifications': unread_notifications,
            'upcoming_events': upcoming_events
        }
        
    except Exception as e:
        print(f"❌ Error en get_sidebar_counts: {e}")
        return {
            'unread_messages': 0,
            'unread_notifications': 0,
            'upcoming_events': 0
        }