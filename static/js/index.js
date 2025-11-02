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

// ==================== SISTEMA DE RESULTADOS PÚBLICOS ====================

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
            <div class="loading-results">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Verificando resultados...</p>
            </div>
        `;
        
        // Deshabilitar botón durante la carga
        if (refreshBtn) {
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Cargando...';
        }

        const response = await fetch(RESULTS_API);
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Error al cargar resultados');
        }

        // Actualizar timestamp
        if (lastUpdate) {
            lastUpdate.textContent = `Última actualización: ${new Date().toLocaleTimeString()}`;
        }

        // Verificar si los resultados están publicados
        if (!data.resultados_publicados) {
            container.style.display = 'none';
            noResults.style.display = 'block';
            noResults.innerHTML = `
                <i class="fas fa-lock fa-3x"></i>
                <h3>Resultados no disponibles</h3>
                <p>Los resultados aún no han sido publicados por la administración.</p>
                <small>Vuelve más tarde para consultar los resultados.</small>
            `;
            return;
        }

        // Verificar si hay resultados
        const { resultados, total_votos } = data;
        const tieneResultados = Object.values(resultados).some(categoria => categoria.length > 0);

        if (!tieneResultados) {
            container.style.display = 'none';
            noResults.style.display = 'block';
            noResults.innerHTML = `
                <i class="fas fa-chart-bar fa-3x"></i>
                <h3>No hay resultados disponibles</h3>
                <p>No se han registrado votos todavía.</p>
            `;
            return;
        }

        // Ocultar mensaje de no resultados
        noResults.style.display = 'none';
        container.style.display = 'block';

        // Generar HTML de resultados con información de publicación
        container.innerHTML = generarHTMLResultados(resultados, total_votos, data);

    } catch (error) {
        console.error('Error cargando resultados:', error);
        container.innerHTML = `
            <div class="no-results">
                <i class="fas fa-exclamation-triangle fa-3x"></i>
                <h3>Error al cargar resultados</h3>
                <p>${error.message}</p>
                <button onclick="cargarResultadosPublicos()" class="btn" style="margin-top: 15px;">
                    <i class="fas fa-redo"></i> Reintentar
                </button>
            </div>
        `;
    } finally {
        // Restaurar botón
        if (refreshBtn) {
            refreshBtn.disabled = false;
            refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Actualizar Resultados';
        }
    }
}

// Función para generar el HTML de los resultados
function generarHTMLResultados(resultados, totalVotos, data) {
    let html = '';
    
    // Información de publicación
    if (data.fecha_publicacion || data.publicado_por) {
        const fechaPub = data.fecha_publicacion ? new Date(data.fecha_publicacion).toLocaleString() : 'Fecha no disponible';
        const publicadoPor = data.publicado_por || 'Administración';
        
        html += `
            <div class="publication-info" style="text-align: center; margin-bottom: 20px; padding: 15px; background: rgba(255,255,255,0.9); border-radius: 10px;">
                <p style="margin: 0; color: #2c3e50; font-size: 0.9rem;">
                    <i class="fas fa-calendar-check"></i> 
                    Publicado el ${fechaPub} por ${publicadoPor}
                </p>
            </div>
        `;
    }
    
    // Definir iconos y títulos para cada categoría
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

    // Generar sección para cada categoría
    Object.entries(resultados).forEach(([categoria, candidatos]) => {
        if (candidatos.length === 0) return;

        const config = categoriasConfig[categoria] || { icon: 'user', title: categoria };
        const totalVotosCategoria = candidatos.reduce((sum, c) => sum + c.votos, 0);
        
        // Encontrar ganador (máximo de votos)
        const maxVotos = Math.max(...candidatos.map(c => c.votos));
        
        html += `
            <div class="results-category">
                <div class="category-header">
                    <div class="category-icon">
                        <i class="fas fa-${config.icon}"></i>
                    </div>
                    <h3 class="category-title">${config.title}</h3>
                    <span class="category-votes">${totalVotosCategoria} votos totales</span>
                </div>
                <div class="results-list">
                    ${candidatos.map(candidato => {
                        const porcentaje = totalVotosCategoria > 0 ? 
                            ((candidato.votos / totalVotosCategoria) * 100).toFixed(1) : 0;
                        const esGanador = candidato.votos === maxVotos && maxVotos > 0;
                        
                        return `
                            <div class="result-item ${esGanador ? 'winner' : ''}">
                                <div class="candidate-info">
                                    <div class="candidate-name">${candidato.nombre}</div>
                                    <div class="candidate-details">
                                        <span class="tarjeton-badge">Tarjetón ${candidato.tarjeton}</span>
                                        <span class="votes-count">${candidato.votos} votos</span>
                                        <span class="votes-percentage">${porcentaje}%</span>
                                    </div>
                                </div>
                                ${esGanador ? `
                                    <span class="winner-badge">
                                        <i class="fas fa-trophy"></i> Ganador
                                    </span>
                                ` : ''}
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    });

    // Agregar resumen general si hay múltiples categorías
    const categoriasConResultados = Object.values(resultados).filter(c => c.length > 0).length;
    if (categoriasConResultados > 1 && totalVotos > 0) {
        html = `
            <div class="total-summary" style="text-align: center; margin-bottom: 25px; padding: 15px; background: rgba(255,255,255,0.9); border-radius: 10px;">
                <h4 style="color: #2c3e50; margin: 0;">Total de votos emitidos: <strong>${totalVotos}</strong></h4>
            </div>
        ` + html;
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

// ===== SCROLL SUAVE Y NAVEGACIÓN =====
function initSmoothScroll() {
    // Scroll suave para enlaces internos
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Actualizar navegación activa al hacer scroll
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav-link');
    
    function updateActiveNav() {
        let current = '';
        sections.forEach(section => {
            const sectionTop = section.offsetTop - 100;
            const sectionHeight = section.clientHeight;
            if (scrollY >= sectionTop && scrollY < sectionTop + sectionHeight) {
                current = section.getAttribute('id');
            }
        });

        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${current}`) {
                link.classList.add('active');
            }
        });
    }

    window.addEventListener('scroll', updateActiveNav);
}

// ===== ANIMACIONES AL SCROLL =====
function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);

    // Observar elementos para animación
    document.querySelectorAll('.feature-card, .program-card, .stat-card').forEach(el => {
        observer.observe(el);
    });
}

// ===== MEJORAS EN EL SISTEMA DE RESULTADOS =====
function generarHTMLResultados(resultados, totalVotos, data) {
    let html = '';
    
    // Información de publicación mejorada
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
                    <span>Total de votos: <strong>${totalVotos}</strong></span>
                </div>
            </div>
        `;
    }
    
    // Resto del código de generación de resultados se mantiene igual...
    // [Aquí iría el código existente de generarHTMLResultados]
    
    return html;
}

// ===== MEJORAS EN LA CARGA DE RESULTADOS =====
async function cargarResultadosPublicos() {
    const container = document.getElementById('public-results-container');
    const noResults = document.getElementById('no-results-message');
    const refreshBtn = document.getElementById('btn-refresh-results');
    const lastUpdate = document.getElementById('last-update');

    try {
        // Mostrar estado de carga mejorado
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

        if (!data.success) {
            throw new Error(data.error || 'Error al cargar resultados');
        }

        // Actualizar timestamp con formato mejorado
        if (lastUpdate) {
            const now = new Date();
            lastUpdate.textContent = `Actualizado: ${now.toLocaleTimeString('es-ES')}`;
        }

        // Manejo de estados mejorado
        if (!data.resultados_publicados) {
            container.style.display = 'none';
            noResults.style.display = 'block';
            noResults.innerHTML = `
                <i class="fas fa-lock"></i>
                <h3>Resultados en Proceso</h3>
                <p>Los resultados del proceso electoral estarán disponibles una vez finalice la votación y sean publicados por la administración.</p>
                <small>Vuelve más tarde para consultar los resultados oficiales.</small>
            `;
            return;
        }

        // Verificar si hay resultados
        const { resultados, total_votos } = data;
        const tieneResultados = Object.values(resultados).some(categoria => categoria.length > 0);

        if (!tieneResultados) {
            container.style.display = 'none';
            noResults.style.display = 'block';
            noResults.innerHTML = `
                <i class="fas fa-chart-bar"></i>
                <h3>Esperando Votos</h3>
                <p>El proceso electoral está en curso. Los resultados aparecerán aquí cuando los estudiantes comiencen a votar.</p>
            `;
            return;
        }

        // Mostrar resultados
        noResults.style.display = 'none';
        container.style.display = 'block';
        container.innerHTML = generarHTMLResultados(resultados, total_votos, data);

        // Animar la entrada de los resultados
        setTimeout(() => {
            document.querySelectorAll('.results-category').forEach((category, index) => {
                category.style.animationDelay = `${index * 0.2}s`;
                category.classList.add('animate-in');
            });
        }, 100);

    } catch (error) {
        console.error('Error cargando resultados:', error);
        container.innerHTML = `
            <div class="error-state">
                <i class="fas fa-exclamation-triangle"></i>
                <h3>Error de Conexión</h3>
                <p>No pudimos cargar los resultados. Verifica tu conexión a internet.</p>
                <button onclick="cargarResultadosPublicos()" class="btn btn-light">
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

// ===== INICIALIZACIÓN MEJORADA =====
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar todas las funcionalidades
    initSmoothScroll();
    initScrollAnimations();
    inicializarResultadosPublicos();
    
    // Efectos de hover mejorados
    initHoverEffects();
    
    // Cargar resultados inmediatamente
    cargarResultadosPublicos();
});

function initHoverEffects() {
    // Efectos de hover para tarjetas
    document.addEventListener('mousemove', function(e) {
        const cards = document.querySelectorAll('.feature-card, .program-card, .stat-card');
        cards.forEach(card => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            card.style.setProperty('--mouse-x', `${x}px`);
            card.style.setProperty('--mouse-y', `${y}px`);
        });
    });
}

// Inicializar el carrusel y otras funciones cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    initCarousel('mi-carrusel-1');
    setupSmoothScroll('contact-scroll-btn', 'contact-form');
    setupSmoothScroll('admissions-btn', 'contact-form');
    setupContactForm();
    inicializarResultadosPublicos(); // ← Agrega esta línea
});