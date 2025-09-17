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
        ('sala_general', 'Sala General'),
        ('sala_especial', 'Sala Especializada')
    ], validators=[DataRequired()])
    sede = QuerySelectField('Sede', query_factory=get_all_sedes,
                           get_pk=lambda s: s.id,
                           get_label=lambda s: s.nombre,
                           allow_blank=True, blank_text='Selecciona una Sede...')
    submit = SubmitField('Registrar Sala')    


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