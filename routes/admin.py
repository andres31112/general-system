from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from controllers.decorators import role_required
from extensions import db
from flask import current_app
from datetime import datetime, timedelta, time, date
from controllers.forms import RegistrationForm, UserEditForm, SalonForm, CursoForm, SedeForm, EquipoForm
from controllers.models import Usuario, Rol, Clase, Curso, Asignatura, Sede, Salon, HorarioGeneral, HorarioCompartido, Matricula, BloqueHorario, HorarioCurso, Equipo, Incidente, Mantenimiento, Comunicacion, Evento, Candidato, HorarioVotacion
from sqlalchemy.exc import IntegrityError
import json
from werkzeug.utils import secure_filename
import os


# Creamos un 'Blueprint' (un plano o borrador) para agrupar todas las rutas de la sección de admin
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# --- Rutas principales ---
@admin_bp.route('/dashboard')
@login_required 
@role_required(1) 
def admin_panel():
    """Muestra el panel principal de administración."""
    return render_template('superadmin/gestion_usuarios/dashboard.html')

@admin_bp.route('/inicio')
@login_required
@role_required(1)
def inicio():
    """Página de inicio del panel de superadmin."""
    return render_template('superadmin/inicio/inicio.html')

# --- Rutas para la Gestión de Inventario ---
@admin_bp.route('/gestion_inventario')
@login_required
@role_required(1)
def gestion_i():
    """Muestra la página principal de gestión de inventario."""
    return render_template('superadmin/gestion_inventario/gi.html')

@admin_bp.route('/equipos')
@login_required
@role_required(1)
def equipos():
    """Muestra la lista de equipos (página de equipos)."""
    return render_template('superadmin/gestion_inventario/equipos.html')

@admin_bp.route('/registro_equipos', methods=['GET', 'POST'])
@login_required
@role_required(1)
def crear_equipo():
    form = EquipoForm()
    if form.validate_on_submit():
        
        if form.asignado_a.data:
            estado_inicial = 'Asignado'
        else:
            estado_inicial = 'Disponible'
        
        nuevo_equipo = Equipo(
            id_referencia=form.id_referencia.data,
            nombre=form.nombre.data,
            tipo=form.tipo.data,
            estado=estado_inicial, 
            id_salon_fk=form.salon.data.id if form.salon.data else None,
            asignado_a=form.asignado_a.data,
            sistema_operativo=form.sistema_operativo.data,
            ram=form.ram.data,
            disco_duro=form.disco_duro.data,
            fecha_adquisicion=datetime.strptime(form.fecha_adquisicion.data, '%Y-%m-%d').date() if form.fecha_adquisicion.data else None,
            descripcion=form.descripcion.data,
            observaciones=form.observaciones.data
        )
        db.session.add(nuevo_equipo)
        db.session.commit()

        flash(f'Equipo "{nuevo_equipo.nombre}" creado exitosamente!', 'success')
        return redirect(url_for('admin.equipos'))

    return render_template(
        'superadmin/gestion_inventario/registro_equipo.html',
        title='Crear Nuevo Equipo',
        form=form
    )

@admin_bp.route('/api/equipos', methods=['GET']) # Cambiado a /api/equipos para ser más general
@login_required
@role_required(1)
def api_equipos_todos():
    """API para listar todos los equipos con información de salón y sede."""
    try:
        equipos_db = db.session.query(
            Equipo.id,
            Equipo.id_referencia,
            Equipo.nombre,
            Equipo.tipo,
            Equipo.estado,
            Equipo.asignado_a,
            Equipo.sistema_operativo,
            Equipo.ram,
            Equipo.disco_duro,
            Equipo.fecha_adquisicion,
            Equipo.descripcion,
            Equipo.observaciones,
            Equipo.id_salon_fk,
            Salon.nombre.label('salon_nombre'),
            Sede.nombre.label('sede_nombre')
        ).outerjoin(Salon, Equipo.id_salon_fk == Salon.id)\
         .outerjoin(Sede, Salon.id_sede_fk == Sede.id)\
         .all()
        
        equipos = []
        for eq in equipos_db:
            equipos.append({
                'id': eq.id,
                'id_referencia': eq.id_referencia,
                'nombre': eq.nombre,
                'tipo': eq.tipo,
                'estado': eq.estado,
                'asignado_a': eq.asignado_a or "N/A",
                'sistema_operativo': eq.sistema_operativo or "N/A",
                'ram': eq.ram or "N/A",
                'disco_duro': eq.disco_duro or "N/A",
                'fecha_adquisicion': eq.fecha_adquisicion.strftime('%Y-%m-%d') if eq.fecha_adquisicion else "N/A",
                'descripcion': eq.descripcion or "N/A",
                'observaciones': eq.observaciones or "N/A",
                'id_salon_fk': eq.id_salon_fk,
                'salon_nombre': eq.salon_nombre or "Sin Salón",
                'sede_nombre': eq.sede_nombre or "Sin Sede"
            })

        return jsonify(equipos), 200 # Retorna directamente la lista de equipos
    except Exception as e:
        print(f"Error al listar equipos: {e}")
        return jsonify({'error': f"Error interno del servidor: {str(e)}"}), 500

@admin_bp.route('/api/equipos/con-incidentes', methods=['GET'])
@login_required
@role_required(1)
def api_equipos_con_incidentes():
    """
    Retorna los IDs de equipos que tienen incidentes activos (no resueltos/cerrados).
    """
    try:
        equipos_con_incidentes = db.session.query(Incidente.equipo_id)\
            .filter(Incidente.estado.in_(['reportado', 'en_proceso']))\
            .distinct()\
            .all()
        
        ids = [eq[0] for eq in equipos_con_incidentes]
        
        return jsonify({'equipos_con_incidentes': ids}), 200
        
    except Exception as e:
        print(f"Error al obtener equipos con incidentes: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/equipos/<int:equipo_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@role_required(1)
def api_equipo_detalle(equipo_id):
    equipo = Equipo.query.get_or_404(equipo_id)
    
    # Lógica de ELIMINACIÓN (DELETE)
    if request.method == 'DELETE':
        try:
            db.session.delete(equipo)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Equipo eliminado exitosamente'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': f'Error al eliminar el equipo: {str(e)}'}), 500

    # Lógica de EDICIÓN (PUT)
    if request.method == 'PUT':
        data = request.get_json()
        
        try:
            equipo.asignado_a = data.get('asignado_a', equipo.asignado_a)
            equipo.estado = data.get('estado', equipo.estado)
            equipo.sistema_operativo = data.get('sistema_operativo', equipo.sistema_operativo)
            equipo.ram = data.get('ram', equipo.ram)
            equipo.disco_duro = data.get('disco_duro', equipo.disco_duro)
            equipo.descripcion = data.get('descripcion', equipo.descripcion)
            equipo.observaciones = data.get('observaciones', equipo.observaciones)
            
            fecha_adquisicion_str = data.get('fecha_adquisicion')
            if fecha_adquisicion_str:
                equipo.fecha_adquisicion = datetime.strptime(fecha_adquisicion_str, '%Y-%m-%d').date()
            else:
                equipo.fecha_adquisicion = None # Permitir que la fecha sea nula si se envía vacío

            # Actualizar id_salon_fk si se proporciona
            id_salon_fk = data.get('id_salon_fk')
            if id_salon_fk is not None: # Permitir 0 o null si es necesario, aunque el formulario lo hace readonly
                salon = Salon.query.get(id_salon_fk)
                if salon:
                    equipo.id_salon_fk = id_salon_fk
                else:
                    return jsonify({'success': False, 'error': 'Salón no encontrado para la actualización.'}), 400

            db.session.commit()
            return jsonify({'success': True, 'message': 'Equipo actualizado exitosamente'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': f'Error al actualizar el equipo: {str(e)}'}), 500
            
    # Lógica de VISTA (GET)
    if request.method == 'GET':
        data = equipo.to_dict()
        # Asegurarse de que salon_nombre y sede_nombre estén presentes
        data['salon_nombre'] = equipo.salon.nombre if equipo.salon else "Sin Salón"
        data['sede_nombre'] = equipo.salon.sede.nombre if equipo.salon and equipo.salon.sede else "Sin Sede"

        data['incidentes'] = [
            {'fecha': i.fecha.strftime("%Y-%m-%d"), 'descripcion': i.descripcion} 
            for i in equipo.incidentes
        ]
        data['mantenimientos'] = [
            {'fecha': m.fecha_programada.strftime("%Y-%m-%d"), 'tipo': m.tipo, 'estado': m.estado} 
            for m in equipo.programaciones
        ]
        
        return jsonify(data), 200
    
@admin_bp.route('/salones')
@login_required
@role_required(1)
def salones():
    """Muestra la lista de todos los salones."""
    # Esta ruta renderiza el HTML, la API /api/salas_todas es la que alimenta los datos
    return render_template('superadmin/gestion_inventario/salones.html')

# ===============================
# API Sedes, Salas y Equipos
# ===============================

@admin_bp.route('/api/sedes', methods=['GET', 'POST', 'DELETE'])
@login_required
def api_sedes():
    if request.method == 'GET':
        sedes = Sede.query.order_by(Sede.nombre).all()
        sedes_data = [{"id": sede.id, "nombre": sede.nombre, "direccion": sede.direccion} for sede in sedes]
        return jsonify(sedes_data), 200

    if request.method == 'POST':
        data = request.get_json()
        form = SedeForm(data=data)
        
        if form.validate_on_submit():
            try:
                nueva_sede = Sede(
                    nombre=form.nombre.data,
                    direccion=form.direccion.data if hasattr(form, 'direccion') else "Dirección por defecto"
                )
                
                db.session.add(nueva_sede)
                db.session.commit()
                
                return jsonify({"message": "Sede creada exitosamente", "sede_id": nueva_sede.id}), 201
            
            except Exception as e:
                db.session.rollback()
                return jsonify({"error": str(e)}), 500
        else:
            errors = {}
            for field, messages in form.errors.items():
                errors[field] = messages
            return jsonify({"errors": errors, "error": "Error de validación"}), 400

    if request.method == 'DELETE':
        data = request.get_json()
        sede_id = data.get('id')
        
        if not sede_id:
            return jsonify({"error": "ID de sede no proporcionado"}), 400

        sede = Sede.query.get(sede_id)
        
        if not sede:
            return jsonify({"error": "Sede no encontrada"}), 404
            
        try:
            db.session.delete(sede)
            db.session.commit()
            return jsonify({"message": "Sede eliminada exitosamente"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": "No se pudo eliminar la sede."}), 500

    return jsonify({"error": "Método no permitido"}), 405

@admin_bp.route('/api/sedes/<int:sede_id>/salas')
def api_salas_por_sede(sede_id): # Renombrada para evitar conflicto con api_salas_todas
    salones = Salon.query.filter_by(id_sede_fk=sede_id).all()
    return jsonify([{"id": s.id, "nombre": s.nombre, "tipo": s.tipo} for s in salones])

@admin_bp.route('/api/salas_todas', methods=['GET'])
@login_required
@role_required(1)
def api_salas_todas():
    salones = Salon.query.all()
    result = []
    for s in salones:
        sede_nombre = s.sede.nombre if s.sede else 'N/A'
        total_equipos = Equipo.query.filter_by(id_salon_fk=s.id).count()
        result.append({
            'id': s.id,
            'nombre': s.nombre,
            'tipo': s.tipo,
            'capacidad': s.capacidad,
            'sede_id': s.id_sede_fk,
            'sede_nombre': sede_nombre,
            'total_equipos': total_equipos
        })
    return jsonify(result)

@admin_bp.route('/api/salones/<int:salon_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@role_required(1)
def api_salon_detalle(salon_id):
    """
    Endpoint para gestionar un salón específico (Ver, Editar, Eliminar).
    GET: Devuelve los detalles de un salón.
    PUT: Actualiza un salón.
    DELETE: Elimina un salón.
    """
    salon = Salon.query.get_or_404(salon_id)

    if request.method == 'GET':
        sede_nombre = salon.sede.nombre if salon.sede else 'N/A'
        total_equipos = Equipo.query.filter_by(id_salon_fk=salon_id).count()
        return jsonify({
            'id': salon.id,
            'nombre': salon.nombre,
            'tipo': salon.tipo,
            'capacidad': salon.capacidad,
            'sede_id': salon.id_sede_fk,
            'sede_nombre': sede_nombre,
            'total_equipos': total_equipos,
            'cantidad_sillas': salon.cantidad_sillas or 0,
            'cantidad_mesas': salon.cantidad_mesas or 0
        }), 200

    if request.method == 'PUT':
        data = request.get_json()
        try:
            salon.nombre = data.get('nombre', salon.nombre)
            salon.tipo = data.get('tipo', salon.tipo)
            salon.capacidad = data.get('capacidad', salon.capacidad)
            salon.id_sede_fk = data.get('sede_id', salon.id_sede_fk)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Salón actualizado exitosamente'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': f'Error al actualizar el salón: {str(e)}'}), 500

    if request.method == 'DELETE':
        # Verificar si hay equipos asociados antes de eliminar
        equipos_asociados = Equipo.query.filter_by(id_salon_fk=salon_id).first()
        if equipos_asociados:
            return jsonify({'success': False, 'error': 'No se puede eliminar el salón porque tiene equipos asociados.'}), 400
        try:
            db.session.delete(salon)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Salón eliminado exitosamente'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': f'Error al eliminar el salón: {str(e)}'}), 500
        
@admin_bp.route('/api/sedes/<int:sede_id>/salas/<int:salon_id>/equipos')
def api_equipos_por_sala(sede_id, salon_id): # Renombrada para evitar conflicto
    equipos = Equipo.query.filter_by(id_salon_fk=salon_id).all()
    data = []
    for eq in equipos:
        data.append({
            "id": eq.id,
            "nombre": eq.nombre,
            "estado": eq.estado,
            "asignado_a": eq.asignado_a or ""
        })
    return jsonify(data)

@admin_bp.route('/reportes')
@login_required # Añadir login_required para consistencia y seguridad
@role_required(1)
def reportes():
    """Muestra la página de reportes de inventario."""
    return render_template('superadmin/gestion_inventario/reportes.html')

@admin_bp.route('/api/reportes/estado_equipos', methods=['GET'])
@login_required
@role_required(1)
def api_reportes_estado_equipos():
    """
    Proporciona datos para el gráfico de estado de equipos y las métricas principales.
    """
    from controllers.models import Equipo, db
    
    # 1. Total de equipos
    total = db.session.query(Equipo).count()
    
    # 2. Conteo por estado
    # Incluye cualquier estado que exista en la base de datos
    estados_raw = db.session.query(Equipo.estado, db.func.count(Equipo.estado)).group_by(Equipo.estado).all()
    estados = {e[0]: e[1] for e in estados_raw}
    
    data = {
        'total_equipos': total,
        'estados': {
            'Disponible': estados.get('Disponible', 0),
            'Mantenimiento': estados.get('Mantenimiento', 0),
            'Incidente': estados.get('Incidente', 0),
            'Asignado': estados.get('Asignado', 0),
            'Revisión': estados.get('Revisión', 0), # Asegurarse de incluir 'Revisión'
            # Incluye todos los demás estados que puedan existir
            **{k: v for k, v in estados.items() if k not in ['Disponible', 'Mantenimiento', 'Incidente', 'Asignado', 'Revisión']}
        }
    }
    
    return jsonify(data), 200

@admin_bp.route('/api/reportes/equipos_por_sede', methods=['GET'])
@login_required
@role_required(1)
def api_reportes_equipos_por_sede():
    """
    Proporciona datos para el gráfico de equipos por sede.
    """
    from controllers.models import Equipo, Salon, Sede, db
    
    # Consulta: Contar equipos agrupados por el nombre de su Sede
    resultados = db.session.query(
        Sede.nombre.label('sede_nombre'),
        db.func.count(Equipo.id).label('total')
    ).join(Salon, Salon.id_sede_fk == Sede.id)\
    .join(Equipo, Equipo.id_salon_fk == Salon.id)\
    .group_by(Sede.nombre)\
    .order_by(db.func.count(Equipo.id).desc())\
    .all()
    
    data = [{
        'sede': r.sede_nombre,
        'total': r.total
    } for r in resultados]
    
    return jsonify(data), 200

@admin_bp.route('/incidentes')
@role_required(1)
def incidentes():
    """Muestra la página de gestión de incidentes."""
    return render_template('superadmin/gestion_inventario/incidentes.html')

# 1. API: OBTENER EQUIPOS CON ESTADO "INCIDENTE"
@admin_bp.route('/api/equipos_para_incidente', methods=['GET'])
@login_required
@role_required(1)
def api_equipos_para_incidente():
    """
    Retorna solo los equipos con estado 'Incidente' para poder registrar incidentes.
    Endpoint exclusivo que no interfiere con /api/equipos/todos
    """
    try:
        equipos_db = db.session.query(
            Equipo.id,
            Equipo.nombre,
            Equipo.estado,
            Salon.nombre.label('salon_nombre'),
            Sede.nombre.label('sede_nombre')
        ).outerjoin(Salon, Equipo.id_salon_fk == Salon.id)\
         .outerjoin(Sede, Salon.id_sede_fk == Sede.id)\
         .order_by(Equipo.nombre)\
         .all()
        
        equipos = []
        for eq in equipos_db:
            equipos.append({
                'id': eq.id,
                'nombre': eq.nombre,
                'estado': eq.estado,
                'salon_nombre': eq.salon_nombre or "Sin Salón",
                'sede_nombre': eq.sede_nombre or "Sin Sede"
            })

        return jsonify(equipos), 200

    except Exception as e:
        print(f"Error al listar equipos para incidente: {e}")
        return jsonify({'error': f"Error interno del servidor: {str(e)}"}), 500


# 2. API: LISTAR TODOS LOS INCIDENTES (GET)
@admin_bp.route('/api/incidentes', methods=['GET'])
@login_required
@role_required(1)
def api_listar_incidentes():
    """
    Lista todos los incidentes con información completa de equipo, salón y sede.
    """
    try:
        incidentes_db = db.session.query(
            Incidente.id,
            Incidente.equipo_id,
            Incidente.usuario_asignado.label('usuario_reporte'),
            Incidente.fecha,
            Incidente.descripcion,
            Incidente.estado,
            Incidente.prioridad,
            Incidente.solucion_propuesta,
            Equipo.nombre.label('equipo_nombre'),
            Salon.nombre.label('salon_nombre'),
            Sede.nombre.label('sede_nombre')
        ).join(Equipo, Incidente.equipo_id == Equipo.id)\
         .outerjoin(Salon, Equipo.id_salon_fk == Salon.id)\
         .outerjoin(Sede, Salon.id_sede_fk == Sede.id)\
         .order_by(Incidente.fecha.desc())\
         .all()
        
        incidentes = []
        for inc in incidentes_db:
            incidentes.append({
                'id': inc.id,
                'equipo_id': inc.equipo_id,
                'usuario_reporte': inc.usuario_reporte or '',
                'fecha': inc.fecha.strftime('%Y-%m-%d %H:%M:%S') if inc.fecha else None,
                'descripcion': inc.descripcion or '',
                'estado': inc.estado or 'reportado',
                'prioridad': inc.prioridad or 'media',
                'solucion_propuesta': inc.solucion_propuesta or '',
                'equipo_nombre': inc.equipo_nombre or "",
                'salon_nombre': inc.salon_nombre or "Sin Salón",
                'sede_nombre': inc.sede_nombre or "Sin Sede"
            })

        return jsonify(incidentes), 200
        
    except Exception as e:
        print(f"Error al listar incidentes: {e}")
        return jsonify({'error': f"Error interno del servidor: {str(e)}"}), 500

# 3. API: CREAR NUEVO INCIDENTE (POST)
@admin_bp.route('/api/incidentes', methods=['POST'])
@login_required
@role_required(1)
def api_crear_incidente():
    """
    Crea un nuevo incidente SIN cambiar el estado del equipo.
    """
    try:
        data = request.get_json()
        
        # Validación de datos obligatorios
        equipo_id = data.get('equipo_id')
        descripcion = data.get('descripcion', '').strip()
        prioridad = data.get('prioridad', 'media')
        usuario_reporte = data.get('usuario_reporte', '').strip()
        
        if not equipo_id:
            return jsonify({
                'success': False, 
                'error': 'El equipo es obligatorio.'
            }), 400
            
        if not descripcion:
            return jsonify({
                'success': False, 
                'error': 'La descripción del problema es obligatoria.'
            }), 400
        
        if not usuario_reporte:
            return jsonify({
                'success': False, 
                'error': 'El usuario que reporta es obligatorio.'
            }), 400

        # Verificar que el equipo exista
        equipo = Equipo.query.get(equipo_id)
        if not equipo:
            return jsonify({
                'success': False, 
                'error': f'El equipo con ID {equipo_id} no existe.'
            }), 404
            
        # ❌ ELIMINAR ESTA LÍNEA: equipo.estado = 'Incidente'

        # Obtener sede del equipo
        sede_nombre = "Sin Sede"
        if equipo.salon and equipo.salon.sede:
            sede_nombre = equipo.salon.sede.nombre

        # Crear el incidente
        nuevo_incidente = Incidente(
            equipo_id=equipo_id,
            usuario_asignado=usuario_reporte,
            sede=sede_nombre,
            fecha=datetime.now(),
            descripcion=descripcion,
            estado='reportado',
            prioridad=prioridad,
            solucion_propuesta=data.get('solucion_propuesta', '')
        )
        
        db.session.add(nuevo_incidente)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Incidente creado exitosamente',
            'incidente': {
                'id': nuevo_incidente.id,
                'equipo_nombre': equipo.nombre,
                'usuario_reporte': usuario_reporte,
                'fecha': nuevo_incidente.fecha.strftime('%Y-%m-%d %H:%M:%S'),
                'estado': nuevo_incidente.estado,
                'prioridad': nuevo_incidente.prioridad
            }
        }), 201

    except IntegrityError as e:
        db.session.rollback()
        return jsonify({
            'success': False, 
            'error': 'Error de integridad de datos. Verifique la información.'
        }), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error al crear incidente: {e}")
        return jsonify({'success': False, 'error': f'Error interno del servidor: {str(e)}'}), 500

# 4. API: CAMBIAR ESTADO DE INCIDENTE (PUT)
@admin_bp.route('/api/incidentes/<int:incidente_id>/estado', methods=['PUT'])
@login_required
@role_required(1)
def api_actualizar_estado_incidente(incidente_id):
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        incidente = Incidente.query.get_or_404(incidente_id)
        
        if not nuevo_estado or nuevo_estado not in ['reportado', 'en_proceso', 'resuelto', 'cerrado']:
             return jsonify({'success': False, 'error': 'Estado inválido.'}), 400

        # 1. Actualizar el estado del incidente
        incidente.estado = nuevo_estado
        incidente.fecha_actualizacion = datetime.now() # O campo similar
        
        # 2. Lógica adicional (ej: actualizar estado del Equipo si es 'cerrado/resuelto')
        if nuevo_estado in ['resuelto', 'cerrado'] and incidente.equipo:
            incidente.equipo.estado = 'Disponible' # O estado apropiado
        elif nuevo_estado == 'reportado' and incidente.equipo:
             incidente.equipo.estado = 'Incidente'
        
        db.session.commit()

        # 3. DEVOLVER EL INCIDENTE ACTUALIZADO COMPLETO (¡CRUCIAL!)
        return jsonify({ 
            'success': True, 
            'message': 'Estado actualizado con éxito',
            # Debes implementar una función para serializar el objeto Incidente a un diccionario
            'incidente_actualizado': incidente.to_dict() 
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error al actualizar estado: {e}")
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500


# 5. API: ELIMINAR INCIDENTE (DELETE)
@admin_bp.route('api/incidentes/<int:incidente_id>', methods=['DELETE'])
@login_required
@role_required(1)
def api_eliminar_incidente(incidente_id):
    """
    Elimina un incidente por su ID.
    """
    try:
        incidente = Incidente.query.get(incidente_id)
        
        if not incidente:
            return jsonify({'success': False, 'error': 'Incidente no encontrado.'}), 404
        
        db.session.delete(incidente)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Incidente {incidente_id} eliminado exitosamente.'})

    except Exception as e:
        db.session.rollback()
        print(f"Error al eliminar incidente: {e}")
        return jsonify({'success': False, 'error': f'Error interno del servidor: {str(e)}'}), 500


# 6. API: OBTENER DETALLE DE UN INCIDENTE (GET - OPCIONAL)
@admin_bp.route('/admin/api/incidentes/<int:incidente_id>', methods=['GET'])
@login_required
@role_required(1)
def api_detalle_incidente(incidente_id):
    """
    Obtiene el detalle completo de un incidente específico.
    """
    try:
        incidente_db = db.session.query(
            Incidente.id,
            Incidente.equipo_id,
            Incidente.usuario_asignado.label('usuario_reporte'),
            Incidente.fecha,
            Incidente.descripcion,
            Incidente.estado,
            Incidente.prioridad,
            Incidente.solucion_propuesta,
            Equipo.nombre.label('equipo_nombre'),
            Salon.nombre.label('salon_nombre'),
            Sede.nombre.label('sede_nombre')
        ).join(Equipo, Incidente.equipo_id == Equipo.id)\
         .outerjoin(Salon, Equipo.id_salon_fk == Salon.id)\
         .outerjoin(Sede, Salon.id_sede_fk == Sede.id)\
         .filter(Incidente.id == incidente_id)\
         .first()
        
        if not incidente_db:
            return jsonify({'success': False, 'error': 'Incidente no encontrado.'}), 404
        
        incidente = {
            'id': incidente_db.id,
            'equipo_id': incidente_db.equipo_id,
            'usuario_reporte': incidente_db.usuario_reporte or '',
            'fecha': incidente_db.fecha.strftime('%Y-%m-%d %H:%M:%S') if incidente_db.fecha else None,
            'descripcion': incidente_db.descripcion or '',
            'estado': incidente_db.estado or 'reportado',
            'prioridad': incidente_db.prioridad or 'media',
            'solucion_propuesta': incidente_db.solucion_propuesta or '',
            'equipo_nombre': incidente_db.equipo_nombre or "",
            'salon_nombre': incidente_db.salon_nombre or "Sin Salón",
            'sede_nombre': incidente_db.sede_nombre or "Sin Sede"
        }

        return jsonify(incidente), 200
        
    except Exception as e:
        print(f"Error al obtener detalle del incidente: {e}")
        return jsonify({'error': f"Error interno del servidor: {str(e)}"}), 500

@admin_bp.route('/mantenimiento')
@role_required(1)
def mantenimiento():
    """Muestra la página de mantenimiento de equipos."""
    return render_template('superadmin/gestion_inventario/mantenimiento.html')

# ========================================
# API DE MANTENIMIENTOS
# ========================================

@admin_bp.route('/api/mantenimientos', methods=['GET'])
@login_required
@role_required(1)
def api_listar_mantenimientos():
    """
    Lista todos los mantenimientos con información completa de equipo, sede y salón.
    """
    try:
        mantenimientos_db = db.session.query(
            Mantenimiento.id,
            Mantenimiento.equipo_id,
            Mantenimiento.sede_id,
            Mantenimiento.fecha_programada,
            Mantenimiento.tipo,
            Mantenimiento.estado,
            Mantenimiento.descripcion,
            Mantenimiento.fecha_realizada,
            Mantenimiento.tecnico,
            Equipo.nombre.label('equipo_nombre'),
            Salon.nombre.label('salon_nombre'), # Añadir nombre del salón
            Sede.nombre.label('sede_nombre')
        ).join(Equipo, Mantenimiento.equipo_id == Equipo.id)\
         .join(Sede, Mantenimiento.sede_id == Sede.id)\
         .outerjoin(Salon, Equipo.id_salon_fk == Salon.id)\
         .order_by(Mantenimiento.fecha_programada.desc())\
         .all()

        mantenimientos = []
        for mant in mantenimientos_db:
            mantenimientos.append({
                'id': mant.id,
                'equipo_id': mant.equipo_id,
                'equipo_nombre': mant.equipo_nombre,
                'sede_id': mant.sede_id,
                'sede': mant.sede_nombre,
                'salon_nombre': mant.salon_nombre or "N/A", # Incluir nombre del salón
                'fecha_programada': mant.fecha_programada.strftime('%Y-%m-%d'),
                'tipo': mant.tipo,
                'estado': mant.estado,
                'descripcion': mant.descripcion or '',
                'fecha_realizada': mant.fecha_realizada.strftime('%Y-%m-%d') if mant.fecha_realizada else None,
                'tecnico': mant.tecnico or ''
            })
        return jsonify(mantenimientos), 200
    except Exception as e:
        print(f"Error al listar mantenimientos: {e}")
        return jsonify({'error': f"Error interno del servidor: {str(e)}"}), 500

@admin_bp.route('/api/mantenimientos/programar', methods=['POST'])
@login_required
@role_required(1)
def api_programar_mantenimiento():
    """
    Programa un nuevo mantenimiento y actualiza el estado del equipo.
    """
    try:
        data = request.get_json()
        equipo_id = data.get('equipo_id')
        sede_id = data.get('sede_id') # Asegurarse de recibir sede_id
        fecha_programada_str = data.get('fecha_programada')
        tipo = data.get('tipo')
        descripcion = data.get('descripcion', '').strip()
        tecnico = data.get('tecnico', '').strip()

        if not all([equipo_id, sede_id, fecha_programada_str, tipo]):
            return jsonify({'success': False, 'error': 'Faltan campos obligatorios.'}), 400

        equipo = Equipo.query.get(equipo_id)
        if not equipo:
            return jsonify({'success': False, 'error': f'Equipo con ID {equipo_id} no encontrado.'}), 404

        # Convertir fecha
        fecha_programada = datetime.strptime(fecha_programada_str, '%Y-%m-%d').date()

        nuevo_mantenimiento = Mantenimiento(
            equipo_id=equipo_id,
            sede_id=sede_id,
            fecha_programada=fecha_programada,
            tipo=tipo,
            estado='pendiente', # Estado inicial
            descripcion=descripcion,
            tecnico=tecnico
        )
        db.session.add(nuevo_mantenimiento)

        # Actualizar estado del equipo a 'Mantenimiento'
        equipo.estado = 'Mantenimiento'
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Mantenimiento programado exitosamente.',
            'mantenimiento': nuevo_mantenimiento.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error al programar mantenimiento: {e}")
        return jsonify({'success': False, 'error': f'Error interno del servidor: {str(e)}'}), 500

@admin_bp.route('/api/mantenimientos/<int:mantenimiento_id>', methods=['GET'])
@login_required
@role_required(1)
def api_detalle_mantenimiento(mantenimiento_id):
    """
    Obtiene el detalle de un mantenimiento específico.
    """
    try:
        mantenimiento = db.session.query(
            Mantenimiento.id,
            Mantenimiento.equipo_id,
            Mantenimiento.sede_id,
            Mantenimiento.fecha_programada,
            Mantenimiento.tipo,
            Mantenimiento.estado,
            Mantenimiento.descripcion,
            Mantenimiento.fecha_realizada,
            Mantenimiento.tecnico,
            Equipo.nombre.label('equipo_nombre'),
            Salon.nombre.label('salon_nombre'),
            Sede.nombre.label('sede_nombre')
        ).join(Equipo, Mantenimiento.equipo_id == Equipo.id)\
         .join(Sede, Mantenimiento.sede_id == Sede.id)\
         .outerjoin(Salon, Equipo.id_salon_fk == Salon.id)\
         .filter(Mantenimiento.id == mantenimiento_id)\
         .first()

        if not mantenimiento:
            return jsonify({'success': False, 'error': 'Mantenimiento no encontrado.'}), 404

        return jsonify({
            'id': mantenimiento.id,
            'equipo_id': mantenimiento.equipo_id,
            'equipo_nombre': mantenimiento.equipo_nombre,
            'sede_id': mantenimiento.sede_id,
            'sede': mantenimiento.sede_nombre,
            'salon_nombre': mantenimiento.salon_nombre or "N/A",
            'fecha_programada': mantenimiento.fecha_programada.strftime('%Y-%m-%d'),
            'tipo': mantenimiento.tipo,
            'estado': mantenimiento.estado,
            'descripcion': mantenimiento.descripcion or '',
            'fecha_realizada': mantenimiento.fecha_realizada.strftime('%Y-%m-%d') if mantenimiento.fecha_realizada else None,
            'tecnico': mantenimiento.tecnico or ''
        }), 200
    except Exception as e:
        print(f"Error al obtener detalle de mantenimiento: {e}")
        return jsonify({'error': f"Error interno del servidor: {str(e)}"}), 500

@admin_bp.route('/api/mantenimientos/<int:mantenimiento_id>/actualizar', methods=['PUT'])
@login_required
@role_required(1)
def api_actualizar_mantenimiento(mantenimiento_id):
    """
    Actualiza el estado, técnico y fecha de realización de un mantenimiento.
    También actualiza el estado del equipo asociado.
    """
    try:
        data = request.get_json()
        mantenimiento = Mantenimiento.query.get_or_404(mantenimiento_id)
        equipo = Equipo.query.get(mantenimiento.equipo_id) # Obtener el equipo asociado

        nuevo_estado = data.get('estado', mantenimiento.estado)
        tecnico = data.get('tecnico', mantenimiento.tecnico)
        fecha_realizada_str = data.get('fecha_realizada')

        if nuevo_estado not in ['pendiente', 'en_progreso', 'completado', 'cancelado']:
            return jsonify({'success': False, 'error': 'Estado de mantenimiento inválido.'}), 400

        mantenimiento.estado = nuevo_estado
        mantenimiento.tecnico = tecnico

        if fecha_realizada_str:
            mantenimiento.fecha_realizada = datetime.strptime(fecha_realizada_str, '%Y-%m-%d').date()
        elif nuevo_estado == 'completado' and not mantenimiento.fecha_realizada:
            mantenimiento.fecha_realizada = date.today() # Establecer hoy si se completa y no hay fecha

        # Lógica para actualizar el estado del equipo
        if equipo:
            if nuevo_estado == 'completado':
                equipo.estado = 'Disponible' # O el estado que corresponda después del mantenimiento
            elif nuevo_estado == 'cancelado':
                # Si se cancela, el equipo vuelve a su estado anterior o a 'Disponible'
                # Aquí asumimos 'Disponible' si no hay un estado anterior claro
                equipo.estado = 'Disponible'
            elif nuevo_estado == 'en_progreso':
                equipo.estado = 'Mantenimiento' # Asegurarse de que el equipo esté en mantenimiento
            # Si es 'pendiente', el estado del equipo ya debería ser 'Mantenimiento' desde la programación

        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Mantenimiento actualizado exitosamente.',
            'mantenimiento_actualizado': mantenimiento.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error al actualizar mantenimiento: {e}")
        return jsonify({'success': False, 'error': f'Error interno del servidor: {str(e)}'}), 500

@admin_bp.route('/api/mantenimientos/<int:mantenimiento_id>', methods=['DELETE'])
@login_required
@role_required(1)
def api_eliminar_mantenimiento(mantenimiento_id):
    """
    Elimina un mantenimiento y restablece el estado del equipo si estaba en 'Mantenimiento'.
    """
    try:
        mantenimiento = Mantenimiento.query.get_or_404(mantenimiento_id)
        equipo = Equipo.query.get(mantenimiento.equipo_id)

        # Si el mantenimiento estaba activo y el equipo en estado 'Mantenimiento',
        # se restablece el estado del equipo a 'Disponible'.
        if equipo and mantenimiento.estado in ['pendiente', 'en_progreso'] and equipo.estado == 'Mantenimiento':
            equipo.estado = 'Disponible'

        db.session.delete(mantenimiento)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Mantenimiento eliminado exitosamente.'}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error al eliminar mantenimiento: {e}")
        return jsonify({'success': False, 'error': f'Error interno del servidor: {str(e)}'}), 500

@admin_bp.route('/api/mantenimientos/estadisticas', methods=['GET'])
@login_required
@role_required(1)
def api_estadisticas_mantenimientos():
    """
    Proporciona estadísticas de mantenimientos por estado.
    """
    try:
        total = db.session.query(Mantenimiento).count()
        estados_raw = db.session.query(Mantenimiento.estado, db.func.count(Mantenimiento.estado))\
                                .group_by(Mantenimiento.estado).all()
        
        stats = {e[0]: e[1] for e in estados_raw}
        
        return jsonify({
            'total': total,
            'pendiente': stats.get('pendiente', 0),
            'en_progreso': stats.get('en_progreso', 0),
            'completado': stats.get('completado', 0),
            'cancelado': stats.get('cancelado', 0)
        }), 200
    except Exception as e:
        print(f"Error al obtener estadísticas de mantenimientos: {e}")
        return jsonify({'error': f"Error interno del servidor: {str(e)}"}), 500

@admin_bp.route('/gestion-salones')
def gestion_salones():
    """Muestra la página de gestión de salones con estadísticas."""
    # Esta ruta renderiza el HTML, la API /api/salas_todas es la que alimenta los datos
    return render_template(
        'superadmin/gestion_inventario/salones.html'
    )

@admin_bp.route('/registro_salon', methods=['GET', 'POST'])
@login_required
@role_required(1)
def registro_salon():
    """Maneja el formulario para crear un nuevo salón."""
    form = SalonForm()
    
    if form.validate_on_submit():
        nuevo_salon = Salon(
            nombre=form.nombre_salon.data,
            tipo=form.tipo.data,
            id_sede_fk=form.sede.data.id,
            capacidad=form.capacidad.data,
            cantidad_sillas=form.cantidad_sillas.data,
            cantidad_mesas=form.cantidad_mesas.data
        )
        db.session.add(nuevo_salon)
        db.session.commit()
        flash('Sala creada exitosamente ✅', 'success')
        return redirect(url_for('admin.salones'))
    return render_template('superadmin/gestion_inventario/registro_salon.html', title='Crear Nueva Sala', form=form)

@admin_bp.route('/registro_incidente', methods=['GET', 'POST'])
@login_required
@role_required('administrador')
def registro_incidente():
    """Muestra la página para registrar un incidente."""
    return render_template('superadmin/gestion_inventario/registro_incidente.html')

# --- Rutas para la Gestión de Usuarios ---

@admin_bp.route('/profesores')
@login_required
@role_required(1)
def profesores():
    """Muestra la página con la lista de profesores."""
    return render_template('superadmin/gestion_usuarios/profesores.html')

@admin_bp.route('/api/profesores')
@login_required
@role_required(1)
def api_profesores():
    try:
        rol_profesor = db.session.query(Rol).filter_by(nombre='Profesor').first()
        profesores = Usuario.query.filter_by(id_rol_fk=rol_profesor.id_rol).all() if rol_profesor else []
        lista_profesores = []
        for profesor in profesores:
            clases = Clase.query.filter_by(profesorId=profesor.id_usuario).all()
            cursos_asignados = set()
            materias_asignadas = set()
            sedes_asignadas = set()
            
            if clases:
                for clase in clases:
                    curso = Curso.query.filter_by(id=clase.cursoId).first()
                    if curso:
                        cursos_asignados.add(curso.nombreCurso)
                        sede = Sede.query.filter_by(id=curso.sedeId).first()
                        if sede:
                            sedes_asignadas.add(sede.nombre)
                    asignatura = Asignatura.query.filter_by(id=clase.asignaturaId).first()
                    if asignatura:
                        materias_asignadas.add(asignatura.nombre)
            
            if not cursos_asignados: cursos_asignados.add('Sin asignar')
            if not materias_asignadas: materias_asignadas.add('Sin asignar')
            if not sedes_asignadas: sedes_asignadas.add('Sin asignar')

            lista_profesores.append({
                'id_usuario': profesor.id_usuario,
                'no_identidad': profesor.no_identidad,
                'nombre_completo': f"{profesor.nombre} {profesor.apellido}",
                'correo': profesor.correo,
                'rol': profesor.rol.nombre if profesor.rol else 'N/A',
                'estado_cuenta': profesor.estado_cuenta,
                'curso_asignado': ", ".join(cursos_asignados),
                'materia_area': ", ".join(materias_asignadas),
                'sede_asignada': ", ".join(sedes_asignadas)
            })
            
        return jsonify({"data": lista_profesores})
    except Exception as e:
        print(f"Error en la API de profesores: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@admin_bp.route('/estudiantes')
@login_required
@role_required(1)
def estudiantes():
    """Muestra la página con la lista de estudiantes."""
    rol_estudiante = db.session.query(Rol).filter_by(nombre='Estudiante').first()
    estudiantes = db.session.query(Usuario).filter_by(id_rol_fk=rol_estudiante.id_rol).all() if rol_estudiante else []
    return render_template('superadmin/gestion_usuarios/estudiantes.html', estudiantes=estudiantes)

@admin_bp.route('/api/directorio/estudiantes', methods=['GET'])
@login_required
@role_required(1) 
def api_estudiantes_directorio():
    """API para obtener el directorio de estudiantes con su curso y sede."""
    try:
        search_query = request.args.get('q', '')
        
        rol_estudiante = db.session.query(Rol).filter_by(nombre='Estudiante').first()
        if not rol_estudiante:
            return jsonify({"data": [], "message": "Rol de estudiante no encontrado"}), 404

        subquery = db.session.query(
            Matricula.estudianteId,
            db.func.max(Matricula.año).label('max_year')
        ).group_by(Matricula.estudianteId).subquery()

        query = db.session.query(
            Usuario,
            Curso.nombreCurso,
            Sede.nombre
        ).filter(
            Usuario.id_rol_fk == rol_estudiante.id_rol
        ).outerjoin(
            subquery, subquery.c.estudianteId == Usuario.id_usuario
        ).outerjoin(
            Matricula,
            (Matricula.estudianteId == subquery.c.estudianteId) & (Matricula.año == subquery.c.max_year)
        ).outerjoin(
            Curso, Curso.id == Matricula.cursoId
        ).outerjoin(
            Sede, Sede.id == Curso.sedeId
        )
        
        if search_query:
            query = query.filter(
                db.or_(
                    Usuario.nombre.ilike(f'%{search_query}%'),
                    Usuario.apellido.ilike(f'%{search_query}%'),
                    Usuario.no_identidad.ilike(f'%{search_query}%')
                )
            )

        estudiantes = query.all()
        
        lista_estudiantes = []
        for usuario, curso_nombre, sede_nombre in estudiantes:
            curso_final = curso_nombre if curso_nombre else "Sin curso"
            sede_final = sede_nombre if sede_nombre else "Sin sede"
            
            lista_estudiantes.append({
                'no_identidad': usuario.no_identidad,
                'nombre_completo': usuario.nombre_completo,
                'correo': usuario.correo,
                'curso': curso_final,
                'sede': sede_final,
                'estado_cuenta': usuario.estado_cuenta,
            })
            
        return jsonify({"data": lista_estudiantes, "message": "Directorio cargado exitosamente."}), 200

    except Exception as e:
        print(f"Error en la API de directorio de estudiantes: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@admin_bp.route('/padres')
@login_required
@role_required(1)
def padres():
    """Muestra la página con la lista de padres."""
    return render_template('superadmin/gestion_usuarios/padres.html')

@admin_bp.route('/superadmins')
@login_required
@role_required(1)
def superadmins():
    return render_template('superadmin/gestion_usuarios/administrativos.html')

@admin_bp.route('/api/padres')
@login_required
@role_required(1)
def api_padres():
    try:
        rol_padre = db.session.query(Rol).filter_by(nombre='Padre').first()
        padres = Usuario.query.filter_by(id_rol_fk=rol_padre.id_rol).all() if rol_padre else []
        lista_padres = []
        for padre in padres:
            hijos_asignados = []
    
            lista_padres.append({
                'id_usuario': padre.id_usuario,
                'no_identidad': padre.no_identidad,
                'nombre_completo': f"{padre.nombre} {padre.apellido}",
                'correo': padre.correo,
                'rol': padre.rol.nombre if padre.rol else 'N/A',
                'estado_cuenta': padre.estado_cuenta,
                'hijos_asignados': hijos_asignados # Placeholder
            })
        return jsonify({"data": lista_padres})
    except Exception as e:
        print(f"Error en la API de padres: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@admin_bp.route('/api/superadmins')
@login_required
@role_required(1)
def api_superadmins():
    try:
        superadmins = Usuario.query.filter_by(id_rol_fk=1).all()
        lista_superadmins = []
        for superadmin in superadmins:
            lista_superadmins.append({
                'id_usuario': superadmin.id_usuario,
                'no_identidad': superadmin.no_identidad,
                'nombre_completo': f"{superadmin.nombre} {superadmin.apellido}",
                'correo': superadmin.correo,
                'rol': superadmin.rol.nombre if superadmin.rol else 'N/A',
                'estado_cuenta': superadmin.estado_cuenta
            })
        return jsonify({"data": lista_superadmins})
    except Exception as e:
        print(f"Error en la API de superadmins: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@admin_bp.route('/gestion-academica')
@login_required
@role_required(1)
def gestion_academica():
    return render_template('superadmin/gestion_academica/dashboard.html')

# === SISTEMA DE HORARIOS ===
@admin_bp.route('/gestion-horarios')
@login_required
@role_required(1)
def gestion_horarios():
    return render_template('superadmin/Horarios/gestion_horarios.html')

@admin_bp.route('/api/horarios/nuevo', methods=['POST'])
@login_required
@role_required(1)
def api_crear_horario_completo():
    try:
        data = request.get_json()
        
        if not data.get('nombre'):
            return jsonify({'success': False, 'error': 'El nombre del horario es requerido'}), 400
        
        dias = data.get('dias', [])
        if not dias:
            return jsonify({'success': False, 'error': 'Seleccione al menos un día'}), 400
        
        bloques = data.get('bloques', [])
        if not bloques:
            return jsonify({'success': False, 'error': 'Agregue al menos un bloque horario'}), 400
        
        nuevo_horario = HorarioGeneral(
            nombre=data.get('nombre'),
            periodo=data.get('periodo', 'Primer Semestre'),
            horaInicio=datetime.strptime(data.get('horaInicio', '07:00'), '%H:%M').time(),
            horaFin=datetime.strptime(data.get('horaFin', '17:00'), '%H:%M').time(),
            diasSemana=json.dumps(dias),
            duracion_clase=data.get('duracion_clase', 45),
            duracion_descanso=data.get('duracion_descanso', 15),
            activo=True
        )
        db.session.add(nuevo_horario)
        db.session.flush()
        
        for i, bloque_data in enumerate(bloques):
            if not all(key in bloque_data for key in ['dia_semana', 'horaInicio', 'horaFin', 'tipo']):
                continue
                
            try:
                nuevo_bloque = BloqueHorario(
                    horario_general_id=nuevo_horario.id,
                    dia_semana=bloque_data['dia_semana'],
                    horaInicio=datetime.strptime(bloque_data['horaInicio'], '%H:%M').time(),
                    horaFin=datetime.strptime(bloque_data['horaFin'], '%H:%M').time(),
                    tipo=bloque_data['tipo'],
                    nombre=bloque_data.get('nombre', f'Bloque {i+1}'),
                    orden=bloque_data.get('orden', i),
                    class_type=bloque_data.get('class_type'),
                    break_type=bloque_data.get('break_type')
                )
                db.session.add(nuevo_bloque)
            except ValueError:
                continue
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Horario creado correctamente',
            'horario': {
                'id': nuevo_horario.id,
                'nombre': nuevo_horario.nombre,
                'periodo': nuevo_horario.periodo
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error creating schedule: {str(e)}")
        return jsonify({'success': False, 'error': f'Error del servidor: {str(e)}'}), 500

@admin_bp.route('/api/horarios/<int:horario_id>', methods=['GET'])
@login_required
@role_required(1)
def api_obtener_horario(horario_id):
    try:
        horario = HorarioGeneral.query.get_or_404(horario_id)
        
        bloques = BloqueHorario.query.filter_by(horario_general_id=horario_id)\
                                    .order_by(BloqueHorario.orden)\
                                    .all()
        
        try:
            dias_lista = json.loads(horario.diasSemana) if horario.diasSemana else []
        except:
            dias_lista = []
        
        return jsonify({
            'id': horario.id,
            'nombre': horario.nombre,
            'periodo': horario.periodo,
            'horaInicio': horario.horaInicio.strftime('%H:%M'),
            'horaFin': horario.horaFin.strftime('%H:%M'),
            'dias': dias_lista,
            'bloques': [{
                'id': b.id,
                'dia_semana': b.dia_semana,
                'horaInicio': b.horaInicio.strftime('%H:%M'),
                'horaFin': b.horaFin.strftime('%H:%M'),
                'tipo': b.tipo,
                'nombre': b.nombre,
                'class_type': b.class_type,
                'break_type': b.break_type
            } for b in bloques]
        })
        
    except Exception as e:
        print(f"❌ Error getting schedule: {str(e)}")
        return jsonify({'error': f'Error al obtener horario: {str(e)}'}), 500

@admin_bp.route('/api/horarios', methods=['GET'])
@login_required
@role_required(1)
def api_listar_horarios():
    try:
        horarios = HorarioGeneral.query.all()
        return jsonify([{
            'id': h.id,
            'nombre': h.nombre,
            'periodo': h.periodo,
            'horaInicio': h.horaInicio.strftime('%H:%M'),
            'horaFin': h.horaFin.strftime('%H:%M'),
            'activo': h.activo,
            'totalCursos': len(h.cursos)
        } for h in horarios])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/horarios/<int:horario_id>', methods=['DELETE'])
@login_required
@role_required(1)
def api_eliminar_horario(horario_id):
    try:
        horario = HorarioGeneral.query.get_or_404(horario_id)
        
        BloqueHorario.query.filter_by(horario_general_id=horario_id).delete()
        
        Curso.query.filter_by(horario_general_id=horario_id).update({'horario_general_id': None})
        
        db.session.delete(horario)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Horario eliminado correctamente'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/horarios/asignar', methods=['POST'])
@login_required
@role_required(1)
def api_asignar_horario_curso():
    try:
        data = request.get_json()
        horario_id = data.get('horario_id')
        cursos_ids = data.get('cursos_ids', [])
        
        if not horario_id:
            return jsonify({'success': False, 'error': 'ID de horario requerido'}), 400
        
        horario = HorarioGeneral.query.get(horario_id)
        if not horario:
            return jsonify({'success': False, 'error': 'Horario no encontrado'}), 404
        
        cursos_asignados = 0
        for curso_id in cursos_ids:
            curso = Curso.query.get(curso_id)
            if curso:
                curso.horario_general_id = horario_id
                cursos_asignados += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Horario "{horario.nombre}" asignado a {cursos_asignados} cursos',
            'cursos_asignados': cursos_asignados
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/estadisticas/horarios')
@login_required
@role_required(1)
def api_estadisticas_horarios():
    try:
        total_cursos = Curso.query.count()
        
        rol_profesor = Rol.query.filter_by(nombre='Profesor').first()
        total_profesores = Usuario.query.filter_by(id_rol_fk=rol_profesor.id_rol).count() if rol_profesor else 0
        
        horarios_activos = HorarioGeneral.query.filter_by(activo=True).count()
        total_salones = Salon.query.count()
        
        salones_ocupados = Curso.query.filter(Curso.horario_general_id.isnot(None)).count()
        salones_libres = max(0, total_salones - salones_ocupados)
        
        return jsonify({
            'total_cursos': total_cursos,
            'total_profesores': total_profesores,
            'horarios_activos': horarios_activos,
            'salones_libres': salones_libres,
            'total_salones': total_salones
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/gestion-horarios-cursos')
@login_required
@role_required(1)
def gestion_horarios_cursos():
    return render_template('superadmin/Horarios/gestion_horarios_cursos.html')

@admin_bp.route('/api/horario_curso/guardar', methods=['POST'])
@login_required
@role_required(1)
def api_guardar_horario_curso():
    try:
        data = request.get_json()
        curso_id = data.get('curso_id')
        horario_general_id = data.get('horario_general_id')
        asignaciones = data.get('asignaciones', {})
        salones_asignaciones = data.get('salones_asignaciones', {}) 

        if not curso_id:
            return jsonify({'success': False, 'error': 'ID de curso requerido'}), 400

        curso = Curso.query.get(curso_id)
        if not curso:
            return jsonify({'success': False, 'error': 'Curso no encontrado'}), 404

        if horario_general_id:
            horario = HorarioGeneral.query.get(horario_general_id)
            if not horario:
                return jsonify({'success': False, 'error': 'Horario general no encontrado'}), 404
            curso.horario_general_id = horario_general_id

        # Eliminar asignaciones existentes
        HorarioCurso.query.filter_by(curso_id=curso_id).delete()

        asignaciones_creadas = 0
        # Procesar asignaciones de materias
        for clave, asignatura_id in asignaciones.items():
            try:
                partes = clave.split('-')
                if len(partes) >= 2:
                    dia = partes[0]
                    hora = partes[1]

                    if not asignatura_id:
                        continue

                    # Obtener el salon_id correspondiente
                    salon_id = salones_asignaciones.get(clave)

                    nueva_asignacion = HorarioCurso(
                        curso_id=curso_id,
                        asignatura_id=asignatura_id,
                        dia_semana=dia,
                        hora_inicio=hora,
                        horario_general_id=horario_general_id,
                        id_salon_fk=salon_id  # ← ASIGNAR EL SALÓN
                    )
                    db.session.add(nueva_asignacion)
                    asignaciones_creadas += 1

            except Exception as e:
                print(f"❌ Error procesando asignación {clave}: {str(e)}")
                continue

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Horario del curso guardado correctamente ({asignaciones_creadas} asignaciones)',
            'asignaciones_creadas': asignaciones_creadas
        })

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error guardando horario del curso: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@admin_bp.route('/api/horario_curso/cargar/<int:curso_id>')
@login_required
@role_required(1)
def api_cargar_horario_curso(curso_id):
    try:
        curso = Curso.query.get(curso_id)
        if not curso:
            return jsonify({'error': 'Curso no encontrado'}), 404

        asignaciones_db = HorarioCurso.query.filter_by(curso_id=curso_id).all()

        asignaciones = {}
        salones_asignaciones = {}  # ← AGREGAR ESTO
        
        for asignacion in asignaciones_db:
            clave = f"{asignacion.dia_semana}-{asignacion.hora_inicio}"
            asignaciones[clave] = asignacion.asignatura_id
            if asignacion.id_salon_fk:  # ← AGREGAR SALÓN SI EXISTE
                salones_asignaciones[clave] = asignacion.id_salon_fk

        bloques_horario = []
        if curso.horario_general_id:
            bloques = BloqueHorario.query.filter_by(
                horario_general_id=curso.horario_general_id
            ).order_by(BloqueHorario.orden).all()

            bloques_horario = [{
                'id': b.id,
                'dia_semana': b.dia_semana,
                'horaInicio': b.horaInicio.strftime('%H:%M'),
                'horaFin': b.horaFin.strftime('%H:%M'),
                'tipo': b.tipo,
                'nombre': b.nombre,
                'class_type': b.class_type,
                'break_type': b.break_type
            } for b in bloques]

        return jsonify({
            'curso_id': curso_id,
            'horario_general_id': curso.horario_general_id,
            'nombre_curso': curso.nombreCurso,
            'asignaciones': asignaciones,
            'salones_asignaciones': salones_asignaciones,  # ← INCLUIR SALONES
            'bloques_horario': bloques_horario,
            'tiene_horario_general': curso.horario_general_id is not None
        })

    except Exception as e:
        print(f"❌ Error cargando horario del curso: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/horario_curso/compartir', methods=['POST'])
@login_required
@role_required(1)
def api_compartir_horario():
    try:
        data = request.get_json()
        curso_id = data.get('curso_id')
        destinatario = data.get('destinatario')
        horario_general_id = data.get('horario_general_id')
        asignaciones = data.get('asignaciones', {})
        salones_asignaciones = data.get('salones_asignaciones', {})

        if not curso_id or not destinatario:
            return jsonify({'success': False, 'error': 'Datos incompletos'}), 400

        curso = Curso.query.get(curso_id)
        if not curso:
            return jsonify({'success': False, 'error': 'Curso no encontrado'}), 404

        if destinatario == 'profesores':
            # Identificar profesores asignados en el horario
            profesores_asignados = set()
            
            for clave, asignatura_id in asignaciones.items():
                if asignatura_id:
                    # Obtener profesores de esta asignatura
                    asignatura = Asignatura.query.get(asignatura_id)
                    if asignatura and asignatura.profesores:
                        for profesor in asignatura.profesores:
                            profesores_asignados.add(profesor)
            
            # Guardar relaciones profesor-curso-horario
            for profesor in profesores_asignados:
                # Para cada asignatura que el profesor tiene en este horario
                for clave, asignatura_id in asignaciones.items():
                    if asignatura_id:
                        asignatura = Asignatura.query.get(asignatura_id)
                        if asignatura and profesor in asignatura.profesores:
                            # Verificar si ya existe esta relación
                            existe = HorarioCompartido.query.filter_by(
                                profesor_id=profesor.id_usuario,
                                curso_id=curso_id,
                                asignatura_id=asignatura_id
                            ).first()
                            
                            if not existe:
                                nuevo_horario_compartido = HorarioCompartido(
                                    profesor_id=profesor.id_usuario,
                                    curso_id=curso_id,
                                    asignatura_id=asignatura_id,
                                    horario_general_id=horario_general_id
                                )
                                db.session.add(nuevo_horario_compartido)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Horario compartido con {len(profesores_asignados)} profesores correctamente',
                'profesores_asignados': len(profesores_asignados)
            })
            
        elif destinatario == 'estudiantes':
            # Lógica para estudiantes (si es necesario)
            return jsonify({
                'success': True,
                'message': 'Horario compartido con estudiantes correctamente'
            })
        else:
            return jsonify({'success': False, 'error': 'Destinatario no válido'}), 400

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error compartiendo horario: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/estadisticas/horarios-cursos')
@login_required
@role_required(1)
def api_estadisticas_horarios_cursos():
    try:
        total_cursos = Curso.query.count()
        cursos_con_horario = Curso.query.filter(Curso.horario_general_id.isnot(None)).count()
        total_asignaturas = Asignatura.query.count()
        
        porcentaje_asignados = (cursos_con_horario / total_cursos * 100) if total_cursos > 0 else 0
        
        return jsonify({
            'total_cursos': total_cursos,
            'horarios_asignados': cursos_con_horario,
            'total_materias': total_asignaturas,
            'porcentaje_asignados': round(porcentaje_asignados, 1)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/cursos/<int:curso_id>')
@login_required
@role_required(1)
def api_obtener_curso(curso_id):
    try:
        curso = Curso.query.get_or_404(curso_id)
        
        return jsonify({
            'id': curso.id,
            'nombreCurso': curso.nombreCurso,
            'sedeId': curso.sedeId,
            'horario_general_id': curso.horario_general_id,
            'sede': curso.sede.nombre if curso.sede else None
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== GESTIÓN DE USUARIOS - FORMULARIOS ====================
@admin_bp.route('/crear_usuario', methods=['GET', 'POST'])
@login_required
@role_required(1)
def crear_usuario():
    form = RegistrationForm()
    
    roles = db.session.query(Rol).all()
    cursos = db.session.query(Curso).all()
    form.rol.choices = [(str(r.id_rol), r.nombre) for r in roles]

    if form.validate_on_submit():
        selected_role_id = int(form.rol.data)
        
        rol_estudiante = db.session.query(Rol).filter_by(nombre='Estudiante').first()
        rol_profesor = db.session.query(Rol).filter_by(nombre='Profesor').first()

        is_student = (rol_estudiante and selected_role_id == rol_estudiante.id_rol)
        is_professor = (rol_profesor and selected_role_id == rol_profesor.id_rol)

        new_user = Usuario(
            tipo_doc=form.tipo_doc.data,
            no_identidad=form.no_identidad.data,
            nombre=form.nombre.data,
            apellido=form.apellido.data,
            correo=form.correo.data,
            telefono=form.telefono.data,
            id_rol_fk=selected_role_id,
            estado_cuenta='activa'
        )
        new_user.set_password(form.password.data)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            
            if is_student:
                if form.curso_id.data and form.anio_matricula.data:
                    nueva_matricula = Matricula(
                        estudianteId=new_user.id_usuario,
                        cursoId=form.curso_id.data.id,
                        año=int(form.anio_matricula.data)
                    )
                    db.session.add(nueva_matricula)
                    db.session.commit()
                else:
                    flash('Se requiere curso y año de matrícula para un estudiante.', 'warning')
                    db.session.rollback()
                    return redirect(url_for('admin.crear_usuario'))

            elif is_professor:
                if form.asignatura_id.data and form.curso_asignacion_id.data:
                    new_clase = Clase(
                        profesorId=new_user.id_usuario,
                        asignaturaId=form.asignatura_id.data.id,
                        cursoId=form.curso_asignacion_id.data.id,
                        horarioId=1
                    )
                    db.session.add(new_clase)
                    db.session.commit()
                else:
                    flash('Se requiere asignatura y curso para un profesor.', 'warning')
                    db.session.rollback()
                    return redirect(url_for('admin.crear_usuario'))
            
            flash(f'Usuario "{new_user.nombre_completo}" creado exitosamente!', 'success')
            return redirect(url_for('admin.profesores'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el usuario o la asignación: {e}', 'danger')
            return redirect(url_for('admin.crear_usuario'))

    return render_template(
        'superadmin/gestion_usuarios/crear_usuario.html',
        title='Crear Nuevo Usuario',
        form=form,
        cursos=cursos,
        now=date.today
    )

@admin_bp.route('/editar_usuario/<int:user_id>', methods=['GET', 'POST'])
@login_required
@role_required(1)
def editar_usuario(user_id):
    user = db.session.query(Usuario).get_or_404(user_id)
    form = UserEditForm(original_no_identidad=user.no_identidad, original_correo=user.correo)

    if request.method == 'GET':
        form.tipo_doc.data = user.tipo_doc
        form.no_identidad.data = user.no_identidad
        form.nombre.data = user.nombre
        form.apellido.data = user.apellido
        form.correo.data = user.correo
        form.telefono.data = getattr(user, 'telefono', '')
        form.estado_cuenta.data = getattr(user, 'estado_cuenta', 'activa')
        form.rol.data = user.rol
    
    if form.validate_on_submit():
        user.tipo_doc = form.tipo_doc.data
        user.no_identidad = form.no_identidad.data
        user.nombre = form.nombre.data
        user.apellido = form.apellido.data
        user.correo = form.correo.data
        user.telefono = form.telefono.data
        user.estado_cuenta = form.estado_cuenta.data
        user.rol = form.rol.data
        db.session.commit()
        flash(f'Usuario "{user.nombre_completo}" actualizado exitosamente!', 'success')
        return redirect(url_for('admin.profesores'))

    return render_template('superadmin/gestion_usuarios/editar_perfil.html',
                           title='Editar Usuario', form=form, user=user)

@admin_bp.route('/eliminar_usuario/<int:user_id>', methods=['POST'])
@login_required
@role_required(1)
def eliminar_usuario(user_id):
    user = db.session.query(Usuario).get_or_404(user_id)
    if current_user.id_usuario == user.id_usuario or user.has_role('administrador'):
        flash('No puedes eliminar tu propia cuenta o la de otro administrador.', 'danger')
        return redirect(url_for('admin.profesores'))
    
    db.session.delete(user)
    db.session.commit()
    flash(f'Usuario "{user.nombre_completo}" eliminado exitosamente.', 'success')
    return redirect(url_for('admin.profesores'))

# ==================== GESTIÓN DE SEDES ====================
@admin_bp.route('/gestion_sedes')
@login_required
@role_required(1)
def gestion_sedes():
    form = SedeForm()
    return render_template('superadmin/gestion_academica/sedes.html', form=form)

@admin_bp.route('/api/salones', methods=['GET'])
@login_required
@role_required(1)
def api_salones():
    try:
        salones = Salon.query.order_by(Salon.nombre).all()
        return jsonify([{
            'id': s.id,
            'nombre': s.nombre,
            'capacidad': s.capacidad
        } for s in salones])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== GESTIÓN DE CURSOS ====================
@admin_bp.route('/gestion_cursos')
@login_required
@role_required(1)
def gestion_cursos():
    form = CursoForm()
    return render_template('superadmin/gestion_academica/cursos.html', form=form)

@admin_bp.route('/api/cursos', methods=['GET', 'POST', 'DELETE'])
@login_required
@role_required(1)
def api_cursos():
    if request.method == 'GET':
        try:
            cursos = db.session.query(Curso, Sede.nombre).join(Sede).all()
            cursos_list = [{
                'id': c.id,
                'nombreCurso': c.nombreCurso,
                'sede': sede_nombre,
                'horario_general_id': c.horario_general_id,
                'sedeId': c.sedeId
            } for c, sede_nombre in cursos]
            return jsonify({"data": cursos_list})
        except Exception as e:
            return jsonify({"error": "Error interno del servidor"}), 500

    elif request.method == 'POST':
        form = CursoForm()
        if form.validate_on_submit():
            try:
                sede = form.sedeId.data
                nuevo_curso = Curso(
                    nombreCurso=form.nombreCurso.data,
                    sedeId=sede.id if sede else None
                )
                db.session.add(nuevo_curso)
                db.session.commit()
                return jsonify({
                    'id': nuevo_curso.id,
                    'nombreCurso': nuevo_curso.nombreCurso,
                    'sede': sede.nombre if sede else 'N/A',
                    'horario_general_id': None
                }), 201
            except IntegrityError:
                db.session.rollback()
                return jsonify({'error': 'Este curso ya existe. Por favor, elige un nombre diferente.'}), 409
            except Exception as e:
                db.session.rollback()
                return jsonify({'error': f'Error interno: {str(e)}'}), 500
        else:
            errors = {field.name: field.errors for field in form if field.errors}
            return jsonify({'errors': errors}), 400

    elif request.method == 'DELETE':
        data = request.get_json()
        curso_id = data.get('id')
        if not curso_id:
            return jsonify({'error': 'ID del curso no proporcionado'}), 400
        
        curso = Curso.query.get(curso_id)
        if not curso:
            return jsonify({'error': 'Curso no encontrado'}), 404
        
        try:
            db.session.delete(curso)
            db.session.commit()
            return jsonify({'message': 'Curso eliminado'}), 200
        except IntegrityError:
            db.session.rollback()
            return jsonify({'error': 'No se puede eliminar el curso porque está asociado a estudiantes o clases. Elimina esas asociaciones primero.'}), 409
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Error interno: {str(e)}'}), 500

# ==================== GESTIÓN DE ASIGNATURAS ====================
@admin_bp.route('/gestion-asignaturas')
@login_required
@role_required(1)
def gestion_asignaturas():
    return render_template('superadmin/gestion_academica/gestion_asignaturas.html')

@admin_bp.route('/api/asignaturas')
@login_required
@role_required(1)
def api_asignaturas():
    """API para obtener todas las asignaturas con sus profesores"""
    try:
        asignaturas = Asignatura.query.order_by(Asignatura.nombre).all()
        return jsonify([{
            'id': a.id,
            'nombre': a.nombre,
            'descripcion': a.descripcion or '',
            'estado': getattr(a, 'estado', 'activa'),
            'profesores': [{
                'id_usuario': prof.id_usuario,
                'nombre_completo': prof.nombre_completo,
                'correo': prof.correo
            } for prof in a.profesores]
        } for a in asignaturas])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/asignaturas/crear', methods=['POST'])
@login_required
@role_required(1)
def api_crear_asignatura():
    """API para crear una nueva asignatura con profesores"""
    try:
        data = request.get_json()
        print("📝 Datos recibidos para crear asignatura:", data)
        
        if not data.get('nombre'):
            return jsonify({'success': False, 'error': 'El nombre de la asignatura es requerido'}), 400
        
        # Verificar si ya existe una asignatura con el mismo nombre
        existe = Asignatura.query.filter_by(nombre=data['nombre']).first()
        if existe:
            return jsonify({'success': False, 'error': 'Ya existe una asignatura con ese nombre'}), 400
        
        nueva_asignatura = Asignatura(
            nombre=data['nombre'],
            descripcion=data.get('descripcion', ''),
            estado=data.get('estado', 'activa')
        )
        
        db.session.add(nueva_asignatura)
        db.session.flush()  # Para obtener el ID
        
        # Asignar profesores
        profesores_ids = data.get('profesores', [])
        print(f"👨‍🏫 IDs de profesores a asignar: {profesores_ids}")
        
        for profesor_id in profesores_ids:
            profesor = Usuario.query.get(profesor_id)
            if profesor:
                print(f"✅ Asignando profesor: {profesor.nombre_completo}")
                nueva_asignatura.profesores.append(profesor)
            else:
                print(f"⚠️ Profesor con ID {profesor_id} no encontrado")
        
        db.session.commit()
        
        print(f"✅ Asignatura creada: {nueva_asignatura.nombre} con {len(profesores_ids)} profesores")
        
        return jsonify({
            'success': True,
            'message': 'Asignatura creada correctamente',
            'asignatura': {
                'id': nueva_asignatura.id,
                'nombre': nueva_asignatura.nombre,
                'descripcion': nueva_asignatura.descripcion,
                'estado': nueva_asignatura.estado,
                'profesores': [{
                    'id_usuario': prof.id_usuario,
                    'nombre_completo': prof.nombre_completo,
                    'correo': prof.correo
                } for prof in nueva_asignatura.profesores]
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error creando asignatura: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/asignaturas/<int:asignatura_id>', methods=['PUT'])
@login_required
@role_required(1)
def api_actualizar_asignatura(asignatura_id):
    """API para actualizar una asignatura existente con profesores"""
    try:
        data = request.get_json()
        print(f"📝 Datos recibidos para actualizar asignatura {asignatura_id}:", data)
        
        asignatura = Asignatura.query.get_or_404(asignatura_id)
        
        if not data.get('nombre'):
            return jsonify({'success': False, 'error': 'El nombre de la asignatura es requerido'}), 400
        
        # Verificar si ya existe otra asignatura con el mismo nombre
        existe = Asignatura.query.filter(
            Asignatura.nombre == data['nombre'],
            Asignatura.id != asignatura_id
        ).first()
        if existe:
            return jsonify({'success': False, 'error': 'Ya existe otra asignatura con ese nombre'}), 400
        
        asignatura.nombre = data['nombre']
        asignatura.descripcion = data.get('descripcion', '')
        asignatura.estado = data.get('estado', 'activa')
        
        # Actualizar profesores - limpiar y agregar nuevos
        profesores_ids = data.get('profesores', [])
        print(f"👨‍🏫 IDs de profesores para actualizar: {profesores_ids}")
        
        # Limpiar profesores actuales
        asignatura.profesores.clear()
        
        # Agregar nuevos profesores
        for profesor_id in profesores_ids:
            profesor = Usuario.query.get(profesor_id)
            if profesor:
                print(f"✅ Asignando profesor: {profesor.nombre_completo}")
                asignatura.profesores.append(profesor)
            else:
                print(f"⚠️ Profesor con ID {profesor_id} no encontrado")
        
        db.session.commit()
        
        print(f"✅ Asignatura actualizada: {asignatura.nombre} con {len(profesores_ids)} profesores")
        
        return jsonify({
            'success': True,
            'message': 'Asignatura actualizada correctamente',
            'asignatura': {
                'id': asignatura.id,
                'nombre': asignatura.nombre,
                'descripcion': asignatura.descripcion,
                'estado': asignatura.estado,
                'profesores': [{
                    'id_usuario': prof.id_usuario,
                    'nombre_completo': prof.nombre_completo,
                    'correo': prof.correo
                } for prof in asignatura.profesores]
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error actualizando asignatura: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/asignaturas/<int:asignatura_id>', methods=['DELETE'])
@login_required
@role_required(1)
def api_eliminar_asignatura(asignatura_id):
    try:
        asignatura = Asignatura.query.get_or_404(asignatura_id)
        
        clases_con_asignatura = Clase.query.filter_by(asignaturaId=asignatura_id).first()
        if clases_con_asignatura:
            return jsonify({
                'success': False, 
                'error': 'No se puede eliminar la asignatura porque está asignada a clases existentes'
            }), 400
        
        db.session.delete(asignatura)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Asignatura eliminada correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    
# --- Rutas del Sistema de Votación ---
@admin_bp.route('/sistema-votaciones')
@login_required
@role_required(1)  # Solo el rol Super Admin 
def sistema_votaciones():
    """Vista principal del sistema de votación."""
    return render_template('superadmin/sistema_votaciones/admin.html')

@admin_bp.route('/sistema-votaciones/votar')
@login_required
def votar():
    return render_template('superadmin/sistema_votaciones/votar.html')


# 📌 Vista del calendario de eventos (HTML)
@admin_bp.route("/eventos/calendario", methods=["GET"])
@login_required
def calendario_eventos():
    return render_template("superadmin/calendario_admin/index.html")

# 📌 API: Eliminar evento
@admin_bp.route("/eventos/<int:evento_id>", methods=["DELETE"])
@login_required
def eliminar_evento(evento_id):
    try:
        evento = Evento.query.get(evento_id)
        if not evento:
            return jsonify({"error": "Evento no encontrado"}), 404

        db.session.delete(evento)
        db.session.commit()
        return jsonify({"mensaje": "Evento eliminado correctamente ✅"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# 📌 API: Listar todos los eventos (JSON)
@admin_bp.route("/eventos", methods=["GET"])
@login_required
def listar_eventos():
    try:
        eventos = Evento.query.all()
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


# 📌 API: Crear un nuevo evento
@admin_bp.route("/eventos", methods=["POST"])
@login_required
def crear_evento():
    data = request.get_json()
    print("📥 Payload recibido:", data)  # Debug en consola

    try:
        # Leer valores (aceptando minúsculas o mayúsculas)
        nombre = data.get("nombre") or data.get("Nombre")
        descripcion = data.get("descripcion") or data.get("Descripcion")
        fecha_str = data.get("fecha") or data.get("Fecha")
        hora_str = data.get("hora") or data.get("Hora")
        rol_destino = data.get("rol_destino") or data.get("RolDestino")

        if not fecha_str or not hora_str:
            return jsonify({"error": "Faltan fecha u hora"}), 400

        # 🕒 Normalizar hora: quitar "a. m." / "p. m." y convertir a 24h
        hora_str = hora_str.replace("a. m.", "AM").replace("p. m.", "PM").strip()

        try:
            hora_dt = datetime.strptime(hora_str, "%I:%M %p")  # 12h → 24h
        except ValueError:
            hora_dt = datetime.strptime(hora_str[:5], "%H:%M")  # fallback

        nuevo_evento = Evento(
            nombre=nombre,
            descripcion=descripcion,
            fecha=datetime.strptime(fecha_str, "%Y-%m-%d").date(),
            hora=hora_dt.time(),
            rol_destino=rol_destino
        )

        db.session.add(nuevo_evento)
        db.session.commit()
        return jsonify({"mensaje": "Evento creado correctamente ✅"}), 201

    except Exception as e:
        db.session.rollback()
        print("❌ Error creando evento:", str(e))  # Debug en consola
        return jsonify({"error": str(e)}), 400





# -------------------------
# 📌 Listar candidatos
@admin_bp.route("/listar-candidatos", methods=["GET"])
@login_required
def listar_candidatos():
    candidatos = Candidato.query.all()
    lista = []
    for c in candidatos:
        lista.append({
            "id": c.id,
            "nombre": c.nombre,
            "categoria": c.categoria,
            "tarjeton": c.tarjeton,
            "propuesta": c.propuesta,
            "foto": c.foto
        })
    return jsonify(lista)





@admin_bp.route("/crear-candidato", methods=["POST"])
@login_required
def crear_candidato():
    try:
        nombre = request.form.get("nombre")
        tarjeton = request.form.get("tarjeton")
        propuesta = request.form.get("propuesta")
        categoria = request.form.get("categoria")
        foto = request.files.get("foto")

        if not nombre or not tarjeton or not propuesta or not categoria:
            return jsonify({"ok": False, "error": "Todos los campos son obligatorios"}), 400

        filename = None
        if foto:
            filename = secure_filename(foto.filename)
            path = os.path.join(current_app.static_folder, "images/candidatos", filename)
            foto.save(path)

        nuevo = Candidato(
            nombre=nombre,
            tarjeton=tarjeton,
            propuesta=propuesta,
            categoria=categoria,
            foto=filename
        )
        db.session.add(nuevo)
        db.session.commit()

        # devolver lista actualizada
        candidatos = Candidato.query.all()
        return jsonify({
            "ok": True,
            "candidatos": [c.to_dict() for c in candidatos]
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500





@admin_bp.route("/candidatos/<int:candidato_id>", methods=["PUT", "POST"])
def editar_candidato(candidato_id):
    try:
        candidato = Candidato.query.get(candidato_id)
        if not candidato:
            return jsonify({"ok": False, "error": "Candidato no encontrado"}), 404

        nombre = request.form.get("nombre", "").strip()
        propuesta = request.form.get("propuesta", "").strip()
        categoria = request.form.get("categoria", "").strip()
        tarjeton = request.form.get("tarjeton", "").strip()
        file = request.files.get("foto")

        # ✅ Validar obligatorios (excepto foto, que puede quedar igual)
        if not nombre or not propuesta or not categoria or not tarjeton:
            return jsonify({"ok": False, "error": "Todos los campos son obligatorios"}), 400

        # ✅ Validar tarjetón único (ignora el del propio candidato)
        existe_tarjeton = Candidato.query.filter(
            Candidato.tarjeton == tarjeton,
            Candidato.id != candidato.id
        ).first()
        if existe_tarjeton:
            return jsonify({"ok": False, "error": "⚠️ Ese número de tarjetón ya existe"}), 400

        # ✅ Validar nombre único
        existe_nombre = Candidato.query.filter(
            Candidato.nombre == nombre,
            Candidato.id != candidato.id
        ).first()
        if existe_nombre:
            return jsonify({"ok": False, "error": "⚠️ Ya existe un candidato con ese nombre"}), 400

        # ✅ Si subió nueva foto, guardarla
        if file:
            ext_permitidas = {"png", "jpg", "jpeg", "gif"}
            if "." not in file.filename or file.filename.rsplit(".", 1)[1].lower() not in ext_permitidas:
                return jsonify({"ok": False, "error": "Formato de imagen inválido"}), 400

            ext = file.filename.rsplit(".", 1)[1].lower()
            foto_filename = f"{secure_filename(nombre)}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
            path = os.path.join(current_app.config["UPLOAD_FOLDER"], foto_filename)
            file.save(path)
            candidato.foto = foto_filename  # 👈 actualiza foto

        # ✅ Actualizar campos
        candidato.nombre = nombre
        candidato.propuesta = propuesta
        candidato.categoria = categoria
        candidato.tarjeton = tarjeton

        db.session.commit()

        # ✅ Retornar candidatos actualizados
        candidatos = Candidato.query.all()
        candidatos_json = [
            {
                "id": c.id,
                "nombre": c.nombre,
                "propuesta": c.propuesta,
                "categoria": c.categoria,
                "tarjeton": c.tarjeton,
                "foto": c.foto,
                "votos": c.votos if hasattr(c, "votos") else 0
            }
            for c in candidatos
        ]

        return jsonify({"ok": True, "mensaje": "Candidato actualizado correctamente", "candidatos": candidatos_json}), 200

    except Exception as e:
        db.session.rollback()
        print("❌ Error al editar candidato:", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@admin_bp.route("/candidatos/<int:candidato_id>", methods=["DELETE"])
@login_required
def eliminar_candidato(candidato_id):
    try:
        candidato = Candidato.query.get(candidato_id)
        if not candidato:
            return jsonify({"ok": False, "error": "Candidato no encontrado"}), 404

        db.session.delete(candidato)
        db.session.commit()

        # Devolver la lista actualizada de candidatos para refrescar resultados
        candidatos = Candidato.query.all()
        candidatos_data = [
            {
                "id": c.id,
                "nombre": c.nombre,
                "categoria": c.categoria,
                "tarjeton": c.tarjeton,
                "propuesta": c.propuesta,
                "votos": c.votos
            }
            for c in candidatos
        ]

        return jsonify({"ok": True, "candidatos": candidatos_data}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500



@admin_bp.route("/guardar-horario", methods=["POST"])
@login_required
def guardar_horario():
    try:
        inicio = request.form.get("inicio")
        fin = request.form.get("fin")

        if not inicio or not fin:
            flash("Debe ingresar inicio y fin del horario", "danger")
            return redirect(url_for("admin.admin_panel"))

        # Guardar nuevo horario (sobrescribe anterior)
        horario = HorarioVotacion.query.first()
        if horario:
            horario.inicio = datetime.strptime(inicio, "%H:%M").time()
            horario.fin = datetime.strptime(fin, "%H:%M").time()
        else:
            nuevo = HorarioVotacion(
                inicio=datetime.strptime(inicio, "%H:%M").time(),
                fin=datetime.strptime(fin, "%H:%M").time()
            )
            db.session.add(nuevo)

        db.session.commit()
        flash("✅ Horario de votación guardado correctamente", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al guardar horario: {str(e)}", "danger")

    return redirect(url_for("admin.admin_panel"))

# 📌 Obtener último horario en JSON
@admin_bp.route("/ultimo-horario", methods=["GET"])
@login_required
def ultimo_horario():
    horario = HorarioVotacion.query.order_by(HorarioVotacion.id.desc()).first()
    if horario:
        return jsonify({
            "inicio": horario.inicio.strftime("%H:%M"),
            "fin": horario.fin.strftime("%H:%M")
        })
    return jsonify({})
