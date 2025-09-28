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
    
    // Configurar icono según el tipo
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

    // Configurar botones
    const btnConfirmar = document.getElementById('alert-confirm');
    const btnCancelar = document.getElementById('alert-cancel');
    
    // Remover event listeners anteriores
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
    console.log('🔗 API Request:', url, options.method || 'GET');
    
    try {
        const config = {
            headers: {
                'Content-Type': 'application/json',
            },
            ...options
        };

        if (config.body) {
            config.body = JSON.stringify(config.body);
        }

        const response = await fetch(url, config);
        console.log('📥 API Response:', response.status);
        
        if (!response.ok) {
            let errorMessage = `Error ${response.status}: ${response.statusText}`;
            
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorData.message || errorMessage;
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
        estado.horarios = Array.isArray(horarios) ? horarios : [];
        console.log('📋 Horarios cargados:', estado.horarios.length);
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
        estado.cursos = data.data || [];
        console.log('📚 Cursos cargados:', estado.cursos.length);
    } catch (error) {
        console.error('Error cargando cursos:', error);
        estado.cursos = [];
    }
}

async function cargarHorario(id) {
    if (!id || isNaN(id)) {
        mostrarNotificacion('ID de horario inválido', 'error');
        return;
    }

    mostrarLoading('Cargando horario...');
    
    try {
        const horarioData = await apiRequest(`${API_URLS.obtenerHorario}/${id}`);
        console.log('📋 Datos del horario recibidos:', horarioData);

        // Validar datos críticos
        if (!horarioData || typeof horarioData !== 'object') {
            throw new Error('Datos de horario inválidos');
        }

        // Reiniciar estado
        estado.bloques = [];
        estado.diasActivos.clear();

        // Procesar días
        if (horarioData.dias && Array.isArray(horarioData.dias)) {
            horarioData.dias.forEach(dia => estado.diasActivos.add(dia));
        }

        // Procesar bloques
        if (horarioData.bloques && Array.isArray(horarioData.bloques)) {
            estado.bloques = horarioData.bloques.map(bloque => ({
                id: bloque.id || Date.now() + Math.random(),
                day: bloque.dia_semana || bloque.day || 'Lunes',
                type: bloque.tipo || bloque.type || 'class',
                start: bloque.horaInicio || bloque.start || '07:00',
                end: bloque.horaFin || bloque.end || '07:45',
                nombre: bloque.nombre || 'Bloque',
                classType: bloque.class_type || bloque.classType,
                breakType: bloque.break_type || bloque.breakType
            })).filter(bloque => bloque.day && bloque.start && bloque.end);
        }

        estado.horarioCargadoId = id;

        // Actualizar interfaz
        if (horarioData.nombre) {
            const nombreParts = horarioData.nombre.split(' - ');
            document.getElementById('schedule-name').value = nombreParts[0] || horarioData.nombre;
            if (nombreParts.length > 1) {
                document.getElementById('schedule-period').value = nombreParts[1];
            }
        }

        actualizarUI();
        document.getElementById('delete-schedule-btn').style.display = 'block';
        
        mostrarNotificacion('Horario cargado correctamente', 'success');

    } catch (error) {
        console.error('❌ Error cargando horario:', error);
        mostrarNotificacion('Error al cargar horario: ' + error.message, 'error');
        
        // Estado limpio en caso de error
        estado.horarioCargadoId = null;
        estado.bloques = [];
        actualizarUI();
    } finally {
        ocultarLoading();
    }
}

async function guardarHorarioBD() {
    const nombre = document.getElementById('schedule-name').value.trim();
    const periodo = document.getElementById('schedule-period').value;

    // Validaciones
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

    // Preparar datos
    const datosHorario = {
        nombre: nombre,
        periodo: periodo,
        dias: Array.from(estado.diasActivos),
        bloques: estado.bloques.map((bloque, index) => ({
            dia_semana: bloque.day,
            horaInicio: bloque.start,
            horaFin: bloque.end,
            tipo: bloque.type,
            nombre: bloque.nombre,
            orden: index,
            class_type: bloque.classType,
            break_type: bloque.breakType
        })),
        horaInicio: calcularHoraInicio(),
        horaFin: calcularHoraFin(),
        duracion_clase: 45,
        duracion_descanso: 15
    };

    console.log('💾 Enviando datos:', datosHorario);
    mostrarLoading('Guardando horario...');

    try {
        const resultado = await apiRequest(API_URLS.crearHorario, {
            method: 'POST',
            body: datosHorario
        });

        if (resultado.success) {
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
    try {
        const resultado = await apiRequest(`${API_URLS.eliminarHorario}/${id}`, {
            method: 'DELETE'
        });

        if (resultado.success) {
            mostrarNotificacion('Horario eliminado correctamente', 'success');
            if (estado.horarioCargadoId === id) {
                nuevoHorario();
            }
            await cargarHorariosGuardados();
        }
    } catch (error) {
        mostrarNotificacion('Error al eliminar el horario: ' + error.message, 'error');
    }
}

async function asignarHorarioCursos(horarioId, cursosIds) {
    mostrarLoading('Asignando horario...');
    
    try {
        const resultado = await apiRequest(API_URLS.asignarHorario, {
            method: 'POST',
            body: {
                horario_id: horarioId,
                cursos_ids: cursosIds
            }
        });

        if (resultado.success) {
            mostrarNotificacion('Horario asignado correctamente', 'success');
            return true;
        } else {
            throw new Error(resultado.error || 'Error al asignar');
        }
    } catch (error) {
        mostrarNotificacion('Error al asignar: ' + error.message, 'error');
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

    // Ordenar bloques por hora de inicio
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

    // Crear intervalos de tiempo
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

    if (!estado.horarios || estado.horarios.length === 0) {
        contenedor.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">No hay horarios guardados</p>';
        select.innerHTML = '<option value="">No hay horarios disponibles</option>';
        return;
    }

    contenedor.innerHTML = estado.horarios.map(horario => {
        const esActivo = estado.horarioCargadoId === horario.id;
        const nombreSeguro = (horario.nombre || 'Sin nombre').replace(/'/g, "&#39;");
        
        return `
            <div class="schedule-item ${esActivo ? 'active' : ''}" 
                 onclick="cargarHorario(${horario.id})">
                <div class="schedule-item-info">
                    <div class="schedule-item-name">${horario.nombre || 'Sin nombre'}</div>
                    <div class="schedule-item-details">
                        ${horario.horaInicio || '07:00'} - ${horario.horaFin || '17:00'} | 
                        ${horario.totalCursos || 0} cursos
                    </div>
                </div>
                <div class="schedule-item-actions">
                    <button class="small danger" onclick="event.stopPropagation(); configurarEliminacionHorario(${horario.id}, '${nombreSeguro}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }).join('');

    select.innerHTML = estado.horarios.map(horario => 
        `<option value="${horario.id}">${horario.nombre || 'Horario sin nombre'}</option>`
    ).join('');
}

// =============================================
// GESTIÓN DE BLOQUES
// =============================================

function agregarBloque() {
    const dia = document.getElementById('block-day').value;
    const tipo = document.getElementById('block-type').value;
    const inicio = document.getElementById('block-start').value;
    const fin = document.getElementById('block-end').value;

    // Validaciones
    if (!estado.diasActivos.has(dia)) {
        mostrarNotificacion(`El día ${dia} no está activo. Active el día primero.`, 'error');
        return;
    }

    if (inicio >= fin) {
        mostrarNotificacion('La hora de fin debe ser posterior a la de inicio', 'error');
        return;
    }

    if (haySuperposicion(dia, inicio, fin, estado.editandoBloqueId)) {
        mostrarNotificacion('El bloque se superpone con uno existente en el mismo día', 'error');
        return;
    }

    // Generar nombre del bloque
    let nombre = generarNombreBloque(tipo);

    const nuevoBloque = {
        id: estado.editandoBloqueId || generarIdUnico(),
        day: dia,
        type: tipo,
        start: inicio,
        end: fin,
        nombre: nombre,
        classType: tipo === 'class' ? document.getElementById('class-type').value : null,
        breakType: tipo === 'break' ? document.getElementById('break-type').value : null
    };

    if (estado.editandoBloqueId) {
        // Editar bloque existente
        const index = estado.bloques.findIndex(b => b.id === estado.editandoBloqueId);
        if (index !== -1) {
            estado.bloques[index] = nuevoBloque;
            mostrarNotificacion('Bloque actualizado correctamente', 'success');
        }
    } else {
        // Agregar nuevo bloque
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
    
    // Llenar formulario con datos del bloque
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
    
    // Mostrar formulario
    document.getElementById('floating-block-form').style.display = 'block';
    
    // Scroll al formulario
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
    mostrarAlerta(
        'Eliminar Horario',
        `¿Está seguro de eliminar el horario "${nombre}"? Esta acción no se puede deshacer.`,
        'error',
        () => eliminarHorario(id)
    );
}

// =============================================
// FUNCIONES DE UTILIDAD
// =============================================

function timeToMinutes(timeStr) {
    if (!timeStr) return 0;
    const [hours, minutes] = timeStr.split(':').map(Number);
    return hours * 60 + minutes;
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
    if (estado.bloques.length === 0) return '07:00';
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
            custom: 'Descanso Personalizado'
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
        
        // Solo crear intervalos de al menos 15 minutos
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
    document.getElementById('block-start').value = '07:00';
    document.getElementById('block-end').value = '07:45';
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

    const cursosLista = document.getElementById('courses-list');
    cursosLista.innerHTML = estado.cursos.map(curso => `
        <div class="course-item">
            <input type="checkbox" class="course-checkbox" value="${curso.id}" 
                   id="curso-${curso.id}">
            <label for="curso-${curso.id}" class="course-info">
                <div class="course-name">${curso.nombreCurso || 'Curso sin nombre'}</div>
                <div class="course-details">Sede: ${curso.sede || 'Sin sede'}</div>
            </label>
            <div class="course-schedule ${curso.horario_general_id ? 'has-schedule' : 'no-schedule'}">
                ${curso.horario_general_id ? '✓ Con horario' : '✗ Sin horario'}
            </div>
        </div>
    `).join('');

    document.getElementById('assign-schedule-modal').style.display = 'flex';
}

async function confirmarAsignacion() {
    const horarioId = parseInt(document.getElementById('schedule-select').value);
    const cursosSeleccionados = Array.from(document.querySelectorAll('.course-checkbox:checked'))
        .map(cb => parseInt(cb.value));

    if (!horarioId) {
        mostrarNotificacion('Seleccione un horario de la lista', 'error');
        return;
    }

    if (cursosSeleccionados.length === 0) {
        mostrarNotificacion('Seleccione al menos un curso', 'error');
        return;
    }

    const exito = await asignarHorarioCursos(horarioId, cursosSeleccionados);
    if (exito) {
        document.getElementById('assign-schedule-modal').style.display = 'none';
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
                // Eliminar bloques del día deseleccionado
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

    // Botones principales
    document.getElementById('new-schedule-btn').addEventListener('click', nuevoHorario);
    document.getElementById('save-schedule-btn').addEventListener('click', async () => {
        const horarioGuardado = await guardarHorarioBD();
        if (horarioGuardado) {
            estado.horarioCargadoId = horarioGuardado.id;
            document.getElementById('delete-schedule-btn').style.display = 'block';
        }
    });

    document.getElementById('assign-schedule-btn').addEventListener('click', mostrarModalAsignacion);
    
    document.getElementById('delete-schedule-btn').addEventListener('click', function() {
        if (estado.horarioCargadoId) {
            const horarioActual = estado.horarios.find(h => h.id === estado.horarioCargadoId);
            const nombre = horarioActual ? horarioActual.nombre : 'este horario';
            configurarEliminacionHorario(estado.horarioCargadoId, nombre);
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
        
        // Cargar datos en paralelo
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