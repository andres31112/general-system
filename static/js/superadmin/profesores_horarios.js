/**
 * FUNCIONALIDAD DE PROFESORES EN HORARIOS
 * Maneja la selección y validación de profesores específicos para cada asignatura
 */

// ============================================================================
// VARIABLES GLOBALES
// ============================================================================
let profesoresPorAsignatura = {};
let profesoresAsignaciones = {};

// ============================================================================
// FUNCIONES PARA MANEJO DE PROFESORES
// ============================================================================

/**
 * Obtiene los profesores asignados a una asignatura específica
 */
async function obtenerProfesoresPorAsignatura(asignaturaId) {
    try {
        const response = await fetch(`/admin/api/profesores/asignatura/${asignaturaId}`);
        const data = await response.json();
        
        if (data.success) {
            profesoresPorAsignatura[asignaturaId] = data.profesores;
            return data.profesores;
        } else {
            console.error('Error obteniendo profesores:', data.error);
            return [];
        }
    } catch (error) {
        console.error('Error en la petición:', error);
        return [];
    }
}

/**
 * Valida si un profesor está asignado a una asignatura
 */
async function validarProfesorAsignatura(profesorId, asignaturaId) {
    try {
        const response = await fetch(`/admin/api/profesores/validar/${profesorId}/${asignaturaId}`);
        const data = await response.json();
        
        return data.success && data.es_valido;
    } catch (error) {
        console.error('Error validando profesor:', error);
        return false;
    }
}

/**
 * Crea un selector de profesores para una asignatura específica
 */
function crearSelectorProfesores(asignaturaId, profesorSeleccionadoId = null) {
    const selector = document.createElement('select');
    selector.className = 'form-select profesor-selector';
    selector.dataset.asignaturaId = asignaturaId;
    selector.style.marginTop = '5px';
    selector.style.fontSize = '12px';
    
    // Opción por defecto
    const opcionDefault = document.createElement('option');
    opcionDefault.value = '';
    opcionDefault.textContent = 'Seleccionar profesor...';
    opcionDefault.disabled = true;
    opcionDefault.selected = true;
    selector.appendChild(opcionDefault);
    
    // Cargar profesores de forma asíncrona
    cargarProfesoresEnSelector(selector, asignaturaId, profesorSeleccionadoId);
    
    return selector;
}

/**
 * Carga los profesores en un selector específico
 */
async function cargarProfesoresEnSelector(selector, asignaturaId, profesorSeleccionadoId = null) {
    const profesores = await obtenerProfesoresPorAsignatura(asignaturaId);
    
    // Limpiar opciones existentes (excepto la primera)
    while (selector.children.length > 1) {
        selector.removeChild(selector.lastChild);
    }
    
    if (profesores.length === 0) {
        const opcionVacia = document.createElement('option');
        opcionVacia.value = '';
        opcionVacia.textContent = 'No hay profesores asignados';
        opcionVacia.disabled = true;
        selector.appendChild(opcionVacia);
        return;
    }
    
    // Agregar opciones de profesores
    profesores.forEach(profesor => {
        const opcion = document.createElement('option');
        opcion.value = profesor.id_usuario;
        opcion.textContent = profesor.nombre_completo;
        
        // Marcar como seleccionado si es el profesor actual
        if (profesorSeleccionadoId && profesor.id_usuario == profesorSeleccionadoId) {
            opcion.selected = true;
        }
        
        selector.appendChild(opcion);
    });
}

/**
 * Maneja el cambio de asignatura en el horario
 */
function manejarCambioAsignatura(celda, asignaturaId) {
    const selectorProfesor = celda.querySelector('.profesor-selector');
    
    if (selectorProfesor) {
        // Recargar profesores para la nueva asignatura
        cargarProfesoresEnSelector(selectorProfesor, asignaturaId);
    } else {
        // Crear nuevo selector si no existe
        const nuevoSelector = crearSelectorProfesores(asignaturaId);
        celda.appendChild(nuevoSelector);
    }
}

/**
 * Valida que el profesor seleccionado esté asignado a la asignatura
 */
async function validarSeleccionProfesor(profesorId, asignaturaId) {
    if (!profesorId || !asignaturaId) {
        return true; // No hay nada que validar
    }
    
    const esValido = await validarProfesorAsignatura(profesorId, asignaturaId);
    
    if (!esValido) {
        mostrarNotificacion('El profesor seleccionado no está asignado a esta asignatura.', 'error');
        return false;
    }
    
    return true;
}

/**
 * Guarda la asignación de profesor en el horario
 */
async function guardarAsignacionProfesor(cursoId, diaSemana, horaInicio, asignaturaId, profesorId) {
    try {
        // Validar que el profesor esté asignado a la asignatura
        const esValido = await validarSeleccionProfesor(profesorId, asignaturaId);
        if (!esValido) {
            return false;
        }
        
        // Actualizar el objeto de profesores asignaciones
        const clave = `${diaSemana}-${horaInicio}`;
        profesoresAsignaciones[clave] = profesorId;
        
        return true;
        
    } catch (error) {
        console.error('Error guardando asignación:', error);
        return false;
    }
}

/**
 * Carga los profesores existentes al cargar el horario
 */
async function cargarProfesoresExistentes(profesoresAsignacionesData) {
    profesoresAsignaciones = profesoresAsignacionesData || {};
    
    for (const [clave, profesorId] of Object.entries(profesoresAsignaciones)) {
        const [diaSemana, horaInicio] = clave.split('-');
        const celda = document.querySelector(`[data-dia="${diaSemana}"][data-hora="${horaInicio}"]`);
        
        if (celda) {
            const asignaturaSelector = celda.querySelector('.asignatura-selector');
            const asignaturaId = asignaturaSelector.value;
            
            if (asignaturaId) {
                const selectorProfesor = celda.querySelector('.profesor-selector');
                if (selectorProfesor) {
                    await cargarProfesoresEnSelector(selectorProfesor, asignaturaId, profesorId);
                } else {
                    // Crear selector si no existe
                    const nuevoSelector = crearSelectorProfesores(asignaturaId, profesorId);
                    celda.appendChild(nuevoSelector);
                }
            }
        }
    }
}

/**
 * Obtiene los datos de profesores para enviar al servidor
 */
function obtenerDatosProfesores() {
    const profesoresData = {};
    
    document.querySelectorAll('.profesor-selector').forEach(selector => {
        const celda = selector.closest('[data-dia][data-hora]');
        if (celda) {
            const diaSemana = celda.getAttribute('data-dia');
            const horaInicio = celda.getAttribute('data-hora');
            const profesorId = selector.value;
            
            if (profesorId) {
                const clave = `${diaSemana}-${horaInicio}`;
                profesoresData[clave] = parseInt(profesorId);
            }
        }
    });
    
    return profesoresData;
}

/**
 * Inicializa la funcionalidad de profesores en el horario
 */
function inicializarProfesoresHorario() {
    // Agregar event listeners a los selectores de asignatura
    document.addEventListener('change', async function(e) {
        if (e.target.classList.contains('asignatura-selector')) {
            const celda = e.target.closest('[data-dia][data-hora]');
            const asignaturaId = e.target.value;
            
            if (asignaturaId) {
                manejarCambioAsignatura(celda, asignaturaId);
            } else {
                // Si no hay asignatura, ocultar selector de profesor
                const selectorProfesor = celda.querySelector('.profesor-selector');
                if (selectorProfesor) {
                    selectorProfesor.style.display = 'none';
                }
            }
        }
        
        // Manejar cambio de profesor
        if (e.target.classList.contains('profesor-selector')) {
            const celda = e.target.closest('[data-dia][data-hora]');
            const asignaturaSelector = celda.querySelector('.asignatura-selector');
            const asignaturaId = asignaturaSelector.value;
            const profesorId = e.target.value;
            
            if (asignaturaId && profesorId) {
                await validarSeleccionProfesor(profesorId, asignaturaId);
            }
        }
    });
}

/**
 * Modifica la función de guardar horario para incluir profesores
 */
function modificarFuncionGuardar() {
    // Interceptar la función de guardar existente
    const originalSaveFunction = window.saveCourseSchedule;
    
    window.saveCourseSchedule = async function() {
        // Obtener datos de profesores
        const profesoresData = obtenerDatosProfesores();
        
        // Llamar a la función original
        if (originalSaveFunction) {
            const resultado = await originalSaveFunction();
            
            // Si la función original fue exitosa, agregar datos de profesores
            if (resultado && typeof resultado === 'object') {
                resultado.profesores_asignaciones = profesoresData;
            }
            
            return resultado;
        }
        
        return false;
    };
}

// ============================================================================
// INTEGRACIÓN CON EL SISTEMA EXISTENTE
// ============================================================================

/**
 * Integra la funcionalidad de profesores con el sistema de horarios existente
 */
function integrarConSistemaExistente() {
    // Esperar a que el sistema principal esté cargado
    const checkSystemReady = () => {
        if (typeof window.loadCourseSchedule === 'function') {
            // Interceptar la función de cargar horario
            const originalLoadFunction = window.loadCourseSchedule;
            
            window.loadCourseSchedule = async function() {
                const resultado = await originalLoadFunction();
                
                // Si hay datos de profesores, cargarlos
                if (resultado && resultado.profesores_asignaciones) {
                    await cargarProfesoresExistentes(resultado.profesores_asignaciones);
                }
                
                return resultado;
            };
            
            // Modificar función de guardar
            modificarFuncionGuardar();
            
            return true;
        }
        return false;
    };
    
    // Verificar cada 100ms hasta que el sistema esté listo
    const interval = setInterval(() => {
        if (checkSystemReady()) {
            clearInterval(interval);
        }
    }, 100);
}

// ============================================================================
// INICIALIZACIÓN
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Inicializando funcionalidad de profesores en horarios...');
    
    // Inicializar funcionalidad básica
    inicializarProfesoresHorario();
    
    // Integrar con sistema existente
    integrarConSistemaExistente();
    
    console.log('✅ Funcionalidad de profesores inicializada');
});

// ============================================================================
// FUNCIONES DE UTILIDAD PARA NOTIFICACIONES
// ============================================================================

function mostrarNotificacion(mensaje, tipo = 'info') {
    const notification = document.getElementById('notification');
    const notificationText = document.getElementById('notification-text');
    
    if (notification && notificationText) {
        notificationText.textContent = mensaje;
        notification.className = `notification ${tipo}`;
        notification.style.display = 'block';
        
        setTimeout(() => {
            notification.style.display = 'none';
        }, 3000);
    } else {
        console.log(`[${tipo.toUpperCase()}] ${mensaje}`);
    }
}
