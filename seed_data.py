# seed_data.py (Versión Corregida y Funcional Definitiva)
"""
Script de seeding completo para el sistema educativo
Genera datos realistas con énfasis en usuarios con correos reales
50 estudiantes en total
"""
from datetime import datetime, date, time, timedelta
import random
import os
# Importar app y modelos asumiendo que están en la estructura del proyecto
from app import app
from controllers.models import (
    db, Rol, Usuario, Sede, Curso, HorarioGeneral, BloqueHorario,
    Asignatura, Matricula, Clase, Calificacion, CategoriaCalificacion,
    Asistencia, Salon, Equipo, Incidente, Mantenimiento, Evento,
    Comunicacion, Notificacion, Candidato, Voto, HorarioCurso,
    HorarioCompartido, ConfiguracionCalificacion, SolicitudConsulta
)

# Datos de ejemplo (se mantienen)
NOMBRES_MASCULINOS = [
    'Juan', 'Pedro', 'Luis', 'Carlos', 'Miguel', 'José', 'Antonio', 'Francisco',
    'Manuel', 'David', 'Javier', 'Daniel', 'Rafael', 'Fernando', 'Jorge',
    'Andrés', 'Sergio', 'Alberto', 'Roberto', 'Ricardo', 'Ángel', 'Alejandro'
]

NOMBRES_FEMENINOS = [
    'María', 'Ana', 'Carmen', 'Laura', 'Isabel', 'Patricia', 'Sofía', 'Elena',
    'Lucía', 'Paula', 'Andrea', 'Valentina', 'Gabriela', 'Carolina', 'Daniela',
    'Natalia', 'Camila', 'Mariana', 'Juliana', 'Catalina', 'Diana', 'Verónica'
]

APELLIDOS = [
    'García', 'Rodríguez', 'Martínez', 'López', 'González', 'Pérez', 'Sánchez',
    'Ramírez', 'Torres', 'Flores', 'Rivera', 'Gómez', 'Díaz', 'Cruz', 'Morales',
    'Jiménez', 'Hernández', 'Ruiz', 'Reyes', 'Álvarez', 'Romero', 'Vargas',
    'Castro', 'Ortiz', 'Ramos', 'Vega', 'Medina', 'Méndez', 'Silva', 'Rojas'
]

ASIGNATURAS_DATA = [
    ('Matemáticas', 'Álgebra, geometría y aritmética'),
    ('Lengua Castellana', 'Lectura, escritura y gramática'),
    ('Inglés', 'Idioma extranjero nivel básico-intermedio'),
    ('Ciencias Naturales', 'Biología, química y física'),
    ('Ciencias Sociales', 'Historia, geografía y civismo'),
    ('Educación Física', 'Deportes y actividad física'),
    ('Artes', 'Expresión artística y cultural'),
    ('Tecnología e Informática', 'Computación y tecnología'),
    ('Ética y Valores', 'Formación en valores y ética'),
    ('Religión', 'Formación religiosa'),
    ('Música', 'Teoría y práctica musical'),
    ('Emprendimiento', 'Formación empresarial y emprendimiento')
]

CURSOS_DATA = [
    '6A', '6B', '7A', '7B', '8A', '8B', '9A', '9B', '10A', '10B', '11A', '11B'
]

DIAS_SEMANA = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']

# --- UTILS ---

def get_or_create(model, defaults=None, **kwargs):
    """Obtiene o crea una instancia del modelo de forma idempotente"""
    # 1. Intenta encontrar la instancia por los kwargs (identificadores únicos)
    instance = model.query.filter_by(**kwargs).first()
    if instance:
        return instance, False # Ya existe
    
    # 2. Si no existe, crea una nueva instancia
    params = dict(kwargs)
    if defaults:
        params.update(defaults)
    
    # Intenta obtener el hash de la contraseña si se está creando un Usuario
    if model == Usuario and 'password_hash' not in params:
        # Se asume que 'password' es el campo para la contraseña plana
        password_plana = params.pop('password', '123456') 
        instance = model(**params)
        instance.set_password(password_plana)
    else:
        instance = model(**params)

    db.session.add(instance)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Intentar nuevamente la búsqueda después del rollback si hubo concurrencia
        instance = model.query.filter_by(**kwargs).first()
        if instance:
            return instance, False
            
        print(f"Error crítico al crear {model.__name__} con kwargs {kwargs}: {e}")
        return None, False
    return instance, True


# --- SEEDING FUNCTIONS ---

def seed_roles():
    """Crea los roles del sistema"""
    print('📋 Creando roles...')
    roles = {}
    for nombre in ['Super Admin', 'Profesor', 'Estudiante', 'Padre']:
        rol, _ = get_or_create(Rol, nombre=nombre)
        roles[nombre] = rol
    print('   ✅ Roles creados')
    return roles


def seed_sedes():
    """Crea las sedes del colegio"""
    print('🏫 Creando sedes...')
    sedes = [
        ('Sede Principal', 'Cra 10 # 15-20, Bogotá'),
        ('Sede Norte', 'Calle 100 # 25-30, Bogotá'),
    ]
    
    sedes_creadas = []
    for nombre, direccion in sedes:
        sede, _ = get_or_create(Sede, nombre=nombre, direccion=direccion)
        sedes_creadas.append(sede)
    
    print(f'   ✅ {len(sedes_creadas)} sedes creadas')
    return sedes_creadas


def seed_horarios_generales():
    """Crea horarios generales y bloques de horario asociados"""
    print('🕐 Creando horarios generales y bloques...')
    
    horarios_data = [
        ('Jornada Mañana', '2025-A', time(7, 0), time(12, 30), 45, 15),
        ('Jornada Tarde', '2025-A', time(13, 0), time(18, 0), 45, 15),
    ]
    
    horarios = []
    for nombre, periodo, hora_inicio, hora_fin, dur_clase, dur_descanso in horarios_data:
        horario, created = get_or_create(
            HorarioGeneral,
            nombre=nombre,
            periodo=periodo,
            horaInicio=hora_inicio,
            horaFin=hora_fin,
            diasSemana='["Lunes","Martes","Miércoles","Jueves","Viernes"]',
            duracion_clase=dur_clase,
            duracion_descanso=dur_descanso,
            activo=True
        )
        
        if created or not BloqueHorario.query.filter_by(horario_general_id=horario.id_horario).first(): 
            # Crear bloques de horario
            orden_global = 1
            for dia in DIAS_SEMANA:
                hora_actual = datetime.combine(date.today(), hora_inicio)
                
                # Bucle de Creación de bloques
                while hora_actual.time() < hora_fin:
                    hora_fin_bloque_dt = hora_actual + timedelta(minutes=dur_clase)
                    
                    if hora_fin_bloque_dt.time() > hora_fin: break # No exceder hora final
                    
                    get_or_create(BloqueHorario,
                        horario_general_id=horario.id_horario,
                        dia_semana=dia,
                        horaInicio=hora_actual.time(),
                        horaFin=hora_fin_bloque_dt.time(),
                        tipo='clase',
                        orden=orden_global,
                        nombre=f'Bloque {orden_global}',
                        class_type='normal'
                    )
                    
                    # Agregar tiempo de clase + descanso
                    hora_actual = hora_actual + timedelta(minutes=dur_clase + dur_descanso)
                    orden_global += 1
            
            db.session.commit()
        
        horarios.append(horario)
    
    print(f'   ✅ {len(horarios)} horarios generales y sus bloques creados')
    return horarios


def seed_cursos(sedes, horarios):
    """Crea los cursos"""
    print('📚 Creando cursos...')
    
    cursos = []
    for i, nombre_curso in enumerate(CURSOS_DATA):
        sede = sedes[i % len(sedes)]
        horario = horarios[i % len(horarios)]
        
        curso, _ = get_or_create(
            Curso,
            nombreCurso=nombre_curso,
            sedeId=sede.id_sede,
            horario_general_id=horario.id_horario
        )
        cursos.append(curso)
    
    print(f'   ✅ {len(cursos)} cursos creados')
    return cursos


def seed_asignaturas():
    """Crea las asignaturas"""
    print('📖 Creando asignaturas...')
    
    asignaturas = []
    for nombre, descripcion in ASIGNATURAS_DATA:
        asignatura, _ = get_or_create(
            Asignatura,
            nombre=nombre,
            descripcion=descripcion,
            estado='activa'
        )
        asignaturas.append(asignatura)
    
    print(f'   ✅ {len(asignaturas)} asignaturas creadas')
    return asignaturas


def seed_categorias_calificacion():
    """
    Crea categorías de calificación y la configuración mínima por asignatura.
    FIX: Se ajusta para NO intentar insertar 'id_categoria_fk' ni 'porcentaje' 
    en ConfiguracionCalificacion, resolviendo el 'InvalidRequestError'.
    """
    print('📊 Creando categorías de calificación...')
    
    categorias_data = [
        ('Parcial 1', '#1976d2', 25),
        ('Parcial 2', '#2196f3', 25),
        ('Talleres', '#2e7d32', 20),
        ('Participación', '#f57c00', 15),
        ('Proyecto Final', '#d32f2f', 15),
    ]
    
    categorias = []
    for nombre, color, porcentaje in categorias_data:
        # 1. Crear la CategoriaCalificacion
        cat, _ = get_or_create(
            CategoriaCalificacion,
            nombre=nombre,
            color=color,
            porcentaje=porcentaje
        )
        categorias.append(cat)
    
    # 2. Crear las configuraciones base (ConfiguracionCalificacion)
    for asignatura in Asignatura.query.all():
         get_or_create(
            ConfiguracionCalificacion,
            asignatura_id=asignatura.id_asignatura,
            defaults={
                'notaMinima': 0.00,
                'notaMaxima': 5.00,
                'notaMinimaAprobacion': 3.00
                # Se omiten 'id_categoria_fk' y 'porcentaje'
            }
        )

    print(f'   ✅ {len(categorias)} categorías y configuraciones de asignatura creadas')
    return categorias


def seed_salones(sedes):
    """Crea salones"""
    print('🚪 Creando salones...')
    
    tipos_salon = ['Aula', 'Laboratorio', 'Sala de Sistemas', 'Biblioteca']
    salones = []
    contador = 0
    
    for sede in sedes:
        prefijo = sede.nombre[:4].upper().replace(' ', '')
        
        for i in range(1, 16):
            contador += 1
            tipo = tipos_salon[i % len(tipos_salon)]
            capacidad = 35 if tipo == 'Aula' else 25
            
            nombre_salon = f'{prefijo}{contador:03d}'
            
            # Se usa id_sede_fk si existe en Salon
            salon, _ = get_or_create(
                Salon,
                nombre=nombre_salon,
                tipo=tipo,
                capacidad=capacidad,
                cantidad_sillas=capacidad,
                cantidad_mesas=capacidad // 2,
                id_sede_fk=sede.id_sede,
                estado='disponible'
            )
            salones.append(salon)
    
    print(f'   ✅ {len(salones)} salones creados')
    return salones


def seed_profesores(roles, asignaturas):
    """Crea 10 profesores y asigna asignaturas"""
    print('👨‍🏫 Creando profesores...')
    
    rol_profesor = roles['Profesor']
    profesores = []
    
    # Profesor con correo real (importante para pruebas)
    prof_real = Usuario.query.filter_by(correo='lopexangel24@gmail.com').first()
    if not prof_real:
        prof_real, _ = get_or_create(
            Usuario,
            no_identidad='1122334455', tipo_doc='CC', nombre='Ángel', apellido='López',
            correo='lopexangel24@gmail.com', id_rol_fk=rol_profesor.id_rol,
            defaults={
                'telefono': '3001112233', 'direccion': 'Calle 10 # 20-30', 
                'email_verified': True, 'password': '123456' # Se usa 'password' para set_password en get_or_create
            }
        )
    
    # Asignar asignaturas al profesor real (usando la relación M2M)
    if not prof_real.asignaturas:
        prof_real.asignaturas.append(asignaturas[0])
        prof_real.asignaturas.append(asignaturas[1])
        prof_real.asignaturas.append(asignaturas[3])
        db.session.commit()
    
    profesores.append(prof_real)
    
    # 9 profesores adicionales
    for i in range(1, 10):
        nombres = random.choice(NOMBRES_MASCULINOS if i % 2 == 0 else NOMBRES_FEMENINOS)
        apellido = random.choice(APELLIDOS)
        correo = f'profesor{i}@colegio.edu.co'
        
        profesor, _ = get_or_create(
            Usuario,
            correo=correo,
            defaults={
                'no_identidad': f'10{100000 + i}', 'tipo_doc': 'CC', 'nombre': nombres,
                'apellido': f'{apellido} {random.choice(APELLIDOS)}',
                'telefono': f'300{1000000 + i}', 'direccion': f'Calle {i*5} # {i*2}-{i*3}',
                'id_rol_fk': rol_profesor.id_rol, 'email_verified': True, 'password': '123456'
            }
        )
        
        # Asignar 2-3 asignaturas a cada profesor
        if not profesor.asignaturas:
            num_asignaturas = random.randint(2, 3)
            asignaturas_profesor = random.sample(asignaturas, num_asignaturas)
            for asignatura in asignaturas_profesor:
                profesor.asignaturas.append(asignatura)
            db.session.commit()
        
        profesores.append(profesor)
    
    print(f'   ✅ {len(profesores)} profesores creados')
    return profesores


def seed_padres(roles):
    """Crea 10 padres"""
    print('👨‍👩‍👧 Creando padres...')
    
    rol_padre = roles['Padre']
    padres = []
    
    # Padre con correo real
    padre_real = Usuario.query.filter_by(correo='carlosandresangelnacun@gmail.com').first()
    if not padre_real:
        padre_real, _ = get_or_create(
            Usuario,
            correo='carlosandresangelnacun@gmail.com',
            defaults={
                'no_identidad': '9988776655', 'tipo_doc': 'CC', 'nombre': 'Carlos Andrés', 'apellido': 'Ángel Nacún', # 🔑 SYNTAX ERROR CORREGIDO
                'telefono': '3012223344', 'direccion': 'Calle 10 # 20-30',
                'id_rol_fk': rol_padre.id_rol, 'email_verified': True, 'password': '123456'
            }
        )
    
    padres.append(padre_real)
    
    # 9 padres adicionales
    for i in range(1, 10):
        nombres = random.choice(NOMBRES_MASCULINOS if i % 2 == 0 else NOMBRES_FEMENINOS)
        apellido = random.choice(APELLIDOS)
        correo = f'padre{i}@gmail.com'
        
        padre, _ = get_or_create(
            Usuario,
            correo=correo,
            defaults={
                'no_identidad': f'20{100000 + i}', 'tipo_doc': 'CC', 'nombre': nombres,
                'apellido': f'{apellido} {random.choice(APELLIDOS)}',
                'telefono': f'301{1000000 + i}', 'direccion': f'Carrera {i*3} # {i*4}-{i*5}',
                'id_rol_fk': rol_padre.id_rol, 'email_verified': True, 'password': '123456'
            }
        )
        
        padres.append(padre)
    
    print(f'   ✅ {len(padres)} padres creados')
    return padres


def seed_estudiantes(roles, cursos, padres):
    """Crea 50 estudiantes y los matricula"""
    print('👨‍🎓 Creando 50 estudiantes...')
    
    rol_estudiante = roles['Estudiante']
    estudiantes = []
    
    # Estudiante con correo real
    est_real = Usuario.query.filter_by(correo='lopex8485@gmail.com').first()
    if not est_real:
        est_real, _ = get_or_create(
            Usuario,
            correo='lopex8485@gmail.com',
            defaults={
                'no_identidad': '5566778899', 'tipo_doc': 'TI', 'nombre': 'Carlos Andrés', 'apellido':'López Nacún',
                'telefono': '3004445566', 'direccion': 'Calle 10 # 20-30',
                'id_rol_fk': rol_estudiante.id_rol, 'email_verified': True, 'password': '123456'
            }
        )
    
    # Asignar padre al estudiante real (usando la relación M2M)
    padre_real = padres[0]
    if padre_real not in est_real.padres:
        est_real.padres.append(padre_real)
        db.session.commit()
    
    # Matricular al estudiante real en el primer curso (6A)
    get_or_create(
        Matricula,
        estudianteId=est_real.id_usuario,
        cursoId=cursos[0].id_curso,
        año=2025,
        defaults={'fecha_matricula': date.today()}
    )
    
    estudiantes.append(est_real)
    
    # 49 estudiantes adicionales
    for i in range(1, 50):
        nombres = random.choice(NOMBRES_MASCULINOS if i % 2 == 0 else NOMBRES_FEMENINOS)
        apellido1 = random.choice(APELLIDOS)
        apellido2 = random.choice(APELLIDOS)
        correo = f'estudiante{i}@colegio.edu.co'
        
        estudiante, _ = get_or_create(
            Usuario,
            correo=correo,
            defaults={
                'no_identidad': f'30{100000 + i}', 'tipo_doc': 'TI' if i % 3 != 0 else 'CC', 'nombre': nombres,
                'apellido': f'{apellido1} {apellido2}', 'telefono': f'302{1000000 + i}',
                'direccion': f'Avenida {i} # {i*2}-{i}', 'id_rol_fk': rol_estudiante.id_rol,
                'email_verified': True, 'password': '123456'
            }
        )
        
        # Asignar padre
        padre = padres[i % len(padres)]
        if padre not in estudiante.padres:
            estudiante.padres.append(padre)
            db.session.commit()
        
        # Matricular en un curso
        curso = cursos[i % len(cursos)]
        get_or_create(
            Matricula,
            estudianteId=estudiante.id_usuario,
            cursoId=curso.id_curso,
            año=2025,
            defaults={'fecha_matricula': date.today()}
        )
        
        estudiantes.append(estudiante)
    
    print(f'   ✅ {len(estudiantes)} estudiantes creados y matriculados')
    return estudiantes


def seed_clases(cursos, profesores, asignaturas):
    """Crea clases asignando profesores a cursos y asignaturas"""
    print('🎓 Creando clases...')
    
    clases = []
    for curso in cursos:
        # Asignar solo las asignaturas que tienen un profesor con ese curso
        # Esta lógica asegura que haya un profesor en la base de datos para la clase.
        asignaturas_profesoras = [a for a in asignaturas if any(a in p.asignaturas for p in profesores)]

        for asignatura in asignaturas_profesoras:
            profesores_asignatura = [p for p in profesores if asignatura in p.asignaturas]
            
            if profesores_asignatura:
                profesor = random.choice(profesores_asignatura)
                
                clase, _ = get_or_create(
                    Clase,
                    asignaturaId=asignatura.id_asignatura,
                    profesorId=profesor.id_usuario,
                    cursoId=curso.id_curso,
                    horarioId=curso.horario_general_id # Usar el FK correcto
                )
                clases.append(clase)
    
    print(f'   ✅ {len(clases)} clases creadas')
    return clases


def seed_calificaciones_estudiante_real(estudiante_real, asignaturas, categorias):
    """Genera calificaciones completas para el estudiante con correo real"""
    print('📝 Generando calificaciones para estudiante real...')
    count = 0
    for asignatura in asignaturas:
        for categoria in random.sample(categorias, min(random.randint(3, 4), len(categorias))):
            nota = round(random.uniform(3.5, 5.0), 1)
            get_or_create(
                Calificacion,
                estudianteId=estudiante_real.id_usuario,
                asignaturaId=asignatura.id_asignatura,
                categoriaId=categoria.id_categoria,
                defaults={
                    'valor': nota,
                    'nombre_calificacion': f'{categoria.nombre} - {asignatura.nombre}',
                    'observaciones': 'Buen desempeño' if nota >= 4.0 else 'Puede mejorar',
                    'fecha_registro': datetime.now()
                }
            )
            count += 1
    print(f'   ✅ {count} calificaciones para estudiante real')
    return count


def seed_calificaciones_otros(estudiantes, asignaturas, categorias):
    """Genera calificaciones para los demás estudiantes"""
    print('📝 Generando calificaciones para otros estudiantes...')
    count = 0
    for estudiante in estudiantes[1:]:
        asignaturas_estudiante = random.sample(asignaturas, random.randint(3, 5))
        for asignatura in asignaturas_estudiante:
            for categoria in random.sample(categorias, random.randint(2, 3)):
                nota = round(random.uniform(2.5, 5.0), 1)
                get_or_create(
                    Calificacion,
                    estudianteId=estudiante.id_usuario,
                    asignaturaId=asignatura.id_asignatura,
                    categoriaId=categoria.id_categoria,
                    defaults={
                        'valor': nota,
                        'nombre_calificacion': f'{categoria.nombre} - {asignatura.nombre}',
                        'observaciones': 'Evaluación registrada',
                        'fecha_registro': datetime.now()
                    }
                )
                count += 1
    print(f'   ✅ {count} calificaciones para otros estudiantes')
    return count


def seed_asistencias(estudiantes, clases):
    """Genera registros de asistencia"""
    print('✅ Generando asistencias...')
    
    estados = ['presente', 'ausente', 'tarde']
    count = 0
    
    for i in range(15):
        fecha = date.today() - timedelta(days=i)
        
        for estudiante in estudiantes:
            matricula = Matricula.query.filter_by(estudianteId=estudiante.id_usuario).first()
            if not matricula: continue
            
            clases_curso = [c for c in clases if c.cursoId == matricula.cursoId]
            
            for clase in random.sample(clases_curso, min(random.randint(3, 5), len(clases_curso))):
                if estudiante.correo == 'lopex8485@gmail.com':
                    estado = random.choices(estados, weights=[95, 3, 2])[0]
                else:
                    estado = random.choices(estados, weights=[85, 10, 5])[0]
                
                get_or_create(
                    Asistencia,
                    estudianteId=estudiante.id_usuario,
                    claseId=clase.id_clase,
                    fecha=fecha,
                    defaults={'estado': estado, 'excusa': False}
                )
                count += 1
    
    print(f'   ✅ {count} registros de asistencia generados')


def seed_horarios_curso(cursos, asignaturas, salones):
    """Asigna horarios específicos a los cursos"""
    print('📅 Asignando horarios a cursos...')
    
    count = 0
    bloques = BloqueHorario.query.all()
    
    for curso in cursos:
        # Asignar un subconjunto de asignaturas al curso
        asignaturas_curso = random.sample(asignaturas, min(8, len(asignaturas)))
        
        for asignatura in asignaturas_curso:
            dia = random.choice(DIAS_SEMANA)
            
            # Asignar un bloque de horario y un salón
            bloque = random.choice(bloques)
            salon = random.choice(salones)
            
            get_or_create(
                HorarioCurso,
                curso_id=curso.id_curso,
                asignatura_id=asignatura.id_asignatura,
                dia_semana=dia,
                hora_inicio=bloque.horaInicio,
                hora_fin=bloque.horaFin,
                defaults={
                    'horario_general_id': curso.horario_general_id,
                    'id_salon_fk': salon.id_salon
                }
            )
            count += 1
    
    print(f'   ✅ {count} horarios de curso asignados')


def seed_equipos(salones):
    """Crea 50 equipos vinculados a salones existentes"""
    print('Creando equipos...')
    
    TIPOS_EQUIPO = ['Computadora de Escritorio', 'Laptop', 'Tablet', 'Proyector', 'Impresora', 'Escáner', 'Servidor', 'Otro']
    SISTEMAS = ['Windows 11', 'Windows 10', 'Linux Ubuntu', 'Linux Mint', None]
    RAMS = ['4GB DDR3', '8GB DDR4', '16GB DDR4', '32GB DDR4']
    DISCOS = ['256GB SSD', '512GB SSD', '1TB SSD', '500GB HDD', '1TB HDD', '2TB HDD']
    ESTADOS = ['Disponible', 'En uso', 'Mantenimiento', 'Dañado']
    
    equipos_creados = 0
    for i in range(1, 51):
        tipo = random.choice(TIPOS_EQUIPO)
        es_computadora = tipo in ['Computadora de Escritorio', 'Laptop', 'Tablet', 'Servidor']
        so = random.choice([s for s in SISTEMAS if s is not None]) if es_computadora else None
        ram = random.choice(RAMS) if es_computadora else None
        disco = random.choice(DISCOS) if es_computadora else None
        referencia = f'EQ-{i:03d}'

        if tipo == 'Computadora de Escritorio': nombre = f'{random.choice(["Dell", "HP", "Lenovo"])} {random.choice(["i3", "i5", "i7"])}'
        elif tipo == 'Laptop': nombre = f'{random.choice(["Dell", "HP", "MacBook"])} {random.choice(["i5", "M1"])}'
        elif tipo == 'Proyector': nombre = f'{random.choice(["Epson", "BenQ"])} Proyector'
        else: nombre = random.choice(['Tablero Digital', 'Televisor 55"', 'Cámara IP', 'Router'])

        salon = random.choice(salones)
        fecha_adq = date.today() - timedelta(days=random.randint(30, 5 * 365))
        estado = random.choice(ESTADOS)

        equipo, created = get_or_create(
            Equipo, id_referencia=referencia,
            defaults={'nombre': nombre, 'tipo': tipo, 'id_salon_fk': salon.id_salon,
                      'sistema_operativo': so, 'ram': ram, 'disco_duro': disco,
                      'fecha_adquisicion': fecha_adq, 'estado': estado}
        )
        if created: equipos_creados += 1

    print(f'   ✅ {equipos_creados} equipos creados y vinculados a salones existentes')
    return Equipo.query.all()


def seed_incidentes_y_mantenimientos(equipos, sedes):
    """Genera incidentes y mantenimientos"""
    print('🔧 Generando incidentes y mantenimientos...')
    
    incidentes_count = 0
    mantenimientos_count = 0
    
    for equipo in random.sample(equipos, min(15, len(equipos))):
        get_or_create(
            Incidente, equipo_id=equipo.id_equipo,
            descripcion=random.choice(['No enciende correctamente', 'Pantalla con rayas', 'Muy lento']),
            sede=equipo.salon.sede.nombre,
            defaults={'prioridad': random.choice(['baja', 'media', 'alta']), 'estado': random.choice(['reportado', 'en_proceso', 'resuelto'])}
        )
        incidentes_count += 1
    
    for equipo in random.sample(equipos, min(20, len(equipos))):
        get_or_create(
            Mantenimiento, equipo_id=equipo.id_equipo, sede_id=equipo.salon.sede.id_sede,
            fecha_programada=date.today() + timedelta(days=random.randint(1, 30)),
            tipo=random.choice(['Preventivo', 'Correctivo']),
            defaults={'estado': 'pendiente', 'descripcion': 'Mantenimiento programado'}
        )
        mantenimientos_count += 1
    
    print(f'   ✅ {incidentes_count} incidentes y {mantenimientos_count} mantenimientos')


def seed_eventos():
    """Crea eventos del colegio"""
    print('📅 Creando eventos...')
    
    eventos_data = [
        ('Reunión de padres', 'Reunión informativa trimestral', 'Padre'),
        ('Día de la ciencia', 'Feria de ciencias y tecnología', 'Estudiante'),
        ('Consejo académico', 'Reunión del consejo académico', 'Profesor'),
    ]
    
    for i, (nombre, desc, rol) in enumerate(eventos_data):
        get_or_create(
            Evento, nombre=nombre, descripcion=desc,
            fecha=date.today() + timedelta(days=i*7), hora=time(9, 0), rol_destino=rol
        )
    
    print('   ✅ Eventos creados')


def seed_comunicaciones(profesores, padres):
    """Genera comunicaciones entre profesores y padres"""
    print('💬 Generando comunicaciones...')
    count = 0
    prof_real = next((p for p in profesores if p.correo == 'lopexangel24@gmail.com'), None)
    padre_real = next((p for p in padres if p.correo == 'carlosandresangelnacun@gmail.com'), None)
    
    if prof_real and padre_real:
        get_or_create(Comunicacion, remitente_id=prof_real.id_usuario, destinatario_id=padre_real.id_usuario,
            asunto='Seguimiento académico de Carlos Andrés',
            defaults={'mensaje': 'Estimado padre de familia, me complace informarle...', 'estado': 'inbox'}
        )
        count += 1
    
    for _ in range(15):
        profesor = random.choice(profesores)
        padre = random.choice(padres)
        get_or_create(Comunicacion, remitente_id=profesor.id_usuario, destinatario_id=padre.id_usuario,
            asunto=random.choice(['Seguimiento académico', 'Citación reunión', 'Informe de rendimiento']),
            defaults={'mensaje': 'Mensaje de seguimiento académico del estudiante.', 'estado': random.choice(['inbox', 'inbox', 'sent'])}
        )
        count += 1
    
    print(f'   ✅ {count} comunicaciones generadas')


def seed_notificaciones(estudiantes, padre_real):
    """Genera notificaciones para estudiantes y el padre real"""
    print('🔔 Generando notificaciones...')
    
    tipos = ['calificacion', 'asistencia', 'evento', 'comunicacion']
    count = 0
    est_real = next((e for e in estudiantes if e.correo == 'lopex8485@gmail.com'), None)
    
    if est_real:
        for _ in range(5):
            get_or_create(
                Notificacion, usuario_id=est_real.id_usuario, titulo=f'Nueva notificación',
                mensaje=f'Tienes una actualización en {random.choice(tipos)}',
                tipo=random.choice(tipos), defaults={'leida': random.choice([True, False])}
            )
            count += 1
    
    if padre_real:
        for _ in range(3):
            get_or_create(
                Notificacion, usuario_id=padre_real.id_usuario, titulo='Actualización académica',
                mensaje='Se han registrado nuevas calificaciones', tipo='calificacion', defaults={'leida': False}
            )
            count += 1
    
    for estudiante in random.sample(estudiantes[1:], min(20, len(estudiantes)-1)):
        for _ in range(random.randint(1, 3)):
            get_or_create(
                Notificacion, usuario_id=estudiante.id_usuario, titulo=f'Nueva notificación',
                mensaje=f'Tienes una actualización en {random.choice(tipos)}',
                tipo=random.choice(tipos), defaults={'leida': random.choice([True, False])}
            )
            count += 1
    
    print(f'   ✅ {count} notificaciones generadas')


def seed_votaciones(estudiantes):
    """Crea candidatos y votaciones"""
    print('🗳️ Creando sistema de votaciones...')
    
    candidatos_data = [
        ('María Fernanda Gómez', 'A1', 'Mejorar bibliotecas y zonas de estudio', 'Personero'),
        ('Juan Pablo Martínez', 'B2', 'Más eventos deportivos y recreativos', 'Personero'),
        ('Ana Sofía Torres', 'C3', 'Apoyo en tecnología y conectividad', 'Personero'),
    ]
    
    candidatos = []
    for nombre, tarjeton, propuesta, categoria in candidatos_data:
        cand, _ = get_or_create(
            Candidato, nombre=nombre, tarjeton=tarjeton, propuesta=propuesta,
            categoria=categoria, defaults={'foto': 'default.jpg', 'votos': 0}
        )
        candidatos.append(cand)
    
    # El estudiante real vota
    est_real = next((e for e in estudiantes if e.correo == 'lopex8485@gmail.com'), None)
    count = 0
    if est_real and candidatos:
        candidato = candidatos[0]
        voto, created = get_or_create(Voto, estudiante_id=est_real.id_usuario, candidato_id=candidato.id_candidato)
        if created:
            candidato.votos += 1
            db.session.commit() # Commit inmediato para reflejar el cambio en la base de datos
            count += 1
    
    # Otros estudiantes votan
    for estudiante in random.sample(estudiantes[1:], min(25, len(estudiantes)-1)):
        candidato = random.choice(candidatos)
        voto, created = get_or_create(Voto, estudiante_id=estudiante.id_usuario, candidato_id=candidato.id_candidato)
        if created:
            candidato.votos += 1
            count += 1
    
    db.session.commit()
    print(f'   ✅ {len(candidatos)} candidatos y {count} votos creados')


# --- MAIN EXECUTION ---

def seed_all():
    """Ejecuta todo el proceso de seeding dentro del contexto de Flask."""
    with app.app_context():
        print('\n' + '='*60)
        print('🌱 INICIANDO SEEDING DE DATOS (50 ESTUDIANTES)')
        print('='*60 + '\n')
        
        # db.drop_all() # Descomentar solo si quieres borrar todas las tablas antes de empezar
        db.create_all()
        print('✅ Tablas de base de datos verificadas/creadas.\n')
        
        roles = seed_roles()
        sedes = seed_sedes()
        horarios = seed_horarios_generales()
        cursos = seed_cursos(sedes, horarios)
        asignaturas = seed_asignaturas()
        
        # FUNCIÓN CORREGIDA: Se ajusta a la estructura actual de ConfiguracionCalificacion
        categorias = seed_categorias_calificacion() 
        
        salones = seed_salones(sedes)
        
        profesores = seed_profesores(roles, asignaturas)
        padres = seed_padres(roles) # FUNCIÓN CON EL SYNTAX ERROR CORREGIDO
        estudiantes = seed_estudiantes(roles, cursos, padres)
        
        clases = seed_clases(cursos, profesores, asignaturas)
        
        est_real = estudiantes[0]
        seed_calificaciones_estudiante_real(est_real, asignaturas, categorias)
        seed_calificaciones_otros(estudiantes, asignaturas, categorias)
        
        seed_asistencias(estudiantes, clases)
        seed_horarios_curso(cursos, asignaturas, salones)
        
        equipos = seed_equipos(salones)
        seed_incidentes_y_mantenimientos(equipos, sedes)
        
        seed_eventos()
        seed_comunicaciones(profesores, padres)
        
        padre_real = padres[0]
        seed_notificaciones(estudiantes, padre_real)
        seed_votaciones(estudiantes)
        
        print('\n' + '='*60)
        print('✅ SEEDING COMPLETADO EXITOSAMENTE')
        print('='*60)
        print('\n📊 RESUMEN:')
        print(f'   - {len(sedes)} sedes')
        print(f'   - {len(cursos)} cursos')
        print(f'   - {len(asignaturas)} asignaturas')
        print(f'   - {len(profesores)} profesores')
        print(f'   - {len(padres)} padres')
        print(f'   - {len(estudiantes)} estudiantes')
        print(f'   - {len(clases)} clases')
        print('\n🔐 CREDENCIALES USUARIOS REALES:')
        print('   Profesor: lopexangel24@gmail.com / 123456')
        print('   Estudiante: lopex8485@gmail.com / 123456')
        print('   Padre: carlosandresangelnacun@gmail.com / 123456')
        print('\n💡 Todos los usuarios tienen contraseña: 123456')
        print()


if __name__ == '__main__':
    seed_all()