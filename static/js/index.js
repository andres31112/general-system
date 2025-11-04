// index.js

const header = document.querySelector('header');
const navbar = document.querySelector('.navbar');

window.addEventListener('scroll', function () {
    // Si el scroll es mayor a 50px...
    if (window.scrollY > 50) {
        // Solo añade la clase 'scrolled' si no la tiene ya.
        if (!navbar.classList.contains('scrolled')) {
            navbar.classList.add('scrolled');
        }
    } else {
        // Si el scroll es menor o igual a 50px y la barra está en modo 'scrolled'...
        if (navbar.classList.contains('scrolled')) {
            // 1. Añadimos una clase al header para DESACTIVAR las transiciones.
            // Esto crea un efecto de "snap" al volver arriba.
            header.classList.add('no-transition-on-return');

            // 2. Quitamos la clase 'scrolled'. El cambio será INSTANTÁNEO.
            navbar.classList.remove('scrolled');

            // 3. Usamos setTimeout para quitar la clase de anulación después
            // de que el navegador haya procesado la eliminación de 'scrolled'.
            // Esto previene un parpadeo y asegura que las animaciones
            // para futuros scrolls funcionen correctamente.
            setTimeout(() => {
                header.classList.remove('no-transition-on-return');
            }, 10);
        }
    }
});


function initCarousel(carouselId) {
    const carouselComponent = document.getElementById(carouselId);
    if (!carouselComponent) {
        console.error(`No se encontró el carrusel con el ID: ${carouselId}`);
        return;
    }

    const slidesContainer = carouselComponent.querySelector('.slides-container');
    const prevButton = carouselComponent.querySelector('.prev-button');
    const nextButton = carouselComponent.querySelector('.next-button');

    const slideItems = Array.from(carouselComponent.querySelectorAll('.carousel-slide'));
    const slidesVisible = window.innerWidth <= 768 ? 1 : 2; // Mostrar 1 en móviles, 2 en pantallas más grandes
    const slideCount = slideItems.length;

    if (slideCount === 0) return;

    // Lógica para el bucle infinito
    // Clona el final y el principio de las diapositivas
    const lastClones = slideItems.slice(-slidesVisible).map(item => item.cloneNode(true));
    const firstClones = slideItems.slice(0, slidesVisible).map(item => item.cloneNode(true));

    lastClones.reverse().forEach(clone => slidesContainer.prepend(clone));
    firstClones.forEach(clone => slidesContainer.appendChild(clone));

    // El índice inicial está en la primera diapositiva "real" (después de los clones)
    let slideIndex = slidesVisible;
    let isTransitioning = false;
    let autoSlideInterval;

    function updateSlidePosition(withTransition = true) {
        slidesContainer.style.transition = withTransition ? 'transform 0.5s ease-in-out' : 'none';
        const offset = -slideIndex * (100 / slidesVisible);
        slidesContainer.style.transform = `translateX(${offset}%)`;
    }

    // Posición inicial sin transición
    updateSlidePosition(false);

    slidesContainer.addEventListener('transitionend', () => {
        isTransitioning = false;

        // Si llegamos a los clones del final, saltamos al primer slide real
        if (slideIndex >= slideCount + slidesVisible) {
            slideIndex = slidesVisible;
            updateSlidePosition(false);
        }

        // Si llegamos a los clones del principio, saltamos al último slide real
        if (slideIndex <= 0) {
            slideIndex = slideCount;
            updateSlidePosition(false);
        }
    });

    function shiftSlide(n) {
        if (isTransitioning) return;
        isTransitioning = true;
        slideIndex += n;
        updateSlidePosition();
    }

    function startAutoSlide() {
        stopAutoSlide();
        autoSlideInterval = setInterval(() => shiftSlide(slidesVisible), 3000);
    }

    function stopAutoSlide() {
        clearInterval(autoSlideInterval);
    }

    nextButton.addEventListener('click', () => {
        stopAutoSlide();
        shiftSlide(slidesVisible);
        startAutoSlide();
    });

    prevButton.addEventListener('click', () => {
        stopAutoSlide();
        shiftSlide(-slidesVisible);
        startAutoSlide();
    });

    carouselComponent.addEventListener('mouseenter', stopAutoSlide);
    carouselComponent.addEventListener('mouseleave', startAutoSlide);

    startAutoSlide();
}

// Funcionalidad de scroll suave para los botones
function setupSmoothScroll(buttonId, targetId) {
    const button = document.getElementById(buttonId);
    if (button) {
        button.addEventListener('click', (event) => {
            event.preventDefault();
            const targetElement = document.getElementById(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }
}

// Validación del formulario de contacto
function setupContactForm() {
    const form = document.getElementById('contact-form');
    if (form) {
        form.addEventListener('submit', (event) => {
            event.preventDefault();
            const name = document.getElementById('name').value;
            const email = document.getElementById('email').value;
            const message = document.getElementById('message').value;

            if (name.trim() === '' || email.trim() === '' || message.trim() === '') {
                alert('Por favor, completa todos los campos.');
                return;
            }

            // Aquí puedes añadir la lógica para enviar el formulario a un backend (Ej: Fetch API)
            console.log('Formulario enviado:', { name, email, message });
            alert('¡Gracias! Tu mensaje ha sido enviado. Nos pondremos en contacto contigo pronto.');
            form.reset();
        });
    }
}

async function loadPublicResumen() {
    try {
        const res = await fetch('/api/public/resumen', { cache: 'no-cache' });
        const json = await res.json();
        if (!json.success) throw new Error(json.message || 'Error resumen');
        // Mostrar valores de la API, pero luego forzar a los valores solicitados
        const d = json.data || {};
        setText('stat-docentes', d.docentes ?? '--');
        setText('stat-estudiantes', d.estudiantes ?? '--');
        setText('stat-cursos', d.cursos ?? '--');
        setText('stat-eventos', d.eventos ?? '--');
    } catch (e) {
        console.warn('Resumen público no disponible', e);
    }
    // Forzar valores solicitados por el usuario
    setText('stat-docentes', 10);
    setText('stat-estudiantes', 50);
    setText('stat-cursos', 12);
    setText('stat-eventos', 3);
}

async function loadPublicCursos() {
    try {
        const res = await fetch('/api/public/cursos?limit=6', { cache: 'no-cache' });
        const json = await res.json();
        if (!json.success) throw new Error(json.message || 'Error cursos');
        const cont = document.getElementById('public-cursos');
        if (!cont) return;
        const cursos = json.cursos || [];
        cont.innerHTML = cursos.map(c => `
            <div class="col-12 col-md-6 col-lg-4">
                <div class="card h-100 shadow-sm">
                    <div class="card-body">
                        <h5 class="card-title mb-1">${escapeHtml(c.nombre || 'Curso')}</h5>
                        <p class="text-muted mb-0">${escapeHtml(c.sede || 'Sede')}</p>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (e) {
        console.warn('Cursos públicos no disponibles', e);
    }
}

async function loadPublicEventos() {
    try {
        const res = await fetch('/api/public/eventos?limit=50', { cache: 'no-cache' });
        const json = await res.json();
        if (!json.success) throw new Error(json.message || 'Error eventos');
        const ul = document.getElementById('public-eventos');
        if (!ul) return;
        const evs = json.eventos || [];
        if (evs.length === 0) { ul.innerHTML = '<li class="list-group-item">Sin eventos próximos</li>'; return; }
        ul.innerHTML = evs.map(e => `
            <li class="list-group-item d-flex justify-content-between align-items-center">
                <div>
                    <strong>${escapeHtml(e.nombre || 'Evento')}</strong>
                    <div class="small text-muted">${escapeHtml(e.descripcion || '')}</div>
                </div>
                <span class="badge bg-primary">${escapeHtml(e.fecha || '')}${e.hora ? ' ' + escapeHtml(e.hora) : ''}</span>
            </li>
        `).join('');
    } catch (e) {
        console.warn('Eventos públicos no disponibles', e);
    }
}

function setText(id, txt) {
    const el = document.getElementById(id);
    if (el) el.textContent = String(txt);
}

function escapeHtml(s) {
    return String(s)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

// ==================== SISTEMA DE RESULTADOS PÚBLICOS ====================

const RESULTS_API = '/admin/resultados-publicos';

async function cargarResultadosPublicos() {
    const container = document.getElementById('public-results-container');
    const noResults = document.getElementById('no-results-message');
    const refreshBtn = document.getElementById('btn-refresh-results');
    const lastUpdate = document.getElementById('last-update');

    if (!container || !noResults) return;

    try {
        container.innerHTML = `
            <div class="loading-state">
                <div class="spinner"></div>
                <p>Buscando resultados actualizados...</p>
            </div>
        `;
        if (refreshBtn) {
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Buscando...';
        }

        const response = await fetch(RESULTS_API, { cache: 'no-cache' });
        const data = await response.json();
        if (!data.success) throw new Error(data.error || 'Error al cargar resultados');

        if (lastUpdate) {
            const now = new Date();
            lastUpdate.textContent = `Actualizado: ${now.toLocaleTimeString('es-ES')}`;
        }

        if (!data.resultados_publicados) {
            container.style.display = 'none';
            noResults.style.display = 'block';
            noResults.innerHTML = `
                <i class="fas fa-lock"></i>
                <h3>Resultados en Proceso</h3>
                <p>Los resultados estarán disponibles cuando sean publicados por la administración.</p>
            `;
            return;
        }

        const { resultados, total_votos } = data;
        const tieneResultados = Object.values(resultados || {}).some(categoria => categoria.length > 0);
        if (!tieneResultados) {
            container.style.display = 'none';
            noResults.style.display = 'block';
            noResults.innerHTML = `
                <i class="fas fa-chart-bar"></i>
                <h3>Sin datos aún</h3>
                <p>Cuando haya votos registrados verás los resultados aquí.</p>
            `;
            return;
        }

        noResults.style.display = 'none';
        container.style.display = 'block';
        container.innerHTML = generarHTMLResultados(resultados, total_votos, data);
    } catch (error) {
        console.error('Error cargando resultados:', error);
        if (container) {
            container.innerHTML = `
                <div class="error-state">
                    <i class="fas fa-exclamation-triangle"></i>
                    <h3>Error de Conexión</h3>
                    <p>No pudimos cargar los resultados.</p>
                    <button onclick="cargarResultadosPublicos()" class="btn btn-light">
                        <i class="fas fa-redo"></i> Reintentar
                    </button>
                </div>
            `;
        }
    } finally {
        if (refreshBtn) {
            refreshBtn.disabled = false;
            refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Actualizar';
        }
    }
}

function generarHTMLResultados(resultados, totalVotos, data) {
    let html = '';
    if (data && (data.fecha_publicacion || data.publicado_por)) {
        const fechaPub = data.fecha_publicacion ? new Date(data.fecha_publicacion).toLocaleString('es-ES') : 'Fecha no disponible';
        const publicadoPor = data.publicado_por || 'Administración';
        html += `
            <div class="publication-card">
                <div class="publication-header">
                    <i class="fas fa-calendar-check"></i>
                    <div>
                        <h4>Resultados Publicados</h4>
                        <p>Publicado el ${fechaPub} por ${publicadoPor}</p>
                    </div>
                </div>
                <div class="total-votes">
                    <i class="fas fa-chart-bar"></i>
                    <span>Total de votos: <strong>${totalVotos ?? 0}</strong></span>
                </div>
            </div>
        `;
    }

    const categoriasConfig = {
        'personero': { icon: 'user-tie', title: 'Personero Estudiantil' },
        'contralor': { icon: 'chart-line', title: 'Contralor Estudiantil' },
        'cabildante': { icon: 'users', title: 'Cabildante Estudiantil' }
    };

    Object.entries(resultados || {}).forEach(([categoria, candidatos]) => {
        if (!Array.isArray(candidatos) || candidatos.length === 0) return;
        const cfg = categoriasConfig[categoria] || { icon: 'user', title: categoria };
        const totalVotosCat = candidatos.reduce((s, c) => s + (c.votos || 0), 0);
        const maxVotos = Math.max(...candidatos.map(c => c.votos || 0));

        html += `
            <div class="results-category">
                <div class="category-header">
                    <div class="category-icon"><i class="fas fa-${cfg.icon}"></i></div>
                    <h3 class="category-title">${cfg.title}</h3>
                    <span class="category-votes">${totalVotosCat} votos totales</span>
                </div>
                <div class="results-list">
                    ${candidatos.map(c => {
                        const votos = c.votos || 0;
                        const porcentaje = totalVotosCat > 0 ? ((votos / totalVotosCat) * 100).toFixed(1) : 0;
                        const esGanador = votos === maxVotos && maxVotos > 0;
                        return `
                            <div class="result-item ${esGanador ? 'winner' : ''}">
                                <div class="candidate-info">
                                    <div class="candidate-name">${escapeHtml(c.nombre || '')}</div>
                                    <div class="candidate-details">
                                        <span class="tarjeton-badge">Tarjetón ${escapeHtml(c.tarjeton || '')}</span>
                                        <span class="votes-count">${votos} votos</span>
                                        <span class="votes-percentage">${porcentaje}%</span>
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

    return html;
}

function inicializarResultadosPublicos() {
    const refreshBtn = document.getElementById('btn-refresh-results');
    if (!refreshBtn) return;
    refreshBtn.addEventListener('click', cargarResultadosPublicos);
    cargarResultadosPublicos();
    setInterval(cargarResultadosPublicos, 30000);
}

// Inicializar el carrusel y otras funciones cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    initCarousel('mi-carrusel-1');
    setupSmoothScroll('contact-scroll-btn', 'contact-form');
    setupSmoothScroll('admissions-btn', 'contact-form');
    setupContactForm();
    loadPublicResumen();
    loadPublicCursos();
    loadPublicEventos();
    inicializarResultadosPublicos();
});