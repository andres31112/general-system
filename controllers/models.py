from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from controllers.permisos import ROLE_PERMISSIONS
from datetime import time
from datetime import datetime
import json

# Tabla intermedia para relación muchos a muchos entre asignaturas y profesores
asignatura_profesor = db.Table('asignatura_profesor',
    db.Column('asignatura_id', db.Integer, db.ForeignKey('asignatura.id'), primary_key=True),
    db.Column('profesor_id', db.Integer, db.ForeignKey('usuarios.id_usuario'), primary_key=True),
    db.Column('fecha_asignacion', db.DateTime, default=datetime.utcnow)
)

# Roles
class Rol(db.Model):
    __tablename__ = 'roles'
    id_rol = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.String(200))
    
    usuarios = db.relationship('Usuario', back_populates='rol')

# Usuarios
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
    
    rol = db.relationship('Rol', back_populates='usuarios')
    asignaturas = db.relationship('Asignatura', secondary=asignatura_profesor, back_populates='profesores')

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"
    
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

# Académico
class Sede(db.Model):
    __tablename__ = 'sede'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    direccion = db.Column(db.String(200), nullable=False)

class Curso(db.Model):
    __tablename__ = 'curso'
    id = db.Column(db.Integer, primary_key=True)
    nombreCurso = db.Column(db.String(100), nullable=False)
    sedeId = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=False)
    horario_general_id = db.Column(db.Integer, db.ForeignKey('horario_general.id'))
    
    sede = db.relationship('Sede', backref=db.backref('cursos', lazy=True))
    horario_general = db.relationship('HorarioGeneral', backref=db.backref('cursos_rel', lazy=True))
    
class Matricula(db.Model):
    __tablename__ = 'matricula'
    id = db.Column(db.Integer, primary_key=True)
    estudianteId = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    cursoId = db.Column(db.Integer, db.ForeignKey('curso.id'), nullable=False)
    año = db.Column(db.Integer, nullable=False)

class Asignatura(db.Model):
    __tablename__ = 'asignatura'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    estado = db.Column(db.String(20), default='activa')
    
    profesores = db.relationship('Usuario', secondary=asignatura_profesor, back_populates='asignaturas')
    
    def to_dict(self):
        return {
            "id": self.id, 
            "nombre": self.nombre, 
            "descripcion": self.descripcion,
            "estado": self.estado,
            "profesores": [{
                "id_usuario": prof.id_usuario,
                "nombre_completo": prof.nombre_completo,
                "correo": prof.correo
            } for prof in self.profesores]
        }

class Clase(db.Model):
    __tablename__ = 'clase'
    id = db.Column(db.Integer, primary_key=True)
    asignaturaId = db.Column(db.Integer, db.ForeignKey('asignatura.id'), nullable=False)
    profesorId = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    cursoId = db.Column(db.Integer, db.ForeignKey('curso.id'), nullable=False)
    horarioId = db.Column(db.Integer, db.ForeignKey('horario_general.id'), nullable=False)
    representanteCursoId = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'))

# Sistema de Horarios
class HorarioGeneral(db.Model):
    __tablename__ = 'horario_general'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    periodo = db.Column(db.String(50), nullable=False, default='Primer Semestre')
    horaInicio = db.Column(db.Time, nullable=False)
    horaFin = db.Column(db.Time, nullable=False)
    diasSemana = db.Column(db.Text, nullable=False)
    duracion_clase = db.Column(db.Integer, default=45)
    duracion_descanso = db.Column(db.Integer, default=15)
    activo = db.Column(db.Boolean, default=True)
    
    cursos = db.relationship('Curso', backref='horario_general_rel', lazy=True)
    
    def to_dict(self):
        try:
            dias_lista = json.loads(self.diasSemana) if self.diasSemana else []
        except:
            dias_lista = []
            
        return {
            "id": self.id,
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
        return BloqueHorario.query.filter_by(horario_general_id=self.id).order_by(BloqueHorario.orden).all()

class BloqueHorario(db.Model):
    __tablename__ = 'bloque_horario'
    id = db.Column(db.Integer, primary_key=True)
    horario_general_id = db.Column(db.Integer, db.ForeignKey('horario_general.id'), nullable=False)
    dia_semana = db.Column(db.String(20), nullable=False)
    horaInicio = db.Column(db.Time, nullable=False)
    horaFin = db.Column(db.Time, nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    orden = db.Column(db.Integer, nullable=False)
    nombre = db.Column(db.String(100))
    class_type = db.Column(db.String(20))
    break_type = db.Column(db.String(20))
    
    horario_general = db.relationship('HorarioGeneral', backref=db.backref('bloques', lazy=True, cascade='all, delete-orphan'))
    
    def to_dict(self):
        return {
            "id": self.id,
            "day": self.dia_semana,
            "start": self.horaInicio.strftime("%H:%M"),
            "end": self.horaFin.strftime("%H:%M"),
            "type": self.tipo,
            "nombre": self.nombre,
            "orden": self.orden,
            "classType": self.class_type,
            "breakType": self.break_type
        }

class HorarioCurso(db.Model):
    __tablename__ = 'horario_curso'
    
    id = db.Column(db.Integer, primary_key=True)
    curso_id = db.Column(db.Integer, db.ForeignKey('curso.id'), nullable=False)
    asignatura_id = db.Column(db.Integer, db.ForeignKey('asignatura.id'), nullable=False)
    dia_semana = db.Column(db.String(20), nullable=False)
    hora_inicio = db.Column(db.String(5), nullable=False)
    horario_general_id = db.Column(db.Integer, db.ForeignKey('horario_general.id'))
    
    curso = db.relationship('Curso', backref='horarios_especificos')
    asignatura = db.relationship('Asignatura', backref='horarios_asignados')
    horario_general = db.relationship('HorarioGeneral', backref='horarios_cursos')
    
    def __repr__(self):
        return f'<HorarioCurso {self.curso_id} - {self.asignatura_id}>'

class Asistencia(db.Model):
    __tablename__ = 'asistencia'
    id = db.Column(db.Integer, primary_key=True)
    estudianteId = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    claseId = db.Column(db.Integer, db.ForeignKey('clase.id'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    estado = db.Column(db.String(20), nullable=False, default='presente')

class ConfiguracionCalificacion(db.Model):
    __tablename__ = 'configuracion_calificacion'
    id = db.Column(db.Integer, primary_key=True)
    notaMinima = db.Column(db.Numeric(5,2), nullable=False)
    notaMaxima = db.Column(db.Numeric(5,2), nullable=False)
    notaMinimaAprobacion = db.Column(db.Numeric(5,2), nullable=False)

class CategoriaCalificacion(db.Model):
    __tablename__ = 'categoria_calificacion'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(20), nullable=False)
    porcentaje = db.Column(db.Numeric(5,2), nullable=False)

class Calificacion(db.Model):
    __tablename__ = 'calificacion'
    id = db.Column(db.Integer, primary_key=True)
    estudianteId = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    asignaturaId = db.Column(db.Integer, db.ForeignKey('asignatura.id'), nullable=False)
    categoriaId = db.Column(db.Integer, db.ForeignKey('categoria_calificacion.id'), nullable=False)
    valor = db.Column(db.Numeric(5,2), nullable=False)
    observaciones = db.Column(db.Text)

class Salon(db.Model):
    __tablename__ = 'salones'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    tipo = db.Column(db.String(50), nullable=False)
    capacidad = db.Column(db.Integer, nullable=True, default=0)
    cantidad_sillas = db.Column(db.Integer, nullable=True)
    cantidad_mesas = db.Column(db.Integer, nullable=True)
    id_sede_fk = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=False)
    sede = db.relationship('Sede', backref=db.backref('salones', lazy=True))

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "tipo": self.tipo,
            "capacidad": self.capacidad,
            "id_sede_fk": self.id_sede_fk,
            "sede_nombre": self.sede.nombre if self.sede else "Sin Sede",
            "equipos_count": Equipo.query.filter_by(id_salon_fk=self.id).count(),
            "cantidad_sillas": self.cantidad_sillas or 0,
            "cantidad_mesas": self.cantidad_mesas or 0
        }
    
    def __repr__(self):
        return f"Salon('{self.nombre}', '{self.tipo}')"

class Equipo(db.Model):
    __tablename__ = 'equipos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.Enum('Disponible', 'Mantenimiento', 'Asignado', 'Incidente', 'Revisión', name='estado_equipo_enum'), nullable=False, default='Disponible')
    id_salon_fk = db.Column(db.Integer, db.ForeignKey('salones.id'), nullable=False)
    asignado_a = db.Column(db.String(100))
    id_referencia = db.Column(db.String(50))
    tipo = db.Column(db.String(100))
    sistema_operativo = db.Column(db.String(100))
    ram = db.Column(db.String(50))
    disco_duro = db.Column(db.String(100))
    fecha_adquisicion = db.Column(db.Date)
    descripcion = db.Column(db.Text)
    observaciones = db.Column(db.Text)
    salon = db.relationship('Salon', backref=db.backref('equipos', lazy=True))
    
    def to_dict(self):
        """Devuelve un diccionario con los datos del equipo para la API y el frontend."""
        data = {
            "id": self.id,
            "id_referencia": self.id_referencia,
            "nombre": self.nombre,
            "tipo": self.tipo,
            "asignado_a": self.asignado_a,
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
        }
        return data

class Incidente(db.Model):
    __tablename__ = 'Incidentes'
    id = db.Column(db.Integer, primary_key=True)
    equipo_id = db.Column(db.Integer, db.ForeignKey('equipos.id'), nullable=False)
    usuario_asignado = db.Column(db.String(100), nullable=True)
    sede = db.Column(db.String(100), nullable=False)
    fecha = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    descripcion = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String(50), nullable=True)
    equipo = db.relationship('Equipo', backref=db.backref('incidentes', lazy=True))
    
    def to_dict(self):
        return {
            "id": self.id,
            "equipo_id": self.equipo_id,
            "equipo_nombre": self.equipo.nombre if self.equipo else "",
            "usuario_asignado": self.usuario_asignado or "",
            "sede": self.sede,
            "fecha": self.fecha.strftime("%Y-%m-%d"),
            "descripcion": self.descripcion,
            "estado": self.estado or ""
        }

class Mantenimiento(db.Model):
    __tablename__ = 'Mantenimiento'
    id = db.Column(db.Integer, primary_key=True)
    equipo_id = db.Column(db.Integer, db.ForeignKey('equipos.id'), nullable=False)
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=False)
    fecha_programada = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    estado = db.Column(db.String(50), default='pendiente')
    descripcion = db.Column(db.Text, nullable=True)
    fecha_realizada = db.Column(db.Date, nullable=True)
    tecnico = db.Column(db.String(100), nullable=True)
    equipo = db.relationship('Equipo', backref=db.backref('programaciones', lazy=True))
    sede = db.relationship('Sede', lazy='joined')
    
    def to_dict(self):
        return {
            "id": self.id,
            "equipo_id": self.equipo_id,
            "equipo_nombre": self.equipo.nombre if self.equipo else "",
            "sede": self.sede.nombre if self.sede else "",
            "fecha_programada": self.fecha_programada.strftime("%Y-%m-%d"),
            "tipo": self.tipo,
            "estado": self.estado,
            "descripcion": self.descripcion or "",
            "fecha_realizada": self.fecha_realizada.strftime("%Y-%m-%d") if self.fecha_realizada else "",
            "tecnico": self.tecnico or ""
        }