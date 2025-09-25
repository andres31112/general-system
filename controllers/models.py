from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from controllers.permisos import ROLE_PERMISSIONS
from datetime import datetime

# Roles
class Rol(db.Model):
    __tablename__ = 'roles'
    id_rol = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)

    # Relación inversa a usuarios
    usuarios = db.relationship('Usuario', back_populates='rol', lazy=True)
# -----------------------------------------------------------------------------------------------------------------------------------------------------
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
    rol = db.relationship('Rol', back_populates='usuarios', lazy='joined')
    estado_cuenta = db.Column(db.Enum('activa', 'inactiva', name='estado_cuenta_enum'), nullable=False, default='activa')
    # Propiedad para nombre completo
    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"
    # Funciones de contraseña
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    # Flask-Login: ID del usuario
    def get_id(self):
        return str(self.id_usuario)

    # Funciones de roles y permisos
    def has_role(self, role_name):
        return self.rol.nombre.lower() == role_name.lower() if self.rol else False

    def has_permission(self, permiso_nombre):
        if not self.rol:
            return False
        return permiso_nombre in ROLE_PERMISSIONS.get(self.rol.nombre, [])


# Académico
class Sede(db.Model):
    __tablename__ = 'Sede'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    direccion = db.Column(db.String(200), nullable=False)


class Curso(db.Model):
    __tablename__ = 'Curso'
    id = db.Column(db.Integer, primary_key=True)
    nombreCurso = db.Column(db.String(100), nullable=False)
    sedeId = db.Column(db.Integer, db.ForeignKey('Sede.id'), nullable=False)


class Matricula(db.Model):
    __tablename__ = 'Matricula'
    id = db.Column(db.Integer, primary_key=True)
    estudianteId = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    cursoId = db.Column(db.Integer, db.ForeignKey('Curso.id'), nullable=False)
    año = db.Column(db.Integer, nullable=False)


class Asignatura(db.Model):
    __tablename__ = 'Asignatura'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    
    def to_dict(self):
        return {"id": self.id, "nombre": self.nombre, "descripcion": self.descripcion}


class Clase(db.Model):
    __tablename__ = 'Clase'
    id = db.Column(db.Integer, primary_key=True)
    asignaturaId = db.Column(db.Integer, db.ForeignKey('Asignatura.id'), nullable=False)
    profesorId = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    cursoId = db.Column(db.Integer, db.ForeignKey('Curso.id'), nullable=False)
    horarioId = db.Column(db.Integer, db.ForeignKey('HorarioGeneral.id'), nullable=False)
    representanteCursoId = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'))


class HorarioGeneral(db.Model):
    __tablename__ = 'HorarioGeneral'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    horaInicio = db.Column(db.Time, nullable=False)
    horaFin = db.Column(db.Time, nullable=False)
    diasSemana = db.Column(db.String(100), nullable=False)
    # Relación con descansos
    descansos = db.relationship('Descanso', backref='horario', cascade="all, delete-orphan", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "horaInicio": self.horaInicio.strftime("%H:%M") if self.horaInicio else None,
            "horaFin": self.horaFin.strftime("%H:%M") if self.horaFin else None,
            "diasSemana": self.diasSemana or "",
            "descansos": [d.to_dict() for d in self.descansos]
        }


class Descanso(db.Model):
    __tablename__ = 'Descanso'
    id = db.Column(db.Integer, primary_key=True)
    horarioId = db.Column(db.Integer, db.ForeignKey('HorarioGeneral.id'), nullable=False)
    horaInicio = db.Column(db.Time, nullable=False)
    horaFin = db.Column(db.Time, nullable=False)

    def to_dict(self):
        # Devuelve horaInicio como "HH:MM" y duracion en minutos
        start = self.horaInicio.strftime("%H:%M") if self.horaInicio else None
        end = self.horaFin.strftime("%H:%M") if self.horaFin else None
        duracion = None
        if self.horaInicio and self.horaFin:
            from datetime import datetime, date
            s = datetime.combine(date.today(), self.horaInicio)
            e = datetime.combine(date.today(), self.horaFin)
            duracion = int((e - s).total_seconds() / 60)
        return {
            "id": self.id,
            "horaInicio": start,
            "horaFin": end,
            "duracion": duracion
        }


class BloqueHorario(db.Model):
    __tablename__ = 'BloqueHorario'
    id = db.Column(db.Integer, primary_key=True)
    horaInicio = db.Column(db.Time, nullable=False)
    horaFin = db.Column(db.Time, nullable=False)


class AsignaturaHorario(db.Model):
    __tablename__ = 'AsignaturaHorario'
    id = db.Column(db.Integer, primary_key=True)
    asignaturaId = db.Column(db.Integer, db.ForeignKey('Asignatura.id'), nullable=False)
    horarioId = db.Column(db.Integer, db.ForeignKey('HorarioGeneral.id'), nullable=False)
    bloqueId = db.Column(db.Integer, db.ForeignKey('BloqueHorario.id'), nullable=False)


class Asistencia(db.Model):
    __tablename__ = 'Asistencia'
    id = db.Column(db.Integer, primary_key=True)
    estudianteId = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    claseId = db.Column(db.Integer, db.ForeignKey('Clase.id'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    estado = db.Column(db.Enum('presente', 'ausente', 'tarde', 'justificado'), nullable=False)


class ConfiguracionCalificacion(db.Model):
    __tablename__ = 'ConfiguracionCalificacion'
    id = db.Column(db.Integer, primary_key=True)
    notaMinima = db.Column(db.Numeric(5,2), nullable=False)
    notaMaxima = db.Column(db.Numeric(5,2), nullable=False)
    notaMinimaAprobacion = db.Column(db.Numeric(5,2), nullable=False)


class CategoriaCalificacion(db.Model):
    __tablename__ = 'CategoriaCalificacion'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(20), nullable=False)
    porcentaje = db.Column(db.Numeric(5,2), nullable=False)


class Calificacion(db.Model):
    __tablename__ = 'Calificacion'
    id = db.Column(db.Integer, primary_key=True)
    estudianteId = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    asignaturaId = db.Column(db.Integer, db.ForeignKey('Asignatura.id'), nullable=False)
    categoriaId = db.Column(db.Integer, db.ForeignKey('CategoriaCalificacion.id'), nullable=False)
    valor = db.Column(db.Numeric(5,2), nullable=False)
    observaciones = db.Column(db.Text)

class Salon(db.Model):
    __tablename__ = 'Salones'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    tipo = db.Column(db.String(50), nullable=False) # 'sala_computo', 'sala_general', etc.
    id_sede_fk = db.Column(db.Integer, db.ForeignKey('Sede.id'), nullable=False)
    
    sede = db.relationship('Sede', backref=db.backref('salones', lazy=True))

    def __repr__(self):
        return f"Salon('{self.nombre}', '{self.tipo}')"
    
class Equipo(db.Model):
    __tablename__ = 'Equipos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.Enum('Disponible', 'Mantenimiento', 'Asignado', 'Incidente', 'Revisión', name='estado_equipo_enum'), nullable=False, default='Disponible')
    id_salon_fk = db.Column(db.Integer, db.ForeignKey('Salones.id'), nullable=False)
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
        return {
            "id": self.id,
            "nombre": self.nombre,
            "estado": self.estado,
            "id_salon_fk": self.id_salon_fk,
            "sala_nombre": self.salon.nombre if self.salon else "",
            "sede_nombre": self.salon.sede.nombre if self.salon and self.salon.sede else "",
            "asignado_a": self.asignado_a or "",
            "id_referencia": self.id_referencia or "",
            "tipo": self.tipo or "",
            "sistema_operativo": self.sistema_operativo or "",
            "ram": self.ram or "",
            "disco_duro": self.disco_duro or "",
            "fecha_adquisicion": self.fecha_adquisicion.strftime("%Y-%m-%d") if self.fecha_adquisicion else "",
            "descripcion": self.descripcion or "",
            "observaciones": self.observaciones or ""
        }
    
class Incidente(db.Model):
    __tablename__ = 'Incidentes'
    id = db.Column(db.Integer, primary_key=True)
    equipo_id = db.Column(db.Integer, db.ForeignKey('Equipos.id'), nullable=False)
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
    equipo_id = db.Column(db.Integer, db.ForeignKey('Equipos.id'), nullable=False)
    sede_id = db.Column(db.Integer, db.ForeignKey('Sede.id'), nullable=False)
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