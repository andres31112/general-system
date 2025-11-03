// SISTEMA DE ADMINISTRACIÓN DE VOTACIÓN - VERSIÓN COMPLETA CORREGIDA

// Configuración
const API_URLS = {
    horarios: '/admin/ultimo-horario',
    guardarHorario: '/admin/guardar-horario',
    candidatos: '/admin/listar-candidatos',
    crearCandidato: '/admin/crear-candidato',
    editarCandidato: '/admin/candidatos/',
    eliminarCandidato: '/admin/candidatos/',
    publicarResultados: '/admin/publicar-resultados',
    ocultarResultados: '/admin/ocultar-resultados',
    estadoPublicacion: '/admin/estado-publicacion'
};

// Estado de la aplicación
let estado = {
    candidatos: [],
    horarioActual: null,
    resultadosPublicados: false
};

// Elementos DOM
let elementos = {};

// FUNCIONES DE UTILIDAD - VERSIÓN CORREGIDA CON NOTIFICACIONES PUSH
function mostrarNotificacion(mensaje, tipo = 'success', titulo = null) {
    // Crear elemento de notificación push
    const notificacion = document.createElement('div');
    notificacion.className = `notificacion-push ${tipo}`;
    
    // Icono según el tipo
    let icono = 'check';
    if (tipo === 'error') icono = 'exclamation-triangle';
    if (tipo === 'warning') icono = 'exclamation-circle';
    if (tipo === 'info') icono = 'info-circle';
    
    // Título por defecto según el tipo
    if (!titulo) {
        switch(tipo) {
            case 'success': titulo = 'Éxito'; break;
            case 'error': titulo = 'Error'; break;
            case 'warning': titulo = 'Advertencia'; break;
            case 'info': titulo = 'Información'; break;
            default: titulo = 'Notificación';
        }
    }
    
    notificacion.innerHTML = `
        <i class="fas fa-${icono}"></i>
        <div class="contenido">
            <div class="titulo">${titulo}</div>
            <div class="mensaje">${mensaje}</div>
        </div>
        <button class="btn-cerrar" onclick="cerrarNotificacion(this)">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    // Agregar al contenedor de notificaciones push
    const contenedor = document.getElementById('notificaciones-push');
    if (contenedor) {
        contenedor.appendChild(notificacion);
        
        // Iniciar animación de entrada
        setTimeout(() => {
            notificacion.style.transform = 'translateX(0)';
            notificacion.style.opacity = '1';
        }, 10);
        
        // Auto-eliminar después de 8 segundos (tiempo suficiente para leer)
        const timeoutId = setTimeout(() => {
            cerrarNotificacionSuavemente(notificacion);
        }, 8000);
        
        // Guardar el timeout ID para poder cancelarlo si el usuario cierra manualmente
        notificacion.dataset.timeoutId = timeoutId;
        
    } else {
        // Fallback: usar alerta normal
        const notification = document.createElement('div');
        notification.className = `alert alert-${tipo} alert-dismissible fade show`;
        notification.innerHTML = `
            <i class="fas fa-${tipo === 'success' ? 'check' : 'exclamation-triangle'} me-2"></i>
            ${mensaje}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Insertar después del header
        const header = document.querySelector('.admin-header');
        if (header && header.parentNode) {
            header.parentNode.insertBefore(notification, header.nextSibling);
        }
        
        // Auto-eliminar después de 8 segundos
        setTimeout(() => {
            if (notification.parentNode) {
                const bsAlert = new bootstrap.Alert(notification);
                bsAlert.close();
            }
        }, 8000);
    }
}

// Función para cerrar notificación manualmente
function cerrarNotificacion(boton) {
    const notificacion = boton.closest('.notificacion-push');
    cerrarNotificacionSuavemente(notificacion);
}

// Función para cerrar notificación con animación suave
function cerrarNotificacionSuavemente(notificacion) {
    if (!notificacion) return;
    
    // Cancelar el timeout si existe
    if (notificacion.dataset.timeoutId) {
        clearTimeout(parseInt(notificacion.dataset.timeoutId));
    }
    
    // Animación de salida
    notificacion.style.transform = 'translateX(400px)';
    notificacion.style.opacity = '0';
    
    // Eliminar del DOM después de la animación
    setTimeout(() => {
        if (notificacion.parentNode) {
            notificacion.remove();
        }
    }, 500);
}

// Función para mantener la notificación al hacer hover
function configurarHoverNotificaciones() {
    document.addEventListener('mouseover', function(e) {
        const notificacion = e.target.closest('.notificacion-push');
        if (notificacion && notificacion.dataset.timeoutId) {
            // Pausar el timeout cuando el mouse está sobre la notificación
            clearTimeout(parseInt(notificacion.dataset.timeoutId));
            notificacion.dataset.timeoutId = '';
        }
    });
    
    document.addEventListener('mouseout', function(e) {
        const notificacion = e.target.closest('.notificacion-push');
        if (notificacion && !notificacion.dataset.timeoutId) {
            // Reanudar el timeout cuando el mouse sale de la notificación
            const timeoutId = setTimeout(() => {
                cerrarNotificacionSuavemente(notificacion);
            }, 3000); // 3 segundos adicionales después de que el mouse sale
            notificacion.dataset.timeoutId = timeoutId;
        }
    });
}
async function apiRequest(url, options = {}) {
    try {
        console.log(`🔄 Haciendo petición a: ${url}`);
        const response = await fetch(url, options);
        
        if (!response.ok) {
            throw new Error(`Error ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log(`✅ Respuesta de ${url}:`, data);
        return data;
        
    } catch (error) {
        console.error(`❌ Error en petición a ${url}:`, error);
        throw error;
    }
}

// GESTIÓN DE HORARIOS
async function cargarHorarioActual() {
    try {
        const data = await apiRequest(API_URLS.horarios);
        if (data.inicio && data.fin) {
            document.getElementById("inicio").value = data.inicio;
            document.getElementById("fin").value = data.fin;
            elementos.horarioActual.innerHTML = `<strong>Horario actual:</strong> ${data.inicio} - ${data.fin}`;
            estado.horarioActual = data;
        }
    } catch (error) {
        console.error('Error cargando horario:', error);
    }
}

// GESTIÓN DE CANDIDATOS - VERSIÓN CON DEBUG
async function cargarCandidatos() {
    try {
        console.log('🔄 Cargando candidatos...');
        const data = await apiRequest(API_URLS.candidatos);
        
        if (!Array.isArray(data)) {
            throw new Error('Formato de datos inválido');
        }
        
        // 🔥 DEBUG: Mostrar votos de cada candidato
        console.log('📊 DATOS DE CANDIDATOS RECIBIDOS:');
        data.forEach(candidato => {
            console.log(`   ${candidato.nombre}: ${candidato.votos} votos (Categoría: ${candidato.categoria})`);
        });
        
        estado.candidatos = data.map(candidato => {
            return {
                id: candidato.id || candidato.id_candidato,
                nombre: candidato.nombre || 'Sin nombre',
                tarjeton: candidato.tarjeton || 'Sin tarjetón',
                propuesta: candidato.propuesta || 'Sin propuesta',
                categoria: candidato.categoria || 'Sin categoría',
                foto: candidato.foto || null,
                votos: candidato.votos || 0
            };
        });
        
        console.log(`✅ Cargados ${estado.candidatos.length} candidatos`);
        actualizarListaCandidatos();
        actualizarResultados();
        
    } catch (error) {
        console.error('❌ Error cargando candidatos:', error);
        estado.candidatos = [];
        actualizarListaCandidatos();
        mostrarNotificacion('Error al cargar los candidatos: ' + error.message, 'error');
    }
}

function actualizarListaCandidatos() {
    console.log('🔄 Actualizando lista de candidatos en el DOM...');
    
    if (!estado.candidatos || estado.candidatos.length === 0) {
        elementos.listaCandidatos.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-users fa-3x mb-3"></i>
                <p>No hay candidatos registrados.</p>
                <button class="btn btn-primary mt-2" onclick="cargarCandidatos()">
                    <i class="fas fa-sync-alt"></i> Reintentar
                </button>
            </div>
        `;
        elementos.candidatesCount.textContent = '(0)';
        return;
    }

    elementos.candidatesCount.textContent = `(${estado.candidatos.length})`;
    
    const candidatosHTML = estado.candidatos.map(candidato => {
        if (!candidato.id) {
            console.error('Candidato sin ID:', candidato);
            return '';
        }
        
        return `
        <div class="candidate-card" data-id="${candidato.id}">
            <div class="candidate-info">
                <h3>${candidato.nombre}</h3>
                <div class="candidate-meta">
                    <p><strong><i class="fas fa-tag"></i> Categoría:</strong> 
                       <span class="badge bg-primary">${candidato.categoria}</span>
                    </p>
                    <p><strong><i class="fas fa-hashtag"></i> Tarjetón:</strong> 
                       <span class="badge bg-secondary">${candidato.tarjeton}</span>
                    </p>
                    <p><strong><i class="fas fa-bullhorn"></i> Propuesta:</strong> ${candidato.propuesta}</p>
                    <p><strong><i class="fas fa-chart-bar"></i> Votos:</strong> 
                       <span class="badge bg-success">${candidato.votos}</span>
                    </p>
                </div>
                ${candidato.foto ? `
                    <div class="candidate-photo">
                        <img src="/static/images/candidatos/${candidato.foto}" 
                             alt="${candidato.nombre}" 
                             onerror="this.src='/static/images/candidatos/default.png'">
                    </div>
                ` : ''}
            </div>
            <div class="candidate-actions">
                <button class="btn btn-warning btn-sm btn-editar" data-id="${candidato.id}">
                    <i class="fas fa-edit"></i> Editar
                </button>
                <button class="btn btn-danger btn-sm btn-eliminar" data-id="${candidato.id}">
                    <i class="fas fa-trash"></i> Eliminar
                </button>
            </div>
        </div>
        `;
    }).join('');

    elementos.listaCandidatos.innerHTML = candidatosHTML;
    console.log('✅ Lista de candidatos actualizada en el DOM');
}

// ACTUALIZACIÓN DE RESULTADOS - VERSIÓN CON DEBUG DETALLADO
function actualizarResultados() {
    console.log('🔄 Actualizando resultados...');
    console.log('📊 Candidatos para resultados:', estado.candidatos);
    
    if (!estado.candidatos || estado.candidatos.length === 0) {
        elementos.resultados.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-chart-bar fa-3x mb-3"></i>
                <p>No hay candidatos registrados para mostrar resultados.</p>
            </div>
        `;
        return;
    }

    // Agrupar por categoría
    const categorias = {};
    estado.candidatos.forEach(candidato => {
        if (!categorias[candidato.categoria]) {
            categorias[candidato.categoria] = [];
        }
        categorias[candidato.categoria].push(candidato);
    });

    console.log('📋 Categorías encontradas:', Object.keys(categorias));

    let resultadosHTML = '';
    let hayResultados = false;

    Object.keys(categorias).forEach(categoria => {
        const candidatosCategoria = categorias[categoria];
        
        console.log(`📊 Procesando categoría: ${categoria}`);
        console.log(`   Candidatos en ${categoria}:`, candidatosCategoria.map(c => `${c.nombre}: ${c.votos} votos`));
        
        // Ordenar por votos descendente
        candidatosCategoria.sort((a, b) => (b.votos || 0) - (a.votos || 0));
        const maxVotos = Math.max(...candidatosCategoria.map(c => c.votos || 0));
        
        console.log(`   Máximo de votos en ${categoria}: ${maxVotos}`);
        
        // Contar cuántos candidatos tienen el máximo de votos
        const ganadores = candidatosCategoria.filter(c => c.votos === maxVotos && maxVotos > 0);
        const esEmpate = ganadores.length > 1;
        
        console.log(`   Ganadores en ${categoria}:`, ganadores.map(g => g.nombre));
        console.log(`   ¿Es empate?: ${esEmpate}`);

        const totalVotosCategoria = candidatosCategoria.reduce((sum, c) => sum + (c.votos || 0), 0);
        
        if (totalVotosCategoria > 0) {
            hayResultados = true;
        }

        resultadosHTML += `
            <div class="result-category">
                <h4 class="category-title">
                    <i class="fas fa-${getIconoCategoria(categoria)}"></i>
                    ${categoria.charAt(0).toUpperCase() + categoria.slice(1)}
                    <span class="total-votes">(${totalVotosCategoria} votos totales)</span>
                </h4>
                <div class="results-list">
                    ${candidatosCategoria.map(candidato => {
                        const esGanador = candidato.votos === maxVotos && maxVotos > 0;
                        const porcentaje = totalVotosCategoria > 0 ? 
                            Math.round((candidato.votos / totalVotosCategoria) * 100) : 0;
                        
                        console.log(`   ${candidato.nombre}: ${candidato.votos} votos, ¿Es ganador?: ${esGanador}`);
                        
                        let badgeGanador = '';
                        if (esGanador) {
                            if (esEmpate) {
                                badgeGanador = '<span class="winner-badge empate"><i class="fas fa-handshake"></i> Empate</span>';
                            } else {
                                badgeGanador = '<span class="winner-badge"><i class="fas fa-trophy"></i> Ganador</span>';
                            }
                        }
                        
                        return `
                            <div class="result-item ${esGanador ? 'winner' : ''} ${esEmpate && esGanador ? 'empate' : ''}">
                                <div class="candidate-info">
                                    <strong>${candidato.nombre}</strong>
                                    <div class="candidate-details">
                                        <span class="tarjeton">Tarjetón: ${candidato.tarjeton}</span>
                                        <span class="votes">${candidato.votos || 0} votos (${porcentaje}%)</span>
                                    </div>
                                </div>
                                ${badgeGanador}
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    });

    if (!hayResultados) {
        resultadosHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-chart-bar fa-3x mb-3"></i>
                <p>No hay votos registrados todavía.</p>
                <small>Los resultados aparecerán aquí cuando los estudiantes comiencen a votar.</small>
            </div>
        `;
    }

    elementos.resultados.innerHTML = resultadosHTML;
    console.log('✅ Resultados actualizados');
}

function getIconoCategoria(categoria) {
    const iconos = {
        'personero': 'user-tie',
        'contralor': 'chart-line',
        'cabildante': 'users'
    };
    return iconos[categoria] || 'user';
}

// GESTIÓN DE FORMULARIOS
async function enviarFormCandidato(form, esEdicion = false) {
    const formData = new FormData(form);
    const id = esEdicion ? document.getElementById('edit-id').value : null;

    try {
        const url = esEdicion ? `${API_URLS.editarCandidato}${id}` : API_URLS.crearCandidato;
        
        console.log(`🔄 Enviando formulario a: ${url}`);
        const response = await fetch(url, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!data.ok) {
            throw new Error(data.error || 'Error al procesar la solicitud');
        }

        mostrarNotificacion(
            esEdicion ? 'Candidato actualizado correctamente' : 'Candidato agregado correctamente',
            'success'
        );

        await cargarCandidatos();
        form.reset();
        
        if (esEdicion) {
            elementos.modalEditar.hide();
        } else {
            if (elementos.fotoPreview) {
                elementos.fotoPreview.style.display = 'none';
            }
        }

    } catch (error) {
        console.error('Error en formulario:', error);
        mostrarNotificacion(error.message, 'error');
    }
}

// FUNCIONES PARA EDITAR Y ELIMINAR
function editarCandidato(id) {
    console.log('✏️ Editando candidato ID:', id);
    
    const candidato = estado.candidatos.find(c => c.id == id);
    
    if (!candidato) {
        mostrarNotificacion('Error: Candidato no encontrado', 'error');
        return;
    }

    document.getElementById('edit-id').value = candidato.id;
    document.getElementById('edit-nombre').value = candidato.nombre;
    document.getElementById('edit-tarjeton').value = candidato.tarjeton;
    document.getElementById('edit-propuesta').value = candidato.propuesta;
    document.getElementById('edit-categoria').value = candidato.categoria;
    
    if (elementos.fotoPreviewEditar) {
        elementos.fotoPreviewEditar.style.display = 'none';
    }
    
    const editFotoInput = document.getElementById('edit-foto');
    if (editFotoInput) {
        editFotoInput.value = '';
    }

    if (elementos.modalEditar) {
        elementos.modalEditar.show();
    }
}

async function eliminarCandidato(id) {
    if (!confirm('¿Está seguro de eliminar este candidato? Esta acción no se puede deshacer.')) {
        return;
    }

    try {
        console.log(`🗑️ Eliminando candidato ID: ${id}`);
        const response = await fetch(`${API_URLS.eliminarCandidato}${id}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.ok) {
            mostrarNotificacion('Candidato eliminado correctamente', 'success');
            await cargarCandidatos();
        } else {
            throw new Error(data.error || 'Error al eliminar el candidato');
        }
    } catch (error) {
        mostrarNotificacion(error.message, 'error');
    }
}

// GESTIÓN DE PUBLICACIÓN DE RESULTADOS
async function publicarResultados() {
    const btnPublicar = document.getElementById('btn-publicar-resultados');
    
    if (!confirm('¿Está seguro de publicar los resultados? Esta acción hará los resultados visibles para todos los usuarios en la página principal.')) {
        return;
    }

    try {
        btnPublicar.disabled = true;
        btnPublicar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Publicando...';
        
        console.log('📢 Publicando resultados...');
        const data = await apiRequest(API_URLS.publicarResultados, {
            method: 'POST'
        });

        if (data.success) {
            mostrarNotificacion(data.message || '✅ Resultados publicados correctamente', 'success');
            
            btnPublicar.innerHTML = '<i class="fas fa-eye"></i> Resultados Publicados';
            btnPublicar.classList.remove('btn-success');
            btnPublicar.classList.add('btn-secondary');
            btnPublicar.onclick = null;
            
            agregarBotonOcultar();
            
            estado.resultadosPublicados = true;
            
        } else {
            throw new Error(data.error || 'Error al publicar resultados');
        }
        
    } catch (error) {
        console.error('❌ Error publicando resultados:', error);
        mostrarNotificacion(error.message, 'error');
        
        btnPublicar.disabled = false;
        btnPublicar.innerHTML = '<i class="fas fa-bullhorn"></i> Publicar';
        
    } finally {
        setTimeout(() => {
            if (btnPublicar.disabled && btnPublicar.innerHTML.includes('Publicando')) {
                btnPublicar.disabled = false;
                btnPublicar.innerHTML = '<i class="fas fa-bullhorn"></i> Publicar';
            }
        }, 3000);
    }
}

async function ocultarResultados() {
    if (!confirm('¿Está seguro de ocultar los resultados? Los usuarios ya no podrán verlos en la página principal.')) {
        return;
    }

    try {
        const btnOcultar = document.getElementById('btn-ocultar-resultados');
        if (btnOcultar) {
            btnOcultar.disabled = true;
            btnOcultar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Ocultando...';
        }

        const response = await fetch(API_URLS.ocultarResultados, {
            method: 'POST'
        });
        
        const data = await response.json();

        if (data.success) {
            mostrarNotificacion(data.message || '✅ Resultados ocultados correctamente', 'success');
            
            const btnPublicar = document.getElementById('btn-publicar-resultados');
            btnPublicar.innerHTML = '<i class="fas fa-bullhorn"></i> Publicar';
            btnPublicar.classList.remove('btn-secondary');
            btnPublicar.classList.add('btn-success');
            btnPublicar.onclick = publicarResultados;
            btnPublicar.disabled = false;
            
            if (btnOcultar) {
                btnOcultar.remove();
            }
            
            estado.resultadosPublicados = false;
            
        } else {
            throw new Error(data.error || 'Error al ocultar resultados');
        }
    } catch (error) {
        console.error('❌ Error ocultando resultados:', error);
        mostrarNotificacion(error.message, 'error');
        
        const btnOcultar = document.getElementById('btn-ocultar-resultados');
        if (btnOcultar) {
            btnOcultar.disabled = false;
            btnOcultar.innerHTML = '<i class="fas fa-eye-slash"></i> Ocultar Resultados';
        }
    }
}

function agregarBotonOcultar() {
    const resultsActions = document.querySelector('.results-actions');
    
    if (!document.getElementById('btn-ocultar-resultados')) {
        const btnOcultar = document.createElement('button');
        btnOcultar.id = 'btn-ocultar-resultados';
        btnOcultar.className = 'btn btn-warning';
        btnOcultar.innerHTML = '<i class="fas fa-eye-slash"></i> Ocultar Resultados';
        btnOcultar.onclick = ocultarResultados;
        
        resultsActions.appendChild(btnOcultar);
    }
}

async function verificarEstadoPublicacion() {
    try {
        const data = await apiRequest(API_URLS.estadoPublicacion);
        
        if (data.success && data.estado.resultados_publicados) {
            const btnPublicar = document.getElementById('btn-publicar-resultados');
            if (btnPublicar) {
                btnPublicar.innerHTML = '<i class="fas fa-eye"></i> Resultados Publicados';
                btnPublicar.classList.remove('btn-success');
                btnPublicar.classList.add('btn-secondary');
                btnPublicar.onclick = null;
                btnPublicar.disabled = true;
                
                agregarBotonOcultar();
                
                estado.resultadosPublicados = true;
            }
        } else {
            const btnPublicar = document.getElementById('btn-publicar-resultados');
            if (btnPublicar) {
                btnPublicar.innerHTML = '<i class="fas fa-bullhorn"></i> Publicar';
                btnPublicar.classList.remove('btn-secondary');
                btnPublicar.classList.add('btn-success');
                btnPublicar.onclick = publicarResultados;
                btnPublicar.disabled = false;
                
                const btnOcultar = document.getElementById('btn-ocultar-resultados');
                if (btnOcultar) {
                    btnOcultar.remove();
                }
                
                estado.resultadosPublicados = false;
            }
        }
    } catch (error) {
        console.error('Error verificando estado de publicación:', error);
    }
}

// EVENTOS Y CONFIGURACIÓN
function configurarEventos() {
    console.log('🔄 Configurando eventos...');
    
    elementos = {
        formHorario: document.getElementById("form-horario"),
        formCandidato: document.getElementById("form-candidato"),
        formEditar: document.getElementById("form-editar"),
        listaCandidatos: document.getElementById("lista-candidatos"),
        resultados: document.getElementById("resultados"),
        horarioActual: document.getElementById("horario-actual"),
        fotoPreview: document.getElementById("foto-preview"),
        fotoPreviewEditar: document.getElementById("foto-preview-editar"),
        candidatesCount: document.getElementById("candidates-count"),
        modalEditar: new bootstrap.Modal(document.getElementById("modalEditar"))
    };

    console.log('Elementos DOM encontrados:', elementos);

    if (elementos.formHorario) {
        elementos.formHorario.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            try {
                const formData = new FormData(elementos.formHorario);
                
                const response = await fetch(API_URLS.guardarHorario, {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    window.location.reload();
                } else {
                    throw new Error('Error al guardar el horario');
                }
            } catch (error) {
                mostrarNotificacion(error.message, 'error');
            }
        });
    }

    if (elementos.formCandidato) {
        elementos.formCandidato.addEventListener('submit', (e) => {
            e.preventDefault();
            enviarFormCandidato(elementos.formCandidato, false);
        });
    }

    if (elementos.formEditar) {
        elementos.formEditar.addEventListener('submit', (e) => {
            e.preventDefault();
            enviarFormCandidato(elementos.formEditar, true);
        });
    }

    const fotoInput = document.getElementById('foto');
    if (fotoInput && elementos.fotoPreview) {
        fotoInput.addEventListener('change', function(e) {
            mostrarPreviewImagen(e.target, elementos.fotoPreview);
        });
    }

    const editFotoInput = document.getElementById('edit-foto');
    if (editFotoInput && elementos.fotoPreviewEditar) {
        editFotoInput.addEventListener('change', function(e) {
            mostrarPreviewImagen(e.target, elementos.fotoPreviewEditar);
        });
    }

    if (elementos.listaCandidatos) {
        elementos.listaCandidatos.addEventListener('click', (e) => {
            const botonEditar = e.target.closest('.btn-editar');
            const botonEliminar = e.target.closest('.btn-eliminar');

            if (botonEditar) {
                const id = botonEditar.getAttribute('data-id');
                if (id) {
                    editarCandidato(id);
                }
            }

            if (botonEliminar) {
                const id = botonEliminar.getAttribute('data-id');
                if (id) {
                    eliminarCandidato(id);
                }
            }
        });
    }

    const btnDashboard = document.getElementById('btn-dashboard');
    if (btnDashboard) {
        btnDashboard.addEventListener('click', () => {
            window.location.href = btnDashboard.dataset.url;
        });
    }

    const btnVerResultados = document.getElementById('btn-ver-resultados');
    if (btnVerResultados) {
        btnVerResultados.addEventListener('click', () => {
            cargarCandidatos();
            mostrarNotificacion('Resultados actualizados', 'info');
        });
    }

    const btnPublicarResultados = document.getElementById('btn-publicar-resultados');
    if (btnPublicarResultados) {
        btnPublicarResultados.addEventListener('click', publicarResultados);
    }
}

function mostrarPreviewImagen(input, previewElement) {
    const file = input.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            previewElement.querySelector('img').src = e.target.result;
            previewElement.style.display = 'block';
        };
        reader.readAsDataURL(file);
    } else {
        previewElement.style.display = 'none';
    }
}

// INICIALIZACIÓN
async function inicializar() {
    console.log('🚀 Inicializando sistema de administración...');
    
    try {
        configurarEventos();
        configurarHoverNotificaciones(); 
        await cargarHorarioActual();
        await cargarCandidatos();
        await verificarEstadoPublicacion();
        
        console.log('✅ Sistema inicializado correctamente');
        
        setInterval(() => {
            cargarCandidatos();
        }, 30000);
        
    } catch (error) {
        console.error('❌ Error en inicialización:', error);
        mostrarNotificacion('Error al inicializar el sistema: ' + error.message, 'error');
    }
}

// Iniciar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', inicializar);

// Utilidades globales
window.cargarCandidatos = cargarCandidatos;
window.editarCandidato = editarCandidato;
window.eliminarCandidato = eliminarCandidato;
window.publicarResultados = publicarResultados;
window.ocultarResultados = ocultarResultados;