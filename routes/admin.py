from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from controllers.decorators import role_required
from extensions import db
from datetime import datetime, timedelta, time, date
from controllers.forms import RegistrationForm, UserEditForm, SalonForm, CursoForm, SedeForm, EquipoForm
from controllers.models import Usuario, Rol, Clase, Curso, Asignatura, Sede, Salon, HorarioGeneral, HorarioCompartido, Matricula, BloqueHorario, HorarioCurso, Equipo, Incidente, Mantenimiento
from sqlalchemy.exc import IntegrityError
import json

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
        nuevo_equipo = Equipo(
            id_referencia=form.id_referencia.data,
            nombre=form.nombre.data,
            tipo=form.tipo.data,
            estado=form.estado.data,
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
            # Aquí va toda la lógica de actualización (como se indicó previamente)
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

            db.session.commit()
            return jsonify({'success': True, 'message': 'Equipo actualizado exitosamente'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': f'Error al actualizar el equipo: {str(e)}'}), 500
            
    # Lógica de VISTA (GET)
    if request.method == 'GET':
        # Aquí va la lógica para obtener los detalles del equipo (ya existente)
        data = equipo.to_dict()
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
    salones = db.session.query(Salon).all()
    return render_template('superadmin/gestion_inventario/salones.html', salones=salones)

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
def api_salas(sede_id):
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
            'sede_id': salon.id_sede_fk,   # 🔹 unificado con /api/salas_todas
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
def api_equipos(sede_id, salon_id):
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
            # Incluye todos los demás estados
            **estados 
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

@admin_bp.route('/mantenimiento')
@role_required(1)
def mantenimiento():
    """Muestra la página de mantenimiento de equipos."""
    return render_template('superadmin/gestion_inventario/mantenimiento.html')

@admin_bp.route('/gestion-salones')
def gestion_salones():
    """Muestra la página de gestión de salones con estadísticas."""
    salones = db.session.query(Salon).all()
    total_salones = db.session.query(Salon).count()
    salas_computo = db.session.query(Salon).filter_by(tipo='sala_computo').count()
    aulas = db.session.query(Salon).filter_by(tipo='aula').count()
    laboratorios = db.session.query(Salon).filter_by(tipo='laboratorio').count()
    auditorios = db.session.query(Salon).filter_by(tipo='auditorio').count()

    return render_template(
        'superadmin/gestion_inventario/salones.html',
        salones=salones,
        total_salones=total_salones,
        salas_computo=salas_computo,
        aulas=aulas,
        laboratorios=laboratorios,
        auditorios=auditorios
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
            id_sede_fk=form.sede.data.id
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