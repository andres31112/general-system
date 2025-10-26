"""
Servicio para gestión de Ciclos y Periodos Académicos
"""

from datetime import datetime, timedelta, date
from controllers.models import db, CicloAcademico, PeriodoAcademico, Matricula, Calificacion, Asistencia
from sqlalchemy import and_, func


def crear_ciclo_academico(nombre, fecha_inicio, fecha_fin):
    """
    Crea un nuevo ciclo académico
    
    Args:
        nombre (str): Nombre del ciclo (ej: "Año Escolar 2024-2025")
        fecha_inicio (date): Fecha de inicio del ciclo
        fecha_fin (date): Fecha de fin del ciclo
    
    Returns:
        tuple: (ciclo, error)
    """
    try:
        # Validar que no haya otro ciclo activo
        ciclo_activo = CicloAcademico.query.filter_by(activo=True).first()
        if ciclo_activo:
            return None, f"Ya existe un ciclo activo: {ciclo_activo.nombre}"
        
        # Validar fechas
        if fecha_inicio >= fecha_fin:
            return None, "La fecha de inicio debe ser anterior a la fecha de fin"
        
        # Crear el ciclo
        ciclo = CicloAcademico(
            nombre=nombre,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado='planificado',
            activo=False
        )
        
        db.session.add(ciclo)
        db.session.commit()
        
        return ciclo, None
        
    except Exception as e:
        db.session.rollback()
        return None, f"Error creando ciclo académico: {str(e)}"


def crear_periodo(ciclo_id, numero_periodo, nombre, fecha_inicio, fecha_fin, fecha_cierre_notas, dias_notificacion=7):
    """
    Crea un nuevo periodo académico dentro de un ciclo
    
    Args:
        ciclo_id (int): ID del ciclo académico
        numero_periodo (int): Número del periodo (1, 2, 3)
        nombre (str): Nombre del periodo (ej: "Primer Trimestre")
        fecha_inicio (date): Fecha de inicio del periodo
        fecha_fin (date): Fecha de fin del periodo
        fecha_cierre_notas (date): Fecha límite para cerrar notas
        dias_notificacion (int): Días de anticipación para notificaciones
    
    Returns:
        tuple: (periodo, error)
    """
    try:
        # Validar que el ciclo existe
        ciclo = CicloAcademico.query.get(ciclo_id)
        if not ciclo:
            return None, "Ciclo académico no encontrado"
        
        # Validar que el periodo esté dentro del ciclo
        if fecha_inicio < ciclo.fecha_inicio or fecha_fin > ciclo.fecha_fin:
            return None, "El periodo debe estar dentro de las fechas del ciclo"
        
        # Validar fechas
        if fecha_inicio >= fecha_fin:
            return None, "La fecha de inicio debe ser anterior a la fecha de fin"
        
        if fecha_cierre_notas > fecha_fin:
            return None, "La fecha de cierre de notas debe ser anterior o igual a la fecha de fin"
        
        # Validar que no haya solapamiento con otros periodos
        periodos_existentes = PeriodoAcademico.query.filter_by(ciclo_academico_id=ciclo_id).all()
        for periodo_existente in periodos_existentes:
            if (fecha_inicio <= periodo_existente.fecha_fin and fecha_fin >= periodo_existente.fecha_inicio):
                return None, f"El periodo se solapa con: {periodo_existente.nombre}"
        
        # Crear el periodo
        periodo = PeriodoAcademico(
            ciclo_academico_id=ciclo_id,
            numero_periodo=numero_periodo,
            nombre=nombre,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            fecha_cierre_notas=fecha_cierre_notas,
            dias_notificacion_anticipada=dias_notificacion,
            estado='planificado'
        )
        
        db.session.add(periodo)
        db.session.commit()
        
        return periodo, None
        
    except Exception as e:
        db.session.rollback()
        return None, f"Error creando periodo: {str(e)}"


def activar_ciclo(ciclo_id):
    """
    Activa un ciclo académico y su primer periodo
    
    Args:
        ciclo_id (int): ID del ciclo a activar
    
    Returns:
        tuple: (success, error)
    """
    try:
        # Obtener el ciclo
        ciclo = CicloAcademico.query.get(ciclo_id)
        if not ciclo:
            return False, "Ciclo no encontrado"
        
        # Validar que tenga al menos un periodo
        if len(ciclo.periodos) == 0:
            return False, "El ciclo debe tener al menos un periodo configurado"
        
        # Desactivar cualquier ciclo activo
        CicloAcademico.query.filter_by(activo=True).update({'activo': False, 'estado': 'cerrado'})
        
        # Activar el ciclo
        ciclo.activo = True
        ciclo.estado = 'activo'
        
        # Activar el primer periodo
        primer_periodo = PeriodoAcademico.query.filter_by(
            ciclo_academico_id=ciclo_id,
            numero_periodo=1
        ).first()
        
        if primer_periodo:
            primer_periodo.estado = 'activo'
        
        db.session.commit()
        
        # Programar notificaciones
        from services.notification_service import notificar_inicio_ciclo
        notificar_inicio_ciclo(ciclo_id)
        
        return True, None
        
    except Exception as e:
        db.session.rollback()
        return False, f"Error activando ciclo: {str(e)}"


def obtener_ciclo_activo():
    """
    Obtiene el ciclo académico activo actual
    
    Returns:
        CicloAcademico: Ciclo activo o None
    """
    return CicloAcademico.query.filter_by(activo=True).first()


def obtener_periodo_activo():
    """
    Obtiene el periodo académico activo actual
    
    Returns:
        PeriodoAcademico: Periodo activo o None
    """
    ciclo_activo = obtener_ciclo_activo()
    if not ciclo_activo:
        return None
    
    return PeriodoAcademico.query.filter_by(
        ciclo_academico_id=ciclo_activo.id_ciclo,
        estado='activo'
    ).first()


def cerrar_periodo(periodo_id):
    """
    Cierra un periodo académico
    
    Args:
        periodo_id (int): ID del periodo a cerrar
    
    Returns:
        tuple: (success, error)
    """
    try:
        periodo = PeriodoAcademico.query.get(periodo_id)
        if not periodo:
            return False, "Periodo no encontrado"
        
        # Validar que esté activo
        if periodo.estado != 'activo':
            return False, "Solo se pueden cerrar periodos activos"
        
        # Validar que todas las notas estén completas
        validacion_ok, mensaje = validar_notas_completas(periodo_id)
        if not validacion_ok:
            return False, mensaje
        
        # Cerrar el periodo
        periodo.estado = 'cerrado'
        
        # Activar el siguiente periodo si existe
        siguiente_periodo = PeriodoAcademico.query.filter_by(
            ciclo_academico_id=periodo.ciclo_academico_id,
            numero_periodo=periodo.numero_periodo + 1
        ).first()
        
        if siguiente_periodo:
            siguiente_periodo.estado = 'activo'
        
        db.session.commit()
        
        # Notificar cierre
        from services.notification_service import notificar_cierre_periodo
        notificar_cierre_periodo(periodo_id)
        
        # Generar reportes del periodo
        from services.reporte_service import generar_reporte_periodo
        generar_reporte_periodo(periodo_id)
        
        return True, None
        
    except Exception as e:
        db.session.rollback()
        return False, f"Error cerrando periodo: {str(e)}"


def validar_notas_completas(periodo_id):
    """
    Valida que todas las notas del periodo estén completas
    
    Args:
        periodo_id (int): ID del periodo
    
    Returns:
        tuple: (es_valido, mensaje)
    """
    try:
        # Contar calificaciones sin valor (NULL)
        calificaciones_incompletas = Calificacion.query.filter(
            Calificacion.periodo_academico_id == periodo_id,
            Calificacion.valor == None
        ).count()
        
        if calificaciones_incompletas > 0:
            return False, f"Hay {calificaciones_incompletas} calificaciones sin valor. Complete todas las notas antes de cerrar."
        
        return True, "Todas las notas están completas"
        
    except Exception as e:
        return False, f"Error validando notas: {str(e)}"


def activar_siguiente_periodo(ciclo_id, periodo_actual_numero):
    """
    Activa el siguiente periodo del ciclo
    
    Args:
        ciclo_id (int): ID del ciclo
        periodo_actual_numero (int): Número del periodo actual
    
    Returns:
        tuple: (success, error)
    """
    try:
        siguiente_periodo = PeriodoAcademico.query.filter_by(
            ciclo_academico_id=ciclo_id,
            numero_periodo=periodo_actual_numero + 1
        ).first()
        
        if not siguiente_periodo:
            return False, "No hay más periodos en este ciclo"
        
        siguiente_periodo.estado = 'activo'
        db.session.commit()
        
        # Notificar inicio del nuevo periodo
        from services.notification_service import notificar_inicio_periodo
        notificar_inicio_periodo(siguiente_periodo.id_periodo)
        
        return True, None
        
    except Exception as e:
        db.session.rollback()
        return False, f"Error activando siguiente periodo: {str(e)}"


def obtener_periodos_ciclo(ciclo_id):
    """
    Obtiene todos los periodos de un ciclo
    
    Args:
        ciclo_id (int): ID del ciclo
    
    Returns:
        list: Lista de periodos ordenados por número
    """
    return PeriodoAcademico.query.filter_by(
        ciclo_academico_id=ciclo_id
    ).order_by(PeriodoAcademico.numero_periodo).all()


def obtener_todos_los_ciclos():
    """
    Obtiene todos los ciclos académicos
    
    Returns:
        list: Lista de ciclos ordenados por fecha de creación (más reciente primero)
    """
    return CicloAcademico.query.order_by(CicloAcademico.fecha_creacion.desc()).all()


def actualizar_periodo(periodo_id, datos):
    """
    Actualiza los datos de un periodo
    
    Args:
        periodo_id (int): ID del periodo
        datos (dict): Diccionario con los campos a actualizar
    
    Returns:
        tuple: (periodo, error)
    """
    try:
        periodo = PeriodoAcademico.query.get(periodo_id)
        if not periodo:
            return None, "Periodo no encontrado"
        
        # No permitir modificar si está cerrado
        if periodo.estado == 'cerrado':
            return None, "No se puede modificar un periodo cerrado"
        
        # Actualizar campos permitidos
        campos_permitidos = ['nombre', 'fecha_inicio', 'fecha_fin', 'fecha_cierre_notas', 'dias_notificacion_anticipada']
        for campo in campos_permitidos:
            if campo in datos:
                setattr(periodo, campo, datos[campo])
        
        db.session.commit()
        return periodo, None
        
    except Exception as e:
        db.session.rollback()
        return None, f"Error actualizando periodo: {str(e)}"


def eliminar_periodo(periodo_id):
    """
    Elimina un periodo académico
    
    Args:
        periodo_id (int): ID del periodo
    
    Returns:
        tuple: (success, error)
    """
    try:
        periodo = PeriodoAcademico.query.get(periodo_id)
        if not periodo:
            return False, "Periodo no encontrado"
        
        # No permitir eliminar si está activo o cerrado
        if periodo.estado in ['activo', 'cerrado']:
            return False, "No se puede eliminar un periodo activo o cerrado"
        
        # Verificar que no tenga datos asociados
        tiene_calificaciones = Calificacion.query.filter_by(periodo_academico_id=periodo_id).count() > 0
        tiene_asistencias = Asistencia.query.filter_by(periodo_academico_id=periodo_id).count() > 0
        
        if tiene_calificaciones or tiene_asistencias:
            return False, "No se puede eliminar un periodo con calificaciones o asistencias registradas"
        
        db.session.delete(periodo)
        db.session.commit()
        
        return True, None
        
    except Exception as e:
        db.session.rollback()
        return False, f"Error eliminando periodo: {str(e)}"


def verificar_proximidad_cierre():
    """
    Verifica si hay periodos próximos a cerrar y envía notificaciones
    Esta función debe ejecutarse diariamente (cron/celery)
    
    Returns:
        dict: Diccionario con resultados de las notificaciones
    """
    try:
        periodo_activo = obtener_periodo_activo()
        if not periodo_activo:
            return {'notificaciones_enviadas': 0, 'mensaje': 'No hay periodo activo'}
        
        dias_restantes = periodo_activo.dias_para_cierre()
        if dias_restantes is None:
            return {'notificaciones_enviadas': 0, 'mensaje': 'No se pudo calcular días restantes'}
        
        # Si faltan exactamente los días configurados, notificar
        if dias_restantes == periodo_activo.dias_notificacion_anticipada:
            from services.notification_service import notificar_proximidad_cierre
            notificar_proximidad_cierre(periodo_activo.id_periodo)
            return {
                'notificaciones_enviadas': 1,
                'mensaje': f'Notificaciones enviadas: faltan {dias_restantes} días para cierre'
            }
        
        return {
            'notificaciones_enviadas': 0,
            'mensaje': f'Faltan {dias_restantes} días, no es momento de notificar'
        }
        
    except Exception as e:
        return {'error': str(e)}

