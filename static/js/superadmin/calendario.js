// calendario.js - Script completo con validación de un evento por día

let events = [];
let currentDate = new Date();
let selectedEventIndex = null;
let selectedRoles = new Set(['Estudiante']); // Valor por defecto, ahora solo uno
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
    
    // Configurar hora máxima para AM (11:59 AM)
    document.getElementById('time').max = '11:59';
    document.getElementById('editTime').max = '11:59';
    
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
    
    // Validación en tiempo real para evitar eventos en la misma fecha
    document.getElementById('date').addEventListener('change', checkDateAvailability);
    
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
        if (editingEventId !== null) {
            const event = events.find(ev => ev.id === editingEventId);
            if (event) {
                openEditModal(event);
            }
        }
    });
    
    // Botón de guardar edición
    document.getElementById('saveEditBtn').addEventListener('click', saveEditedEvent);
    
    // Efectos de hover en botones de navegación
    setupNavigationEffects();
    
    // Botón de eliminar en modal de detalles
    document.getElementById('deleteBtn').addEventListener('click', function() {
        if (editingEventId !== null) {
            deleteEvent(editingEventId);
        }
    });
    
    console.log('🎯 Event listeners configurados');
}

// =============================================
// VALIDACIÓN DE HORARIO AM Y EVENTOS EN MISMA FECHA
// =============================================

function validateTimeRange(time) {
    if (!time) {
        return { isValid: false, message: 'La hora es requerida' };
    }
    
    // Validar que la hora esté en el rango AM (00:00 - 11:59)
    const [hours, minutes] = time.split(':').map(Number);
    
    if (isNaN(hours) || isNaN(minutes)) {
        return { isValid: false, message: 'Formato de hora inválido' };
    }
    
    if (hours < 0 || hours > 11 || minutes < 0 || minutes > 59) {
        return { isValid: false, message: 'La hora debe estar entre 00:00 y 11:59 AM' };
    }
    
    return { isValid: true, message: 'Hora válida' };
}

function checkDateAvailability() {
    const date = document.getElementById("date").value;
    
    if (!date) return { isValid: true, message: '' };
    
    // Buscar si ya existe algún evento en esta fecha
    const existingEvent = events.find(event => event.date === date);
    
    const dateInput = document.getElementById("date");
    
    if (existingEvent) {
        showFieldError(dateInput, `Ya existe un evento programado para el ${formatDateForDisplay(date)}. Solo se permite un evento por día.`);
        return { isValid: false, message: `Ya existe un evento en esta fecha: "${existingEvent.title}"` };
    } else {
        clearFieldError({ target: dateInput });
        return { isValid: true, message: 'Fecha disponible' };
    }
}

function checkEditDateAvailability() {
    const date = document.getElementById("editDate").value;
    
    if (!date || !editingEventId) return { isValid: true, message: '' };
    
    // Buscar si ya existe algún evento en esta fecha (excluyendo el actual)
    const existingEvent = events.find(event => 
        event.id !== editingEventId &&
        event.date === date
    );
    
    const dateInput = document.getElementById("editDate");
    
    if (existingEvent) {
        showEditFieldError(dateInput, `Ya existe un evento programado para el ${formatDateForDisplay(date)}. Solo se permite un evento por día.`);
        return { isValid: false, message: `Ya existe un evento en esta fecha: "${existingEvent.title}"` };
    } else {
        clearEditFieldError({ target: dateInput });
        return { isValid: true, message: 'Fecha disponible' };
    }
}

function checkDuplicateEvent() {
    const title = document.getElementById("title").value.trim();
    const date = document.getElementById("date").value;
    
    if (!title || !date) return { isValid: true, message: '' };
    
    // Buscar eventos existentes con el mismo título (para evitar nombres duplicados en general)
    const isDuplicate = events.some(event => 
        event.title.toLowerCase() === title.toLowerCase()
    );
    
    if (isDuplicate) {
        return { isValid: false, message: `Ya existe un evento llamado "${title}". Por favor, usa un nombre diferente.` };
    }
    
    return { isValid: true, message: 'Nombre de evento disponible' };
}

function checkEditDuplicateEvent() {
    const title = document.getElementById("editTitle").value.trim();
    const date = document.getElementById("editDate").value;
    
    if (!title || !date || !editingEventId) return { isValid: true, message: '' };
    
    // Buscar eventos existentes con el mismo título (excluyendo el actual)
    const isDuplicate = events.some(event => 
        event.id !== editingEventId &&
        event.title.toLowerCase() === title.toLowerCase()
    );
    
    if (isDuplicate) {
        return { isValid: false, message: `Ya existe un evento llamado "${title}". Por favor, usa un nombre diferente.` };
    }
    
    return { isValid: true, message: 'Nombre de evento disponible' };
}

function formatDateForDisplay(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('es-ES', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    });
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
    
    if (!value.trim()) {
        return { isValid: false, message: `${fieldName} es requerido` };
    }
    
    // Patrón extremadamente restrictivo: solo letras, números y espacios
    const allowedPattern = /^[a-zA-ZÀ-ÿ0-9\s]*$/;
    
    // Encontrar caracteres no permitidos (cualquier cosa que no sea letra, número o espacio)
    const invalidChars = /[^a-zA-ZÀ-ÿ0-9\s]/g;
    const foundInvalid = value.match(invalidChars);
    const hasInvalid = foundInvalid && foundInvalid.length > 0;
    
    if (hasInvalid) {
        // Mostrar error con los caracteres específicos encontrados
        const uniqueChars = [...new Set(foundInvalid)];
        return { 
            isValid: false, 
            message: `Caracteres no permitidos en ${fieldName.toLowerCase()}: ${uniqueChars.join(', ')}. Solo se permiten letras, números y espacios.` 
        };
    }
    
    if (!allowedPattern.test(value) && value.length > 0) {
        return { isValid: false, message: `Solo se permiten letras, números y espacios en el ${fieldName.toLowerCase()}` };
    }
    
    // Validaciones de longitud específicas
    if (fieldType === 'title' || fieldType === 'editTitle') {
        if (value.length < 5) {
            return { isValid: false, message: 'El título debe tener al menos 5 caracteres' };
        }
        if (value.length > 100) {
            return { isValid: false, message: 'El título no puede tener más de 100 caracteres' };
        }
    }
    
    if (fieldType === 'description' || fieldType === 'editDescription') {
        if (value.length < 10) {
            return { isValid: false, message: 'La descripción debe tener al menos 10 caracteres' };
        }
        if (value.length > 500) {
            return { isValid: false, message: 'La descripción no puede tener más de 500 caracteres' };
        }
    }
    
    return { isValid: true, message: `${fieldName} válido` };
}

function getFieldName(fieldType) {
    const fieldNames = {
        'title': 'Título del evento',
        'description': 'Descripción del evento',
        'editTitle': 'Título del evento',
        'editDescription': 'Descripción del evento',
        'date': 'Fecha del evento',
        'time': 'Hora del evento',
        'editDate': 'Fecha del evento',
        'editTime': 'Hora del evento'
    };
    return fieldNames[fieldType] || 'Campo';
}

function showCharacterError(input, message) {
    input.classList.add('field-error');
    
    let errorDiv = input.parentNode.querySelector('.validation-error');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.className = 'validation-error';
        input.parentNode.appendChild(errorDiv);
    }
    errorDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${message}`;
    
    // Agregar efecto visual de shake
    input.style.animation = 'shake 0.5s ease';
    setTimeout(() => {
        input.style.animation = '';
    }, 500);
}

function clearCharacterError(input) {
    input.classList.remove('field-error');
    
    const errorDiv = input.parentNode.querySelector('.validation-error');
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
// SELECTOR DE ROLES - MODIFICADO PARA UN SOLO ROL
// =============================================

function initializeRoleSelector() {
    const roleOptions = document.querySelectorAll('.role-option:not(#editEvent .role-option)');
    
    roleOptions.forEach(option => {
        option.addEventListener('click', function(e) {
            e.preventDefault();
            const role = this.dataset.value;
            
            // Solo permitir un rol seleccionado - limpiar todos primero
            selectedRoles.clear();
            selectedRoles.add(role);
            
            // Actualizar UI - remover selección de todos, agregar al clickeado
            roleOptions.forEach(opt => opt.classList.remove('selected'));
            this.classList.add('selected');
            
            createSelectParticles(this);
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
    console.log('👥 Selector de roles principal inicializado (solo un rol)');
}

function initializeEditRoleSelector() {
    const roleOptions = document.querySelectorAll('#editEvent .role-option');
    
    roleOptions.forEach(option => {
        option.addEventListener('click', function(e) {
            e.preventDefault();
            const role = this.dataset.value;
            
            // Solo permitir un rol seleccionado - limpiar todos primero
            editSelectedRoles.clear();
            editSelectedRoles.add(role);
            
            // Actualizar UI - remover selección de todos, agregar al clickeado
            roleOptions.forEach(opt => opt.classList.remove('selected'));
            this.classList.add('selected');
            
            createSelectParticles(this);
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
    
    console.log('👥 Selector de roles de edición inicializado (solo un rol)');
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
    
    // Solo mostrar un rol (el primero del Set)
    const role = Array.from(selectedRoles)[0];
    const tag = document.createElement('div');
    tag.className = `role-tag ${role.toLowerCase()}`;
    
    const icon = role === 'Estudiante' ? '👨‍🎓' : '👩‍🏫';
    tag.innerHTML = `
        ${icon} ${role}
    `;
    
    tagsContainer.appendChild(tag);
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
    
    // Solo mostrar un rol (el primero del Set)
    const role = Array.from(editSelectedRoles)[0];
    const tag = document.createElement('div');
    tag.className = `role-tag ${role.toLowerCase()}`;
    
    const icon = role === 'Estudiante' ? '👨‍🎓' : '👩‍🏫';
    tag.innerHTML = `
        ${icon} ${role}
    `;
    
    tagsContainer.appendChild(tag);
}

// =============================================
// VALIDACIÓN DE ROLES
// =============================================

function validateRoles() {
    if (selectedRoles.size === 0) {
        return { isValid: false, message: 'Debe seleccionar un destinatario para el evento' };
    }
    return { isValid: true, message: 'Destinatario válido' };
}

function validateEditRoles() {
    if (editSelectedRoles.size === 0) {
        return { isValid: false, message: 'Debe seleccionar un destinatario para el evento' };
    }
    return { isValid: true, message: 'Destinatario válido' };
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
    if (roles.length === 1) {
        return roles[0] === 'Estudiante' ? 'Estudiantes' : 'Profesores';
    } else {
        return roles.join(', ');
    }
}

function getEventClass(roles) {
    if (roles.includes('Estudiante')) {
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
            time: "10:00",
            role: "Estudiante"
        },
        {
            id: 2,
            title: "Capacitación Docente",
            description: "Sesión de capacitación sobre nuevas metodologías educativas",
            date: `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-20`,
            time: "09:00",
            role: "Profesor"
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
            
            evDiv.innerHTML = `${ev.time} - ${ev.title}`;
            evDiv.onclick = (e) => {
                createRippleEffect(e);
                showEventDetails(ev);
            };
            
            // Animación de entrada escalonada
            evDiv.style.animation = `fadeIn 0.5s ease ${index * 0.1}s both`;
            dayEventsDiv.appendChild(evDiv);
        });
    });
}

// =============================================
// VALIDACIÓN DE FORMULARIOS - MEJORADA
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
    const fieldName = getFieldName(field.id);
    
    // Remover errores previos
    clearFieldError(e);
    
    let validationResult = { isValid: true, message: '' };
    
    // Validaciones específicas por campo
    switch(field.id) {
        case 'title':
            if (!value) {
                validationResult = { isValid: false, message: 'El título del evento es requerido' };
            } else {
                validationResult = validateOnlyLettersNumbersSpaces(field, 'title');
                if (validationResult.isValid) {
                    const duplicateCheck = checkDuplicateEvent();
                    if (!duplicateCheck.isValid) {
                        validationResult = duplicateCheck;
                    }
                }
            }
            break;
            
        case 'description':
            if (!value) {
                validationResult = { isValid: false, message: 'La descripción del evento es requerida' };
            } else {
                validationResult = validateOnlyLettersNumbersSpaces(field, 'description');
            }
            break;
            
        case 'date':
            if (!value) {
                validationResult = { isValid: false, message: 'La fecha del evento es requerida' };
            } else {
                const dateAvailability = checkDateAvailability();
                if (!dateAvailability.isValid) {
                    validationResult = dateAvailability;
                } else if (!validarFechaFutura(value, document.getElementById('time').value).isValid) {
                    validationResult = validarFechaFutura(value, document.getElementById('time').value);
                } else {
                    validationResult = { isValid: true, message: 'Fecha disponible' };
                }
            }
            break;
            
        case 'time':
            if (!value) {
                validationResult = { isValid: false, message: 'La hora del evento es requerida' };
            } else {
                validationResult = validateTimeRange(value);
            }
            break;
    }
    
    if (!validationResult.isValid) {
        showFieldError(field, validationResult.message);
    } else {
        showFieldSuccess(field, validationResult.message);
    }
    
    return validationResult.isValid;
}

function validateEditField(e) {
    const field = e.target;
    const value = field.value.trim();
    const fieldName = getFieldName(field.id);
    
    // Remover errores previos
    clearEditFieldError(e);
    
    let validationResult = { isValid: true, message: '' };
    
    // Validaciones específicas por campo
    switch(field.id) {
        case 'editTitle':
            if (!value) {
                validationResult = { isValid: false, message: 'El título del evento es requerido' };
            } else {
                validationResult = validateOnlyLettersNumbersSpaces(field, 'editTitle');
                if (validationResult.isValid) {
                    const duplicateCheck = checkEditDuplicateEvent();
                    if (!duplicateCheck.isValid) {
                        validationResult = duplicateCheck;
                    }
                }
            }
            break;
            
        case 'editDescription':
            if (!value) {
                validationResult = { isValid: false, message: 'La descripción del evento es requerida' };
            } else {
                validationResult = validateOnlyLettersNumbersSpaces(field, 'editDescription');
            }
            break;
            
        case 'editDate':
            if (!value) {
                validationResult = { isValid: false, message: 'La fecha del evento es requerida' };
            } else {
                const dateAvailability = checkEditDateAvailability();
                if (!dateAvailability.isValid) {
                    validationResult = dateAvailability;
                } else if (!validarFechaFutura(value, document.getElementById('editTime').value).isValid) {
                    validationResult = validarFechaFutura(value, document.getElementById('editTime').value);
                } else {
                    validationResult = { isValid: true, message: 'Fecha disponible' };
                }
            }
            break;
            
        case 'editTime':
            if (!value) {
                validationResult = { isValid: false, message: 'La hora del evento es requerida' };
            } else {
                validationResult = validateTimeRange(value);
            }
            break;
    }
    
    if (!validationResult.isValid) {
        showEditFieldError(field, validationResult.message);
    } else {
        showEditFieldSuccess(field, validationResult.message);
    }
    
    return validationResult.isValid;
}

function validarFechaFutura(date, time) {
    if (!date) {
        return { isValid: false, message: 'La fecha es requerida' };
    }
    
    const ahora = new Date();
    const fechaEvento = new Date(date + 'T' + (time || '00:00'));
    
    if (fechaEvento < ahora) {
        return { isValid: false, message: 'No puedes crear eventos en fechas pasadas' };
    }
    
    return { isValid: true, message: 'Fecha válida' };
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

function showFieldSuccess(field, message) {
    field.classList.remove('field-error');
    
    let successDiv = field.parentNode.querySelector('.validation-success');
    if (!successDiv) {
        successDiv = document.createElement('div');
        successDiv.className = 'validation-success';
        field.parentNode.appendChild(successDiv);
    }
    successDiv.innerHTML = `<i class="fas fa-check-circle"></i> ${message}`;
    
    setTimeout(() => {
        successDiv.remove();
    }, 3000);
}

function showEditFieldSuccess(field, message) {
    field.classList.remove('field-error');
    
    let successDiv = field.parentNode.querySelector('.validation-success');
    if (!successDiv) {
        successDiv = document.createElement('div');
        successDiv.className = 'validation-success';
        field.parentNode.appendChild(successDiv);
    }
    successDiv.innerHTML = `<i class="fas fa-check-circle"></i> ${message}`;
    
    setTimeout(() => {
        successDiv.remove();
    }, 3000);
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
    const fields = [
        { id: 'title', name: 'Título del evento' },
        { id: 'description', name: 'Descripción del evento' },
        { id: 'date', name: 'Fecha del evento' },
        { id: 'time', name: 'Hora del evento' }
    ];
    
    let isValid = true;
    let errorMessages = [];
    
    // Validar campos individuales
    fields.forEach(field => {
        const input = document.getElementById(field.id);
        if (input) {
            const event = new Event('blur');
            input.dispatchEvent(event);
            if (input.classList.contains('field-error')) {
                isValid = false;
                errorMessages.push(field.name);
            }
        }
    });
    
    // Validar roles
    const rolesValidation = validateRoles();
    if (!rolesValidation.isValid) {
        isValid = false;
        showToast(rolesValidation.message, 'error');
    }
    
    // Mostrar mensaje específico si hay errores
    if (!isValid && errorMessages.length > 0) {
        showToast(`Por favor corrige los siguientes campos: ${errorMessages.join(', ')}`, 'error');
    }
    
    return isValid;
}

function validateEditForm() {
    const fields = [
        { id: 'editTitle', name: 'Título del evento' },
        { id: 'editDescription', name: 'Descripción del evento' },
        { id: 'editDate', name: 'Fecha del evento' },
        { id: 'editTime', name: 'Hora del evento' }
    ];
    
    let isValid = true;
    let errorMessages = [];
    
    // Validar campos individuales
    fields.forEach(field => {
        const input = document.getElementById(field.id);
        if (input) {
            const event = new Event('blur');
            input.dispatchEvent(event);
            if (input.classList.contains('field-error')) {
                isValid = false;
                errorMessages.push(field.name);
            }
        }
    });
    
    // Validar roles
    const rolesValidation = validateEditRoles();
    if (!rolesValidation.isValid) {
        isValid = false;
        showToast(rolesValidation.message, 'error');
    }
    
    // Mostrar mensaje específico si hay errores
    if (!isValid && errorMessages.length > 0) {
        showToast(`Por favor corrige los siguientes campos: ${errorMessages.join(', ')}`, 'error');
    }
    
    return isValid;
}

// =============================================
// CREACIÓN Y EDICIÓN DE EVENTOS - CORREGIDO
// =============================================

function addEvent() {
    const title = document.getElementById("title").value.trim();
    const description = document.getElementById("description").value.trim();
    const date = document.getElementById("date").value;
    const time = document.getElementById("time").value;
    const roles = getSelectedRoles();

    console.log("📝 Intentando crear evento...");

    // Validaciones detalladas
    if (!validateForm()) {
        console.log("❌ Validación falló - mostrando errores específicos");
        return;
    }

    // Validaciones adicionales de fecha
    const fechaValidation = validarFechaFutura(date, time);
    if (!fechaValidation.isValid) {
        showToast(fechaValidation.message, 'error');
        return;
    }

    // Validación de disponibilidad de fecha (UN EVENTO POR DÍA)
    const dateAvailability = checkDateAvailability();
    if (!dateAvailability.isValid) {
        showToast(dateAvailability.message, 'error');
        return;
    }

    const timeValidation = validateTimeRange(time);
    if (!timeValidation.isValid) {
        showToast(timeValidation.message, 'error');
        return;
    }

    const duplicateCheck = checkDuplicateEvent();
    if (!duplicateCheck.isValid) {
        showToast(duplicateCheck.message, 'error');
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
            throw new Error(data.error || "No se pudo crear el evento");
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
        showToast(`❌ Error al crear evento: ${err.message}`, 'error');
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
    
    // Siempre mantener máximo en 11:59 AM
    timeInput.max = '11:59';
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
    
    // Siempre mantener máximo en 11:59 AM
    timeInput.max = '11:59';
}

// =============================================
// MODALES Y DETALLES - CORREGIDO
// =============================================

function showEventDetails(ev) {
    console.log("🔍 Mostrando detalles del evento:", ev);
    
    // Guardar el ID real del evento para edición
    editingEventId = ev.id;
    
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
    if (roles.includes('Estudiante')) {
        badge.textContent = '👨‍🎓 Estudiantes';
        badge.style.background = 'linear-gradient(135deg, var(--accent1), #ff7a5a)';
    } else {
        badge.textContent = '👩‍🏫 Profesores';
        badge.style.background = 'linear-gradient(135deg, var(--accent4), #2a5a8c)';
    }
    
    // Mostrar modal con animación
    const modal = document.getElementById("eventDetails");
    modal.style.display = "flex";
    
    console.log("✅ Evento seleccionado para edición - ID:", editingEventId, "Título:", ev.title);
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
    console.log("✏️ Abriendo modal de edición para evento:", event);
    
    // Usar el evento que se pasa como parámetro
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
    
    console.log("✅ Formulario de edición listo para evento ID:", editingEventId);
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
    if (!editingEventId) {
        showToast("❌ No se ha seleccionado ningún evento para editar", 'error');
        return;
    }

    const title = document.getElementById("editTitle").value.trim();
    const description = document.getElementById("editDescription").value.trim();
    const date = document.getElementById("editDate").value;
    const time = document.getElementById("editTime").value;
    const roles = Array.from(editSelectedRoles);

    console.log("💾 Guardando cambios para evento ID:", editingEventId);

    // Validaciones detalladas
    if (!validateEditForm()) {
        console.log("❌ Validación de edición falló - mostrando errores específicos");
        return;
    }

    // Validaciones adicionales de fecha
    const fechaValidation = validarFechaFutura(date, time);
    if (!fechaValidation.isValid) {
        showToast(fechaValidation.message, 'error');
        return;
    }

    // Validación de disponibilidad de fecha (UN EVENTO POR DÍA)
    const dateAvailability = checkEditDateAvailability();
    if (!dateAvailability.isValid) {
        showToast(dateAvailability.message, 'error');
        return;
    }

    const timeValidation = validateTimeRange(time);
    if (!timeValidation.isValid) {
        showToast(timeValidation.message, 'error');
        return;
    }

    const duplicateCheck = checkEditDuplicateEvent();
    if (!duplicateCheck.isValid) {
        showToast(duplicateCheck.message, 'error');
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
            throw new Error(data.error || "No se pudo actualizar el evento");
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
        showToast(`❌ Error al actualizar evento: ${err.message}`, 'error');
    })
    .finally(() => {
        saveBtn.innerHTML = originalText;
        saveBtn.disabled = false;
    });
}

function deleteEvent(id) {
    if (!id) {
        showToast("❌ No se ha seleccionado ningún evento para eliminar", 'error');
        return;
    }

    if (!confirm('¿Está seguro de que desea eliminar este evento? Esta acción no se puede deshacer.')) {
        return;
    }

    const deleteBtn = document.getElementById("deleteBtn");
    const originalText = deleteBtn.innerHTML;
    deleteBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Eliminando...';
    deleteBtn.disabled = true;

    console.log("🗑️ Eliminando evento ID:", id);

    fetch(`/admin/eventos/${id}`, { method: "DELETE" })
        .then(r => {
            if (!r.ok) throw new Error("Error al eliminar el evento");
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
            showToast("❌ No se pudo eliminar el evento", 'error');
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
    }, 5000);
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