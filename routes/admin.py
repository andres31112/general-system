from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from datetime import datetime, date
import os
import json
from werkzeug.utils import secure_filename
from controllers.decorators import role_required
from extensions import db
from services.email_service import send_welcome_email, generate_verification_code, send_verification_success_email, send_welcome_email_with_retry, get_verification_info
from controllers.forms import RegistrationForm, UserEditForm, SalonForm, CursoForm, SedeForm, EquipoForm
from controllers.models import (
    Usuario, Rol, Clase, Curso, Asignatura, Sede, Salon, 
    HorarioGeneral, HorarioCompartido, Matricula, BloqueHorario, 
    HorarioCurso, AsignacionEquipo, Equipo, Incidente, Mantenimiento, Comunicacion, 
    Evento, Candidato, HorarioVotacion, ReporteCalificaciones, Notificacion
)

# Creamos un 'Blueprint' (un plano o borrador) para agrupar todas las rutas de la sección de admin
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# ==================== DASHBOARD Y PÁGINAS PRINCIPALES ====================

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

# ==================== GESTIÓN DE USUARIOS ====================

# --- Búsqueda de usuarios ---
@admin_bp.route('/buscar-usuario')
@login_required
@role_required(1)
def buscar_usuario():
    """API para búsqueda global de usuarios"""
    identificacion = request.args.get('identificacion', '')
    
    usuarios_encontrados = []
    
    # Buscar en profesores
    rol_profesor = Rol.query.filter_by(nombre='Profesor').first()
    if rol_profesor:
        profesores = Usuario.query.filter(
            Usuario.id_rol_fk == rol_profesor.id_rol,
            db.or_(
                Usuario.no_identidad.ilike(f'%{identificacion}%'),
                Usuario.nombre.ilike(f'%{identificacion}%'),
                Usuario.apellido.ilike(f'%{identificacion}%')
            )
        ).limit(5).all()
        
        for prof in profesores:
            usuarios_encontrados.append({
                'id': prof.no_identidad,
                'nombre': prof.nombre,
                'apellido': prof.apellido,
                'rol': 'profesor',
                'rolUrl': url_for('admin.profesores')
            })
    
    # Buscar en estudiantes
    rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()
    if rol_estudiante:
        estudiantes = Usuario.query.filter(
            Usuario.id_rol_fk == rol_estudiante.id_rol,
            db.or_(
                Usuario.no_identidad.ilike(f'%{identificacion}%'),
                Usuario.nombre.ilike(f'%{identificacion}%'),
                Usuario.apellido.ilike(f'%{identificacion}%')
            )
        ).limit(5).all()
        
        for est in estudiantes:
            usuarios_encontrados.append({
                'id': est.no_identidad,
                'nombre': est.nombre,
                'apellido': est.apellido,
                'rol': 'estudiante',
                'rolUrl': url_for('admin.estudiantes')
            })
    
    # Buscar en padres/tutores
    rol_padre = Rol.query.filter_by(nombre='Padre').first()
    if rol_padre:
        padres = Usuario.query.filter(
            Usuario.id_rol_fk == rol_padre.id_rol,
            db.or_(
                Usuario.no_identidad.ilike(f'%{identificacion}%'),
                Usuario.nombre.ilike(f'%{identificacion}%'),
                Usuario.apellido.ilike(f'%{identificacion}%')
            )
        ).limit(5).all()
        
        for pad in padres:
            usuarios_encontrados.append({
                'id': pad.no_identidad,
                'nombre': pad.nombre,
                'apellido': pad.apellido,
                'rol': 'padre',
                'rolUrl': url_for('admin.padres')
            })
    
    # Buscar en administradores
    rol_admin = Rol.query.filter_by(nombre='Administrador Institucional').first()
    if rol_admin:
        admins = Usuario.query.filter(
            Usuario.id_rol_fk == rol_admin.id_rol,
            db.or_(
                Usuario.no_identidad.ilike(f'%{identificacion}%'),
                Usuario.nombre.ilike(f'%{identificacion}%'),
                Usuario.apellido.ilike(f'%{identificacion}%')
            )
        ).limit(5).all()
        
        for admin in admins:
            usuarios_encontrados.append({
                'id': admin.no_identidad,
                'nombre': admin.nombre,
                'apellido': admin.apellido,
                'rol': 'admin',
                'rolUrl': url_for('admin.superadmins')
            })
    
    return jsonify(usuarios_encontrados)

# --- Lista de usuarios por rol ---
@admin_bp.route('/profesores')
@login_required
@role_required(1)
def profesores():
    """Muestra la página con la lista de profesores."""
    filter_id = request.args.get('filter_id', '')
    return render_template('superadmin/gestion_usuarios/profesores.html', filter_id=filter_id)

@admin_bp.route('/api/profesores')
@login_required
@role_required(1)
def api_profesores():
    """API para obtener la lista de profesores"""
    try:
        filter_id = request.args.get('filter_id', '')
        rol_profesor = Rol.query.filter_by(nombre='Profesor').first()
        
        if filter_id:
            profesores = Usuario.query.filter_by(id_rol_fk=rol_profesor.id_rol, no_identidad=filter_id).all() if rol_profesor else []
        else:
            profesores = Usuario.query.filter_by(id_rol_fk=rol_profesor.id_rol).all() if rol_profesor else []
            
        lista_profesores = []
        for profesor in profesores:
            clases = Clase.query.filter_by(profesorId=profesor.id_usuario).all()
            cursos_asignados = set()
            materias_asignadas = set()
            sedes_asignadas = set()
            
            if clases:
                for clase in clases:
                    curso = Curso.query.filter_by(id_curso=clase.cursoId).first()
                    if curso:
                        cursos_asignados.add(curso.nombreCurso)
                        sede = Sede.query.filter_by(id_sede=curso.sedeId).first()
                        if sede:
                            sedes_asignadas.add(sede.nombre)
                    asignatura = Asignatura.query.filter_by(id_asignatura=clase.asignaturaId).first()
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
    filter_id = request.args.get('filter_id', '')
    rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()
    
    # Cargar estudiantes
    if filter_id:
        estudiantes = Usuario.query.filter_by(
            id_rol_fk=rol_estudiante.id_rol, 
            no_identidad=filter_id
        ).all() if rol_estudiante else []
    else:
        estudiantes = Usuario.query.filter_by(
            id_rol_fk=rol_estudiante.id_rol
        ).all() if rol_estudiante else []
    
    # Pre-cargar matrículas y padres para evitar consultas N+1
    estudiante_ids = [est.id_usuario for est in estudiantes]
    
    if estudiante_ids:
        # Obtener todas las matrículas
        matriculas = Matricula.query.filter(
            Matricula.estudianteId.in_(estudiante_ids)
        ).all()
        
        # Obtener cursos relacionados
        curso_ids = [mat.cursoId for mat in matriculas]
        cursos_dict = {curso.id_curso: curso for curso in Curso.query.filter(Curso.id_curso.in_(curso_ids)).all()}
        
        # Obtener padres usando SQL directo
        padres_dict = {}
        try:
            from sqlalchemy import text
            result = db.session.execute(text("""
                SELECT ep.estudiante_id, u.id_usuario, u.nombre, u.apellido 
                FROM estudiante_padre ep 
                JOIN usuarios u ON ep.padre_id = u.id_usuario 
                WHERE ep.estudiante_id IN :estudiante_ids
            """), {'estudiante_ids': tuple(estudiante_ids)})
            
            for row in result:
                estudiante_id = row[0]
                if estudiante_id not in padres_dict:
                    padres_dict[estudiante_id] = []
                padres_dict[estudiante_id].append(f"{row[2]} {row[3]}")
        except Exception as e:
            print(f"Error cargando padres: {e}")
            padres_dict = {}
        
        # Organizar matrículas por estudiante
        matriculas_por_estudiante = {}
        for matricula in matriculas:
            if matricula.estudianteId not in matriculas_por_estudiante:
                matriculas_por_estudiante[matricula.estudianteId] = []
            matriculas_por_estudiante[matricula.estudianteId].append(matricula)
        
        # Asignar datos a cada estudiante
        for estudiante in estudiantes:
            estudiante._matriculas = matriculas_por_estudiante.get(estudiante.id_usuario, [])
            estudiante._cursos_dict = cursos_dict
            estudiante._padres = padres_dict.get(estudiante.id_usuario, [])
    else:
        for estudiante in estudiantes:
            estudiante._matriculas = []
            estudiante._cursos_dict = {}
            estudiante._padres = []
    
    # Crear el formulario y configurar el rol predefinido como Estudiante
    form = RegistrationForm()
    
    # ✅ CORREGIDO: Cargar choices para el rol
    form.rol.choices = [(str(rol_estudiante.id_rol), rol_estudiante.nombre)] if rol_estudiante else []
    form.rol.data = str(rol_estudiante.id_rol) if rol_estudiante else None
    
    # ✅ CORREGIDO: Cargar choices para cursos
    cursos = Curso.query.all()
    form.curso_id.choices = [(str(curso.id_curso), curso.nombreCurso) for curso in cursos]
    
    return render_template(
        'superadmin/gestion_usuarios/estudiantes.html', 
        estudiantes=estudiantes,
        form=form,  
        cursos=cursos,
        rol_predefinido='Estudiante',
        rol_predefinido_id=str(rol_estudiante.id_rol) if rol_estudiante else None,
        now=date.today
    )
# API para estudiantes
@admin_bp.route('/api/estudiantes')
@login_required
@role_required(1)
def api_estudiantes():
    """API para obtener la lista de estudiantes con información completa"""
    try:
        filter_id = request.args.get('filter_id', '')
        rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()
        
        if filter_id:
            estudiantes = Usuario.query.filter_by(id_rol_fk=rol_estudiante.id_rol, no_identidad=filter_id).all() if rol_estudiante else []
        else:
            estudiantes = Usuario.query.filter_by(id_rol_fk=rol_estudiante.id_rol).all() if rol_estudiante else []
            
        lista_estudiantes = []
        for estudiante in estudiantes:
            # Obtener información de matrícula actual
            matricula_actual = Matricula.query.filter_by(estudianteId=estudiante.id_usuario)\
                                            .order_by(Matricula.año.desc())\
                                            .first()
            
            curso_nombre = "Sin asignar"
            anio_matricula = "N/A"
            padre_acudiente = "Sin asignar"
            
            if matricula_actual:
                curso = Curso.query.get(matricula_actual.cursoId)
                if curso:
                    curso_nombre = curso.nombreCurso
                anio_matricula = matricula_actual.año

            lista_estudiantes.append({
                'id_usuario': estudiante.id_usuario,
                'no_identidad': estudiante.no_identidad,
                'nombre_completo': f"{estudiante.nombre} {estudiante.apellido}",
                'correo': estudiante.correo,
                'curso': curso_nombre,
                'anio_matricula': anio_matricula,
                'padre_acudiente': padre_acudiente,
                'estado_cuenta': estudiante.estado_cuenta
            })
            
        return jsonify({"data": lista_estudiantes})
    except Exception as e:
        print(f"Error en la API de estudiantes: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@admin_bp.route('/estudiantes/crear', methods=['GET', 'POST'])
@login_required
@role_required(1)
def crear_estudiante():
    """Crear nuevo estudiante - Ruta específica para estudiantes"""
    form = RegistrationForm()
    
    # ✅ CORREGIDO: SIEMPRE cargar las opciones de roles ANTES de validar
    roles = Rol.query.all()
    form.rol.choices = [(str(r.id_rol), r.nombre) for r in roles] if roles else []
    
    # Obtener el rol de Estudiante
    rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()
    if not rol_estudiante:
        flash('Error: Rol de Estudiante no encontrado', 'error')
        return redirect(url_for('admin.estudiantes'))
    
    # Configurar el formulario para estudiantes
    form.rol.data = str(rol_estudiante.id_rol)
    
    # ✅ CORREGIDO: Cargar opciones de cursos
    cursos = Curso.query.all()
    form.curso_id.choices = [(str(curso.id_curso), curso.nombreCurso) for curso in cursos]
    
    # ✅ AHORA SÍ validar el formulario (con los choices ya cargados)
    if form.validate_on_submit():
        try:
            from datetime import datetime, timedelta
            verification_code = generate_verification_code()
            
            print(f"DEBUG: Creando estudiante - Contraseña del formulario: {form.password.data}")
            
            # Crear usuario estudiante con verificación de email
            new_user = Usuario(
                tipo_doc=form.tipo_doc.data,
                no_identidad=form.no_identidad.data,
                nombre=form.nombre.data,
                apellido=form.apellido.data,
                direccion=form.direccion.data,
                correo=form.correo.data,
                telefono=form.telefono.data,
                id_rol_fk=rol_estudiante.id_rol,
                estado_cuenta='activa',
                email_verified=False,
                verification_code=verification_code, 
                verification_code_expires=datetime.utcnow() + timedelta(hours=24),
                verification_attempts=0,
                temp_password=form.password.data  # ✅ GUARDAR CONTRASEÑA TEMPORAL
            )
            new_user.set_password(form.password.data)  # Esto hashea la contraseña
            
            db.session.add(new_user)
            db.session.flush()  # Para obtener el ID del estudiante
            
            print(f"DEBUG: Estudiante creado con ID: {new_user.id_usuario}")
            print(f"DEBUG: Contraseña temporal guardada: {new_user.temp_password}")
            
            # Crear matrícula si se proporcionó curso y año
            if form.curso_id.data and form.anio_matricula.data:
                nueva_matricula = Matricula(
                    estudianteId=new_user.id_usuario,
                    cursoId=int(form.curso_id.data),
                    año=int(form.anio_matricula.data)
                )
                db.session.add(nueva_matricula)
            
            # Asignar padre si se seleccionó uno
            parent_id = request.form.get('parent_id')
            if parent_id:
                try:
                    padre_id_int = int(parent_id)
                    padre = Usuario.query.get(padre_id_int)
                    if padre:
                        from sqlalchemy import text
                        db.session.execute(
                            text("INSERT INTO estudiante_padre (estudiante_id, padre_id) VALUES (:estudiante_id, :padre_id)"),
                            {'estudiante_id': new_user.id_usuario, 'padre_id': padre_id_int}
                        )
                        flash(f'Padre "{padre.nombre_completo}" asignado correctamente al estudiante', 'success')
                    else:
                        flash('El padre seleccionado no existe', 'warning')
                except (ValueError, Exception) as e:
                    flash(f'Error al asignar padre: {str(e)}', 'warning')
            
            db.session.commit()
            
            print(f"DEBUG: Enviando correo de verificación a {new_user.correo}")
            
            # Enviar correo de bienvenida con código de verificación
            email_result = send_welcome_email(new_user, verification_code)
            
            if email_result == True:
                flash(f'Estudiante "{new_user.nombre_completo}" creado exitosamente! Se ha enviado un correo de verificación.', 'success')
                print(f"DEBUG: Correo enviado exitosamente")
            elif email_result == "limit_exceeded":
                flash(f'Estudiante "{new_user.nombre_completo}" creado exitosamente! ⚠️ Límite diario de correos excedido. Código de verificación: {verification_code}', 'warning')
                print(f"DEBUG: Límite de correos excedido - Código: {verification_code}")
            else:
                flash(f'Estudiante "{new_user.nombre_completo}" creado pero hubo un error enviando el correo de verificación. Código de verificación: {verification_code}', 'warning')
                print(f"DEBUG: Error enviando correo - Código: {verification_code}")
            
            return redirect(url_for('admin.estudiantes'))
            
        except Exception as e:
            db.session.rollback()
            print(f"ERROR en crear_estudiante: {str(e)}")
            flash(f'Error al crear estudiante: {str(e)}', 'error')
    
    return render_template(
        'superadmin/gestion_usuarios/crear_estudiante.html',
        title='Crear Estudiante',
        form=form,
        cursos=cursos,
        now=date.today,
        rol_predefinido='Estudiante',
        rol_predefinido_id=str(rol_estudiante.id_rol)
    )

@admin_bp.route('/debug/usuarios/<int:user_id>')
@login_required
@role_required(1)
def debug_usuario(user_id):
    """Endpoint para debug de usuario"""
    usuario = Usuario.query.get_or_404(user_id)
    
    debug_info = {
        'id_usuario': usuario.id_usuario,
        'nombre_completo': usuario.nombre_completo,
        'correo': usuario.correo,
        'email_verified': usuario.email_verified,
        'verification_code': usuario.verification_code,
        'verification_code_expires': usuario.verification_code_expires,
        'verification_attempts': usuario.verification_attempts,
        'estado_cuenta': usuario.estado_cuenta,
        'rol': usuario.rol.nombre if usuario.rol else 'N/A'
    }
    
    return jsonify(debug_info)

# Rutas específicas para estudiantes
@admin_bp.route('/estudiantes/<int:id>/eliminar', methods=['DELETE'])
@login_required
@role_required(1)
def eliminar_estudiante(id):
    """Eliminar un estudiante específico"""
    try:
        estudiante = Usuario.query.get_or_404(id)
        
        # Verificar que sea un estudiante
        rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()
        if estudiante.id_rol_fk != rol_estudiante.id_rol:
            return jsonify({'success': False, 'error': 'El usuario no es un estudiante'}), 400
        
        # Eliminar matrículas asociadas
        Matricula.query.filter_by(estudianteId=id).delete()
        
        # Eliminar el estudiante
        db.session.delete(estudiante)
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
         .filter(Incidente.id == incidente_db)\
         .first()
        
        if not incidente_db:
            return jsonify({'success': False, 'error': 'Incidente no encontrado.'}), 404
        
        incidente = {
            'id': incidente_db.id_incidente,
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
            Mantenimiento.id_mantenimiento,
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
        ).join(Equipo, Mantenimiento.equipo_id == Equipo.id_equipo)\
         .join(Sede, Mantenimiento.sede_id == Sede.id_sede)\
         .outerjoin(Salon, Equipo.id_salon_fk == Salon.id_salon)\
         .order_by(Mantenimiento.fecha_programada.desc())\
         .all()

        mantenimientos = []
        for mant in mantenimientos_db:
            mantenimientos.append({
                'id': mant.id_mantenimiento,
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
        sede_id = data.get('sede_id')
        fecha_programada_str = data.get('fecha_programada')
        tipo = data.get('tipo')
        descripcion = data.get('descripcion', '').strip()
        tecnico = data.get('tecnico', '').strip()

        if not all([equipo_id, sede_id, fecha_programada_str, tipo]):
            return jsonify({
                'success': False, 
                'error': 'Faltan campos obligatorios. Se requiere: equipo_id, sede_id, fecha_programada y tipo.'
            }), 400

        equipo = Equipo.query.get(equipo_id)
        if not equipo:
            return jsonify({
                'success': False, 
                'error': f'Equipo con ID {equipo_id} no encontrado.'
            }), 404

        sede = Sede.query.get(sede_id)
        if not sede:
            return jsonify({
                'success': False, 
                'error': f'Sede con ID {sede_id} no encontrada.'
            }), 404

        try:
            fecha_programada = datetime.strptime(fecha_programada_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False, 
                'error': 'Formato de fecha inválido. Use: YYYY-MM-DD'
            }), 400

        
        nuevo_mantenimiento = Mantenimiento(
            equipo_id=equipo_id,
            sede_id=sede_id,
            fecha_programada=fecha_programada,
            tipo=tipo,
            estado='pendiente',
            descripcion=descripcion,
            tecnico=tecnico
        )
        db.session.add(nuevo_mantenimiento)
            
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Mantenimiento programado exitosamente para el equipo "{equipo.nombre}"',
            'mantenimiento': {
                'id': nuevo_mantenimiento.id_mantenimiento,  # o el nombre del campo ID en tu modelo
                'equipo_id': nuevo_mantenimiento.equipo_id,
                'equipo_nombre': equipo.nombre,
                'sede': sede.nombre,
                'fecha_programada': nuevo_mantenimiento.fecha_programada.strftime('%Y-%m-%d'),
                'tipo': nuevo_mantenimiento.tipo,
                'estado': nuevo_mantenimiento.estado,
                'tecnico': nuevo_mantenimiento.tecnico or 'N/A'
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error al programar mantenimiento: {e}")
        return jsonify({
            'success': False, 
            'error': f'Error interno del servidor: {str(e)}'
        }), 500

@admin_bp.route('/api/equipos/con-mantenimientos', methods=['GET'])
@login_required
@role_required(1)
def api_equipos_con_mantenimientos():
    """
    Retorna los IDs de equipos que tienen mantenimientos activos (pendientes o en progreso).
    """
    try:
        equipos_con_mantenimientos = db.session.query(Mantenimiento.equipo_id)\
            .filter(Mantenimiento.estado.in_(['pendiente', 'en_progreso']))\
            .distinct()\
            .all()
        
        ids = [eq[0] for eq in equipos_con_mantenimientos]
        
        return jsonify({'equipos_con_mantenimientos': ids}), 200
        
    except Exception as e:
        print(f"Error al obtener equipos con mantenimientos: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/mantenimientos/<int:mantenimiento_id>', methods=['GET'])
@login_required
@role_required(1)
def api_detalle_mantenimiento(mantenimiento_id):
    """
    Obtiene el detalle de un mantenimiento específico.
    """
    try:
        mantenimiento = db.session.query(
            Mantenimiento.id_mantenimiento,
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
        ).join(Equipo, Mantenimiento.equipo_id == Equipo.id_equipo)\
         .join(Sede, Mantenimiento.sede_id == Sede.id_sede)\
         .outerjoin(Salon, Equipo.id_salon_fk == Salon.id_salon)\
         .filter(Mantenimiento.id_mantenimiento == mantenimiento_id)\
         .first()

        if not mantenimiento:
            return jsonify({'success': False, 'error': 'Mantenimiento no encontrado.'}), 404

        return jsonify({
            'id': mantenimiento.id_mantenimiento,
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

@admin_bp.route('/estudiantes/<int:id>/editar')
@login_required
@role_required(1)
def editar_estudiante(id):
    """Redirigir a la página de edición de estudiante"""
    return redirect(url_for('admin.editar_usuario', user_id=id))

@admin_bp.route('/estudiantes/<int:id>/detalles')
@login_required
@role_required(1)
def detalles_estudiante(id):
    """Página de detalles del estudiante"""
    estudiante = Usuario.query.get_or_404(id)
    
    # Verificar que sea un estudiante
    rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()
    if estudiante.id_rol_fk != rol_estudiante.id_rol:
        flash('El usuario no es un estudiante', 'error')
        return redirect(url_for('admin.estudiantes'))
    
    # Obtener información adicional del estudiante
    matricula_actual = Matricula.query.filter_by(estudianteId=id)\
                                    .order_by(Matricula.año.desc())\
                                    .first()
    
    return render_template('superadmin/gestion_usuarios/detalles_estudiante.html', 
                         estudiante=estudiante, 
                         matricula=matricula_actual)

@admin_bp.route('/api/directorio/estudiantes', methods=['GET'])
@login_required
@role_required(1) 
def api_estudiantes_directorio():
    """API para obtener el directorio de estudiantes con su curso y sede."""
    try:
        search_query = request.args.get('q', '')
        filter_id = request.args.get('filter_id', '')
        
        rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()
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
            Curso, Curso.id_curso == Matricula.cursoId
        ).outerjoin(
            Sede, Sede.id_sede == Curso.sedeId
        )
        
        if filter_id:
            query = query.filter(Usuario.no_identidad == filter_id)
        elif search_query:
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
    filter_id = request.args.get('filter_id', '')
    return render_template('superadmin/gestion_usuarios/padres.html', filter_id=filter_id)

@admin_bp.route('/api/padres')
@login_required
@role_required(1)
def api_padres():
    """API para obtener la lista de padres con sus hijos asociados"""
    try:
        filter_id = request.args.get('filter_id', '')
        rol_padre = Rol.query.filter_by(nombre='Padre').first()
        
        if filter_id:
            padres = Usuario.query.filter_by(id_rol_fk=rol_padre.id_rol, no_identidad=filter_id).all() if rol_padre else []
        else:
            padres = Usuario.query.filter_by(id_rol_fk=rol_padre.id_rol).all() if rol_padre else []
        
        # Obtener IDs de padres para consulta de hijos
        padre_ids = [padre.id_usuario for padre in padres]
        
        # Obtener hijos asociados usando SQL directo para mejor rendimiento
        hijos_dict = {}
        if padre_ids:
            try:
                from sqlalchemy import text
                result = db.session.execute(text("""
                    SELECT ep.padre_id, u.id_usuario, u.nombre, u.apellido, u.no_identidad
                    FROM estudiante_padre ep 
                    JOIN usuarios u ON ep.estudiante_id = u.id_usuario 
                    WHERE ep.padre_id IN :padre_ids
                    ORDER BY ep.padre_id, u.nombre
                """), {'padre_ids': tuple(padre_ids)})
                
                for row in result:
                    padre_id = row[0]
                    if padre_id not in hijos_dict:
                        hijos_dict[padre_id] = []
                    hijos_dict[padre_id].append({
                        'id': row[1],
                        'nombre_completo': f"{row[2]} {row[3]}",
                        'no_identidad': row[4]
                    })
            except Exception as e:
                print(f"Error cargando hijos de padres: {e}")
                hijos_dict = {}
            
        lista_padres = []
        for padre in padres:
            # Obtener hijos asociados a este padre
            hijos_asignados = hijos_dict.get(padre.id_usuario, [])
            
            lista_padres.append({
                'id_usuario': padre.id_usuario,
                'no_identidad': padre.no_identidad,
                'nombre_completo': f"{padre.nombre} {padre.apellido}",
                'correo': padre.correo,
                'telefono': getattr(padre, 'telefono', '') or 'N/A',
                'rol': padre.rol.nombre if padre.rol else 'N/A',
                'estado_cuenta': padre.estado_cuenta,
                'hijos_asignados': hijos_asignados,
                'total_hijos': len(hijos_asignados)
            })
        return jsonify({"data": lista_padres})
    except Exception as e:
        print(f"Error en la API de padres: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@admin_bp.route('/superadmins')
@login_required
@role_required(1)
def superadmins():
    """Muestra la página con la lista de administradores"""
    filter_id = request.args.get('filter_id', '')
    return render_template('superadmin/gestion_usuarios/administrativos.html', filter_id=filter_id)

@admin_bp.route('/api/superadmins')
@login_required
@role_required(1)
def api_superadmins():
    """API para obtener la lista de administradores"""
    try:
        filter_id = request.args.get('filter_id', '')
        
        if filter_id:
            superadmins = Usuario.query.filter_by(id_rol_fk=1, no_identidad=filter_id).all()
        else:
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

# --- Formularios de usuarios ---
@admin_bp.route('/crear_usuario', methods=['GET', 'POST'])
@login_required
@role_required(1)
def crear_usuario():
    """Crear nuevo usuario con rol específico y verificación de email"""
    form = RegistrationForm()
    
    # ✅ CORREGIDO: SIEMPRE cargar las opciones de roles ANTES de validar
    roles = Rol.query.all()
    form.rol.choices = [(str(r.id_rol), r.nombre) for r in roles] if roles else []
    
    # ✅ CORREGIDO: Cargar opciones de cursos
    cursos = Curso.query.all()
    form.curso_id.choices = [(str(curso.id_curso), curso.nombreCurso) for curso in cursos]
    
    # Obtener el rol predefinido desde la URL
    rol_predefinido = request.args.get('rol')
    
    # Si hay rol predefinido, establecerlo en el formulario
    rol_predefinido_id = None
    if rol_predefinido and request.method == 'GET':
        # Buscar el ID del rol correspondiente al nombre
        if rol_predefinido.lower() == 'estudiante':
            rol_obj = Rol.query.filter_by(nombre='Estudiante').first()
        elif rol_predefinido.lower() == 'profesor':
            rol_obj = Rol.query.filter_by(nombre='Profesor').first()
        elif rol_predefinido.lower() == 'padre':
            rol_obj = Rol.query.filter_by(nombre='Padre').first()
        elif rol_predefinido.lower() == 'administrador_institucional':
            rol_obj = Rol.query.filter_by(nombre='Administrador Institucional').first()
        else:
            rol_obj = None
            
        if rol_obj:
            form.rol.data = str(rol_obj.id_rol)
            rol_predefinido_id = str(rol_obj.id_rol)

    # ✅ AHORA SÍ validar el formulario (con los choices ya cargados)
    if form.validate_on_submit():
        selected_role_id = int(form.rol.data)
        
        rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()
        rol_profesor = Rol.query.filter_by(nombre='Profesor').first()
        rol_padre = Rol.query.filter_by(nombre='Padre').first()
        rol_admin = Rol.query.filter_by(nombre='Administrador Institucional').first()

        is_student = (rol_estudiante and selected_role_id == rol_estudiante.id_rol)
        is_professor = (rol_profesor and selected_role_id == rol_profesor.id_rol)

        # Generar código de verificación
        from datetime import datetime, timedelta
        verification_code = generate_verification_code()
        print(f"DEBUG: Creando usuario - Contraseña del formulario:{form.password.data}")
        # Crear usuario con verificación de email
        new_user = Usuario(
            tipo_doc=form.tipo_doc.data,
            no_identidad=form.no_identidad.data,
            nombre=form.nombre.data,
            apellido=form.apellido.data,
            direccion=form.direccion.data,
            correo=form.correo.data,
            telefono=form.telefono.data,
            id_rol_fk=selected_role_id,
            estado_cuenta='activa',
            email_verified=False,
            verification_code=verification_code,
            verification_code_expires=datetime.utcnow() + timedelta(hours=24),
            verification_attempts=0,
            temp_password=form.password.data
        )
        new_user.set_password(form.password.data)
        
        try:
            db.session.add(new_user)
            db.session.flush()  # Para obtener el ID del usuario
            
            # Crear matrícula si es estudiante y se proporcionó curso y año
            if is_student and form.curso_id.data and form.anio_matricula.data:
                nueva_matricula = Matricula(
                    estudianteId=new_user.id_usuario,
                    cursoId=int(form.curso_id.data),
                    año=int(form.anio_matricula.data)
                )
                db.session.add(nueva_matricula)
            
            db.session.commit()
            print(f"DEBUG: Usuario creado - Contraseña temporal: {new_user.temp_password}")
            # Enviar correo de bienvenida con código de verificación
            email_result = send_welcome_email(new_user, new_user.verification_code)
            
            if email_result == True:
                flash(f'Usuario "{new_user.nombre_completo}" creado exitosamente! Se ha enviado un correo de verificación.', 'success')
            elif email_result == "limit_exceeded":
                flash(f'Usuario "{new_user.nombre_completo}" creado exitosamente! ⚠️ Límite diario de correos excedido. Código de verificación: {new_user.verification_code}', 'warning')
            else:
                flash(f'Usuario "{new_user.nombre_completo}" creado pero hubo un error enviando el correo de verificación. Código de verificación: {new_user.verification_code}', 'warning')
            
            # Redirigir según el rol creado
            if is_student:
                return redirect(url_for('admin.estudiantes'))
            elif is_professor:
                return redirect(url_for('admin.profesores'))
            elif rol_padre and selected_role_id == rol_padre.id_rol:
                return redirect(url_for('admin.padres'))
            elif rol_admin and selected_role_id == rol_admin.id_rol:
                return redirect(url_for('admin.superadmins'))
            else:
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
        now=date.today,
        rol_predefinido=rol_predefinido,
        rol_predefinido_id=rol_predefinido_id
    )
    
@admin_bp.route('/api/verificar-identidad')
@login_required
@role_required(1)
def api_verificar_identidad():
    """API para verificar si un número de identidad ya está registrado"""
    try:
        no_identidad = request.args.get('no_identidad', '')
        
        if not no_identidad:
            return jsonify({'exists': False})
        
        # Verificar si el número de identidad existe
        usuario = Usuario.query.filter_by(no_identidad=no_identidad).first()
        
        return jsonify({'exists': usuario is not None})
        
    except Exception as e:
        print(f"Error verificando identidad: {e}")
        return jsonify({'exists': False})
    
@admin_bp.route('/api/verificar-correo')
@login_required
@role_required(1)
def api_verificar_correo():
    """API para verificar si un correo ya está registrado"""
    try:
        email = request.args.get('email', '')
        
        if not email:
            return jsonify({'exists': False})
        
        # Verificar si el correo existe
        usuario = Usuario.query.filter_by(correo=email).first()
        
        return jsonify({'exists': usuario is not None})
        
    except Exception as e:
        print(f"Error verificando correo: {e}")
        return jsonify({'exists': False})

@admin_bp.route('/editar_usuario/<int:user_id>', methods=['GET', 'POST'])
@login_required
@role_required(1)
def editar_usuario(user_id):
    """Editar usuario existente"""
    user = Usuario.query.get_or_404(user_id)
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
    """Eliminar usuario"""
    user = Usuario.query.get_or_404(user_id)
    if current_user.id_usuario == user.id_usuario or user.has_role('administrador'):
        flash('No puedes eliminar tu propia cuenta o la de otro administrador.', 'danger')
        return redirect(url_for('admin.profesores'))
    
    db.session.delete(user)
    db.session.commit()
    flash(f'Usuario "{user.nombre_completo}" eliminado exitosamente.', 'success')
    return redirect(url_for('admin.profesores'))

# ==================== API PARA PADRES - ESTUDIANTES ====================

@admin_bp.route('/api/buscar-padres')
@login_required
@role_required(1)
def api_buscar_padres():
    """API para buscar padres/acudientes existentes"""
    try:
        search_query = request.args.get('q', '')
        
        rol_padre = Rol.query.filter_by(nombre='Padre').first()
        if not rol_padre:
            return jsonify([])
        
        query = Usuario.query.filter_by(id_rol_fk=rol_padre.id_rol)
        
        if search_query:
            query = query.filter(
                or_(
                    Usuario.nombre.ilike(f'%{search_query}%'),
                    Usuario.apellido.ilike(f'%{search_query}%'),
                    Usuario.no_identidad.ilike(f'%{search_query}%'),
                    Usuario.correo.ilike(f'%{search_query}%')
                )
            )
        
        padres = query.limit(10).all()
        
        resultados = []
        for padre in padres:
            resultados.append({
                'id_usuario': padre.id_usuario,
                'nombre_completo': padre.nombre_completo,
                'correo': padre.correo,
                'no_identidad': padre.no_identidad,
                'telefono': padre.telefono or ''
            })
        
        return jsonify(resultados)
        
    except Exception as e:
        print(f"Error buscando padres: {e}")
        return jsonify([])

@admin_bp.route('/api/crear-padre', methods=['POST'])
@login_required
@role_required(1)
def api_crear_padre():
    """API para crear un nuevo padre/acudiente con verificación de email"""
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        required_fields = ['no_identidad', 'tipo_doc', 'nombre', 'apellido', 'correo', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'El campo {field} es requerido'}), 400
        
        # Verificar si ya existe un usuario con ese número de identidad
        usuario_existente = Usuario.query.filter_by(no_identidad=data['no_identidad']).first()
        if usuario_existente:
            return jsonify({'success': False, 'error': 'Ya existe un usuario con ese número de identidad'}), 400
        
        # Verificar si ya existe un usuario con ese correo
        correo_existente = Usuario.query.filter_by(correo=data['correo']).first()
        if correo_existente:
            return jsonify({'success': False, 'error': 'Ya existe un usuario con ese correo electrónico'}), 400
        
        # Obtener el rol de Padre
        rol_padre = Rol.query.filter_by(nombre='Padre').first()
        if not rol_padre:
            return jsonify({'success': False, 'error': 'Rol de Padre no encontrado'}), 500
        
        # Generar código de verificación
        from datetime import datetime, timedelta
        verification_code = generate_verification_code()
        
        # Crear nuevo padre con verificación de email
        nuevo_padre = Usuario(
            tipo_doc=data['tipo_doc'],
            no_identidad=data['no_identidad'],
            nombre=data['nombre'],
            apellido=data['apellido'],
            correo=data['correo'],
            telefono=data.get('telefono', ''),
            id_rol_fk=rol_padre.id_rol,
            estado_cuenta='activa',
            email_verified=False,
            verification_code=verification_code,
            verification_code_expires=datetime.utcnow() + timedelta(hours=24),
            verification_attempts=0,
            temp_password=data['password']  # ✅ Guardar contraseña temporal
        )
        nuevo_padre.set_password(data['password'])
        
        db.session.add(nuevo_padre)
        db.session.commit()
        
        # Enviar correo de bienvenida con código de verificación
        email_result = send_welcome_email(nuevo_padre, verification_code)
        
        if email_result == True:
            message = 'Padre/acudiente creado exitosamente y correo de verificación enviado'
        elif email_result == "limit_exceeded":
            message = f'Padre/acudiente creado exitosamente! ⚠️ Límite diario de correos excedido. Código de verificación: {verification_code}'
        else:
            message = f'Padre/acudiente creado exitosamente pero hubo un error enviando el correo de verificación. Código de verificación: {verification_code}'
            print(f"ADVERTENCIA: No se pudo enviar el correo de verificación al padre {nuevo_padre.correo}")
        
        return jsonify({
            'success': True,
            'message': message,
            'padre': {
                'id_usuario': nuevo_padre.id_usuario,
                'nombre_completo': nuevo_padre.nombre_completo,
                'correo': nuevo_padre.correo,
                'no_identidad': nuevo_padre.no_identidad
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creando padre: {e}")
        return jsonify({'success': False, 'error': f'Error interno del servidor: {str(e)}'}), 500

# ==================== GESTIÓN ACADÉMICA ====================

@admin_bp.route('/gestion-academica')
@login_required
@role_required(1)
def gestion_academica():
    """Página principal de gestión académica"""
    return render_template('superadmin/gestion_academica/dashboard.html')

# --- Gestión de Sedes ---
@admin_bp.route('/gestion_sedes')
@login_required
@role_required(1)
def gestion_sedes():
    """Gestión de sedes"""
    form = SedeForm()
    return render_template('superadmin/gestion_academica/sedes.html', form=form)

@admin_bp.route('/api/sedes', methods=['GET', 'POST', 'DELETE'])
@login_required
@role_required(1)
def api_sedes():
    """API para gestión de sedes"""
    if request.method == 'GET':
        sedes = Sede.query.order_by(Sede.nombre).all()
        sedes_data = [{"id_sede": sede.id_sede, "nombre": sede.nombre, "direccion": sede.direccion} for sede in sedes]
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
                
                return jsonify({"message": "Sede creada exitosamente", "sede_id": nueva_sede.id_sede}), 201
            
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
        sede_id = data.get('id_sede')
        
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

# --- Gestión de Cursos ---
@admin_bp.route('/gestion_cursos')
@login_required
@role_required(1)
def gestion_cursos():
    """Gestión de cursos"""
    form = CursoForm()
    return render_template('superadmin/gestion_academica/cursos.html', form=form)

@admin_bp.route('/api/cursos', methods=['GET', 'POST', 'DELETE'])
@login_required
@role_required(1)
def api_cursos():
    """API para gestión de cursos"""
    if request.method == 'GET':
        try:
            cursos = db.session.query(Curso, Sede.nombre).join(Sede).all()
            cursos_list = [{
                'id_curso': c.id_curso,
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
                    sedeId=sede.id_sede if sede else None
                )
                db.session.add(nuevo_curso)
                db.session.commit()
                return jsonify({
                    'id_curso': nuevo_curso.id_curso,
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
        curso_id = data.get('id_curso')
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

@admin_bp.route('/api/cursos/<int:curso_id>')
@login_required
@role_required(1)
def api_obtener_curso(curso_id):
    """API para obtener información de un curso específico"""
    try:
        curso = Curso.query.get_or_404(curso_id)
        
        return jsonify({
            'id_curso': curso.id_curso,
            'nombreCurso': curso.nombreCurso,
            'sedeId': curso.sedeId,
            'horario_general_id': curso.horario_general_id,
            'sede': curso.sede.nombre if curso.sede else None
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Gestión de Asignaturas ---
@admin_bp.route('/gestion-asignaturas')
@login_required
@role_required(1)
def gestion_asignaturas():
    """Gestión de asignaturas"""
    return render_template('superadmin/gestion_academica/gestion_asignaturas.html')

@admin_bp.route('/api/asignaturas')
@login_required
@role_required(1)
def api_asignaturas():
    """API para obtener todas las asignaturas con sus profesores"""
    try:
        asignaturas = Asignatura.query.order_by(Asignatura.nombre).all()
        return jsonify([{
            'id_asignatura': a.id_asignatura,
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
        
        for profesor_id in profesores_ids:
            profesor = Usuario.query.get(profesor_id)
            if profesor:
                nueva_asignatura.profesores.append(profesor)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Asignatura creada correctamente',
            'asignatura': {
                'id_asignatura': nueva_asignatura.id_asignatura,
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
        print(f"Error creando asignatura: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/asignaturas/<int:asignatura_id>', methods=['PUT'])
@login_required
@role_required(1)
def api_actualizar_asignatura(asignatura_id):
    """API para actualizar una asignatura existente con profesores"""
    try:
        data = request.get_json()
        
        asignatura = Asignatura.query.get_or_404(asignatura_id)
        
        if not data.get('nombre'):
            return jsonify({'success': False, 'error': 'El nombre de la asignatura es requerido'}), 400
        
        # Verificar si ya existe otra asignatura con el mismo nombre
        existe = Asignatura.query.filter(
            Asignatura.nombre == data['nombre'],
            Asignatura.id_asignatura != asignatura_id
        ).first()
        if existe:
            return jsonify({'success': False, 'error': 'Ya existe otra asignatura con ese nombre'}), 400
        
        asignatura.nombre = data['nombre']
        asignatura.descripcion = data.get('descripcion', '')
        asignatura.estado = data.get('estado', 'activa')
        
        # Actualizar profesores - limpiar y agregar nuevos
        profesores_ids = data.get('profesores', [])
        
        # Limpiar profesores actuales
        asignatura.profesores.clear()
        
        # Agregar nuevos profesores
        for profesor_id in profesores_ids:
            profesor = Usuario.query.get(profesor_id)
            if profesor:
                asignatura.profesores.append(profesor)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Asignatura actualizada correctamente',
            'asignatura': {
                'id_asignatura': asignatura.id_asignatura,
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
        print(f"Error actualizando asignatura: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/asignaturas/<int:asignatura_id>', methods=['DELETE'])
@login_required
@role_required(1)
def api_eliminar_asignatura(asignatura_id):
    """API para eliminar una asignatura"""
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

# ==================== SISTEMA DE HORARIOS ====================

@admin_bp.route('/gestion-horarios')
@login_required
@role_required(1)
def gestion_horarios():
    """Gestión de horarios generales"""
    return render_template('superadmin/Horarios/gestion_horarios.html')

@admin_bp.route('/api/horarios/nuevo', methods=['POST'])
@login_required
@role_required(1)
def api_crear_horario_completo():
    """API para crear un nuevo horario general"""
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
                    horario_general_id=nuevo_horario.id_horario,
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
                'id_horario': nuevo_horario.id_horario,
                'nombre': nuevo_horario.nombre,
                'periodo': nuevo_horario.periodo
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creando horario: {str(e)}")
        return jsonify({'success': False, 'error': f'Error del servidor: {str(e)}'}), 500

@admin_bp.route('/api/horarios/<int:horario_id>', methods=['GET'])
@login_required
@role_required(1)
def api_obtener_horario(horario_id):
    """API para obtener un horario específico"""
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
            'id_horario': horario.id_horario,
            'nombre': horario.nombre,
            'periodo': horario.periodo,
            'horaInicio': horario.horaInicio.strftime('%H:%M'),
            'horaFin': horario.horaFin.strftime('%H:%M'),
            'dias': dias_lista,
            'bloques': [{
                'id_bloque': b.id_bloque,
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
        print(f"Error obteniendo horario: {str(e)}")
        return jsonify({'error': f'Error al obtener horario: {str(e)}'}), 500

@admin_bp.route('/api/horarios', methods=['GET'])
@login_required
@role_required(1)
def api_listar_horarios():
    """API para listar todos los horarios"""
    try:
        horarios = HorarioGeneral.query.all()
        return jsonify([{
            'id_horario': h.id_horario,
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
    """API para eliminar un horario"""
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
    """API para asignar horario a cursos"""
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
    """API para estadísticas de horarios"""
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
    """Gestión de horarios por curso"""
    return render_template('superadmin/Horarios/gestion_horarios_cursos.html')

def validar_conflicto_horario_profesor(profesor_id, dia_semana, hora_inicio, hora_fin, curso_id_excluir=None, asignatura_id_excluir=None):
    """
    Valida si un profesor tiene conflicto de horarios en el mismo día y hora.
    
    Args:
        profesor_id: ID del profesor a validar
        dia_semana: Día de la semana (ej: 'lunes', 'martes', etc.)
        hora_inicio: Hora de inicio en formato 'HH:MM'
        hora_fin: Hora de fin en formato 'HH:MM'
        curso_id_excluir: ID del curso a excluir de la validación (para ediciones)
        asignatura_id_excluir: ID de la asignatura a excluir de la validación (para ediciones)
    
    Returns:
        dict: {'tiene_conflicto': bool, 'conflicto_info': str}
    """
    try:
        from datetime import datetime, time, timedelta
        
        # Convertir horas a objetos time para comparación
        hora_inicio_obj = datetime.strptime(hora_inicio, '%H:%M').time()
        hora_fin_obj = datetime.strptime(hora_fin, '%H:%M').time()
        
        # Buscar todos los horarios compartidos del profesor
        horarios_profesor = HorarioCompartido.query.filter_by(profesor_id=profesor_id).all()
        
        for horario_comp in horarios_profesor:
            # Excluir el curso/asignatura actual si se está editando
            if (curso_id_excluir and horario_comp.curso_id == curso_id_excluir and 
                asignatura_id_excluir and horario_comp.asignatura_id == asignatura_id_excluir):
                continue
                
            # Buscar el HorarioCurso correspondiente
            horario_curso = HorarioCurso.query.filter_by(
                curso_id=horario_comp.curso_id,
                asignatura_id=horario_comp.asignatura_id
            ).first()
            
            if not horario_curso:
                continue
                
            # Verificar si es el mismo día
            if horario_curso.dia_semana.lower() != dia_semana.lower():
                continue
                
            # Convertir horas del horario existente
            try:
                hora_inicio_existente = datetime.strptime(horario_curso.hora_inicio, '%H:%M').time()
                hora_fin_existente = datetime.strptime(horario_curso.hora_fin, '%H:%M').time()
            except:
                continue
                
            # Verificar solapamiento de horarios
            # Dos horarios se solapan si: inicio1 < fin2 Y fin1 > inicio2
            if (hora_inicio_obj < hora_fin_existente and hora_fin_obj > hora_inicio_existente):
                # Obtener información del conflicto
                curso = Curso.query.get(horario_comp.curso_id)
                asignatura = Asignatura.query.get(horario_comp.asignatura_id)
                
                return {
                    'tiene_conflicto': True,
                    'conflicto_info': f"Conflicto con {asignatura.nombre if asignatura else 'Asignatura'} en {curso.nombreCurso if curso else 'Curso'} ({horario_curso.hora_inicio}-{horario_curso.hora_fin})"
                }
        
        return {'tiene_conflicto': False, 'conflicto_info': ''}
        
    except Exception as e:
        print(f"Error en validación de conflicto: {str(e)}")
        return {'tiene_conflicto': False, 'conflicto_info': ''}

@admin_bp.route('/api/horario_curso/guardar', methods=['POST'])
@login_required
@role_required(1)
def api_guardar_horario_curso():
    """API para guardar horario de curso - VERSIÓN CORREGIDA CON VALIDACIÓN DE CONFLICTOS"""
    try:
        data = request.get_json()
        
        print("=" * 50)
        print("DEBUG - DATOS RECIBIDOS EN EL BACKEND:")
        print("=" * 50)
        print(f"Data completa: {data}")
        print(f"Curso ID: {data.get('curso_id')}")
        print(f"Horario General ID: {data.get('horario_general_id')}")
        
        asignaciones = data.get('asignaciones', {})
        salones_asignaciones = data.get('salones_asignaciones', {})
        
        print(f"Asignaciones recibidas: {asignaciones}")
        print(f"Salones recibidos: {salones_asignaciones}")
        print(f"Total asignaciones: {len(asignaciones)}")
        print(f"Total salones: {len(salones_asignaciones)}")
        
        # Mostrar las primeras 5 asignaciones para debug
        if asignaciones:
            print("Primeras 5 asignaciones:")
            for i, (clave, valor) in enumerate(list(asignaciones.items())[:5]):
                print(f"   {i+1}. {clave} -> {valor}")

        curso_id = data.get('curso_id')
        if not curso_id:
            print("ERROR: No hay curso_id")
            return jsonify({'success': False, 'error': 'ID de curso requerido'}), 400

        # Verificar que el curso existe
        curso = Curso.query.get(curso_id)
        if not curso:
            print(f"ERROR: Curso {curso_id} no encontrado")
            return jsonify({'success': False, 'error': 'Curso no encontrado'}), 404

        # Obtener asignaciones existentes
        asignaciones_existentes = HorarioCurso.query.filter_by(curso_id=curso_id).all()
        print(f"Asignaciones existentes en BD: {len(asignaciones_existentes)}")

        # Crear diccionario de asignaciones existentes
        asignaciones_existentes_dict = {}
        for asignacion in asignaciones_existentes:
            clave = f"{asignacion.dia_semana}-{asignacion.hora_inicio}"
            asignaciones_existentes_dict[clave] = asignacion
            print(f"   {clave} -> Asignatura: {asignacion.asignatura_id}, Salon: {asignacion.id_salon_fk}")

        asignaciones_creadas = 0
        asignaciones_actualizadas = 0
        asignaciones_eliminadas = 0

        # Procesar CADA asignación del request
        print("Procesando asignaciones del request...")
        for clave, asignatura_id in asignaciones.items():
            try:
                print(f"   Procesando: {clave} -> {asignatura_id}")
                
                # Parsear la clave
                partes = clave.split('-')
                if len(partes) < 2:
                    print(f"   Clave inválida: {clave}")
                    continue
                    
                dia = partes[0]
                hora_inicio = partes[1]

                # Si no hay asignatura_id, eliminar
                if not asignatura_id:
                    if clave in asignaciones_existentes_dict:
                        db.session.delete(asignaciones_existentes_dict[clave])
                        asignaciones_eliminadas += 1
                        print(f"   Eliminada asignación vacía: {clave}")
                    continue

                # Verificar asignatura
                asignatura = Asignatura.query.get(asignatura_id)
                if not asignatura:
                    print(f"   Asignatura no encontrada: {asignatura_id}")
                    continue

                # Calcular hora_fin (versión simplificada)
                hora_fin = "08:00"  # Valor por defecto
                try:
                    from datetime import datetime, timedelta
                    hora_inicio_dt = datetime.strptime(hora_inicio, '%H:%M')
                    hora_fin_dt = hora_inicio_dt + timedelta(minutes=45)
                    hora_fin = hora_fin_dt.strftime('%H:%M')
                except:
                    pass

                # VALIDACIÓN DE CONFLICTOS DE HORARIOS
                # Verificar conflictos para todos los profesores de esta asignatura
                profesores_asignatura = asignatura.profesores
                for profesor in profesores_asignatura:
                    # Determinar si es una edición (existe la asignación)
                    curso_id_excluir = curso_id if clave in asignaciones_existentes_dict else None
                    asignatura_id_excluir = asignatura_id if clave in asignaciones_existentes_dict else None
                    
                    # Validar conflicto de horario
                    validacion = validar_conflicto_horario_profesor(
                        profesor_id=profesor.id_usuario,
                        dia_semana=dia,
                        hora_inicio=hora_inicio,
                        hora_fin=hora_fin,
                        curso_id_excluir=curso_id_excluir,
                        asignatura_id_excluir=asignatura_id_excluir
                    )
                    
                    if validacion['tiene_conflicto']:
                        print(f"   CONFLICTO DETECTADO: {validacion['conflicto_info']}")
                        return jsonify({
                            'success': False, 
                            'error': f"Conflicto de horario detectado para el profesor {profesor.nombre} {profesor.apellido}: {validacion['conflicto_info']}"
                        }), 400

                # Obtener salon
                salon_id = salones_asignaciones.get(clave)
                if salon_id:
                    salon = Salon.query.get(salon_id)
                    if not salon:
                        print(f"   Salón no encontrado: {salon_id}")
                        salon_id = None

                # Crear o actualizar asignación
                if clave in asignaciones_existentes_dict:
                    asignacion_existente = asignaciones_existentes_dict[clave]
                    asignacion_existente.asignatura_id = asignatura_id
                    asignacion_existente.hora_fin = hora_fin
                    asignacion_existente.id_salon_fk = salon_id
                    asignaciones_actualizadas += 1
                    print(f"   ACTUALIZADA: {clave}")
                else:
                    nueva_asignacion = HorarioCurso(
                        curso_id=curso_id,
                        asignatura_id=asignatura_id,
                        dia_semana=dia,
                        hora_inicio=hora_inicio,
                        hora_fin=hora_fin,
                        horario_general_id=data.get('horario_general_id'),
                        id_salon_fk=salon_id,
                        fecha_creacion=datetime.now()
                    )
                    db.session.add(nueva_asignacion)
                    asignaciones_creadas += 1
                    print(f"   CREADA: {clave}")

            except Exception as e:
                print(f"   Error procesando {clave}: {str(e)}")
                continue

        # Eliminar asignaciones obsoletas
        claves_request = set(asignaciones.keys())
        for clave, asignacion_existente in list(asignaciones_existentes_dict.items()):
            if clave not in claves_request or not asignaciones.get(clave):
                db.session.delete(asignacion_existente)
                asignaciones_eliminadas += 1
                print(f"   ELIMINADA: {clave}")

        # Hacer commit
        db.session.commit()
        
        # Verificar resultado final
        total_final = HorarioCurso.query.filter_by(curso_id=curso_id).count()
        
        print("=" * 50)
        print("RESUMEN FINAL:")
        print(f"   Creadas: {asignaciones_creadas}")
        print(f"   Actualizadas: {asignaciones_actualizadas}")
        print(f"   Eliminadas: {asignaciones_eliminadas}")
        print(f"   Total en BD: {total_final}")
        print("=" * 50)

        return jsonify({
            'success': True,
            'message': f'Horario guardado: {asignaciones_creadas} nuevas, {asignaciones_actualizadas} actualizadas, {asignaciones_eliminadas} eliminadas',
            'stats': {
                'creadas': asignaciones_creadas,
                'actualizadas': asignaciones_actualizadas,
                'eliminadas': asignaciones_eliminadas,
                'total': total_final
            }
        })

    except Exception as e:
        db.session.rollback()
        print(f"ERROR CRÍTICO: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Error del servidor: {str(e)}'}), 500
    
@admin_bp.route('/api/horario_curso/cargar/<int:curso_id>')
@login_required
@role_required(1)
def api_cargar_horario_curso(curso_id):
    """API para cargar horario de curso - VERSIÓN MEJORADA"""
    try:
        curso = Curso.query.get(curso_id)
        if not curso:
            return jsonify({'error': 'Curso no encontrado'}), 404

        # Obtener asignaciones existentes
        asignaciones_db = HorarioCurso.query.filter_by(curso_id=curso_id).all()

        asignaciones = {}
        salones_asignaciones = {}
        
        for asignacion in asignaciones_db:
            clave = f"{asignacion.dia_semana}-{asignacion.hora_inicio}"
            asignaciones[clave] = asignacion.asignatura_id
            if asignacion.id_salon_fk:
                salones_asignaciones[clave] = asignacion.id_salon_fk

        # Obtener bloques del horario general
        bloques_horario = []
        if curso.horario_general_id:
            bloques = BloqueHorario.query.filter_by(
                horario_general_id=curso.horario_general_id
            ).order_by(BloqueHorario.orden).all()

            bloques_horario = [{
                'id_bloque': b.id_bloque,
                'dia_semana': b.dia_semana,
                'horaInicio': b.horaInicio.strftime('%H:%M'),
                'horaFin': b.horaFin.strftime('%H:%M'),
                'tipo': b.tipo,
                'nombre': b.nombre,
                'class_type': b.class_type,
                'break_type': b.break_type
            } for b in bloques]

        print(f"📥 Cargando horario para curso {curso_id}:")
        print(f"   Asignaciones: {len(asignaciones)}")
        print(f"   Salones: {len(salones_asignaciones)}")
        print(f"   Bloques: {len(bloques_horario)}")

        return jsonify({
            'curso_id': curso_id,
            'horario_general_id': curso.horario_general_id,
            'nombre_curso': curso.nombreCurso,
            'asignaciones': asignaciones,
            'salones_asignaciones': salones_asignaciones,
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
    """API para compartir horario con profesores"""
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
            
            # VALIDACIÓN DE CONFLICTOS ANTES DE COMPARTIR
            for profesor in profesores_asignados:
                for clave, asignatura_id in asignaciones.items():
                    if asignatura_id:
                        asignatura = Asignatura.query.get(asignatura_id)
                        if asignatura and profesor in asignatura.profesores:
                            # Parsear la clave para obtener día y hora
                            partes = clave.split('-')
                            if len(partes) >= 2:
                                dia = partes[0]
                                hora_inicio = partes[1]
                                
                                # Calcular hora_fin
                                try:
                                    from datetime import datetime, timedelta
                                    hora_inicio_dt = datetime.strptime(hora_inicio, '%H:%M')
                                    hora_fin_dt = hora_inicio_dt + timedelta(minutes=45)
                                    hora_fin = hora_fin_dt.strftime('%H:%M')
                                except:
                                    hora_fin = "08:00"
                                
                                # Validar conflicto de horario
                                validacion = validar_conflicto_horario_profesor(
                                    profesor_id=profesor.id_usuario,
                                    dia_semana=dia,
                                    hora_inicio=hora_inicio,
                                    hora_fin=hora_fin
                                )
                                
                                if validacion['tiene_conflicto']:
                                    return jsonify({
                                        'success': False, 
                                        'error': f"No se puede compartir el horario. Conflicto detectado para el profesor {profesor.nombre} {profesor.apellido}: {validacion['conflicto_info']}"
                                    }), 400

            # Guardar relaciones profesor-curso-horario (solo si no hay conflictos)
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
        print(f"Error compartiendo horario: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/estadisticas/horarios-cursos')
@login_required
@role_required(1)
def api_estadisticas_horarios_cursos():
    """API para estadísticas de horarios de cursos"""
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

# ==================== GESTIÓN DE INVENTARIO ====================

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

@admin_bp.route('/api/equipos', methods=['GET'])
@login_required
@role_required(1)
def api_equipos_todos():
    equipos = Equipo.query.all()
    return jsonify([e.to_dict() for e in equipos])

@admin_bp.route('/api/estudiantes-por-curso/<int:curso_id>', methods=['GET'])
@login_required
@role_required(1)
def api_estudiantes_por_curso(curso_id):
    """API para obtener estudiantes de un curso específico"""
    try:
        # Obtener el rol de estudiante
        rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()
        if not rol_estudiante:
            return jsonify([]), 200
        
        # Obtener estudiantes matriculados en el curso
        estudiantes = db.session.query(Usuario).join(
            Matricula, Usuario.id_usuario == Matricula.estudianteId
        ).filter(
            Usuario.id_rol_fk == rol_estudiante.id_rol,
            Matricula.cursoId == curso_id,
            Usuario.estado_cuenta == 'activa'
        ).order_by(Usuario.nombre, Usuario.apellido).all()
        
        # Formatear respuesta
        estudiantes_data = []
        for est in estudiantes:
            estudiantes_data.append({
                'id_usuario': est.id_usuario,
                'nombre_completo': est.nombre_completo,
                'no_identidad': est.no_identidad,
                'correo': est.correo
            })
        
        return jsonify(estudiantes_data), 200
        
    except Exception as e:
        print(f"Error obteniendo estudiantes por curso: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/registro_equipos', methods=['GET', 'POST'])
@login_required
@role_required(1)
def crear_equipo():
    """Registro de nuevo equipo"""
    form = EquipoForm()
    cursos = Curso.query.all()
    if form.validate_on_submit():
        try:
            if form.asignado_a.data:
                estado_inicial = 'Asignado'
            else:
                estado_inicial = 'Disponible'
            
            nuevo_equipo = Equipo(
                id_referencia=form.id_referencia.data,
                nombre=form.nombre.data,
                tipo=form.tipo.data,
                estado=estado_inicial,
                id_salon_fk=form.salon.data.id_salon if form.salon.data else None,
                sistema_operativo=form.sistema_operativo.data,
                ram=form.ram.data,
                disco_duro=form.disco_duro.data,
                fecha_adquisicion=datetime.strptime(form.fecha_adquisicion.data, '%Y-%m-%d').date() if form.fecha_adquisicion.data else None,
                descripcion=form.descripcion.data,
                observaciones=form.observaciones.data
            )
            db.session.add(nuevo_equipo)
            db.session.flush()  # Para obtener el ID del equipo

            # ✅ Procesar asignaciones de estudiantes
            estudiantes_ids = request.form.getlist('estudiantes_asignados[]')

            if estudiantes_ids:
                for estudiante_id in estudiantes_ids:
                    nueva_asignacion = AsignacionEquipo(
                        equipo_id=nuevo_equipo.id_equipo,
                        estudiante_id=int(estudiante_id),
                        fecha_asignacion=datetime.now(),
                        estado_asignacion='activa'
                    )
                    db.session.add(nueva_asignacion)

                # Si hay asignaciones, cambiar estado del equipo
                nuevo_equipo.estado = 'Asignado'

            # Commit una vez aplicadas las operaciones
            db.session.commit()

            flash(f'Equipo "{nuevo_equipo.nombre}" creado exitosamente{f" con {len(estudiantes_ids)} asignaciones" if estudiantes_ids else ""}!', 'success')
            return redirect(url_for('admin.equipos'))

        except Exception as e:
            db.session.rollback()
            print(f"Error creando equipo: {e}")
            flash(f'Error al crear equipo: {str(e)}', 'error')
            return redirect(url_for('admin.crear_equipo'))

    return render_template(
        'superadmin/gestion_inventario/registro_equipo.html',
        title='Crear Nuevo Equipo',
        form=form,
        cursos=cursos
    )

@admin_bp.route('/api/equipos/con-incidentes', methods=['GET'])
@login_required
@role_required(1)
def api_equipos_con_incidentes():
    """
    Retorna los IDs de equipos que tienen incidentes activos.
    """
    try:
        todos_incidentes = db.session.query(
            Incidente.equipo_id, 
            Incidente.estado
        ).all()
        
        print("DEBUG - Todos los incidentes en BD:")
        for inc in todos_incidentes:
            print(f"  Equipo ID: {inc.equipo_id}, Estado: '{inc.estado}'")
        
        equipos_con_incidentes = db.session.query(Incidente.equipo_id)\
            .distinct()\
            .all()
        
        ids = [eq[0] for eq in equipos_con_incidentes]
        
        print(f"DEBUG - IDs con incidentes: {ids}")
        
        return jsonify({'equipos_con_incidentes': ids}), 200
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/equipos/<int:id_equipo>', methods=['GET', 'DELETE'])
@login_required
@role_required(1)
def api_equipo_detalle(id_equipo):
    """API para gestión detallada de equipos (Ver y Eliminar)"""
    equipo = Equipo.query.get_or_404(id_equipo)
    
    # Lógica de ELIMINACIÓN (DELETE)
    if request.method == 'DELETE':
        try:
            db.session.delete(equipo)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Equipo eliminado exitosamente'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': f'Error al eliminar el equipo: {str(e)}'}), 500

    # Lógica de VISTA (GET)
    if request.method == 'GET':
        data = equipo.to_dict()
        data['salon_nombre'] = equipo.salon.nombre if equipo.salon else "Sin Salón"
        data['sede_nombre'] = equipo.salon.sede.nombre if equipo.salon and equipo.salon.sede else "Sin Sede"

        # ✅ Información detallada de asignaciones
        asignaciones_activas = equipo.get_asignaciones_activas()
        data['asignaciones'] = []
        
        for asig in asignaciones_activas:
            # Obtener curso del estudiante
            matricula = Matricula.query.filter_by(
                estudianteId=asig.estudiante_id
            ).order_by(Matricula.año.desc()).first()
            
            data['asignaciones'].append({
                'id_asignacion': asig.id_asignacion,
                'estudiante_id': asig.estudiante_id,
                'estudiante_nombre': asig.estudiante.nombre_completo if asig.estudiante else 'Desconocido',
                'estudiante_curso': matricula.curso.nombreCurso if matricula and matricula.curso else 'Sin curso',
                'curso_id': matricula.cursoId if matricula else None,
                'fecha_asignacion': asig.fecha_asignacion.strftime('%Y-%m-%d') if asig.fecha_asignacion else None,
                'observaciones': asig.observaciones
            })

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
    salones = Salon.query.all()
    return render_template('superadmin/gestion_inventario/salones.html', salones=salones)

# ===============================
# API Sedes, Salas y Equipos
# ===============================

@admin_bp.route('/api/estudiante/<int:estudiante_id>/equipos-en-sala/<int:salon_id>', methods=['GET'])
@login_required
@role_required(1)
def api_verificar_equipo_estudiante_en_sala(estudiante_id, salon_id):
    """API para verificar si un estudiante ya tiene un equipo asignado en una sala específica"""
    try:
        # Buscar asignaciones activas del estudiante en esta sala específica
        asignacion_en_sala = db.session.query(AsignacionEquipo)\
            .join(Equipo, AsignacionEquipo.equipo_id == Equipo.id_equipo)\
            .filter(
                AsignacionEquipo.estudiante_id == estudiante_id,
                AsignacionEquipo.estado_asignacion == 'activa',
                Equipo.id_salon_fk == salon_id
            ).first()
        
        if asignacion_en_sala:
            return jsonify({
                'tiene_equipo_en_sala': True,
                'equipo_id': asignacion_en_sala.equipo_id,
                'equipo_nombre': asignacion_en_sala.equipo.nombre,
                'salon_id': salon_id,
                'salon_nombre': asignacion_en_sala.equipo.salon.nombre if asignacion_en_sala.equipo.salon else 'Sin nombre'
            }), 200
        
        return jsonify({
            'tiene_equipo_en_sala': False,
            'equipo_id': None,
            'equipo_nombre': None
        }), 200
        
    except Exception as e:
        print(f"Error verificando equipo del estudiante en sala: {e}")
        return jsonify({'error': str(e)}), 500
    
@admin_bp.route('/api/equipos/<int:equipo_id>/actualizar', methods=['PUT'])
@login_required
@role_required(1)
def api_actualizar_equipo(equipo_id):
    """API para actualizar equipo con validación: solo UN equipo por estudiante por sala"""
    try:
        data = request.get_json()
        equipo = Equipo.query.get_or_404(equipo_id)
        
        # Actualizar campos básicos
        equipo.sistema_operativo = data.get('sistema_operativo', equipo.sistema_operativo)
        equipo.ram = data.get('ram', equipo.ram)
        equipo.disco_duro = data.get('disco_duro', equipo.disco_duro)
        equipo.descripcion = data.get('descripcion', equipo.descripcion)
        equipo.observaciones = data.get('observaciones', equipo.observaciones)
        
        if data.get('fecha_adquisicion'):
            equipo.fecha_adquisicion = datetime.strptime(data['fecha_adquisicion'], '%Y-%m-%d').date()
        
        # Procesar asignaciones
        asignaciones_nuevas = data.get('asignaciones', [])
        salon_id = equipo.id_salon_fk
        
        # ✅ VALIDACIÓN: Verificar que ningún estudiante tenga YA otro equipo en ESTA sala
        for asig_data in asignaciones_nuevas:
            estudiante_id = asig_data['estudiante_id']
            
            # Buscar si el estudiante tiene OTRO equipo activo en ESTA MISMA sala
            otra_asignacion_misma_sala = db.session.query(AsignacionEquipo)\
                .join(Equipo, AsignacionEquipo.equipo_id == Equipo.id_equipo)\
                .filter(
                    AsignacionEquipo.estudiante_id == estudiante_id,
                    AsignacionEquipo.estado_asignacion == 'activa',
                    Equipo.id_salon_fk == salon_id,
                    Equipo.id_equipo != equipo_id  # Excluir el equipo actual
                ).first()
            
            if otra_asignacion_misma_sala:
                estudiante = Usuario.query.get(estudiante_id)
                equipo_existente = otra_asignacion_misma_sala.equipo
                salon_nombre = equipo_existente.salon.nombre if equipo_existente.salon else 'Sin nombre'
                return jsonify({
                    'success': False,
                    'error': f'❌ El estudiante "{estudiante.nombre_completo}" ya tiene el equipo "{equipo_existente.nombre}" asignado en esta sala ({salon_nombre}).\n\nSolo puede tener UN equipo por sala.'
                }), 400
        
        # Eliminar asignaciones que ya no están en la lista
        asignaciones_actuales = AsignacionEquipo.query.filter_by(
            equipo_id=equipo_id,
            estado_asignacion='activa'
        ).all()
        
        estudiantes_nuevos_ids = [asig['estudiante_id'] for asig in asignaciones_nuevas]
        
        for asig_actual in asignaciones_actuales:
            if asig_actual.estudiante_id not in estudiantes_nuevos_ids:
                asig_actual.estado_asignacion = 'devuelto'
                asig_actual.fecha_devolucion = datetime.now()
        
        # Agregar nuevas asignaciones
        for asig_data in asignaciones_nuevas:
            estudiante_id = asig_data['estudiante_id']
            
            # Verificar si ya existe esta asignación específica
            existe = AsignacionEquipo.query.filter_by(
                equipo_id=equipo_id,
                estudiante_id=estudiante_id,
                estado_asignacion='activa'
            ).first()
            
            if not existe:
                nueva_asignacion = AsignacionEquipo(
                    equipo_id=equipo_id,
                    estudiante_id=estudiante_id,
                    fecha_asignacion=datetime.now(),
                    estado_asignacion='activa'
                )
                db.session.add(nueva_asignacion)
        
        # Actualizar estado del equipo
        if len(estudiantes_nuevos_ids) > 0:
            equipo.estado = 'Asignado'
        else:
            equipo.estado = 'Disponible'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'✅ Equipo actualizado exitosamente con {len(estudiantes_nuevos_ids)} asignaciones'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error actualizando equipo: {e}")
        return jsonify({
            'success': False,
            'error': f'Error del servidor: {str(e)}'
        }), 500

@admin_bp.route('/api/sedes/<int:id_sede>/salas')
@login_required
@role_required(1)
def api_salas_por_sede(id_sede):
    """API para obtener salas por sede"""
    salones = Salon.query.filter_by(id_sede_fk=id_sede).all()
    return jsonify([{"id_salon": s.id_salon, "nombre": s.nombre, "tipo": s.tipo} for s in salones])

@admin_bp.route('/api/salas_todas', methods=['GET'])
@login_required
@role_required(1)
def api_salas_todas():
    """API para obtener todas las salas"""
    salones = Salon.query.all()
    result = []
    for s in salones:
        sede_nombre = s.sede.nombre if s.sede else 'N/A'
        total_equipos = Equipo.query.filter_by(id_salon_fk=s.id_salon).count()
        result.append({
            'id_salon': s.id_salon,
            'nombre': s.nombre,
            'tipo': s.tipo,
            'capacidad': s.capacidad,
            'id_sede': s.id_sede_fk,
            'sede_nombre': sede_nombre,
            'total_equipos': total_equipos
        })
    return jsonify(result)

@admin_bp.route('/api/salones/<int:id_salon>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@role_required(1)
def api_salon_detalle(id_salon):
    """
    Endpoint para gestionar un salón específico (Ver, Editar, Eliminar).
    """
    salon = Salon.query.get_or_404(id_salon)

    if request.method == 'GET':
        sede_nombre = salon.sede.nombre if salon.sede else 'N/A'
        total_equipos = Equipo.query.filter_by(id_salon_fk=id_salon).count()
        return jsonify({
            'id_salon': salon.id_salon,
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
        equipos_asociados = Equipo.query.filter_by(id_salon_fk=id_salon).first()
        if equipos_asociados:
            return jsonify({'success': False, 'error': 'No se puede eliminar el salón porque tiene equipos asociados.'}), 400
        try:
            db.session.delete(salon)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Salón eliminado exitosamente'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': f'Error al eliminar el salón: {str(e)}'}), 500
        
@admin_bp.route('/api/sedes/<int:id_sede>/salas/<int:id_salon>/equipos')
@login_required
@role_required(1)
def api_equipos_por_sala(id_sede, id_salon):
    """API para obtener equipos por sala"""
    equipos = Equipo.query.filter_by(id_salon_fk=id_salon).all()
    data = []
    for eq in equipos:
        data.append({
            "id": eq.id_equipo,
            "nombre": eq.nombre,
            "estado": eq.estado
        })
        
    return jsonify(data)

@admin_bp.route('/reportes')
@login_required
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
    try:
        # 1. Total de equipos
        total = db.session.query(Equipo).count()
        
        # 2. Conteo por estado del equipo
        estados_raw = db.session.query(Equipo.estado, db.func.count(Equipo.estado))\
                                .group_by(Equipo.estado).all()
        estados = {e[0]: e[1] for e in estados_raw}
        
        # ✅ 3. Contar equipos con incidentes activos (sin importar su estado)
        equipos_con_incidentes = db.session.query(Incidente.equipo_id)\
            .distinct()\
            .count()
        
        # ✅ 4. Contar equipos con mantenimientos programados
        equipos_con_mantenimientos = db.session.query(Mantenimiento.equipo_id)\
            .filter(Mantenimiento.estado.in_(['pendiente', 'en_progreso']))\
            .distinct()\
            .count()
            
        # ✅ 5. Contar equipos con revisiones programadas
        #equipos_con_revisiones = db.session.query(Revision.equipo_id)\
            # .filter(Revision.estado.in_(['pendiente', 'en_progreso']))
        
        data = {
            'total_equipos': total,
            'estados': {
                'Disponible': estados.get('Disponible', 0),
                'Mantenimiento': estados.get('Mantenimiento', 0),
                'Incidente': estados.get('Incidente', 0),
                'Asignado': estados.get('Asignado', 0),
                'Revisión': estados.get('Revisión', 0),
                **{k: v for k, v in estados.items() if k not in ['Disponible', 'Mantenimiento', 'Incidente', 'Asignado', 'Revisión']}
            },
            'equipos_con_incidentes': equipos_con_incidentes,
            'equipos_con_mantenimientos': equipos_con_mantenimientos
            
        }
        
        return jsonify(data), 200
        
    except Exception as e:
        print(f"Error en reportes estado equipos: {e}")
        return jsonify({'error': f"Error interno del servidor: {str(e)}"}), 500


@admin_bp.route('/api/reportes/equipos_por_sede', methods=['GET'])
@login_required
@role_required(1)
def api_reportes_equipos_por_sede():
    """
    Proporciona datos para el gráfico de equipos por sede.
    """
    # Consulta: Contar equipos agrupados por el nombre de su Sede
    resultados = db.session.query(
        Sede.nombre.label('sede_nombre'),
        db.func.count(Equipo.id_equipo).label('total')
    ).join(Salon, Salon.id_sede_fk == Sede.id_sede)\
    .join(Equipo, Equipo.id_salon_fk == Salon.id_salon)\
    .group_by(Sede.nombre)\
    .order_by(db.func.count(Equipo.id_equipo).desc())\
    .all()
    
    data = [{
        'sede': r.sede_nombre,
        'total': r.total
    } for r in resultados]
    
    return jsonify(data), 200

@admin_bp.route('/incidentes')
@login_required
@role_required(1)
def incidentes():
    """Muestra la página de gestión de incidentes."""
    return render_template('superadmin/gestion_inventario/incidentes.html')

@admin_bp.route('/gestion-salones')
@login_required
@role_required(1)
def gestion_salones():
    """Muestra la página de gestión de salones con estadísticas."""
    return render_template('superadmin/gestion_inventario/salones.html')

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
            id_sede_fk=form.sede.data.id_sede,
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
@role_required(1)
def registro_incidente():
    """Muestra la página para registrar un incidente."""
    return render_template('superadmin/gestion_inventario/registro_incidente.html')

@admin_bp.route('/api/salones', methods=['GET'])
@login_required
@role_required(1)
def api_salones():
    """API para obtener todos los salones"""
    try:
        salones = Salon.query.order_by(Salon.nombre).all()
        return jsonify([{
            'id_salon': s.id_salon,
            'nombre': s.nombre,
            'capacidad': s.capacidad
        } for s in salones])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/equipos_para_incidente', methods=['GET'])
@login_required
@role_required(1)
def api_equipos_para_incidente():
    """
    Retorna solo los equipos con estado 'Incidente' para poder registrar incidentes.
    """
    try:
        equipos_db = db.session.query(
            Equipo.id_equipo,
            Equipo.nombre,
            Equipo.estado,
            Salon.nombre.label('salon_nombre'),
            Sede.nombre.label('sede_nombre')
        ).outerjoin(Salon, Equipo.id_salon_fk == Salon.id_salon)\
         .outerjoin(Sede, Salon.id_sede_fk == Sede.id_sede)\
         .order_by(Equipo.nombre)\
         .all()
        
        equipos = []
        for eq in equipos_db:
            equipos.append({
                'id_equipo': eq.id_equipo,
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
            Incidente.id_incidente,
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
        ).join(Equipo, Incidente.equipo_id == Equipo.id_equipo)\
         .outerjoin(Salon, Equipo.id_salon_fk == Salon.id_salon)\
         .outerjoin(Sede, Salon.id_sede_fk == Sede.id_sede)\
         .order_by(Incidente.fecha.desc())\
         .all()
        
        incidentes = []
        for inc in incidentes_db:
            incidentes.append({
                'id_incidente': inc.id_incidente,
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

@admin_bp.route('/api/incidentes', methods=['POST'])
@login_required
@role_required(1)
def api_crear_incidente():
    """
    Crea un nuevo incidente.
    """
    try:
        data = request.get_json()
        
        # ✅ Validación de datos obligatorios
        equipo_id = data.get('equipo_id')
        descripcion = data.get('descripcion', '').strip()
        prioridad = data.get('prioridad', 'media')
        usuario_reporte = data.get('usuario_reporte', '').strip()
        
        print(f"DEBUG - Datos recibidos:")
        print(f"  equipo_id: {equipo_id}")
        print(f"  descripcion: {descripcion}")
        print(f"  prioridad: {prioridad}")
        print(f"  usuario_reporte: {usuario_reporte}")
        
        # Validaciones
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

        # Verificar que el equipo existe
        equipo = Equipo.query.get(equipo_id)
        if not equipo:
            return jsonify({
                'success': False, 
                'error': f'El equipo con ID {equipo_id} no existe.'
            }), 404
            
        # Obtener sede del equipo
        sede_nombre = "Sin Sede"
        if equipo.salon and equipo.salon.sede:
            sede_nombre = equipo.salon.sede.nombre

        # ✅ Crear el incidente con el nombre de campo correcto
        # Verifica en tu models.py si el campo se llama 'equipo_id' o 'id_equipo'
        nuevo_incidente = Incidente(
            equipo_id=equipo_id,  # Cambia a id_equipo si es necesario
            usuario_asignado=usuario_reporte,
            sede=sede_nombre,
            fecha=datetime.now(),
            descripcion=descripcion,
            estado='reportado',
            prioridad=prioridad,
            solucion_propuesta=data.get('solucion_propuesta', '')
        )
        
        db.session.add(nuevo_incidente)
        db.session.flush()  # Para obtener el ID antes del commit
        
        print(f"DEBUG - Incidente creado con ID: {nuevo_incidente.id_incidente}")
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Incidente creado exitosamente',
            'incidente': {
                'id': nuevo_incidente.id_incidente,
                'equipo_nombre': equipo.nombre,
                'usuario_reporte': usuario_reporte,
                'fecha': nuevo_incidente.fecha.strftime('%Y-%m-%d %H:%M:%S'),
                'estado': nuevo_incidente.estado,
                'prioridad': nuevo_incidente.prioridad
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"❌ ERROR al crear incidente: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': f'Error interno del servidor: {str(e)}'
        }), 500
 
@admin_bp.route('/api/incidentes/<int:id_incidente>/estado', methods=['PUT'])
@login_required
@role_required(1)
def api_actualizar_estado_incidente(id_incidente):
    """API para actualizar estado de incidente"""
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        incidente = Incidente.query.get_or_404(id_incidente)
        
        if not nuevo_estado or nuevo_estado not in ['reportado', 'en_proceso', 'resuelto', 'cerrado']:
             return jsonify({'success': False, 'error': 'Estado inválido.'}), 400

        # 1. Actualizar el estado del incidente
        incidente.estado = nuevo_estado
        
        # 2. Lógica adicional (ej: actualizar estado del Equipo si es 'cerrado/resuelto')
        if nuevo_estado in ['resuelto', 'cerrado'] and incidente.equipo:
            incidente.equipo.estado = 'Disponible'
        elif nuevo_estado == 'reportado' and incidente.equipo:
             incidente.equipo.estado = 'Incidente'
        
        db.session.commit()

        return jsonify({ 
            'success': True, 
            'message': 'Estado actualizado con éxito',
            'incidente_actualizado': incidente.to_dict() 
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error al actualizar estado: {e}")
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500

@admin_bp.route('/api/incidentes/<int:id_incidente>', methods=['DELETE'])
@login_required
@role_required(1)
def api_eliminar_incidente(id_incidente):
    """
    Elimina un incidente por su ID.
    """
    try:
        incidente = Incidente.query.get(id_incidente)
        
        if not incidente:
            return jsonify({'success': False, 'error': 'Incidente no encontrado.'}), 404
        
        db.session.delete(incidente)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Incidente {id_incidente} eliminado exitosamente.'})

    except Exception as e:
        db.session.rollback()
        print(f"Error al eliminar incidente: {e}")
        return jsonify({'success': False, 'error': f'Error interno del servidor: {str(e)}'}), 500

@admin_bp.route('/api/incidentes/<int:id_incidente>', methods=['GET'])
@login_required
@role_required(1)
def api_detalle_incidente(id_incidente):
    """
    Obtiene el detalle completo de un incidente específico.
    """
    try:
        incidente_db = db.session.query(
            Incidente.id_incidente,
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
        ).join(Equipo, Incidente.equipo_id == Equipo.id_equipo)\
         .outerjoin(Salon, Equipo.id_salon_fk == Salon.id_salon)\
         .outerjoin(Sede, Salon.id_sede_fk == Sede.id_sede)\
         .filter(Incidente.id_incidente == id_incidente)\
         .first()
        
        if not incidente_db:
            return jsonify({'success': False, 'error': 'Incidente no encontrado.'}), 404
        
        incidente = {
            'id_incidente': incidente_db.id_incidente,
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

# ==================== CALENDARIO Y EVENTOS ====================

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



# ==================== SISTEMA DE VOTACIÓN ====================

@admin_bp.route('/sistema-votaciones')
@login_required
@role_required(1)
def sistema_votaciones():
    """Vista principal del sistema de votación."""
    return render_template('superadmin/sistema_votaciones/admin.html')

@admin_bp.route('/sistema-votaciones/votar')
@login_required
def votar():
    """Página para votar"""
    return render_template('superadmin/sistema_votaciones/votar.html')



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
    # CORREGIDO: usa id_horario_votacion en lugar de id
    horario = HorarioVotacion.query.order_by(HorarioVotacion.id_horario_votacion.desc()).first()
    if horario:
        return jsonify({
            "inicio": horario.inicio.strftime("%H:%M"),
            "fin": horario.fin.strftime("%H:%M")
        })
    return jsonify({})

# ==================== GESTIÓN DE CANDIDATOS ====================

@admin_bp.route("/listar-candidatos", methods=["GET"])
@login_required
@role_required(1)
def listar_candidatos():
    """API para listar candidatos"""
    candidatos = Candidato.query.all()
    lista = []
    for c in candidatos:
        lista.append({
            "id_candidato": c.id_candidato,
            "nombre": c.nombre,
            "categoria": c.categoria,
            "tarjeton": c.tarjeton,
            "propuesta": c.propuesta,
            "foto": c.foto
        })
    return jsonify(lista)

@admin_bp.route("/crear-candidato", methods=["POST"])
@login_required
@role_required(1)
def crear_candidato():
    """API para crear candidato"""
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
@login_required
@role_required(1)
def editar_candidato(candidato_id):
    """API para editar candidato"""
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
            Candidato.id_candidato != candidato.id_candidato
        ).first()
        if existe_tarjeton:
            return jsonify({"ok": False, "error": "⚠️ Ese número de tarjetón ya existe"}), 400

        # ✅ Validar nombre único
        existe_nombre = Candidato.query.filter(
            Candidato.nombre == nombre,
            Candidato.id_candidato != candidato.id_candidato
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
            candidato.foto = foto_filename

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
                "id_candidato": c.id_candidato,
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
@role_required(1)
def eliminar_candidato(candidato_id):
    """API para eliminar candidato"""
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
                "id_candidato": c.id_candidato,
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



# ============================================================================ #
# RUTAS DE REPORTES DE CALIFICACIONES
# ============================================================================ #

@admin_bp.route('/reportes-calificaciones')
@login_required
@role_required(1)
def reportes_calificaciones():
    """Página principal de reportes de calificaciones."""
    return render_template('superadmin/reportes/reportes.html')

@admin_bp.route('/api/reportes-calificaciones', methods=['GET'])
@login_required
@role_required(1)
def api_obtener_reportes():
    """API para obtener reportes de calificaciones con paginación y filtros."""
    try:
        # Parámetros de paginación
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        estado = request.args.get('estado', '', type=str)
        curso = request.args.get('curso', '', type=str)
        profesor = request.args.get('profesor', '', type=str)
        
        # Construir consulta base
        query = db.session.query(ReporteCalificaciones)
        
        # Aplicar filtros
        if estado:
            query = query.filter(ReporteCalificaciones.estado == estado)
        if curso:
            query = query.filter(ReporteCalificaciones.nombre_curso.ilike(f'%{curso}%'))
        if profesor:
            query = query.join(Usuario, ReporteCalificaciones.profesor_id == Usuario.id_usuario)
            query = query.filter(Usuario.nombre_completo.ilike(f'%{profesor}%'))
        
        # Ordenar por fecha de generación (más recientes primero)
        query = query.order_by(ReporteCalificaciones.fecha_generacion.desc())
        
        # Aplicar paginación
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        reportes_data = [reporte.to_dict() for reporte in pagination.items]
        
        return jsonify({
            'success': True,
            'reportes': reportes_data,
            'pagination': {
                'page': pagination.page,
                'pages': pagination.pages,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev,
                'next_num': pagination.next_num,
                'prev_num': pagination.prev_num
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error obteniendo reportes: {str(e)}'
        }), 500

@admin_bp.route('/api/enviar-comunicado-profesor', methods=['POST'])
@login_required
@role_required(1)
def api_enviar_comunicado_profesor():
    """API para enviar comunicado del admin al profesor sobre un reporte."""
    try:
        data = request.get_json()
        profesor_id = data.get('profesor_id')
        reporte_id = data.get('reporte_id')
        asunto = data.get('asunto')
        mensaje = data.get('mensaje')
        
        if not all([profesor_id, reporte_id, asunto, mensaje]):
            return jsonify({
                'success': False,
                'message': 'Faltan campos requeridos'
            }), 400
        
        # Verificar que el reporte existe
        reporte = ReporteCalificaciones.query.get(reporte_id)
        if not reporte:
            return jsonify({
                'success': False,
                'message': 'Reporte no encontrado'
            }), 404
        
        # Verificar que el profesor existe
        profesor = Usuario.query.get(profesor_id)
        if not profesor:
            return jsonify({
                'success': False,
                'message': 'Profesor no encontrado'
            }), 404
        
        # Crear el comunicado
        from controllers.models import Comunicacion
        comunicado = Comunicacion(
            remitente_id=current_user.id_usuario,
            destinatario_id=profesor_id,
            asunto=f"[Reporte de Calificaciones] {asunto}",
            mensaje=f"Reporte: {reporte.nombre_curso} - {reporte.nombre_asignatura}\n\n{mensaje}",
            estado='inbox'
        )
        
        db.session.add(comunicado)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Comunicado enviado correctamente',
            'comunicado_id': comunicado.id_comunicacion
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error enviando comunicado: {str(e)}'
        }), 500

# ==================== COMUNICACIONES PARA ADMINISTRADORES ====================

@admin_bp.route('/comunicaciones')
@login_required
@role_required(1)
def comunicaciones():
    """Página de comunicaciones para administradores."""
    return render_template('superadmin/comunicaciones.html')

@admin_bp.route('/api/comunicaciones', methods=['GET'])
@login_required
@role_required(1)
def api_obtener_comunicaciones():
    """API para obtener comunicaciones del administrador."""
    try:
        folder = request.args.get('folder', 'inbox')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))  # Reducido para mejor rendimiento
        
        # Obtener comunicaciones según la carpeta con paginación
        if folder == 'inbox':
            # Comunicaciones recibidas (donde el admin es destinatario)
            comunicaciones = db.session.query(Comunicacion).filter(
                Comunicacion.destinatario_id == current_user.id_usuario,
                Comunicacion.estado == 'inbox'
            ).order_by(Comunicacion.fecha_envio.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            ).items
            
            # Convertir a diccionarios de manera más eficiente
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
            # Comunicaciones enviadas (donde el admin es remitente)
            comunicaciones = db.session.query(Comunicacion).filter(
                Comunicacion.remitente_id == current_user.id_usuario,
                Comunicacion.estado.in_(['inbox', 'sent'])
            ).order_by(Comunicacion.fecha_envio.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            ).items
            
            # Agrupar comunicaciones por grupo_id (como Gmail)
            grupos = {}
            for com in comunicaciones:
                grupo_key = com.grupo_id or f"individual_{com.id_comunicacion}"
                if grupo_key not in grupos:
                    grupos[grupo_key] = {
                        'id': com.id_comunicacion,
                        'remitente': com.remitente.nombre_completo if com.remitente else 'Desconocido',
                        'remitente_nombre': com.remitente.nombre_completo if com.remitente else 'Desconocido',
                        'remitente_email': com.remitente.correo if com.remitente else '',
                        'asunto': com.asunto,
                        'mensaje': com.mensaje,
                        'fecha': com.fecha_envio.strftime('%Y-%m-%d %H:%M') if com.fecha_envio else '',
                        'fecha_envio': com.fecha_envio.isoformat() if com.fecha_envio else '',
                        'estado': com.estado,
                        'tipo': 'enviada',
                        'destinatarios': [],
                        'destinatarios_count': 0
                    }
                
                # Agregar destinatario al grupo
                destinatario_info = {
                    'nombre': com.destinatario.nombre_completo if com.destinatario else 'Desconocido',
                    'email': com.destinatario.correo if com.destinatario else '',
                    'id': com.destinatario.id_usuario if com.destinatario else None
                }
                grupos[grupo_key]['destinatarios'].append(destinatario_info)
                grupos[grupo_key]['destinatarios_count'] += 1
            
            # Convertir grupos a lista
            comunicaciones_data = []
            for grupo in grupos.values():
                # Crear texto de destinatarios múltiples
                if grupo['destinatarios_count'] > 1:
                    grupo['destinatario'] = f"{grupo['destinatarios'][0]['nombre']} y {grupo['destinatarios_count'] - 1} más"
                    grupo['destinatario_nombre'] = grupo['destinatario']
                else:
                    grupo['destinatario'] = grupo['destinatarios'][0]['nombre']
                    grupo['destinatario_nombre'] = grupo['destinatario']
                
                comunicaciones_data.append(grupo)
                
        elif folder == 'draft':
            # Borradores del admin
            comunicaciones = db.session.query(Comunicacion).filter(
                Comunicacion.remitente_id == current_user.id_usuario,
                Comunicacion.estado == 'draft'
            ).order_by(Comunicacion.fecha_envio.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            ).items
            
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
                Comunicacion.remitente_id == current_user.id_usuario,
                Comunicacion.estado == 'deleted'
            ).order_by(Comunicacion.fecha_envio.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            ).items
            
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
            return jsonify({'success': False, 'message': 'Carpeta no válida'}), 400

        return jsonify({
            'success': True,
            'recibidas': comunicaciones_data if folder == 'inbox' else [],
            'enviadas': comunicaciones_data if folder == 'sent' else [],
            'data': comunicaciones_data if folder in ['draft', 'deleted'] else []
        })
        
    except Exception as e:
        print(f"Error obteniendo comunicaciones: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error obteniendo comunicaciones: {str(e)}'
        }), 500

@admin_bp.route('/api/comunicaciones', methods=['POST'])
@login_required
@role_required(1)
def api_enviar_comunicacion():
    """API para enviar comunicaciones del administrador."""
    try:
        data = request.get_json()
        recipient_type = data.get('recipient_type')
        recipient_types = data.get('recipient_types') or []
        to_email = data.get('to')
        asunto = data.get('asunto')
        mensaje = data.get('mensaje')
        
        if not all([asunto, mensaje]):
            return jsonify({
                'success': False,
                'message': 'Faltan campos requeridos'
            }), 400
        
        # Determinar destinatarios según el tipo (soporta múltiples)
        destinatarios = []
        tipos = []
        if isinstance(recipient_types, list) and len(recipient_types) > 0:
            tipos = recipient_types
        elif isinstance(recipient_type, str) and recipient_type:
            tipos = [recipient_type]
        
        if 'all' in tipos:
            # Enviar a todos los usuarios activos
            destinatarios = Usuario.query.filter_by(estado_cuenta='activa').all()
        elif len(tipos) > 0:
            # Construir conjunto de destinatarios según roles múltiples
            usuarios_set = set()
            if 'profesores' in tipos:
                rol_profesor = Rol.query.filter_by(nombre='Profesor').first()
                if rol_profesor:
                    for u in Usuario.query.filter_by(id_rol_fk=rol_profesor.id_rol, estado_cuenta='activa').all():
                        usuarios_set.add(u)
            if 'estudiantes' in tipos:
                rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()
                if rol_estudiante:
                    for u in Usuario.query.filter_by(id_rol_fk=rol_estudiante.id_rol, estado_cuenta='activa').all():
                        usuarios_set.add(u)
            if 'padres' in tipos:
                rol_padre = Rol.query.filter_by(nombre='Padre').first()
                if rol_padre:
                    for u in Usuario.query.filter_by(id_rol_fk=rol_padre.id_rol, estado_cuenta='activa').all():
                        usuarios_set.add(u)
            if 'specific' in tipos and to_email:
                destinatario = Usuario.query.filter_by(correo=to_email).first()
                if destinatario:
                    usuarios_set.add(destinatario)
            destinatarios = list(usuarios_set)
        elif recipient_type == 'profesores':
            # Enviar solo a profesores
            rol_profesor = Rol.query.filter_by(nombre='Profesor').first()
            if rol_profesor:
                destinatarios = Usuario.query.filter_by(id_rol_fk=rol_profesor.id_rol, estado_cuenta='activa').all()
        elif recipient_type == 'estudiantes':
            # Enviar solo a estudiantes
            rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()
            if rol_estudiante:
                destinatarios = Usuario.query.filter_by(id_rol_fk=rol_estudiante.id_rol, estado_cuenta='activa').all()
        elif recipient_type == 'padres':
            # Enviar solo a padres
            rol_padre = Rol.query.filter_by(nombre='Padre').first()
            if rol_padre:
                destinatarios = Usuario.query.filter_by(id_rol_fk=rol_padre.id_rol, estado_cuenta='activa').all()
        elif recipient_type == 'specific' and to_email:
            # Enviar a usuario específico
            destinatario = Usuario.query.filter_by(correo=to_email).first()
            if destinatario:
                destinatarios = [destinatario]
            else:
                return jsonify({
                    'success': False,
                    'message': 'Usuario destinatario no encontrado'
                }), 404
        else:
            return jsonify({
                'success': False,
                'message': 'Tipo de destinatario no válido'
            }), 400
        
        if not destinatarios:
            return jsonify({
                'success': False,
                'message': 'No se encontraron destinatarios válidos'
            }), 404
        
        # Crear comunicaciones para cada destinatario (excluyendo al remitente)
        import uuid
        grupo_id = str(uuid.uuid4())  # ID único para agrupar este envío
        comunicaciones_creadas = []
        
        for destinatario in destinatarios:
            # Evitar que el administrador reciba sus propios comunicados
            if destinatario.id_usuario != current_user.id_usuario:
                nueva_comunicacion = Comunicacion(
                    remitente_id=current_user.id_usuario,
                    destinatario_id=destinatario.id_usuario,
                    asunto=asunto,
                    mensaje=mensaje,
                    estado='inbox',
                    grupo_id=grupo_id
                )
                db.session.add(nueva_comunicacion)
                comunicaciones_creadas.append(nueva_comunicacion)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Mensaje enviado a {len(destinatarios)} destinatario(s)',
            'destinatarios_count': len(destinatarios)
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error enviando comunicación: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error enviando comunicación: {str(e)}'
        }), 500

@admin_bp.route('/api/comunicaciones/cleanup', methods=['POST'])
@login_required
@role_required(1)
def api_cleanup_comunicaciones_admin():
    """API para limpiar comunicaciones automáticamente (admin)."""
    try:
        from controllers.models import Comunicacion
        from datetime import datetime, timedelta
        
        # Fecha actual
        now = datetime.utcnow()
        
        # Mensajes de más de 1 mes (30 días) - mover a papelera
        one_month_ago = now - timedelta(days=30)
        
        # Mensajes de más de 2 meses (60 días) en papelera - eliminar permanentemente
        two_months_ago = now - timedelta(days=60)
        
        # Mover mensajes antiguos a papelera
        mensajes_a_papelera = Comunicacion.query.filter(
            Comunicacion.estado.in_(['inbox', 'sent', 'draft']),
            Comunicacion.fecha_envio < one_month_ago
        ).all()
        
        moved_to_trash = 0
        for mensaje in mensajes_a_papelera:
            mensaje.estado = 'deleted'
            moved_to_trash += 1
        
        # Eliminar permanentemente mensajes muy antiguos en papelera
        mensajes_a_eliminar = Comunicacion.query.filter(
            Comunicacion.estado == 'deleted',
            Comunicacion.fecha_envio < two_months_ago
        ).all()
        
        permanently_deleted = 0
        for mensaje in mensajes_a_eliminar:
            db.session.delete(mensaje)
            permanently_deleted += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Limpieza completada: {moved_to_trash} mensajes movidos a papelera, {permanently_deleted} eliminados permanentemente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error en limpieza automática: {str(e)}'
        }), 500

@admin_bp.route('/api/comunicaciones/<int:comunicacion_id>/marcar-leida', methods=['PUT'])
@login_required
@role_required(1)
def api_marcar_comunicacion_leida(comunicacion_id):
    """API para marcar una comunicación como leída."""
    try:
        comunicacion = Comunicacion.query.get(comunicacion_id)
        
        if not comunicacion:
            return jsonify({
                'success': False,
                'message': 'Comunicación no encontrada'
            }), 404
        
        if comunicacion.destinatario_id != current_user.id_usuario:
            return jsonify({
                'success': False,
                'message': 'No tienes permisos para esta comunicación'
            }), 403
        
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

@admin_bp.route('/api/comunicaciones/<int:comunicacion_id>', methods=['DELETE'])
@login_required
@role_required(1)
def api_eliminar_comunicacion(comunicacion_id):
    """API para eliminar una comunicación."""
    try:
        comunicacion = Comunicacion.query.get(comunicacion_id)
        
        if not comunicacion:
            return jsonify({
                'success': False,
                'message': 'Comunicación no encontrada'
            }), 404
        
        # Verificar permisos: remitente o destinatario pueden eliminar
        if (comunicacion.remitente_id != current_user.id_usuario and 
            comunicacion.destinatario_id != current_user.id_usuario):
            return jsonify({
                'success': False,
                'message': 'No tienes permisos para eliminar esta comunicación'
            }), 403
        
        # Si ya está en papelera, eliminar permanentemente
        if comunicacion.estado == 'deleted':
            db.session.delete(comunicacion)
            message = 'Comunicación eliminada permanentemente'
        else:
            # Marcar como eliminada en lugar de eliminar físicamente
            comunicacion.estado = 'deleted'
            message = 'Comunicación movida a papelera'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error eliminando comunicación: {str(e)}'
        }), 500

@admin_bp.route('/api/comunicaciones/bulk-delete', methods=['POST'])
@login_required
@role_required(1)
def api_eliminar_solicitudes_masivas():
    """API para eliminar múltiples comunicaciones."""
    try:
        data = request.get_json()
        comunicacion_ids = data.get('ids', [])
        
        if not comunicacion_ids:
            return jsonify({
                'success': False,
                'message': 'No se proporcionaron IDs de comunicaciones'
            }), 400
        
        # Verificar que todas las comunicaciones pertenecen al usuario actual
        comunicaciones = Comunicacion.query.filter(
            Comunicacion.id_comunicacion.in_(comunicacion_ids),
            db.or_(
                Comunicacion.remitente_id == current_user.id_usuario,
                Comunicacion.destinatario_id == current_user.id_usuario
            )
        ).all()
        
        if len(comunicaciones) != len(comunicacion_ids):
            return jsonify({
                'success': False,
                'message': 'Algunas comunicaciones no se encontraron o no tienes permisos'
            }), 403
        
        # Eliminar comunicaciones
        eliminadas = 0
        movidas_a_papelera = 0
        
        for comunicacion in comunicaciones:
            if comunicacion.estado == 'deleted':
                # Eliminar permanentemente si ya está en papelera
                db.session.delete(comunicacion)
                eliminadas += 1
            else:
                # Mover a papelera
                comunicacion.estado = 'deleted'
                movidas_a_papelera += 1
        
        db.session.commit()
        
        mensaje = []
        if movidas_a_papelera > 0:
            mensaje.append(f'{movidas_a_papelera} comunicación(es) movida(s) a papelera')
        if eliminadas > 0:
            mensaje.append(f'{eliminadas} comunicación(es) eliminada(s) permanentemente')
        
        return jsonify({
            'success': True,
            'message': '; '.join(mensaje)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error eliminando comunicaciones: {str(e)}'
        }), 500

@admin_bp.route('/api/comunicaciones/<int:comunicacion_id>/restore', methods=['PUT'])
@login_required
@role_required(1)
def api_restaurar_comunicacion(comunicacion_id):
    """API para restaurar una comunicación desde la papelera."""
    try:
        comunicacion = Comunicacion.query.get(comunicacion_id)
        
        if not comunicacion:
            return jsonify({
                'success': False,
                'message': 'Comunicación no encontrada'
            }), 404
        
        # Verificar permisos: remitente o destinatario pueden restaurar
        if (comunicacion.remitente_id != current_user.id_usuario and 
            comunicacion.destinatario_id != current_user.id_usuario):
            return jsonify({
                'success': False,
                'message': 'No tienes permisos para restaurar esta comunicación'
            }), 403
        
        # Restaurar el email cambiando su estado a 'inbox'
        comunicacion.estado = 'inbox'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Comunicación restaurada'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error restaurando comunicación: {str(e)}'
        }), 500

@admin_bp.route('/api/comunicaciones/draft', methods=['POST'])
@login_required
@role_required(1)
def api_guardar_borrador():
    """API para guardar un borrador de comunicación."""
    try:
        data = request.get_json()
        to_email = data.get('to')
        asunto = data.get('asunto')
        mensaje = data.get('mensaje')
        
        if not asunto and not mensaje:
            return jsonify({
                'success': False,
                'message': 'No hay contenido para guardar como borrador'
            }), 400
        
        # Buscar usuario destinatario si se especifica
        destinatario_id = None
        if to_email:
            destinatario = Usuario.query.filter_by(correo=to_email).first()
            if destinatario:
                destinatario_id = destinatario.id_usuario
        
        # Crear borrador
        borrador = Comunicacion(
            remitente_id=current_user.id_usuario,
            destinatario_id=destinatario_id or current_user.id_usuario,  # Si no hay destinatario, usar admin
            asunto=asunto or '(Sin asunto)',
            mensaje=mensaje or '',
            estado='draft'
        )
        
        db.session.add(borrador)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Borrador guardado correctamente',
            'id': borrador.id_comunicacion
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error guardando borrador: {str(e)}'
        }), 500

@admin_bp.route('/api/usuarios/buscar')
@login_required
@role_required(1)
def api_buscar_usuarios():
    """API para buscar usuarios para el autocompletado."""
    try:
        query = request.args.get('q', '').strip()
        
        if len(query) < 2:
            return jsonify([])
        
        # Buscar usuarios por nombre, apellido o correo
        usuarios = Usuario.query.filter(
            or_(
                Usuario.nombre.contains(query),
                Usuario.apellido.contains(query),
                Usuario.correo.contains(query)
            ),
            Usuario.estado_cuenta == 'activa'
        ).limit(10).all()
        
        usuarios_data = []
        for usuario in usuarios:
            usuarios_data.append({
                'id': usuario.id_usuario,
                'nombre': usuario.nombre_completo,
                'email': usuario.correo,
                'correo': usuario.correo,
                'rol': usuario.rol_nombre
            })
        
        return jsonify(usuarios_data)
        
    except Exception as e:
        print(f"Error buscando usuarios: {str(e)}")
        return jsonify([]), 500

@admin_bp.route('/api/reportes-calificaciones/<int:reporte_id>/estado', methods=['PUT'])
@login_required
@role_required(1)
def api_actualizar_estado_reporte(reporte_id):
    """API para actualizar el estado de un reporte."""
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        if nuevo_estado not in ['pendiente', 'revisado', 'archivado']:
            return jsonify({
                'success': False,
                'message': 'Estado inválido'
            }), 400
        
        reporte = ReporteCalificaciones.query.get(reporte_id)
        if not reporte:
            return jsonify({
                'success': False,
                'message': 'Reporte no encontrado'
            }), 404
        
        reporte.estado = nuevo_estado
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Estado actualizado correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error actualizando estado: {str(e)}'
        }), 500

@admin_bp.route('/api/reportes-calificaciones/<int:reporte_id>', methods=['DELETE'])
@login_required
@role_required(1)
def api_eliminar_reporte(reporte_id):
    """API para eliminar un reporte."""
    try:
        reporte = ReporteCalificaciones.query.get(reporte_id)
        if not reporte:
            return jsonify({
                'success': False,
                'message': 'Reporte no encontrado'
            }), 404
        
        db.session.delete(reporte)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Reporte eliminado correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error eliminando reporte: {str(e)}'
        }), 500

# ==================== GESTIÓN DE CÓDIGOS DE VERIFICACIÓN ====================

@admin_bp.route('/verification-codes')
@login_required
@role_required(1)
def verification_codes():
    """Página para gestionar códigos de verificación pendientes"""
    # Obtener usuarios con email no verificado
    usuarios_pendientes = Usuario.query.filter(
        Usuario.email_verified == False,
        Usuario.verification_code.isnot(None)
    ).all()
    
    return render_template('superadmin/verification_codes.html', 
                        usuarios_pendientes=usuarios_pendientes)

@admin_bp.route('/reenviar-verificacion', methods=['POST'])
@login_required
@role_required(1)
def reenviar_verificacion():
    """Reenvía el correo de verificación a un usuario"""
    try:
        user_id = request.form.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'ID de usuario requerido'
            }), 400
        
        usuario = Usuario.query.get(user_id)
        if not usuario:
            return jsonify({
                'success': False,
                'message': 'Usuario no encontrado'
            }), 404
        
        if usuario.email_verified:
            return jsonify({
                'success': False,
                'message': 'El usuario ya está verificado'
            }), 400
        
        # Reenviar correo con reintentos
        email_result = send_welcome_email_with_retry(usuario, usuario.verification_code)
        
        if email_result == True:
            return jsonify({
                'success': True,
                'message': 'Correo de verificación reenviado exitosamente'
            })
        elif email_result == "limit_exceeded":
            return jsonify({
                'success': False,
                'message': f'Límite diario de correos excedido. Código de verificación: {usuario.verification_code}'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Error al reenviar correo. Código de verificación: {usuario.verification_code}'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@admin_bp.route('/verificar-manual', methods=['POST'])
@login_required
@role_required(1)
def verificar_manual():
    """Marca un usuario como verificado manualmente"""
    try:
        user_id = request.form.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'ID de usuario requerido'
            }), 400
        
        usuario = Usuario.query.get(user_id)
        if not usuario:
            return jsonify({
                'success': False,
                'message': 'Usuario no encontrado'
            }), 404
        
        if usuario.email_verified:
            return jsonify({
                'success': False,
                'message': 'El usuario ya está verificado'
            }), 400
        
        # Marcar como verificado
        usuario.email_verified = True
        usuario.verification_code = None
        usuario.verification_code_expires = None
        usuario.verification_attempts = 0
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Usuario verificado exitosamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@admin_bp.route('/verification-info/<int:user_id>')
@login_required
@role_required(1)
def get_verification_info_route(user_id):
    """Obtiene información de verificación para un usuario"""
    try:
        usuario = Usuario.query.get(user_id)
        if not usuario:
            return jsonify({
                'success': False,
                'message': 'Usuario no encontrado'
            }), 404
        
        if usuario.email_verified:
            return jsonify({
                'success': False,
                'message': 'El usuario ya está verificado'
            }), 400
        
        info = get_verification_info(usuario)
        
        return jsonify({
            'success': True,
            'data': info
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


# ==================== NOTIFICACIONES ====================

@admin_bp.route('/notificaciones')
@login_required
@role_required(1)
def notificaciones():
    """Página principal de notificaciones para administradores"""
    return render_template('superadmin/notificaciones/notificaciones.html')


@admin_bp.route('/api/notificaciones')
@login_required
@role_required(1)
def api_notificaciones():
    """API para obtener notificaciones paginadas"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        filtro = request.args.get('filtro', 'todas', type=str)
        
        from services.notification_service import get_notifications_paginated
        
        pagination = get_notifications_paginated(
            current_user.id_usuario, page, per_page, filtro
        )
        
        return jsonify({
            'success': True,
            'data': {
                'notificaciones': [notif.to_dict() for notif in pagination.items],
                'total': pagination.total,
                'pages': pagination.pages,
                'current_page': pagination.page,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@admin_bp.route('/api/notificaciones/marcar-leidas', methods=['POST'])
@login_required
@role_required(1)
def api_marcar_leidas():
    """API para marcar notificaciones como leídas"""
    try:
        data = request.get_json()
        notificacion_ids = data.get('notificacion_ids', [])
        
        from services.notification_service import mark_read
        
        if notificacion_ids:
            updated = mark_read(current_user.id_usuario, notificacion_ids)
        else:
            from services.notification_service import mark_all_read
            updated = mark_all_read(current_user.id_usuario)
        
        return jsonify({
            'success': True,
            'message': f'Se marcaron {updated} notificaciones como leídas'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@admin_bp.route('/api/notificaciones/eliminar', methods=['POST'])
@login_required
@role_required(1)
def api_eliminar_notificaciones():
    """API para eliminar notificaciones"""
    try:
        data = request.get_json()
        notificacion_ids = data.get('notificacion_ids', [])
        eliminar_todas = data.get('eliminar_todas', False)
        
        from services.notification_service import delete_notifications, delete_all_user_notifications
        
        if eliminar_todas:
            deleted = delete_all_user_notifications(current_user.id_usuario)
            message = f'Se eliminaron {deleted} notificaciones'
        else:
            deleted = delete_notifications(current_user.id_usuario, notificacion_ids)
            message = f'Se eliminaron {deleted} notificaciones'
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

