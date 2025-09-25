# Importaciones necesarias para que todo el sistema funcione ⚙️
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from controllers.decorators import role_required
from extensions import db
from datetime import datetime, timedelta, time, date
from controllers.forms import RegistrationForm, UserEditForm, SalonForm, CursoForm, SedeForm, EquipoForm
from controllers.models import db, Usuario, Rol, Clase, Curso, Asignatura, Sede, Salon, HorarioGeneral, Descanso, Matricula, Equipo, Incidente, Mantenimiento
from sqlalchemy.exc import IntegrityError

# Creamos un 'Blueprint' (un plano o borrador) para agrupar todas las rutas de la sección de admin
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# --- Rutas de Navegación y Vistas Principales ---
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
@role_required(1)
def api_sedes():
    """
    Endpoint para gestionar sedes (Listar, Crear, Eliminar).
    GET: Devuelve todas las sedes.
    POST: Crea una nueva sede.
    DELETE: Elimina una sede por su ID.
    """
    if request.method == 'GET':
        sedes = Sede.query.order_by(Sede.nombre).all()
        return jsonify([{"id": sede.id, "nombre": sede.nombre, "direccion": sede.direccion} for sede in sedes]), 200

    if request.method == 'POST':
        data = request.get_json()
        nombre = data.get("nombre")
        direccion = data.get("direccion", "Dirección por defecto")

        if not nombre:
            return jsonify({"error": "El nombre de la sede es obligatorio"}), 400

        try:
            nueva_sede = Sede(nombre=nombre, direccion=direccion)
            db.session.add(nueva_sede)
            db.session.commit()
            return jsonify({"message": "Sede creada exitosamente", "sede_id": nueva_sede.id}), 201
        except IntegrityError:
            db.session.rollback()
            return jsonify({"error": "Ya existe una sede con ese nombre"}), 409
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

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
        except Exception:
            db.session.rollback()
            return jsonify({"error": "No se pudo eliminar la sede"}), 500

    return jsonify({"error": "Método no permitido"}), 405


@admin_bp.route('/api/sedes/<int:sede_id>/salas')
def api_salas(sede_id):
    salones = Salon.query.filter_by(id_sede_fk=sede_id).all()
    return jsonify([{"id": s.id, "nombre": s.nombre, "tipo": s.tipo} for s in salones])

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
@role_required(1)
def reportes():
    """Muestra la página de reportes de inventario."""
    return render_template('superadmin/gestion_inventario/reportes.html')

@admin_bp.route('/incidentes')
@role_required(1)
def incidentes():
    """Muestra la página de gestión de incidentes."""
    return render_template('superadmin/gestion_inventario/incidentes.html')

# ===============================
# API de Incidentes
# ===============================
@admin_bp.route('/api/incidentes', methods=['GET'])
@login_required
@role_required(1)
def api_incidentes():
    data = []

    # 1. Obtener incidentes registrados
    incidentes = Incidente.query.all()
    for inc in incidentes:
        data.append({
            "id": inc.id,
            "equipo_id": inc.equipo_id,
            "equipo_nombre": inc.equipo.nombre if inc.equipo else "Sin equipo",
            "usuario_asignado": inc.usuario_asignado or "",
            "sede": inc.sede,
            "fecha": inc.fecha.strftime("%Y-%m-%d"),
            "descripcion": inc.descripcion,
            "estado": inc.estado or ""
        })

    # 2. Obtener equipos en mantenimiento (que no estén en incidentes)
    equipos_mantenimiento = Equipo.query.filter_by(estado="Mantenimiento").all()
    incidentes_ids = {inc.equipo_id for inc in incidentes}

    for eq in equipos_mantenimiento:
        if eq.id not in incidentes_ids:
            data.append({
                "id": None,
                "equipo_id": eq.id,
                "equipo_nombre": eq.nombre,
                "usuario_asignado": "",
                "sede": eq.salon.sede.nombre if eq.salon and eq.salon.sede else "Sin sede",
                "fecha": datetime.utcnow().strftime("%Y-%m-%d"),
                "descripcion": "Equipo en mantenimiento",
                "estado": "Mantenimiento"
            })

    return jsonify(data)

@admin_bp.route('/mantenimiento')
@role_required(1)
def mantenimiento():
    """Muestra la página de mantenimiento de equipos."""
    return render_template('superadmin/gestion_inventario/mantenimiento.html')

# ===============================
# API de Mantenimientos
# ===============================
@admin_bp.route('/api/mantenimientos', methods=['GET'])
@login_required
@role_required(1)
def api_mantenimientos():
    mantenimientos = Mantenimiento.query.all()
    data = []
    for m in mantenimientos:
        data.append({
            "id": m.id,
            "equipo_id": m.equipo.id if m.equipo else None,
            "equipo_nombre": m.equipo.nombre if m.equipo else "Sin equipo",
            "sede_id": m.sede.id if m.sede else None,
            "sede_nombre": m.sede.nombre if m.sede else "Sin sede",
            "fecha_programada": m.fecha_programada.strftime("%Y-%m-%d"),
            "tipo": m.tipo,
            "descripcion": m.descripcion or "",
            "estado": m.estado
        })
    return jsonify(data)


@admin_bp.route('/api/mantenimientos', methods=['POST'])
@login_required
@role_required(1)
def crear_mantenimiento():
    data = request.get_json()
    equipo_id = data.get("equipo_id")
    fecha_programada = datetime.strptime(data.get("fecha_programada"), "%Y-%m-%d").date()
    tipo = data.get("tipo", "mantenimiento")
    descripcion = data.get("descripcion", "")

    equipo = Equipo.query.get(equipo_id)
    if not equipo:
        return jsonify({"error": "Equipo no encontrado"}), 404

    sede_id = equipo.salon.sede.id if equipo.salon and equipo.salon.sede else None
    if not sede_id:
        return jsonify({"error": "El equipo no tiene sede asociada"}), 400

    nuevo = Mantenimiento(
        equipo_id=equipo_id,
        sede_id=sede_id,
        fecha_programada=fecha_programada,
        tipo=tipo,
        descripcion=descripcion,
        estado="Programado"
    )
    db.session.add(nuevo)
    db.session.commit()

    return jsonify({"success": True, "id": nuevo.id})


@admin_bp.route('/api/mantenimientos/<int:mantenimiento_id>/cancelar', methods=['POST'])
@login_required
@role_required(1)
def cancelar_mantenimiento(mantenimiento_id):
    m = Mantenimiento.query.get(mantenimiento_id)
    if not m:
        return jsonify({"error": "Mantenimiento no encontrado"}), 404
    m.estado = "Cancelado"
    db.session.commit()
    return jsonify({"success": True})

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
    """Muestra la página con la lista de superadmins."""
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
            lista_padres.append({
                'id_usuario': padre.id_usuario,
                'no_identidad': padre.no_identidad,
                'nombre_completo': f"{padre.nombre} {padre.apellido}",
                'correo': padre.correo,
                'rol': padre.rol.nombre if padre.rol else 'N/A',
                'estado_cuenta': padre.estado_cuenta,
                'hijos_asignados': []  # Placeholder
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


# ===============================
# Gestión Académica
# ===============================
@admin_bp.route('/gestion-academica')
@login_required
@role_required(1)
def gestion_academica():
    return render_template('superadmin/gestion_academica/dashboard.html')

@admin_bp.route('/gestion-horario')
@login_required
@role_required(1)
def gestion_horario():
    horarios = db.session.query(HorarioGeneral).all()
    horarios_list = [h.to_dict() for h in horarios]
    return render_template('superadmin/Horarios/HorarioG.html', horarios=horarios_list)

# --- API de Horarios ---
@admin_bp.route('/api/horarios', methods=['GET'])
@login_required
@role_required(1)
def api_list_horarios():
    horarios = HorarioGeneral.query.all()
    return jsonify([h.to_dict() for h in horarios])

@admin_bp.route('/api/horarios', methods=['POST'])
@login_required
@role_required(1)
def api_create_horario():
    data = request.get_json() or {}
    nombre = data.get('nombre') or 'Horario'
    horaInicio = datetime.strptime(data.get('horaInicio','07:00'), '%H:%M').time()
    horaFin = datetime.strptime(data.get('horaFin','12:00'), '%H:%M').time()
    dias = data.get('diasSemana','')
    nuevo = HorarioGeneral(nombre=nombre, horaInicio=horaInicio, horaFin=horaFin, diasSemana=dias)
    db.session.add(nuevo)
    db.session.commit()
    return jsonify(nuevo.to_dict()), 201 

@admin_bp.route('/api/horarios', methods=['PUT'])
@login_required
@role_required(1)
def api_update_horario():
    data = request.get_json() or {}
    horario_id = data.get('id')
    if not horario_id:
        return jsonify({"error":"id requerido"}), 400
    horario = HorarioGeneral.query.get(horario_id)
    if not horario:
        return jsonify({"error":"No encontrado"}), 404
    if 'nombre' in data: horario.nombre = data['nombre']
    if 'horaInicio' in data:
        try:
            horario.horaInicio = datetime.strptime(data['horaInicio'], '%H:%M').time()
        except ValueError:
            return jsonify({"error":"Formato horaInicio inválido"}), 400
    if 'horaFin' in data:
        try:
            horario.horaFin = datetime.strptime(data['horaFin'], '%H:%M').time()
        except ValueError:
            return jsonify({"error":"Formato horaFin inválido"}), 400
    if 'diasSemana' in data: horario.diasSemana = data['diasSemana']
    db.session.commit()
    return jsonify(horario.to_dict())

@admin_bp.route('/api/horarios', methods=['DELETE'])
@login_required
@role_required(1)
def api_delete_horario():
    data = request.get_json() or {}
    horario_id = data.get('id')
    if not horario_id:
        return jsonify({"error":"id requerido"}), 400
    horario = HorarioGeneral.query.get(horario_id)
    if not horario:
        return jsonify({"error":"No encontrado"}), 404
    db.session.delete(horario)
    db.session.commit()
    return jsonify({"success": True})

@admin_bp.route('/api/horarios/<int:horario_id>/breaks', methods=['POST'])
@login_required
@role_required(1)
def api_create_break(horario_id):
    data = request.get_json() or {}
    horaInicio_str = data.get('horaInicio')
    duracion = int(data.get('duracion') or 0)
    if not horaInicio_str or duracion <= 0:
        return jsonify({"error":"horaInicio y duracion requeridos"}), 400
    try:
        start_dt = datetime.strptime(horaInicio_str, '%H:%M')
    except ValueError:
        return jsonify({"error":"Formato horaInicio inválido"}), 400
    end_dt = start_dt + timedelta(minutes=duracion)
    horario = HorarioGeneral.query.get(horario_id)
    if not horario:
        return jsonify({"error":"Horario no encontrado"}), 404
    nuevo = Descanso(horarioId=horario_id, horaInicio=start_dt.time(), horaFin=end_dt.time())
    db.session.add(nuevo)
    db.session.commit()
    return jsonify(nuevo.to_dict()), 201

@admin_bp.route('/api/horarios/<int:horario_id>/breaks', methods=['DELETE'])
@login_required
@role_required(1)
def api_delete_break(horario_id):
    data = request.get_json() or {}
    descanso_id = data.get('id')
    if not descanso_id:
        return jsonify({"error":"id requerido"}), 400
    descanso = Descanso.query.get(descanso_id)
    if not descanso or descanso.horarioId != horario_id:
        return jsonify({"error":"Descanso no encontrado"}), 404
    db.session.delete(descanso)
    db.session.commit()
    return jsonify({"success": True})

# ===============================
# API de Materias
# ===============================
@admin_bp.route('/api/materias', methods=['GET'])
@login_required
@role_required(1)
def api_list_materias():
    materias = Asignatura.query.all()
    return jsonify([m.to_dict() if hasattr(m,'to_dict') else {"id":m.id,"nombre":m.nombre} for m in materias])

@admin_bp.route('/api/materias', methods=['POST'])
@login_required
@role_required(1)
def api_create_materia():
    data = request.get_json() or {}
    nombre = data.get('nombre')
    if not nombre:
        return jsonify({"error":"nombre requerido"}), 400
    m = Asignatura(nombre=nombre)
    db.session.add(m)
    db.session.commit()
    return jsonify({"id": m.id, "nombre": m.nombre}), 201

@admin_bp.route('/api/materias/<int:mat_id>', methods=['DELETE'])
@login_required
@role_required(1)
def api_delete_materia(mat_id):
    m = Asignatura.query.get(mat_id)
    if not m:
        return jsonify({"error":"No encontrado"}), 404
    db.session.delete(m)
    db.session.commit()
    return jsonify({"success": True})

# ===============================
# Gestión de Usuarios
# ===============================
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
                        horarioId=1  # TODO: cambiar por lógica real
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

# ===============================
# Gestión de Cursos
# ===============================
@admin_bp.route('/gestion_sedes')
@login_required
@role_required(1)
def gestion_sedes():
    form = SedeForm()
    return render_template('superadmin/gestion_academica/sedes.html', form=form)

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
        cursos = db.session.query(Curso, Sede.nombre).join(Sede).all()
        cursos_list = [{
            'id': c.id,
            'nombreCurso': c.nombreCurso,
            'sede': sede_nombre
        } for c, sede_nombre in cursos]
        return jsonify({"data": cursos_list})

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
                    'sede': sede.nombre if sede else 'N/A'
                }), 201
            except IntegrityError:
                db.session.rollback()
                return jsonify({'error': 'Este curso ya existe.'}), 409
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
            return jsonify({'error': 'No se puede eliminar el curso porque está asociado.'}), 409
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Error interno: {str(e)}'}), 500