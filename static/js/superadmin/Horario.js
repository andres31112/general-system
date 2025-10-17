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

// Estado de la aplicación
let estado = {
    horarios: [],
    cursos: [],
    horarioActual: null,
    bloques: [],
    diasActivos: new Set(['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']),
    editandoBloqueId: null,
    horarioCargadoId: null
};

// =============================================
// FUNCIONES DE UTILIDAD
// =============================================

function mostrarLoading(mensaje = 'Cargando...') {
    document.getElementById('loading-message').textContent = mensaje;
    document.getElementById('loading-modal').style.display = 'flex';
}

function ocultarLoading() {
    document.getElementById('loading-modal').style.display = 'none';
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
    try {
        console.log('🔗 API Request:', url, options.method || 'GET');
        
        const config = {
            headers: {
                'Content-Type': 'application/json',
            },
            ...options
        };

        if (config.body) {
            config.body = JSON.stringify(config.body);
            console.log('📦 Request Body:', config.body);
        }

        const response = await fetch(url, config);
        console.log('📥 API Response Status:', response.status);
        
        if (!response.ok) {
            let errorMessage = `Error ${response.status}: ${response.statusText}`;
            
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorData.message || errorMessage;
                console.error('❌ API Error Data:', errorData);
            } catch (e) {
                const text = await response.text();
                if (text) errorMessage += ` - ${text.substring(0, 200)}`;
            }
            
            throw new Error(errorMessage);
        }

        const data = await response.json();
        console.log('✅ API Success:', data);
        return data;
        
    } catch (error) {
        console.error('❌ API Error:', error);
        throw error;
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

        // Procesar días
        if (horarioData.diasSemana) {
            try {
                if (typeof horarioData.diasSemana === 'string') {
                    const diasArray = JSON.parse(horarioData.diasSemana);
                    if (Array.isArray(diasArray)) {
                        diasArray.forEach(dia => estado.diasActivos.add(dia));
                    }
                } else if (Array.isArray(horarioData.diasSemana)) {
                    horarioData.diasSemana.forEach(dia => estado.diasActivos.add(dia));
                }
            } catch (e) {
                console.warn('Error procesando días, usando días por defecto');
                ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes'].forEach(dia => estado.diasActivos.add(dia));
            }
        }

        // Procesar bloques
        if (horarioData.bloques && Array.isArray(horarioData.bloques)) {
            estado.bloques = horarioData.bloques.map(bloque => ({
                id: bloque.id_bloque || bloque.id || generarIdUnico(),
                day: bloque.dia_semana || bloque.day || 'Lunes',
                type: bloque.tipo || bloque.type || 'class',
                start: formatTimeForInput(bloque.horaInicio || bloque.start || '07:00'),
                end: formatTimeForInput(bloque.horaFin || bloque.end || '07:45'),
                nombre: bloque.nombre || 'Bloque',
                classType: bloque.class_type || bloque.classType || 'single',
                breakType: bloque.break_type || bloque.breakType || 'morning'
            })).filter(bloque => bloque.day && bloque.start && bloque.end);
        }

        estado.horarioCargadoId = horarioId;

        // Actualizar interfaz
        if (horarioData.nombre) {
            document.getElementById('schedule-name').value = horarioData.nombre;
        }
        
        if (horarioData.periodo) {
            document.getElementById('schedule-period').value = horarioData.periodo;
        }

        actualizarUI();
        document.getElementById('delete-schedule-btn').style.display = 'block';
        
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
    if (!timeValue) return '07:00';
    
    if (typeof timeValue === 'string' && timeValue.match(/^\d{1,2}:\d{2}$/)) {
        const [hours, minutes] = timeValue.split(':');
        return `${hours.padStart(2, '0')}:${minutes.padStart(2, '0')}`;
    }
    
    if (typeof timeValue === 'object' && timeValue.hours !== undefined) {
        return `${timeValue.hours.toString().padStart(2, '0')}:${timeValue.minutes.toString().padStart(2, '0')}`;
    }
    
    return '07:00';
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

    // ✅ VALIDACIÓN CRÍTICA: Asegurar que todos los bloques tengan hora_fin
    const bloquesConHoraFin = estado.bloques.map((bloque, index) => {
        // Si no hay hora_fin, calcularla basándose en la hora_inicio
        if (!bloque.end || bloque.end === '') {
            const horaInicio = timeToMinutes(bloque.start);
            const horaFin = horaInicio + 45; // 45 minutos por defecto
            bloque.end = minutesToTime(horaFin);
            console.warn(`⚠️ Bloque ${index} sin hora_fin, calculada automáticamente: ${bloque.end}`);
        }
        
        // Validar que hora_fin sea posterior a hora_inicio
        if (timeToMinutes(bloque.start) >= timeToMinutes(bloque.end)) {
            const horaInicio = timeToMinutes(bloque.start);
            const horaFin = horaInicio + 45; // 45 minutos por defecto
            bloque.end = minutesToTime(horaFin);
            console.warn(`⚠️ Bloque ${index} con hora_fin anterior a inicio, corregido: ${bloque.end}`);
        }

        return {
            dia_semana: bloque.day,
            horaInicio: bloque.start,
            horaFin: bloque.end, // ✅ Ahora siempre tendrá valor
            tipo: bloque.type,
            nombre: bloque.nombre || `Bloque ${index + 1}`,
            orden: index,
            class_type: bloque.classType,
            break_type: bloque.breakType
        };
    });

    // ✅ CALCULAR HORAS DE INICIO Y FIN GLOBALES
    const horaInicio = calcularHoraInicio();
    const horaFin = calcularHoraFin();

    const datosHorario = {
        nombre: nombre,
        periodo: periodo,
        dias: Array.from(estado.diasActivos),
        bloques: bloquesConHoraFin,
        horaInicio: horaInicio,
        horaFin: horaFin,
        duracion_clase: 45,
        duracion_descanso: 15
    };

    console.log('💾 Guardando horario con validación:', datosHorario);
    mostrarLoading('Guardando horario...');

    try {
        const resultado = await apiRequest(API_URLS.crearHorario, {
            method: 'POST',
            body: datosHorario
        });

        console.log('💾 Resultado guardar horario:', resultado);

        if (resultado.success || resultado.id) {
            mostrarNotificacion('Horario guardado correctamente', 'success');
            await cargarHorariosGuardados();
            return resultado.horario || { id: resultado.id, nombre: datosHorario.nombre };
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
        const resultado = await apiRequest(`${API_URLS.eliminarHorario}/${horarioId}`, {
            method: 'DELETE'
        });

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
    } catch (error) {
        console.error('❌ Error asignando horario:', error);
        mostrarNotificacion('Error al asignar horario: ' + error.message, 'error');
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
        const estaActivo = estado.diasActivos.has(dia);
        
        diaElem.classList.toggle('selected', estaActivo);
        
        const bloquesDia = estado.bloques.filter(b => b.day === dia);
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

    contador.textContent = `(${estado.bloques.length})`;

    if (estado.bloques.length === 0) {
        contenedor.innerHTML = `
            <p style="text-align: center; color: #666; padding: 20px;">
                No hay bloques programados. Agregue el primer bloque.
            </p>
        `;
        return;
    }

    estado.bloques.sort((a, b) => timeToMinutes(a.start) - timeToMinutes(b.start));

    contenedor.innerHTML = estado.bloques.map(bloque => `
        <div class="block-item" data-block-id="${bloque.id}">
            <div class="block-info">
                <strong>${bloque.nombre}</strong>
                <div class="block-details">
                    ${bloque.day} • ${formatTime12h(bloque.start)} - ${formatTime12h(bloque.end)}
                    <span class="block-type-tag ${bloque.type}">
                        ${bloque.type === 'class' ? '📚 Clase' : '☕ Descanso'}
                    </span>
                </div>
            </div>
            <div class="block-actions">
                <button class="small secondary" onclick="editarBloque('${bloque.id}')">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="small danger" onclick="eliminarBloque('${bloque.id}')">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `).join('');
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
    
    document.getElementById('class-count').textContent = `${totalClases} clases`;
    document.getElementById('break-count').textContent = `${totalDescansos} descansos`;
    document.getElementById('total-blocks').textContent = `${estado.bloques.length} bloques`;
    
    const estadoConfig = estado.bloques.length > 0 ? 'Configurado' : 'Sin configurar';
    document.getElementById('schedule-config-status').textContent = estadoConfig;
    document.getElementById('schedule-config-status').className = estadoConfig === 'Configurado' ? 'config-ok' : 'config-pending';
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
            console.warn('⚠️ Horario sin ID válido:', horario);
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
                    <button class="small danger" data-horario-id="${horarioId}" data-horario-nombre="${nombreSeguro}">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
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
            item.addEventListener('click', function(e) {
                if (e.target.closest('.schedule-item-actions')) {
                    return;
                }
                const horarioId = this.getAttribute('data-horario-id');
                console.log('🖱️ Click en horario ID:', horarioId, 'Tipo:', typeof horarioId);
                
                if (!horarioId || horarioId === 'null' || horarioId === 'undefined') {
                    mostrarNotificacion('ID de horario no válido', 'error');
                    return;
                }
                
                cargarHorario(horarioId);
            });
        });

        document.querySelectorAll('.schedule-item-actions .danger').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                const horarioId = this.getAttribute('data-horario-id');
                const horarioNombre = this.getAttribute('data-horario-nombre');
                console.log('🗑️ Eliminar horario ID:', horarioId);
                
                if (!horarioId || horarioId === 'null' || horarioId === 'undefined') {
                    mostrarNotificacion('ID de horario no válido para eliminar', 'error');
                    return;
                }
                
                configurarEliminacionHorario(horarioId, horarioNombre);
            });
        });
    }, 100);
}

// =============================================
// GESTIÓN DE BLOQUES
// =============================================

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
            
            document.getElementById('schedule-name').value = '';
            document.getElementById('schedule-period').value = 'Primer Semestre';
            document.getElementById('delete-schedule-btn').style.display = 'none';
            
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
}

async function confirmarAsignacion() {
    const horarioSelect = document.getElementById('schedule-select');
    const horarioId = parseInt(horarioSelect.value);
    const cursosSeleccionados = Array.from(document.querySelectorAll('.course-checkbox:checked'))
        .map(cb => {
            const cursoId = parseInt(cb.value);
            console.log('✅ Curso seleccionado ID:', cursoId);
            return cursoId;
        })
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

    const exito = await asignarHorarioCursos(horarioId, cursosSeleccionados);
    if (exito) {
        document.getElementById('assign-schedule-modal').style.display = 'none';
        // Recargar cursos para actualizar el estado de horarios asignados
        await cargarCursos();
    }
}

// =============================================
// INICIALIZACIÓN Y CONFIGURACIÓN DE EVENTOS
// =============================================

function configurarEventListeners() {
    // Días de la semana
    document.querySelectorAll('.day').forEach(dia => {
        dia.addEventListener('click', function() {
            const diaNombre = this.dataset.day;
            if (estado.diasActivos.has(diaNombre)) {
                estado.diasActivos.delete(diaNombre);
                estado.bloques = estado.bloques.filter(b => b.day !== diaNombre);
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
        document.getElementById('floating-block-form').style.display = 'block';
    });

    document.getElementById('block-type').addEventListener('change', actualizarFormularioBloque);
    document.getElementById('save-block-btn').addEventListener('click', agregarBloque);
    document.getElementById('cancel-block-btn').addEventListener('click', cerrarFormularioBloque);

    // Cerrar formulario al hacer click fuera
    document.addEventListener('click', function(e) {
        const formulario = document.getElementById('floating-block-form');
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
            estado.horarioCargadoId = resultado.id || resultado.horario_id;
            document.getElementById('delete-schedule-btn').style.display = 'block';
            
            // Recargar la lista de horarios
            await cargarHorariosGuardados();
        } else {
            console.log('❌ Error al guardar horario');
        }
    });

    // Botones principales
    document.getElementById('new-schedule-btn').addEventListener('click', nuevoHorario);
    document.getElementById('assign-schedule-btn').addEventListener('click', mostrarModalAsignacion);
    
    document.getElementById('delete-schedule-btn').addEventListener('click', function() {
        if (estado.horarioCargadoId) {
            const horarioActual = estado.horarios.find(h => h.id === estado.horarioCargadoId);
            const nombre = horarioActual ? horarioActual.nombre : 'este horario';
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