# controllers/models.py

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from controllers.permisos import ROLE_PERMISSIONS
from datetime import datetime, time, date
import json

# ================================
# Tablas Intermedias
# ================================

asignatura_profesor = db.Table('asignatura_profesor',
    db.Column('asignatura_id', db.Integer, db.ForeignKey('asignatura.id_asignatura'), primary_key=True),
    db.Column('profesor_id', db.Integer, db.ForeignKey('usuarios.id_usuario'), primary_key=True),
    db.Column('fecha_asignacion', db.DateTime, default=datetime.utcnow)
)

estudiante_padre = db.Table('estudiante_padre',
    db.Column('estudiante_id', db.Integer, db.ForeignKey('usuarios.id_usuario'), primary_key=True),
    db.Column('padre_id', db.Integer, db.ForeignKey('usuarios.id_usuario'), primary_key=True),
    db.Column('fecha_asignacion', db.DateTime, default=datetime.utcnow)
)

# ================================
# Modelos de Autenticación y Usuarios
# ================================

class Rol(db.Model):
    __tablename__ = 'roles'
    id_rol = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.String(200))
    
    usuarios = db.relationship('Usuario', back_populates='rol')

    def __repr__(self):
        return f'<Rol {self.nombre}>'


class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    
    id_usuario = db.Column(db.Integer, primary_key=True)
    tipo_doc = db.Column(db.String(20), nullable=False)
    no_identidad = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    telefono = db.Column(db.String(20))
    direccion = db.Column(db.String(200))
    password_hash = db.Column(db.Text, nullable=False)
    id_rol_fk = db.Column(db.Integer, db.ForeignKey('roles.id_rol'), nullable=False)
    estado_cuenta = db.Column(db.Enum('activa', 'inactiva', name='estado_cuenta_enum'), nullable=False, default='activa')
    
    # Nuevos campos para verificación de email
    temp_password = db.Column(db.String(100), nullable=True)
    email_verified = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(8), nullable=True)
    verification_code_expires = db.Column(db.DateTime, nullable=True)
    verification_attempts = db.Column(db.Integer, default=0)
    last_verification_attempt = db.Column(db.DateTime, nullable=True)
    
    # Relaciones
    rol = db.relationship('Rol', back_populates='usuarios')
    asignaturas = db.relationship('Asignatura', secondary=asignatura_profesor, back_populates='profesores')
    
    # Relación estudiantes-padres
    padres = db.relationship('Usuario',
                           secondary=estudiante_padre,
                           primaryjoin='Usuario.id_usuario == estudiante_padre.c.estudiante_id',
                           secondaryjoin='Usuario.id_usuario == estudiante_padre.c.padre_id',
                           backref=db.backref('hijos', lazy='dynamic'),
                           lazy='dynamic')
    
    # Relación con matrículas
    matriculas = db.relationship('Matricula', back_populates='estudiante', foreign_keys='Matricula.estudianteId')
    
    # Relación con calificaciones
    calificaciones = db.relationship('Calificacion', back_populates='estudiante')
    
    # Relación con asistencias
    asistencias = db.relationship('Asistencia', back_populates='estudiante_rel')
    
    # Relación con horarios compartidos
    horarios_compartidos = db.relationship('HorarioCompartido', back_populates='profesor')
    
    # Relación con votos
    votos_realizados = db.relationship('Voto', back_populates='estudiante')
    
    # Relación con comunicaciones
    mensajes_enviados = db.relationship('Comunicacion', foreign_keys='Comunicacion.remitente_id', back_populates='remitente', overlaps="comunicaciones_enviadas")
    mensajes_recibidos = db.relationship('Comunicacion', foreign_keys='Comunicacion.destinatario_id', back_populates='destinatario', overlaps="comunicaciones_recibidas")
    
    # Relación con notificaciones
    notificaciones = db.relationship('Notificacion', back_populates='usuario', lazy='dynamic')

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"
    
    @property
    def rol_nombre(self):
        return self.rol.nombre if self.rol else None
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_id(self):
        return str(self.id_usuario)

    def has_role(self, role_name):
        return self.rol.nombre.lower() == role_name.lower() if self.rol else False
        
    def has_permission(self, permiso_nombre):
        if not self.rol:
            return False
        return permiso_nombre in ROLE_PERMISSIONS.get(self.rol.nombre, [])
    
    def es_estudiante(self):
        return self.has_role('estudiante')
    
    def es_profesor(self):
        return self.has_role('profesor')
    
    def es_padre(self):
        return self.has_role('padre')
    
    def es_admin(self):
        return self.has_role('super admin') or self.has_role('admin')
    
    def to_dict(self):
        return {
            'id_usuario': self.id_usuario,
            'nombre_completo': self.nombre_completo,
            'correo': self.correo,
            'telefono': self.telefono,
            'rol': self.rol_nombre,
            'estado_cuenta': self.estado_cuenta,
            'email_verified': self.email_verified
        }

    def __repr__(self):
        return f'<Usuario {self.nombre_completo} - {self.rol_nombre}>'
    
    # Relación con equipos asignados
    
    equipos_asignados = db.relationship('AsignacionEquipo', back_populates='estudiante')
    
    def get_equipos_activos(self):
        """Obtiene equipos actualmente asignados al estudiante"""
        return [asig.equipo for asig in self.equipos_asignados if asig.estado_asignacion == 'activa']

# ================================
# Modelos Académicos
# ================================

class Sede(db.Model):
    __tablename__ = 'sede'
    id_sede = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    direccion = db.Column(db.String(200), nullable=False)
    
    # Relaciones
    cursos = db.relationship('Curso', back_populates='sede')
    salones = db.relationship('Salon', back_populates='sede')
    mantenimientos = db.relationship('Mantenimiento', back_populates='sede')

    def __repr__(self):
        return f'<Sede {self.nombre}>'


class Curso(db.Model):
    __tablename__ = 'curso'
    id_curso = db.Column(db.Integer, primary_key=True)
    nombreCurso = db.Column(db.String(100), nullable=False)
    sedeId = db.Column(db.Integer, db.ForeignKey('sede.id_sede'), nullable=False)
    horario_general_id = db.Column(db.Integer, db.ForeignKey('horario_general.id_horario'))
    
    # Relaciones
    sede = db.relationship('Sede', back_populates='cursos')
    horario_general = db.relationship('HorarioGeneral', back_populates='cursos')
    matriculas = db.relationship('Matricula', back_populates='curso')
    horarios_especificos = db.relationship('HorarioCurso', back_populates='curso')
    horarios_compartidos_profesores = db.relationship('HorarioCompartido', back_populates='curso')

    def __repr__(self):
        return f'<Curso {self.nombreCurso}>'


class Matricula(db.Model):
    __tablename__ = 'matricula'
    id_matricula = db.Column(db.Integer, primary_key=True)
    estudianteId = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    cursoId = db.Column(db.Integer, db.ForeignKey('curso.id_curso'), nullable=False)
    año = db.Column(db.Integer, nullable=False)
    fecha_matricula = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    estudiante = db.relationship('Usuario', back_populates='matriculas', foreign_keys=[estudianteId])
    curso = db.relationship('Curso', back_populates='matriculas', foreign_keys=[cursoId])

    def __repr__(self):
        return f'<Matricula {self.estudianteId} - {self.cursoId}>'


class Asignatura(db.Model):
    __tablename__ = 'asignatura'
    id_asignatura = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    estado = db.Column(db.String(20), default='activa')
    
    # Relaciones
    profesores = db.relationship('Usuario', secondary=asignatura_profesor, back_populates='asignaturas')
    horarios_asignados = db.relationship('HorarioCurso', back_populates='asignatura')
    horarios_compartidos = db.relationship('HorarioCompartido', back_populates='asignatura')
    calificaciones = db.relationship('Calificacion', back_populates='asignatura')
    clases = db.relationship('Clase', back_populates='asignatura')
    solicitudes_consulta = db.relationship('SolicitudConsulta', back_populates='asignatura')

    def to_dict(self):
        return {
            "id_asignatura": self.id_asignatura, 
            "nombre": self.nombre, 
            "descripcion": self.descripcion,
            "estado": self.estado,
            "profesores": [{
                "id_usuario": prof.id_usuario,
                "nombre_completo": prof.nombre_completo,
                "correo": prof.correo
            } for prof in self.profesores]
        }

    def __repr__(self):
        return f'<Asignatura {self.nombre}>'


class Clase(db.Model):
    __tablename__ = 'clase'
    id_clase = db.Column(db.Integer, primary_key=True)
    asignaturaId = db.Column(db.Integer, db.ForeignKey('asignatura.id_asignatura'), nullable=False)
    profesorId = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    cursoId = db.Column(db.Integer, db.ForeignKey('curso.id_curso'), nullable=False)
    horarioId = db.Column(db.Integer, db.ForeignKey('horario_general.id_horario'), nullable=False)
    representanteCursoId = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'))
    
    # Relaciones
    asignatura = db.relationship('Asignatura', back_populates='clases')
    profesor = db.relationship('Usuario', foreign_keys=[profesorId])
    curso = db.relationship('Curso', foreign_keys=[cursoId])
    horario = db.relationship('HorarioGeneral', foreign_keys=[horarioId])
    representante = db.relationship('Usuario', foreign_keys=[representanteCursoId])
    asistencias = db.relationship('Asistencia', back_populates='clase')

    def __repr__(self):
        return f'<Clase {self.asignatura.nombre} - {self.curso.nombreCurso}>'


class Asistencia(db.Model):
    __tablename__ = 'asistencia'
    id_asistencia = db.Column(db.Integer, primary_key=True)
    estudianteId = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    claseId = db.Column(db.Integer, db.ForeignKey('clase.id_clase'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    estado = db.Column(db.String(20), nullable=False, default='presente')
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    excusa = db.Column(db.Boolean, default=False)  # ✅ NUEVO CAMPO AÑADIDO
    
    # Relaciones
    estudiante_rel = db.relationship('Usuario', back_populates='asistencias', foreign_keys=[estudianteId])
    clase = db.relationship('Clase', back_populates='asistencias', foreign_keys=[claseId])

    def __repr__(self):
        return f'<Asistencia {self.estudianteId} - {self.fecha}>'

# ================================
# Modelos de Calificaciones
# ================================

class ConfiguracionCalificacion(db.Model):
    __tablename__ = 'configuracion_calificacion'
    id_configuracion = db.Column(db.Integer, primary_key=True)
    asignatura_id = db.Column(db.Integer, db.ForeignKey('asignatura.id_asignatura'), nullable=True)  # NULL para configuración global
    notaMinima = db.Column(db.Numeric(5,2), nullable=False)
    notaMaxima = db.Column(db.Numeric(5,2), nullable=False)
    notaMinimaAprobacion = db.Column(db.Numeric(5,2), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    asignatura = db.relationship('Asignatura', foreign_keys=[asignatura_id])

    def __repr__(self):
        return f'<ConfiguracionCalificacion {self.notaMinimaAprobacion}>'


class CategoriaCalificacion(db.Model):
    __tablename__ = 'categoria_calificacion'
    id_categoria = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(20), nullable=False)
    porcentaje = db.Column(db.Numeric(5,2), nullable=False)
    
    # Relaciones
    calificaciones = db.relationship('Calificacion', back_populates='categoria')

    def __repr__(self):
        return f'<CategoriaCalificacion {self.nombre}>'


class Calificacion(db.Model):
    __tablename__ = 'calificacion'
    id_calificacion = db.Column(db.Integer, primary_key=True)
    estudianteId = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    asignaturaId = db.Column(db.Integer, db.ForeignKey('asignatura.id_asignatura'), nullable=False)
    categoriaId = db.Column(db.Integer, db.ForeignKey('categoria_calificacion.id_categoria'), nullable=False)
    # Allow null initially (assignments may be created before grades are entered)
    valor = db.Column(db.Numeric(5,2), nullable=True)
    # Nombre libre para identificar la calificación / asignación (por ejemplo: 'Parcial 1')
    nombre_calificacion = db.Column(db.String(200), nullable=True)
    observaciones = db.Column(db.Text)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    estudiante = db.relationship('Usuario', back_populates='calificaciones', foreign_keys=[estudianteId])
    asignatura = db.relationship('Asignatura', back_populates='calificaciones', foreign_keys=[asignaturaId])
    categoria = db.relationship('CategoriaCalificacion', back_populates='calificaciones', foreign_keys=[categoriaId])

    def __repr__(self):
        return f'<Calificacion {self.estudianteId} - {self.valor}>'

# ================================
# Modelos de Horarios
# ================================

class HorarioGeneral(db.Model):
    __tablename__ = 'horario_general'
    id_horario = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    periodo = db.Column(db.String(50), nullable=False, default='Primer Semestre')
    horaInicio = db.Column(db.Time, nullable=False)
    horaFin = db.Column(db.Time, nullable=False)
    diasSemana = db.Column(db.Text, nullable=False)
    duracion_clase = db.Column(db.Integer, default=45)
    duracion_descanso = db.Column(db.Integer, default=15)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    cursos = db.relationship('Curso', back_populates='horario_general')
    bloques = db.relationship('BloqueHorario', back_populates='horario_general', cascade='all, delete-orphan')
    horarios_cursos = db.relationship('HorarioCurso', back_populates='horario_general')
    horarios_compartidos = db.relationship('HorarioCompartido', back_populates='horario_general')
    
    def to_dict(self):
        try:
            dias_lista = json.loads(self.diasSemana) if self.diasSemana else []
        except:
            dias_lista = []
            
        return {
            "id_horario": self.id_horario,
            "nombre": self.nombre,
            "periodo": self.periodo,
            "horaInicio": self.horaInicio.strftime("%H:%M") if self.horaInicio else "07:00",
            "horaFin": self.horaFin.strftime("%H:%M") if self.horaFin else "17:00",
            "dias": dias_lista,
            "diasSemana": ", ".join(dias_lista) if dias_lista else "",
            "duracion_clase": self.duracion_clase,
            "duracion_descanso": self.duracion_descanso,
            "activo": self.activo,
            "totalCursos": len(self.cursos)  
        }
    
    def get_bloques(self):
        return BloqueHorario.query.filter_by(horario_general_id=self.id_horario).order_by(BloqueHorario.orden).all()

    def __repr__(self):
        return f'<HorarioGeneral {self.nombre}>'


class BloqueHorario(db.Model):
    __tablename__ = 'bloque_horario'
    id_bloque = db.Column(db.Integer, primary_key=True)
    horario_general_id = db.Column(db.Integer, db.ForeignKey('horario_general.id_horario'), nullable=False)
    dia_semana = db.Column(db.String(20), nullable=False)
    horaInicio = db.Column(db.Time, nullable=False)
    horaFin = db.Column(db.Time, nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    orden = db.Column(db.Integer, nullable=False)
    nombre = db.Column(db.String(100))
    class_type = db.Column(db.String(20))
    break_type = db.Column(db.String(20))
    
    # Relaciones
    horario_general = db.relationship('HorarioGeneral', back_populates='bloques')
    
    def to_dict(self):
        return {
            "id_bloque": self.id_bloque,
            "day": self.dia_semana,
            "start": self.horaInicio.strftime("%H:%M"),
            "end": self.horaFin.strftime("%H:%M"),
            "type": self.tipo,
            "nombre": self.nombre,
            "orden": self.orden,
            "classType": self.class_type,
            "breakType": self.break_type
        }

    def __repr__(self):
        return f'<BloqueHorario {self.dia_semana} {self.horaInicio}-{self.horaFin}>'


class HorarioCurso(db.Model):
    __tablename__ = 'horario_curso'
    
    id_horario_curso = db.Column(db.Integer, primary_key=True)
    curso_id = db.Column(db.Integer, db.ForeignKey('curso.id_curso'), nullable=False)
    asignatura_id = db.Column(db.Integer, db.ForeignKey('asignatura.id_asignatura'), nullable=False)
    dia_semana = db.Column(db.String(20), nullable=False)
    hora_inicio = db.Column(db.String(5), nullable=False)
    hora_fin = db.Column(db.String(5), nullable=False)  # ✅ YA ESTÁ DEFINIDO CORRECTAMENTE
    horario_general_id = db.Column(db.Integer, db.ForeignKey('horario_general.id_horario'))
    id_salon_fk = db.Column(db.Integer, db.ForeignKey('salones.id_salon'), nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    curso = db.relationship('Curso', back_populates='horarios_especificos')
    asignatura = db.relationship('Asignatura', back_populates='horarios_asignados')
    horario_general = db.relationship('HorarioGeneral', back_populates='horarios_cursos')
    salon = db.relationship('Salon', back_populates='horarios_asignados')
    
    def to_dict(self):
        return {
            'id_horario_curso': self.id_horario_curso,
            'curso_id': self.curso_id,
            'asignatura_id': self.asignatura_id,
            'dia_semana': self.dia_semana,
            'hora_inicio': self.hora_inicio,
            'hora_fin': self.hora_fin,  # ✅ INCLUIR HORA_FIN
            'horario_general_id': self.horario_general_id,
            'id_salon_fk': self.id_salon_fk,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None
        }
    
    def __repr__(self):
        return f'<HorarioCurso {self.curso_id} - {self.asignatura_id}>'


class HorarioCompartido(db.Model):
    __tablename__ = 'horario_compartido'
    
    id_horario_compartido = db.Column(db.Integer, primary_key=True)
    profesor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    curso_id = db.Column(db.Integer, db.ForeignKey('curso.id_curso'), nullable=False)
    asignatura_id = db.Column(db.Integer, db.ForeignKey('asignatura.id_asignatura'), nullable=False)
    horario_general_id = db.Column(db.Integer, db.ForeignKey('horario_general.id_horario'))
    fecha_compartido = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    profesor = db.relationship('Usuario', back_populates='horarios_compartidos')
    curso = db.relationship('Curso', back_populates='horarios_compartidos_profesores')
    asignatura = db.relationship('Asignatura', back_populates='horarios_compartidos')
    horario_general = db.relationship('HorarioGeneral', back_populates='horarios_compartidos')

    def __repr__(self):
        return f'<HorarioCompartido {self.profesor_id} - {self.curso_id}>'

# ================================
# Modelos de Infraestructura
# ================================

class Salon(db.Model):
    __tablename__ = 'salones' 
    id_salon = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    tipo = db.Column(db.String(50), nullable=False)
    capacidad = db.Column(db.Integer, nullable=False)
    cantidad_sillas = db.Column(db.Integer, nullable=True)
    cantidad_mesas = db.Column(db.Integer, nullable=True)
    id_sede_fk = db.Column(db.Integer, db.ForeignKey('sede.id_sede'), nullable=False)
    estado = db.Column(db.String(20), default='disponible')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    sede = db.relationship('Sede', back_populates='salones')
    equipos = db.relationship('Equipo', back_populates='salon')
    horarios_asignados = db.relationship('HorarioCurso', back_populates='salon')

    def to_dict(self):
        return {
            "id_salon": self.id_salon,
            "nombre": self.nombre,
            "tipo": self.tipo,
            "capacidad": self.capacidad,
            "id_sede_fk": self.id_sede_fk,
            "sede_nombre": self.sede.nombre if self.sede else "Sin Sede",
            "equipos_count": len(self.equipos),
            "cantidad_sillas": self.cantidad_sillas or 0,
            "cantidad_mesas": self.cantidad_mesas or 0,
            "estado": self.estado
        }
    
    def __repr__(self):
        return f"<Salon {self.nombre} - {self.tipo}>"


class Equipo(db.Model):
    __tablename__ = 'equipos'
    id_equipo = db.Column(db.Integer, primary_key=True)
    id_referencia = db.Column(db.String(50), unique=True)
    nombre = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.Enum('Disponible', 'Mantenimiento', 'Asignado', 'Incidente', name='estado_equipo_enum'), 
                      nullable=False, default='Disponible')
    id_salon_fk = db.Column(db.Integer, db.ForeignKey('salones.id_salon'), nullable=False)
    sistema_operativo = db.Column(db.String(100))
    ram = db.Column(db.String(50))
    disco_duro = db.Column(db.String(100))
    fecha_adquisicion = db.Column(db.Date)
    descripcion = db.Column(db.Text)
    observaciones = db.Column(db.Text)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    salon = db.relationship('Salon', back_populates='equipos')
    asignaciones = db.relationship('AsignacionEquipo', back_populates='equipo', cascade='all, delete-orphan')
    incidentes = db.relationship('Incidente', back_populates='equipo')
    programaciones = db.relationship('Mantenimiento', back_populates='equipo')
    
    def get_asignaciones_activas(self):
        """Obtiene todas las asignaciones activas del equipo"""
        return [asig for asig in self.asignaciones if asig.estado_asignacion == 'activa']
    
    def get_estudiantes_asignados(self):
        """Obtiene lista de estudiantes con asignaciones activas"""
        return [asig.estudiante for asig in self.get_asignaciones_activas()]
    
    def get_cursos_asignados(self):
        """Obtiene lista de cursos de los estudiantes asignados"""
        cursos = set()
        for asignacion in self.get_asignaciones_activas():
            curso = asignacion.get_curso_estudiante()
            if curso:
                cursos.add(curso)
        return list(cursos)
    
    def puede_asignar_a_curso(self, curso_id):
        """Verifica si se puede asignar a un estudiante de este curso"""
        # Obtener cursos ya asignados
        for asignacion in self.get_asignaciones_activas():
            matricula = Matricula.query.filter_by(
                estudianteId=asignacion.estudiante_id
            ).order_by(Matricula.año.desc()).first()
            
            if matricula and matricula.cursoId == curso_id:
                return False  # Ya hay un estudiante de este curso
        
        return True
    
    def to_dict(self):
        asignaciones_activas = self.get_asignaciones_activas()
        estudiantes_nombres = [asig.estudiante.nombre_completo for asig in asignaciones_activas if asig.estudiante]
        
        return {
            "id_equipo": self.id_equipo,
            "id_referencia": self.id_referencia,
            "nombre": self.nombre,
            "tipo": self.tipo,
            "estado": self.estado,
            "sistema_operativo": self.sistema_operativo,
            "ram": self.ram,
            "disco_duro": self.disco_duro,
            "descripcion": self.descripcion,
            "observaciones": self.observaciones,
            "fecha_adquisicion": self.fecha_adquisicion.strftime("%Y-%m-%d") if self.fecha_adquisicion else "",
            "id_salon_fk": self.id_salon_fk,
            "salon": self.salon.nombre if self.salon else "Sin Salón Asignado",
            "sede_nombre": self.salon.sede.nombre if self.salon and self.salon.sede else "Sin Sede",
            "sede_id": self.salon.id_sede_fk if self.salon else None,
            "total_asignaciones": len(asignaciones_activas),
            "estudiantes_asignados": estudiantes_nombres,
            "asignado_a": ", ".join(estudiantes_nombres) if estudiantes_nombres else "N/A",
            "cursos_asignados": self.get_cursos_asignados()
        }

    def __repr__(self):
        return f"<Equipo {self.nombre} - {self.estado}>"

class AsignacionEquipo(db.Model):
    """Tabla intermedia para asignar equipos a múltiples estudiantes"""
    __tablename__ = 'asignaciones_equipos'
    
    id_asignacion = db.Column(db.Integer, primary_key=True)
    equipo_id = db.Column(db.Integer, db.ForeignKey('equipos.id_equipo'), nullable=False)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    fecha_asignacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_devolucion = db.Column(db.DateTime, nullable=True)
    estado_asignacion = db.Column(db.String(20), default='activa')  # activa, devuelto, perdido
    observaciones = db.Column(db.Text, nullable=True)
    
    # Relaciones
    equipo = db.relationship('Equipo', back_populates='asignaciones')
    estudiante = db.relationship('Usuario', back_populates='equipos_asignados')
    
    # Constraint única: un estudiante no puede tener el mismo equipo asignado dos veces activamente
    __table_args__ = (
        db.UniqueConstraint('equipo_id', 'estudiante_id', 'estado_asignacion', 
                          name='uq_equipo_estudiante_activo'),
    )
    
    def to_dict(self):
        return {
            'id_asignacion': self.id_asignacion,
            'equipo_id': self.equipo_id,
            'equipo_nombre': self.equipo.nombre if self.equipo else None,
            'estudiante_id': self.estudiante_id,
            'estudiante_nombre': self.estudiante.nombre_completo if self.estudiante else None,
            'estudiante_curso': self.get_curso_estudiante(),
            'fecha_asignacion': self.fecha_asignacion.strftime('%Y-%m-%d %H:%M') if self.fecha_asignacion else None,
            'fecha_devolucion': self.fecha_devolucion.strftime('%Y-%m-%d %H:%M') if self.fecha_devolucion else None,
            'estado_asignacion': self.estado_asignacion,
            'observaciones': self.observaciones
        }
    
    def get_curso_estudiante(self):
        """Obtiene el curso actual del estudiante"""
        if not self.estudiante:
            return None
        
        matricula = Matricula.query.filter_by(
            estudianteId=self.estudiante_id
        ).order_by(Matricula.año.desc()).first()
        
        if matricula and matricula.curso:
            return matricula.curso.nombreCurso
        return None
    
    def __repr__(self):
        return f'<AsignacionEquipo {self.equipo_id} -> {self.estudiante_id}>'


class Incidente(db.Model):
    __tablename__ = 'incidentes'
    id_incidente = db.Column(db.Integer, primary_key=True)
    equipo_id = db.Column(db.Integer, db.ForeignKey('equipos.id_equipo'), nullable=False)
    usuario_asignado = db.Column(db.String(100), nullable=True)
    sede = db.Column(db.String(100), nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    descripcion = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String(50), nullable=True, default='reportado')
    prioridad = db.Column(db.String(20), nullable=False, default='media')
    solucion_propuesta = db.Column(db.Text, nullable=True)
    fecha_solucion = db.Column(db.DateTime, nullable=True)
    
    # Relaciones
    equipo = db.relationship('Equipo', back_populates='incidentes')

    def to_dict(self):
        return {
            "id_incidente": self.id_incidente,
            "equipo_id": self.equipo_id,
            "equipo_nombre": self.equipo.nombre if self.equipo else "",
            "usuario_reporte": self.usuario_asignado or "",
            "sede": self.sede,
            "fecha": self.fecha.strftime("%Y-%m-%d %H:%M"),
            "descripcion": self.descripcion,
            "estado": self.estado or "reportado",
            "prioridad": self.prioridad or "media",
            "solucion_propuesta": self.solucion_propuesta or "",
            "fecha_solucion": self.fecha_solucion.strftime("%Y-%m-%d %H:%M") if self.fecha_solucion else ""
        }

    def __repr__(self):
        return f"<Incidente {self.id_incidente} - {self.equipo.nombre}>"


class Mantenimiento(db.Model):
    __tablename__ = 'mantenimiento'
    id_mantenimiento = db.Column(db.Integer, primary_key=True)
    equipo_id = db.Column(db.Integer, db.ForeignKey('equipos.id_equipo'), nullable=False)
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id_sede'), nullable=False)
    fecha_programada = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    estado = db.Column(db.String(50), default='pendiente')
    descripcion = db.Column(db.Text, nullable=True)
    fecha_realizada = db.Column(db.Date, nullable=True)
    tecnico = db.Column(db.String(100), nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    equipo = db.relationship('Equipo', back_populates='programaciones')
    sede = db.relationship('Sede', back_populates='mantenimientos')


    def to_dict(self):
        salon_nombre = self.equipo.salon.nombre if self.equipo and self.equipo.salon else "N/A"
        
        return {
            "id_mantenimiento": self.id_mantenimiento,
            "equipo_id": self.equipo_id,
            "equipo_nombre": self.equipo.nombre if self.equipo else "",
            "sede_id": self.sede_id,
            "sede": self.sede.nombre if self.sede else "",
            "salon_nombre": salon_nombre,
            "fecha_programada": self.fecha_programada.strftime("%Y-%m-%d"),
            "tipo": self.tipo,
            "estado": self.estado,
            "descripcion": self.descripcion or "",
            "fecha_realizada": self.fecha_realizada.strftime("%Y-%m-%d") if self.fecha_realizada else None,
            "tecnico": self.tecnico or ""
        }
        
#==========================================================================================================#
#Eventos y votaciones
#==========================================================================================================#

# ================================
# Modelos de Eventos y Comunicaciones
# ================================

class Evento(db.Model):
    __tablename__ = "eventos"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    hora = db.Column(db.Time, nullable=False)
    rol_destino = db.Column(db.String(50), nullable=False)

    def to_dict(self):
        return {
            "IdEvento": self.id,
            "Nombre": self.nombre,
            "Descripcion": self.descripcion,
            "Fecha": self.fecha.isoformat(),
            "Hora": self.hora.strftime("%H:%M"),
            "RolDestino": self.rol_destino
        }

    def __repr__(self):
        return f"<Evento {self.nombre}>"



class Comunicacion(db.Model):
    __tablename__ = 'comunicaciones'
    
    id_comunicacion = db.Column(db.Integer, primary_key=True)
    remitente_id = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    destinatario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    asunto = db.Column(db.String(200))
    mensaje = db.Column(db.Text)
    fecha_envio = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(20), default='inbox')  # inbox, sent, draft, deleted
    grupo_id = db.Column(db.String(100), nullable=True)  # Para agrupar comunicados como Gmail
    
    # Relaciones
    remitente = db.relationship('Usuario', foreign_keys=[remitente_id], backref='comunicaciones_enviadas')
    destinatario = db.relationship('Usuario', foreign_keys=[destinatario_id], backref='comunicaciones_recibidas')
    
    def to_dict(self):
        return {
            'id_comunicacion': self.id_comunicacion,
            'remitente_id': self.remitente_id,
            'remitente_nombre': self.remitente.nombre,
            'destinatario_id': self.destinatario_id,
            'destinatario_nombre': self.destinatario.nombre,
            'asunto': self.asunto,
            'mensaje': self.mensaje,
            'fecha_envio': self.fecha_envio.isoformat(),
            'estado': self.estado,
        }


# ================================
# Modelos de Votaciones
# ================================

class Candidato(db.Model):
    __tablename__ = "candidatos"
    id_candidato = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    tarjeton = db.Column(db.String(20), unique=True, nullable=False)
    propuesta = db.Column(db.Text, nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    foto = db.Column(db.String(200), nullable=False)
    votos = db.Column(db.Integer, default=0)
    activo = db.Column(db.Boolean, default=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    votos_registrados = db.relationship("Voto", back_populates="candidato")

    def to_dict(self):
        return {
            "id_candidato": self.id_candidato,
            "nombre": self.nombre,
            "tarjeton": self.tarjeton,
            "propuesta": self.propuesta,
            "categoria": self.categoria,
            "foto": self.foto,
            "votos": self.votos,
            "activo": self.activo
        }

    def __repr__(self):
        return f"<Candidato {self.nombre}>"


class Voto(db.Model):
    __tablename__ = "votos"
    id_voto = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False)
    candidato_id = db.Column(db.Integer, db.ForeignKey("candidatos.id_candidato"), nullable=False)
    fecha_voto = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))
    
    # Relaciones
    estudiante = db.relationship("Usuario", back_populates="votos_realizados")
    candidato = db.relationship("Candidato", back_populates="votos_registrados")

    def __repr__(self):
        return f"<Voto {self.estudiante_id} - {self.candidato_id}>"


class HorarioVotacion(db.Model):
    __tablename__ = "horarios_votacion"
    id_horario_votacion = db.Column(db.Integer, primary_key=True)
    inicio = db.Column(db.Time, nullable=False)
    fin = db.Column(db.Time, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            "id_horario_votacion": self.id_horario_votacion,
            "inicio": self.inicio.strftime("%H:%M"),
            "fin": self.fin.strftime("%H:%M"),
            "activo": self.activo
        }

    def __repr__(self):
        return f"<HorarioVotacion {self.inicio}-{self.fin}>"


# ================================
# Modelo de Reportes de Calificaciones
# ================================

class ReporteCalificaciones(db.Model):
    __tablename__ = "reportes_calificaciones"
    
    id_reporte = db.Column(db.Integer, primary_key=True)
    profesor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False)
    curso_id = db.Column(db.Integer, db.ForeignKey("curso.id_curso"), nullable=False)
    asignatura_id = db.Column(db.Integer, db.ForeignKey("asignatura.id_asignatura"), nullable=False)
    nombre_curso = db.Column(db.String(100), nullable=False)
    nombre_asignatura = db.Column(db.String(100), nullable=False)
    datos_estudiantes = db.Column(db.JSON, nullable=False)  # JSON con nombres y promedios
    promedio_general = db.Column(db.Float, nullable=False)
    nota_mas_alta = db.Column(db.Float, nullable=False)
    nota_mas_baja = db.Column(db.Float, nullable=False)
    fecha_generacion = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, revisado, archivado
    
    # Relaciones
    profesor = db.relationship("Usuario", foreign_keys=[profesor_id])
    curso = db.relationship("Curso", foreign_keys=[curso_id])
    asignatura = db.relationship("Asignatura", foreign_keys=[asignatura_id])
    
    def to_dict(self):
        return {
            "id_reporte": self.id_reporte,
            "profesor_nombre": self.profesor.nombre_completo if self.profesor else "Desconocido",
            "curso_nombre": self.nombre_curso,
            "asignatura_nombre": self.nombre_asignatura,
            "datos_estudiantes": self.datos_estudiantes,
            "promedio_general": self.promedio_general,
            "nota_mas_alta": self.nota_mas_alta,
            "nota_mas_baja": self.nota_mas_baja,
            "fecha_generacion": self.fecha_generacion.strftime("%Y-%m-%d %H:%M") if self.fecha_generacion else "",
            "estado": self.estado
        }
    
    def __repr__(self):
        return f"<ReporteCalificaciones {self.nombre_curso} - {self.nombre_asignatura}>"


# ================================
# Modelo de Solicitudes de Consulta
# ================================

class SolicitudConsulta(db.Model):
    __tablename__ = "solicitudes_consulta"
    
    id_solicitud = db.Column(db.Integer, primary_key=True)
    padre_id = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False)
    estudiante_id = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False)
    asignatura_id = db.Column(db.Integer, db.ForeignKey("asignatura.id_asignatura"), nullable=False)
    profesor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False)
    numero_documento_hijo = db.Column(db.String(20), nullable=False)
    nombre_completo_hijo = db.Column(db.String(200), nullable=False)
    justificacion = db.Column(db.Text, nullable=False)
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, aceptada, denegada
    respuesta_profesor = db.Column(db.Text, nullable=True)
    fecha_respuesta = db.Column(db.DateTime, nullable=True)
    
    # Relaciones
    padre = db.relationship("Usuario", foreign_keys=[padre_id], backref='solicitudes_enviadas')
    estudiante = db.relationship("Usuario", foreign_keys=[estudiante_id], backref='solicitudes_recibidas')
    asignatura = db.relationship("Asignatura", back_populates='solicitudes_consulta')
    profesor = db.relationship("Usuario", foreign_keys=[profesor_id], backref='solicitudes_profesor')
    
    def to_dict(self):
        return {
            "id_solicitud": self.id_solicitud,
            "padre_nombre": self.padre.nombre_completo if self.padre else "Desconocido",
            "estudiante_nombre": self.estudiante.nombre_completo if self.estudiante else "Desconocido",
            "asignatura_nombre": self.asignatura.nombre if self.asignatura else "Desconocida",
            "profesor_nombre": self.profesor.nombre_completo if self.profesor else "Desconocido",
            "numero_documento_hijo": self.numero_documento_hijo,
            "nombre_completo_hijo": self.nombre_completo_hijo,
            "justificacion": self.justificacion,
            "fecha_solicitud": self.fecha_solicitud.strftime("%Y-%m-%d %H:%M") if self.fecha_solicitud else "",
            "estado": self.estado,
            "respuesta_profesor": self.respuesta_profesor,
            "fecha_respuesta": self.fecha_respuesta.strftime("%Y-%m-%d %H:%M") if self.fecha_respuesta else None
        }
    
    def __repr__(self):
        return f"<SolicitudConsulta {self.id_solicitud} - {self.estado}>"


# ================================
# Modelo de Notificaciones
# ================================

class Notificacion(db.Model):
    __tablename__ = "notificaciones"
    
    id_notificacion = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # comunicacion, calificacion, asistencia, solicitud, etc.
    link = db.Column(db.String(500), nullable=True)
    leida = db.Column(db.Boolean, default=False)
    creada_en = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    usuario = db.relationship("Usuario", back_populates="notificaciones")
    
    def to_dict(self):
        return {
            "id_notificacion": self.id_notificacion,
            "titulo": self.titulo,
            "mensaje": self.mensaje,
            "tipo": self.tipo,
            "link": self.link,
            "leida": self.leida,
            "creada_en": self.creada_en.isoformat() if self.creada_en else None
        }
    
    def __repr__(self):
        return f"<Notificacion {self.id_notificacion} - {self.titulo}>"