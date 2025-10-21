# 📝 ARCHIVOS A MODIFICAR - SISTEMA DE PERIODOS ACADÉMICOS

## 📊 RESUMEN GENERAL

| Categoría | Archivos Nuevos | Archivos Modificados |
|-----------|-----------------|----------------------|
| **Backend (Python)** | 4 | 5 |
| **Frontend (HTML)** | 8 | 12 |
| **Frontend (JS)** | 4 | 5 |
| **Frontend (CSS)** | 4 | 0 |
| **Otros** | 1 | 2 |
| **TOTAL** | **21 nuevos** | **24 modificados** |

---

## 🔧 1. BACKEND - PYTHON/FLASK

### 1.1 ARCHIVOS A MODIFICAR (5 archivos)

#### ✏️ `controllers/models.py`
**Cambios:**
- ✅ Agregar 2 nuevas clases/modelos:
  - `CicloAcademico`
  - `PeriodoAcademico`
  
- ✅ Extender 5 modelos existentes:
  - `Matricula` → agregar 7 campos nuevos (ciclo_academico_id, estado_matricula, promedio_final, etc.)
  - `Calificacion` → agregar 1 campo (periodo_academico_id)
  - `Asistencia` → agregar 1 campo (periodo_academico_id)
  - `Notificacion` → agregar 4 campos (periodo_academico_id, ciclo_academico_id, tipo_evento, programada_para, enviada)
  - `ReporteCalificaciones` → agregar 6 campos (periodo_academico_id, ciclo_academico_id, tipo_reporte, formato_archivo, ruta_archivo, nombre_archivo, generado_por_id)

- ✅ Agregar relationships a todos los modelos relacionados

**Líneas estimadas:** ~150 líneas nuevas

---

#### ✏️ `routes/admin.py`
**Cambios:**
- ✅ Agregar rutas para gestión de ciclos académicos:
  ```python
  @admin_bp.route('/ciclos_academicos')
  @admin_bp.route('/ciclos_academicos/crear', methods=['POST'])
  @admin_bp.route('/ciclos_academicos/<int:id>/editar', methods=['PUT'])
  @admin_bp.route('/ciclos_academicos/<int:id>/activar', methods=['POST'])
  @admin_bp.route('/ciclos_academicos/<int:id>/cerrar', methods=['POST'])
  ```

- ✅ Agregar rutas para gestión de periodos:
  ```python
  @admin_bp.route('/periodos_academicos')
  @admin_bp.route('/periodos_academicos/crear', methods=['POST'])
  @admin_bp.route('/periodos_academicos/<int:id>/editar', methods=['PUT'])
  @admin_bp.route('/periodos_academicos/<int:id>/cerrar', methods=['POST'])
  @admin_bp.route('/periodos_academicos/activo')
  ```

- ✅ Agregar rutas para cierre de ciclo y promoción:
  ```python
  @admin_bp.route('/ciclos/<int:id>/finalizar', methods=['POST'])
  @admin_bp.route('/ciclos/<int:id>/promocion', methods=['POST'])
  @admin_bp.route('/ciclos/<int:id>/reportes')
  ```

- ✅ Agregar rutas para gestión de notificaciones de periodos:
  ```python
  @admin_bp.route('/periodos/<int:id>/notificaciones')
  @admin_bp.route('/periodos/<int:id>/notificaciones/programar', methods=['POST'])
  ```

**Líneas estimadas:** ~400 líneas nuevas

---

#### ✏️ `routes/profesor.py`
**Cambios:**
- ✅ Modificar rutas de registro de notas para incluir periodo:
  - `registrar_calificacion()` → agregar parámetro periodo_academico_id
  - `editar_calificacion()` → validar que periodo esté activo
  - `api_obtener_calificaciones()` → filtrar por periodo

- ✅ Modificar rutas de asistencias para incluir periodo:
  - `registrar_asistencia()` → agregar parámetro periodo_academico_id
  - `api_obtener_asistencias()` → filtrar por periodo

- ✅ Agregar rutas para selector de periodo:
  ```python
  @profesor_bp.route('/api/periodos/activo')
  @profesor_bp.route('/api/periodos/disponibles')
  @profesor_bp.route('/api/periodos/<int:id>/estadisticas')
  ```

- ✅ Modificar rutas de reportes:
  - `generar_reporte()` → permitir filtrar por periodo

**Líneas estimadas:** ~200 líneas modificadas/agregadas

---

#### ✏️ `routes/padres.py`
**Cambios:**
- ✅ Modificar APIs para consultas por periodo:
  - `api_promedios_estudiante()` → agregar filtro por periodo
  - `api_asistencia_estudiante()` → agregar filtro por periodo
  
- ✅ Agregar rutas para consultas históricas:
  ```python
  @padre_bp.route('/api/estudiante/<int:id>/notas/periodo/<int:periodo_id>')
  @padre_bp.route('/api/estudiante/<int:id>/asistencias/periodo/<int:periodo_id>')
  @padre_bp.route('/api/estudiante/<int:id>/historial_academico')
  @padre_bp.route('/api/estudiante/<int:id>/certificado/<int:ciclo_id>')
  ```

- ✅ Modificar dashboard para mostrar datos del periodo actual:
  - `dashboard()` → filtrar por periodo activo

**Líneas estimadas:** ~150 líneas modificadas/agregadas

---

#### ✏️ `routes/estudiantes.py`
**Cambios:**
- ✅ Modificar dashboard para mostrar periodo actual
- ✅ Agregar rutas para consultar historial por periodos:
  ```python
  @estudiante_bp.route('/api/mis_notas/periodo/<int:periodo_id>')
  @estudiante_bp.route('/api/mis_asistencias/periodo/<int:periodo_id>')
  @estudiante_bp.route('/api/mi_historial_academico')
  ```

- ✅ Agregar ruta para descargar certificados:
  ```python
  @estudiante_bp.route('/descargar_certificado/<int:ciclo_id>')
  ```

**Líneas estimadas:** ~100 líneas modificadas/agregadas

---

### 1.2 ARCHIVOS NUEVOS A CREAR (4 archivos)

#### 🆕 `services/periodo_service.py`
**Contenido:**
```python
# Servicios para gestión de ciclos y periodos
- crear_ciclo_academico()
- crear_periodo_academico()
- activar_ciclo()
- activar_periodo()
- cerrar_periodo()
- obtener_periodo_activo()
- obtener_ciclo_activo()
- validar_fechas_periodo()
- verificar_notas_completas()
```
**Líneas estimadas:** ~300 líneas

---

#### 🆕 `services/promocion_service.py`
**Contenido:**
```python
# Servicios para proceso de promoción
- calcular_promedio_final_estudiante()
- calcular_promedio_periodo()
- procesar_promocion_estudiante()
- promover_estudiante()
- reprobar_estudiante()
- graduar_estudiante()
- finalizar_ciclo_academico()
- obtener_curso_siguiente()
- generar_historial_academico()
```
**Líneas estimadas:** ~400 líneas

---

#### 🆕 `services/reporte_service.py`
**Contenido:**
```python
# Servicios para generación de reportes
- generar_reporte_periodo()
- generar_reporte_ciclo()
- generar_certificado_individual()
- generar_reporte_promocion()
- generar_reporte_asistencias()
- generar_estadisticas_generales()
- exportar_a_pdf()
- exportar_a_excel()
- exportar_a_csv()
```
**Líneas estimadas:** ~500 líneas

---

#### 🆕 `services/notificacion_periodo_service.py`
**Contenido:**
```python
# Servicios para notificaciones automáticas de periodos
- programar_notificacion_inicio_periodo()
- programar_notificacion_cierre()
- enviar_notificacion_proximidad_cierre()
- enviar_notificacion_cierre_periodo()
- enviar_notificacion_promocion()
- procesar_notificaciones_programadas()
- notificar_masivamente()
```
**Líneas estimadas:** ~250 líneas

---

#### ✏️ `services/notification_service.py` (Modificar existente)
**Cambios:**
- ✅ Agregar funciones para notificaciones de periodos:
  ```python
  - notificar_inicio_periodo()
  - notificar_cierre_periodo()
  - notificar_resultado_promocion()
  ```
**Líneas estimadas:** ~100 líneas agregadas

---

#### ✏️ `services/email_service.py` (Modificar existente)
**Cambios:**
- ✅ Agregar templates de emails para:
  - Email de inicio de periodo
  - Email de cierre de periodo
  - Email de resultado de promoción
  - Email de certificado disponible
**Líneas estimadas:** ~50 líneas agregadas

---

## 🎨 2. FRONTEND - TEMPLATES HTML

### 2.1 TEMPLATES DE ADMIN - NUEVOS (6 archivos)

#### 🆕 `templates/superadmin/gestion_academica/ciclos_periodos.html`
**Contenido:**
- Vista principal de gestión de ciclos y periodos
- Lista de ciclos académicos
- Lista de periodos por ciclo
- Botones de acciones (crear, editar, activar, cerrar)
**Líneas estimadas:** ~400 líneas

---

#### 🆕 `templates/superadmin/gestion_academica/crear_ciclo.html`
**Contenido:**
- Formulario para crear nuevo ciclo académico
- Validaciones de fechas
- Configuración inicial
**Líneas estimadas:** ~200 líneas

---

#### 🆕 `templates/superadmin/gestion_academica/crear_periodo.html`
**Contenido:**
- Formulario para crear nuevo periodo
- Selector de ciclo académico
- Configuración de fechas y notificaciones
**Líneas estimadas:** ~250 líneas

---

#### 🆕 `templates/superadmin/gestion_academica/cierre_periodo.html`
**Contenido:**
- Panel de cierre de periodo
- Checklist de validaciones
- Vista previa de reportes a generar
- Confirmación de cierre
**Líneas estimadas:** ~300 líneas

---

#### 🆕 `templates/superadmin/gestion_academica/finalizacion_ciclo.html`
**Contenido:**
- Panel de finalización de ciclo escolar
- Resumen de estudiantes (aprobados/reprobados)
- Configuración de promoción automática
- Generación de reportes finales
**Líneas estimadas:** ~400 líneas

---

#### 🆕 `templates/superadmin/gestion_academica/notificaciones_periodo.html`
**Contenido:**
- Panel de configuración de notificaciones
- Lista de notificaciones programadas
- Configuración de días de anticipación
- Destinatarios por rol
**Líneas estimadas:** ~300 líneas

---

### 2.2 TEMPLATES DE ADMIN - A MODIFICAR (2 archivos)

#### ✏️ `templates/superadmin/gestion_academica/dashboard.html`
**Cambios:**
- ✅ Agregar widget de "Ciclo Actual"
- ✅ Agregar widget de "Periodo Activo"
- ✅ Agregar botón rápido "Gestionar Periodos"
- ✅ Agregar alertas de fechas próximas de cierre
**Líneas estimadas:** ~100 líneas agregadas

---

#### ✏️ `templates/superadmin/reportes/reportes.html`
**Cambios:**
- ✅ Agregar sección de "Reportes por Periodo"
- ✅ Agregar sección de "Reportes de Ciclo Completo"
- ✅ Agregar filtros por periodo/ciclo
- ✅ Agregar opción de descarga de certificados masivos
**Líneas estimadas:** ~150 líneas agregadas

---

### 2.3 TEMPLATES DE PROFESOR - NUEVOS (1 archivo)

#### 🆕 `templates/profesores/selector_periodo.html`
**Contenido:**
- Componente reutilizable de selector de periodo
- Dropdown con periodos disponibles
- Indicador de periodo activo
- Alertas de cierre próximo
**Líneas estimadas:** ~150 líneas

---

### 2.4 TEMPLATES DE PROFESOR - A MODIFICAR (5 archivos)

#### ✏️ `templates/profesores/dashboard.html`
**Cambios:**
- ✅ Agregar información del periodo activo
- ✅ Agregar contador de días para cierre
- ✅ Agregar resumen de notas pendientes por periodo
**Líneas estimadas:** ~80 líneas agregadas

---

#### ✏️ `templates/profesores/Gestion_LC.html` (Gestión de notas)
**Cambios:**
- ✅ Agregar selector de periodo en la parte superior
- ✅ Filtrar notas por periodo seleccionado
- ✅ Bloquear edición si periodo está cerrado
- ✅ Agregar indicador visual de periodo cerrado
**Líneas estimadas:** ~120 líneas modificadas

---

#### ✏️ `templates/profesores/asistencia.html`
**Cambios:**
- ✅ Agregar selector de periodo
- ✅ Filtrar asistencias por periodo
- ✅ Bloquear edición si periodo está cerrado
- ✅ Agregar estadísticas por periodo
**Líneas estimadas:** ~100 líneas modificadas

---

#### ✏️ `templates/profesores/cursos.html`
**Cambios:**
- ✅ Agregar información de periodo actual
- ✅ Agregar estadísticas por periodo
- ✅ Mostrar historial de periodos anteriores
**Líneas estimadas:** ~60 líneas agregadas

---

#### ✏️ `templates/profesores/solicitudes.html`
**Cambios:**
- ✅ Agregar filtro por periodo al mostrar notas solicitadas
**Líneas estimadas:** ~30 líneas agregadas

---

### 2.5 TEMPLATES DE PADRES - NUEVO (1 archivo)

#### 🆕 `templates/padres/historial_academico.html`
**Contenido:**
- Vista completa del historial académico del estudiante
- Navegación por periodos y ciclos
- Gráficas de evolución
- Opción de descarga de certificados
**Líneas estimadas:** ~400 líneas

---

### 2.6 TEMPLATES DE PADRES - A MODIFICAR (3 archivos)

#### ✏️ `templates/padres/dashboard.html`
**Cambios:**
- ✅ Agregar información del periodo actual
- ✅ Agregar resumen de notas del periodo
- ✅ Agregar enlace a historial completo
**Líneas estimadas:** ~80 líneas agregadas

---

#### ✏️ `templates/padres/informacion_academica.html`
**Cambios:**
- ✅ Agregar selector de periodo
- ✅ Filtrar calificaciones por periodo
- ✅ Agregar vista de historial por periodos
- ✅ Agregar botón "Ver todos los periodos"
- ✅ Agregar gráficas de evolución por periodo
**Líneas estimadas:** ~200 líneas agregadas

---

#### ✏️ `templates/padres/calificaciones_estudiante.html`
**Cambios:**
- ✅ Agregar selector de periodo
- ✅ Agregar comparación entre periodos
- ✅ Agregar botón de descarga de boletín por periodo
**Líneas estimadas:** ~100 líneas agregadas

---

### 2.7 TEMPLATES DE ESTUDIANTES - A MODIFICAR (2 archivos)

#### ✏️ `templates/estudiantes/dashboard.html`
**Cambios:**
- ✅ Agregar widget de periodo actual
- ✅ Agregar resumen de notas del periodo
- ✅ Agregar enlace a historial académico
**Líneas estimadas:** ~70 líneas agregadas

---

#### 🆕 `templates/estudiantes/historial_academico.html`
**Contenido:**
- Vista del historial académico completo
- Navegación por periodos
- Descarga de certificados
**Líneas estimadas:** ~350 líneas

---

## 💻 3. FRONTEND - JAVASCRIPT

### 3.1 ARCHIVOS NUEVOS (4 archivos)

#### 🆕 `static/js/superadmin/ciclos_periodos.js`
**Contenido:**
```javascript
// Gestión de ciclos y periodos
- cargarCiclos()
- crearCiclo()
- editarCiclo()
- activarCiclo()
- cerrarCiclo()
- cargarPeriodos()
- crearPeriodo()
- cerrarPeriodo()
- finalizarCiclo()
- validarFechas()
```
**Líneas estimadas:** ~500 líneas

---

#### 🆕 `static/js/superadmin/notificaciones_periodo.js`
**Contenido:**
```javascript
// Gestión de notificaciones de periodos
- cargarNotificaciones()
- programarNotificacion()
- editarNotificacion()
- eliminarNotificacion()
- previsualizarNotificacion()
```
**Líneas estimadas:** ~300 líneas

---

#### 🆕 `static/js/profesor/selector_periodo.js`
**Contenido:**
```javascript
// Componente de selector de periodo
- inicializarSelector()
- cambiarPeriodo()
- obtenerPeriodoActivo()
- actualizarDatosSegunPeriodo()
```
**Líneas estimadas:** ~200 líneas

---

#### 🆕 `static/js/padres/historial_academico.js`
**Contenido:**
```javascript
// Vista de historial académico
- cargarHistorial()
- navegarPorPeriodos()
- generarGraficasEvolucion()
- descargarCertificado()
- compararPeriodos()
```
**Líneas estimadas:** ~400 líneas

---

### 3.2 ARCHIVOS A MODIFICAR (5 archivos)

#### ✏️ `static/js/profesor/Gestion_LC.js`
**Cambios:**
- ✅ Integrar selector de periodo
- ✅ Filtrar notas por periodo seleccionado
- ✅ Validar periodo activo antes de guardar
- ✅ Agregar parámetro periodo_id a todas las peticiones
**Líneas estimadas:** ~150 líneas modificadas

---

#### ✏️ `static/js/profesor/asistencia_notas.js`
**Cambios:**
- ✅ Integrar selector de periodo
- ✅ Filtrar asistencias por periodo
- ✅ Validar periodo activo
- ✅ Agregar parámetro periodo_id
**Líneas estimadas:** ~100 líneas modificadas

---

#### ✏️ `static/js/superadmin/reportes.js` (si existe, o crear)
**Cambios:**
- ✅ Agregar filtros por periodo/ciclo
- ✅ Agregar generación de reportes por periodo
- ✅ Agregar descarga masiva de certificados
**Líneas estimadas:** ~200 líneas agregadas

---

#### ✏️ `static/js/estudiantes/base.js`
**Cambios:**
- ✅ Agregar funciones para consultar historial por periodo
- ✅ Agregar funciones para descargar certificados
**Líneas estimadas:** ~100 líneas agregadas

---

#### ✏️ Crear nuevo: `static/js/padres/informacion_academica.js`
**Contenido:**
- ✅ Lógica del selector de periodo
- ✅ Carga de datos por periodo
- ✅ Gráficas de evolución
**Líneas estimadas:** ~300 líneas

---

## 🎨 4. FRONTEND - CSS

### 4.1 ARCHIVOS NUEVOS (4 archivos)

#### 🆕 `static/css/superadmin/gestion_academica/ciclos_periodos.css`
**Contenido:** Estilos para gestión de ciclos y periodos
**Líneas estimadas:** ~300 líneas

---

#### 🆕 `static/css/profesor/selector_periodo.css`
**Contenido:** Estilos para componente selector de periodo
**Líneas estimadas:** ~150 líneas

---

#### 🆕 `static/css/padres/historial_academico.css`
**Contenido:** Estilos para vista de historial académico
**Líneas estimadas:** ~250 líneas

---

#### 🆕 `static/css/estudiantes/historial_academico.css`
**Contenido:** Estilos para vista de historial (estudiantes)
**Líneas estimadas:** ~250 líneas

---

## 📄 5. OTROS ARCHIVOS

### 5.1 BASE DE DATOS

#### 🆕 `migrations/add_sistema_periodos.py` (o similar según tu ORM)
**Contenido:**
- Crear tablas: ciclo_academico, periodo_academico
- Alterar tablas: matricula, calificacion, asistencia, notificacion, ReporteCalificaciones
**Líneas estimadas:** ~200 líneas

---

### 5.2 CONFIGURACIÓN

#### ✏️ `config.py` (si es necesario)
**Cambios:**
- ✅ Agregar configuraciones para:
  - Ruta de almacenamiento de reportes
  - Configuración de generación de PDFs
  - Configuración de tareas programadas (si usas Celery)
**Líneas estimadas:** ~20 líneas agregadas

---

#### 🆕 `tasks.py` (si usas Celery para tareas programadas)
**Contenido:**
```python
# Tareas programadas
- verificar_notificaciones_pendientes()
- enviar_recordatorios_cierre()
- procesar_cierres_automaticos()
```
**Líneas estimadas:** ~150 líneas

---

## 📊 RESUMEN POR TIPO DE CAMBIO

### Cambios Críticos (Requieren mayor atención)
1. ✅ `controllers/models.py` - Base del sistema
2. ✅ `routes/admin.py` - Toda la gestión de admin
3. ✅ `services/promocion_service.py` - Lógica de promoción automática
4. ✅ `services/periodo_service.py` - Lógica central de periodos

### Cambios Importantes
5. ✅ `routes/profesor.py` - Afecta el flujo diario de profesores
6. ✅ `routes/padres.py` - Afecta consultas de padres
7. ✅ `templates/profesores/Gestion_LC.html` - UI crítica de notas
8. ✅ `static/js/profesor/Gestion_LC.js` - Lógica de notas

### Cambios Moderados
- Todos los templates de visualización
- Scripts JS de consultas
- Servicios de reportes

### Cambios Menores
- CSS adicional
- Templates de email
- Configuraciones

---

## ⚠️ CONSIDERACIONES IMPORTANTES

### 1. Retrocompatibilidad
- Los campos nuevos deben ser `nullable=True` inicialmente
- Las consultas antiguas deben seguir funcionando
- Agregar valores por defecto para datos existentes

### 2. Migración de Datos Existentes
Después de crear las tablas, necesitarás:
```python
# Script de migración
1. Crear ciclo académico para año actual
2. Crear periodos para año actual
3. Asociar todas las notas existentes al periodo actual
4. Asociar todas las asistencias existentes al periodo actual
5. Asociar todas las matrículas existentes al ciclo actual
```

### 3. Testing
Archivos de prueba a crear:
- `tests/test_periodo_service.py`
- `tests/test_promocion_service.py`
- `tests/test_reporte_service.py`

### 4. Documentación
Actualizar:
- README.md - Agregar sección de periodos académicos
- Manual de usuario (admin)
- Manual de usuario (profesor)
- Manual de usuario (padre)

---

## 📅 ORDEN RECOMENDADO DE IMPLEMENTACIÓN

### Fase 1: Base (1-2 días)
1. Modificar `models.py`
2. Crear migración de BD
3. Crear `periodo_service.py` básico

### Fase 2: Admin (2-3 días)
4. Crear rutas en `admin.py`
5. Crear templates de admin
6. Crear JS de gestión

### Fase 3: Profesor (2-3 días)
7. Modificar rutas de profesor
8. Modificar templates de profesor
9. Integrar selector de periodo

### Fase 4: Padres/Estudiantes (1-2 días)
10. Modificar rutas de padres/estudiantes
11. Crear vistas de historial
12. Crear JS de consultas

### Fase 5: Promoción y Reportes (3-4 días)
13. Crear `promocion_service.py`
14. Crear `reporte_service.py`
15. Integrar generación de reportes

### Fase 6: Notificaciones (1-2 días)
16. Crear `notificacion_periodo_service.py`
17. Configurar tareas programadas
18. Crear templates de emails

### Fase 7: Testing y Ajustes (2-3 días)
19. Pruebas completas
20. Corrección de bugs
21. Optimización de consultas

### TOTAL ESTIMADO: 12-19 días de desarrollo

---

**Última actualización:** Octubre 2024  
**Versión:** 1.0

