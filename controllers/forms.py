from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from wtforms_sqlalchemy.fields import QuerySelectField
from extensions import db
from controllers.models import Usuario, Rol, Sede, Curso, Asignatura

# Función para obtener todos los roles
def get_all_roles():
    return Rol.query.order_by(Rol.nombre).all()

# Función para obtener todas las sedes
def get_all_sedes():
    return Sede.query.order_by(Sede.nombre).all()

# Función para obtener todos los cursos
def get_all_courses():
    return Curso.query.order_by(Curso.nombreCurso).all()

# ✅ Nueva función para obtener todas las asignaturas
def get_all_subjects():
    return Asignatura.query.order_by(Asignatura.nombre).all()


class RegistrationForm(FlaskForm):
    no_identidad = StringField('Número de Identidad', validators=[DataRequired(), Length(min=5, max=25)])
    tipo_doc = SelectField('Tipo de Documento', choices=[
        ('cc', 'Cédula de Ciudadanía'),
        ('ti', 'Tarjeta de Identidad'),
        ('ce', 'Cédula de Extranjería'),
        ('ppt', 'Permiso por Protección Temporal'),
        ('pep', 'Permiso Especial de Permanencia'),
        ('registro_civil', 'Registro Civil')
    ], validators=[DataRequired()])
    nombre = StringField('Nombre', validators=[DataRequired(), Length(min=2, max=50)])
    apellido = StringField('Apellido', validators=[DataRequired(), Length(min=2, max=50)])
    correo = StringField('Correo Electrónico', validators=[DataRequired(), Email()])
    telefono = StringField('Teléfono Celular', validators=[Length(max=20)])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmar Contraseña', validators=[DataRequired(), EqualTo('password')])
    
    rol = SelectField('Rol del Usuario', validators=[DataRequired()])
    
    # Existing student fields
    curso_id = QuerySelectField(
        'Curso',
        query_factory=get_all_courses,
        get_pk=lambda c: c.id,
        get_label=lambda c: c.nombreCurso,
        allow_blank=True,
        blank_text='Selecciona un Curso...'
    )
    anio_matricula = StringField('Año de Matrícula', validators=[Length(max=4)])
    
    # ✅ New fields for professor assignment
    asignatura_id = QuerySelectField(
        'Asignatura',
        query_factory=get_all_subjects,
        get_pk=lambda a: a.id,
        get_label=lambda a: a.nombre,
        allow_blank=True,
        blank_text='Selecciona una Asignatura...'
    )
    curso_asignacion_id = QuerySelectField(
        'Curso de la Asignatura',
        query_factory=get_all_courses,
        get_pk=lambda c: c.id,
        get_label=lambda c: c.nombreCurso,
        allow_blank=True,
        blank_text='Selecciona el Curso...'
    )

    submit = SubmitField('Registrar Usuario')

    def validate_no_identidad(self, no_identidad):
        if Usuario.query.filter_by(no_identidad=no_identidad.data).first():
            raise ValidationError('Ese número de identidad ya está registrado. Por favor, elige uno diferente.')

    def validate_correo(self, correo):
        if Usuario.query.filter_by(correo=correo.data).first():
            raise ValidationError('Ese correo electrónico ya está registrado. Por favor, elige uno diferente.')
    no_identidad = StringField('Número de Identidad', validators=[DataRequired(), Length(min=5, max=25)])
    tipo_doc = SelectField('Tipo de Documento', choices=[
        ('cc', 'Cédula de Ciudadanía'),
        ('ti', 'Tarjeta de Identidad'),
        ('ce', 'Cédula de Extranjería'),
        ('ppt', 'Permiso por Protección Temporal'),
        ('pep', 'Permiso Especial de Permanencia'),
        ('registro_civil', 'Registro Civil')
    ], validators=[DataRequired()])
    nombre = StringField('Nombre', validators=[DataRequired(), Length(min=2, max=50)])
    apellido = StringField('Apellido', validators=[DataRequired(), Length(min=2, max=50)])
    correo = StringField('Correo Electrónico', validators=[DataRequired(), Email()])
    telefono = StringField('Teléfono Celular', validators=[Length(max=20)])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmar Contraseña', validators=[DataRequired(), EqualTo('password')])
    
    # ✅ Se cambia a SelectField para manejar las opciones en la ruta
    rol = SelectField('Rol del Usuario', validators=[DataRequired()])
    
    # ✅ Nuevos campos para la matrícula del estudiante
    curso_id = QuerySelectField(
        'Curso',
        query_factory=get_all_courses,
        get_pk=lambda c: c.id,
        get_label=lambda c: c.nombreCurso,
        allow_blank=True,
        blank_text='Selecciona un Curso...'
    )
    anio_matricula = StringField('Año de Matrícula', validators=[Length(max=4)])
    submit = SubmitField('Registrar Usuario')

    def validate_no_identidad(self, no_identidad):
        if Usuario.query.filter_by(no_identidad=no_identidad.data).first():
            raise ValidationError('Ese número de identidad ya está registrado. Por favor, elige uno diferente.')

    def validate_correo(self, correo):
        if Usuario.query.filter_by(correo=correo.data).first():
            raise ValidationError('Ese correo electrónico ya está registrado. Por favor, elige uno diferente.')

class LoginForm(FlaskForm):
    correo = StringField('Correo Electrónico', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    remember = BooleanField('Recordarme')
    submit = SubmitField('Iniciar Sesión')


class RoleForm(FlaskForm):
    nombre = StringField('Nombre del Rol', validators=[DataRequired(), Length(min=2, max=50)])
    descripcion = TextAreaField('Descripción del Rol', validators=[Length(max=255)])
    submit = SubmitField('Guardar Rol')

    def __init__(self, original_nombre=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_nombre = original_nombre

    def validate_nombre(self, nombre):
        if nombre.data != self.original_nombre:
            if Rol.query.filter_by(nombre=nombre.data).first():
                raise ValidationError('Este nombre de rol ya existe. Por favor, elige uno diferente.')

class UserEditForm(FlaskForm):
    no_identidad = StringField('Número de Identidad', validators=[DataRequired(), Length(min=5, max=25)])
    tipo_doc = SelectField('Tipo de Documento', choices=[
        ('cc', 'Cédula de Ciudadanía'),
        ('ti', 'Tarjeta de Identidad'),
        ('ce', 'Cédula de Extranjería'),
        ('ppt', 'Permiso por Protección Temporal'),
        ('pep', 'Permiso Especial de Permanencia'),
        ('registro_civil', 'Registro Civil')
    ], validators=[DataRequired()])
    nombre = StringField('Nombre', validators=[DataRequired(), Length(min=2, max=50)])
    apellido = StringField('Apellido', validators=[DataRequired(), Length(min=2, max=50)])
    correo = StringField('Correo Electrónico', validators=[DataRequired(), Email()])
    telefono = StringField('Teléfono Celular', validators=[Length(max=20)])
    estado_cuenta = SelectField('Estado de la Cuenta', choices=[
        ('activa', 'Activa'),
        ('inactiva', 'Inactiva')
    ], validators=[DataRequired()])
    rol = QuerySelectField('Rol del Usuario', query_factory=get_all_roles,
                           get_pk=lambda r: r.id_rol,
                           get_label=lambda r: r.nombre,
                           allow_blank=True, blank_text='Selecciona un Rol...')
    submit = SubmitField('Actualizar Usuario')

    def __init__(self, original_no_identidad=None, original_correo=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_no_identidad = original_no_identidad
        self.original_correo = original_correo

    def validate_no_identidad(self, no_identidad):
        if no_identidad.data != self.original_no_identidad:
            if Usuario.query.filter_by(no_identidad=no_identidad.data).first():
                raise ValidationError('Ese número de identidad ya está en uso. Por favor, elige uno diferente.')

    def validate_correo(self, correo):
        if correo.data != self.original_correo:
            if Usuario.query.filter_by(correo=correo.data).first():
                raise ValidationError('Ese correo electrónico ya está registrado. Por favor, elige uno diferente.')


class ForgotPasswordForm(FlaskForm):
    correo = StringField('Correo Electrónico', validators=[DataRequired(), Email()])
    submit = SubmitField('Solicitar Restablecimiento')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nueva Contraseña', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmar Contraseña', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Restablecer Contraseña')

class SalonForm(FlaskForm):
    nombre_salon = StringField('Nombre de la Sala', validators=[DataRequired(), Length(min=2, max=100)])
    tipo = SelectField('Tipo de Sala', choices=[
        ('sala_computo', 'Sala de Cómputo'),
        ('aula', 'Aula'),
        ('laboratorio', 'Laboratorio'),
        ('auditorio', 'Auditorio')
    ], validators=[DataRequired()])
    capacidad = StringField('Capacidad', validators=[DataRequired()], 
                           render_kw={"type": "number", "min": "1", "max": "200"})
    cantidad_sillas = StringField('Cantidad de Sillas', validators=[Length(max=10)],
                                 render_kw={"type": "number", "min": "0", "max": "200"})
    cantidad_mesas = StringField('Cantidad de Mesas', validators=[Length(max=10)],
                                render_kw={"type": "number", "min": "0", "max": "100"})
    sede = QuerySelectField('Sede', query_factory=get_all_sedes,
                           get_pk=lambda s: s.id,
                           get_label=lambda s: s.nombre,
                           allow_blank=True, blank_text='Selecciona una Sede...',
                           validators=[DataRequired()])
    submit = SubmitField('Registrar Sala')

    def validate_capacidad(self, capacidad):
        try:
            cap_value = int(capacidad.data)
            if cap_value <= 0:
                raise ValidationError('La capacidad debe ser un número mayor a 0.')
            if cap_value > 200:
                raise ValidationError('La capacidad no puede ser mayor a 200.')
        except (ValueError, TypeError):
            raise ValidationError('La capacidad debe ser un número válido.')

    def validate_cantidad_sillas(self, cantidad_sillas):
        if cantidad_sillas.data:
            try:
                sillas_value = int(cantidad_sillas.data)
                if sillas_value < 0:
                    raise ValidationError('La cantidad de sillas no puede ser negativa.')
                if sillas_value > 200:
                    raise ValidationError('La cantidad de sillas no puede ser mayor a 200.')
            except (ValueError, TypeError):
                raise ValidationError('La cantidad de sillas debe ser un número válido.')

    def validate_cantidad_mesas(self, cantidad_mesas):
        if cantidad_mesas.data:
            try:
                mesas_value = int(cantidad_mesas.data)
                if mesas_value < 0:
                    raise ValidationError('La cantidad de mesas no puede ser negativa.')
                if mesas_value > 100:
                    raise ValidationError('La cantidad de mesas no puede ser mayor a 100.')
            except (ValueError, TypeError):
                raise ValidationError('La cantidad de mesas debe ser un número válido.')

    def validate_nombre_salon(self, nombre_salon):
        from controllers.models import Salon
        salon = Salon.query.filter_by(nombre=nombre_salon.data).first()
        if salon:
            raise ValidationError('Ya existe un salón con ese nombre. Por favor, elige uno diferente.')    

class CursoForm(FlaskForm):
    nombreCurso = StringField('Nombre del Curso', validators=[DataRequired(), Length(min=2, max=100)])
    sedeId = QuerySelectField('Sede', query_factory=get_all_sedes,
                              get_pk=lambda s: s.id,
                              get_label=lambda s: s.nombre,
                              allow_blank=True, blank_text='Selecciona una Sede...')
    submit = SubmitField('Guardar Curso')

    def validate_nombreCurso(self, nombreCurso):
        curso = Curso.query.filter_by(nombreCurso=nombreCurso.data).first()
        if curso:
            raise ValidationError('Este curso ya existe. Por favor, elige uno diferente.')
        
class SedeForm(FlaskForm):
    nombre = StringField('Nombre de la Sede', validators=[DataRequired(), Length(min=3, max=100)])
    submit = SubmitField('Guardar Sede')

    def validate_nombre(self, nombre):
        sede = Sede.query.filter_by(nombre=nombre.data).first()
        if sede:
            raise ValidationError('Esta sede ya existe. Por favor, elige un nombre diferente.')

# ================================
# Funciones para QuerySelect - Equipos
# ================================
def get_all_salones():
    """Retorna todos los salones ordenados por nombre con información de sede."""
    from controllers.models import Salon
    return Salon.query.join(Sede).order_by(Salon.nombre).all()

# ================================
# Formulario para Equipos
# ================================
class EquipoForm(FlaskForm):
    id_referencia = StringField('ID/Referencia del Equipo', validators=[Length(max=50)])
    nombre = StringField('Nombre del Equipo', validators=[DataRequired(), Length(min=2, max=100)])
    tipo = SelectField('Tipo de Equipo', choices=[
        ('computadora', 'Computadora de Escritorio'),
        ('laptop', 'Laptop'),
        ('tablet', 'Tablet'),
        ('proyector', 'Proyector'),
        ('impresora', 'Impresora'),
        ('scanner', 'Escáner'),
        ('servidor', 'Servidor'),
        ('otro', 'Otro')
    ], validators=[DataRequired()])
    estado = SelectField('Estado del Equipo', choices=[
        ('Disponible', 'Disponible'),
        ('Asignado', 'Asignado'),
        ('Mantenimiento', 'Mantenimiento'),
        ('Incidente', 'Incidente'),
        ('Revisión', 'Revisión')
    ], validators=[DataRequired()], default='Disponible')
    salon = QuerySelectField('Sala', query_factory=get_all_salones, get_pk=lambda s: s.id, get_label=lambda s: f"{s.nombre} ({s.sede.nombre if s.sede else 'Sin sede'})", allow_blank=True, blank_text='Selecciona una Sala...')
    asignado_a = StringField('Asignado a', validators=[Length(max=100)])
    sistema_operativo = StringField('Sistema Operativo', validators=[Length(max=100)])
    ram = StringField('Memoria RAM', validators=[Length(max=50)], render_kw={"placeholder": "Ej: 8GB DDR4"})
    disco_duro = StringField('Disco Duro', validators=[Length(max=100)], render_kw={"placeholder": "Ej: 256GB SSD"})
    fecha_adquisicion = StringField('Fecha de Adquisición', render_kw={"type": "date"})
    descripcion = TextAreaField('Descripción', validators=[Length(max=500)])
    observaciones = TextAreaField('Observaciones', validators=[Length(max=500)])
    submit = SubmitField('Registrar Equipo')

    def validate_id_referencia(self, id_referencia):
        if id_referencia.data:
            from controllers.models import Equipo
            if Equipo.query.filter_by(id_referencia=id_referencia.data).first():
                raise ValidationError('Esa referencia ya está registrada. Por favor, elige una diferente.')