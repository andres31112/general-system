// SISTEMA DE ADMINISTRACIÓN DE VOTACIÓN

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
    // Crear notificación temporal
    const notification = document.createElement('div');
    notification.className = `alert alert-${tipo} alert-dismissible fade show`;
    notification.innerHTML = `
        <i class="fas fa-${tipo === 'success' ? 'check' : 'exclamation-triangle'} me-2"></i>
        ${mensaje}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insertar después del header
    const header = document.querySelector('.admin-header');
    header.parentNode.insertBefore(notification, header.nextSibling);
    
    // Auto-eliminar después de 5 segundos
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

async function apiRequest(url, options = {}) {
    try {
        const config = {
            headers: {
                'Content-Type': 'application/json',
            },
            ...options
        };

        if (config.body && typeof config.body === 'object') {
            config.body = JSON.stringify(config.body);
        }

        const response = await fetch(url, config);
        
        if (!response.ok) {
            throw new Error(`Error ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Error en la petición:', error);
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

// GESTIÓN DE CANDIDATOS
async function cargarCandidatos() {
    try {
        const data = await apiRequest(API_URLS.candidatos);
        console.log('Datos de candidatos recibidos:', data);
        
        // Verificar la estructura de los datos
        estado.candidatos = Array.isArray(data) ? data : [];
        
        // Mapear los datos para asegurar que tengan id
        estado.candidatos = estado.candidatos.map(candidato => {
            // Si no tiene id, intentar usar id_candidato u otro campo
            const id = candidato.id || candidato.id_candidato || candidato.ID || Date.now() + Math.random();
            return {
                id: id,
                nombre: candidato.nombre,
                tarjeton: candidato.tarjeton,
                propuesta: candidato.propuesta,
                categoria: candidato.categoria,
                foto: candidato.foto,
                votos: candidato.votos || 0
            };
        });
        
        console.log('Candidatos procesados:', estado.candidatos);
        
        // Debug temporal - verificar la estructura completa de los datos
        if (estado.candidatos.length > 0) {
            console.log('Estructura completa del primer candidato:', estado.candidatos[0]);
            console.log('Todos los campos disponibles:', Object.keys(estado.candidatos[0]));
        }
        
        actualizarListaCandidatos();
        actualizarResultados();
    } catch (error) {
        console.error('Error cargando candidatos:', error);
        estado.candidatos = [];
        actualizarListaCandidatos();
    }
}

function actualizarListaCandidatos() {
    if (!estado.candidatos || estado.candidatos.length === 0) {
        elementos.listaCandidatos.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-users fa-3x mb-3"></i>
                <p>No hay candidatos registrados.</p>
            </div>
        `;
        elementos.candidatesCount.textContent = '(0)';
        return;
    }

    elementos.candidatesCount.textContent = `(${estado.candidatos.length})`;
    
    // Verificar que todos los candidatos tengan ID antes de renderizar
    console.log('IDs de candidatos a renderizar:', estado.candidatos.map(c => ({id: c.id, nombre: c.nombre})));
    
    elementos.listaCandidatos.innerHTML = estado.candidatos.map(candidato => {
        // Verificar que el candidato tenga ID
        if (!candidato.id) {
            console.error('Candidato sin ID:', candidato);
            return '';
        }
        
        return `
        <div class="candidate-card">
            <div class="candidate-info">
                <h3>${candidato.nombre}</h3>
                <div class="candidate-meta">
                    <p><strong><i class="fas fa-tag"></i> Categoría:</strong> ${candidato.categoria}</p>
                    <p><strong><i class="fas fa-hashtag"></i> Tarjetón:</strong> ${candidato.tarjeton}</p>
                    <p><strong><i class="fas fa-bullhorn"></i> Propuesta:</strong> ${candidato.propuesta}</p>
                </div>
                ${candidato.foto ? `
                    <div class="candidate-photo">
                        <img src="/static/images/candidatos/${candidato.foto}" alt="${candidato.nombre}">
                    </div>
                ` : ''}
            </div>
            <div class="candidate-actions">
                <button class="btn btn-warning btn-editar" data-id="${candidato.id}">
                    <i class="fas fa-edit"></i> Editar
                </button>
                <button class="btn btn-danger btn-eliminar" data-id="${candidato.id}">
                    <i class="fas fa-trash"></i> Eliminar
                </button>
            </div>
        </div>
        `;
    }).join('');
}

function actualizarResultados() {
    if (!estado.candidatos || estado.candidatos.length === 0) {
        elementos.resultados.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-chart-bar fa-3x mb-3"></i>
                <p>No hay resultados disponibles.</p>
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
    
    Object.keys(categorias).forEach(categoria => {
        // Ordenar por votos descendente
        const candidatosCategoria = categorias[categoria].sort((a, b) => (b.votos || 0) - (a.votos || 0));
        const maxVotos = Math.max(...candidatosCategoria.map(c => c.votos || 0));

        resultadosHTML += `
            <div class="result-category">
                <h4>${categoria.charAt(0).toUpperCase() + categoria.slice(1)}</h4>
                ${candidatosCategoria.map(candidato => {
                    const esGanador = (candidato.votos || 0) === maxVotos && maxVotos > 0;
                    return `
                        <div class="result-item ${esGanador ? 'winner' : ''}">
                            <div>
                                <strong>${candidato.nombre}</strong>
                                <div class="text-muted">Tarjetón: ${candidato.tarjeton}</div>
                            </div>
                            <span class="vote-count">${candidato.votos || 0} votos</span>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    });

    elementos.resultados.innerHTML = resultadosHTML;
}

// GESTIÓN DE FORMULARIOS
async function enviarFormCandidato(form, esEdicion = false) {
    const formData = new FormData(form);
    const id = esEdicion ? document.getElementById('edit-id').value : null;

    try {
        const url = esEdicion ? `${API_URLS.editarCandidato}${id}` : API_URLS.crearCandidato;
        const response = await fetch(url, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok || !data.ok) {
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
            elementos.fotoPreview.style.display = 'none';
        }

    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion(error.message, 'error');
    }
}

// FUNCIONES PARA EDITAR CANDIDATOS
function editarCandidato(id) {
    console.log('Editando candidato ID:', id, 'Tipo:', typeof id);
    console.log('Candidatos disponibles:', estado.candidatos);
    
    if (!id || id === 'undefined') {
        console.error('ID no válido recibido:', id);
        mostrarNotificacion('Error: ID de candidato no válido', 'error');
        return;
    }
    
    // Buscar el candidato - convertir a número si es necesario
    const candidato = estado.candidatos.find(c => {
        const candidatoId = c.id;
        const buscadoId = isNaN(id) ? id : Number(id);
        
        console.log(`Comparando: c.id=${candidatoId} (tipo: ${typeof candidatoId}) con id=${buscadoId} (tipo: ${typeof buscadoId})`);
        return candidatoId == buscadoId; // Usar == para comparación flexible
    });
    
    if (!candidato) {
        console.error('Candidato no encontrado con ID:', id);
        console.error('Candidatos disponibles:', estado.candidatos.map(c => c.id));
        mostrarNotificacion('Error: Candidato no encontrado', 'error');
        return;
    }

    console.log('Datos del candidato encontrado:', candidato);

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
    console.log('Mostrando modal de edición');
    if (elementos.modalEditar) {
        elementos.modalEditar.show();
    } else {
        console.error('Modal de edición no encontrado');
    }
}

async function eliminarCandidato(id) {
    if (!confirm('¿Está seguro de eliminar este candidato? Esta acción no se puede deshacer.')) {
        return;
    }

    try {
        const response = await fetch(`${API_URLS.eliminarCandidato}${id}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (response.ok && data.ok) {
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

    console.log('Elementos DOM inicializados:', elementos);

    // Formulario de horario
    if (elementos.formHorario) {
        elementos.formHorario.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            try {
                // USA FormData directamente para coincidir con tu ruta Flask
                const formData = new FormData(elementos.formHorario);
                
                const response = await fetch(API_URLS.guardarHorario, {
                    method: 'POST',
                    body: formData  // Envía FormData, no JSON
                });

                if (response.ok) {
                    // Recarga la página para mostrar los mensajes flash
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
    if (fotoInput) {
        fotoInput.addEventListener('change', function(e) {
            mostrarPreviewImagen(e.target, elementos.fotoPreview);
        });
    }

    const editFotoInput = document.getElementById('edit-foto');
    if (editFotoInput) {
        editFotoInput.addEventListener('change', function(e) {
            mostrarPreviewImagen(e.target, elementos.fotoPreviewEditar);
        });
    }

    // Eventos delegados para la lista de candidatos - MEJORADO
    if (elementos.listaCandidatos) {
        elementos.listaCandidatos.addEventListener('click', (e) => {
            console.log('Click en lista de candidatos:', e.target);
            console.log('Elemento clickeado:', e.target.tagName, e.target.className);
            
            // Buscar el botón más cercano
            const botonEditar = e.target.closest('.btn-editar');
            const botonEliminar = e.target.closest('.btn-eliminar');

            if (botonEditar) {
                const id = botonEditar.getAttribute('data-id');
                console.log('Botón editar clickeado, ID:', id, 'Tipo:', typeof id);
                console.log('Atributos del botón:', botonEditar.attributes);
                
                if (id && id !== 'undefined') {
                    editarCandidato(id);
                } else {
                    console.error('ID no válido en botón editar');
                    mostrarNotificacion('Error: ID de candidato no válido', 'error');
                }
            }

            if (botonEliminar) {
                const id = botonEliminar.getAttribute('data-id');
                console.log('Botón eliminar clickeado, ID:', id);
                
                if (id && id !== 'undefined') {
                    eliminarCandidato(id);
                } else {
                    console.error('ID no válido en botón eliminar');
                    mostrarNotificacion('Error: ID de candidato no válido', 'error');
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
            actualizarResultados();
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

                    if (response.ok && data.success) {
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
    console.log('Inicializando sistema de administración...');
    
    try {
        configurarEventos();
        await Promise.all([
            cargarHorarioActual(),
            cargarCandidatos()
        ]);
        
        console.log('Sistema inicializado correctamente');
        console.log('Candidatos cargados:', estado.candidatos);
    } catch (error) {
        console.error('Error en inicialización:', error);
        mostrarNotificacion('Error al inicializar el sistema', 'error');
    }
}

// Iniciar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', inicializar);