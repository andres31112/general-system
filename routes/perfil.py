from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from extensions import db
from controllers.forms import PerfilForm
from controllers.models import HorarioCompartido, Asignatura, Usuario, Curso 

perfil = Blueprint('perfil', __name__, url_prefix='/perfil')

def obtener_detalles_profesor(user_id):
    profesor = Usuario.query.get(user_id)
    if not profesor or not profesor.es_profesor():
        return {
            'asignaturas_list': [],
            'cursos_list': [],
            'total_horarios': 0
        }
    
    asignaturas_nombres = sorted([a.nombre for a in profesor.asignaturas])
    
    total_horarios_compartidos = HorarioCompartido.query.filter_by(profesor_id=user_id).count()
    
    try:
        cursos_unicos_query = db.session.query(Curso.nombreCurso)\
                                       .join(HorarioCompartido, HorarioCompartido.curso_id == Curso.id_curso)\
                                       .filter(HorarioCompartido.profesor_id == user_id)\
                                       .distinct()\
                                       .order_by(Curso.nombreCurso)\
                                       .all()
        cursos_nombres = [c[0] for c in cursos_unicos_query]
    except Exception:
        cursos_nombres = []
    
    return {
        'asignaturas_list': asignaturas_nombres,
        'cursos_list': cursos_nombres,
        'total_horarios': total_horarios_compartidos
    }

def obtener_estadisticas_profesor_legacy(user_id):
    profesor = Usuario.query.get(user_id)
    if not profesor or not profesor.es_profesor():
        return {
            'total_cursos': 0,
            'total_asignaturas': 0,
            'total_horarios': 0
        }
    
    total_asignaturas = len(profesor.asignaturas)
    total_horarios_compartidos = HorarioCompartido.query.filter_by(profesor_id=user_id).count()
    
    cursos_ids = db.session.query(HorarioCompartido.curso_id)\
                   .filter(HorarioCompartido.profesor_id == user_id)\
                   .distinct()\
                   .all()
    total_cursos_unicos = len(cursos_ids)
    
    return {
        'total_cursos': total_cursos_unicos,
        'total_asignaturas': total_asignaturas,
        'total_horarios': total_horarios_compartidos
    }

@perfil.route("/ver")
@login_required 
def ver_perfil():
    form = PerfilForm() 

    form.nombre.data = current_user.nombre
    form.apellido.data = current_user.apellido
    form.telefono.data = current_user.telefono
    
    form.tipo_doc.data = current_user.tipo_doc
    form.no_identidad.data = current_user.no_identidad
    form.correo.data = current_user.correo
    form.estado_cuenta.data = current_user.estado_cuenta
    
    rol_nombre = current_user.rol_nombre 
    
    # FIX APLICADO: Usamos .strip() para eliminar espacios invisibles y .capitalize()
    rol_display = rol_nombre.strip().capitalize()
    
    form.rol.data = rol_display

    contexto = {'form': form, 'rol_usuario': rol_display}
    
    if current_user.es_profesor(): 
        detalles = obtener_detalles_profesor(current_user.id_usuario)
        contexto.update(detalles)
    else:
        contexto.update({
            'asignaturas_list': [],
            'cursos_list': [],
            'total_horarios': 0
        })
    
    return render_template("ver_perfil.html", **contexto)

@perfil.route("/editar", methods=["GET", "POST"])
@login_required 
def editar_perfil():
    form = PerfilForm()

    if form.validate_on_submit():
        try:
            current_user.nombre = form.nombre.data
            current_user.apellido = form.apellido.data
            current_user.telefono = form.telefono.data
            db.session.commit()
            flash('¡Perfil actualizado con éxito! Los cambios se han guardado.', 'success')
            return redirect(url_for('perfil.editar_perfil')) 
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar los cambios: {e}', 'danger')
            return redirect(url_for('perfil.editar_perfil'))

    elif request.method == 'GET':
        form.nombre.data = current_user.nombre
        form.apellido.data = current_user.apellido
        form.telefono.data = current_user.telefono
        
        form.tipo_doc.data = current_user.tipo_doc
        form.no_identidad.data = current_user.no_identidad
        form.correo.data = current_user.correo
        form.estado_cuenta.data = current_user.estado_cuenta
        
    rol_nombre = current_user.rol_nombre 
    
    # FIX APLICADO: Usamos .strip() para eliminar espacios invisibles y .capitalize()
    rol_display = rol_nombre.strip().capitalize()
    
    form.rol.data = rol_display

    contexto = {'form': form, 'rol_usuario': rol_display}
    
    if current_user.es_profesor(): 
        stats = obtener_estadisticas_profesor_legacy(current_user.id_usuario)
        contexto.update(stats)
    else:
        contexto.update({
            'total_cursos': 0,
            'total_asignaturas': 0,
            'total_horarios': 0
        })
    
    return render_template("editar_perfil.html", **contexto)