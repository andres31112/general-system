# 📚 SISTEMA DE PERIODOS ACADÉMICOS - DOCUMENTACIÓN COMPLETA
## Versión Optimizada

---

## 📖 ÍNDICE
1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Estructura de Base de Datos](#estructura-de-base-de-datos)
3. [Flujo Completo del Sistema](#flujo-completo-del-sistema)
4. [Casos de Uso](#casos-de-uso)
5. [Interfaces de Usuario](#interfaces-de-usuario)
6. [Implementación Técnica](#implementación-técnica)

---

## 1. RESUMEN EJECUTIVO

### Objetivo
Implementar un sistema divisor por periodos o trimestres académicos donde:
- Al final de cada trimestre hay un cierre de notas
- Se puede iniciar un nuevo trimestre/periodo
- El administrador gestiona fechas límite
- Notificaciones automáticas a usuarios (inicio/fin de periodos)
- Finalización del ciclo escolar con promoción automática de estudiantes
- Generación de reportes (notas, asistencias, etc.)

### Decisiones de Diseño
- ✅ **Solo 2 tablas nuevas:** `ciclo_academico` y `periodo_academico`
- ✅ **Reutilizar tablas existentes:** Se extienden 5 tablas con nuevos campos
- ✅ **Sin tablas redundantes:** Usa `Notificacion` y `ReporteCalificaciones` existentes
- ✅ **Historial integrado:** La tabla `matricula` ahora guarda historial completo

---

## 2. ESTRUCTURA DE BASE DE DATOS

### 2.1 NUEVAS TABLAS (Solo 2)

#### A) Tabla: `ciclo_academico`
**Propósito:** Representa el año escolar completo (ej: 2024-2025)

```python
class CicloAcademico(db.Model):
    __tablename__ = 'ciclo_academico'
    
    id_ciclo = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    estado = db.Column(db.Enum('planificado', 'activo', 'cerrado'), default='planificado')
    activo = db.Column(db.Boolean, default=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    periodos = relationship('PeriodoAcademico', back_populates='ciclo')
    matriculas = relationship('Matricula', back_populates='ciclo_academico')
    notificaciones = relationship('Notificacion', back_populates='ciclo_academico')
    reportes = relationship('ReporteCalificaciones', back_populates='ciclo_academico')
```

**Ejemplo:**
```
id: 1
nombre: "Año Escolar 2024-2025"
fecha_inicio: 2024-02-05
fecha_fin: 2024-11-30
estado: activo
activo: True
```

---

#### B) Tabla: `periodo_academico`
**Propósito:** Representa cada trimestre/periodo dentro del ciclo

```python
class PeriodoAcademico(db.Model):
    __tablename__ = 'periodo_academico'
    
    id_periodo = db.Column(db.Integer, primary_key=True)
    ciclo_academico_id = db.Column(db.Integer, db.ForeignKey('ciclo_academico.id_ciclo'))
    numero_periodo = db.Column(db.Integer, nullable=False)  # 1, 2, 3
    nombre = db.Column(db.String(100), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    fecha_cierre_notas = db.Column(db.Date, nullable=False)
    estado = db.Column(db.Enum('planificado', 'activo', 'en_cierre', 'cerrado'), default='planificado')
    dias_notificacion_anticipada = db.Column(db.Integer, default=7)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    ciclo = relationship('CicloAcademico', back_populates='periodos')
    calificaciones = relationship('Calificacion', back_populates='periodo_academico')
    asistencias = relationship('Asistencia', back_populates='periodo_academico')
    notificaciones = relationship('Notificacion', back_populates='periodo_academico')
    reportes = relationship('ReporteCalificaciones', back_populates='periodo_academico')
```

**Ejemplo:**
```
Periodo 1: "Primer Trimestre"
  fecha_inicio: 2024-02-05, fecha_fin: 2024-05-10
  fecha_cierre_notas: 2024-05-08
  dias_notificacion: 7, estado: activo

Periodo 2: "Segundo Trimestre"
  fecha_inicio: 2024-05-13, fecha_fin: 2024-08-16
  estado: planificado

Periodo 3: "Tercer Trimestre"
  fecha_inicio: 2024-08-19, fecha_fin: 2024-11-30
  estado: planificado
```

---

### 2.2 TABLAS EXTENDIDAS (5 tablas)

#### C) `matricula` - Nuevos campos

```python
# ✅ NUEVOS CAMPOS AGREGADOS:
ciclo_academico_id = db.Column(db.Integer, db.ForeignKey('ciclo_academico.id_ciclo'), nullable=True)
estado_matricula = db.Column(db.Enum('activa', 'inactiva', 'finalizada', 'retirada'), default='activa')
promedio_final = db.Column(db.Numeric(5,2), nullable=True)
estado_promocion = db.Column(db.Enum('aprobado', 'reprobado', 'graduado', 'en_curso', 'retirado'), nullable=True)
curso_promocion_id = db.Column(db.Integer, db.ForeignKey('curso.id_curso'), nullable=True)
fecha_promocion = db.Column(db.DateTime, nullable=True)
observaciones_cierre = db.Column(db.Text, nullable=True)

# Relaciones
ciclo_academico = relationship('CicloAcademico', back_populates='matriculas')
curso_promocion = relationship('Curso', foreign_keys=[curso_promocion_id])
```

**Propósito:** Ahora guarda historial académico completo (aprobó/reprobó, promoción)

**Evolución de datos:**
```
INICIO CICLO:
  estudiante_id: 10, curso_id: 5 (10° A), estado: activa, promocion: en_curso

FIN CICLO (aprueba):
  promedio_final: 4.2, estado: finalizada, promocion: aprobado
  curso_promocion_id: 6 (11° A)

NUEVO CICLO:
  estudiante_id: 10, curso_id: 6 (11° A), estado: activa
```

---

#### D) `calificacion` - Nuevo campo

```python
# ✅ NUEVO CAMPO:
periodo_academico_id = db.Column(db.Integer, db.ForeignKey('periodo_academico.id_periodo'), nullable=True)
periodo_academico = relationship('PeriodoAcademico', back_populates='calificaciones')
```

**Propósito:** Cada nota está vinculada a un periodo específico

---

#### E) `asistencia` - Nuevo campo

```python
# ✅ NUEVO CAMPO:
periodo_academico_id = db.Column(db.Integer, db.ForeignKey('periodo_academico.id_periodo'), nullable=True)
periodo_academico = relationship('PeriodoAcademico', back_populates='asistencias')
```

---

#### F) `notificacion` - Nuevos campos

```python
# ✅ NUEVOS CAMPOS:
periodo_academico_id = db.Column(db.Integer, db.ForeignKey('periodo_academico.id_periodo'), nullable=True)
ciclo_academico_id = db.Column(db.Integer, db.ForeignKey('ciclo_academico.id_ciclo'), nullable=True)
tipo_evento = db.Column(db.Enum('inicio_periodo', 'proximidad_cierre', 'cierre_periodo', 
                                 'inicio_ciclo', 'fin_ciclo', 'promocion'), nullable=True)
programada_para = db.Column(db.DateTime, nullable=True)
enviada = db.Column(db.Boolean, default=False)

# Relaciones
periodo_academico = relationship('PeriodoAcademico', back_populates='notificaciones')
ciclo_academico = relationship('CicloAcademico', back_populates='notificaciones')
```

**Ejemplos de notificaciones:**
- Inicio de periodo
- Recordatorio de cierre (X días antes)
- Cierre de periodo
- Resultados de promoción

---

#### G) `ReporteCalificaciones` - Nuevos campos

```python
# ✅ NUEVOS CAMPOS:
periodo_academico_id = db.Column(db.Integer, db.ForeignKey('periodo_academico.id_periodo'), nullable=True)
ciclo_academico_id = db.Column(db.Integer, db.ForeignKey('ciclo_academico.id_ciclo'), nullable=True)
tipo_reporte = db.Column(db.Enum('periodo', 'ciclo_completo', 'notas', 'asistencias', 
                                  'general', 'promocion', 'curso', 'estudiante'), nullable=True)
formato_archivo = db.Column(db.Enum('pdf', 'excel', 'csv'), nullable=True)
ruta_archivo = db.Column(db.String(500), nullable=True)
nombre_archivo = db.Column(db.String(200), nullable=True)
generado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=True)
```

**Tipos de reportes:**
- Por periodo (curso/asignatura)
- Ciclo completo (certificados)
- Asistencias
- Promoción general

---

## 3. FLUJO COMPLETO DEL SISTEMA

### FASE 1: Configuración Inicial (Admin)

```
1. Admin crea Ciclo Académico
   └─> "Año Escolar 2024-2025" (05/02/2024 - 30/11/2024)

2. Admin crea 3 Periodos
   ├─> Periodo 1: 05/02 - 10/05/2024
   ├─> Periodo 2: 13/05 - 16/08/2024
   └─> Periodo 3: 19/08 - 30/11/2024

3. Admin activa el Ciclo
   └─> Sistema activa Periodo 1 automáticamente
       Sistema envía notificación de inicio a todos
```

### FASE 2: Durante el Periodo

```
PROFESORES:
├─> Registran asistencias (vinculadas al periodo actual)
├─> Ingresar notas (vinculadas al periodo actual)
└─> Reciben notificación: "Cierre en 7 días"

ESTUDIANTES/PADRES:
├─> Consultan notas del periodo actual
└─> Ven asistencias del periodo

SISTEMA (Automático):
├─> 7 días antes → Notifica a profesores
└─> Fecha de cierre → Notifica cierre
```

### FASE 3: Cierre de Periodo (Admin)

```
Admin: "Cerrar Periodo 1"

Sistema ejecuta:
1. Valida que todas las notas estén ingresadas
2. Calcula promedios del periodo
3. Genera reportes (PDF, Excel)
4. Cambia estado a "cerrado"
5. Bloquea edición de notas del periodo
6. Activa Periodo 2
7. Notifica inicio del nuevo periodo
```

### FASE 4: Finalización de Ciclo (Admin)

```
Admin: "Finalizar Año Escolar"

Sistema ejecuta:
1. Cierra último periodo (si no está cerrado)

2. Calcula promedios finales por estudiante

3. Proceso de Promoción:
   Para cada estudiante:
     SI promedio >= nota_minima:
       - Actualiza matrícula: finalizada, aprobado
       - Crea nueva matrícula en curso superior
       - Notifica: "Promovido a 11°"
     
     SI NO:
       - Actualiza matrícula: finalizada, reprobado
       - Crea nueva matrícula en mismo curso
       - Notifica: "Debe repetir grado"

4. Genera reportes finales:
   ├─> Certificados individuales (PDF)
   ├─> Reporte de promoción (Excel)
   └─> Estadísticas generales (Excel)

5. Cierra ciclo: estado = "cerrado"

6. Notifica resultados a todos
```

---

## 4. CASOS DE USO

### Caso 1: Consultar notas históricas

**Padre quiere ver notas del Periodo 1:**
```sql
SELECT * FROM calificacion 
WHERE estudianteId = 10 
AND periodo_academico_id = 1
```

**Ver notas de todo el año:**
```sql
SELECT * FROM calificacion c
JOIN periodo_academico p ON c.periodo_academico_id = p.id_periodo
WHERE c.estudianteId = 10 
AND p.ciclo_academico_id = 1
```

### Caso 2: Estudiante repite y luego aprueba

```
AÑO 2024 (Ciclo 1) - REPRUEBA:
├─> Matricula: curso 10° A, promedio: 2.5
└─> estado_promocion: "reprobado"

AÑO 2025 (Ciclo 2) - APRUEBA:
├─> Nueva Matricula: curso 10° A (repite)
└─> promedio: 4.0, promocion: "aprobado"

AÑO 2026 (Ciclo 3):
└─> Nueva Matricula: curso 11° A
```

### Caso 3: Generar certificado individual

```python
1. Buscar matrícula del estudiante en el ciclo
2. Obtener notas de todos los periodos
3. Calcular promedios por periodo
4. Generar PDF con:
   - Datos del estudiante
   - Notas por asignatura y periodo
   - Promedio final
   - Resultado: APROBADO/REPROBADO
5. Guardar en ReporteCalificaciones
```

---

## 5. INTERFACES DE USUARIO

### Panel del Administrador

```
┌─────────────────────────────────────────┐
│  GESTIÓN DE CICLOS Y PERIODOS           │
├─────────────────────────────────────────┤
│  📅 Ciclo Actual: Año 2024-2025         │
│     Estado: ● Activo                    │
│                                         │
│  PERIODOS:                              │
│  ✓ Periodo 1: CERRADO [Ver Reportes]   │
│  ● Periodo 2: ACTIVO [Cerrar Periodo]   │
│  ○ Periodo 3: PLANIFICADO              │
│                                         │
│  [🔔 Notificaciones]                    │
│  [📊 Estadísticas]                      │
│  [🏁 Finalizar Año Escolar]             │
└─────────────────────────────────────────┘
```

### Panel del Profesor

```
┌─────────────────────────────────────────┐
│  NOTAS - Matemáticas 10° A             │
├─────────────────────────────────────────┤
│  Periodo: [▼ Periodo 2 (Activo)]        │
│  ⚠️ Cierre: 14/08/2024 (en 10 días)    │
│                                         │
│  [Tabla de notas por estudiante]        │
│                                         │
│  📜 Ver histórico: [Periodo 1▼]         │
└─────────────────────────────────────────┘
```

### Panel del Padre/Estudiante

```
┌─────────────────────────────────────────┐
│  CALIFICACIONES - Juan Pérez            │
├─────────────────────────────────────────┤
│  Periodo: [▼ Periodo 2 (Activo)]        │
│                                         │
│  Matemáticas - Promedio: 4.3            │
│  Español - Promedio: 4.0                │
│                                         │
│  HISTÓRICO:                             │
│  Periodo 1: 4.4 [Ver detalle]           │
│  Periodo 2: En curso...                 │
│                                         │
│  [📄 Descargar Boletín]                 │
└─────────────────────────────────────────┘
```

---

## 6. IMPLEMENTACIÓN TÉCNICA

### 6.1 Archivos a Crear/Modificar

**Nuevos archivos:**
```
controllers/models.py - Agregar 2 nuevas tablas + extender 5 existentes
routes/admin_periodos.py - Rutas para gestión de ciclos/periodos
services/periodo_service.py - Lógica de negocios
services/promocion_service.py - Lógica de promoción automática
services/reporte_service.py - Generación de reportes
templates/admin/periodos/ - Interfaces de admin
```

**Modificar:**
```
routes/profesor.py - Agregar selector de periodo
routes/padres.py - Agregar consulta por periodo
templates/profesor/* - Agregar selector de periodo
templates/padres/* - Agregar selector de periodo
```

### 6.2 Servicios Principales

**periodo_service.py:**
- `crear_ciclo()`
- `crear_periodo()`
- `activar_ciclo()`
- `cerrar_periodo()`
- `obtener_periodo_activo()`

**promocion_service.py:**
- `calcular_promedio_final()`
- `procesar_promocion()`
- `promover_estudiante()`
- `finalizar_ciclo()`

**reporte_service.py:**
- `generar_reporte_periodo()`
- `generar_certificado_individual()`
- `generar_reporte_promocion()`
- `generar_estadisticas_ciclo()`

### 6.3 Notificaciones Automáticas

**Proceso automatizado (Celery/Cron):**
```python
# Verificar diariamente:
1. ¿Hay periodo que inicia hoy? → Notificar
2. ¿Hay cierre en X días? → Notificar a profesores
3. ¿Hay notificaciones programadas? → Enviar
```

---

## 7. VENTAJAS DEL SISTEMA

✅ **Solo 2 tablas nuevas** - Mínima complejidad  
✅ **Reutiliza infraestructura** - Usa tablas existentes  
✅ **Historial completo** - Toda la trayectoria en `matricula`  
✅ **Consultas eficientes** - Menos joins  
✅ **Automatización** - Notificaciones y promoción automáticas  
✅ **Flexible** - Soporta bimestres/trimestres/cuatrimestres  
✅ **Escalable** - Fácil agregar funcionalidades  
✅ **Trazabilidad** - Reportes detallados  

---

## 8. PRÓXIMOS PASOS

1. ✅ Revisar y aprobar este diseño
2. Crear modelos en `models.py`
3. Crear migración de base de datos
4. Implementar servicios de lógica
5. Crear rutas del admin
6. Crear interfaces de usuario
7. Implementar notificaciones automáticas
8. Pruebas completas
9. Documentación de usuario

---

**Fecha de creación:** Octubre 2024  
**Versión:** 1.0 Optimizada  
**Estado:** Propuesta para aprobación

