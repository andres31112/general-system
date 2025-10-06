# controllers/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField, IntegerField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional
from wtforms_sqlalchemy.fields import QuerySelectField
import re
from extensions import db
from controllers.models import Usuario, Rol, Sede, Curso, Asignatura

# ================================
# Funciones de Consulta para QuerySelectField
# ================================

def get_all_roles():
    """Retorna todos los roles ordenados por nombre"""
    return Rol.query.order_by(Rol.nombre).all()

def get_all_sedes():
    """Retorna todas las sedes ordenadas por nombre"""
    return Sede.query.order_by(Sede.nombre).all()

def get_all_courses():
    """Retorna todos los cursos ordenados por nombre"""
    return Curso.query.order_by(Curso.nombreCurso).all()

def get_all_subjects():
    """Retorna todas las asignaturas ordenadas por nombre"""
    return Asignatura.query.order_by(Asignatura.nombre).all()

def get_all_salones():
    """Retorna todos los salones ordenados por nombre con información de sede"""
    from controllers.models import Salon
    return Salon.query.join(Sede).order_by(Salon.nombre).all()

# ================================
# Formularios de Autenticación
# ================================

class LoginForm(FlaskForm):
    """Formulario para inicio de sesión"""
    correo = StringField('Correo Electrónico', 
                        validators=[DataRequired(), Email()],
                        render_kw={"placeholder": "tu@correo.com"})
    password = PasswordField('Contraseña', 
                            validators=[DataRequired()],
                            render_kw={"placeholder": "Ingresa tu contraseña"})
    remember = BooleanField('Recordarme')
    submit = SubmitField('Iniciar Sesión')


class ForgotPasswordForm(FlaskForm):
    """Formulario para solicitar restablecimiento de contraseña"""
    correo = StringField('Correo Electrónico',
                        validators=[DataRequired(), Email()],
                        render_kw={"placeholder": "tu@correo.com"})
    submit = SubmitField('Solicitar Restablecimiento')


class ResetPasswordForm(FlaskForm):
    """Formulario para restablecer contraseña"""
    password = PasswordField('Nueva Contraseña', 
                            validators=[DataRequired(), Length(min=8)],
                            render_kw={"placeholder": "Mínimo 8 caracteres"})
    confirm_password = PasswordField('Confirmar Contraseña', 
                                    validators=[DataRequired(), EqualTo('password')],
                                    render_kw={"placeholder": "Repite la contraseña"})
    submit = SubmitField('Restablecer Contraseña')

    def validate_password(self, field):
        password = field.data
        if len(password) < 8:
            raise ValidationError('La contraseña debe tener al menos 8 caracteres')
        if not re.search(r'[A-Z]', password):
            raise ValidationError('La contraseña debe contener al menos una mayúscula')
        if not re.search(r'[a-z]', password):
            raise ValidationError('La contraseña debe contener al menos una minúscula')
        if not re.search(r'\d', password):
            raise ValidationError('La contraseña debe contener al menos un número')
        if not re.search(r'[!@#$%&*]', password):
            raise ValidationError('La contraseña debe contener al menos un carácter especial (!@#$%&*)')

# ================================
# Formularios de Gestión de Usuarios
# ================================

class RegistrationForm(FlaskForm):
    """Formulario para registro de usuarios (estudiantes, profesores, padres)"""
    
    # Información personal
    no_identidad = StringField('Número de Identidad', 
                              validators=[DataRequired(), Length(min=5, max=25)],
                              render_kw={"placeholder": "Ej: 1234567890"})
    
    tipo_doc = SelectField('Tipo de Documento', 
                          choices=[
                              ('CC', 'Cédula de Ciudadanía'),
                              ('CE', 'Cédula de Extranjería'),
                              ('TI', 'Tarjeta de Identidad'),
                              ('PAS', 'Pasaporte'),
                              ('PPT', 'Permiso por Protección Temporal'),
                              ('PEP', 'Permiso Especial de Permanencia'),
                              ('RC', 'Registro Civil')
                          ], 
                          validators=[DataRequired()])
    
    nombre = StringField('Nombre', 
                        validators=[DataRequired(), Length(min=2, max=50)],
                        render_kw={"placeholder": "Nombre del usuario"})
    
    apellido = StringField('Apellido', 
                          validators=[DataRequired(), Length(min=2, max=50)],
                          render_kw={"placeholder": "Apellido del usuario"})
    
    direccion = StringField('Dirección', 
                           validators=[DataRequired(), Length(max=200)],
                           render_kw={"placeholder": "Dirección completa"})
    
    # Información de contacto
    correo = StringField('Correo Electrónico', 
                        validators=[DataRequired(), Email()],
                        render_kw={"placeholder": "correo@ejemplo.com"})
    
    telefono = StringField('Teléfono Celular', 
                          validators=[Optional(), Length(max=20)],
                          render_kw={"placeholder": "+57 300 123 4567"})
    
    # Seguridad
    password = PasswordField('Contraseña', 
                            validators=[DataRequired()],
                            render_kw={"placeholder": "Contraseña segura", "readonly": True})
    
    confirm_password = PasswordField('Confirmar Contraseña', 
                                    validators=[DataRequired(), EqualTo('password')],
                                    render_kw={"placeholder": "Repetir contraseña", "readonly": True})
    
    # Rol y configuración
    rol = SelectField('Rol del Usuario', validators=[DataRequired()])
    
    # Campos específicos para estudiantes
    curso_id = QuerySelectField(
        'Curso',
        query_factory=get_all_courses,
        get_pk=lambda c: c.id_curso,
        get_label=lambda c: c.nombreCurso,
        allow_blank=True,
        blank_text='Selecciona un Curso...'
    )
    
    anio_matricula = IntegerField('Año de Matrícula', 
                                 validators=[Optional()],
                                 render_kw={"placeholder": "Ej: 2024"})
    
    # Campos específicos para profesores
    asignatura_id = QuerySelectField(
        'Asignatura',
        query_factory=get_all_subjects,
        get_pk=lambda a: a.id_asignatura,
        get_label=lambda a: a.nombre,
        allow_blank=True,
        blank_text='Selecciona una Asignatura...'
    )
    
    curso_asignacion_id = QuerySelectField(
        'Curso de la Asignatura',
        query_factory=get_all_courses,
        get_pk=lambda c: c.id_curso,
        get_label=lambda c: c.nombreCurso,
        allow_blank=True,
        blank_text='Selecciona el Curso...'
    )

    submit = SubmitField('Registrar Usuario')

    def validate_no_identidad(self, no_identidad):
        """Valida que el número de identidad no esté registrado"""
        if Usuario.query.filter_by(no_identidad=no_identidad.data).first():
            raise ValidationError('Este número de identidad ya está registrado. Por favor, elige uno diferente.')

    def validate_correo(self, correo):
        """Valida que el correo electrónico no esté registrado"""
        if Usuario.query.filter_by(correo=correo.data).first():
            raise ValidationError('Este correo electrónico ya está registrado. Por favor, elige uno diferente.')

    def validate_password(self, field):
        """Valida los requisitos de seguridad de la contraseña"""
        password = field.data
        if len(password) < 8:
            raise ValidationError('La contraseña debe tener al menos 8 caracteres')
        if not re.search(r'[A-Z]', password):
            raise ValidationError('La contraseña debe contener al menos una mayúscula')
        if not re.search(r'[a-z]', password):
            raise ValidationError('La contraseña debe contener al menos una minúscula')
        if not re.search(r'\d', password):
            raise ValidationError('La contraseña debe contener al menos un número')
        if not re.search(r'[!@#$%&*]', password):
            raise ValidationError('La contraseña debe contener al menos un carácter especial (!@#$%&*)')


class UserEditForm(FlaskForm):
    """Formulario para edición de usuarios existentes"""
    
    no_identidad = StringField('Número de Identidad', 
                              validators=[DataRequired(), Length(min=5, max=25)])
    
    tipo_doc = SelectField('Tipo de Documento', 
                          choices=[
                              ('CC', 'Cédula de Ciudadanía'),
                              ('CE', 'Cédula de Extranjería'),
                              ('TI', 'Tarjeta de Identidad'),
                              ('PAS', 'Pasaporte'),
                              ('PPT', 'Permiso por Protección Temporal'),
                              ('PEP', 'Permiso Especial de Permanencia'),
                              ('RC', 'Registro Civil')
                          ], 
                          validators=[DataRequired()])
    
    nombre = StringField('Nombre', 
                        validators=[DataRequired(), Length(min=2, max=50)])
    
    apellido = StringField('Apellido', 
                          validators=[DataRequired(), Length(min=2, max=50)])
    
    correo = StringField('Correo Electrónico', 
                        validators=[DataRequired(), Email()])
    
    telefono = StringField('Teléfono Celular', 
                          validators=[Optional(), Length(max=20)])
    
    estado_cuenta = SelectField('Estado de la Cuenta', 
                               choices=[
                                   ('activa', 'Activa'),
                                   ('inactiva', 'Inactiva')
                               ], 
                               validators=[DataRequired()])
    
    rol = QuerySelectField('Rol del Usuario', 
                          query_factory=get_all_roles,
                          get_pk=lambda r: r.id_rol,
                          get_label=lambda r: r.nombre,
                          allow_blank=True, 
                          blank_text='Selecciona un Rol...')
    
    submit = SubmitField('Actualizar Usuario')

    def __init__(self, original_no_identidad=None, original_correo=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_no_identidad = original_no_identidad
        self.original_correo = original_correo

    def validate_no_identidad(self, no_identidad):
        """Valida que el número de identidad no esté en uso por otro usuario"""
        if no_identidad.data != self.original_no_identidad:
            if Usuario.query.filter_by(no_identidad=no_identidad.data).first():
                raise ValidationError('Este número de identidad ya está en uso. Por favor, elige uno diferente.')

    def validate_correo(self, correo):
        """Valida que el correo electrónico no esté en uso por otro usuario"""
        if correo.data != self.original_correo:
            if Usuario.query.filter_by(correo=correo.data).first():
                raise ValidationError('Este correo electrónico ya está registrado. Por favor, elige uno diferente.')

# ================================
# Formularios de Gestión Académica
# ================================

class RoleForm(FlaskForm):
    """Formulario para creación y edición de roles"""
    nombre = StringField('Nombre del Rol', 
                        validators=[DataRequired(), Length(min=2, max=50)],
                        render_kw={"placeholder": "Nombre del rol"})
    
    descripcion = TextAreaField('Descripción del Rol', 
                               validators=[Optional(), Length(max=255)],
                               render_kw={"placeholder": "Descripción del rol", "rows": 3})
    
    submit = SubmitField('Guardar Rol')

    def __init__(self, original_nombre=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_nombre = original_nombre

    def validate_nombre(self, nombre):
        """Valida que el nombre del rol no exista"""
        if nombre.data != self.original_nombre:
            if Rol.query.filter_by(nombre=nombre.data).first():
                raise ValidationError('Este nombre de rol ya existe. Por favor, elige uno diferente.')


class SedeForm(FlaskForm):
    """Formulario para creación y edición de sedes"""
    nombre = StringField('Nombre de la Sede', 
                        validators=[DataRequired(), Length(min=3, max=100)],
                        render_kw={"placeholder": "Nombre de la sede"})
    
    submit = SubmitField('Guardar Sede')

    def validate_nombre(self, nombre):
        """Valida que el nombre de la sede no exista"""
        sede = Sede.query.filter_by(nombre=nombre.data).first()
        if sede:
            raise ValidationError('Esta sede ya existe. Por favor, elige un nombre diferente.')


class CursoForm(FlaskForm):
    """Formulario para creación y edición de cursos"""
    nombreCurso = StringField('Nombre del Curso', 
                             validators=[DataRequired(), Length(min=2, max=100)],
                             render_kw={"placeholder": "Nombre del curso"})
    
    sedeId = QuerySelectField('Sede', 
                             query_factory=get_all_sedes,
                             get_pk=lambda s: s.id_sede,
                             get_label=lambda s: s.nombre,
                             allow_blank=True, 
                             blank_text='Selecciona una Sede...')
    
    submit = SubmitField('Guardar Curso')

    def validate_nombreCurso(self, nombreCurso):
        """Valida que el nombre del curso no exista"""
        curso = Curso.query.filter_by(nombreCurso=nombreCurso.data).first()
        if curso:
            raise ValidationError('Este curso ya existe. Por favor, elige un nombre diferente.')


class SalonForm(FlaskForm):
    """Formulario para creación y edición de salones"""
    nombre_salon = StringField('Nombre de la Sala', 
                              validators=[DataRequired(), Length(min=2, max=100)],
                              render_kw={"placeholder": "Nombre del salón"})
    
    tipo = SelectField('Tipo de Sala', 
                      choices=[
                          ('sala_computo', 'Sala de Cómputo'),
                          ('aula', 'Aula'),
                          ('laboratorio', 'Laboratorio'),
                          ('auditorio', 'Auditorio')
                      ], 
                      validators=[DataRequired()])
    
    capacidad = IntegerField('Capacidad', 
                           validators=[DataRequired()],
                           render_kw={"min": "1", "max": "200", "placeholder": "Número de personas"})
    
    cantidad_sillas = IntegerField('Cantidad de Sillas', 
                                  validators=[Optional()],
                                  render_kw={"min": "0", "max": "200", "placeholder": "0"})
    
    cantidad_mesas = IntegerField('Cantidad de Mesas', 
                                 validators=[Optional()],
                                 render_kw={"min": "0", "max": "100", "placeholder": "0"})
    
    sede = QuerySelectField('Sede', 
                           query_factory=get_all_sedes,
                           get_pk=lambda s: s.id_sede,
                           get_label=lambda s: s.nombre,
                           allow_blank=True, 
                           blank_text='Selecciona una Sede...',
                           validators=[DataRequired()])
    
    submit = SubmitField('Registrar Sala')

    def validate_capacidad(self, capacidad):
        """Valida que la capacidad sea un número válido"""
        if capacidad.data <= 0:
            raise ValidationError('La capacidad debe ser un número mayor a 0.')
        if capacidad.data > 200:
            raise ValidationError('La capacidad no puede ser mayor a 200.')

    def validate_cantidad_sillas(self, cantidad_sillas):
        """Valida que la cantidad de sillas sea un número válido"""
        if cantidad_sillas.data is not None:
            if cantidad_sillas.data < 0:
                raise ValidationError('La cantidad de sillas no puede ser negativa.')
            if cantidad_sillas.data > 200:
                raise ValidationError('La cantidad de sillas no puede ser mayor a 200.')

    def validate_cantidad_mesas(self, cantidad_mesas):
        """Valida que la cantidad de mesas sea un número válido"""
        if cantidad_mesas.data is not None:
            if cantidad_mesas.data < 0:
                raise ValidationError('La cantidad de mesas no puede ser negativa.')
            if cantidad_mesas.data > 100:
                raise ValidationError('La cantidad de mesas no puede ser mayor a 100.')

    def validate_nombre_salon(self, nombre_salon):
        """Valida que el nombre del salón no exista"""
        from controllers.models import Salon
        salon = Salon.query.filter_by(nombre=nombre_salon.data).first()
        if salon:
            raise ValidationError('Ya existe un salón con ese nombre. Por favor, elige uno diferente.')

# ================================
# Formularios de Gestión de Equipos
# ================================

class EquipoForm(FlaskForm):
    """Formulario para registro y edición de equipos tecnológicos"""
    
    id_referencia = StringField('ID/Referencia del Equipo', 
                               validators=[Optional(), Length(max=50)],
                               render_kw={"placeholder": "Código interno o referencia"})
    
    nombre = StringField('Nombre del Equipo', 
                        validators=[DataRequired(), Length(min=2, max=100)],
                        render_kw={"placeholder": "Nombre descriptivo del equipo"})
    
    tipo = SelectField('Tipo de Equipo', 
                      choices=[
                          ('computadora', 'Computadora de Escritorio'),
                          ('laptop', 'Laptop'),
                          ('tablet', 'Tablet'),
                          ('proyector', 'Proyector'),
                          ('impresora', 'Impresora'),
                          ('scanner', 'Escáner'),
                          ('servidor', 'Servidor'),
                          ('otro', 'Otro')
                      ], 
                      validators=[DataRequired()])
    
    estado = SelectField('Estado del Equipo', 
                        choices=[
                            ('Disponible', 'Disponible'),
                            ('Asignado', 'Asignado'),
                            ('Mantenimiento', 'Mantenimiento'),
                            ('Incidente', 'Incidente'),
                            ('Revisión', 'Revisión')
                        ], 
                        validators=[DataRequired()], 
                        default='Disponible')
    
    salon = QuerySelectField('Sala', 
                            query_factory=get_all_salones, 
                            get_pk=lambda s: s.id_salon,
                            get_label=lambda s: f"{s.nombre} ({s.sede.nombre if s.sede else 'Sin sede'})", 
                            allow_blank=True, 
                            blank_text='Selecciona una Sala...')
    
    asignado_a = StringField('Asignado a', 
                            validators=[Optional(), Length(max=100)],
                            render_kw={"placeholder": "Persona o departamento"})
    
    sistema_operativo = StringField('Sistema Operativo', 
                                   validators=[Optional(), Length(max=100)],
                                   render_kw={"placeholder": "Ej: Windows 10, Ubuntu 20.04"})
    
    ram = StringField('Memoria RAM', 
                     validators=[Optional(), Length(max=50)],
                     render_kw={"placeholder": "Ej: 8GB DDR4"})
    
    disco_duro = StringField('Disco Duro', 
                            validators=[Optional(), Length(max=100)],
                            render_kw={"placeholder": "Ej: 256GB SSD"})
    
    fecha_adquisicion = StringField('Fecha de Adquisición', 
                                   render_kw={"type": "date"})
    
    descripcion = TextAreaField('Descripción', 
                               validators=[Optional(), Length(max=500)],
                               render_kw={"placeholder": "Descripción detallada del equipo", "rows": 3})
    
    observaciones = TextAreaField('Observaciones', 
                                 validators=[Optional(), Length(max=500)],
                                 render_kw={"placeholder": "Observaciones adicionales", "rows": 3})
    
    submit = SubmitField('Registrar Equipo')

    def validate_id_referencia(self, id_referencia):
        """Valida que la referencia del equipo no esté duplicada"""
        if id_referencia.data:
            from controllers.models import Equipo
            if Equipo.query.filter_by(id_referencia=id_referencia.data).first():
                raise ValidationError('Esta referencia ya está registrada. Por favor, elige una diferente.')