from flask import Blueprint, render_template, jsonify, request
from datetime import date
from controllers.models import db, Usuario, Rol, Sede, Curso, Evento

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

# API pública: resumen de cifras para la portada
@main_bp.route('/api/public/resumen')
def api_public_resumen():
    try:
        total_sedes = Sede.query.count()
        total_cursos = Curso.query.count()
        rol_docente = Rol.query.filter_by(nombre='Profesor').first()
        rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()
        total_docentes = Usuario.query.filter_by(id_rol_fk=rol_docente.id_rol).count() if rol_docente else 0
        total_estudiantes = Usuario.query.filter_by(id_rol_fk=rol_estudiante.id_rol).count() if rol_estudiante else 0
        eventos_hoy_en_adelante = Evento.query.filter(Evento.fecha >= date.today()).count()
        return jsonify({
            'success': True,
            'data': {
                'sedes': total_sedes,
                'cursos': total_cursos,
                'docentes': total_docentes,
                'estudiantes': total_estudiantes,
                'eventos': eventos_hoy_en_adelante
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# API pública: listado breve de cursos
@main_bp.route('/api/public/cursos')
def api_public_cursos():
    try:
        limit = max(1, min(int(request.args.get('limit', 10)), 30))
        cursos = Curso.query.limit(limit).all()
        data = [{
            'id': c.id_curso,
            'nombre': c.nombreCurso,
            'sede': getattr(c.sede, 'nombre', 'Sede') if hasattr(c, 'sede') else None
        } for c in cursos]
        return jsonify({'success': True, 'cursos': data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# API pública: próximos eventos
@main_bp.route('/api/public/eventos')
def api_public_eventos():
    try:
        limit = max(1, min(int(request.args.get('limit', 5)), 20))
        desde = request.args.get('desde')
        q = Evento.query
        if desde:
            try:
                from datetime import datetime
                d = datetime.strptime(desde, '%Y-%m-%d').date()
            except Exception:
                d = date.today()
        else:
            d = date.today()
        q = q.filter(Evento.fecha >= d).order_by(Evento.fecha.asc())
        eventos = q.limit(limit).all()
        data = [{
            'id': e.id_evento if hasattr(e, 'id_evento') else getattr(e, 'id', None),
            'nombre': e.nombre,
            'descripcion': e.descripcion,
            'fecha': e.fecha.strftime('%Y-%m-%d') if getattr(e, 'fecha', None) else None,
            'hora': e.hora.strftime('%H:%M') if getattr(e, 'hora', None) else None,
            'rol_destino': getattr(e, 'rol_destino', None)
        } for e in eventos]
        return jsonify({'success': True, 'eventos': data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# API pública: contacto (simple logging/persistencia ligera)
@main_bp.route('/api/public/contacto', methods=['POST'])
def api_public_contacto():
    try:
        data = request.get_json(silent=True) or {}
        nombre = (data.get('name') or '').strip()
        correo = (data.get('email') or '').strip()
        mensaje = (data.get('message') or '').strip()
        if not nombre or not correo or not mensaje:
            return jsonify({'success': False, 'message': 'Campos incompletos'}), 400
        # Opcional: guardar como Notificacion o Evento; por simplicidad, registrar en logs
        current = {'nombre': nombre, 'correo': correo, 'mensaje': mensaje}
        try:
            print('[Contacto público]', current)
        except Exception:
            pass
        return jsonify({'success': True, 'message': 'Mensaje recibido. ¡Gracias por contactarnos!'}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500