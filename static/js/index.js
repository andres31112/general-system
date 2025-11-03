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

// ==================== SISTEMA DE RESULTADOS PÚBLICOS CORREGIDO ====================

const RESULTS_API = '/admin/resultados-publicos';

// Función para cargar y mostrar resultados públicos
async function cargarResultadosPublicos() {
    const container = document.getElementById('public-results-container');
    const noResults = document.getElementById('no-results-message');
    const refreshBtn = document.getElementById('btn-refresh-results');
    const lastUpdate = document.getElementById('last-update');

    try {
        // Mostrar estado de carga
        container.innerHTML = `
            <div class="loading-state">
                <div class="spinner"></div>
                <p>Buscando resultados actualizados...</p>
            </div>
        `;
        
        // Deshabilitar botón durante la carga
        if (refreshBtn) {
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Buscando...';
        }

        const response = await fetch(RESULTS_API);
        const data = await response.json();

        console.log('📊 Datos recibidos:', data); // Debug

        if (!data.success) {
            throw new Error(data.error || 'Error al cargar resultados');
        }

        // Actualizar timestamp
        if (lastUpdate) {
            const now = new Date();
            lastUpdate.textContent = `Actualizado: ${now.toLocaleTimeString('es-ES')}`;
        }

        // Verificar si los resultados están publicados
        if (!data.resultados_publicados) {
            container.style.display = 'none';
            noResults.style.display = 'block';
            noResults.innerHTML = `
                <i class="fas fa-lock fa-3x mb-3"></i>
                <h3>Resultados en Proceso</h3>
                <p>Los resultados del proceso electoral estarán disponibles una vez finalice la votación y sean publicados por la administración.</p>
                <small>Vuelve más tarde para consultar los resultados oficiales.</small>
            `;
            return;
        }

        // Verificar si hay resultados
        const { resultados, total_votos } = data;
        
        // Debug: Ver estructura de resultados
        console.log('📋 Estructura de resultados:', resultados);
        console.log('🔢 Total de votos:', total_votos);

        const tieneResultados = resultados && Object.values(resultados).some(categoria => 
            Array.isArray(categoria) && categoria.length > 0
        );

        if (!tieneResultados) {
            container.style.display = 'none';
            noResults.style.display = 'block';
            noResults.innerHTML = `
                <i class="fas fa-chart-bar fa-3x mb-3"></i>
                <h3>Esperando Votos</h3>
                <p>El proceso electoral está en curso. Los resultados aparecerán aquí cuando los estudiantes comiencen a votar.</p>
            `;
            return;
        }

        // Mostrar resultados
        noResults.style.display = 'none';
        container.style.display = 'block';
        container.innerHTML = generarHTMLResultados(resultados, total_votos, data);

    } catch (error) {
        console.error('❌ Error cargando resultados:', error);
        container.innerHTML = `
            <div class="error-state">
                <i class="fas fa-exclamation-triangle fa-3x mb-3"></i>
                <h3>Error de Conexión</h3>
                <p>No pudimos cargar los resultados. Verifica tu conexión a internet.</p>
                <button onclick="cargarResultadosPublicos()" class="btn btn-light mt-3">
                    <i class="fas fa-redo"></i> Reintentar
                </button>
            </div>
        `;
    } finally {
        // Restaurar botón
        if (refreshBtn) {
            refreshBtn.disabled = false;
            refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Actualizar';
        }
    }
}

// Función para generar el HTML de los resultados - VERSIÓN CORREGIDA
function generarHTMLResultados(resultados, totalVotos, data) {
    console.log('🎨 Generando HTML con resultados:', resultados); // Debug
    
    let html = '';
    
    // Información de publicación
    if (data.fecha_publicacion || data.publicado_por) {
        const fechaPub = data.fecha_publicacion ? 
            new Date(data.fecha_publicacion).toLocaleDateString('es-ES', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            }) : 'Fecha no disponible';
        
        const publicadoPor = data.publicado_por || 'Administración';
        
        html += `
            <div class="publication-card" style="background: rgba(255,255,255,0.95); padding: 20px; border-radius: 15px; margin-bottom: 25px; text-align: center;">
                <div style="display: flex; align-items: center; justify-content: center; gap: 15px; margin-bottom: 10px;">
                    <i class="fas fa-calendar-check" style="color: #2c5aa0; font-size: 1.5rem;"></i>
                    <div>
                        <h4 style="color: #2c3e50; margin: 0;">Resultados Publicados</h4>
                        <p style="color: #666; margin: 5px 0 0 0;">Publicado el ${fechaPub} por ${publicadoPor}</p>
                    </div>
                </div>
                <div style="background: #2c5aa0; color: white; padding: 10px 20px; border-radius: 25px; display: inline-flex; align-items: center; gap: 8px;">
                    <i class="fas fa-chart-bar"></i>
                    <span>Total de votos: <strong>${totalVotos || 0}</strong></span>
                </div>
            </div>
        `;
    }
    
    // Configuración de categorías
    const categoriasConfig = {
        'personero': {
            icon: 'user-tie',
            title: 'Personero Estudiantil',
            color: '#3498db'
        },
        'contralor': {
            icon: 'chart-line',
            title: 'Contralor Estudiantil', 
            color: '#e74c3c'
        },
        'cabildante': {
            icon: 'users',
            title: 'Cabildante Estudiantil',
            color: '#2ecc71'
        }
    };

    // Verificar estructura de resultados
    if (!resultados || typeof resultados !== 'object') {
        return html + `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle"></i>
                Estructura de datos inválida
            </div>
        `;
    }

    // Generar sección para cada categoría
    Object.entries(resultados).forEach(([categoria, candidatos]) => {
        console.log(`📊 Procesando categoría: ${categoria}`, candidatos); // Debug
        
        if (!Array.isArray(candidatos) || candidatos.length === 0) {
            console.log(`❌ Categoría ${categoria} vacía o no es array`);
            return;
        }

        const config = categoriasConfig[categoria] || { 
            icon: 'user', 
            title: categoria.charAt(0).toUpperCase() + categoria.slice(1),
            color: '#95a5a6'
        };
        
        // Calcular total de votos para esta categoría
        const totalVotosCategoria = candidatos.reduce((sum, c) => sum + (parseInt(c.votos) || 0), 0);
        
        // Encontrar ganador(es)
        const maxVotos = Math.max(...candidatos.map(c => parseInt(c.votos) || 0));
        const ganadores = candidatos.filter(c => parseInt(c.votos) === maxVotos && maxVotos > 0);
        const esEmpate = ganadores.length > 1;
        
        console.log(`🏆 Ganadores en ${categoria}:`, ganadores.map(g => g.nombre));
        
        html += `
            <div class="results-category" style="background: white; border-radius: 15px; padding: 25px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                <div class="category-header" style="display: flex; align-items: center; gap: 15px; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 2px solid #f0f0f0;">
                    <div class="category-icon" style="width: 60px; height: 60px; background: ${config.color}; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 1.5rem;">
                        <i class="fas fa-${config.icon}"></i>
                    </div>
                    <div style="flex: 1;">
                        <h3 class="category-title" style="color: #2c3e50; margin: 0 0 5px 0; font-size: 1.5rem;">${config.title}</h3>
                        <div style="display: flex; align-items: center; gap: 15px; flex-wrap: wrap;">
                            <span class="category-votes" style="color: #666; font-size: 0.9rem;">
                                <i class="fas fa-chart-bar"></i> ${totalVotosCategoria} votos totales
                            </span>
                            ${maxVotos > 0 ? `
                                <span style="background: ${esEmpate ? '#f39c12' : config.color}; color: white; padding: 4px 12px; border-radius: 15px; font-size: 0.8rem; font-weight: 600;">
                                    <i class="fas fa-${esEmpate ? 'handshake' : 'trophy'}"></i>
                                    ${esEmpate ? `Empate (${ganadores.length} candidatos)` : 'Ganador único'}
                                </span>
                            ` : ''}
                        </div>
                    </div>
                </div>
                
                <div class="results-list">
                    ${candidatos.map(candidato => {
                        const votos = parseInt(candidato.votos) || 0;
                        const porcentaje = totalVotosCategoria > 0 ? 
                            ((votos / totalVotosCategoria) * 100).toFixed(1) : 0;
                        const esGanador = votos === maxVotos && maxVotos > 0;
                        
                        return `
                            <div class="result-item ${esGanador ? 'winner' : ''}" 
                                 style="display: flex; justify-content: space-between; align-items: center; padding: 20px; margin-bottom: 12px; background: ${esGanador ? 'linear-gradient(135deg, #fff9c4, #fff176)' : '#f8f9fa'}; border-radius: 12px; border-left: 4px solid ${esGanador ? config.color : '#ddd'}; transition: all 0.3s ease;">
                                <div class="candidate-info" style="flex: 1;">
                                    <div class="candidate-name" style="font-weight: 600; color: #2c3e50; margin-bottom: 8px; font-size: 1.1rem;">
                                        ${candidato.nombre || 'Candidato sin nombre'}
                                    </div>
                                    <div class="candidate-details" style="display: flex; gap: 15px; flex-wrap: wrap; font-size: 0.9rem;">
                                        <span class="tarjeton-badge" style="background: #2c5aa0; color: white; padding: 4px 12px; border-radius: 12px; font-weight: 600;">
                                            Tarjetón ${candidato.tarjeton || 'N/A'}
                                        </span>
                                        <span class="votes-count" style="color: #27ae60; font-weight: 600;">
                                            <i class="fas fa-chart-bar"></i> ${votos} votos
                                        </span>
                                        <span class="votes-percentage" style="color: #666;">
                                            ${porcentaje}%
                                        </span>
                                    </div>
                                </div>
                                ${esGanador ? `
                                    <span class="winner-badge" style="background: ${config.color}; color: white; padding: 8px 16px; border-radius: 20px; font-weight: 600; display: flex; align-items: center; gap: 6px;">
                                        <i class="fas fa-${esEmpate ? 'handshake' : 'trophy'}"></i>
                                        ${esEmpate ? 'Empate' : 'Ganador'}
                                    </span>
                                ` : ''}
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    });

    // Si no se generó ningún contenido
    if (html === '') {
        html = `
            <div class="alert alert-info" style="background: #d1ecf1; color: #0c5460; padding: 20px; border-radius: 10px; text-align: center;">
                <i class="fas fa-info-circle"></i>
                <h4>Datos en Procesamiento</h4>
                <p>Los resultados se están procesando y estarán disponibles pronto.</p>
            </div>
        `;
    }

    return html;
}

// Función para inicializar el sistema de resultados
function inicializarResultadosPublicos() {
    const refreshBtn = document.getElementById('btn-refresh-results');
    
    if (refreshBtn) {
        refreshBtn.addEventListener('click', cargarResultadosPublicos);
        
        // Cargar resultados automáticamente al iniciar
        cargarResultadosPublicos();
        
        // Actualizar cada 30 segundos
        setInterval(cargarResultadosPublicos, 30000);
    }
}

// ===== INICIALIZACIÓN MEJORADA =====
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Inicializando página de resultados públicos...');
    
    // Inicializar todas las funcionalidades
    initSmoothScroll();
    initScrollAnimations();
    inicializarResultadosPublicos();
    
    // Cargar resultados inmediatamente
    setTimeout(() => {
        cargarResultadosPublicos();
    }, 1000);
});

// Funciones auxiliares (mantener las existentes)
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
}

function initScrollAnimations() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.feature-card, .program-card, .stat-card').forEach(el => {
        observer.observe(el);
    });
}