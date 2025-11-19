from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from datetime import datetime, date
from sqlalchemy import text
import os
import json
from werkzeug.utils import secure_filename
from controllers.decorators import role_required
from extensions import db
from services.notification_service import (
    notificar_nuevo_evento, 
    notificar_evento_actualizado, 
    notificar_evento_eliminado
)
from services.email_service import send_welcome_email, generate_verification_code, send_verification_success_email, send_welcome_email_with_retry, get_verification_info
from controllers.forms import RegistrationForm, UserEditForm, SalonForm, CursoForm, SedeForm, EquipoForm
from controllers.models import (
    Usuario, Rol, Clase, Curso, Asignatura, Sede, Salon, 
    HorarioGeneral, HorarioCompartido, Matricula, BloqueHorario, 
    HorarioCurso, AsignacionEquipo, Equipo, Incidente, Mantenimiento, Comunicacion, 
    Evento, Candidato, HorarioVotacion, ReporteCalificaciones, Notificacion,
    CicloAcademico, PeriodoAcademico,EstadoPublicacion, Voto
)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# ========== FUNCIÓN AUXILIAR==========
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


@admin_bp.route('/dashboard')
@login_required 
@role_required(1) 
def admin_panel():
    counts = get_sidebar_counts() 
    return render_template('superadmin/gestion_usuarios/dashboard.html',
                            # VARIABLES PARA EL TEMPLATE BASE
                            unread_messages=counts['unread_messages'],
                            unread_notifications=counts['unread_notifications'],
                            upcoming_events=counts['upcoming_events'])

@admin_bp.route('/inicio')
@login_required
@role_required(1)
def inicio():
    counts = get_sidebar_counts()
    return render_template('superadmin/inicio/inicio.html',
                          unread_messages=counts['unread_messages'],
                          unread_notifications=counts['unread_notifications'],
                          upcoming_events=counts['upcoming_events'])

@admin_bp.route('/buscar-usuario')
@login_required
@role_required(1)
def buscar_usuario():
    identificacion = request.args.get('identificacion', '')
    
    usuarios_encontrados = []
    
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

@admin_bp.route('/profesores')
@login_required
@role_required(1)
def profesores():
    filter_id = request.args.get('filter_id', '')
    counts = get_sidebar_counts()
    return render_template('superadmin/gestion_usuarios/profesores.html', 
                         filter_id=filter_id,
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])

@admin_bp.route('/api/profesores')
@login_required
@role_required(1)
def api_profesores():
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
    filter_id = request.args.get('filter_id', '')
    rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()
    
    if filter_id:
        estudiantes = Usuario.query.filter_by(
            id_rol_fk=rol_estudiante.id_rol, 
            no_identidad=filter_id
        ).all() if rol_estudiante else []
    else:
        estudiantes = Usuario.query.filter_by(
            id_rol_fk=rol_estudiante.id_rol
        ).all() if rol_estudiante else []
    
    estudiante_ids = [est.id_usuario for est in estudiantes]
    
    if estudiante_ids:
        matriculas = Matricula.query.filter(
            Matricula.estudianteId.in_(estudiante_ids)
        ).all()
        
        curso_ids = [mat.cursoId for mat in matriculas]
        cursos_dict = {curso.id_curso: curso for curso in Curso.query.filter(Curso.id_curso.in_(curso_ids)).all()}
        
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
        
        matriculas_por_estudiante = {}
        for matricula in matriculas:
            if matricula.estudianteId not in matriculas_por_estudiante:
                matriculas_por_estudiante[matricula.estudianteId] = []
            matriculas_por_estudiante[matricula.estudianteId].append(matricula)
        
        for estudiante in estudiantes:
            estudiante._matriculas = matriculas_por_estudiante.get(estudiante.id_usuario, [])
            estudiante._cursos_dict = cursos_dict
            estudiante._padres = padres_dict.get(estudiante.id_usuario, [])
    else:
        for estudiante in estudiantes:
            estudiante._matriculas = []
            estudiante._cursos_dict = {}
            estudiante._padres = []
    
    form = RegistrationForm()
    
    form.rol.choices = [(str(rol_estudiante.id_rol), rol_estudiante.nombre)] if rol_estudiante else []
    form.rol.data = str(rol_estudiante.id_rol) if rol_estudiante else None
    
    cursos = Curso.query.all()
    form.curso_id.choices = [(str(curso.id_curso), curso.nombreCurso) for curso in cursos]
    
    counts = get_sidebar_counts()
    
    return render_template(
        'superadmin/gestion_usuarios/estudiantes.html', 
        estudiantes=estudiantes,
        form=form,  
        cursos=cursos,
        rol_predefinido='Estudiante',
        rol_predefinido_id=str(rol_estudiante.id_rol) if rol_estudiante else None,
        now=date.today,
        unread_messages=counts['unread_messages'],
        unread_notifications=counts['unread_notifications'],
        upcoming_events=counts['upcoming_events']
    )

@admin_bp.route('/api/estudiantes')
@login_required
@role_required(1)
def api_estudiantes():
    try:
        filter_id = request.args.get('filter_id', '')
        rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()
        
        if filter_id:
            estudiantes = Usuario.query.filter_by(id_rol_fk=rol_estudiante.id_rol, no_identidad=filter_id).all() if rol_estudiante else []
        else:
            estudiantes = Usuario.query.filter_by(id_rol_fk=rol_estudiante.id_rol).all() if rol_estudiante else []
            
        lista_estudiantes = []
        for estudiante in estudiantes:
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

@admin_bp.route('/api/estudiantes/<int:id>', methods=['GET'])
@login_required
@role_required(1)
def api_detalles_estudiante(id):
    try:
        
        rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()
        if not rol_estudiante:
            return jsonify({"success": False, "message": "Rol 'Estudiante' no encontrado"}), 500

        estudiante = Usuario.query.filter_by(
            id_usuario=id, 
            id_rol_fk=rol_estudiante.id_rol
        ).first()
        if not estudiante:
            return jsonify({"success": False, "message": "Estudiante no encontrado"}), 404

        matricula = Matricula.query.filter_by(estudianteId=estudiante.id_usuario)\
                                   .order_by(Matricula.año.desc())\
                                   .first()
        curso_nombre = "Sin asignar"
        anio_matricula = "N/A"
        if matricula:
            curso = Curso.query.get(matricula.cursoId)
            curso_nombre = curso.nombreCurso if curso else "Sin curso"
            anio_matricula = str(matricula.año)
            
        padres = db.session.execute(
            text("""
                SELECT u.nombre, u.apellido 
                FROM estudiante_padre ep 
                JOIN usuarios u ON ep.padre_id = u.id_usuario 
                WHERE ep.estudiante_id = :est_id
            """),
            {"est_id": estudiante.id_usuario}
        ).fetchall()

        padre_acudiente = ", ".join([f"{p.nombre} {p.apellido}" for p in padres]) if padres else "Sin asignar"

        return jsonify({
            "success": True,
            "estudiante": {
                "id_usuario": estudiante.id_usuario,
                "no_identidad": estudiante.no_identidad,
                "nombre": estudiante.nombre,
                "apellido": estudiante.apellido,
                "correo": estudiante.correo,
                "curso": curso_nombre,
                "anio_matricula": anio_matricula,
                "padre_acudiente": padre_acudiente,
                "estado_cuenta": estudiante.estado_cuenta
            }
        })

    except Exception as e:
        print(f"[ERROR API ESTUDIANTE] ID {id}: {str(e)}")
        return jsonify({"success": False, "message": "Error interno del servidor"}), 500

@admin_bp.route('/estudiantes/crear', methods=['GET', 'POST'])
@login_required
@role_required(1)
def crear_estudiante():
    form = RegistrationForm()
    
    roles = Rol.query.all()
    form.rol.choices = [(str(r.id_rol), r.nombre) for r in roles] if roles else []
    
    rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()
    if not rol_estudiante:
        flash('Error: Rol de Estudiante no encontrado', 'error')
        return redirect(url_for('admin.estudiantes'))
    
    form.rol.data = str(rol_estudiante.id_rol)
    
    cursos = Curso.query.all()
    form.curso_id.choices = [(str(curso.id_curso), curso.nombreCurso) for curso in cursos]
    
    if form.validate_on_submit():
        try:
            from datetime import datetime, timedelta
            verification_code = generate_verification_code()
            
            print(f"DEBUG: Creando estudiante - Contraseña del formulario: {form.password.data}")
            
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
                temp_password=form.password.data  
            )
            new_user.set_password(form.password.data) 
            
            db.session.add(new_user)
            db.session.flush()  
            
            print(f"DEBUG: Estudiante creado con ID: {new_user.id_usuario}")
            print(f"DEBUG: Contraseña temporal guardada: {new_user.temp_password}")
            
            if form.curso_id.data and form.anio_matricula.data:
                nueva_matricula = Matricula(
                    estudianteId=new_user.id_usuario,
                    cursoId=int(form.curso_id.data),
                    año=int(form.anio_matricula.data)
                )
                db.session.add(nueva_matricula)
            
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

@admin_bp.route('/estudiantes/<int:id>/eliminar', methods=['DELETE'])
@login_required
@role_required(1)
def eliminar_estudiante(id):
    try:
        estudiante = Usuario.query.get_or_404(id)
        
        rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()
        if estudiante.id_rol_fk != rol_estudiante.id_rol:
            return jsonify({'success': False, 'error': 'El usuario no es un estudiante'}), 400
        
        Matricula.query.filter_by(estudianteId=id).delete()
        
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
    return render_template('superadmin/gestion_inventario/mantenimiento.html')

@admin_bp.route('/api/mantenimientos', methods=['GET'])
@login_required
@role_required(1)
def api_listar_mantenimientos():

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
            Salon.nombre.label('salon_nombre'), 
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
                'salon_nombre': mant.salon_nombre or "N/A",
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
        db.session.flush()
            
        try:
            from services.notification_service import notificar_nuevo_mantenimiento
            notificaciones_enviadas = notificar_nuevo_mantenimiento(
                mantenimiento=nuevo_mantenimiento,
                admin_id=current_user.id_usuario
            )
            print(f" Notificaciones de mantenimiento enviadas: {notificaciones_enviadas}")
        except Exception as e:
            print(f" Error enviando notificaciones de mantenimiento: {e}")
            notificaciones_enviadas = 0
        
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Mantenimiento programado exitosamente para el equipo "{equipo.nombre}"',
            'notificaciones_enviadas': notificaciones_enviadas,
            'mantenimiento': {
                'id': nuevo_mantenimiento.id_mantenimiento,
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
        print(f" Error al programar mantenimiento: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': f'Error interno del servidor: {str(e)}'
        }), 500
        
@admin_bp.route('/api/equipos/con-mantenimientos', methods=['GET'])
@login_required
@role_required(1)
def api_equipos_con_mantenimientos():

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

@admin_bp.route('/api/horario_curso/restablecer/<int:curso_id>', methods=['POST'])
@login_required
@role_required(1)
def api_restablecer_horario_curso(curso_id):
    try:
        curso = Curso.query.get(curso_id)
        if not curso:
            return jsonify({'success': False, 'error': 'Curso no encontrado'}), 404

        eliminados_hc = HorarioCurso.query.filter_by(curso_id=curso_id).delete(synchronize_session=False)
        eliminados_comp = HorarioCompartido.query.filter_by(curso_id=curso_id).delete(synchronize_session=False)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Horario del curso restablecido correctamente',
            'eliminados': {
                'horario_curso': eliminados_hc,
                'horario_compartido': eliminados_comp
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Error al restablecer: {str(e)}'}), 500

@admin_bp.route('/api/mantenimientos/<int:mantenimiento_id>', methods=['GET'])
@login_required
@role_required(1)
def api_detalle_mantenimiento(mantenimiento_id):

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
 
    try:
        data = request.get_json()
        mantenimiento = Mantenimiento.query.get_or_404(mantenimiento_id)
        equipo = Equipo.query.get(mantenimiento.equipo_id)

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
            mantenimiento.fecha_realizada = date.today()

        if equipo:
            if nuevo_estado == 'completado':
                incidentes_activos = Incidente.query.filter(
                    Incidente.equipo_id == equipo.id_equipo,
                    Incidente.estado.in_(['reportado', 'en_proceso'])
                ).all()
                
                for incidente in incidentes_activos:
                    incidente.estado = 'resuelto'
                    incidente.fecha_solucion = datetime.utcnow()
                    incidente.solucion_propuesta = f"Resuelto mediante mantenimiento #{mantenimiento_id}"
                

                otros_mantenimientos = Mantenimiento.query.filter(
                    Mantenimiento.equipo_id == equipo.id_equipo,
                    Mantenimiento.id_mantenimiento != mantenimiento_id,
                    Mantenimiento.estado.in_(['pendiente', 'en_progreso'])
                ).first()
                
                if not otros_mantenimientos:
                    incidentes_restantes = Incidente.query.filter(
                        Incidente.equipo_id == equipo.id_equipo,
                        Incidente.estado.in_(['reportado', 'en_proceso'])
                    ).first()
                    
                    if not incidentes_restantes:
                        equipo.estado = 'Disponible'
                    else:
                        equipo.estado = 'Incidente'
                        
            elif nuevo_estado == 'cancelado':
                incidentes_activos = Incidente.query.filter(
                    Incidente.equipo_id == equipo.id_equipo,
                    Incidente.estado.in_(['reportado', 'en_proceso'])
                ).first()
                
                otros_mantenimientos = Mantenimiento.query.filter(
                    Mantenimiento.equipo_id == equipo.id_equipo,
                    Mantenimiento.id_mantenimiento != mantenimiento_id,
                    Mantenimiento.estado.in_(['pendiente', 'en_progreso'])
                ).first()
                
                if incidentes_activos:
                    equipo.estado = 'Incidente'
                elif otros_mantenimientos:
                    equipo.estado = 'Mantenimiento'
                else:
                    equipo.estado = 'Disponible'
                    
            elif nuevo_estado == 'en_progreso':
                equipo.estado = 'Mantenimiento'

        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Mantenimiento actualizado exitosamente.',
            'equipo_actualizado': {
                'id_equipo': equipo.id_equipo,
                'estado': equipo.estado,
                'tiene_incidentes': False if nuevo_estado == 'completado' else True,
                'tiene_mantenimientos': False if nuevo_estado in ['completado', 'cancelado'] else True
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error al actualizar mantenimiento: {e}")
        return jsonify({'success': False, 'error': f'Error interno del servidor: {str(e)}'}), 500

@admin_bp.route('/api/mantenimientos/<int:mantenimiento_id>', methods=['DELETE'])
@login_required
@role_required(1)
def api_eliminar_mantenimiento(mantenimiento_id):

    try:
        mantenimiento = Mantenimiento.query.get_or_404(mantenimiento_id)
        equipo = Equipo.query.get(mantenimiento.equipo_id)

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
    return redirect(url_for('admin.editar_usuario', user_id=id))

@admin_bp.route('/estudiantes/<int:id>/detalles')
@login_required
@role_required(1)
def detalles_estudiante(id):
    estudiante = Usuario.query.get_or_404(id)
    
    rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()
    if estudiante.id_rol_fk != rol_estudiante.id_rol:
        flash('El usuario no es un estudiante', 'error')
        return redirect(url_for('admin.estudiantes'))
    
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
    filter_id = request.args.get('filter_id', '')
    counts = get_sidebar_counts()
    return render_template('superadmin/gestion_usuarios/padres.html', 
                         filter_id=filter_id,
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])

@admin_bp.route('/api/padres')
@login_required
@role_required(1)
def api_padres():
    try:
        filter_id = request.args.get('filter_id', '')
        rol_padre = Rol.query.filter_by(nombre='Padre').first()
        
        if filter_id:
            padres = Usuario.query.filter_by(id_rol_fk=rol_padre.id_rol, no_identidad=filter_id).all() if rol_padre else []
        else:
            padres = Usuario.query.filter_by(id_rol_fk=rol_padre.id_rol).all() if rol_padre else []
        
        padre_ids = [padre.id_usuario for padre in padres]
        
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
    filter_id = request.args.get('filter_id', '')
    counts = get_sidebar_counts()
    return render_template('superadmin/gestion_usuarios/administrativos.html', 
                         filter_id=filter_id,
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])

@admin_bp.route('/api/superadmins')
@login_required
@role_required(1)
def api_superadmins():
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

@admin_bp.route('/crear_usuario', methods=['GET', 'POST'])
@login_required
@role_required(1)
def crear_usuario():
    form = RegistrationForm()
    
    roles = Rol.query.all()
    form.rol.choices = [(str(r.id_rol), r.nombre) for r in roles] if roles else []
    
    cursos = Curso.query.all()
    form.curso_id.choices = [(str(curso.id_curso), curso.nombreCurso) for curso in cursos]
    
    rol_predefinido = request.args.get('rol')
    
    rol_predefinido_id = None
    if rol_predefinido and request.method == 'GET':
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

    if form.validate_on_submit():
        selected_role_id = int(form.rol.data)
        
        rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()
        rol_profesor = Rol.query.filter_by(nombre='Profesor').first()
        rol_padre = Rol.query.filter_by(nombre='Padre').first()
        rol_admin = Rol.query.filter_by(nombre='Administrador Institucional').first()

        is_student = (rol_estudiante and selected_role_id == rol_estudiante.id_rol)
        is_professor = (rol_profesor and selected_role_id == rol_profesor.id_rol)

        from datetime import datetime, timedelta
        verification_code = generate_verification_code()
        print(f"DEBUG: Creando usuario - Contraseña del formulario:{form.password.data}")
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
            db.session.flush()  
            
            if is_student and form.curso_id.data and form.anio_matricula.data:
                nueva_matricula = Matricula(
                    estudianteId=new_user.id_usuario,
                    cursoId=int(form.curso_id.data),
                    año=int(form.anio_matricula.data)
                )
                db.session.add(nueva_matricula)
            
            db.session.commit()
            print(f"DEBUG: Usuario creado - Contraseña temporal: {new_user.temp_password}")
            email_result = send_welcome_email(new_user, new_user.verification_code)
            
            if email_result == True:
                flash(f'Usuario "{new_user.nombre_completo}" creado exitosamente! Se ha enviado un correo de verificación.', 'success')
            elif email_result == "limit_exceeded":
                flash(f'Usuario "{new_user.nombre_completo}" creado exitosamente! ⚠️ Límite diario de correos excedido. Código de verificación: {new_user.verification_code}', 'warning')
            else:
                flash(f'Usuario "{new_user.nombre_completo}" creado pero hubo un error enviando el correo de verificación. Código de verificación: {new_user.verification_code}', 'warning')
            

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
    try:
        no_identidad = request.args.get('no_identidad', '')
        
        if not no_identidad:
            return jsonify({'exists': False})
        
        usuario = Usuario.query.filter_by(no_identidad=no_identidad).first()
        
        return jsonify({'exists': usuario is not None})
        
    except Exception as e:
        print(f"Error verificando identidad: {e}")
        return jsonify({'exists': False})
    
@admin_bp.route('/api/verificar-correo')
@login_required
@role_required(1)
def api_verificar_correo():
    try:
        email = request.args.get('email', '')
        
        if not email:
            return jsonify({'exists': False})
        
        usuario = Usuario.query.filter_by(correo=email).first()
        
        return jsonify({'exists': usuario is not None})
        
    except Exception as e:
        print(f"Error verificando correo: {e}")
        return jsonify({'exists': False})

@admin_bp.route('/editar_usuario/<int:user_id>', methods=['GET', 'POST'])
@login_required
@role_required(1)
def editar_usuario(user_id):
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
    user = Usuario.query.get_or_404(user_id)
    if current_user.id_usuario == user.id_usuario or user.has_role('administrador'):
        flash('No puedes eliminar tu propia cuenta o la de otro administrador.', 'danger')
        return redirect(url_for('admin.profesores'))
    
    db.session.delete(user)
    db.session.commit()
    flash(f'Usuario "{user.nombre_completo}" eliminado exitosamente.', 'success')
    return redirect(url_for('admin.profesores'))


@admin_bp.route('/api/buscar-padres')
@login_required
@role_required(1)
def api_buscar_padres():
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
    try:
        data = request.get_json()
        
        required_fields = ['no_identidad', 'tipo_doc', 'nombre', 'apellido', 'correo', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'El campo {field} es requerido'}), 400
        
        usuario_existente = Usuario.query.filter_by(no_identidad=data['no_identidad']).first()
        if usuario_existente:
            return jsonify({'success': False, 'error': 'Ya existe un usuario con ese número de identidad'}), 400
        
        correo_existente = Usuario.query.filter_by(correo=data['correo']).first()
        if correo_existente:
            return jsonify({'success': False, 'error': 'Ya existe un usuario con ese correo electrónico'}), 400
        
        rol_padre = Rol.query.filter_by(nombre='Padre').first()
        if not rol_padre:
            return jsonify({'success': False, 'error': 'Rol de Padre no encontrado'}), 500
        
        from datetime import datetime, timedelta
        verification_code = generate_verification_code()
        
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
            temp_password=data['password'] 
        )
        nuevo_padre.set_password(data['password'])
        
        db.session.add(nuevo_padre)
        db.session.commit()
        
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



@admin_bp.route('/gestion-academica')
@login_required
@role_required(1)
def gestion_academica():
    counts = get_sidebar_counts()
    return render_template('superadmin/gestion_academica/dashboard.html',
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])

@admin_bp.route('/gestion_sedes')
@login_required
@role_required(1)
def gestion_sedes():
    form = SedeForm()
    counts = get_sidebar_counts()
    return render_template('superadmin/gestion_academica/sedes.html', 
                         form=form,
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])


@admin_bp.route('/api/sedes', methods=['GET', 'POST', 'DELETE'])
@login_required
@role_required(1)
def api_sedes():
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

@admin_bp.route('/gestion_cursos')
@login_required
@role_required(1)
def gestion_cursos():
    form = CursoForm()
    counts = get_sidebar_counts()
    return render_template('superadmin/gestion_academica/cursos.html', 
                         form=form,
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])

@admin_bp.route('/periodos')
@login_required
@role_required(1)
def gestion_periodos():
    counts = get_sidebar_counts()
    return render_template('superadmin/gestion_academica/periodos.html',
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])


@admin_bp.route('/api/cursos', methods=['GET', 'POST', 'DELETE'])
@login_required
@role_required(1)
def api_cursos():
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

@admin_bp.route('/gestion-asignaturas')
@login_required
@role_required(1)
def gestion_asignaturas():
    return render_template('superadmin/gestion_academica/gestion_asignaturas.html')

@admin_bp.route('/api/asignaturas')
@login_required
@role_required(1)
def api_asignaturas():
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
    try:
        data = request.get_json()
        
        if not data.get('nombre'):
            return jsonify({'success': False, 'error': 'El nombre de la asignatura es requerido'}), 400
        
        existe = Asignatura.query.filter_by(nombre=data['nombre']).first()
        if existe:
            return jsonify({'success': False, 'error': 'Ya existe una asignatura con ese nombre'}), 400
        
        nueva_asignatura = Asignatura(
            nombre=data['nombre'],
            descripcion=data.get('descripcion', ''),
            estado=data.get('estado', 'activa')
        )
        
        db.session.add(nueva_asignatura)
        db.session.flush() 
        
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
    try:
        data = request.get_json()
        
        asignatura = Asignatura.query.get_or_404(asignatura_id)
        
        if not data.get('nombre'):
            return jsonify({'success': False, 'error': 'El nombre de la asignatura es requerido'}), 400
        
        existe = Asignatura.query.filter(
            Asignatura.nombre == data['nombre'],
            Asignatura.id_asignatura != asignatura_id
        ).first()
        if existe:
            return jsonify({'success': False, 'error': 'Ya existe otra asignatura con ese nombre'}), 400
        
        asignatura.nombre = data['nombre']
        asignatura.descripcion = data.get('descripcion', '')
        asignatura.estado = data.get('estado', 'activa')
        
        profesores_ids = data.get('profesores', [])
        
        asignatura.profesores.clear()
        
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

@admin_bp.route('/api/horarios/<int:horario_id>/reassign-classes', methods=['POST'])
@login_required
@role_required(1)
def api_reasignar_clases_horario(horario_id):
    try:
        data = request.get_json() or {}
        target_id = data.get('target_horario_id')
        if not target_id:
            return jsonify({'success': False, 'error': 'target_horario_id requerido'}), 400
        if int(target_id) == int(horario_id):
            return jsonify({'success': False, 'error': 'El horario destino debe ser diferente'}), 400

        origen = HorarioGeneral.query.get_or_404(horario_id)
        destino = HorarioGeneral.query.get_or_404(target_id)

        actualizadas = Clase.query.filter_by(horarioId=horario_id).update({'horarioId': target_id})
        db.session.commit()

        return jsonify({'success': True, 'message': f'Clases reasignadas a "{destino.nombre}"', 'clases_actualizadas': actualizadas})
    except Exception as e:
        db.session.rollback()
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




@admin_bp.route('/gestion-horarios')
@login_required
@role_required(1)
def gestion_horarios():
    counts = get_sidebar_counts()
    return render_template('superadmin/Horarios/gestion_horarios.html',
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])

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

@admin_bp.route('/api/horarios/<int:horario_id>', methods=['PUT'])
@login_required
@role_required(1)
def api_actualizar_horario(horario_id):
    try:
        data = request.get_json()

        horario = HorarioGeneral.query.get_or_404(horario_id)

        nombre = data.get('nombre')
        if not nombre:
            return jsonify({'success': False, 'error': 'El nombre del horario es requerido'}), 400

        dias = data.get('dias', [])
        if not dias:
            return jsonify({'success': False, 'error': 'Seleccione al menos un día'}), 400

        bloques = data.get('bloques', [])
        if not bloques:
            return jsonify({'success': False, 'error': 'Agregue al menos un bloque horario'}), 400

        horario.nombre = nombre
        horario.periodo = data.get('periodo', horario.periodo)
        try:
            horario.horaInicio = datetime.strptime(data.get('horaInicio', '07:00'), '%H:%M').time()
            horario.horaFin = datetime.strptime(data.get('horaFin', '17:00'), '%H:%M').time()
        except ValueError:
            return jsonify({'success': False, 'error': 'Formato de hora inválido. Use HH:MM'}), 400
        horario.diasSemana = json.dumps(dias)
        horario.duracion_clase = data.get('duracion_clase', horario.duracion_clase or 45)
        horario.duracion_descanso = data.get('duracion_descanso', horario.duracion_descanso or 15)

        BloqueHorario.query.filter_by(horario_general_id=horario.id_horario).delete(synchronize_session=False)

        for i, bloque_data in enumerate(bloques):
            if not all(key in bloque_data for key in ['dia_semana', 'horaInicio', 'horaFin', 'tipo']):
                continue
            try:
                nuevo_bloque = BloqueHorario(
                    horario_general_id=horario.id_horario,
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
            'message': 'Horario actualizado correctamente',
            'updated': True,
            'horario': {
                'id_horario': horario.id_horario,
                'nombre': horario.nombre,
                'periodo': horario.periodo
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error actualizando horario: {str(e)}")
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

@admin_bp.route('/api/horario_curso/validar-conflicto', methods=['POST'])
@login_required
@role_required(1)
def api_validar_conflicto_slot():
    try:
        data = request.get_json() or {}
        print(f"🔍 DATOS RECIBIDOS EN VALIDACIÓN: {data}")
        
        profesor_id = data.get('profesor_id')
        asignatura_id_excluir = data.get('asignatura_id_excluir')
        dia = data.get('dia')
        hora_inicio = data.get('hora_inicio')
        curso_id = data.get('curso_id')

        print(f"🔍 VALIDANDO CONFLICTO - Profesor: {profesor_id}, Día: {dia}, Hora: {hora_inicio}")

        if not (profesor_id and dia and hora_inicio):
            return jsonify({
                'success': True,  
                'conflicto': False,
                'mensaje': 'Datos incompletos para validación'
            }), 200

        try:
            profesor_id = int(profesor_id)
            if asignatura_id_excluir:
                asignatura_id_excluir = int(asignatura_id_excluir)
            if curso_id:
                curso_id = int(curso_id)
        except (ValueError, TypeError):
            return jsonify({
                'success': True,
                'conflicto': False,
                'mensaje': 'IDs inválidos'
            }), 200

        from datetime import datetime, timedelta
        try:
            hi_dt = datetime.strptime(hora_inicio, '%H:%M')
            hf_dt = hi_dt + timedelta(minutes=45)
            hora_fin = hf_dt.strftime('%H:%M')
        except Exception:
            hora_fin = '08:00'

        print(f"🔍 Validando: profesor={profesor_id}, dia={dia}, hora={hora_inicio}-{hora_fin}")

        validacion = validar_conflicto_horario_profesor(
            profesor_id=profesor_id,
            dia_semana=dia,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            curso_id_excluir=curso_id, 
            asignatura_id_excluir=asignatura_id_excluir,  
            dia_semana_excluir=dia,
            hora_inicio_excluir=hora_inicio
        )

        print(f"📋 RESULTADO VALIDACIÓN: {validacion}")

        return jsonify({
            'success': True,
            'conflicto': bool(validacion.get('tiene_conflicto')),
            'mensaje': validacion.get('conflicto_info', '')
        })
    except Exception as e:
        print(f"❌ ERROR en validación: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': True,  
            'conflicto': False,
            'mensaje': f'Error en validación: {str(e)}'
        }), 200

@admin_bp.route('/api/periodos/selector', methods=['GET'])
@login_required
@role_required(1)
def api_listar_periodos():
    try:
        from services.periodo_service import obtener_ciclo_activo, obtener_periodos_ciclo
        ciclo = obtener_ciclo_activo()
        periodos = []
        if ciclo:
            periodos = obtener_periodos_ciclo(ciclo.id_ciclo)
        data = [{
            'id_periodo': p.id_periodo,
            'nombre': p.nombre,
            'numero': p.numero_periodo,
            'fecha_inicio': p.fecha_inicio.isoformat() if p.fecha_inicio else None,
            'fecha_fin': p.fecha_fin.isoformat() if p.fecha_fin else None,
            'estado': p.estado
        } for p in periodos]
        return jsonify({'data': data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/horarios/<int:horario_id>', methods=['DELETE'])
@login_required
@role_required(1)
def api_eliminar_horario(horario_id):
    try:
        horario = HorarioGeneral.query.get_or_404(horario_id)
        clases_asociadas = Clase.query.filter_by(horarioId=horario_id).count()
        if clases_asociadas > 0:
            return jsonify({
                'success': False,
                'error': (
                    f'No se puede eliminar el horario porque existen {clases_asociadas} clases asociadas. '
                    'Primero reasigne o elimine esas clases desde la gestión de clases.'
                ),
                'classes_count': clases_asociadas
            }), 409

        BloqueHorario.query.filter_by(horario_general_id=horario_id).delete(synchronize_session=False)

        try:
            HorarioCurso.query.filter_by(horario_general_id=horario_id).delete(synchronize_session=False)
        except Exception:
            pass
        try:
            HorarioCompartido.query.filter_by(horario_general_id=horario_id).delete(synchronize_session=False)
        except Exception:
            pass


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

@admin_bp.route('/api/horarios/desasignar', methods=['POST'])
@login_required
@role_required(1)
def api_desasignar_horario_cursos():
    try:
        data = request.get_json() or {}
        cursos_ids = data.get('cursos_ids', [])
        if not isinstance(cursos_ids, list) or len(cursos_ids) == 0:
            return jsonify({'success': False, 'error': 'Lista de cursos_ids requerida'}), 400

        ids = [int(x) for x in cursos_ids if str(x).isdigit()]
        if not ids:
            return jsonify({'success': False, 'error': 'IDs de curso inválidos'}), 400

        actualizados = Curso.query.filter(Curso.id_curso.in_(ids)).update({Curso.horario_general_id: None}, synchronize_session=False)
        db.session.commit()

        return jsonify({'success': True, 'message': f'Se desasignó horario de {actualizados} curso(s)', 'cursos_actualizados': actualizados})
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
    counts = get_sidebar_counts()
    return render_template('superadmin/Horarios/gestion_horarios_cursos.html',
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])

def validar_conflicto_horario_profesor(profesor_id, dia_semana, hora_inicio, hora_fin, curso_id_excluir=None, asignatura_id_excluir=None, dia_semana_excluir=None, hora_inicio_excluir=None):

    try:
        from datetime import datetime
        
        print(f"🔍 Validando conflicto para profesor {profesor_id}")
        print(f"   Día: {dia_semana}, Hora: {hora_inicio}-{hora_fin}")
        print(f"   Excluir: curso={curso_id_excluir}, asignatura={asignatura_id_excluir}")

        hora_inicio_obj = datetime.strptime(hora_inicio, '%H:%M').time()
        hora_fin_obj = datetime.strptime(hora_fin, '%H:%M').time()

        asignaciones_existentes = HorarioCurso.query.filter_by(profesor_id=profesor_id).all()

        print(f"   Asignaciones existentes encontradas: {len(asignaciones_existentes)}")

        for asignacion in asignaciones_existentes:
            print(f"   Revisando asignación: ID={asignacion.id_horario_curso}")
            print(f"     Curso: {asignacion.curso_id}, Día: {asignacion.dia_semana}")
            print(f"     Hora: {asignacion.hora_inicio}-{asignacion.hora_fin}")
            print(f"     Asignatura: {asignacion.asignatura_id}")

            if (curso_id_excluir and asignacion.curso_id == curso_id_excluir and
                (dia_semana_excluir or '').lower() == (asignacion.dia_semana or '').lower() and
                (hora_inicio_excluir or '') == (asignacion.hora_inicio or '')):
                print("     ✅ Excluyendo (mismo slot en edición)")
                continue
            
            if (curso_id_excluir and asignatura_id_excluir and 
                asignacion.curso_id == curso_id_excluir and 
                asignacion.asignatura_id == asignatura_id_excluir):
                print("     ✅ Excluyendo (misma asignatura en mismo curso)")
                continue

            if (asignacion.dia_semana or '').lower() != (dia_semana or '').lower():
                print("     ✅ Día diferente, sin conflicto")
                continue

            try:
                hi_exist = asignacion.hora_inicio
                hf_exist = asignacion.hora_fin
                
                if not hi_exist or not hf_exist:
                    print("     ⚠️ Hora inválida, omitiendo")
                    continue
                    
                hi_exist_obj = datetime.strptime(hi_exist, '%H:%M').time()
                hf_exist_obj = datetime.strptime(hf_exist, '%H:%M').time()
            except Exception as e:
                print(f"     ⚠️ Error parseando hora: {e}")
                continue

            tiene_solapamiento = (hora_inicio_obj < hf_exist_obj and hora_fin_obj > hi_exist_obj)
            print(f"     Solapamiento: {tiene_solapamiento} ({hora_inicio_obj} < {hf_exist_obj} y {hora_fin_obj} > {hi_exist_obj})")

            if tiene_solapamiento:
                curso_nombre = "Curso desconocido"
                asignatura_nombre = "Asignatura desconocida"
                
                curso_conflicto = Curso.query.get(asignacion.curso_id)
                if curso_conflicto:
                    curso_nombre = curso_conflicto.nombreCurso
                
                asignatura_conflicto = Asignatura.query.get(asignacion.asignatura_id)
                if asignatura_conflicto:
                    asignatura_nombre = asignatura_conflicto.nombre
                
                mensaje_conflicto = f"Conflicto con {asignatura_nombre} en {curso_nombre} ({hi_exist}-{hf_exist})"
                print(f"     ❌ CONFLICTO: {mensaje_conflicto}")
                
                return {
                    'tiene_conflicto': True,
                    'conflicto_info': mensaje_conflicto
                }

        print("     ✅ Sin conflictos encontrados")
        return {'tiene_conflicto': False, 'conflicto_info': ''}

    except Exception as e:
        print(f"❌ ERROR en validación de conflicto: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'tiene_conflicto': False, 'conflicto_info': ''}


@admin_bp.route('/api/horario_curso/guardar', methods=['POST'])
@login_required
@role_required(1)
def api_guardar_horario_curso():
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
        profesores_asignaciones = data.get('profesores_asignaciones', {})
        
        print(f"Asignaciones recibidas: {asignaciones}")
        print(f"Salones recibidos: {salones_asignaciones}")
        print(f"Total asignaciones: {len(asignaciones)}")
        print(f"Total salones: {len(salones_asignaciones)}")
        

        if asignaciones:
            print("Primeras 5 asignaciones:")
            for i, (clave, valor) in enumerate(list(asignaciones.items())[:5]):
                print(f"   {i+1}. {clave} -> {valor}")

        curso_id = data.get('curso_id')
        if not curso_id:
            print("ERROR: No hay curso_id")
            return jsonify({'success': False, 'error': 'ID de curso requerido'}), 400


        curso = Curso.query.get(curso_id)
        if not curso:
            print(f"ERROR: Curso {curso_id} no encontrado")
            return jsonify({'success': False, 'error': 'Curso no encontrado'}), 404

        # Si no hay asignaciones en la petición, interpretar como 'restablecer' y borrar todo
        if not asignaciones or len(asignaciones) == 0:
            try:
                eliminados_hc = HorarioCurso.query.filter_by(curso_id=curso_id).delete(synchronize_session=False)
                eliminados_comp = HorarioCompartido.query.filter_by(curso_id=curso_id).delete(synchronize_session=False)
                db.session.commit()
                return jsonify({
                    'success': True,
                    'message': 'Horario del curso eliminado correctamente',
                    'resumen': {
                        'creadas': 0,
                        'actualizadas': 0,
                        'eliminadas': eliminados_hc,
                        'total': 0
                    },
                    'eliminados': {
                        'horario_curso': eliminados_hc,
                        'horario_compartido': eliminados_comp
                    }
                })
            except Exception as del_e:
                db.session.rollback()
                return jsonify({'success': False, 'error': f'Error al eliminar asignaciones: {str(del_e)}'}), 500

        asignaciones_existentes = HorarioCurso.query.filter_by(curso_id=curso_id).all()
        print(f"Asignaciones existentes en BD: {len(asignaciones_existentes)}")

        asignaciones_existentes_dict = {}
        for asignacion in asignaciones_existentes:
            clave = f"{asignacion.dia_semana}-{asignacion.hora_inicio}"
            asignaciones_existentes_dict[clave] = asignacion
            print(f"   {clave} -> Asignatura: {asignacion.asignatura_id}, Salon: {asignacion.id_salon_fk}")

        asignaciones_creadas = 0
        asignaciones_actualizadas = 0
        asignaciones_eliminadas = 0

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

                hora_fin = "08:00"
                try:
                    from datetime import datetime, timedelta
                    hora_inicio_dt = datetime.strptime(hora_inicio, '%H:%M')
                    hora_fin_dt = hora_inicio_dt + timedelta(minutes=45)
                    hora_fin = hora_fin_dt.strftime('%H:%M')
                except:
                    pass

                profesor_id = None
                try:
                    val = profesores_asignaciones.get(clave)
                    if val:
                        profesor_id = int(val)
                except Exception:
                    profesor_id = None

                if profesor_id:
                    curso_id_excluir = curso_id if clave in asignaciones_existentes_dict else None
                    asignatura_id_excluir = asignatura_id if clave in asignaciones_existentes_dict else None
                    
                    profesor_obj = Usuario.query.get(profesor_id)
                    profesor_nombre = f"Profesor ID {profesor_id}"
                    if profesor_obj:
                        profesor_nombre = f"{getattr(profesor_obj, 'nombre', '')} {getattr(profesor_obj, 'apellido', '')}".strip()
                    
                    validacion = validar_conflicto_horario_profesor(
                        profesor_id=profesor_id,
                        dia_semana=dia,
                        hora_inicio=hora_inicio,
                        hora_fin=hora_fin,
                        curso_id_excluir=curso_id_excluir,
                        asignatura_id_excluir=asignatura_id_excluir,
                        dia_semana_excluir=dia,
                        hora_inicio_excluir=hora_inicio
                    )
                    
                    if validacion['tiene_conflicto']:
                        print(f"   CONFLICTO DETECTADO para {profesor_nombre}: {validacion['conflicto_info']}")
                        
                        libres = []
                        try:
                            asignatura_obj = Asignatura.query.get(asignatura_id)
                            if asignatura_obj and asignatura_obj.profesores:
                                for prof in asignatura_obj.profesores:
                                    if prof.id_usuario == profesor_id:
                                        continue
                                    v = validar_conflicto_horario_profesor(
                                        profesor_id=prof.id_usuario,
                                        dia_semana=dia,
                                        hora_inicio=hora_inicio,
                                        hora_fin=hora_fin,
                                        curso_id_excluir=curso_id,
                                        asignatura_id_excluir=asignatura_id,
                                        dia_semana_excluir=dia,
                                        hora_inicio_excluir=hora_inicio
                                    )
                                    if not v['tiene_conflicto']:
                                        nombre_prof = f"{getattr(prof, 'nombre', '')} {getattr(prof, 'apellido', '')}".strip()
                                        if nombre_prof:
                                            libres.append(nombre_prof)
                        except Exception as e:
                            print(f"Error obteniendo profesores libres: {str(e)}")

                        mensaje_error = (
                            f"Conflicto de horario detectado para el profesor seleccionado: {validacion['conflicto_info']}\n\n"
                        )
                        if libres:
                            mensaje_error += "Profesores disponibles para esta asignatura:\n• " + "\n• ".join(libres)
                        else:
                            mensaje_error += "No hay otros profesores disponibles para esta asignatura en ese horario."

                        return jsonify({
                            'success': False,
                            'error': mensaje_error
                        }), 400

                salon_id = salones_asignaciones.get(clave)
                if salon_id:
                    salon = Salon.query.get(salon_id)
                    if not salon:
                        print(f"   Salón no encontrado: {salon_id}")
                        salon_id = None

                if clave in asignaciones_existentes_dict:
                    asignacion_existente = asignaciones_existentes_dict[clave]
                    asignacion_existente.asignatura_id = asignatura_id
                    asignacion_existente.hora_fin = hora_fin
                    asignacion_existente.id_salon_fk = salon_id
                    if profesor_id:
                        asignacion_existente.profesor_id = profesor_id
                    asignaciones_actualizadas += 1
                    print(f"   ACTUALIZADA: {clave}")
                else:
                    nueva_asignacion = HorarioCurso(
                        curso_id=curso_id,
                        asignatura_id=asignatura_id,
                        profesor_id=profesor_id,
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

        claves_request = set(asignaciones.keys())
        for clave, asignacion_existente in list(asignaciones_existentes_dict.items()):
            if clave not in claves_request or not asignaciones.get(clave):
                db.session.delete(asignacion_existente)
                asignaciones_eliminadas += 1
                print(f"   ELIMINADA: {clave}")

        horario_general_id = data.get('horario_general_id')
        try:
            actuales = HorarioCurso.query.filter_by(curso_id=curso_id).all()
            creados_hc = 0
            for hc in actuales:
                if hc.profesor_id and hc.asignatura_id:
                    existe = HorarioCompartido.query.filter_by(
                        profesor_id=hc.profesor_id,
                        curso_id=hc.curso_id,
                        asignatura_id=hc.asignatura_id
                    ).first()
                    if not existe:
                        nuevo = HorarioCompartido(
                            profesor_id=hc.profesor_id,
                            curso_id=hc.curso_id,
                            asignatura_id=hc.asignatura_id,
                            horario_general_id=horario_general_id
                        )
                        db.session.add(nuevo)
                        creados_hc += 1
            print(f"   HorarioCompartido creados: {creados_hc}")
        except Exception as e:
            print(f"Advertencia creando HorarioCompartido: {str(e)}")

        db.session.commit()
        
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
            'message': 'Horario del curso guardado correctamente',
            'resumen': {
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
    try:
        curso = Curso.query.get(curso_id)
        if not curso:
            return jsonify({'error': 'Curso no encontrado'}), 404

        asignaciones_db = HorarioCurso.query.filter_by(curso_id=curso_id).all()

        asignaciones = {}
        salones_asignaciones = {}
        profesores_asignaciones = {} 
        
        for asignacion in asignaciones_db:
            clave = f"{asignacion.dia_semana}-{asignacion.hora_inicio}"
            asignaciones[clave] = asignacion.asignatura_id
            if asignacion.id_salon_fk:
                salones_asignaciones[clave] = asignacion.id_salon_fk
            if hasattr(asignacion, 'profesor_id') and asignacion.profesor_id:  
                profesores_asignaciones[clave] = asignacion.profesor_id

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
        print(f"   Profesores: {len(profesores_asignaciones)}")  # ✅ NUEVO
        print(f"   Bloques: {len(bloques_horario)}")

        return jsonify({
            'curso_id': curso_id,
            'horario_general_id': curso.horario_general_id,
            'nombre_curso': curso.nombreCurso,
            'asignaciones': asignaciones,
            'salones_asignaciones': salones_asignaciones,
            'profesores_asignaciones': profesores_asignaciones,  # ✅ NUEVO
            'bloques_horario': bloques_horario,
            'tiene_horario_general': curso.horario_general_id is not None
        })

    except Exception as e:
        print(f"❌ Error cargando horario del curso: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/horarios/<int:horario_id>/cursos', methods=['GET'])
@login_required
@role_required(1)
def api_cursos_por_horario(horario_id):
    try:
        cursos = db.session.query(Curso, Sede.nombre).join(Sede, Curso.sedeId == Sede.id_sede, isouter=True)\
            .filter(Curso.horario_general_id == horario_id).all()

        data = [{
            'id_curso': c.id_curso,
            'nombreCurso': c.nombreCurso,
            'sede': sede_nombre,
            'sedeId': c.sedeId,
            'horario_general_id': c.horario_general_id
        } for c, sede_nombre in cursos]

        return jsonify({'data': data, 'count': len(data)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/profesores/asignatura/<int:asignatura_id>')
@login_required
@role_required(1)
def api_profesores_por_asignatura(asignatura_id):
    try:
        from routes.profesor import obtener_profesores_por_asignatura
        
        profesores = obtener_profesores_por_asignatura(asignatura_id)
        
        return jsonify({
            'success': True,
            'profesores': profesores,
            'total': len(profesores)
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo profesores por asignatura: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al obtener profesores: {str(e)}'
        }), 500

@admin_bp.route('/api/profesores/validar/<int:profesor_id>/<int:asignatura_id>')
@login_required
@role_required(1)
def api_validar_profesor_asignatura(profesor_id, asignatura_id):
    try:
        from routes.profesor import validar_profesor_asignatura
        
        es_valido = validar_profesor_asignatura(profesor_id, asignatura_id)
        
        return jsonify({
            'success': True,
            'es_valido': es_valido
        })
        
    except Exception as e:
        print(f"❌ Error validando profesor-asignatura: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al validar: {str(e)}'
        }), 500

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
            profesores_asignados = set()
            
            for clave, asignatura_id in asignaciones.items():
                if asignatura_id:
                    asignatura = Asignatura.query.get(asignatura_id)
                    if asignatura and asignatura.profesores:
                        for profesor in asignatura.profesores:
                            profesores_asignados.add(profesor)
            
            for profesor in profesores_asignados:
                for clave, asignatura_id in asignaciones.items():
                    if asignatura_id:
                        asignatura = Asignatura.query.get(asignatura_id)
                        if asignatura and profesor in asignatura.profesores:
                            partes = clave.split('-')
                            if len(partes) >= 2:
                                dia = partes[0]
                                hora_inicio = partes[1]
                                
                                try:
                                    from datetime import datetime, timedelta
                                    hora_inicio_dt = datetime.strptime(hora_inicio, '%H:%M')
                                    hora_fin_dt = hora_inicio_dt + timedelta(minutes=45)
                                    hora_fin = hora_fin_dt.strftime('%H:%M')
                                except:
                                    hora_fin = "08:00"
                                
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

            for profesor in profesores_asignados:
                for clave, asignatura_id in asignaciones.items():
                    if asignatura_id:
                        asignatura = Asignatura.query.get(asignatura_id)
                        if asignatura and profesor in asignatura.profesores:
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
            try:
                rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()
                estudiantes = db.session.query(Usuario).join(
                    Matricula, Usuario.id_usuario == Matricula.estudianteId
                ).filter(
                    Usuario.id_rol_fk == rol_estudiante.id_rol if rol_estudiante else True,
                    Matricula.cursoId == curso_id,
                    Usuario.estado_cuenta == 'activa'
                ).all()

                from services.notification_service import crear_notificacion

                total_notificados = 0
                for est in estudiantes:
                    notif = crear_notificacion(
                        usuario_id=est.id_usuario,
                        titulo='📅 Nuevo horario disponible',
                        mensaje=f'Se ha compartido el horario del curso {curso.nombreCurso}. Puedes consultarlo en Mi Horario.',
                        tipo='horario',
                        link='/estudiante/mi-horario',
                        auto_commit=False
                    )
                    if notif is not None:
                        total_notificados += 1

                db.session.commit()

                return jsonify({
                    'success': True,
                    'message': f'Horario compartido con estudiantes correctamente ({total_notificados} notificados)'
                })
            except Exception as e:
                db.session.rollback()
                return jsonify({'success': False, 'error': f'Error notificando estudiantes: {str(e)}'}), 500
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
    counts = get_sidebar_counts()
    return render_template('superadmin/gestion_inventario/gi.html',
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])


@admin_bp.route('/equipos')
@login_required
@role_required(1)
def equipos():
    counts = get_sidebar_counts()
    return render_template('superadmin/gestion_inventario/equipos.html',
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])

@admin_bp.route('/api/equipos', methods=['GET'])
@login_required
@role_required(1)
def api_equipos_todos():
    equipos = Equipo.query.all()
    return jsonify([e.to_dict() for e in equipos])

@admin_bp.route('/api/equipos')
@login_required
@role_required(1)
def api_equipos():
    try:
        equipos = Equipo.query.all()
        lista_equipos = []
        
        for equipo in equipos:
            incidentes_count = len(equipo.incidentes)
            mantenimientos_count = len(equipo.programaciones)
            
            lista_equipos.append({
                'id': equipo.id_equipo, 
                'id_equipo': equipo.id_equipo,
                'nombre': equipo.nombre,
                'estado': equipo.estado,
                'salon_nombre': equipo.salon.nombre if equipo.salon else 'Sin salón',
                'sede_nombre': equipo.salon.sede.nombre if equipo.salon and equipo.salon.sede else 'Sin sede',
                'incidentes': incidentes_count,
                'mantenimientos': mantenimientos_count
            })
        
        return jsonify(lista_equipos)
    except Exception as e:
        current_app.logger.error(f"Error en api_equipos: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500
    
@admin_bp.route('/api/estudiantes-por-curso/<int:curso_id>', methods=['GET'])
@login_required
@role_required(1)
def api_estudiantes_por_curso(curso_id):
    try:
        rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()
        if not rol_estudiante:
            return jsonify([]), 200
        
        estudiantes = db.session.query(Usuario).join(
            Matricula, Usuario.id_usuario == Matricula.estudianteId
        ).filter(
            Usuario.id_rol_fk == rol_estudiante.id_rol,
            Matricula.cursoId == curso_id,
            Usuario.estado_cuenta == 'activa'
        ).order_by(Usuario.nombre, Usuario.apellido).all()
        
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
            db.session.flush()  

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

                nuevo_equipo.estado = 'Asignado'

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

@admin_bp.route('/api/equipos/con-incidentes-activos', methods=['GET'])
@login_required
@role_required(1)
def api_equipos_con_incidentes_activos():

    try:
        equipos_db = db.session.query(
            Equipo.id_equipo,
            Equipo.nombre,
            Equipo.estado,
            Salon.nombre.label('salon_nombre'),
            Sede.id_sede,
            Sede.nombre.label('sede_nombre'),
            db.func.count(Incidente.id_incidente).label('total_incidentes')
        ).join(Incidente, Equipo.id_equipo == Incidente.equipo_id)\
         .outerjoin(Salon, Equipo.id_salon_fk == Salon.id_salon)\
         .outerjoin(Sede, Salon.id_sede_fk == Sede.id_sede)\
         .filter(Incidente.estado.in_(['reportado', 'en_proceso']))\
         .group_by(Equipo.id_equipo, Salon.nombre, Sede.id_sede, Sede.nombre)\
         .order_by(db.func.count(Incidente.id_incidente).desc())\
         .all()
        
        equipos = []
        for eq in equipos_db:
            equipos.append({
                'id_equipo': eq.id_equipo,
                'nombre': eq.nombre,
                'estado': eq.estado,
                'salon_nombre': eq.salon_nombre or "Sin Salón",
                'sede_id': eq.id_sede,
                'sede_nombre': eq.sede_nombre or "Sin Sede",
                'total_incidentes': eq.total_incidentes,
                'tiene_incidente_activo': True
            })

        return jsonify(equipos), 200

    except Exception as e:
        print(f"Error al listar equipos con incidentes activos: {e}")
        return jsonify({'error': f"Error interno del servidor: {str(e)}"}), 500


@admin_bp.route('/api/equipos/<int:id_equipo>', methods=['GET', 'DELETE'])
@login_required
@role_required(1)
def api_equipo_detalle(id_equipo):
    equipo = Equipo.query.get_or_404(id_equipo)
    
    if request.method == 'DELETE':
        try:
            db.session.delete(equipo)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Equipo eliminado exitosamente'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': f'Error al eliminar el equipo: {str(e)}'}), 500

    if request.method == 'GET':
        data = equipo.to_dict()
        data['salon_nombre'] = equipo.salon.nombre if equipo.salon else "Sin Salón"
        data['sede_nombre'] = equipo.salon.sede.nombre if equipo.salon and equipo.salon.sede else "Sin Sede"

        asignaciones_activas = equipo.get_asignaciones_activas()
        data['asignaciones'] = []
        
        for asig in asignaciones_activas:
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
    salones = Salon.query.all()
    return render_template('superadmin/gestion_inventario/salones.html', salones=salones)

# ===============================
# API Sedes, Salas y Equipos
# ===============================

@admin_bp.route('/api/estudiante/<int:estudiante_id>/equipos-en-sala/<int:salon_id>', methods=['GET'])
@login_required
@role_required(1)
def api_verificar_equipo_estudiante_en_sala(estudiante_id, salon_id):
    try:
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
        
        for asig_data in asignaciones_nuevas:
            estudiante_id = asig_data['estudiante_id']
            
            # Buscar si el estudiante tiene OTRO equipo activo en ESTA MISMA sala
            otra_asignacion_misma_sala = db.session.query(AsignacionEquipo)\
                .join(Equipo, AsignacionEquipo.equipo_id == Equipo.id_equipo)\
                .filter(
                    AsignacionEquipo.estudiante_id == estudiante_id,
                    AsignacionEquipo.estado_asignacion == 'activa',
                    Equipo.id_salon_fk == salon_id,
                    Equipo.id_equipo != equipo_id  
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
        
        for asig_data in asignaciones_nuevas:
            estudiante_id = asig_data['estudiante_id']
            
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
    salones = Salon.query.filter_by(id_sede_fk=id_sede).all()
    return jsonify([{"id_salon": s.id_salon, "nombre": s.nombre, "tipo": s.tipo} for s in salones])

@admin_bp.route('/api/salas_todas', methods=['GET'])
@login_required
@role_required(1)
def api_salas_todas():
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
    counts = get_sidebar_counts()
    return render_template('superadmin/gestion_inventario/reportes.html',
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])

@admin_bp.route('/api/incidentes/equipo/<int:equipo_id>', methods=['GET']) 
@login_required
@role_required(1)
def api_incidentes_equipo(equipo_id):
    try:
        incidentes = Incidente.query.filter_by(equipo_id=equipo_id).order_by(Incidente.fecha.desc()).all()
        return jsonify([i.to_dict() for i in incidentes])
    except Exception as e:
        current_app.logger.error(f"Error en api_incidentes_equipo: {str(e)}")
        return jsonify({'error': 'Error al cargar datos'}), 500

@admin_bp.route('/api/mantenimientos/equipo/<int:equipo_id>', methods=['GET'])
@login_required
@role_required(1)
def api_mantenimientos_equipo(equipo_id):
    try:
        mantenimientos = Mantenimiento.query.filter_by(equipo_id=equipo_id).order_by(Mantenimiento.fecha_programada.desc()).all()
        return jsonify([
            {
                'fecha_programada': m.fecha_programada.isoformat() if m.fecha_programada else None,
                'descripcion': m.descripcion or 'Sin descripción',
                'estado': m.estado,
                'tecnico': m.tecnico or 'No asignado'
            } for m in mantenimientos
        ])
    except Exception as e:
        current_app.logger.error(f"Error en api_mantenimientos_equipo: {str(e)}")
        return jsonify({'error': 'Error al cargar datos'}), 500

@admin_bp.route('/api/equipos/<int:equipo_id>/estado-detallado', methods=['GET'])
@login_required
@role_required(1)
def api_estado_detallado_equipo(equipo_id):
 
    try:
        equipo = Equipo.query.get_or_404(equipo_id)
        
        incidentes_activos = Incidente.query.filter(
            Incidente.equipo_id == equipo_id,
            Incidente.estado.in_(['reportado', 'en_proceso'])
        ).count()
        
        mantenimientos_activos = Mantenimiento.query.filter(
            Mantenimiento.equipo_id == equipo_id,
            Mantenimiento.estado.in_(['pendiente', 'en_progreso'])
        ).count()
        
        return jsonify({
            'success': True,
            'equipo_id': equipo_id,
            'estado_equipo': equipo.estado,
            'tiene_incidentes_activos': incidentes_activos > 0,
            'total_incidentes_activos': incidentes_activos,
            'tiene_mantenimientos_activos': mantenimientos_activos > 0,
            'total_mantenimientos_activos': mantenimientos_activos
        }), 200
        
    except Exception as e:
        print(f"Error obteniendo estado detallado: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/reportes/equipos_por_sede', methods=['GET'])
@login_required
@role_required(1)
def api_reportes_equipos_por_sede():

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
    counts = get_sidebar_counts()
    return render_template('superadmin/gestion_inventario/incidentes.html',
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])

@admin_bp.route('/gestion-salones')
@login_required
@role_required(1)
def gestion_salones():
    counts = get_sidebar_counts()
    return render_template('superadmin/gestion_inventario/salones.html',
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])

@admin_bp.route('/registro_salon', methods=['GET', 'POST'])
@login_required
@role_required(1)
def registro_salon():
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
    return render_template('superadmin/gestion_inventario/registro_incidente.html')

@admin_bp.route('/api/salones', methods=['GET'])
@login_required
@role_required(1)
def api_salones():
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

@admin_bp.route('/api/incidentes', methods=['GET'])
@login_required
@role_required(1)
def api_listar_incidentes():

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
    try:
        data = request.get_json()
        
        if not all(key in data for key in ['equipo_id', 'prioridad', 'usuario_reporte', 'descripcion']):
            return jsonify({'success': False, 'error': 'Faltan campos requeridos'}), 400
        
        equipo = Equipo.query.get(data['equipo_id'])
        if not equipo:
            return jsonify({'success': False, 'error': 'Equipo no encontrado'}), 404
        
        sede_nombre = "Sin Sede"
        if equipo.salon and equipo.salon.sede:
            sede_nombre = equipo.salon.sede.nombre
        
        nuevo_incidente = Incidente(
            equipo_id=data['equipo_id'],
            prioridad=data['prioridad'],
            usuario_asignado=data['usuario_reporte'],
            descripcion=data['descripcion'],
            solucion_propuesta=data.get('solucion_propuesta'),
            estado='reportado',
            fecha=datetime.utcnow(),
            sede=sede_nombre
        )
        
        db.session.add(nuevo_incidente)
        db.session.flush() 

        from services.notification_service import notificar_nuevo_incidente
        notificaciones_creadas = notificar_nuevo_incidente(nuevo_incidente)
        
        equipo.estado = 'Incidente'
        
        db.session.commit()
        
        mensaje = 'Incidente creado exitosamente'
        if notificaciones_creadas > 0:
            mensaje += f' y {notificaciones_creadas} notificación(es) enviada(s)'
        
        return jsonify({
            'success': True,
            'message': mensaje,
            'incidente': nuevo_incidente.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error creando incidente: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Error creando incidente: {str(e)}'}), 500 
@admin_bp.route('/api/incidentes/<int:id_incidente>/estado', methods=['PUT'])
@login_required
@role_required(1)
def api_actualizar_estado_incidente(id_incidente):
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        incidente = Incidente.query.get_or_404(id_incidente)
        
        if not nuevo_estado or nuevo_estado not in ['reportado', 'en_proceso', 'resuelto', 'cerrado']:
             return jsonify({'success': False, 'error': 'Estado inválido.'}), 400

        incidente.estado = nuevo_estado
        
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

@admin_bp.route("/eventos/calendario", methods=["GET"])
@login_required
def calendario_eventos():
    counts = get_sidebar_counts()
    return render_template("superadmin/calendario_admin/index.html",
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])


@admin_bp.route("/debug/notificaciones-eventos", methods=["GET"])
@login_required
def debug_notificaciones_eventos():
    try:
        from controllers.models import Notificacion, Usuario, Evento
        
        print("\n" + "="*80)
        print("🔍 NOTIFICACIONES DE EVENTOS ESPECÍFICAMENTE")
        print("="*80)
        
        total_notificaciones = Notificacion.query.count()
        notif_eventos = Notificacion.query.filter_by(tipo='evento').count()
        notif_otros = total_notificaciones - notif_eventos
        
        print(f"\n📊 ESTADÍSTICAS DE NOTIFICACIONES:")
        print(f"   - Total: {total_notificaciones}")
        print(f"   - Tipo 'evento': {notif_eventos}")
        print(f"   - Otros tipos: {notif_otros}")
        
        notificaciones_eventos = Notificacion.query.filter_by(
            tipo='evento'
        ).order_by(Notificacion.creada_en.desc()).limit(30).all()
        
        print(f"\n📅 NOTIFICACIONES DE EVENTOS ({len(notificaciones_eventos)} encontradas):")
        
        for i, notif in enumerate(notificaciones_eventos, 1):
            usuario = Usuario.query.get(notif.usuario_id)
            nombre_usuario = usuario.nombre_completo if usuario else f"ID:{notif.usuario_id}"
            fecha_str = notif.creada_en.strftime("%m/%d %H:%M") if notif.creada_en else "Sin fecha"
            
            print(f"   {i}. [{fecha_str}] {nombre_usuario} (ID:{notif.usuario_id})")
            print(f"      📝 {notif.titulo}")
            print(f"      📄 {notif.mensaje[:60]}...")
            print(f"      🔸 Leída: {notif.leida}")
            print()
        
        print(f"\n👥 DISTRIBUCIÓN POR USUARIOS:")
        distribucion = {}
        notificaciones_todas = Notificacion.query.filter_by(tipo='evento').all()

        for notif in notificaciones_todas:
            if notif.usuario_id not in distribucion:
                usuario = Usuario.query.get(notif.usuario_id)
                nombre = usuario.nombre_completo if usuario else f"ID:{notif.usuario_id}"
                distribucion[notif.usuario_id] = {'nombre': nombre, 'count': 0}
            distribucion[notif.usuario_id]['count'] += 1

        # Ordenar por cantidad y mostrar top 15
        distribucion_ordenada = sorted(distribucion.values(), key=lambda x: x['count'], reverse=True)[:15]

        for item in distribucion_ordenada:
            print(f"   - {item['nombre']}: {item['count']} notificaciones")
        
        print("\n" + "="*80)
        print("✅ DIAGNÓSTICO DE EVENTOS COMPLETADO")
        print("="*80)
        
        return jsonify({
            "message": "Diagnóstico de eventos completado - Revisa la consola",
            "total_notificaciones": total_notificaciones,
            "notificaciones_eventos": notif_eventos,
            "distribucion_usuarios": len(distribucion)
        })
        
    except Exception as e:
        print(f"❌ ERROR EN DIAGNÓSTICO: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def get_sidebar_counts():
    from datetime import datetime
    
    try:
        print("🔧 DEBUG ADMIN: Calculando contadores del sidebar...")
        
        unread_messages = Comunicacion.query.filter(
            Comunicacion.destinatario_id == current_user.id_usuario,
            Comunicacion.estado.in_(['no_leido', 'inbox', 'unread', 'pendiente', 'nuevo'])
        ).count()
        
        print(f"📨 ADMIN - Comunicaciones no leídas: {unread_messages}")
        
        unread_notifications = Notificacion.query.filter_by(
            usuario_id=current_user.id_usuario,
            leida=False
        ).count()
        
        print(f"🔔 ADMIN - Notificaciones no leídas: {unread_notifications}")
        
        hoy = datetime.now().date()
        upcoming_events = Evento.query.filter(
            Evento.fecha.isnot(None),
            Evento.fecha >= hoy
        ).count()
        
        print(f"📅 ADMIN - Eventos próximos: {upcoming_events}")
        print(f"🎯 ADMIN RESUMEN - Mensajes: {unread_messages}, Notificaciones: {unread_notifications}, Eventos: {upcoming_events}")
        
        return {
            'unread_messages': unread_messages,
            'unread_notifications': unread_notifications,
            'upcoming_events': upcoming_events
        }
        
    except Exception as e:
        print(f"❌ ERROR en get_sidebar_counts ADMIN: {e}")
        return {
            'unread_messages': 0,
            'unread_notifications': 0,
            'upcoming_events': 0
        }

@admin_bp.route('/debug-contadores')
@login_required
@role_required('Administrador')
def debug_contadores_admin():
    counts = get_sidebar_counts()
    
    comunicaciones = Comunicacion.query.filter_by(destinatario_id=current_user.id_usuario).all()
    notificaciones = Notificacion.query.filter_by(usuario_id=current_user.id_usuario).all()
    
    debug_info = {
        'usuario_actual': current_user.id_usuario,
        'rol_actual': current_user.rol.nombre if current_user.rol else 'Sin rol',
        'counts_calculados': counts,
        'comunicaciones': [
            {'id': c.id_comunicacion, 'estado': c.estado, 'asunto': c.asunto, 'destinatario_id': c.destinatario_id} 
            for c in comunicaciones
        ],
        'notificaciones': [
            {'id': n.id_notificacion, 'leida': n.leida, 'titulo': n.titulo, 'usuario_id': n.usuario_id} 
            for n in notificaciones
        ]
    }
    
    return jsonify(debug_info)

@admin_bp.route("/debug/notificaciones-padres", methods=["GET"])
@login_required
def debug_notificaciones_padres():
    try:
        from controllers.models import Rol, Usuario, estudiante_padre, Evento
        
        print("🔍 INICIANDO DIAGNÓSTICO DE NOTIFICACIONES A PADRES")
        
        eventos_recientes = Evento.query.order_by(Evento.id.desc()).limit(5).all()
        print("📅 Eventos recientes:")
        for evento in eventos_recientes:
            print(f"   - {evento.nombre} | Rol: {evento.rol_destino} | Fecha: {evento.fecha}")
        
        rol_padre = Rol.query.filter_by(nombre='padre').first()
        if rol_padre:
            padres = Usuario.query.filter_by(id_rol_fk=rol_padre.id_rol).limit(10).all()
            print(f"👨‍👩‍👧‍👦 Padres en sistema ({len(padres)} encontrados):")
            for padre in padres:
                print(f"   - {padre.nombre_completo} (ID: {padre.id_usuario})")
        
        relaciones = db.session.execute(
            db.select(estudiante_padre).limit(10)
        ).fetchall()
        print("🔗 Relaciones padre-estudiante:")
        for rel in relaciones:
            print(f"   - Padre ID: {rel.padre_id} -> Estudiante ID: {rel.estudiante_id}")
        
        if padres:
            notificaciones_padres = Notificacion.query.filter(
                Notificacion.usuario_id.in_([p.id_usuario for p in padres]),
                Notificacion.tipo == 'evento'
            ).limit(10).all()
            
            print(f"📢 Notificaciones de eventos para padres ({len(notificaciones_padres)} encontradas):")
            for notif in notificaciones_padres:
                print(f"   - Para usuario {notif.usuario_id}: {notif.titulo}")
        
        return jsonify({
            "message": "Diagnóstico completado - Revisa la consola del servidor",
            "eventos": len(eventos_recientes),
            "padres": len(padres) if rol_padre else 0,
            "relaciones": len(relaciones),
            "notificaciones_padres": len(notificaciones_padres)
        })
        
    except Exception as e:
        print(f"❌ Error en diagnóstico: {str(e)}")
        return jsonify({"error": str(e)}), 500

@admin_bp.route("/eventos", methods=["GET"])
@login_required
def listar_eventos():
    try:
        eventos = Evento.query.all()
        resultado = []
        for ev in eventos:
            resultado.append({
                "id": ev.id,
                "nombre": ev.nombre,
                "descripcion": ev.descripcion,
                "fecha": ev.fecha.strftime("%Y-%m-%d"),
                "hora": ev.hora.strftime("%H:%M:%S"),
                "rol_destino": ev.rol_destino
            })
        return jsonify(resultado), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route("/eventos", methods=["POST"])
@login_required
def crear_evento():
    data = request.get_json()
    print("📥 Payload recibido:", data)

    try:
        nombre = data.get("nombre") or data.get("Nombre")
        descripcion = data.get("descripcion") or data.get("Descripcion")
        fecha_str = data.get("fecha") or data.get("Fecha")
        hora_str = data.get("hora") or data.get("Hora")
        rol_destino = data.get("rol_destino") or data.get("RolDestino")

        if not all([nombre, descripcion, fecha_str, hora_str, rol_destino]):
            return jsonify({"error": "Faltan campos obligatorios"}), 400

        hora_str = hora_str.replace("a. m.", "AM").replace("p. m.", "PM").strip()

        try:
            hora_dt = datetime.strptime(hora_str, "%I:%M %p")
        except ValueError:
            hora_dt = datetime.strptime(hora_str[:5], "%H:%M")

        fecha_evento = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        if fecha_evento < datetime.now().date():
            return jsonify({"error": "No se pueden crear eventos en fechas pasadas"}), 400

        # Crear evento
        nuevo_evento = Evento(
            nombre=nombre,
            descripcion=descripcion,
            fecha=fecha_evento,
            hora=hora_dt.time(),
            rol_destino=rol_destino
        )

        db.session.add(nuevo_evento)
        db.session.commit()

        from services.notification_service import notificar_nuevo_evento
        
        notificaciones_enviadas = notificar_nuevo_evento(nuevo_evento, current_user.id_usuario)
        
        print(f"✅ Evento creado - Notificaciones enviadas: {notificaciones_enviadas}")

        return jsonify({
            "mensaje": "Evento creado correctamente ✅", 
            "notificaciones_enviadas": notificaciones_enviadas,
            "evento_id": nuevo_evento.id
        }), 201

    except Exception as e:
        db.session.rollback()
        print("❌ Error creando evento:", str(e))
        return jsonify({"error": str(e)}), 400

@admin_bp.route("/eventos/<int:evento_id>", methods=["PUT"])
@login_required
def actualizar_evento(evento_id):
    data = request.get_json()
    print("📥 Payload actualización recibido:", data)

    try:
        evento = Evento.query.get(evento_id)
        if not evento:
            return jsonify({"error": "Evento no encontrado"}), 404

        
        nombre = data.get("nombre") or data.get("Nombre")
        descripcion = data.get("descripcion") or data.get("Descripcion")
        fecha_str = data.get("fecha") or data.get("Fecha")
        hora_str = data.get("hora") or data.get("Hora")
        rol_destino = data.get("rol_destino") or data.get("RolDestino")

        if not all([nombre, descripcion, fecha_str, hora_str, rol_destino]):
            return jsonify({"error": "Faltan campos obligatorios"}), 400

        hora_str = hora_str.replace("a. m.", "AM").replace("p. m.", "PM").strip()

        try:
            hora_dt = datetime.strptime(hora_str, "%I:%M %p")
        except ValueError:
            hora_dt = datetime.strptime(hora_str[:5], "%H:%M")

        fecha_evento = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        if fecha_evento < datetime.now().date():
            return jsonify({"error": "No se pueden actualizar eventos a fechas pasadas"}), 400

        evento.nombre = nombre
        evento.descripcion = descripcion
        evento.fecha = fecha_evento
        evento.hora = hora_dt.time()
        evento.rol_destino = rol_destino

        db.session.commit()

        from services.notification_service import notificar_evento_actualizado
        
        notificaciones_enviadas = notificar_evento_actualizado(evento, current_user.id_usuario)
        
        print(f"✅ Evento actualizado - Notificaciones enviadas: {notificaciones_enviadas}")

        return jsonify({
            "mensaje": "Evento actualizado correctamente ✅",
            "notificaciones_enviadas": notificaciones_enviadas
        }), 200

    except Exception as e:
        db.session.rollback()
        print("❌ Error actualizando evento:", str(e))
        return jsonify({"error": str(e)}), 400

@admin_bp.route("/eventos/<int:evento_id>", methods=["DELETE"])
@login_required
def eliminar_evento(evento_id):
    try:
        evento = Evento.query.get(evento_id)
        if not evento:
            return jsonify({"error": "Evento no encontrado"}), 404

        from services.notification_service import notificar_evento_eliminado
        
        notificaciones_enviadas = notificar_evento_eliminado(evento, current_user.id_usuario)
        
        print(f"✅ Evento eliminado - Notificaciones enviadas: {notificaciones_enviadas}")

        # Eliminar evento
        db.session.delete(evento)
        db.session.commit()

        return jsonify({
            "mensaje": "Evento eliminado correctamente ✅",
            "notificaciones_enviadas": notificaciones_enviadas
        }), 200

    except Exception as e:
        db.session.rollback()
        print("❌ Error eliminando evento:", str(e))
        return jsonify({"error": str(e)}), 500

# ==================== SISTEMA DE VOTACIÓN ====================

@admin_bp.route('/sistema-votaciones')
@login_required
@role_required(1)
def sistema_votaciones():
    counts = get_sidebar_counts()
    return render_template('superadmin/sistema_votaciones/admin.html',
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])


@admin_bp.route('/sistema-votaciones/votar')
@login_required
def votar():
    counts = get_sidebar_counts()
    return render_template('superadmin/sistema_votaciones/votar.html',
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])



@admin_bp.route("/guardar-horario", methods=["POST"])
@login_required
def guardar_horario():
    try:
        inicio = request.form.get("inicio")
        fin = request.form.get("fin")

        if not inicio or not fin:
            flash("Debe ingresar inicio y fin del horario", "danger")
            return redirect(url_for("admin.admin_panel"))

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

@admin_bp.route("/ultimo-horario", methods=["GET"])
@login_required
def ultimo_horario():
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
    candidatos = Candidato.query.all()
    lista = []
    for c in candidatos:
        lista.append({
            "id_candidato": c.id_candidato,
            "nombre": c.nombre,
            "categoria": c.categoria,
            "tarjeton": c.tarjeton,
            "propuesta": c.propuesta,
            "foto": c.foto,
            "votos": c.votos  
        })
    return jsonify(lista)

@admin_bp.route("/crear-candidato", methods=["POST"])
@login_required
@role_required(1)
def crear_candidato():
    try:
        nombre = request.form.get("nombre", "").strip()
        tarjeton = request.form.get("tarjeton", "").strip()
        propuesta = request.form.get("propuesta", "").strip()
        categoria = request.form.get("categoria", "").strip()
        foto = request.files.get("foto")

        if not nombre:
            return jsonify({"ok": False, "error": "⚠️ El nombre del candidato es obligatorio"}), 400
        
        if not tarjeton:
            return jsonify({"ok": False, "error": "⚠️ El número de tarjetón es obligatorio"}), 400
        
        if not propuesta:
            return jsonify({"ok": False, "error": "⚠️ La propuesta es obligatoria"}), 400
        
        if not categoria:
            return jsonify({"ok": False, "error": "⚠️ La categoría es obligatoria"}), 400

        candidato_existente = Candidato.query.filter_by(tarjeton=tarjeton).first()
        if candidato_existente:
            return jsonify({
                "ok": False, 
                "error": f"❌ El tarjetón {tarjeton} ya está registrado para el candidato {candidato_existente.nombre}"
            }), 400

        nombre_existente = Candidato.query.filter_by(nombre=nombre).first()
        if nombre_existente:
            return jsonify({
                "ok": False, 
                "error": f"❌ Ya existe un candidato registrado con el nombre {nombre}"
            }), 400

        filename = None
        if foto:
            if not foto.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                return jsonify({
                    "ok": False, 
                    "error": "❌ Formato de imagen no válido. Use PNG, JPG, JPEG o GIF"
                }), 400
            
            if len(foto.read()) > 5 * 1024 * 1024:
                return jsonify({
                    "ok": False, 
                    "error": "❌ La imagen es demasiado grande. Máximo 5MB"
                }), 400
            
            foto.seek(0)  
            filename = secure_filename(foto.filename)
            
            nombre_base = secure_filename(nombre)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{nombre_base}_{timestamp}_{filename}"
            
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

        candidatos = Candidato.query.all()
        return jsonify({
            "ok": True,
            "mensaje": f"✅ Candidato {nombre} creado exitosamente",
            "candidatos": [c.to_dict() for c in candidatos]
        })

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error inesperado al crear candidato: {str(e)}")
        return jsonify({
            "ok": False, 
            "error": f"❌ Error interno del servidor: {str(e)}"
        }), 500

@admin_bp.route("/candidatos/<int:candidato_id>", methods=["PUT", "POST"])
@login_required
@role_required(1)
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

        if not nombre or not propuesta or not categoria or not tarjeton:
            return jsonify({"ok": False, "error": "Todos los campos son obligatorios"}), 400

        existe_tarjeton = Candidato.query.filter(
            Candidato.tarjeton == tarjeton,
            Candidato.id_candidato != candidato.id_candidato
        ).first()
        if existe_tarjeton:
            return jsonify({"ok": False, "error": "⚠️ Ese número de tarjetón ya existe"}), 400

        existe_nombre = Candidato.query.filter(
            Candidato.nombre == nombre,
            Candidato.id_candidato != candidato.id_candidato
        ).first()
        if existe_nombre:
            return jsonify({"ok": False, "error": "⚠️ Ya existe un candidato con ese nombre"}), 400

        if file:
            ext_permitidas = {"png", "jpg", "jpeg", "gif"}
            if "." not in file.filename or file.filename.rsplit(".", 1)[1].lower() not in ext_permitidas:
                return jsonify({"ok": False, "error": "Formato de imagen inválido"}), 400

            ext = file.filename.rsplit(".", 1)[1].lower()
            foto_filename = f"{secure_filename(nombre)}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
            path = os.path.join(current_app.config["UPLOAD_FOLDER"], foto_filename)
            file.save(path)
            candidato.foto = foto_filename

        candidato.nombre = nombre
        candidato.propuesta = propuesta
        candidato.categoria = categoria
        candidato.tarjeton = tarjeton

        db.session.commit()

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
    try:
        candidato = Candidato.query.get(candidato_id)
        if not candidato:
            return jsonify({"ok": False, "error": "Candidato no encontrado"}), 404

        votos_asociados = Voto.query.filter_by(candidato_id=candidato_id).all()
        total_votos = len(votos_asociados)
        
        estudiantes_liberados = 0
        
        if total_votos > 0:
            usuarios_votantes_ids = list(set([voto.estudiante_id for voto in votos_asociados]))
            
            estudiantes_afectados = Usuario.query.filter(
                Usuario.id_usuario.in_(usuarios_votantes_ids),
                Usuario.id_rol_fk == 3 
            ).all()
            
            for estudiante in estudiantes_afectados:
                estudiante.voto_registrado = False
                estudiantes_liberados += 1
            
            for voto in votos_asociados:
                db.session.delete(voto)

        db.session.delete(candidato)
        db.session.commit()

        candidatos = Candidato.query.all()
        candidatos_data = [
            {
                "id_candidato": c.id_candidato,
                "nombre": c.nombre,
                "categoria": c.categoria,
                "tarjeton": c.tarjeton,
                "propuesta": c.propuesta,
                "votos": c.votos,
                "foto": c.foto
            }
            for c in candidatos
        ]

        mensaje = "✅ Candidato eliminado correctamente"
        if total_votos > 0:
            mensaje += f". {estudiantes_liberados} estudiante(s) pueden volver a votar."

        return jsonify({
            "ok": True, 
            "mensaje": mensaje,
            "candidatos": candidatos_data
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": f"Error al eliminar candidato: {str(e)}"}), 500



@admin_bp.route("/test-sistema-votos", methods=["POST"])
@login_required
def test_sistema_votos():
    try:
        estudiante = Usuario.query.filter_by(id_rol_fk=3).first()  
        if not estudiante:
            return jsonify({"error": "No hay estudiantes"}), 400
            
        print(f"✅ Estudiante: {estudiante.nombre}")
        print(f"✅ voto_registrado: {estudiante.voto_registrado}")
        
        candidatos = Candidato.query.all()
        print(f"✅ Candidatos: {len(candidatos)}")
        
        for c in candidatos:
            print(f"   - {c.nombre}: {c.votos} votos")
        
        if candidatos:
            candidato_prueba = candidatos[0]
            votos_antes = candidato_prueba.votos
            
            candidato_prueba.votos += 1
            estudiante.voto_registrado = True
            db.session.commit()
            
            db.session.refresh(candidato_prueba)
            votos_despues = candidato_prueba.votos
            
            return jsonify({
                "ok": True,
                "prueba": {
                    "candidato": candidato_prueba.nombre,
                    "votos_antes": votos_antes,
                    "votos_despues": votos_despues,
                    "estudiante_voto_registrado": estudiante.voto_registrado
                }
            })
        
        return jsonify({"error": "No hay candidatos"})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ==================== GESTIÓN DE PUBLICACIÓN DE RESULTADOS ====================

@admin_bp.route("/estado-publicacion", methods=["GET"])
def obtener_estado_publicacion():
    try:
        estado = EstadoPublicacion.query.first()
        
        if not estado:
            estado = EstadoPublicacion(
                resultados_publicados=False,
                usuario_publico='Sistema'
            )
            db.session.add(estado)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'estado': estado.to_dict()
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo estado de publicación: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"Error al obtener estado: {str(e)}"
        }), 500

@admin_bp.route("/publicar-resultados", methods=["POST"])
@login_required
@role_required(1)
def publicar_resultados():
    try:
        from flask_login import current_user
        
        usuario = current_user.nombre if current_user.is_authenticated else 'Administrador'
        
        print(f"📢 Intentando publicar resultados como: {usuario}")
        
        estado = EstadoPublicacion.query.first()
        
        if estado:
            print(f"✅ Estado encontrado, actualizando...")
            estado.resultados_publicados = True
            estado.fecha_publicacion = datetime.now()
            estado.usuario_publico = usuario
        else:
            print(f"🆕 Creando nuevo estado de publicación...")
            estado = EstadoPublicacion(
                resultados_publicados=True,
                fecha_publicacion=datetime.now(),
                usuario_publico=usuario
            )
            db.session.add(estado)
        
        db.session.commit()
        
        print(f"📢 Resultados publicados correctamente por: {usuario}")
        
        return jsonify({
            "success": True, 
            "message": "Resultados publicados correctamente. Ahora son visibles para todos los usuarios.",
            "fecha_publicacion": estado.fecha_publicacion.isoformat(),
            "publicado_por": usuario
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error al publicar resultados: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False, 
            "error": f"Error al publicar resultados: {str(e)}"
        }), 500

@admin_bp.route("/ocultar-resultados", methods=["POST"])
@login_required
@role_required(1)
def ocultar_resultados():
    try:
        from flask_login import current_user
        
        usuario = current_user.nombre if current_user.is_authenticated else 'Administrador'
        
        print(f"🔒 Intentando ocultar resultados como: {usuario}")
        
        estado = EstadoPublicacion.query.first()
        
        if estado:
            estado.resultados_publicados = False
            estado.usuario_publico = usuario
        else:
            estado = EstadoPublicacion(
                resultados_publicados=False,
                usuario_publico=usuario
            )
            db.session.add(estado)
        
        db.session.commit()
        
        print(f"🔒 Resultados ocultados correctamente por: {usuario}")
        
        return jsonify({
            "success": True, 
            "message": "Resultados ocultados correctamente.",
            "fecha_ocultacion": datetime.now().isoformat(),
            "ocultado_por": usuario
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error al ocultar resultados: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False, 
            "error": f"Error al ocultar resultados: {str(e)}"
        }), 500

@admin_bp.route("/resultados-publicos", methods=["GET"])
def resultados_publicos():
    try:
        estado = EstadoPublicacion.query.first()
        
        if not estado or not estado.resultados_publicados:
            return jsonify({
                'success': True,
                'resultados_publicados': False,
                'message': 'Los resultados no están disponibles públicamente.'
            }), 200
        
        candidatos = Candidato.query.all()
        
        resultados = {
            'personero': [],
            'contralor': [],
            'cabildante': []
        }
        
        for candidato in candidatos:
            resultado_candidato = {
                'id': candidato.id_candidato,
                'nombre': candidato.nombre,
                'tarjeton': candidato.tarjeton,
                'propuesta': candidato.propuesta,
                'foto': candidato.foto,
                'votos': candidato.votos or 0,
                'categoria': candidato.categoria
            }
            cat = (candidato.categoria or '').strip().lower()
            if cat in ('personero', 'personero estudiantil'):
                key = 'personero'
            elif cat in ('contralor', 'contralor estudiantil'):
                key = 'contralor'
            elif cat in ('cabildante', 'cabildante estudiantil'):
                key = 'cabildante'
            else:
                key = None
            if key:
                resultados[key].append(resultado_candidato)
        
        for categoria in resultados:
            resultados[categoria].sort(key=lambda x: x['votos'], reverse=True)
        
        return jsonify({
            'success': True,
            'resultados_publicados': True,
            'resultados': resultados,
            'total_votos': sum(c.votos or 0 for c in candidatos),
            'fecha_publicacion': estado.fecha_publicacion.isoformat() if estado.fecha_publicacion else None,
            'publicado_por': estado.usuario_publico,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo resultados públicos: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f"Error al obtener resultados: {str(e)}"
        }), 500



# ============================================================================ #
# RUTAS DE REPORTES DE CALIFICACIONES
# ============================================================================ #

@admin_bp.route('/reportes-calificaciones')
@login_required
@role_required(1)
def reportes_calificaciones():
    counts = get_sidebar_counts()
    return render_template('superadmin/reportes/reportes.html',
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])

@admin_bp.route('/api/reportes-calificaciones', methods=['GET'])
@login_required
@role_required(1)
def api_obtener_reportes():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        estado = request.args.get('estado', '', type=str)
        curso = request.args.get('curso', '', type=str)
        profesor = request.args.get('profesor', '', type=str)
        
        query = db.session.query(ReporteCalificaciones)
        
        if estado:
            query = query.filter(ReporteCalificaciones.estado == estado)
        if curso:
            query = query.filter(ReporteCalificaciones.nombre_curso.ilike(f'%{curso}%'))
        if profesor:
            query = query.join(Usuario, ReporteCalificaciones.profesor_id == Usuario.id_usuario)
            query = query.filter(Usuario.nombre_completo.ilike(f'%{profesor}%'))
        
        query = query.order_by(ReporteCalificaciones.fecha_generacion.desc())
        
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
        
        reporte = ReporteCalificaciones.query.get(reporte_id)
        if not reporte:
            return jsonify({
                'success': False,
                'message': 'Reporte no encontrado'
            }), 404
        
        profesor = Usuario.query.get(profesor_id)
        if not profesor:
            return jsonify({
                'success': False,
                'message': 'Profesor no encontrado'
            }), 404
        
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
    counts = get_sidebar_counts()
    return render_template('superadmin/comunicaciones.html',
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])

@admin_bp.route('/api/comunicaciones', methods=['GET'])
@login_required
@role_required(1)
def api_obtener_comunicaciones():
    try:
        folder = request.args.get('folder', 'inbox')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20)) 
        
        if folder == 'inbox':
            comunicaciones = db.session.query(Comunicacion).filter(
                Comunicacion.destinatario_id == current_user.id_usuario,
                Comunicacion.estado == 'inbox'
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
                    'tipo': 'recibida'
                })
                
        elif folder == 'sent':
            comunicaciones = db.session.query(Comunicacion).filter(
                Comunicacion.remitente_id == current_user.id_usuario,
                Comunicacion.estado.in_(['inbox', 'sent'])
            ).order_by(Comunicacion.fecha_envio.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            ).items
            
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
                
                destinatario_info = {
                    'nombre': com.destinatario.nombre_completo if com.destinatario else 'Desconocido',
                    'email': com.destinatario.correo if com.destinatario else '',
                    'id': com.destinatario.id_usuario if com.destinatario else None
                }
                grupos[grupo_key]['destinatarios'].append(destinatario_info)
                grupos[grupo_key]['destinatarios_count'] += 1
            
            comunicaciones_data = []
            for grupo in grupos.values():
                if grupo['destinatarios_count'] > 1:
                    grupo['destinatario'] = f"{grupo['destinatarios'][0]['nombre']} y {grupo['destinatarios_count'] - 1} más"
                    grupo['destinatario_nombre'] = grupo['destinatario']
                else:
                    grupo['destinatario'] = grupo['destinatarios'][0]['nombre']
                    grupo['destinatario_nombre'] = grupo['destinatario']
                
                comunicaciones_data.append(grupo)
                
        elif folder == 'draft':
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
        
        destinatarios = []
        tipos = []
        if isinstance(recipient_types, list) and len(recipient_types) > 0:
            tipos = recipient_types
        elif isinstance(recipient_type, str) and recipient_type:
            tipos = [recipient_type]
        
        if 'all' in tipos:
            destinatarios = Usuario.query.filter_by(estado_cuenta='activa').all()
        elif len(tipos) > 0:
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
            rol_profesor = Rol.query.filter_by(nombre='Profesor').first()
            if rol_profesor:
                destinatarios = Usuario.query.filter_by(id_rol_fk=rol_profesor.id_rol, estado_cuenta='activa').all()
        elif recipient_type == 'estudiantes':
            rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()
            if rol_estudiante:
                destinatarios = Usuario.query.filter_by(id_rol_fk=rol_estudiante.id_rol, estado_cuenta='activa').all()
        elif recipient_type == 'padres':
            rol_padre = Rol.query.filter_by(nombre='Padre').first()
            if rol_padre:
                destinatarios = Usuario.query.filter_by(id_rol_fk=rol_padre.id_rol, estado_cuenta='activa').all()
        elif recipient_type == 'specific' and to_email:
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
        
        import uuid
        grupo_id = str(uuid.uuid4())
        comunicaciones_creadas = []
        
        for destinatario in destinatarios:
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
    try:
        from controllers.models import Comunicacion
        from datetime import datetime, timedelta
        
        now = datetime.utcnow()
        
        one_month_ago = now - timedelta(days=30)
        
        two_months_ago = now - timedelta(days=60)
        
        mensajes_a_papelera = Comunicacion.query.filter(
            Comunicacion.estado.in_(['inbox', 'sent', 'draft']),
            Comunicacion.fecha_envio < one_month_ago
        ).all()
        
        moved_to_trash = 0
        for mensaje in mensajes_a_papelera:
            mensaje.estado = 'deleted'
            moved_to_trash += 1
        
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
        
        comunicacion.estado = 'sent'  
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
    try:
        comunicacion = Comunicacion.query.get(comunicacion_id)
        
        if not comunicacion:
            return jsonify({
                'success': False,
                'message': 'Comunicación no encontrada'
            }), 404
        
        if (comunicacion.remitente_id != current_user.id_usuario and 
            comunicacion.destinatario_id != current_user.id_usuario):
            return jsonify({
                'success': False,
                'message': 'No tienes permisos para eliminar esta comunicación'
            }), 403
        
        if comunicacion.estado == 'deleted':
            db.session.delete(comunicacion)
            message = 'Comunicación eliminada permanentemente'
        else:
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
    try:
        data = request.get_json()
        comunicacion_ids = data.get('ids', [])
        
        if not comunicacion_ids:
            return jsonify({
                'success': False,
                'message': 'No se proporcionaron IDs de comunicaciones'
            }), 400
        
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
        
        eliminadas = 0
        movidas_a_papelera = 0
        
        for comunicacion in comunicaciones:
            if comunicacion.estado == 'deleted':
                db.session.delete(comunicacion)
                eliminadas += 1
            else:
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
    try:
        comunicacion = Comunicacion.query.get(comunicacion_id)
        
        if not comunicacion:
            return jsonify({
                'success': False,
                'message': 'Comunicación no encontrada'
            }), 404
        
        if (comunicacion.remitente_id != current_user.id_usuario and 
            comunicacion.destinatario_id != current_user.id_usuario):
            return jsonify({
                'success': False,
                'message': 'No tienes permisos para restaurar esta comunicación'
            }), 403
        
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
        
        destinatario_id = None
        if to_email:
            destinatario = Usuario.query.filter_by(correo=to_email).first()
            if destinatario:
                destinatario_id = destinatario.id_usuario
        
        borrador = Comunicacion(
            remitente_id=current_user.id_usuario,
            destinatario_id=destinatario_id or current_user.id_usuario, 
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
    try:
        query = request.args.get('q', '').strip()
        
        if len(query) < 2:
            return jsonify([])
        
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
    usuarios_pendientes = Usuario.query.filter(
        Usuario.email_verified == False,
        Usuario.verification_code.isnot(None)
    ).all()
    
    counts = get_sidebar_counts()
    
    return render_template('superadmin/verification_codes.html', 
                        usuarios_pendientes=usuarios_pendientes,
                        unread_messages=counts['unread_messages'],
                        unread_notifications=counts['unread_notifications'],
                        upcoming_events=counts['upcoming_events'])

@admin_bp.route('/reenviar-verificacion', methods=['POST'])
@login_required
@role_required(1)
def reenviar_verificacion():
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
    counts = get_sidebar_counts()
    return render_template('superadmin/notificaciones/notificaciones.html',
                         unread_messages=counts['unread_messages'],
                         unread_notifications=counts['unread_notifications'],
                         upcoming_events=counts['upcoming_events'])


@admin_bp.route('/api/notificaciones')
@login_required
@role_required(1)
def api_notificaciones():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        filtro = request.args.get('filtro', 'todas', type=str)
        
        from services.notification_service import obtener_todas_notificaciones
        
        todas_notificaciones = obtener_todas_notificaciones(current_user.id_usuario, limite=1000)
        
        if filtro == 'pendientes':
            notificaciones_filtradas = [n for n in todas_notificaciones if not n.leida]
        elif filtro == 'leidas':
            notificaciones_filtradas = [n for n in todas_notificaciones if n.leida]
        else:
            notificaciones_filtradas = todas_notificaciones
        
        total = len(notificaciones_filtradas)
        pages = (total + per_page - 1) // per_page 
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        notificaciones_pagina = notificaciones_filtradas[start_idx:end_idx]
        
        return jsonify({
            'success': True,
            'data': {
                'notificaciones': [notif.to_dict() for notif in notificaciones_pagina],
                'total': total,
                'pages': pages,
                'current_page': page,
                'has_next': page < pages,
                'has_prev': page > 1
            }
        })
        
    except Exception as e:
        print(f"❌ Error en API notificaciones: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@admin_bp.route('/api/notificaciones/marcar-leidas', methods=['POST'])
@login_required
@role_required(1)
def api_marcar_leidas():
    try:
        data = request.get_json()
        notificacion_ids = data.get('notificacion_ids', [])
        
        from services.notification_service import marcar_notificacion_como_leida
        
        if notificacion_ids:
            contador = 0
            for notif_id in notificacion_ids:
                if marcar_notificacion_como_leida(notif_id, current_user.id_usuario):
                    contador += 1
            
            return jsonify({
                'success': True,
                'message': f'Se marcaron {contador} notificaciones como leídas'
            })
        else:
            from services.notification_service import obtener_notificaciones_no_leidas
            
            notificaciones_no_leidas = obtener_notificaciones_no_leidas(current_user.id_usuario)
            contador = 0
            
            for notif in notificaciones_no_leidas:
                if marcar_notificacion_como_leida(notif.id_notificacion, current_user.id_usuario):
                    contador += 1
            
            return jsonify({
                'success': True,
                'message': f'Se marcaron {contador} notificaciones como leídas'
            })
        
    except Exception as e:
        print(f"❌ Error marcando notificaciones como leídas: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@admin_bp.route('/api/notificaciones/eliminar', methods=['POST'])
@login_required
@role_required(1)
def api_eliminar_notificaciones():
    try:
        data = request.get_json()
        notificacion_ids = data.get('notificacion_ids', [])
        eliminar_todas = data.get('eliminar_todas', False)
        
        from controllers.models import Notificacion, db
        
        if eliminar_todas:
            deleted = Notificacion.query.filter_by(usuario_id=current_user.id_usuario).delete()
            db.session.commit()
            message = f'Se eliminaron {deleted} notificaciones'
        else:
            deleted = Notificacion.query.filter(
                Notificacion.id_notificacion.in_(notificacion_ids),
                Notificacion.usuario_id == current_user.id_usuario
            ).delete(synchronize_session=False)
            db.session.commit()
            message = f'Se eliminaron {deleted} notificaciones'
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error eliminando notificaciones: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
    


# ============================================================================
# GESTIÓN DE CICLOS Y PERIODOS ACADÉMICOS
# ============================================================================

@admin_bp.route('/periodos')
@admin_bp.route('/periodos/dashboard')
@login_required
@role_required(1)
def periodos_dashboard():
    return render_template('superadmin/gestion_academica/periodos.html')



@admin_bp.route('/api/ciclos', methods=['GET'])
@login_required
@role_required(1)
def api_obtener_ciclos():
    try:
        from services.periodo_service import obtener_todos_los_ciclos
        
        ciclos = obtener_todos_los_ciclos()
        
        return jsonify({
            'success': True,
            'ciclos': [ciclo.to_dict() for ciclo in ciclos]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error obteniendo ciclos: {str(e)}'
        }), 500


@admin_bp.route('/api/ciclos', methods=['POST'])
@login_required
@role_required(1)
def api_crear_ciclo():
    try:
        from services.periodo_service import crear_ciclo_academico
        
        data = request.get_json()
        nombre = data.get('nombre')
        fecha_inicio = datetime.strptime(data.get('fecha_inicio'), '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(data.get('fecha_fin'), '%Y-%m-%d').date()
        
        ciclo, error = crear_ciclo_academico(nombre, fecha_inicio, fecha_fin)
        
        if error:
            return jsonify({
                'success': False,
                'message': error
            }), 400
        
        return jsonify({
            'success': True,
            'message': 'Ciclo académico creado exitosamente',
            'ciclo': ciclo.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error creando ciclo: {str(e)}'
        }), 500


@admin_bp.route('/api/ciclos/<int:ciclo_id>', methods=['GET'])
@login_required
@role_required(1)
def api_obtener_ciclo(ciclo_id):
    try:
        from controllers.models import CicloAcademico
        
        ciclo = CicloAcademico.query.get(ciclo_id)
        if not ciclo:
            return jsonify({
                'success': False,
                'message': 'Ciclo no encontrado'
            }), 404
        
        return jsonify({
            'success': True,
            'ciclo': ciclo.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@admin_bp.route('/api/ciclos/<int:ciclo_id>/activar', methods=['POST'])
@login_required
@role_required(1)
def api_activar_ciclo(ciclo_id):
    try:
        from services.periodo_service import activar_ciclo
        
        success, error = activar_ciclo(ciclo_id)
        
        if error:
            return jsonify({
                'success': False,
                'message': error
            }), 400
        
        return jsonify({
            'success': True,
            'message': 'Ciclo activado exitosamente'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error activando ciclo: {str(e)}'
        }), 500


@admin_bp.route('/api/ciclos/<int:ciclo_id>', methods=['PUT'])
@login_required
@role_required(1)
def api_actualizar_ciclo(ciclo_id):
    try:
        from controllers.models import CicloAcademico
        
        ciclo = CicloAcademico.query.get(ciclo_id)
        if not ciclo:
            return jsonify({
                'success': False,
                'message': 'Ciclo no encontrado'
            }), 404
        
        if ciclo.estado == 'cerrado':
            return jsonify({
                'success': False,
                'message': 'No se puede editar un ciclo cerrado'
            }), 400
        
        data = request.get_json()
        
        if 'nombre' in data:
            ciclo.nombre = data['nombre']
        if 'fecha_inicio' in data:
            from datetime import datetime
            ciclo.fecha_inicio = datetime.strptime(data['fecha_inicio'], '%Y-%m-%d').date()
        if 'fecha_fin' in data:
            from datetime import datetime
            ciclo.fecha_fin = datetime.strptime(data['fecha_fin'], '%Y-%m-%d').date()
        
        if ciclo.fecha_inicio >= ciclo.fecha_fin:
            return jsonify({
                'success': False,
                'message': 'La fecha de inicio debe ser anterior a la fecha de fin'
            }), 400
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Ciclo actualizado exitosamente',
            'ciclo': ciclo.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error actualizando ciclo: {str(e)}'
        }), 500


@admin_bp.route('/api/ciclos/<int:ciclo_id>', methods=['DELETE'])
@login_required
@role_required(1)
def api_eliminar_ciclo(ciclo_id):
    try:
        from controllers.models import CicloAcademico
        
        ciclo = CicloAcademico.query.get(ciclo_id)
        if not ciclo:
            return jsonify({
                'success': False,
                'message': 'Ciclo no encontrado'
            }), 404
        
        if ciclo.activo:
            return jsonify({
                'success': False,
                'message': 'No se puede eliminar el ciclo activo'
            }), 400
        
        if ciclo.periodos and len(ciclo.periodos) > 0:
            return jsonify({
                'success': False,
                'message': 'No se puede eliminar un ciclo que tiene periodos. Elimine los periodos primero.'
            }), 400
        
        nombre_ciclo = ciclo.nombre
        db.session.delete(ciclo)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Ciclo "{nombre_ciclo}" eliminado exitosamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error eliminando ciclo: {str(e)}'
        }), 500


@admin_bp.route('/api/ciclos/activo', methods=['GET'])
@login_required
@role_required(1)
def api_obtener_ciclo_activo():
    try:
        from services.periodo_service import obtener_ciclo_activo
        
        ciclo = obtener_ciclo_activo()
        
        if not ciclo:
            return jsonify({
                'success': True,
                'ciclo': None,
                'message': 'No hay ciclo activo'
            })
        
        return jsonify({
            'success': True,
            'ciclo': ciclo.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


# ==================== PERIODOS ACADÉMICOS ====================

@admin_bp.route('/api/periodos', methods=['GET'])
@login_required
@role_required(1)
def api_obtener_periodos():
    try:
        from services.periodo_service import obtener_periodos_ciclo
        
        ciclo_id = request.args.get('ciclo_id', type=int)
        
        if not ciclo_id:
            return jsonify({
                'success': False,
                'message': 'Se requiere ciclo_id'
            }), 400
        
        periodos = obtener_periodos_ciclo(ciclo_id)
        
        return jsonify({
            'success': True,
            'periodos': [periodo.to_dict() for periodo in periodos]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error obteniendo periodos: {str(e)}'
        }), 500


@admin_bp.route('/api/periodos', methods=['POST'])
@login_required
@role_required(1)
def api_crear_periodo():
    try:
        from services.periodo_service import crear_periodo
        
        data = request.get_json()
        ciclo_id = data.get('ciclo_id')
        numero_periodo = data.get('numero_periodo')
        nombre = data.get('nombre')
        fecha_inicio = datetime.strptime(data.get('fecha_inicio'), '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(data.get('fecha_fin'), '%Y-%m-%d').date()
        fecha_cierre_notas = datetime.strptime(data.get('fecha_cierre_notas'), '%Y-%m-%d').date()
        dias_notificacion = data.get('dias_notificacion', 7)
        
        periodo, error = crear_periodo(
            ciclo_id, numero_periodo, nombre, 
            fecha_inicio, fecha_fin, fecha_cierre_notas, 
            dias_notificacion
        )
        
        if error:
            return jsonify({
                'success': False,
                'message': error
            }), 400
        
        return jsonify({
            'success': True,
            'message': 'Periodo creado exitosamente',
            'periodo': periodo.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error creando periodo: {str(e)}'
        }), 500


@admin_bp.route('/api/periodos/<int:periodo_id>', methods=['GET'])
@login_required
@role_required(1)
def api_obtener_periodo(periodo_id):
    try:
        from controllers.models import PeriodoAcademico
        
        periodo = PeriodoAcademico.query.get(periodo_id)
        if not periodo:
            return jsonify({
                'success': False,
                'message': 'Periodo no encontrado'
            }), 404
        
        return jsonify({
            'success': True,
            'periodo': periodo.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@admin_bp.route('/api/periodos/<int:periodo_id>', methods=['PUT'])
@login_required
@role_required(1)
def api_actualizar_periodo(periodo_id):
    try:
        from services.periodo_service import actualizar_periodo
        
        data = request.get_json()
        
        if 'fecha_inicio' in data:
            data['fecha_inicio'] = datetime.strptime(data['fecha_inicio'], '%Y-%m-%d').date()
        if 'fecha_fin' in data:
            data['fecha_fin'] = datetime.strptime(data['fecha_fin'], '%Y-%m-%d').date()
        if 'fecha_cierre_notas' in data:
            data['fecha_cierre_notas'] = datetime.strptime(data['fecha_cierre_notas'], '%Y-%m-%d').date()
        
        periodo, error = actualizar_periodo(periodo_id, data)
        
        if error:
            return jsonify({
                'success': False,
                'message': error
            }), 400
        
        return jsonify({
            'success': True,
            'message': 'Periodo actualizado exitosamente',
            'periodo': periodo.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error actualizando periodo: {str(e)}'
        }), 500


@admin_bp.route('/api/periodos/<int:periodo_id>', methods=['DELETE'])
@login_required
@role_required(1)
def api_eliminar_periodo(periodo_id):
    try:
        from services.periodo_service import eliminar_periodo
        
        success, error = eliminar_periodo(periodo_id)
        
        if error:
            return jsonify({
                'success': False,
                'message': error
            }), 400
        
        return jsonify({
            'success': True,
            'message': 'Periodo eliminado exitosamente'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error eliminando periodo: {str(e)}'
        }), 500


@admin_bp.route('/api/periodos/<int:periodo_id>/cerrar', methods=['POST'])
@login_required
@role_required(1)
def api_cerrar_periodo(periodo_id):
    try:
        from services.periodo_service import cerrar_periodo
        
        success, error = cerrar_periodo(periodo_id)
        
        if error:
            return jsonify({
                'success': False,
                'message': error
            }), 400
        
        return jsonify({
            'success': True,
            'message': 'Periodo cerrado exitosamente. Se han generado los reportes.'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error cerrando periodo: {str(e)}'
        }), 500


@admin_bp.route('/api/periodos/activo', methods=['GET'])
@login_required
@role_required(1)
def api_obtener_periodo_activo():
    try:
        from services.periodo_service import obtener_periodo_activo
        
        periodo = obtener_periodo_activo()
        
        if not periodo:
            return jsonify({
                'success': True,
                'periodo': None,
                'message': 'No hay periodo activo'
            })
        
        return jsonify({
            'success': True,
            'periodo': periodo.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


# ==================== FINALIZACIÓN DE CICLO ====================

@admin_bp.route('/api/ciclos/<int:ciclo_id>/finalizar', methods=['POST'])
@login_required
@role_required(1)
def api_finalizar_ciclo(ciclo_id):
    try:
        from services.promocion_service import finalizar_ciclo_escolar
        
        resultado = finalizar_ciclo_escolar(ciclo_id)
        
        if not resultado.get('success', False):
            return jsonify(resultado), 400
        
        return jsonify({
            'success': True,
            'message': 'Ciclo escolar finalizado exitosamente',
            'resultado': resultado
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error finalizando ciclo: {str(e)}'
        }), 500


# ==================== REPORTES DE PERIODOS ====================

@admin_bp.route('/api/reportes/periodo/<int:periodo_id>')
@login_required
@role_required(1)
def api_reportes_periodo(periodo_id):
    try:
        from services.reporte_service import obtener_reportes_periodo
        
        reportes = obtener_reportes_periodo(periodo_id)
        
        return jsonify({
            'success': True,
            'reportes': [reporte.to_dict() for reporte in reportes]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@admin_bp.route('/api/reportes/ciclo/<int:ciclo_id>')
@login_required
@role_required(1)
def api_reportes_ciclo(ciclo_id):
    try:
        from services.reporte_service import obtener_reportes_ciclo
        
        reportes = obtener_reportes_ciclo(ciclo_id)
        
        return jsonify({
            'success': True,
            'reportes': [reporte.to_dict() for reporte in reportes]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@admin_bp.route('/api/reportes/promocion/<int:ciclo_id>', methods=['POST'])
@login_required
@role_required(1)
def api_generar_reporte_promocion(ciclo_id):
    try:
        from services.reporte_service import generar_reporte_promocion
        
        reporte = generar_reporte_promocion(ciclo_id)
        
        if not reporte:
            return jsonify({
                'success': False,
                'message': 'No se pudo generar el reporte'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Reporte de promoción generado exitosamente',
            'reporte': reporte.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
