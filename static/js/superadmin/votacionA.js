// SISTEMA DE ADMINISTRACIÓN DE VOTACIÓN - VERSIÓN CORREGIDA

// Configuración
const API_URLS = {
    horarios: '/admin/ultimo-horario',
    guardarHorario: '/admin/guardar-horario',
    candidatos: '/admin/listar-candidatos',
    crearCandidato: '/admin/crear-candidato',
    editarCandidato: '/admin/candidatos/',
    eliminarCandidato: '/admin/candidatos/',
    publicarResultados: '/admin/publicar-resultados'
};

// Estado de la aplicación
let estado = {
    candidatos: [],
    horarioActual: null
};

// Elementos DOM
let elementos = {};

// FUNCIONES DE UTILIDAD
function mostrarNotificacion(mensaje, tipo = 'success') {
    // Eliminar notificaciones existentes
    document.querySelectorAll('.alert').forEach(alert => {
        if (alert.parentNode) alert.remove();
    });
    
    const notification = document.createElement('div');
    notification.className = `alert alert-${tipo} alert-dismissible fade show`;
    notification.innerHTML = `
        <i class="fas fa-${tipo === 'success' ? 'check' : 'exclamation-triangle'} me-2"></i>
        ${mensaje}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const header = document.querySelector('.admin-header');
    header.parentNode.insertBefore(notification, header.nextSibling);
    
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
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

// GESTIÓN DE CANDIDATOS - VERSIÓN MEJORADA
async function cargarCandidatos() {
    try {
        console.log('🔄 Cargando candidatos...');
        const data = await apiRequest(API_URLS.candidatos);
        
        // Validar que data sea un array
        if (!Array.isArray(data)) {
            throw new Error('Formato de datos inválido');
        }
        
        estado.candidatos = data.map(candidato => {
            // Asegurar que todos los campos tengan valores por defecto
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
        
        console.log(`✅ Cargados ${estado.candidatos.length} candidatos:`, estado.candidatos);
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
        // Validar que el candidato tenga ID
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

// ACTUALIZACIÓN DE RESULTADOS
function actualizarResultados() {
    console.log('🔄 Actualizando resultados...');
    
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

    let resultadosHTML = '';
    let hayResultados = false;

    Object.keys(categorias).forEach(categoria => {
        const candidatosCategoria = categorias[categoria];
        
        // Ordenar por votos descendente
        candidatosCategoria.sort((a, b) => (b.votos || 0) - (a.votos || 0));
        const maxVotos = Math.max(...candidatosCategoria.map(c => c.votos || 0));
        
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
                        const esGanador = (candidato.votos || 0) === maxVotos && maxVotos > 0;
                        const porcentaje = totalVotosCategoria > 0 ? 
                            Math.round((candidato.votos / totalVotosCategoria) * 100) : 0;
                        
                        return `
                            <div class="result-item ${esGanador ? 'winner' : ''}">
                                <div class="candidate-info">
                                    <strong>${candidato.nombre}</strong>
                                    <div class="candidate-details">
                                        <span class="tarjeton">Tarjetón: ${candidato.tarjeton}</span>
                                        <span class="votes">${candidato.votos || 0} votos (${porcentaje}%)</span>
                                    </div>
                                </div>
                                ${esGanador ? '<span class="winner-badge"><i class="fas fa-trophy"></i> Ganador</span>' : ''}
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
        console.log('Respuesta del servidor:', data);

        if (!data.ok) {
            throw new Error(data.error || 'Error al procesar la solicitud');
        }

        mostrarNotificacion(
            esEdicion ? 'Candidato actualizado correctamente' : 'Candidato agregado correctamente',
            'success'
        );

        // Recargar la lista de candidatos
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

    // Llenar el formulario de edición
    document.getElementById('edit-id').value = candidato.id;
    document.getElementById('edit-nombre').value = candidato.nombre;
    document.getElementById('edit-tarjeton').value = candidato.tarjeton;
    document.getElementById('edit-propuesta').value = candidato.propuesta;
    document.getElementById('edit-categoria').value = candidato.categoria;
    
    // Limpiar preview de nueva foto
    if (elementos.fotoPreviewEditar) {
        elementos.fotoPreviewEditar.style.display = 'none';
    }
    
    const editFotoInput = document.getElementById('edit-foto');
    if (editFotoInput) {
        editFotoInput.value = '';
    }

    // Mostrar el modal
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

// EVENTOS Y CONFIGURACIÓN
function configurarEventos() {
    console.log('🔄 Configurando eventos...');
    
    // Inicializar elementos DOM
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

    // Formulario de horario
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

    // Formulario de candidato
    if (elementos.formCandidato) {
        elementos.formCandidato.addEventListener('submit', (e) => {
            e.preventDefault();
            enviarFormCandidato(elementos.formCandidato, false);
        });
    }

    // Formulario de edición
    if (elementos.formEditar) {
        elementos.formEditar.addEventListener('submit', (e) => {
            e.preventDefault();
            enviarFormCandidato(elementos.formEditar, true);
        });
    }

    // Preview de imágenes
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

    // Eventos delegados para la lista de candidatos
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

    // Botones de control
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
        btnPublicarResultados.addEventListener('click', async () => {
            if (confirm('¿Está seguro de publicar los resultados? Esta acción no se puede deshacer.')) {
                try {
                    const response = await fetch(API_URLS.publicarResultados, {
                        method: 'POST'
                    });

                    const data = await response.json();

                    if (data.success) {
                        mostrarNotificacion('Resultados publicados correctamente', 'success');
                    } else {
                        throw new Error(data.error || 'Error al publicar resultados');
                    }
                } catch (error) {
                    mostrarNotificacion(error.message, 'error');
                }
            }
        });
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
        await cargarHorarioActual();
        await cargarCandidatos();
        
        console.log('✅ Sistema inicializado correctamente');
        
        // Actualizar automáticamente cada 30 segundos
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