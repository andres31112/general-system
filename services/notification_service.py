from flask import current_app
from controllers.models import db, Notificacion, Usuario
from datetime import datetime

def crear_notificacion(usuario_id, titulo, mensaje, tipo='general', link=None):
    """Crea una nueva notificación para un usuario."""
    try:
        notificacion = Notificacion(
            usuario_id=usuario_id,
            titulo=titulo,
            mensaje=mensaje,
            tipo=tipo,
            link=link,
            leida=False
        )
        
        db.session.add(notificacion)
        db.session.commit()
        
        return notificacion
    except Exception as e:
        db.session.rollback()
        print(f"Error creando notificación: {str(e)}")
        return None

def notificar_respuesta_solicitud(solicitud):
    """Envía notificación al padre cuando el profesor responde a una solicitud."""
    try:
        if solicitud.estado == 'aceptada':
            titulo = "✅ Solicitud de Calificaciones Aceptada"
            mensaje = f"El profesor {solicitud.profesor.nombre_completo} ha aceptado tu solicitud para revisar las calificaciones de {solicitud.nombre_completo_hijo} en {solicitud.asignatura.nombre}."
            link = f"/padre/ver_calificaciones_estudiante/{solicitud.estudiante_id}/{solicitud.asignatura_id}"
        else:
            titulo = "❌ Solicitud de Calificaciones Denegada"
            mensaje = f"El profesor {solicitud.profesor.nombre_completo} ha denegado tu solicitud para revisar las calificaciones de {solicitud.nombre_completo_hijo} en {solicitud.asignatura.nombre}."
            if solicitud.respuesta_profesor:
                mensaje += f"\n\nComentario del profesor: {solicitud.respuesta_profesor}"
            link = "/padre/consultar_estudiante"
        
        return crear_notificacion(
            usuario_id=solicitud.padre_id,
            titulo=titulo,
            mensaje=mensaje,
            tipo='solicitud',
            link=link
        )
    except Exception as e:
        print(f"Error notificando respuesta de solicitud: {str(e)}")
        return None

def notificar_nueva_solicitud(solicitud):
    """Envía notificación al profesor cuando llega una nueva solicitud."""
    try:
        titulo = "📋 Nueva Solicitud de Consulta de Calificaciones"
        mensaje = f"El padre {solicitud.padre.nombre_completo} ha solicitado revisar las calificaciones de {solicitud.nombre_completo_hijo} en {solicitud.asignatura.nombre}."
        link = "/profesor/solicitudes"
        
        return crear_notificacion(
            usuario_id=solicitud.profesor_id,
            titulo=titulo,
            mensaje=mensaje,
            tipo='solicitud',
            link=link
        )
    except Exception as e:
        print(f"Error notificando nueva solicitud: {str(e)}")
        return None

def obtener_notificaciones_no_leidas(usuario_id):
    """Obtiene las notificaciones no leídas de un usuario."""
    try:
        return Notificacion.query.filter_by(
            usuario_id=usuario_id,
            leida=False
        ).order_by(Notificacion.creada_en.desc()).all()
    except Exception as e:
        print(f"Error obteniendo notificaciones: {str(e)}")
        return []

def contar_notificaciones_no_leidas(usuario_id):
    """Cuenta las notificaciones no leídas de un usuario."""
    try:
        return Notificacion.query.filter_by(
            usuario_id=usuario_id,
            leida=False
        ).count()
    except Exception as e:
        print(f"Error contando notificaciones: {str(e)}")
        return 0

def marcar_notificacion_como_leida(notificacion_id, usuario_id):
    """Marca una notificación como leída."""
    try:
        notificacion = Notificacion.query.filter_by(
            id_notificacion=notificacion_id,
            usuario_id=usuario_id
        ).first()
        
        if notificacion:
            notificacion.leida = True
            db.session.commit()
            return True
        return False
    except Exception as e:
        db.session.rollback()
        print(f"Error marcando notificación como leída: {str(e)}")
        return False

def obtener_todas_notificaciones(usuario_id, limite=50):
    """Obtiene todas las notificaciones de un usuario."""
    try:
        return Notificacion.query.filter_by(
            usuario_id=usuario_id
        ).order_by(Notificacion.creada_en.desc()).limit(limite).all()
    except Exception as e:
        print(f"Error obteniendo todas las notificaciones: {str(e)}")
        return []
