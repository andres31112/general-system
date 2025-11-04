// Carga los periodos académicos reales al selector, dejando 'Anual' por defecto
async function cargarPeriodosAcademicosSelect() {
    const sel = document.getElementById('schedule-period');
    if (!sel) return;
    const defaultValue = 'Anual';
    try {
        // Limpiar y poner opción Anual por defecto
        sel.innerHTML = `<option value="${defaultValue}">${defaultValue}</option>`;
        // 1) Obtener ciclo activo
        const resCiclo = await fetch('/admin/api/ciclos/activo');
        if (!resCiclo.ok) throw new Error(`HTTP ${resCiclo.status}`);
        const cicloJson = await resCiclo.json();
        const ciclo = cicloJson && cicloJson.ciclo ? cicloJson.ciclo : null;
        if (!ciclo || !ciclo.id_ciclo) {
            // Sin ciclo activo: dejar solo opciones por defecto
            ['Primer Semestre','Segundo Semestre'].forEach(n => {
                const opt = document.createElement('option');
                opt.value = n; opt.textContent = n; sel.appendChild(opt);
            });
            sel.value = defaultValue;
            return;
        }
        // 2) Obtener periodos del ciclo activo
        const res = await fetch(`/admin/api/periodos?ciclo_id=${encodeURIComponent(ciclo.id_ciclo)}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        const periodos = Array.isArray(json?.periodos) ? json.periodos : [];
        periodos
            .sort((a,b) => ((a.numero_periodo||a.numero||0) - (b.numero_periodo||b.numero||0)))
            .forEach(p => {
                const numero = p.numero_periodo || p.numero;
                const nombre = p.nombre || `Periodo ${numero||''}`;
                const opt = document.createElement('option');
                opt.value = nombre;
                opt.textContent = nombre;
                sel.appendChild(opt);
            });
        // Mantener por defecto 'Anual' si no hay horario cargado
        if (!estado.horarioCargadoId) sel.value = defaultValue;
    } catch (e) {
        // Si falla, asegurar que al menos esté 'Anual' y semestres comunes
        ['Primer Semestre','Segundo Semestre'].forEach(n => {
            const opt = document.createElement('option');
            opt.value = n; opt.textContent = n; sel.appendChild(opt);
        });
        sel.value = defaultValue;
    }
}

// Asegura que un option exista en un select por su valor; si no, lo crea
function ensureOptionExists(selectEl, value, label) {
    if (!selectEl) return;
    const exists = Array.from(selectEl.options).some(opt => opt.value === value);
    if (!exists) {
        const opt = document.createElement('option');
        opt.value = value;
        opt.textContent = label || value;
        selectEl.appendChild(opt);
    }
}

// =============================================
// CONFIGURACIÓN Y VARIABLES GLOBALES
// =============================================
const API_URLS = {
    horarios: '/admin/api/horarios',
    crearHorario: '/admin/api/horarios/nuevo',
    obtenerHorario: '/admin/api/horarios',
    eliminarHorario: '/admin/api/horarios',
    asignarHorario: '/admin/api/horarios/asignar',
    cursos: '/admin/api/cursos',
    estadisticas: '/admin/api/estadisticas/horarios'
};

// Evita que el formulario flotante se cierre inmediatamente al abrirse por el mismo click
let evitarCierreFlotante = false;

// Estado de la aplicación
let estado = {
    horarios: [],
    cursos: [],
    horarioActual: null,
    bloques: [],
    diasActivos: new Set(['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']),
    editandoBloqueId: null,
    horarioCargadoId: null,
    // Filtros para Bloques Programados
    filtroBloquesDia: 'Todos',
    filtroBloquesLimite: 10,
    paginaBloques: 1
};

// Estado para el modal de asignación de cursos
let asignacionModal = {
    page: 1,
    pageSize: 8,
    search: '',
    sede: '',
    assigned: '', // '', 'con', 'sin'
    filteredItems: []
};

// =============================================
// FUNCIONES DE UTILIDAD
// =============================================

function mostrarLoading(mensaje = 'Cargando...') {
    const msgEl = document.getElementById('loading-message');
    const modal = document.getElementById('loading-modal');
    if (msgEl) msgEl.textContent = mensaje;
    if (modal) modal.style.display = 'flex';
}

function ocultarLoading() {
    const modal = document.getElementById('loading-modal');
    if (modal) modal.style.display = 'none';
}

function mostrarNotificacion(mensaje, tipo = 'success') {
    const notification = document.getElementById('notification');
    const notificationText = document.getElementById('notification-text');
    const icon = notification.querySelector('i');
    
    if (tipo === 'error') {
        icon.className = 'fas fa-exclamation-circle';
    } else if (tipo === 'warning') {
        icon.className = 'fas fa-exclamation-triangle';
    } else {
        icon.className = 'fas fa-check-circle';
    }
    
    notificationText.textContent = mensaje;
    notification.className = `notification ${tipo} show`;
    
    setTimeout(() => {
        notification.classList.remove('show');
    }, 4000);
}

function mostrarAlerta(titulo, mensaje, tipo = 'warning', callbackConfirm) {
    const alerta = document.getElementById('custom-alert');
    const icono = document.getElementById('alert-icon');
    const tituloElem = document.getElementById('alert-title');
    const mensajeElem = document.getElementById('alert-message');
    
    const iconos = {
        warning: '<i class="fas fa-exclamation-triangle"></i>',
        error: '<i class="fas fa-times-circle"></i>',
        success: '<i class="fas fa-check-circle"></i>',
        info: '<i class="fas fa-info-circle"></i>'
    };

    icono.innerHTML = iconos[tipo] || iconos.warning;
    tituloElem.textContent = titulo;
    mensajeElem.textContent = mensaje;

    const btnConfirmar = document.getElementById('alert-confirm');
    const btnCancelar = document.getElementById('alert-cancel');
    
    const nuevoBtnConfirmar = btnConfirmar.cloneNode(true);
    const nuevoBtnCancelar = btnCancelar.cloneNode(true);
    
    btnConfirmar.parentNode.replaceChild(nuevoBtnConfirmar, btnConfirmar);
    btnCancelar.parentNode.replaceChild(nuevoBtnCancelar, btnCancelar);
    
    nuevoBtnConfirmar.onclick = function() {
        if (callbackConfirm) callbackConfirm();
        alerta.style.display = 'none';
    };
    
    nuevoBtnCancelar.onclick = function() {
        alerta.style.display = 'none';
    };

    alerta.style.display = 'flex';
}

// =============================================
// FUNCIONES DE COMUNICACIÓN CON LA API
// =============================================

async function apiRequest(url, options = {}) {
    const controller = new AbortController();
    const timeoutMs = options.timeoutMs || 20000;
    const id = setTimeout(() => controller.abort(), timeoutMs);
    try {
        console.log('🔗 API Request:', url, options.method || 'GET');
        const config = {
            headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
            method: options.method || 'GET',
            body: options.body ? JSON.stringify(options.body) : undefined,
            signal: controller.signal
        };
        if (config.body) console.log('📦 Request Body:', config.body);
        const response = await fetch(url, config);
        console.log('📥 API Response Status:', response.status);
        if (!response.ok) {
            let errorMessage = `Error ${response.status}: ${response.statusText}`;
            try {
                const t = await response.text();
                try {
                    const j = JSON.parse(t);
                    errorMessage = j.error || j.message || errorMessage;
                    console.error('❌ API Error Data:', j);
                } catch {
                    if (t) errorMessage += ` - ${t.substring(0, 300)}`;
                }
            } catch {}
            throw new Error(errorMessage);
        }
        const text = await response.text();
        const data = text ? JSON.parse(text) : {};
        console.log('✅ API Success:', data);
        return data;
    } catch (error) {
        if (error.name === 'AbortError') {
            console.error('❌ API Timeout');
            throw new Error('Tiempo de espera agotado comunicando con el servidor');
        }
        console.error('❌ API Error:', error);
        throw error;
    } finally {
        clearTimeout(id);
    }
}

// =============================================
// FUNCIONES DE CARGA DE DATOS
// =============================================

async function cargarEstadisticas() {
    try {
        const data = await apiRequest(API_URLS.estadisticas);
        document.getElementById('total-cursos').textContent = data.total_cursos || 0;
        document.getElementById('total-profesores').textContent = data.total_profesores || 0;
        document.getElementById('salones-libres').textContent = data.salones_libres || 0;
    } catch (error) {
        console.error('Error cargando estadísticas:', error);
        document.getElementById('total-cursos').textContent = '0';
        document.getElementById('total-profesores').textContent = '0';
        document.getElementById('salones-libres').textContent = '0';
    }
}

async function cargarHorariosGuardados() {
    mostrarLoading('Cargando horarios...');
    
    try {
        const horarios = await apiRequest(API_URLS.horarios);
        
        console.log('📋 Estructura de horarios recibida:', horarios);
        
        // Manejar diferentes estructuras de respuesta
        if (Array.isArray(horarios)) {
            estado.horarios = horarios;
        } else if (horarios && Array.isArray(horarios.data)) {
            estado.horarios = horarios.data;
        } else if (horarios && horarios.horarios) {
            estado.horarios = horarios.horarios;
        } else {
            estado.horarios = [];
            console.warn('⚠️  Estructura de horarios no reconocida:', horarios);
        }
        
        console.log('📋 Horarios procesados:', estado.horarios);
        actualizarListaHorariosUI();
        
    } catch (error) {
        console.error('❌ Error cargando horarios:', error);
        mostrarNotificacion('Error al cargar horarios: ' + error.message, 'error');
        estado.horarios = [];
        actualizarListaHorariosUI();
    } finally {
        ocultarLoading();
    }
}

async function cargarCursos() {
    try {
        const data = await apiRequest(API_URLS.cursos);
        console.log('📚 Cursos recibidos:', data);
        
        // Manejar diferentes estructuras de respuesta
        if (Array.isArray(data)) {
            estado.cursos = data;
        } else if (data && Array.isArray(data.data)) {
            estado.cursos = data.data;
        } else if (data && data.cursos) {
            estado.cursos = data.cursos;
        } else {
            estado.cursos = [];
            console.warn('⚠️  Estructura de cursos no reconocida:', data);
        }
        
        console.log('📚 Cursos procesados:', estado.cursos);
    } catch (error) {
        console.error('Error cargando cursos:', error);
        estado.cursos = [];
    }
}

// Renderiza los cursos asignados a un horario específico en su contenedor
async function renderCursosAsignados(horarioId, contenedor) {
    if (!contenedor) return;
    const hId = parseInt(horarioId);
    const header = contenedor.parentElement && contenedor.parentElement.querySelector('.cursos-header');
    try {
        const resp = await fetch(`/admin/api/horarios/${hId}/cursos`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const json = await resp.json();
        const cursosAsignados = Array.isArray(json) ? json : (json.data || []);
        if (header) header.textContent = `Cursos asignados (${cursosAsignados.length})`;
        if (cursosAsignados.length === 0) {
            // Fallback a cliente: filtrar estado.cursos
            const fallback = (Array.isArray(estado.cursos) ? estado.cursos : []).filter(c => {
                const v = c.horario_general_id ?? c.horarioId ?? c.horario_general;
                return parseInt(v) === hId;
            });
            if (header) header.textContent = `Cursos asignados (${fallback.length})`;
            if (fallback.length === 0) {
                contenedor.innerHTML = '<div style="color:#666;">No hay cursos asignados a este horario.</div>';
                return;
            }
            const ordenados = [...fallback].sort((a,b) => (a.nombreCurso||a.nombre||'').localeCompare(b.nombreCurso||b.nombre||''));
            contenedor.innerHTML = `<div class="cursos-grid">${ordenados.map(c => `
                <div class=\"curso-item\">
                    <div class=\"curso-left\">
                        <div class=\"curso-meta\">
                            <div class=\"curso-meta-title\">${(c.nombreCurso || c.nombre || 'Curso')} – ${(c.sede || 'Sin sede')}</div>
                        </div>
                    </div>
                </div>
            `).join('')}</div>`;
            return;
        }
        const ordenadosApi = [...cursosAsignados].sort((a,b) => (a.nombreCurso||a.nombre||'').localeCompare(b.nombreCurso||b.nombre||''));
        contenedor.innerHTML = `<div class="cursos-grid">${ordenadosApi.map(c => `
            <div class=\"curso-item\">
                <div class=\"curso-left\">
                    <div class=\"curso-meta\">
                        <div class=\"curso-meta-title\">${(c.nombreCurso || c.nombre || 'Curso')} – ${(c.sede || 'Sin sede')}</div>
                    </div>
                </div>
            </div>
        `).join('')}</div>`;
    } catch (err) {
        console.error('Error obteniendo cursos por horario:', err);
        if (header) header.textContent = 'Cursos asignados (0)';
        contenedor.innerHTML = '<div style="color:#B00020;">Error cargando cursos asignados.</div>';
    }
}

async function cargarHorario(id) {
    console.log('🔍 Cargando horario ID:', id, 'Tipo:', typeof id);
    
    // Validación mejorada
    if (!id || id === 'null' || id === 'undefined' || id === '') {
        console.error('❌ ID de horario vacío o inválido:', id);
        mostrarNotificacion('ID de horario no válido', 'error');
        return;
    }

    let horarioId;
    
    if (typeof id === 'string') {
        horarioId = parseInt(id);
    } else if (typeof id === 'number') {
        horarioId = id;
    } else {
        console.error('❌ Tipo de ID inválido:', typeof id);
        mostrarNotificacion('Tipo de ID de horario inválido', 'error');
        return;
    }

    if (isNaN(horarioId) || horarioId <= 0) {
        console.error('❌ ID de horario numérico inválido:', horarioId);
        mostrarNotificacion('ID de horario numérico inválido', 'error');
        return;
    }

    console.log('✅ ID de horario válido:', horarioId);
    mostrarLoading('Cargando horario...');
    
    try {
        const url = `${API_URLS.obtenerHorario}/${horarioId}`;
        console.log('🌐 URL de solicitud:', url);
        
        const horarioData = await apiRequest(url);
        console.log('📋 Datos del horario recibidos:', horarioData);
        
        if (!horarioData) {
            throw new Error('No se recibieron datos del horario');
        }

        // Reiniciar estado
        estado.bloques = [];
        estado.diasActivos.clear();

        // Procesar días (compatibilidad con API que puede devolver 'dias' o 'diasSemana')
        try {
            const diasFuente = (horarioData.dias && horarioData.dias.length !== undefined)
                ? horarioData.dias
                : horarioData.diasSemana;

            if (diasFuente) {
                if (typeof diasFuente === 'string') {
                    const diasArray = JSON.parse(diasFuente);
                    if (Array.isArray(diasArray)) {
                        diasArray.forEach(dia => estado.diasActivos.add(dia));
                    }
                } else if (Array.isArray(diasFuente)) {
                    diasFuente.forEach(dia => estado.diasActivos.add(dia));
                }
            }
        } catch (e) {
            console.warn('Error procesando días, usando días por defecto');
            ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes'].forEach(dia => estado.diasActivos.add(dia));
        }

        // Procesar bloques
        if (horarioData.bloques && Array.isArray(horarioData.bloques)) {
            estado.bloques = horarioData.bloques.map(bloque => ({
                id: bloque.id_bloque || bloque.id || generarIdUnico(),
                day: bloque.dia_semana || bloque.day || 'Lunes',
                type: bloque.tipo || bloque.type || 'class',
                start: formatTimeForInput(bloque.horaInicio || bloque.start || '07:00'),
                end: formatTimeForInput(bloque.horaFin || bloque.end || ''),
                nombre: bloque.nombre || 'Bloque',
                classType: bloque.class_type || bloque.classType || 'single',
                breakType: bloque.break_type || bloque.breakType || 'morning'
            })).filter(bloque => bloque.day && bloque.start); // permitir end vacío para que el usuario lo complete
        }

        estado.horarioCargadoId = horarioId;

        // Actualizar interfaz
        if (horarioData.nombre) {
            document.getElementById('schedule-name').value = horarioData.nombre;
        }
        
        if (horarioData.periodo) {
            const sel = document.getElementById('schedule-period');
            ensureOptionExists(sel, horarioData.periodo, horarioData.periodo);
            sel.value = horarioData.periodo;
        }

        actualizarUI();
        document.getElementById('delete-schedule-btn').style.display = 'block';
        const saveBtn = document.getElementById('save-schedule-btn');
        if (saveBtn) saveBtn.innerHTML = '<i class="fas fa-sync"></i> Actualizar Horario';
        
        mostrarNotificacion('Horario cargado correctamente', 'success');

    } catch (error) {
        console.error('❌ Error cargando horario:', error);
        mostrarNotificacion('Error al cargar horario: ' + error.message, 'error');
        
        estado.horarioCargadoId = null;
        estado.bloques = [];
        actualizarUI();
    } finally {
        ocultarLoading();
    }
}

function formatTimeForInput(timeValue) {
    if (!timeValue) return '';
    
    if (typeof timeValue === 'string' && timeValue.match(/^\d{1,2}:\d{2}$/)) {
        const [hours, minutes] = timeValue.split(':');
        return `${hours.padStart(2, '0')}:${minutes.padStart(2, '0')}`;
    }
    
    if (typeof timeValue === 'object' && timeValue.hours !== undefined) {
        return `${timeValue.hours.toString().padStart(2, '0')}:${timeValue.minutes.toString().padStart(2, '0')}`;
    }
    
    return '';
}

async function guardarHorarioBD() {
    const nombre = document.getElementById('schedule-name').value.trim();
    const periodo = document.getElementById('schedule-period').value;

    if (!nombre) {
        mostrarNotificacion('El nombre del horario es requerido', 'error');
        return null;
    }

    if (estado.bloques.length === 0) {
        mostrarNotificacion('Debe agregar al menos un bloque horario', 'error');
        return null;
    }

    if (estado.diasActivos.size === 0) {
        mostrarNotificacion('Debe seleccionar al menos un día activo', 'error');
        return null;
    }

    // ✅ VALIDACIÓN CRÍTICA: Asegurar que todos los bloques tengan hora_fin explícita y válida
    for (let i = 0; i < estado.bloques.length; i++) {
        const b = estado.bloques[i];
        if (!b.end || b.end === '') {
            mostrarNotificacion(`Bloque ${i + 1}: defina la hora de fin`, 'error');
            return null;
        }
        if (timeToMinutes(b.start) >= timeToMinutes(b.end)) {
            mostrarNotificacion(`Bloque ${i + 1}: la hora de fin debe ser posterior al inicio`, 'error');
            return null;
        }
    }

    const bloquesConHoraFin = estado.bloques.map((bloque, index) => ({
        dia_semana: bloque.day,
        horaInicio: bloque.start,
        horaFin: bloque.end,
        tipo: bloque.type,
        nombre: bloque.nombre || `Bloque ${index + 1}`,
        orden: index,
        class_type: bloque.classType,
        break_type: bloque.breakType
    }));

    // ✅ CALCULAR HORAS DE INICIO Y FIN GLOBALES
    const horaInicio = calcularHoraInicio();
    const horaFin = calcularHoraFin();

    const datosHorario = {
        nombre: nombre,
        periodo: periodo,
        dias: Array.from(estado.diasActivos),
        bloques: bloquesConHoraFin,
        horaInicio: horaInicio,
        horaFin: horaFin
    };

    console.log('💾 Guardando horario con validación:', datosHorario);
    mostrarLoading('Guardando horario...');

    try {
        // Crear o actualizar según corresponda
        let resultado;
        if (estado.horarioCargadoId) {
            // UPDATE existente
            const url = `${API_URLS.obtenerHorario}/${estado.horarioCargadoId}`;
            resultado = await apiRequest(url, {
                method: 'PUT',
                body: datosHorario
            });
        } else {
            // CREATE nuevo
            resultado = await apiRequest(API_URLS.crearHorario, {
                method: 'POST',
                body: datosHorario
            });
        }

        console.log('💾 Resultado guardar horario:', resultado);

        if (resultado && (resultado.success || resultado.id || resultado.updated)) {
            mostrarNotificacion('Horario guardado correctamente', 'success');
            await cargarHorariosGuardados();
            await cargarPeriodosAcademicosSelect();
            // Mantener el id cargado al actualizar o asignarlo tras crear
            if (!estado.horarioCargadoId) {
                estado.horarioCargadoId = resultado.id || resultado.horario_id || resultado.horario?.id || resultado.horario?.id_horario;
            }
            return resultado.horario || { id: (resultado.id || estado.horarioCargadoId), nombre: datosHorario.nombre };
        } else {
            throw new Error(resultado.error || 'Error desconocido al guardar');
        }

    } catch (error) {
        console.error('❌ Error guardando horario:', error);
        mostrarNotificacion('Error al guardar: ' + error.message, 'error');
        return null;
    } finally {
        ocultarLoading();
    }
}

async function eliminarHorario(id) {
    const horarioId = parseInt(id);
    if (isNaN(horarioId) || horarioId <= 0) {
        mostrarNotificacion('ID de horario inválido para eliminar', 'error');
        return;
    }

    try {
        const res = await fetch(`${API_URLS.eliminarHorario}/${horarioId}`, { method: 'DELETE' });
        if (res.status === 409) {
            const data = await res.json().catch(() => ({ error: 'Conflicto al eliminar' }));
            // Mostrar modal para reasignar clases
            mostrarModalReasignacion(horarioId, data.error || 'Existen clases asociadas a este horario.', data.classes_count || 0);
            return;
        }
        if (!res.ok) {
            const txt = await res.text();
            throw new Error(`Error ${res.status} ${txt.substring(0,200)}`);
        }
        const resultado = await res.json();
        if (resultado.success) {
            mostrarNotificacion('Horario eliminado correctamente', 'success');
            if (estado.horarioCargadoId === horarioId) {
                nuevoHorario();
            }
            await cargarHorariosGuardados();
        }
    } catch (error) {
        mostrarNotificacion('Error al eliminar el horario: ' + error.message, 'error');
    }
}

async function asignarHorarioCursos(horarioId, cursosIds) {
    console.log('🎯 Asignando horario:', horarioId, 'a cursos:', cursosIds);
    mostrarLoading('Asignando horario a cursos...');
    
    try {
        const resultado = await apiRequest(API_URLS.asignarHorario, {
            method: 'POST',
            body: {
                horario_id: horarioId,
                cursos_ids: cursosIds
            }
        });

        console.log('✅ Resultado asignación:', resultado);

        if (resultado.success) {
            mostrarNotificacion(`Horario asignado correctamente a ${cursosIds.length} cursos`, 'success');
            return true;
        } else {
            throw new Error(resultado.error || 'Error al asignar horario');
        }
    } catch (err) {
        console.error('❌ Error asignando horario a cursos:', err);
        mostrarNotificacion('Error al asignar horario: ' + err.message, 'error');
        return false;
    } finally {
        ocultarLoading();
    }
}

// =============================================
// FUNCIONES DE LA INTERFAZ DE USUARIO
// =============================================

function actualizarUI() {
    actualizarDiasUI();
    actualizarBloquesUI();
    actualizarVistaPrevia();
    actualizarResumen();
}

function actualizarDiasUI() {
    document.querySelectorAll('.day').forEach(diaElem => {
        const dia = diaElem.dataset.day;
        const estaActivo = Array.from(estado.diasActivos).some(d => normalizeDayName(d) === normalizeDayName(dia));
        
        diaElem.classList.toggle('selected', estaActivo);
        
        const bloquesDia = estado.bloques.filter(b => normalizeDayName(b.day) === normalizeDayName(dia));
        diaElem.classList.toggle('has-blocks', bloquesDia.length > 0);
        
        if (bloquesDia.length > 0) {
            const inicio = Math.min(...bloquesDia.map(b => timeToMinutes(b.start)));
            const fin = Math.max(...bloquesDia.map(b => timeToMinutes(b.end)));
            diaElem.querySelector('.day-time').textContent = 
                `${formatTime12h(minutesToTime(inicio))} - ${formatTime12h(minutesToTime(fin))}`;
        } else {
            diaElem.querySelector('.day-time').textContent = '-';
        }
    });
}

function actualizarBloquesUI() {
    const contenedor = document.getElementById('blocks-container');
    const contador = document.getElementById('blocks-count');
    const bloqueList = document.querySelector('.block-list');

    // Utilidades para listeners y sincronización de selects
    const attachOnce = (el, type, handler, flagKey = '_listenerAttached') => {
        if (el && !el[flagKey]) { el.addEventListener(type, handler); el[flagKey] = true; }
    };
    const updateFilterAndCopyOptions = () => {
        // Actualizar filtro de día
        const selDia = document.getElementById('filter-day');
        if (selDia) {
            const current = selDia.value;
            while (selDia.options.length > 1) selDia.remove(1);
            Array.from(estado.diasActivos).forEach(d => {
                const opt = document.createElement('option');
                opt.value = d; opt.textContent = d; selDia.appendChild(opt);
            });
            // Mantener selección si sigue estando entre activos
            const activos = new Set(Array.from(estado.diasActivos));
            if (current && current !== 'Todos' && activos.has(current)) selDia.value = current;
            else selDia.value = 'Todos';
        }
        // Actualizar selects de duplicación
        const sync = (id) => {
            const sel = document.getElementById(id);
            if (!sel) return;
            while (sel.options.length > 1) sel.remove(1);
            Array.from(estado.diasActivos).forEach(d => { const opt = document.createElement('option'); opt.value = d; opt.textContent = d; sel.appendChild(opt); });
        };
        sync('copy-from-day');
        sync('copy-to-day');
        // Asegurar listeners
        const fd = document.getElementById('filter-day');
        const fl = document.getElementById('filter-limit');
        attachOnce(fd, 'change', (e) => { estado.filtroBloquesDia = e.target.value; estado.paginaBloques = 1; actualizarBloquesUI(); });
        attachOnce(fl, 'change', (e) => { estado.filtroBloquesLimite = parseInt(e.target.value, 10); estado.paginaBloques = 1; actualizarBloquesUI(); });
    };

    if (contador) contador.textContent = `(${estado.bloques.length})`;

    if (estado.bloques.length === 0) {
        contenedor.innerHTML = `
            <p style="text-align: center; color: #666; padding: 20px;">
                No hay bloques programados. Agregue el primer bloque.
            </p>
        `;
        return;
    }

    // Utilidad: sincronizar selects de duplicación con días activos
    const syncCopyDaySelects = () => {
        const dias = Array.from(estado.diasActivos);
        const sync = (id) => {
            const sel = document.getElementById(id);
            if (!sel) return;
            while (sel.options.length > 1) sel.remove(1);
            dias.forEach(d => { const opt = document.createElement('option'); opt.value = d; opt.textContent = d; sel.appendChild(opt); });
        };
        sync('copy-from-day');
        sync('copy-to-day');
    };

    // Renderizar controles de filtro si no existen
    if (bloqueList && !document.getElementById('blocks-filters')) {
        const filtros = document.createElement('div');
        filtros.id = 'blocks-filters';
        filtros.style.display = 'flex';
        filtros.style.gap = '10px';
        filtros.style.margin = '10px 0 12px 0';
        filtros.innerHTML = `
            <select id="filter-day" style="flex:1; padding:10px; border:2px solid var(--border); border-radius:10px;">
                <option value="Todos">Todos los días</option>
            </select>
            <select id="filter-limit" style="width:140px; padding:10px; border:2px solid var(--border); border-radius:10px;">
                <option value="5">Máx. 5</option>
                <option value="10" selected>Máx. 10</option>
                <option value="0">Sin límite</option>
            </select>
        `;
        bloqueList.prepend(filtros);

        // Controles para duplicar bloques de un día a otro
        const dup = document.createElement('div');
        dup.id = 'copy-day-controls';
        dup.style.display = 'flex';
        dup.style.flexDirection = 'column';
        dup.style.gap = '10px';
        dup.style.margin = '0 0 12px 0';
        dup.innerHTML = `
            <div style="flex-basis:100%; color:#0D3B66; font-weight:600; margin-bottom:4px;">
                Duplicar bloques entre días
            </div>
            <div class="copy-days" style="display:flex; gap:10px; width:100%;">
                <div class="copy-field" style="flex:1;">
                    <select id="copy-from-day" style="width:100%; min-width:180px; padding:10px; border:2px solid var(--border); border-radius:10px;">
                        <option value="">Desde</option>
                    </select>
                </div>
                <div class="copy-field" style="flex:1;">
                    <select id="copy-to-day" style="width:100%; min-width:180px; padding:10px; border:2px solid var(--border); border-radius:10px;">
                        <option value="">A</option>
                    </select>
                </div>
                <div style="align-self:end;">
                    <button type="button" class="small" id="copy-day-btn" style="min-width:180px; height:42px;">
                        <i class="fas fa-copy"></i> Duplicar bloques
                    </button>
                </div>
            </div>
        `;
        bloqueList.insertBefore(dup, filtros.nextSibling);

        // Inicializar y adjuntar listeners/ opciones
        updateFilterAndCopyOptions();

        // Poblar selects con días activos
        const cargarOpcionesDias = () => {
            const dias = Array.from(estado.diasActivos);
            const fill = (selId) => {
                const sel = document.getElementById(selId);
                if (!sel) return;
                // Limpiar (mantener primera opción)
                while (sel.options.length > 1) sel.remove(1);
                dias.forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d; opt.textContent = d; sel.appendChild(opt);
                });
            };
            fill('copy-from-day');
            fill('copy-to-day');
        };
        cargarOpcionesDias();

        // Listener duplicar
        document.getElementById('copy-day-btn').addEventListener('click', () => {
            const from = document.getElementById('copy-from-day').value;
            const to = document.getElementById('copy-to-day').value;
            if (!from || !to) { mostrarNotificacion('Seleccione día origen y destino', 'warning'); return; }
            if (from === to) { mostrarNotificacion('El origen y destino no pueden ser el mismo día', 'warning'); return; }

            const origenBloques = estado.bloques.filter(b => normalizeDayName(b.day) === normalizeDayName(from));
            if (origenBloques.length === 0) { mostrarNotificacion('El día origen no tiene bloques para duplicar', 'warning'); return; }

            const copias = origenBloques.map(b => ({
                id: generarIdUnico(),
                day: to,
                start: b.start,
                end: b.end,
                type: b.type,
                nombre: b.nombre,
                classType: b.classType,
                breakType: b.breakType
            }));
            estado.bloques.push(...copias);
            mostrarNotificacion(`Se duplicaron ${copias.length} bloques de ${from} a ${to}`, 'success');
            actualizarUI();
        });
        // Asegurar que los selects de duplicación estén sincronizados
        syncCopyDaySelects();
    } else if (bloqueList) {
        // Siempre mantener sincronizadas las opciones y listeners
        updateFilterAndCopyOptions();
    }

    // Aplicar filtros (comparación insensible a acentos)
    let bloquesFiltrados = [...estado.bloques];
    if (estado.filtroBloquesDia && estado.filtroBloquesDia !== 'Todos') {
        const filtroNorm = normalizeDayName(estado.filtroBloquesDia);
        bloquesFiltrados = bloquesFiltrados.filter(b => normalizeDayName(b.day) === filtroNorm);
    } else {
        // Si está en 'Todos', mostrar solo bloques de días activos del horario cargado
        const activosNorm = new Set(Array.from(estado.diasActivos).map(normalizeDayName));
        bloquesFiltrados = bloquesFiltrados.filter(b => activosNorm.has(normalizeDayName(b.day)));
    }

    // Ordenar por hora de inicio
    bloquesFiltrados.sort((a, b) => timeToMinutes(a.start) - timeToMinutes(b.start));

    // Paginación
    const limite = Number.isFinite(estado.filtroBloquesLimite) ? estado.filtroBloquesLimite : 10;
    const total = bloquesFiltrados.length;
    const totalPaginas = limite > 0 ? Math.max(1, Math.ceil(total / limite)) : 1;
    if (estado.paginaBloques > totalPaginas) estado.paginaBloques = totalPaginas;
    if (estado.paginaBloques < 1) estado.paginaBloques = 1;
    const inicio = limite > 0 ? (estado.paginaBloques - 1) * limite : 0;
    const fin = limite > 0 ? inicio + limite : total;
    const paginaItems = bloquesFiltrados.slice(inicio, fin);

    // Renderizar items de la página
    contenedor.innerHTML = paginaItems.map(bloque => `
        <div class="block-item" data-block-id="${bloque.id}">
            <div class="block-info">
                <strong>${bloque.nombre}</strong>
                <div class="block-details">
                    ${bloque.day} • ${formatTime12h(bloque.start)} - ${formatTime12h(bloque.end)}
                    <span class="block-type-tag ${bloque.type}">
                        ${bloque.type === 'class' 
                            ? '<i class="fas fa-book-open"></i> Clase' 
                            : '<i class="fas fa-coffee"></i> Descanso'}
                    </span>
                </div>
            </div>
            <div class="block-actions">
                <button type="button" class="small secondary" onclick="window.editarBloque('${bloque.id}')">
                    <i class="fas fa-edit"></i>
                </button>
                <button type="button" class="small danger" onclick="window.eliminarBloque('${bloque.id}')">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `).join('');

    // Enlazar acciones de edición y eliminación tras render
    try {
        contenedor.querySelectorAll('.btn-edit').forEach(btn => {
            btn.onclick = () => {
                const id = btn.getAttribute('data-block-id');
                if (id) editarBloque(id);
            };
        });
        contenedor.querySelectorAll('.btn-delete').forEach(btn => {
            btn.onclick = () => {
                const id = btn.getAttribute('data-block-id');
                if (id) eliminarBloque(id);
            };
        });
    } catch (e) {
        console.warn('No fue posible vincular acciones de edición/eliminación de bloques:', e);
    }

    // Renderizar controles de paginación
    let pagContainer = document.getElementById('blocks-pagination');
    if (!pagContainer) {
        pagContainer = document.createElement('div');
        pagContainer.id = 'blocks-pagination';
        pagContainer.style.display = 'flex';
        pagContainer.style.justifyContent = 'space-between';
        pagContainer.style.alignItems = 'center';
        pagContainer.style.margin = '10px 0 0 0';
        pagContainer.style.gap = '10px';
        if (bloqueList) bloqueList.appendChild(pagContainer);
    }

    if (totalPaginas > 1) {
        const mostrandoDesde = total === 0 ? 0 : inicio + 1;
        const mostrandoHasta = Math.min(fin, total);
        pagContainer.innerHTML = `
            <div style="color:#555; font-size: 0.9rem;">
                Mostrando ${mostrandoDesde}-${mostrandoHasta} de ${total}
            </div>
            <div style="display:flex; gap:8px;">
                <button type="button" class="small secondary" id="blocks-prev" ${estado.paginaBloques === 1 ? 'disabled' : ''}>&laquo; Anterior</button>
                <span style="align-self:center;">Página ${estado.paginaBloques} de ${totalPaginas}</span>
                <button type="button" class="small secondary" id="blocks-next" ${estado.paginaBloques === totalPaginas ? 'disabled' : ''}>Siguiente &raquo;</button>
            </div>
        `;
        const prevBtn = document.getElementById('blocks-prev');
        const nextBtn = document.getElementById('blocks-next');
        if (prevBtn) prevBtn.onclick = () => { estado.paginaBloques = Math.max(1, estado.paginaBloques - 1); actualizarBloquesUI(); };
        if (nextBtn) nextBtn.onclick = () => { estado.paginaBloques = Math.min(totalPaginas, estado.paginaBloques + 1); actualizarBloquesUI(); };
        pagContainer.style.display = 'flex';
    } else if (pagContainer) {
        pagContainer.innerHTML = '';
        pagContainer.style.display = 'none';
    }
}

function actualizarVistaPrevia() {
    const contenedor = document.getElementById('schedule-table-container');
    
    if (estado.bloques.length === 0 || estado.diasActivos.size === 0) {
        contenedor.innerHTML = `
            <p style="text-align: center; color: #666; padding: 40px;">
                ${estado.diasActivos.size === 0 ? 'Seleccione al menos un día activo' : 'Configure los bloques horarios para ver la vista previa'}
            </p>
        `;
        return;
    }

    const diasActivos = Array.from(estado.diasActivos);
    let tablaHTML = `
        <table class="schedule-table">
            <thead>
                <tr>
                    <th>Hora</th>
                    ${diasActivos.map(dia => `<th>${dia}</th>`).join('')}
                </tr>
            </thead>
            <tbody>
    `;

    const intervalos = generarIntervalosTiempo();
    
    intervalos.forEach(intervalo => {
        tablaHTML += `
            <tr>
                <td class="time-cell">${formatTime12h(intervalo.inicio)} - ${formatTime12h(intervalo.fin)}</td>
                ${diasActivos.map(dia => {
                    const bloque = estado.bloques.find(b => 
                        b.day === dia && 
                        timeToMinutes(b.start) <= timeToMinutes(intervalo.inicio) && 
                        timeToMinutes(b.end) >= timeToMinutes(intervalo.fin)
                    );
                    
                    if (bloque) {
                        let clase = `schedule-block ${bloque.type}-block`;
                        if (bloque.type === 'class' && bloque.classType === 'double') {
                            clase += ' double-block';
                        }
                        if (bloque.type === 'break') {
                            clase += ` ${bloque.breakType}-break`;
                        }
                        
                        return `<td class="${clase}">
                            <div class="block-title">${bloque.nombre}</div>
                            <div class="block-time">${formatTime12h(bloque.start)}-${formatTime12h(bloque.end)}</div>
                        </td>`;
                    }
                    return '<td class="empty-block"></td>';
                }).join('')}
            </tr>
        `;
    });

    tablaHTML += `</tbody></table>`;
    contenedor.innerHTML = tablaHTML;
}

function actualizarResumen() {
    const totalClases = estado.bloques.filter(b => b.type === 'class').length;
    const totalDescansos = estado.bloques.filter(b => b.type === 'break').length;
    
    const classCountEl = document.getElementById('class-count');
    const breakCountEl = document.getElementById('break-count');
    const totalBlocksEl = document.getElementById('total-blocks');
    if (classCountEl) classCountEl.textContent = `${totalClases} clases`;
    if (breakCountEl) breakCountEl.textContent = `${totalDescansos} descansos`;
    if (totalBlocksEl) totalBlocksEl.textContent = `${estado.bloques.length} bloques`;
    
    const estadoConfig = estado.bloques.length > 0 ? 'Configurado' : 'Sin configurar';
    const configEl = document.getElementById('schedule-config-status');
    if (configEl) {
        configEl.textContent = estadoConfig;
        configEl.className = estadoConfig === 'Configurado' ? 'config-ok' : 'config-pending';
    }
}

function actualizarListaHorariosUI() {
    const contenedor = document.getElementById('saved-schedules-list');
    const select = document.getElementById('schedule-select');

    console.log('🔍 IDs de horarios disponibles:', estado.horarios.map(h => ({
        id: h.id,
        id_horario: h.id_horario,
        nombre: h.nombre
    })));

    if (!estado.horarios || estado.horarios.length === 0) {
        contenedor.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">No hay horarios guardados</p>';
        select.innerHTML = '<option value="">No hay horarios disponibles</option>';
        return;
    }

    // SOLUCIÓN: Usar tanto id como id_horario para mayor compatibilidad
    contenedor.innerHTML = estado.horarios.map(horario => {
        // Obtener el ID correcto - priorizar id_horario, luego id
        const horarioId = horario.id_horario || horario.id;
        const esActivo = estado.horarioCargadoId === horarioId;
        const nombreSeguro = (horario.nombre || 'Sin nombre').replace(/'/g, "&#39;");
        
        if (!horarioId) {
            console.warn(' Horario sin ID válido:', horario);
            return '';
        }
        
        return `
            <div class="schedule-item ${esActivo ? 'active' : ''}" 
                 data-horario-id="${horarioId}">
                <div class="schedule-item-info">
                    <div class="schedule-item-name">${horario.nombre || 'Sin nombre'}</div>
                    <div class="schedule-item-details">
                        ${horario.horaInicio || '07:00'} - ${horario.horaFin || '17:00'} | 
                        ${horario.totalCursos || 0} cursos
                    </div>
                </div>
                <div class="schedule-item-actions">
                    <button type="button" class="small danger" data-horario-id="${horarioId}" data-horario-nombre="${nombreSeguro}">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            <div class="schedule-accordion" id="cursos-${horarioId}" style="display:none; border:1px solid #e9ecef; border-radius:8px; margin:8px 8px 16px 8px;">
                <div class="cursos-header" style="padding:10px 12px; font-weight:600; color:#0D3B66; background:#f8f9fa; border-bottom:1px solid #e9ecef;">
                    Cursos asignados
                </div>
                <div class="cursos-contenido" style="padding:10px 12px;"></div>
            </div>
        `;
    }).join('');

    // Actualizar el select también
    select.innerHTML = estado.horarios.map(horario => {
        const horarioId = horario.id_horario || horario.id;
        return horarioId ? `<option value="${horarioId}">${horario.nombre || 'Horario sin nombre'}</option>` : '';
    }).join('');

    // Agregar event listeners después de crear el HTML
    setTimeout(() => {
        document.querySelectorAll('.schedule-item[data-horario-id]').forEach(item => {
            item.addEventListener('click', async function(e) {
                if (e.target.closest('.schedule-item-actions')) return;
                const horarioId = this.getAttribute('data-horario-id');
                if (!horarioId || horarioId === 'null' || horarioId === 'undefined') {
                    mostrarNotificacion('ID de horario no válido', 'error');
                    return;
                }
                // Cargar datos del horario (comportamiento existente)
                cargarHorario(horarioId);

                // Toggle acordeón de cursos bajo este horario
                const acc = document.getElementById(`cursos-${horarioId}`);
                if (!acc) return;
                // Cerrar otros acordeones
                document.querySelectorAll('.schedule-accordion').forEach(el => {
                    if (el !== acc) el.style.display = 'none';
                });
                const contenido = acc.querySelector('.cursos-contenido');
                const visible = acc.style.display !== 'none';
                if (visible) {
                    acc.style.display = 'none';
                    return;
                }
                if (contenido) contenido.innerHTML = '<div style="color:#666;">Cargando cursos...</div>';
                try {
                    // Asegurar cursos en memoria por si el endpoint devuelve vacío
                    if (!estado.cursos || estado.cursos.length === 0) {
                        await cargarCursos();
                    }
                    await renderCursosAsignados(horarioId, contenido);
                    acc.style.display = 'block';
                    const parentList = document.getElementById('saved-schedules-list');
                    if (parentList) {
                        parentList.style.overflow = 'visible';
                        parentList.style.maxHeight = 'none';
                    }
                } catch (err) {
                    console.error('Error mostrando cursos en acordeón:', err);
                    if (contenido) contenido.innerHTML = '<div style="color:#B00020;">Error cargando cursos.</div>';
                }
            });
        });

        document.querySelectorAll('.schedule-item-actions .danger').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                const horarioId = this.getAttribute('data-horario-id');
                const horarioNombre = this.getAttribute('data-horario-nombre');
                console.log(' Eliminar horario ID:', horarioId);
                
                if (!horarioId || horarioId === 'null' || horarioId === 'undefined') {
                    mostrarNotificacion('ID de horario no válido para eliminar', 'error');
                    return;
                }
                
                configurarEliminacionHorario(horarioId, horarioNombre);
            });
        });

        // (Removed toggle button listeners; click en item maneja el acordeón)
    }, 100);
}

function agregarBloque() {
    const dia = document.getElementById('block-day').value;
    const tipo = document.getElementById('block-type').value;
    const inicio = document.getElementById('block-start').value;
    let fin = document.getElementById('block-end').value;

    if (!estado.diasActivos.has(dia)) {
        mostrarNotificacion(`El día ${dia} no está activo. Active el día primero.`, 'error');
        return;
    }

    // ✅ VALIDACIÓN: Si no hay hora_fin, calcular automáticamente
    if (!fin || fin === '') {
        const inicioMinutos = timeToMinutes(inicio);
        fin = minutesToTime(inicioMinutos + 45); // 45 minutos por defecto
        document.getElementById('block-end').value = fin;
        console.warn('⚠️ Hora fin vacía, calculada automáticamente:', fin);
    }

    if (inicio >= fin) {
        mostrarNotificacion('La hora de fin debe ser posterior a la de inicio', 'error');
        return;
    }

    if (haySuperposicion(dia, inicio, fin, estado.editandoBloqueId)) {
        mostrarNotificacion('El bloque se superpone con uno existente en el mismo día', 'error');
        return;
    }

    let nombre = generarNombreBloque(tipo);

    const nuevoBloque = {
        id: estado.editandoBloqueId || generarIdUnico(),
        day: dia,
        type: tipo,
        start: inicio,
        end: fin, // ✅ Ahora siempre tendrá valor
        nombre: nombre,
        classType: tipo === 'class' ? document.getElementById('class-type').value : null,
        breakType: tipo === 'break' ? document.getElementById('break-type').value : null
    };

    if (estado.editandoBloqueId) {
        const index = estado.bloques.findIndex(b => b.id === estado.editandoBloqueId);
        if (index !== -1) {
            estado.bloques[index] = nuevoBloque;
            mostrarNotificacion('Bloque actualizado correctamente', 'success');
        }
    } else {
        estado.bloques.push(nuevoBloque);
        // Ajustar página para mostrar el nuevo bloque (ir a la última página)
        const limite = Number.isFinite(estado.filtroBloquesLimite) ? estado.filtroBloquesLimite : 10;
        if (limite > 0) {
            const total = (estado.filtroBloquesDia && estado.filtroBloquesDia !== 'Todos')
                ? estado.bloques.filter(b => b.day === estado.filtroBloquesDia).length
                : estado.bloques.length;
            estado.paginaBloques = Math.max(1, Math.ceil(total / limite));
        }
        mostrarNotificacion('Bloque agregado correctamente', 'success');
    }

    actualizarUI();
    cerrarFormularioBloque();
}

function editarBloque(id) {
    const bloque = estado.bloques.find(b => b.id == id);
    if (!bloque) {
        mostrarNotificacion('Bloque no encontrado', 'error');
        return;
    }

    estado.editandoBloqueId = id;
    
    document.getElementById('block-day').value = bloque.day;
    document.getElementById('block-type').value = bloque.type;
    document.getElementById('block-start').value = bloque.start;
    document.getElementById('block-end').value = bloque.end;
    
    if (bloque.type === 'class' && bloque.classType) {
        document.getElementById('class-type').value = bloque.classType;
    }
    if (bloque.type === 'break' && bloque.breakType) {
        document.getElementById('break-type').value = bloque.breakType;
    }
    
    document.getElementById('block-form-title').textContent = 'Editar Bloque';
    document.getElementById('save-block-text').textContent = 'Actualizar';
    actualizarFormularioBloque();
    
    // Evitar cierre inmediato por listener global
    evitarCierreFlotante = true;
    document.getElementById('floating-block-form').style.display = 'block';
    document.getElementById('floating-block-form').scrollIntoView({ behavior: 'smooth' });
}

function eliminarBloque(id) {
    mostrarAlerta(
        'Eliminar Bloque',
        '¿Está seguro de eliminar este bloque horario?',
        'warning',
        () => {
            estado.bloques = estado.bloques.filter(b => b.id != id);
            // Asegurar que la página actual sea válida tras eliminar
            const limite = Number.isFinite(estado.filtroBloquesLimite) ? estado.filtroBloquesLimite : 10;
            if (limite > 0) {
                const total = (estado.filtroBloquesDia && estado.filtroBloquesDia !== 'Todos')
                    ? estado.bloques.filter(b => b.day === estado.filtroBloquesDia).length
                    : estado.bloques.length;
                const totalPaginas = Math.max(1, Math.ceil(total / limite));
                if (estado.paginaBloques > totalPaginas) estado.paginaBloques = totalPaginas;
            }
            actualizarUI();
            mostrarNotificacion('Bloque eliminado correctamente', 'success');
        }
    );
}

function configurarEliminacionHorario(id, nombre) {
    console.log('🗑️ Configurando eliminación para horario ID:', id);
    
    if (!id || id === 'null' || id === 'undefined') {
        mostrarNotificacion('ID de horario inválido', 'error');
        return;
    }

    const horarioId = parseInt(id);
    if (isNaN(horarioId) || horarioId <= 0) {
        mostrarNotificacion('ID de horario numérico inválido', 'error');
        return;
    }
    
    mostrarAlerta(
        'Eliminar Horario',
        `¿Está seguro de eliminar el horario "${nombre}"? Esta acción no se puede deshacer.`,
        'error',
        () => eliminarHorario(horarioId)
    );
}

// =============================================
// FUNCIONES DE UTILIDAD
// =============================================

function timeToMinutes(timeStr) {
    if (!timeStr || timeStr === '') {
        console.warn('⚠️ timeToMinutes recibió tiempo vacío');
        return 0;
    }
    
    // Manejar formato HH:MM
    if (timeStr.match(/^\d{1,2}:\d{2}$/)) {
        const [hours, minutes] = timeStr.split(':').map(Number);
        return hours * 60 + minutes;
    }
    
    console.warn('⚠️ Formato de tiempo no reconocido:', timeStr);
    return 0;
}

function minutesToTime(minutes) {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
}

// Normaliza nombres de días para comparaciones (quita acentos y minúsculas)
function normalizeDayName(name) {
    if (!name) return '';
    return name
        .toString()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '') // quitar diacríticos
        .toLowerCase();
}

function formatTime12h(time24h) {
    if (!time24h) return '';
    const [hours, minutes] = time24h.split(':');
    const hour = parseInt(hours);
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const hour12 = hour % 12 || 12;
    return `${hour12}:${minutes} ${ampm}`;
}

function calcularHoraInicio() {
    if (estado.bloques.length === 0) return '06:00';
    const minutos = Math.min(...estado.bloques.map(b => timeToMinutes(b.start)));
    return minutesToTime(Math.floor(minutos / 60) * 60);
}

function calcularHoraFin() {
    if (estado.bloques.length === 0) return '17:00';
    const minutos = Math.max(...estado.bloques.map(b => timeToMinutes(b.end)));
    return minutesToTime(Math.ceil(minutos / 60) * 60);
}

function haySuperposicion(dia, inicio, fin, excluirId = null) {
    const inicioNuevo = timeToMinutes(inicio);
    const finNuevo = timeToMinutes(fin);
    
    return estado.bloques.some(bloque => {
        if (bloque.day !== dia) return false;
        if (excluirId && bloque.id == excluirId) return false;
        
        const inicioExistente = timeToMinutes(bloque.start);
        const finExistente = timeToMinutes(bloque.end);
        
        return inicioNuevo < finExistente && finNuevo > inicioExistente;
    });
}

function generarNombreBloque(tipo) {
    if (tipo === 'class') {
        const tipoClase = document.getElementById('class-type').value;
        return tipoClase === 'double' ? 'Clase Doble' : 'Clase Simple';
    } else {
        const tipoDescanso = document.getElementById('break-type').value;
        const nombres = {
            morning: 'Descanso de Mañana',
            afternoon: 'Descanso de Tarde',
            lunch: 'Almuerzo',
            custom: 'Otro'
        };
        return nombres[tipoDescanso] || 'Descanso';
    }
}

function generarIdUnico() {
    return Date.now() + Math.random().toString(36).substr(2, 9);
}

// Sugerir horas para un día dado basándose en los bloques existentes del mismo día
function sugerirHorasParaDia(dia) {
    try {
        const inicioInput = document.getElementById('block-start');
        const finInput = document.getElementById('block-end');
        if (!inicioInput || !finInput) return;

        const bloquesDia = estado.bloques
            .filter(b => b.day === dia)
            .sort((a, b) => timeToMinutes(a.end) - timeToMinutes(b.end));

        let sugeridoInicio = '06:00';
        if (bloquesDia.length > 0) {
            const ultimoFinMin = timeToMinutes(bloquesDia[bloquesDia.length - 1].end);
            sugeridoInicio = minutesToTime(ultimoFinMin);
        }
        const sugeridoFin = minutesToTime(timeToMinutes(sugeridoInicio) + 60); // 60 min por defecto

        inicioInput.value = sugeridoInicio;
        finInput.value = sugeridoFin;
    } catch (e) {
        console.warn('No fue posible sugerir horas para el día', dia, e);
    }
}

// Ajustar duración automáticamente según el tipo de bloque/clase
function ajustarDuracionPorTipo() {
    const tipo = document.getElementById('block-type')?.value;
    const classType = document.getElementById('class-type')?.value;
    const inicioEl = document.getElementById('block-start');
    const finEl = document.getElementById('block-end');
    if (!inicioEl || !finEl) return;

    const inicio = inicioEl.value;
    if (!inicio) return;

    if (tipo === 'class' && classType === 'double') {
        // Clase doble: 120 minutos
        finEl.value = minutesToTime(timeToMinutes(inicio) + 120);
    } else if (tipo === 'class' && classType === 'single') {
        // Clase simple: 45 minutos por consistencia con el resto del sistema
        finEl.value = minutesToTime(timeToMinutes(inicio) + 45);
    }
}

function generarIntervalosTiempo() {
    if (estado.bloques.length === 0) return [];
    
    const todosLosTiempos = new Set();
    estado.bloques.forEach(bloque => {
        todosLosTiempos.add(timeToMinutes(bloque.start));
        todosLosTiempos.add(timeToMinutes(bloque.end));
    });

    const tiemposOrdenados = Array.from(todosLosTiempos).sort((a, b) => a - b);
    const intervalos = [];

    for (let i = 0; i < tiemposOrdenados.length - 1; i++) {
        const inicio = tiemposOrdenados[i];
        const fin = tiemposOrdenados[i + 1];
        
        if (fin - inicio >= 15) {
            intervalos.push({
                inicio: minutesToTime(inicio),
                fin: minutesToTime(fin)
            });
        }
    }

    return intervalos;
}

// =============================================
// GESTIÓN DE FORMULARIOS Y MODALES
// =============================================

function actualizarFormularioBloque() {
    const tipo = document.getElementById('block-type').value;
    document.getElementById('class-details-group').style.display = tipo === 'class' ? 'block' : 'none';
    document.getElementById('break-details-group').style.display = tipo === 'break' ? 'block' : 'none';
}

function resetearFormularioBloque() {
    document.getElementById('block-day').value = 'Lunes';
    document.getElementById('block-type').value = 'class';
    document.getElementById('block-start').value = '06:00';
    document.getElementById('block-end').value = '07:00'; 
    document.getElementById('class-type').value = 'single';
    document.getElementById('break-type').value = 'morning';
    actualizarFormularioBloque();
}

function cerrarFormularioBloque() {
    document.getElementById('floating-block-form').style.display = 'none';
    estado.editandoBloqueId = null;
    resetearFormularioBloque();
}

function nuevoHorario() {
    mostrarAlerta(
        'Nuevo Horario',
        '¿Está seguro de crear un nuevo horario? Se perderán los cambios no guardados.',
        'warning',
        () => {
            estado.bloques = [];
            estado.horarioCargadoId = null;
            estado.diasActivos = new Set(['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']);

            const nameEl = document.getElementById('schedule-name');
            const periodEl = document.getElementById('schedule-period');
            if (nameEl) nameEl.value = '';
            if (periodEl) periodEl.value = 'Anual';
            const delBtn = document.getElementById('delete-schedule-btn');
            if (delBtn) delBtn.style.display = 'none';
            const saveBtn = document.getElementById('save-schedule-btn');
            if (saveBtn) saveBtn.innerHTML = '<i class="fas fa-save"></i> Guardar Horario';

            actualizarUI();
            mostrarNotificacion('Nuevo horario listo para configurar', 'success');
        }
    );
}

function mostrarModalAsignacion() {
    if (estado.horarios.length === 0) {
        mostrarNotificacion('No hay horarios guardados para asignar', 'warning');
        return;
    }

    if (estado.cursos.length === 0) {
        mostrarNotificacion('No hay cursos disponibles para asignar', 'warning');
        return;
    }

    console.log('📋 Cursos para asignación:', estado.cursos);

    const cursosLista = document.getElementById('courses-list');
    cursosLista.innerHTML = estado.cursos.map(curso => {
        // Usar el ID correcto del curso
        const cursoId = curso.id_curso || curso.id;
        const tieneHorario = curso.horario_general_id || curso.horario_asignado;
        
        if (!cursoId) {
            console.warn('⚠️ Curso sin ID válido:', curso);
            return '';
        }

        return `
            <div class="course-item">
                <input type="checkbox" class="course-checkbox" value="${cursoId}" 
                       id="curso-${cursoId}">
                <label for="curso-${cursoId}" class="course-info">
                    <div class="course-name">${curso.nombreCurso || curso.nombre || 'Curso sin nombre'}</div>
                    <div class="course-details">Sede: ${curso.sede || 'Sin sede'}</div>
                </label>
                <div class="course-schedule ${tieneHorario ? 'has-schedule' : 'no-schedule'}">
                    ${tieneHorario ? '✓ Con horario' : '✗ Sin horario'}
                </div>
            </div>
        `;
    }).join('');

    document.getElementById('assign-schedule-modal').style.display = 'flex';
    // Reiniciar estado del modal
    asignacionModal.page = 1;

    // Inicializar contador
    actualizarContadorSeleccionCursos();
    // Escuchar cambios en checkboxes
    cursosLista.querySelectorAll('.course-checkbox').forEach(cb => {
        cb.addEventListener('change', actualizarContadorSeleccionCursos);
    });

    // Filtro/buscador de cursos
    const buscador = document.getElementById('courses-search');
    if (buscador) {
        buscador.value = '';
        buscador.addEventListener('input', () => {
            asignacionModal.search = buscador.value;
            aplicarFiltrosYPaginacion();
        });
    }
    // Poblar filtro de sedes y enlazar
    const sedeSel = document.getElementById('courses-sede-filter');
    if (sedeSel) {
        // Construir set de sedes desde los items
        const sedes = new Set();
        document.querySelectorAll('#courses-list .course-item .course-details').forEach(el => {
            const m = /Sede:\s*(.+)/i.exec(el.textContent || '');
            if (m && m[1]) sedes.add(m[1].trim());
        });
        const actual = sedeSel.value;
        // Limpiar opciones (menos 'Todas las sedes') y rellenar
        while (sedeSel.options.length > 1) sedeSel.remove(1);
        Array.from(sedes).sort().forEach(nombre => {
            const opt = document.createElement('option');
            opt.value = nombre; opt.text = nombre; sedeSel.appendChild(opt);
        });
        if (actual && Array.from(sedes).includes(actual)) sedeSel.value = actual; else sedeSel.value = '';
        sedeSel.addEventListener('change', () => {
            asignacionModal.sede = sedeSel.value || '';
            asignacionModal.page = 1;
            aplicarFiltrosYPaginacion();
        });
    }

    // Filtro por estado asignado
    const assignedSel = document.getElementById('courses-assigned-filter');
    if (assignedSel) {
        assignedSel.value = '';
        assignedSel.addEventListener('change', () => {
            asignacionModal.assigned = assignedSel.value || '';
            asignacionModal.page = 1;
            aplicarFiltrosYPaginacion();
        });
    }

    // Paginación
    const prevBtn = document.getElementById('prev-page-btn');
    const nextBtn = document.getElementById('next-page-btn');
    if (prevBtn) prevBtn.onclick = () => { asignacionModal.page = Math.max(1, asignacionModal.page - 1); aplicarFiltrosYPaginacion(); };
    if (nextBtn) nextBtn.onclick = () => { asignacionModal.page += 1; aplicarFiltrosYPaginacion(); };

    // Aplicar filtros inicialmente
    aplicarFiltrosYPaginacion();
}

async function confirmarAsignacion() {
    const horarioSelect = document.getElementById('schedule-select');
    const horarioId = parseInt(horarioSelect.value);
    const checkboxes = Array.from(document.querySelectorAll('.course-checkbox:checked'));
    const cursosSeleccionados = checkboxes
        .map(cb => parseInt(cb.value))
        .filter(id => !isNaN(id) && id > 0);

    console.log('🎯 Confirmando asignación - Horario ID:', horarioId, 'Cursos:', cursosSeleccionados);

    if (!horarioId || isNaN(horarioId)) {
        mostrarNotificacion('Seleccione un horario válido de la lista', 'error');
        return;
    }

    if (cursosSeleccionados.length === 0) {
        mostrarNotificacion('Seleccione al menos un curso', 'error');
        return;
    }

    const conHorario = checkboxes.filter(cb => {
        const item = cb.closest('.course-item');
        const badge = item ? item.querySelector('.course-schedule.has-schedule') : null;
        return !!badge;
    });

    const proceder = async () => {
        const exito = await asignarHorarioCursos(horarioId, cursosSeleccionados);
        if (exito) {
            document.getElementById('assign-schedule-modal').style.display = 'none';
            await cargarCursos();
        }
        // Cerrar loader por si quedó abierto por cualquier flujo
        ocultarLoading();
    };

    if (conHorario.length > 0) {
        const count = conHorario.length;
        const mensaje = `Se detectó ${count} curso${count>1?'s':''} con horario asignado. Si confirmas, se reemplazará el horario actual por el seleccionado. Esto puede afectar clases ya planificadas.`;
        mostrarAlerta('Reemplazar horario de curso', mensaje, 'warning', proceder);
        return;
    }

    await proceder();
}

// =============================================
// INICIALIZACIÓN Y CONFIGURACIÓN DE EVENTOS
// =============================================

function configurarEventListeners() {
    // Días de la semana
    document.querySelectorAll('.day').forEach(dia => {
        dia.addEventListener('click', function() {
            const diaNombre = this.dataset.day;
            const estabaActivo = estado.diasActivos.has(diaNombre);
            if (estabaActivo) {
                const tieneBloques = estado.bloques.some(b => b.day === diaNombre);
                if (tieneBloques) {
                    mostrarAlerta(
                        'Desactivar día',
                        `El día ${diaNombre} tiene bloques asignados. ¿Desea desactivarlo y eliminar esos bloques?`,
                        'warning',
                        () => {
                            estado.diasActivos.delete(diaNombre);
                            estado.bloques = estado.bloques.filter(b => b.day !== diaNombre);
                            actualizarUI();
                        }
                    );
                    return;
                }
                estado.diasActivos.delete(diaNombre);
            } else {
                estado.diasActivos.add(diaNombre);
            }
            actualizarUI();
        });
    });

    // Botón "Seleccionar Todos"
    document.getElementById('select-all-days').addEventListener('click', function() {
        const todosDias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
        if (estado.diasActivos.size === todosDias.length) {
            estado.diasActivos.clear();
            estado.bloques = [];
        } else {
            estado.diasActivos = new Set(todosDias);
        }
        actualizarUI();
    });

    // Gestión de bloques
    document.getElementById('add-block-btn').addEventListener('click', function() {
        estado.editandoBloqueId = null;
        document.getElementById('block-form-title').textContent = 'Nuevo Bloque';
        document.getElementById('save-block-text').textContent = 'Guardar';
        resetearFormularioBloque();
        // Evitar cierre inmediato por listener global
        evitarCierreFlotante = true;
        document.getElementById('floating-block-form').style.display = 'block';
        // Prefijar horas en función del último bloque del día seleccionado
        const diaSel = document.getElementById('block-day').value;
        sugerirHorasParaDia(diaSel);
    });

    // Delegación de eventos para editar/eliminar bloques
    const blocksContainer = document.getElementById('blocks-container');
    if (blocksContainer) {
        blocksContainer.addEventListener('click', (e) => {
            const editBtn = e.target.closest('.btn-edit');
            if (editBtn) {
                const id = editBtn.getAttribute('data-block-id');
                if (id) editarBloque(id);
                return;
            }
            const delBtn = e.target.closest('.btn-delete');
            if (delBtn) {
                const id = delBtn.getAttribute('data-block-id');
                if (id) eliminarBloque(id);
            }
        });
    }

    // Fallback global: si por alguna razón el listener del contenedor no captura
    document.addEventListener('click', (e) => {
        const editBtn = e.target.closest && e.target.closest('.btn-edit');
        if (editBtn) {
            e.preventDefault();
            const id = editBtn.getAttribute('data-block-id');
            if (id) editarBloque(id);
            return;
        }
        const delBtn = e.target.closest && e.target.closest('.btn-delete');
        if (delBtn) {
            e.preventDefault();
            const id = delBtn.getAttribute('data-block-id');
            if (id) eliminarBloque(id);
        }
    });

    document.getElementById('block-type').addEventListener('change', function() {
        actualizarFormularioBloque();
        ajustarDuracionPorTipo();
    });
    // Si cambia el día mientras se crea un bloque nuevo, sugerir horas para ese día
    document.getElementById('block-day').addEventListener('change', function() {
        if (!estado.editandoBloqueId) {
            sugerirHorasParaDia(this.value);
        }
    });
    // Ajustar duración cuando cambia tipo de clase o la hora de inicio
    const classTypeEl = document.getElementById('class-type');
    if (classTypeEl) {
        classTypeEl.addEventListener('change', ajustarDuracionPorTipo);
    }
    const startEl = document.getElementById('block-start');
    if (startEl) {
        startEl.addEventListener('change', ajustarDuracionPorTipo);
        startEl.addEventListener('input', ajustarDuracionPorTipo);
    }
    document.getElementById('save-block-btn').addEventListener('click', agregarBloque);
    document.getElementById('cancel-block-btn').addEventListener('click', cerrarFormularioBloque);

    // Cerrar formulario al hacer click fuera
    document.addEventListener('click', function(e) {
        const formulario = document.getElementById('floating-block-form');
        // Si acabamos de abrir el formulario, ignorar el primer click global
        if (evitarCierreFlotante) {
            evitarCierreFlotante = false;
            return;
        }
        if (formulario.style.display === 'block' && 
            !formulario.contains(e.target) && 
            e.target.id !== 'add-block-btn') {
            cerrarFormularioBloque();
        }
    });

    document.getElementById('save-schedule-btn').addEventListener('click', async function() {
        console.log('💾 Intentando guardar horario...');
        
        const resultado = await guardarHorarioBD();
        if (resultado) {
            console.log('✅ Horario guardado exitosamente:', resultado);
            // resultado puede ser el objeto horario devuelto con id_horario
            estado.horarioCargadoId = (resultado.id_horario || resultado.id || resultado.horario_id || estado.horarioCargadoId);
            document.getElementById('delete-schedule-btn').style.display = 'block';
            
            // Recargar la lista de horarios
            await cargarHorariosGuardados();
        } else {
            console.log('❌ Error al guardar horario');
            mostrarNotificacion('No se pudo guardar el horario. Verifique los campos y los bloques.', 'error');
        }
    });

    // Botones principales
    document.getElementById('new-schedule-btn').addEventListener('click', nuevoHorario);
    document.getElementById('assign-schedule-btn').addEventListener('click', mostrarModalAsignacion);
    
    document.getElementById('delete-schedule-btn').addEventListener('click', function() {
        if (estado.horarioCargadoId) {
            const horarioActual = estado.horarios.find(h => (h.id_horario || h.id) === estado.horarioCargadoId);
            const nombre = horarioActual && horarioActual.nombre ? horarioActual.nombre : 'este horario';
            configurarEliminacionHorario(estado.horarioCargadoId.toString(), nombre);
        }
    });

    // Cerrar modales
    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', function() {
            this.closest('.modal').style.display = 'none';
        });
    });

    // Cerrar modal al hacer click fuera
    document.getElementById('assign-schedule-modal').addEventListener('click', function(e) {
        if (e.target === this) {
            this.style.display = 'none';
        }
    });

    document.getElementById('custom-alert').addEventListener('click', function(e) {
        if (e.target === this) {
            this.style.display = 'none';
        }
    });

    // Confirmar asignación
    document.getElementById('confirm-assign-btn').addEventListener('click', confirmarAsignacion);
    const assignAllBtn = document.getElementById('assign-all-btn');
    if (assignAllBtn) {
        assignAllBtn.addEventListener('click', () => {
            // Seleccionar todos los cursos FILTRADOS (todas las páginas)
            const items = asignacionModal.filteredItems && asignacionModal.filteredItems.length
                ? asignacionModal.filteredItems
                : Array.from(document.querySelectorAll('#courses-list .course-item'));
            items.forEach(item => {
                const cb = item.querySelector('.course-checkbox');
                if (cb) cb.checked = true;
            });
            actualizarContadorSeleccionCursos();
        });
    }
    const assignNoneBtn = document.getElementById('assign-none-btn');
    if (assignNoneBtn) {
        assignNoneBtn.addEventListener('click', () => {
            const items = asignacionModal.filteredItems && asignacionModal.filteredItems.length
                ? asignacionModal.filteredItems
                : Array.from(document.querySelectorAll('#courses-list .course-item'));
            items.forEach(item => {
                const cb = item.querySelector('.course-checkbox');
                if (cb) cb.checked = false;
            });
            actualizarContadorSeleccionCursos();
        });
    }

    // Desasignar seleccionados
    const unassignBtn = document.getElementById('unassign-selected-btn');
    if (unassignBtn) {
        unassignBtn.addEventListener('click', async () => {
            const universo = (asignacionModal.filteredItems && asignacionModal.filteredItems.length)
                ? asignacionModal.filteredItems
                : Array.from(document.querySelectorAll('#courses-list .course-item'));
            const seleccionados = universo
                .map(item => ({ item, cb: item.querySelector('.course-checkbox') }))
                .filter(x => x.cb && x.cb.checked);
            if (seleccionados.length === 0) { mostrarNotificacion('No hay cursos seleccionados', 'warning'); return; }
            try {
                mostrarLoading('Desasignando cursos...');
                const ids = seleccionados.map(x => parseInt(x.cb.value)).filter(n => !isNaN(n) && n > 0);
                const resp = await apiRequest('/admin/api/horarios/desasignar', { method: 'POST', body: { cursos_ids: ids } });
                if (resp && resp.success) {
                    // Actualizar UI de badges
                    seleccionados.forEach(x => {
                        const badge = x.item.querySelector('.course-schedule');
                        if (badge) { badge.classList.remove('has-schedule'); badge.classList.add('no-schedule'); badge.textContent = '✗ Sin horario'; }
                        x.cb.checked = false;
                    });
                    mostrarNotificacion(`Se desasignó el horario de ${ids.length} curso(s)`, 'success');
                    actualizarContadorSeleccionCursos();
                } else {
                    throw new Error(resp?.error || 'Error al desasignar');
                }
            } catch (e) {
                mostrarNotificacion('Error al desasignar: ' + e.message, 'error');
            } finally {
                ocultarLoading();
            }
        });
    }
}

function actualizarContadorSeleccionCursos() {
    const universo = (asignacionModal.filteredItems && asignacionModal.filteredItems.length)
        ? asignacionModal.filteredItems
        : Array.from(document.querySelectorAll('#courses-list .course-item'));
    const total = universo.length;
    const seleccionados = universo.filter(item => item.querySelector('.course-checkbox')?.checked).length;
    const lbl = document.getElementById('assign-selection-counter');
    if (lbl) lbl.textContent = `${seleccionados} seleccionados de ${total}`;
}

function filtrarCursosModal(termino) {
    asignacionModal.search = (termino || '').toString();
    aplicarFiltrosYPaginacion();
}

function aplicarFiltrosYPaginacion() {
    const q = (asignacionModal.search || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    const sedeFiltro = asignacionModal.sede || '';
    const assigned = asignacionModal.assigned || '';
    const items = Array.from(document.querySelectorAll('#courses-list .course-item'));

    // Filtrar
    const filtrados = items.filter(item => {
        const texto = item.innerText.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        if (q && !texto.includes(q)) return false;
        if (sedeFiltro) {
            const details = item.querySelector('.course-details');
            const sedeTxt = details ? details.textContent : '';
            if (!sedeTxt.includes(sedeFiltro)) return false;
        }
        if (assigned === 'con' && !item.querySelector('.course-schedule.has-schedule')) return false;
        if (assigned === 'sin' && !item.querySelector('.course-schedule.no-schedule')) return false;
        return true;
    });

    // Guardar referencia para seleccionar/deseleccionar y contador global
    asignacionModal.filteredItems = filtrados;

    // Paginación
    const total = filtrados.length;
    const perPage = asignacionModal.pageSize;
    const totalPages = Math.max(1, Math.ceil(total / perPage));
    if (asignacionModal.page > totalPages) asignacionModal.page = totalPages;
    const start = (asignacionModal.page - 1) * perPage;
    const end = start + perPage;
    const visibles = new Set(filtrados.slice(start, end));

    // Aplicar visibilidad
    items.forEach(item => { item.style.display = visibles.has(item) ? '' : 'none'; });

    // UI de paginación
    const pi = document.getElementById('page-info');
    if (pi) pi.textContent = `Página ${totalPages === 0 ? 0 : asignacionModal.page} de ${totalPages}`;
    const prevBtn = document.getElementById('prev-page-btn');
    const nextBtn = document.getElementById('next-page-btn');
    if (prevBtn) prevBtn.disabled = asignacionModal.page <= 1;
    if (nextBtn) nextBtn.disabled = asignacionModal.page >= totalPages;

    actualizarContadorSeleccionCursos();
}

async function inicializar() {
    console.log('🚀 Inicializando sistema de horarios...');
    
    try {
        mostrarLoading('Inicializando sistema de horarios...');
        
        await Promise.allSettled([
            cargarEstadisticas(),
            cargarHorariosGuardados(),
            cargarCursos()
        ]);

        // Cargar periodos académicos del ciclo activo para el selector
        try {
            await cargarPeriodosAcademicosSelect();
        } catch (e) {
            console.warn('No fue posible cargar periodos académicos, se mantiene opción por defecto:', e.message);
        }

        configurarEventListeners();
        actualizarUI();
        
        mostrarNotificacion('Sistema de horarios cargado correctamente', 'success');
        
    } catch (error) {
        console.error('❌ Error en inicialización:', error);
        mostrarNotificacion('Error al inicializar el sistema: ' + error.message, 'error');
    } finally {
        ocultarLoading();
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', inicializar);

// Exportar funciones globales para uso en HTML
window.cargarHorario = cargarHorario;
window.editarBloque = editarBloque;
window.eliminarBloque = eliminarBloque;
window.configurarEliminacionHorario = configurarEliminacionHorario;

// Modal para reasignar clases cuando no se permite eliminar
function mostrarModalReasignacion(origenId, mensaje, count = 0) {
    // Construir modal rápido (reutiliza custom-alert container para evitar HTML nuevo)
    const alerta = document.getElementById('custom-alert');
    if (!alerta) return alert(mensaje);
    document.getElementById('alert-icon').innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
    document.getElementById('alert-title').textContent = 'Reasignar clases';
    const body = alerta.querySelector('.custom-alert-body');
    // Incluir todos los horarios disponibles excepto el de origen
    const destinos = estado.horarios.filter(h => (h.id_horario || h.id) !== origenId);
    const opciones = destinos.map(h => {
        const periodo = h.periodo || 'Anual';
        const hi = h.horaInicio || '??:??';
        const hf = h.horaFin || '??:??';
        const label = `${h.nombre} — ${periodo} — ${hi} a ${hf}`;
        return `<option value="${h.id_horario||h.id}">${label}</option>`;
    }).join('');
    const sinDestinos = destinos.length === 0;
    body.innerHTML = `
        <div style="color:#444; margin-bottom:10px;">${mensaje}</div>
        <div style="margin:8px 0 14px 0;">
            <span style="background:#E6F0FA;color:#0D3B66;border-radius:999px;padding:6px 10px;font-weight:700;">${count} clases afectadas</span>
        </div>
        ${sinDestinos ? `
            <div style="background:#FFF3CD;color:#856404;border:1px solid #FFEEBA;padding:10px;border-radius:8px;margin-bottom:8px;">
                No hay otros horarios disponibles para reasignar. Cree un horario o active otro existente.
            </div>
        ` : `
            <label style="font-weight:600; color:#0D3B66;">Seleccione horario destino</label>
            <select id="reassign-target" style="width:100%; padding:10px; border:2px solid var(--border); border-radius:10px; margin-top:6px;">${opciones}</select>
        `}
    `;
    const btnOk = document.getElementById('alert-confirm');
    const btnCancel = document.getElementById('alert-cancel');
    const okClone = btnOk.cloneNode(true);
    const cancelClone = btnCancel.cloneNode(true);
    btnOk.parentNode.replaceChild(okClone, btnOk);
    btnCancel.parentNode.replaceChild(cancelClone, btnCancel);
    okClone.textContent = sinDestinos ? 'Cerrar' : okClone.textContent;
    okClone.onclick = async () => {
        if (sinDestinos) { alerta.style.display = 'none'; return; }
        const selectEl = document.getElementById('reassign-target');
        const target = selectEl ? selectEl.value : null;
        if (!target) { mostrarNotificacion('Seleccione un horario destino', 'warning'); return; }
        try {
            const resp = await fetch(`/admin/api/horarios/${origenId}/reassign-classes`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_horario_id: parseInt(target) })
            });
            const json = await resp.json();
            if (!resp.ok || !json.success) throw new Error(json.error || 'Fallo al reasignar');
            mostrarNotificacion(json.message || 'Clases reasignadas', 'success');
            alerta.style.display = 'none';
            // Reintentar eliminación
            await eliminarHorario(origenId);
        } catch (e) {
            mostrarNotificacion('Error en la reasignación: ' + e.message, 'error');
        }
    };
    cancelClone.onclick = () => { alerta.style.display = 'none'; };
    alerta.style.display = 'flex';
}