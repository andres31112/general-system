from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from controllers.decorators import role_required
from controllers.forms import RegistrationForm, UserEditForm
from extensions import db
from datetime import datetime, timedelta, time, date
from controllers.models import db, Usuario, Rol, Clase, Curso, Asignatura, Sede, Salon, HorarioGeneral, Descanso

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# ===============================
# Panel y vistas generales
# ===============================
@admin_bp.route('/dashboard')
@login_required
@role_required(1)
def admin_panel():
    return render_template('superadmin/gestion_usuarios/dashboard.html')


@admin_bp.route('/inicio')
@login_required
@role_required(1)
def inicio():
    return render_template('superadmin/inicio/inicio.html')


@admin_bp.route('/gestion_inventario')
@login_required
@role_required(1)
def gestion_i():
    return render_template('superadmin/gestion_inventario/gi.html')


@admin_bp.route('/equipos')
@login_required
@role_required(1)
def equipos():
    return render_template('superadmin/gestion_inventario/equipos.html')


@admin_bp.route('/salones')
@login_required
@role_required(1)
def salones():
    salones = db.session.query(Salon).all()
    return render_template('superadmin/gestion_inventario/salones.html', salones=salones)


@admin_bp.route('/gestion-salones')
@login_required
@role_required(1)
def gestion_salones():
    salones = db.session.query(Salon).all()
    total_salones = db.session.query(Salon).count()
    salas_computo = db.session.query(Salon).filter_by(tipo='sala_computo').count()
    salas_general = db.session.query(Salon).filter_by(tipo='sala_general').count()
    salas_especial = db.session.query(Salon).filter_by(tipo='sala_especial').count()
    return render_template(
        'superadmin/gestion_inventario/salones.html',
        total_salones=total_salones,
        salas_computo=salas_computo,
        salas_general=salas_general,
        salas_especial=salas_especial,
        salones=salones
    )


# ===============================
# Registro de salones y equipos
# ===============================
@admin_bp.route('/registro_salon', methods=['GET', 'POST'])
@login_required
@role_required(1)
def registro_salon():
    form = SalonForm()
    if form.validate_on_submit():
        nuevo_salon = Salon(
            nombre_salon=form.nombre_salon.data,
            tipo=form.tipo.data,
            sede=form.sede.data
        )
        db.session.add(nuevo_salon)
        db.session.commit()
        flash('Sala creada exitosamente ✅', 'success')
        return redirect(url_for('admin.salones'))
    return render_template('superadmin/gestion_inventario/registro_salon.html', title='Crear Nueva Sala', form=form)


@admin_bp.route('/registro_equipo', methods=['GET', 'POST'])
@login_required
@role_required(1)
def registro_equipo():
    return render_template('superadmin/gestion_inventario/registro_equipo.html')


@admin_bp.route('/registro_incidente', methods=['GET', 'POST'])
@login_required
@role_required('administrador')
def registro_incidente():
    return render_template('superadmin/gestion_inventario/registro_incidente.html')


# ===============================
# Profesores y estudiantes
# ===============================
@admin_bp.route('/profesores')
@login_required
@role_required(1)
def profesores():
    # Esta ruta ahora solo sirve la plantilla HTML, el JS se encargará de los datos.
    return render_template('superadmin/gestion_usuarios/profesores.html')


@admin_bp.route('/api/profesores')
@login_required
@role_required(1)
def api_profesores():
    try:
        rol_profesor = db.session.query(Rol).filter_by(nombre='Profesor').first()
        # Filtrar solo usuarios activos por defecto
        # profesores = Usuario.query.filter_by(id_rol_fk=rol_profesor.id_rol, estado_cuenta='activa').all() if rol_profesor else []
        # O, si quieres todos los profesores para filtrar en JS:
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
            
            # Si no hay clases asignadas
            if not cursos_asignados:
                cursos_asignados.add('Sin asignar')
            if not materias_asignadas:
                materias_asignadas.add('Sin asignar')
            if not sedes_asignadas:
                sedes_asignadas.add('Sin asignar')

            lista_profesores.append({              
                'id_usuario': profesor.id_usuario, 
                'no_identidad': profesor.no_identidad,
                'nombre_completo': f"{profesor.nombre} {profesor.apellido}", # Combina nombre y apellido
                'correo': profesor.correo,
                'rol': profesor.rol.nombre if profesor.rol else 'N/A',
                'estado_cuenta': profesor.estado_cuenta, # Añade el estado de la cuenta
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
    rol_estudiante = db.session.query(Rol).filter_by(nombre='estudiante').first()
    estudiantes = db.session.query(Usuario).filter_by(id_rol_fk=rol_estudiante.id_rol).all() if rol_estudiante else []
    return render_template('superadmin/gestion_usuarios/estudiantes.html', estudiantes=estudiantes)
# ===============================
# Crear usuario
# ===============================
@admin_bp.route('/crear_usuario', methods=['GET', 'POST'])
@login_required
@role_required(1)
def crear_usuario():
    form = RegistrationForm()
    if form.validate_on_submit():
        new_user = Usuario(
            tipo_doc=form.tipo_doc.data,
            no_identidad=form.no_identidad.data,
            nombre=form.nombre.data,
            apellido=form.apellido.data,
            correo=form.correo.data,
            telefono=form.telefono.data,
            rol=form.rol.data,  # rol ya es un objeto Rol
            estado_cuenta='activa'  # si añadiste este campo
        )
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()

        flash(f'Usuario "{new_user.nombre} {new_user.apellido}" creado exitosamente!', 'success')
        return redirect(url_for('admin.profesores'))  # o la vista que corresponda

    return render_template(
        'superadmin/gestion_usuarios/crear_usuario.html',
        title='Crear Nuevo Usuario',
        form=form
    )


# ===============================
# Editar usuario
# ===============================
@admin_bp.route('/editar_usuario/<int:user_id>', methods=['GET', 'POST'])
@login_required
@role_required(1)
def editar_usuario(user_id):
    user = db.session.query(Usuario).get_or_404(user_id)
    form = UserEditForm(original_no_identidad=user.no_identidad, original_correo=user.correo)

    # Prellenar datos al cargar el formulario
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


# ===============================
# Eliminar usuario
# ===============================
@admin_bp.route('/eliminar_usuario/<int:user_id>', methods=['POST'])
@login_required
@role_required(1)
def eliminar_usuario(user_id):
    user = db.session.query(Usuario).get_or_404(user_id)
    # Usar has_role() para una verificación de rol más robusta
    if current_user.id_usuario == user.id_usuario or user.has_role('administrador'):
        flash('No puedes eliminar tu propia cuenta o la de otro administrador.', 'danger')
        return redirect(url_for('admin.profesores'))
    
    # Aquí va tu código de eliminación
    db.session.delete(user)
    db.session.commit()
    flash(f'Usuario "{user.nombre_completo}" eliminado exitosamente.', 'success')
    return redirect(url_for('admin.profesores'))

# ===============================
# Gestión Académica
# ===============================
@admin_bp.route('/gestion-academica')
@login_required
@role_required(1)
def gestion_academica():
    horarios = db.session.query(HorarioGeneral).all()
    horarios_list = [h.to_dict() for h in horarios]
    return render_template('superadmin/Horarios/HorarioG.html', horarios=horarios_list)

#GET: listar horarios (útil para debug)
@admin_bp.route('/api/horarios', methods=['GET'])
@login_required
@role_required(1)
def api_list_horarios():
    horarios = HorarioGeneral.query.all()
    return jsonify([h.to_dict() for h in horarios])

# POST: crear nuevo horario (frontend envía {nombre})
@admin_bp.route('/api/horarios', methods=['POST'])
@login_required
@role_required(1)
def api_create_horario():
    data = request.get_json() or {}
    nombre = data.get('nombre') or 'Horario'
    # usamos valores por defecto si no vienen horas (para no violar nullable=False)
    horaInicio = datetime.strptime(data.get('horaInicio','07:00'), '%H:%M').time()
    horaFin   = datetime.strptime(data.get('horaFin','12:00'), '%H:%M').time()
    dias = data.get('diasSemana','')
    nuevo = HorarioGeneral(nombre=nombre, horaInicio=horaInicio, horaFin=horaFin, diasSemana=dias)
    db.session.add(nuevo)
    db.session.commit()
    return jsonify(nuevo.to_dict()), 201

# PUT: actualizar (envía {id, campo: valor})
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

    if 'nombre' in data:
        horario.nombre = data['nombre']
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
    if 'diasSemana' in data:
        horario.diasSemana = data['diasSemana']

    db.session.commit()
    return jsonify(horario.to_dict())

# DELETE: eliminar horario (envía {id})
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

# POST: agregar descanso a un horario (envía {horaInicio: "HH:MM", duracion: minutos})
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

# DELETE: eliminar descanso (envía {id})
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

# Materias (Asignatura)
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