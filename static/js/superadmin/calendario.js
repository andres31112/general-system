// calendario.js - Script completo para el calendario de eventos

let events = [];
let currentDate = new Date();
let selectedEventIndex = null;
let selectedRoles = new Set(['Estudiante']); // Valor por defecto
let editingEventId = null;
let editSelectedRoles = new Set();

// =============================================
// INICIALIZACIÓN Y CONFIGURACIÓN
// =============================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Inicializando calendario...');
    initializeCalendar();
    setupEventListeners();
    loadEvents();
    createParticles();
    initializeRoleSelector();
    initializeEditRoleSelector();
});

function initializeCalendar() {
    createCalendar();
    
    // Establecer fecha mínima en el input de fecha (hoy)
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('date').min = today;
    document.getElementById('editDate').min = today;
    
    // Mostrar tooltips en hover
    setupTooltips();
    
    console.log('📅 Calendario inicializado correctamente');
}

function setupEventListeners() {
    // Navegación entre meses
    document.getElementById('prevMonth').addEventListener('click', goToPreviousMonth);
    document.getElementById('nextMonth').addEventListener('click', goToNextMonth);
    
    // Toggle del formulario
    document.getElementById('toggleForm').addEventListener('click', toggleForm);
    
    // Validación de fecha y hora
    document.getElementById('date').addEventListener('change', updateTimeValidation);
    document.getElementById('editDate').addEventListener('change', updateEditTimeValidation);
    
    // Validación en tiempo real
    setupRealTimeValidation();
    
    // Prevención de caracteres especiales
    setupCharacterValidation();
    
    // Cerrar modales con ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeModal();
            closeEditModal();
        }
    });
    
    // Cerrar modales haciendo click fuera
    document.getElementById('eventDetails').addEventListener('click', function(e) {
        if (e.target === this) {
            closeModal();
        }
    });
    
    document.getElementById('editEvent').addEventListener('click', function(e) {
        if (e.target === this) {
            closeEditModal();
        }
    });
    
    // Botón de edición
    document.getElementById('editBtn').addEventListener('click', function() {
        if (selectedEventIndex !== null) {
            const event = events[selectedEventIndex];
            openEditModal(event);
        }
    });
    
    // Botón de guardar edición
    document.getElementById('saveEditBtn').addEventListener('click', saveEditedEvent);
    
    // Efectos de hover en botones de navegación
    setupNavigationEffects();
    
    // Botón de eliminar en modal de detalles
    document.getElementById('deleteBtn').addEventListener('click', function() {
        if (selectedEventIndex !== null) {
            const event = events[selectedEventIndex];
            deleteEvent(event.id);
        }
    });
    
    console.log('🎯 Event listeners configurados');
}

// =============================================
// VALIDACIÓN DE CARACTERES - SOLO LETRAS Y NÚMEROS
// =============================================

function setupCharacterValidation() {
    // Campos que deben validar caracteres especiales
    const titleInput = document.getElementById('title');
    const descriptionInput = document.getElementById('description');
    const editTitleInput = document.getElementById('editTitle');
    const editDescriptionInput = document.getElementById('editDescription');
    
    if (titleInput) {
        titleInput.addEventListener('input', function(e) {
            validateOnlyLettersNumbersSpaces(this, 'title');
        });
        
        titleInput.addEventListener('keypress', function(e) {
            preventSpecialCharacters(e);
        });
        
        titleInput.addEventListener('blur', function(e) {
            validateOnlyLettersNumbersSpaces(this, 'title');
        });
    }
    
    if (descriptionInput) {
        descriptionInput.addEventListener('input', function(e) {
            validateOnlyLettersNumbersSpaces(this, 'description');
        });
        
        descriptionInput.addEventListener('keypress', function(e) {
            preventSpecialCharacters(e);
        });
        
        descriptionInput.addEventListener('blur', function(e) {
            validateOnlyLettersNumbersSpaces(this, 'description');
        });
    }
    
    if (editTitleInput) {
        editTitleInput.addEventListener('input', function(e) {
            validateOnlyLettersNumbersSpaces(this, 'editTitle');
        });
        
        editTitleInput.addEventListener('keypress', function(e) {
            preventSpecialCharacters(e);
        });
        
        editTitleInput.addEventListener('blur', function(e) {
            validateOnlyLettersNumbersSpaces(this, 'editTitle');
        });
    }
    
    if (editDescriptionInput) {
        editDescriptionInput.addEventListener('input', function(e) {
            validateOnlyLettersNumbersSpaces(this, 'editDescription');
        });
        
        editDescriptionInput.addEventListener('keypress', function(e) {
            preventSpecialCharacters(e);
        });
        
        editDescriptionInput.addEventListener('blur', function(e) {
            validateOnlyLettersNumbersSpaces(this, 'editDescription');
        });
    }
}

function preventSpecialCharacters(e) {
    // Permitir teclas de control (backspace, delete, tab, etc.)
    if (e.ctrlKey || e.altKey || e.metaKey) return true;
    
    // Permitir teclas de navegación
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight' || 
        e.key === 'ArrowUp' || e.key === 'ArrowDown' ||
        e.key === 'Home' || e.key === 'End' ||
        e.key === 'Tab' || e.key === 'Enter') return true;
    
    // Solo permitir: letras, números, espacios
    const allowedPattern = /^[a-zA-ZÀ-ÿ0-9\s]$/;
    
    if (!allowedPattern.test(e.key)) {
        e.preventDefault();
        showTemporaryMessage('Solo se permiten letras, números y espacios');
        return false;
    }
    
    return true;
}

function validateOnlyLettersNumbersSpaces(input, fieldType) {
    const value = input.value;
    const fieldName = getFieldName(fieldType);
    
    // Patrón extremadamente restrictivo: solo letras, números y espacios
    const allowedPattern = /^[a-zA-ZÀ-ÿ0-9\s]*$/;
    
    // Encontrar caracteres no permitidos (cualquier cosa que no sea letra, número o espacio)
    const invalidChars = /[^a-zA-ZÀ-ÿ0-9\s]/g;
    const foundInvalid = value.match(invalidChars);
    const hasInvalid = foundInvalid && foundInvalid.length > 0;
    
    if (hasInvalid) {
        // Mostrar error con los caracteres específicos encontrados
        const uniqueChars = [...new Set(foundInvalid)];
        showCharacterError(input, `Caracteres no permitidos: ${uniqueChars.join(', ')}`);
        
        // Limpiar automáticamente los caracteres inválidos
        const cleanedValue = value.replace(invalidChars, '');
        input.value = cleanedValue;
        
        return false;
    }
    
    if (!allowedPattern.test(value) && value.length > 0) {
        showCharacterError(input, 'Solo se permiten letras, números y espacios');
        return false;
    }
    
    // Limpiar error si todo está bien
    clearCharacterError(input);
    return true;
}

function getFieldName(fieldType) {
    const fieldNames = {
        'title': 'Título',
        'description': 'Descripción',
        'editTitle': 'Título',
        'editDescription': 'Descripción'
    };
    return fieldNames[fieldType] || 'Campo';
}

function showCharacterError(input, message) {
    input.classList.add('character-error');
    
    let errorDiv = input.parentNode.querySelector('.character-validation-error');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.className = 'character-validation-error';
        input.parentNode.appendChild(errorDiv);
    }
    errorDiv.innerHTML = `<i class="fas fa-ban"></i> ${message}`;
    
    // Agregar efecto visual de shake
    input.style.animation = 'shake 0.5s ease';
    setTimeout(() => {
        input.style.animation = '';
    }, 500);
}

function clearCharacterError(input) {
    input.classList.remove('character-error');
    
    const errorDiv = input.parentNode.querySelector('.character-validation-error');
    if (errorDiv) {
        errorDiv.remove();
    }
}

function showTemporaryMessage(message) {
    // Crear mensaje temporal
    const tempMessage = document.createElement('div');
    tempMessage.className = 'temporary-message';
    tempMessage.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${message}`;
    tempMessage.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: var(--error-color);
        color: white;
        padding: 10px 15px;
        border-radius: 5px;
        z-index: 10000;
        animation: fadeInOut 2s ease;
    `;
    
    document.body.appendChild(tempMessage);
    
    setTimeout(() => {
        tempMessage.remove();
    }, 2000);
}

// Función para sanitizar el texto - elimina TODO lo que no sea letra, número o espacio
function sanitizeText(text) {
    if (!text) return text;
    
    // Remover TODO carácter especial, solo dejar letras, números y espacios
    return text.replace(/[^a-zA-ZÀ-ÿ0-9\s]/g, '');
}

// =============================================
// SELECTOR DE ROLES
// =============================================

function initializeRoleSelector() {
    const roleOptions = document.querySelectorAll('.role-option:not(#editEvent .role-option)');
    
    roleOptions.forEach(option => {
        option.addEventListener('click', function(e) {
            e.preventDefault();
            const role = this.dataset.value;
            
            if (selectedRoles.has(role)) {
                selectedRoles.delete(role);
                this.classList.remove('selected');
                createDeselectParticles(this);
            } else {
                selectedRoles.add(role);
                this.classList.add('selected');
                createSelectParticles(this);
            }
            
            // Asegurar que siempre haya al menos un rol seleccionado
            if (selectedRoles.size === 0) {
                selectedRoles.add('Estudiante');
                document.querySelector('.role-option[data-value="Estudiante"]').classList.add('selected');
                createSelectParticles(document.querySelector('.role-option[data-value="Estudiante"]'));
            }
            
            updateSelectedRolesDisplay();
            createRippleEffect(e);
        });
        
        // Efectos de hover mejorados
        option.addEventListener('mouseenter', function() {
            if (!this.classList.contains('selected')) {
                this.style.transform = 'translateY(-3px) scale(1.02)';
            }
        });
        
        option.addEventListener('mouseleave', function() {
            if (!this.classList.contains('selected')) {
                this.style.transform = 'translateY(0) scale(1)';
            }
        });
    });
    
    // Inicializar display con el valor por defecto
    updateSelectedRolesDisplay();
    console.log('👥 Selector de roles principal inicializado');
}

function initializeEditRoleSelector() {
    const roleOptions = document.querySelectorAll('#editEvent .role-option');
    
    roleOptions.forEach(option => {
        option.addEventListener('click', function(e) {
            e.preventDefault();
            const role = this.dataset.value;
            
            if (editSelectedRoles.has(role)) {
                editSelectedRoles.delete(role);
                this.classList.remove('selected');
                createDeselectParticles(this);
            } else {
                editSelectedRoles.add(role);
                this.classList.add('selected');
                createSelectParticles(this);
            }
            
            // Asegurar que siempre haya al menos un rol seleccionado
            if (editSelectedRoles.size === 0) {
                editSelectedRoles.add('Estudiante');
                document.querySelector('#editEvent .role-option[data-value="Estudiante"]').classList.add('selected');
                createSelectParticles(document.querySelector('#editEvent .role-option[data-value="Estudiante"]'));
            }
            
            updateEditSelectedRolesDisplay();
            createRippleEffect(e);
        });
        
        // Efectos de hover mejorados
        option.addEventListener('mouseenter', function() {
            if (!this.classList.contains('selected')) {
                this.style.transform = 'translateY(-3px) scale(1.02)';
            }
        });
        
        option.addEventListener('mouseleave', function() {
            if (!this.classList.contains('selected')) {
                this.style.transform = 'translateY(0) scale(1)';
            }
        });
    });
    
    console.log('👥 Selector de roles de edición inicializado');
}

function updateEditRoleSelector() {
    const roleOptions = document.querySelectorAll('#editEvent .role-option');
    
    roleOptions.forEach(option => {
        const role = option.dataset.value;
        if (editSelectedRoles.has(role)) {
            option.classList.add('selected');
        } else {
            option.classList.remove('selected');
        }
    });
    
    updateEditSelectedRolesDisplay();
}

function updateSelectedRolesDisplay() {
    const tagsContainer = document.getElementById('selectedRolesTags');
    tagsContainer.innerHTML = '';
    
    if (selectedRoles.size === 0) {
        const emptyMessage = document.createElement('span');
        emptyMessage.className = 'empty-message';
        emptyMessage.textContent = 'Ningún rol seleccionado';
        emptyMessage.style.color = 'var(--gray)';
        emptyMessage.style.fontStyle = 'italic';
        tagsContainer.appendChild(emptyMessage);
        return;
    }
    
    selectedRoles.forEach(role => {
        const tag = document.createElement('div');
        tag.className = `role-tag ${role.toLowerCase()}`;
        
        const icon = role === 'Estudiante' ? '👨‍🎓' : '👩‍🏫';
        tag.innerHTML = `
            ${icon} ${role}
            <button class="tag-remove" data-role="${role}">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        tagsContainer.appendChild(tag);
    });
    
    // Agregar event listeners para los botones de eliminar
    document.querySelectorAll('.tag-remove').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const role = this.dataset.role;
            
            // No permitir eliminar si es el último rol
            if (selectedRoles.size <= 1) {
                showToast('Debe haber al menos un rol seleccionado', 'warning');
                return;
            }
            
            selectedRoles.delete(role);
            
            // Deseleccionar la opción correspondiente
            const roleOption = document.querySelector(`.role-option[data-value="${role}"]`);
            if (roleOption) {
                roleOption.classList.remove('selected');
                createDeselectParticles(roleOption);
            }
            
            updateSelectedRolesDisplay();
        });
    });
}

function updateEditSelectedRolesDisplay() {
    const tagsContainer = document.getElementById('editSelectedRolesTags');
    tagsContainer.innerHTML = '';
    
    if (editSelectedRoles.size === 0) {
        const emptyMessage = document.createElement('span');
        emptyMessage.className = 'empty-message';
        emptyMessage.textContent = 'Ningún rol seleccionado';
        emptyMessage.style.color = 'var(--gray)';
        emptyMessage.style.fontStyle = 'italic';
        tagsContainer.appendChild(emptyMessage);
        return;
    }
    
    editSelectedRoles.forEach(role => {
        const tag = document.createElement('div');
        tag.className = `role-tag ${role.toLowerCase()}`;
        
        const icon = role === 'Estudiante' ? '👨‍🎓' : '👩‍🏫';
        tag.innerHTML = `
            ${icon} ${role}
            <button class="tag-remove" data-role="${role}">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        tagsContainer.appendChild(tag);
    });
    
    // Agregar event listeners para los botones de eliminar
    document.querySelectorAll('#editEvent .tag-remove').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const role = this.dataset.role;
            
            // No permitir eliminar si es el último rol
            if (editSelectedRoles.size <= 1) {
                showToast('Debe haber al menos un rol seleccionado', 'warning');
                return;
            }
            
            editSelectedRoles.delete(role);
            
            // Deseleccionar la opción correspondiente
            const roleOption = document.querySelector(`#editEvent .role-option[data-value="${role}"]`);
            if (roleOption) {
                roleOption.classList.remove('selected');
                createDeselectParticles(roleOption);
            }
            
            updateEditSelectedRolesDisplay();
        });
    });
}

// =============================================
// EFECTOS VISUALES Y ANIMACIONES
// =============================================

function createSelectParticles(element) {
    const rect = element.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    
    for (let i = 0; i < 8; i++) {
        const particle = document.createElement('div');
        particle.className = 'role-particle';
        
        const angle = (i / 8) * Math.PI * 2;
        const distance = 50 + Math.random() * 30;
        const tx = Math.cos(angle) * distance;
        const ty = Math.sin(angle) * distance;
        
        particle.style.setProperty('--tx', `${tx}px`);
        particle.style.setProperty('--ty', `${ty}px`);
        particle.style.left = `${centerX}px`;
        particle.style.top = `${centerY}px`;
        
        // Color basado en el tipo de rol
        const role = element.dataset.value;
        if (role === 'Estudiante') {
            particle.style.background = 'var(--accent1)';
        } else {
            particle.style.background = 'var(--accent4)';
        }
        
        document.body.appendChild(particle);
        
        setTimeout(() => {
            particle.remove();
        }, 1000);
    }
}

function createDeselectParticles(element) {
    const rect = element.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    
    for (let i = 0; i < 6; i++) {
        const particle = document.createElement('div');
        particle.className = 'role-particle';
        
        const angle = (i / 6) * Math.PI * 2;
        const distance = 30 + Math.random() * 20;
        const tx = Math.cos(angle) * distance;
        const ty = Math.sin(angle) * distance;
        
        particle.style.setProperty('--tx', `${tx}px`);
        particle.style.setProperty('--ty', `${ty}px`);
        particle.style.left = `${centerX}px`;
        particle.style.top = `${centerY}px`;
        particle.style.background = 'var(--gray)';
        
        document.body.appendChild(particle);
        
        setTimeout(() => {
            particle.remove();
        }, 800);
    }
}

function createParticles() {
    const container = document.getElementById('particles-container');
    const particleCount = 15;
    
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = Math.random() * 100 + 'vw';
        particle.style.top = Math.random() * 100 + 'vh';
        particle.style.animationDelay = Math.random() * 6 + 's';
        particle.style.background = getRandomColor();
        container.appendChild(particle);
    }
    
    console.log('✨ Partículas creadas');
}

function getRandomColor() {
    const colors = ['#F95738', '#EE964B', '#F4D35E', '#0D3B66'];
    return colors[Math.floor(Math.random() * colors.length)];
}

function createRippleEffect(event) {
    const ripple = document.createElement('div');
    ripple.style.position = 'absolute';
    ripple.style.borderRadius = '50%';
    ripple.style.background = 'rgba(244, 211, 94, 0.6)';
    ripple.style.transform = 'scale(0)';
    ripple.style.animation = 'ripple 0.6s linear';
    ripple.style.pointerEvents = 'none';
    
    const rect = event.target.getBoundingClientRect();
    ripple.style.left = (event.clientX - rect.left - 5) + 'px';
    ripple.style.top = (event.clientY - rect.top - 5) + 'px';
    ripple.style.width = '10px';
    ripple.style.height = '10px';
    
    event.target.style.position = 'relative';
    event.target.appendChild(ripple);
    
    setTimeout(() => ripple.remove(), 600);
}

function setupNavigationEffects() {
    const navButtons = document.querySelectorAll('.month-nav-btn');
    
    navButtons.forEach(btn => {
        btn.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.15) translateY(-2px)';
        });
        
        btn.addEventListener('mouseleave', function() {
            if (!this.classList.contains('active')) {
                this.style.transform = 'scale(1) translateY(0)';
            }
        });
        
        btn.addEventListener('mousedown', function() {
            this.style.transform = 'scale(1.05) translateY(0)';
        });
        
        btn.addEventListener('mouseup', function() {
            this.style.transform = 'scale(1.15) translateY(-2px)';
        });
    });
}

function setupTooltips() {
    const tooltips = document.querySelectorAll('.btn-tooltip');
    
    tooltips.forEach(tooltip => {
        tooltip.parentElement.addEventListener('mouseenter', function() {
            tooltip.style.opacity = '1';
            tooltip.style.visibility = 'visible';
        });
        
        tooltip.parentElement.addEventListener('mouseleave', function() {
            tooltip.style.opacity = '0';
            tooltip.style.visibility = 'hidden';
        });
    });
}

// =============================================
// FUNCIONALIDAD DEL CALENDARIO
// =============================================

function toggleForm() {
    const formContent = document.getElementById('formContent');
    const toggleBtn = document.getElementById('toggleForm');
    const icon = toggleBtn.querySelector('i');
    
    if (formContent.style.display === 'none' || !formContent.style.display) {
        formContent.style.display = 'block';
        icon.className = 'fas fa-chevron-up';
        showToast('Formulario expandido', 'info');
    } else {
        formContent.style.display = 'none';
        icon.className = 'fas fa-chevron-down';
        showToast('Formulario contraído', 'info');
    }
}

function goToPreviousMonth() {
    const prevBtn = document.getElementById('prevMonth');
    prevBtn.style.animation = 'bounce 0.5s ease';
    
    currentDate.setMonth(currentDate.getMonth() - 1);
    createCalendar();
    showToast('Mes anterior', 'info');
    
    setTimeout(() => {
        prevBtn.style.animation = '';
    }, 500);
}

function goToNextMonth() {
    const nextBtn = document.getElementById('nextMonth');
    nextBtn.style.animation = 'bounce 0.5s ease';
    
    currentDate.setMonth(currentDate.getMonth() + 1);
    createCalendar();
    showToast('Siguiente mes', 'info');
    
    setTimeout(() => {
        nextBtn.style.animation = '';
    }, 500);
}

function createCalendar() {
    const calendar = document.getElementById("calendar");
    calendar.innerHTML = '';
    
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    
    // Actualizar display del mes
    const monthNames = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
    document.getElementById("currentMonth").textContent = `${monthNames[month]} ${year}`;
    
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const today = new Date();

    // Espacios vacíos hasta el primer día
    for (let i = 0; i < firstDay; i++) {
        const empty = document.createElement("div");
        empty.classList.add('day-empty');
        calendar.appendChild(empty);
    }

    // Días del mes
    for (let day = 1; day <= daysInMonth; day++) {
        const dayDiv = document.createElement("div");
        dayDiv.classList.add("day");
        
        const dateStr = `${year}-${String(month+1).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
        dayDiv.dataset.date = dateStr;
        
        // Marcar día actual
        if (today.getDate() === day && 
            today.getMonth() === month && 
            today.getFullYear() === year) {
            dayDiv.classList.add('current-day');
        }
        
        dayDiv.innerHTML = `<strong>${day}</strong><div class="events"></div>`;
        
        // Efecto al hacer click
        dayDiv.addEventListener('click', function(e) {
            if (e.target === this) {
                this.style.animation = 'shake 0.5s ease';
                setTimeout(() => this.style.animation = '', 500);
                
                const dayEvents = events.filter(ev => ev.date === dateStr);
                if (dayEvents.length > 0) {
                    showToast(`Tienes ${dayEvents.length} evento(s) este día`, 'info');
                } else {
                    showToast(`No hay eventos programados para el ${day}`, 'info');
                }
            }
        });
        
        calendar.appendChild(dayDiv);
    }

    renderEvents();
    console.log(`📅 Calendario de ${monthNames[month]} ${year} creado`);
}

// =============================================
// GESTIÓN DE EVENTOS
// =============================================

function getSelectedRoles() {
    return Array.from(selectedRoles);
}

function formatRolesDisplay(roles) {
    if (roles.length === 2) {
        return 'Estudiantes y Profesores';
    } else if (roles.length === 1) {
        return roles[0] === 'Estudiante' ? 'Estudiantes' : 'Profesores';
    } else {
        return roles.join(', ');
    }
}

function getEventClass(roles) {
    if (roles.length === 2) {
        return 'event multiple-roles';
    } else if (roles.includes('Estudiante')) {
        return 'event estudiante';
    } else if (roles.includes('Profesor')) {
        return 'event profesor';
    } else {
        return 'event';
    }
}

function loadEvents() {
    const loadingIndicator = document.getElementById('loading');
    loadingIndicator.style.display = 'block';
    
    // Simular carga con timeout para mostrar la animación
    setTimeout(() => {
        fetch("/admin/eventos")
            .then(r => {
                if (!r.ok) throw new Error("Error al cargar eventos");
                return r.json();
            })
            .then(data => {
                console.log("✅ Eventos recibidos:", data);
                events = data.map(e => ({
                    id: e.IdEvento || e.id,
                    title: e.Nombre || e.nombre,
                    description: e.Descripcion || e.descripcion,
                    date: e.Fecha || e.fecha,
                    time: (e.Hora || e.hora || '').slice(0,5),
                    role: e.RolDestino || e.rol_destino
                }));
                renderEvents();
                loadingIndicator.style.display = 'none';
                showToast(`Se cargaron ${events.length} eventos`, 'success');
            })
            .catch(err => {
                console.error("❌ Error cargando eventos:", err);
                loadingIndicator.style.display = 'none';
                showToast('Error al cargar eventos', 'error');
                // Cargar eventos de ejemplo para desarrollo
                loadSampleEvents();
            });
    }, 1000);
}

function loadSampleEvents() {
    const currentYear = new Date().getFullYear();
    const currentMonth = new Date().getMonth();
    
    events = [
        {
            id: 1,
            title: "Reunión de Padres",
            description: "Reunión general de padres de familia para tratar temas importantes del ciclo escolar",
            date: `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-15`,
            time: "15:00",
            role: "Estudiante"
        },
        {
            id: 2,
            title: "Capacitación Docente",
            description: "Sesión de capacitación sobre nuevas metodologías educativas",
            date: `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-20`,
            time: "09:00",
            role: "Profesor"
        },
        {
            id: 3,
            title: "Feria Científica",
            description: "Exposición de proyectos científicos de los estudiantes",
            date: `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-25`,
            time: "14:00",
            role: "Estudiante,Profesor"
        }
    ];
    
    renderEvents();
    showToast('Eventos de ejemplo cargados', 'warning');
}

function renderEvents() {
    document.querySelectorAll(".day").forEach(dayDiv => {
        const dayEventsDiv = dayDiv.querySelector(".events");
        dayEventsDiv.innerHTML = '';
        const date = dayDiv.dataset.date;

        const dayEvents = events.filter(ev => ev.date === date);
        
        if (dayEvents.length > 0) {
            dayDiv.classList.add('has-events');
        }

        dayEvents.forEach((ev, index) => {
            const evDiv = document.createElement("div");
            // Parsear los roles
            const roles = typeof ev.role === 'string' ? ev.role.split(',') : [ev.role];
            
            evDiv.className = getEventClass(roles);
            evDiv.setAttribute('data-roles', formatRolesDisplay(roles));
            
            // Agregar badges de roles si hay múltiples
            let roleBadges = '';
            if (roles.length > 1) {
                roleBadges = roles.map(role => 
                    `<span class="role-badge">${role === 'Estudiante' ? '👨‍🎓' : '👩‍🏫'}</span>`
                ).join('');
            }
            
            evDiv.innerHTML = `${ev.time} - ${ev.title} ${roleBadges}`;
            evDiv.onclick = (e) => {
                createRippleEffect(e);
                showEventDetails(ev, index);
            };
            
            // Animación de entrada escalonada
            evDiv.style.animation = `fadeIn 0.5s ease ${index * 0.1}s both`;
            dayEventsDiv.appendChild(evDiv);
        });
    });
}

// =============================================
// VALIDACIÓN DE FORMULARIOS
// =============================================

function setupRealTimeValidation() {
    // Validación en tiempo real para el formulario principal
    const inputs = ['title', 'description', 'date', 'time'];
    inputs.forEach(inputId => {
        const input = document.getElementById(inputId);
        if (input) {
            input.addEventListener('blur', validateField);
            input.addEventListener('input', clearFieldError);
        }
    });
    
    // Validación para el formulario de edición
    const editInputs = ['editTitle', 'editDescription', 'editDate', 'editTime'];
    editInputs.forEach(inputId => {
        const input = document.getElementById(inputId);
        if (input) {
            input.addEventListener('blur', validateEditField);
            input.addEventListener('input', clearEditFieldError);
        }
    });
}

function validateField(e) {
    const field = e.target;
    const value = field.value.trim();
    const fieldName = field.previousElementSibling?.textContent || 'Campo';
    
    // Remover errores previos
    clearFieldError(e);
    
    if (!value) {
        showFieldError(field, `${fieldName} es obligatorio`);
        return false;
    }
    
    // Validaciones específicas por campo
    switch(field.id) {
        case 'title':
            if (value.length < 5) {
                showFieldError(field, 'El título debe tener al menos 5 caracteres');
                return false;
            }
            // Validar caracteres especiales
            if (!validateOnlyLettersNumbersSpaces(field, 'title')) {
                return false;
            }
            break;
        case 'description':
            if (value.length < 10) {
                showFieldError(field, 'La descripción debe tener al menos 10 caracteres');
                return false;
            }
            // Validar caracteres especiales
            if (!validateOnlyLettersNumbersSpaces(field, 'description')) {
                return false;
            }
            break;
        case 'date':
            if (!validarFechaFutura(value, document.getElementById('time').value)) {
                showFieldError(field, 'La fecha debe ser futura');
                return false;
            }
            break;
    }
    
    showFieldSuccess(field);
    return true;
}

function validateEditField(e) {
    const field = e.target;
    const value = field.value.trim();
    const fieldName = field.previousElementSibling?.textContent || 'Campo';
    
    // Remover errores previos
    clearEditFieldError(e);
    
    if (!value) {
        showEditFieldError(field, `${fieldName} es obligatorio`);
        return false;
    }
    
    // Validaciones específicas por campo
    switch(field.id) {
        case 'editTitle':
            if (value.length < 5) {
                showEditFieldError(field, 'El título debe tener al menos 5 caracteres');
                return false;
            }
            // Validar caracteres especiales
            if (!validateOnlyLettersNumbersSpaces(field, 'editTitle')) {
                return false;
            }
            break;
        case 'editDescription':
            if (value.length < 10) {
                showEditFieldError(field, 'La descripción debe tener al menos 10 caracteres');
                return false;
            }
            // Validar caracteres especiales
            if (!validateOnlyLettersNumbersSpaces(field, 'editDescription')) {
                return false;
            }
            break;
        case 'editDate':
            if (!validarFechaFutura(value, document.getElementById('editTime').value)) {
                showEditFieldError(field, 'La fecha debe ser futura');
                return false;
            }
            break;
    }
    
    showEditFieldSuccess(field);
    return true;
}

function showFieldError(field, message) {
    field.classList.add('field-error');
    
    let errorDiv = field.parentNode.querySelector('.validation-error');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.className = 'validation-error';
        field.parentNode.appendChild(errorDiv);
    }
    errorDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${message}`;
}

function showEditFieldError(field, message) {
    field.classList.add('field-error');
    
    let errorDiv = field.parentNode.querySelector('.validation-error');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.className = 'validation-error';
        field.parentNode.appendChild(errorDiv);
    }
    errorDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${message}`;
}

function showFieldSuccess(field) {
    field.classList.remove('field-error');
    
    let successDiv = field.parentNode.querySelector('.validation-success');
    if (!successDiv) {
        successDiv = document.createElement('div');
        successDiv.className = 'validation-success';
        field.parentNode.appendChild(successDiv);
    }
    successDiv.innerHTML = `<i class="fas fa-check-circle"></i> Campo válido`;
    
    setTimeout(() => {
        successDiv.remove();
    }, 2000);
}

function showEditFieldSuccess(field) {
    field.classList.remove('field-error');
    
    let successDiv = field.parentNode.querySelector('.validation-success');
    if (!successDiv) {
        successDiv = document.createElement('div');
        successDiv.className = 'validation-success';
        field.parentNode.appendChild(successDiv);
    }
    successDiv.innerHTML = `<i class="fas fa-check-circle"></i> Campo válido`;
    
    setTimeout(() => {
        successDiv.remove();
    }, 2000);
}

function clearFieldError(e) {
    const field = e.target;
    field.classList.remove('field-error');
    
    const errorDiv = field.parentNode.querySelector('.validation-error');
    if (errorDiv) {
        errorDiv.remove();
    }
    
    const successDiv = field.parentNode.querySelector('.validation-success');
    if (successDiv) {
        successDiv.remove();
    }
}

function clearEditFieldError(e) {
    const field = e.target;
    field.classList.remove('field-error');
    
    const errorDiv = field.parentNode.querySelector('.validation-error');
    if (errorDiv) {
        errorDiv.remove();
    }
    
    const successDiv = field.parentNode.querySelector('.validation-success');
    if (successDiv) {
        successDiv.remove();
    }
}

function validateForm() {
    const fields = ['title', 'description', 'date', 'time'];
    let isValid = true;
    
    fields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            const event = new Event('blur');
            field.dispatchEvent(event);
            if (field.classList.contains('field-error') || field.classList.contains('character-error')) {
                isValid = false;
            }
        }
    });
    
    // Validar roles
    if (selectedRoles.size === 0) {
        showToast('Debe seleccionar al menos un destinatario', 'error');
        isValid = false;
    }
    
    return isValid;
}

function validateEditForm() {
    const fields = ['editTitle', 'editDescription', 'editDate', 'editTime'];
    let isValid = true;
    
    fields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            const event = new Event('blur');
            field.dispatchEvent(event);
            if (field.classList.contains('field-error') || field.classList.contains('character-error')) {
                isValid = false;
            }
        }
    });
    
    // Validar roles
    if (editSelectedRoles.size === 0) {
        showToast('Debe seleccionar al menos un destinatario', 'error');
        isValid = false;
    }
    
    return isValid;
}

// =============================================
// CREACIÓN Y EDICIÓN DE EVENTOS
// =============================================

function addEvent() {
    const title = document.getElementById("title").value.trim();
    const description = document.getElementById("description").value.trim();
    const date = document.getElementById("date").value;
    const time = document.getElementById("time").value;
    const roles = getSelectedRoles();

    // Validaciones
    if (!validateForm()) {
        showToast("⚠️ Por favor, corrige los errores en el formulario", 'error');
        return;
    }

    // Validar que la fecha no sea del pasado
    if (!validarFechaFutura(date, time)) {
        return;
    }

    // Sanitizar texto antes de enviar (elimina TODO carácter especial)
    const sanitizedTitle = sanitizeText(title);
    const sanitizedDescription = sanitizeText(description);

    // Mostrar indicador de carga
    const submitBtn = document.querySelector('.submit-btn');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creando evento...';
    submitBtn.disabled = true;

    fetch("/admin/eventos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            nombre: sanitizedTitle,
            descripcion: sanitizedDescription,
            fecha: date,
            hora: time,
            rol_destino: roles.join(',')
        })
    })
    .then(async r => {
        const data = await r.json().catch(() => ({}));
        if (!r.ok) {
            throw new Error(data.error || "❌ No se pudo crear el evento");
        }
        return data;
    })
    .then(data => {
        console.log("✅ Evento creado:", data);
        loadEvents();
        
        // Limpiar formulario
        document.getElementById("title").value = '';
        document.getElementById("description").value = '';
        document.getElementById("date").value = '';
        document.getElementById("time").value = '';
        
        // Resetear roles
        selectedRoles = new Set(['Estudiante']);
        updateSelectedRolesDisplay();
        updateRoleSelector();
        
        showToast("🎉 Evento creado con éxito", 'success');
    })
    .catch(err => {
        console.error("❌ Error creando evento:", err);
        showToast("⚠️ No se pudo crear el evento: " + err.message, 'error');
    })
    .finally(() => {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    });
}

function updateRoleSelector() {
    const roleOptions = document.querySelectorAll('.role-option:not(#editEvent .role-option)');
    roleOptions.forEach(option => {
        const role = option.dataset.value;
        if (selectedRoles.has(role)) {
            option.classList.add('selected');
        } else {
            option.classList.remove('selected');
        }
    });
}

function validarFechaFutura(date, time) {
    const ahora = new Date();
    const fechaEvento = new Date(date + 'T' + time);
    
    if (fechaEvento < ahora) {
        showToast("📅 No puedes crear eventos en fechas pasadas", 'error');
        return false;
    }
    
    return true;
}

function updateTimeValidation() {
    const selectedDate = document.getElementById('date').value;
    const today = new Date().toISOString().split('T')[0];
    const timeInput = document.getElementById('time');
    
    if (selectedDate === today) {
        const now = new Date();
        const currentHour = now.getHours().toString().padStart(2, '0');
        const currentMinute = now.getMinutes().toString().padStart(2, '0');
        timeInput.min = `${currentHour}:${currentMinute}`;
    } else {
        timeInput.min = '00:00';
    }
}

function updateEditTimeValidation() {
    const selectedDate = document.getElementById('editDate').value;
    const today = new Date().toISOString().split('T')[0];
    const timeInput = document.getElementById('editTime');
    
    if (selectedDate === today) {
        const now = new Date();
        const currentHour = now.getHours().toString().padStart(2, '0');
        const currentMinute = now.getMinutes().toString().padStart(2, '0');
        timeInput.min = `${currentHour}:${currentMinute}`;
    } else {
        timeInput.min = '00:00';
    }
}

// =============================================
// MODALES Y DETALLES
// =============================================

function showEventDetails(ev, index) {
    selectedEventIndex = index;
    document.getElementById("detailTitle").textContent = ev.title;
    
    // Formatear fecha para mostrar
    const fecha = new Date(ev.date);
    const opciones = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    document.getElementById("detailDate").textContent = fecha.toLocaleDateString('es-ES', opciones);
    
    document.getElementById("detailTime").textContent = ev.time || 'Por definir';
    
    // Mostrar roles en el modal
    const roles = typeof ev.role === 'string' ? ev.role.split(',') : [ev.role];
    document.getElementById("detailRoles").textContent = formatRolesDisplay(roles);
    document.getElementById("detailDescription").textContent = ev.description || 'Sin descripción disponible.';
    
    // Actualizar badge del modal
    const badge = document.getElementById("detailBadge");
    if (roles.length === 2) {
        badge.textContent = '👥 Ambos';
        badge.style.background = 'linear-gradient(135deg, var(--accent2), var(--accent3))';
    } else if (roles.includes('Estudiante')) {
        badge.textContent = '👨‍🎓 Estudiantes';
        badge.style.background = 'linear-gradient(135deg, var(--accent1), #ff7a5a)';
    } else {
        badge.textContent = '👩‍🏫 Profesores';
        badge.style.background = 'linear-gradient(135deg, var(--accent4), #2a5a8c)';
    }
    
    // Mostrar modal con animación
    const modal = document.getElementById("eventDetails");
    modal.style.display = "flex";
}

function closeModal() {
    const modal = document.getElementById("eventDetails");
    const modalContent = modal.querySelector('.modal-content');
    modalContent.style.animation = 'modalSlideIn 0.3s ease reverse';
    
    setTimeout(() => {
        modal.style.display = "none";
        modalContent.style.animation = '';
        selectedEventIndex = null;
    }, 300);
}

function openEditModal(event) {
    editingEventId = event.id;
    
    // Llenar el formulario con los datos actuales del evento
    document.getElementById("editTitle").value = event.title;
    document.getElementById("editDescription").value = event.description;
    document.getElementById("editDate").value = event.date;
    document.getElementById("editTime").value = event.time;
    
    // Configurar roles seleccionados
    const roles = typeof event.role === 'string' ? event.role.split(',') : [event.role];
    editSelectedRoles = new Set(roles);
    
    // Actualizar la UI de roles
    updateEditRoleSelector();
    
    // Cerrar el modal de detalles
    closeModal();
    
    // Mostrar el modal de edición
    const modal = document.getElementById("editEvent");
    modal.style.display = "flex";
}

function closeEditModal() {
    const modal = document.getElementById("editEvent");
    const modalContent = modal.querySelector('.modal-content');
    modalContent.style.animation = 'modalSlideIn 0.3s ease reverse';
    
    setTimeout(() => {
        modal.style.display = "none";
        modalContent.style.animation = '';
        editingEventId = null;
        editSelectedRoles.clear();
    }, 300);
}

function saveEditedEvent() {
    const title = document.getElementById("editTitle").value.trim();
    const description = document.getElementById("editDescription").value.trim();
    const date = document.getElementById("editDate").value;
    const time = document.getElementById("editTime").value;
    const roles = Array.from(editSelectedRoles);

    // Validaciones
    if (!validateEditForm()) {
        showToast("⚠️ Por favor, corrige los errores en el formulario", 'error');
        return;
    }

    // Validar que la fecha no sea del pasado
    if (!validarFechaFutura(date, time)) {
        return;
    }

    // Sanitizar texto antes de enviar (elimina TODO carácter especial)
    const sanitizedTitle = sanitizeText(title);
    const sanitizedDescription = sanitizeText(description);

    // Mostrar indicador de carga
    const saveBtn = document.getElementById('saveEditBtn');
    const originalText = saveBtn.innerHTML;
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
    saveBtn.disabled = true;

    fetch(`/admin/eventos/${editingEventId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            nombre: sanitizedTitle,
            descripcion: sanitizedDescription,
            fecha: date,
            hora: time,
            rol_destino: roles.join(',')
        })
    })
    .then(async r => {
        const data = await r.json().catch(() => ({}));
        if (!r.ok) {
            throw new Error(data.error || "❌ No se pudo actualizar el evento");
        }
        return data;
    })
    .then(data => {
        console.log("✅ Evento actualizado:", data);
        loadEvents();
        closeEditModal();
        showToast("🎉 Evento actualizado con éxito", 'success');
    })
    .catch(err => {
        console.error("❌ Error actualizando evento:", err);
        showToast("⚠️ No se pudo actualizar el evento: " + err.message, 'error');
    })
    .finally(() => {
        saveBtn.innerHTML = originalText;
        saveBtn.disabled = false;
    });
}

function deleteEvent(id) {
    if (!confirm('¿Está seguro de que desea eliminar este evento? Esta acción no se puede deshacer.')) {
        return;
    }

    const deleteBtn = document.getElementById("deleteBtn");
    const originalText = deleteBtn.innerHTML;
    deleteBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Eliminando...';
    deleteBtn.disabled = true;

    fetch(`/admin/eventos/${id}`, { method: "DELETE" })
        .then(r => {
            if (!r.ok) throw new Error("Error al eliminar");
            return r.json();
        })
        .then(data => {
            console.log("✅ Evento eliminado:", data);
            closeModal();
            loadEvents();
            showToast("🗑️ Evento eliminado correctamente", 'success');
        })
        .catch(err => {
            console.error("❌ Error eliminando evento:", err);
            showToast("⚠️ No se pudo eliminar el evento", 'error');
        })
        .finally(() => {
            deleteBtn.innerHTML = originalText;
            deleteBtn.disabled = false;
        });
}

// =============================================
// NOTIFICACIONES Y UTILIDADES
// =============================================

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    
    // Icono según el tipo
    let icon = 'fas fa-info-circle';
    if (type === 'success') icon = 'fas fa-check-circle';
    if (type === 'error') icon = 'fas fa-exclamation-circle';
    if (type === 'warning') icon = 'fas fa-exclamation-triangle';
    
    toast.innerHTML = `<i class="${icon}"></i> ${message}`;
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 4000);
}

// =============================================
// EXPORTACIÓN DE FUNCIONES GLOBALES
// =============================================

window.addEvent = addEvent;
window.closeModal = closeModal;
window.closeEditModal = closeEditModal;
window.validateForm = validateForm;

console.log('🎉 Calendario de eventos cargado correctamente');

// Manejo de errores global
window.addEventListener('error', function(e) {
    console.error('❌ Error global:', e.error);
    showToast('Ha ocurrido un error inesperado', 'error');
});

// Exportar para pruebas
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        events,
        currentDate,
        selectedRoles,
        editSelectedRoles,
        initializeCalendar,
        createCalendar,
        validateForm,
        validateEditForm,
        getSelectedRoles,
        formatRolesDisplay,
        getEventClass,
        validateOnlyLettersNumbersSpaces,
        sanitizeText
    };
}