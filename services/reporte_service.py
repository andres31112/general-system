"""
Servicio para gestión de Promoción de Estudiantes
"""

from datetime import datetime
from controllers.models import (
    db, CicloAcademico, PeriodoAcademico, Matricula, Calificacion, 
    Usuario, Curso, ConfiguracionCalificacion
)
from sqlalchemy import and_, func
from decimal import Decimal


def calcular_promedio_final_estudiante(estudiante_id, ciclo_id):
    """
    Calcula el promedio final de un estudiante en un ciclo académico
    
    Args:
        estudiante_id (int): ID del estudiante
        ciclo_id (int): ID del ciclo académico
    
    Returns:
        tuple: (promedio, error)
    """
    try:
        # Obtener todos los periodos del ciclo
        periodos = PeriodoAcademico.query.filter_by(ciclo_academico_id=ciclo_id).all()
        if not periodos:
            return None, "No hay periodos en este ciclo"
        
        promedios_por_periodo = []
        
        for periodo in periodos:
            # Obtener calificaciones del estudiante en este periodo
            calificaciones = Calificacion.query.filter_by(
                estudianteId=estudiante_id,
                periodo_academico_id=periodo.id_periodo
            ).all()
            
            if calificaciones:
                valores = [float(cal.valor) for cal in calificaciones if cal.valor is not None]
                if valores:
                    promedio_periodo = sum(valores) / len(valores)
                    promedios_por_periodo.append(promedio_periodo)
        
        if not promedios_por_periodo:
            return None, "No hay calificaciones para calcular promedio"
        
        # Calcular promedio general
        promedio_final = sum(promedios_por_periodo) / len(promedios_por_periodo)
        return round(Decimal(promedio_final), 2), None
        
    except Exception as e:
        return None, f"Error calculando promedio: {str(e)}"


def obtener_nota_minima_aprobacion():
    """
    Obtiene la nota mínima de aprobación configurada
    
    Returns:
        Decimal: Nota mínima de aprobación
    """
    try:
        # Buscar configuración global (asignatura_id = NULL)
        config = ConfiguracionCalificacion.query.filter_by(asignatura_id=None).first()
        if config:
            return config.notaMinimaAprobacion
        
        # Valor por defecto si no hay configuración
        return Decimal('3.0')
        
    except Exception as e:
        print(f"Error obteniendo nota mínima: {e}")
        return Decimal('3.0')


def obtener_curso_siguiente(curso_actual_id):
    """
    Determina el curso siguiente al actual
    Lógica: Busca un curso con nombre que indique el siguiente grado
    
    Args:
        curso_actual_id (int): ID del curso actual
    
    Returns:
        int: ID del curso siguiente o None si no hay
    """
    try:
        curso_actual = Curso.query.get(curso_actual_id)
        if not curso_actual:
            return None
        
        # Extraer el número del curso (ej: "10° A" -> 10)
        import re
        match = re.search(r'(\d+)', curso_actual.nombreCurso)
        if not match:
            return None
        
        grado_actual = int(match.group(1))
        grado_siguiente = grado_actual + 1
        
        # Buscar curso con el siguiente grado en la misma sede
        curso_siguiente = Curso.query.filter(
            Curso.nombreCurso.like(f'%{grado_siguiente}%'),
            Curso.sedeId == curso_actual.sedeId
        ).first()
        
        return curso_siguiente.id_curso if curso_siguiente else None
        
    except Exception as e:
        print(f"Error obteniendo curso siguiente: {e}")
        return None


def promover_estudiante(estudiante_id, ciclo_id, curso_siguiente_id, promedio_final):
    """
    Promueve un estudiante al siguiente curso
    
    Args:
        estudiante_id (int): ID del estudiante
        ciclo_id (int): ID del ciclo actual
        curso_siguiente_id (int): ID del curso al que se promueve
        promedio_final (Decimal): Promedio final del estudiante
    
    Returns:
        tuple: (success, error)
    """
    try:
        # Obtener matrícula actual
        matricula_actual = Matricula.query.filter_by(
            estudianteId=estudiante_id,
            ciclo_academico_id=ciclo_id,
            estado_matricula='activa'
        ).first()
        
        if not matricula_actual:
            return False, "No se encontró matrícula activa"
        
        # Actualizar matrícula actual
        matricula_actual.estado_matricula = 'finalizada'
        matricula_actual.promedio_final = promedio_final
        matricula_actual.estado_promocion = 'aprobado'
        matricula_actual.curso_promocion_id = curso_siguiente_id
        matricula_actual.fecha_promocion = datetime.utcnow()
        matricula_actual.observaciones_cierre = f"Promovido con promedio {promedio_final}"
        
        db.session.commit()
        
        # Notificar al estudiante
        from services.notification_service import notificar_promocion
        notificar_promocion(estudiante_id, 'aprobado', promedio_final, curso_siguiente_id)
        
        return True, None
        
    except Exception as e:
        db.session.rollback()
        return False, f"Error promoviendo estudiante: {str(e)}"


def reprobar_estudiante(estudiante_id, ciclo_id, curso_actual_id, promedio_final):
    """
    Marca a un estudiante como reprobado (repite el mismo curso)
    
    Args:
        estudiante_id (int): ID del estudiante
        ciclo_id (int): ID del ciclo actual
        curso_actual_id (int): ID del curso que debe repetir
        promedio_final (Decimal): Promedio final del estudiante
    
    Returns:
        tuple: (success, error)
    """
    try:
        # Obtener matrícula actual
        matricula_actual = Matricula.query.filter_by(
            estudianteId=estudiante_id,
            ciclo_academico_id=ciclo_id,
            estado_matricula='activa'
        ).first()
        
        if not matricula_actual:
            return False, "No se encontró matrícula activa"
        
        # Actualizar matrícula actual
        matricula_actual.estado_matricula = 'finalizada'
        matricula_actual.promedio_final = promedio_final
        matricula_actual.estado_promocion = 'reprobado'
        matricula_actual.curso_promocion_id = curso_actual_id  # Mismo curso
        matricula_actual.fecha_promocion = datetime.utcnow()
        matricula_actual.observaciones_cierre = f"Reprobado con promedio {promedio_final}. Debe repetir el grado."
        
        db.session.commit()
        
        # Notificar al estudiante
        from services.notification_service import notificar_promocion
        notificar_promocion(estudiante_id, 'reprobado', promedio_final, curso_actual_id)
        
        return True, None
        
    except Exception as e:
        db.session.rollback()
        return False, f"Error reprobando estudiante: {str(e)}"


def graduar_estudiante(estudiante_id, ciclo_id, promedio_final):
    """
    Marca a un estudiante como graduado (último grado completado)
    
    Args:
        estudiante_id (int): ID del estudiante
        ciclo_id (int): ID del ciclo actual
        promedio_final (Decimal): Promedio final del estudiante
    
    Returns:
        tuple: (success, error)
    """
    try:
        # Obtener matrícula actual
        matricula_actual = Matricula.query.filter_by(
            estudianteId=estudiante_id,
            ciclo_academico_id=ciclo_id,
            estado_matricula='activa'
        ).first()
        
        if not matricula_actual:
            return False, "No se encontró matrícula activa"
        
        # Actualizar matrícula actual
        matricula_actual.estado_matricula = 'finalizada'
        matricula_actual.promedio_final = promedio_final
        matricula_actual.estado_promocion = 'graduado'
        matricula_actual.curso_promocion_id = None  # No hay curso siguiente
        matricula_actual.fecha_promocion = datetime.utcnow()
        matricula_actual.observaciones_cierre = f"¡Graduado! Promedio final: {promedio_final}"
        
        db.session.commit()
        
        # Notificar al estudiante
        from services.notification_service import notificar_promocion
        notificar_promocion(estudiante_id, 'graduado', promedio_final, None)
        
        return True, None
        
    except Exception as e:
        db.session.rollback()
        return False, f"Error graduando estudiante: {str(e)}"


def procesar_promocion_estudiante(estudiante_id, ciclo_id):
    """
    Procesa la promoción de un estudiante individual
    Determina si aprueba, reprueba o se gradúa
    
    Args:
        estudiante_id (int): ID del estudiante
        ciclo_id (int): ID del ciclo académico
    
    Returns:
        tuple: (resultado, error) donde resultado = 'aprobado'|'reprobado'|'graduado'
    """
    try:
        # Calcular promedio final
        promedio_final, error = calcular_promedio_final_estudiante(estudiante_id, ciclo_id)
        if error:
            return None, error
        
        # Obtener nota mínima de aprobación
        nota_minima = obtener_nota_minima_aprobacion()
        
        # Obtener matrícula actual para saber el curso
        matricula_actual = Matricula.query.filter_by(
            estudianteId=estudiante_id,
            ciclo_academico_id=ciclo_id,
            estado_matricula='activa'
        ).first()
        
        if not matricula_actual:
            return None, "No se encontró matrícula activa"
        
        curso_actual_id = matricula_actual.cursoId
        
        # Verificar si aprueba
        if promedio_final >= nota_minima:
            # Obtener curso siguiente
            curso_siguiente_id = obtener_curso_siguiente(curso_actual_id)
            
            if curso_siguiente_id:
                # Promover al siguiente curso
                success, error = promover_estudiante(estudiante_id, ciclo_id, curso_siguiente_id, promedio_final)
                if success:
                    return 'aprobado', None
                return None, error
            else:
                # No hay curso siguiente = Graduado
                success, error = graduar_estudiante(estudiante_id, ciclo_id, promedio_final)
                if success:
                    return 'graduado', None
                return None, error
        else:
            # Reprueba - repite el mismo curso
            success, error = reprobar_estudiante(estudiante_id, ciclo_id, curso_actual_id, promedio_final)
            if success:
                return 'reprobado', None
            return None, error
            
    except Exception as e:
        return None, f"Error procesando promoción: {str(e)}"


def procesar_promocion_masiva(ciclo_id):
    """
    Procesa la promoción de todos los estudiantes de un ciclo
    
    Args:
        ciclo_id (int): ID del ciclo académico
    
    Returns:
        dict: Estadísticas del proceso
    """
    try:
        # Obtener todas las matrículas activas del ciclo
        matriculas = Matricula.query.filter_by(
            ciclo_academico_id=ciclo_id,
            estado_matricula='activa'
        ).all()
        
        resultados = {
            'total': len(matriculas),
            'aprobados': 0,
            'reprobados': 0,
            'graduados': 0,
            'errores': 0,
            'detalles_errores': []
        }
        
        for matricula in matriculas:
            resultado, error = procesar_promocion_estudiante(matricula.estudianteId, ciclo_id)
            
            if error:
                resultados['errores'] += 1
                estudiante = Usuario.query.get(matricula.estudianteId)
                resultados['detalles_errores'].append({
                    'estudiante': estudiante.nombre_completo if estudiante else 'Desconocido',
                    'error': error
                })
            else:
                if resultado == 'aprobado':
                    resultados['aprobados'] += 1
                elif resultado == 'reprobado':
                    resultados['reprobados'] += 1
                elif resultado == 'graduado':
                    resultados['graduados'] += 1
        
        return resultados
        
    except Exception as e:
        return {
            'error': f"Error en promoción masiva: {str(e)}",
            'total': 0,
            'aprobados': 0,
            'reprobados': 0,
            'graduados': 0,
            'errores': 0
        }


def crear_matriculas_nuevo_ciclo(ciclo_nuevo_id):
    """
    Crea matrículas automáticas para el nuevo ciclo basándose en las promociones
    
    Args:
        ciclo_nuevo_id (int): ID del nuevo ciclo académico
    
    Returns:
        dict: Estadísticas de las matrículas creadas
    """
    try:
        # Obtener ciclo anterior (el que tiene estado cerrado más reciente)
        ciclo_anterior = CicloAcademico.query.filter_by(
            estado='cerrado'
        ).order_by(CicloAcademico.fecha_fin.desc()).first()
        
        if not ciclo_anterior:
            return {'error': 'No se encontró ciclo anterior cerrado'}
        
        # Obtener matrículas finalizadas del ciclo anterior
        matriculas_anteriores = Matricula.query.filter_by(
            ciclo_academico_id=ciclo_anterior.id_ciclo,
            estado_matricula='finalizada'
        ).all()
        
        matriculas_creadas = 0
        errores = 0
        
        for mat_anterior in matriculas_anteriores:
            # Solo crear matrícula si tiene curso de promoción
            if mat_anterior.curso_promocion_id and mat_anterior.estado_promocion != 'graduado':
                try:
                    nueva_matricula = Matricula(
                        estudianteId=mat_anterior.estudianteId,
                        cursoId=mat_anterior.curso_promocion_id,
                        año=datetime.now().year,
                        ciclo_academico_id=ciclo_nuevo_id,
                        estado_matricula='activa',
                        estado_promocion='en_curso'
                    )
                    db.session.add(nueva_matricula)
                    matriculas_creadas += 1
                except Exception as e:
                    print(f"Error creando matrícula para estudiante {mat_anterior.estudianteId}: {e}")
                    errores += 1
        
        db.session.commit()
        
        return {
            'matriculas_creadas': matriculas_creadas,
            'errores': errores,
            'total_procesadas': len(matriculas_anteriores)
        }
        
    except Exception as e:
        db.session.rollback()
        return {'error': f"Error creando matrículas: {str(e)}"}


def finalizar_ciclo_escolar(ciclo_id):
    """
    Finaliza un ciclo escolar completo
    1. Procesa la promoción de todos los estudiantes
    2. Genera reportes finales
    3. Cierra el ciclo
    
    Args:
        ciclo_id (int): ID del ciclo a finalizar
    
    Returns:
        dict: Resultado del proceso
    """
    try:
        ciclo = CicloAcademico.query.get(ciclo_id)
        if not ciclo:
            return {'success': False, 'error': 'Ciclo no encontrado'}
        
        if ciclo.estado == 'cerrado':
            return {'success': False, 'error': 'El ciclo ya está cerrado'}
        
        # 1. Procesar promoción masiva
        resultados_promocion = procesar_promocion_masiva(ciclo_id)
        
        # 2. Generar reportes finales
        from services.reporte_service import generar_reporte_promocion, generar_estadisticas_ciclo
        reporte_promocion = generar_reporte_promocion(ciclo_id)
        estadisticas = generar_estadisticas_ciclo(ciclo_id)
        
        # 3. Cerrar todos los periodos del ciclo
        periodos = PeriodoAcademico.query.filter_by(ciclo_academico_id=ciclo_id).all()
        for periodo in periodos:
            if periodo.estado != 'cerrado':
                periodo.estado = 'cerrado'
        
        # 4. Cerrar el ciclo
        ciclo.estado = 'cerrado'
        ciclo.activo = False
        
        db.session.commit()
        
        # 5. Notificar fin de ciclo
        from services.notification_service import notificar_fin_ciclo
        notificar_fin_ciclo(ciclo_id)
        
        return {
            'success': True,
            'promocion': resultados_promocion,
            'reporte_generado': reporte_promocion is not None,
            'estadisticas_generadas': estadisticas is not None
        }
        
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'error': f"Error finalizando ciclo: {str(e)}"}

