let events = [];
let currentDate = new Date();
let selectedEventIndex = null;

// Inicialización cuando el DOM está listo
document.addEventListener('DOMContentLoaded', function() {
    initializeCalendar();
    setupEventListeners();
    loadEvents();
    createParticles();
});

function initializeCalendar() {
    createCalendar();
    
    // Establecer fecha mínima en el input de fecha (hoy)
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('date').min = today;
}

function setupEventListeners() {
    // Navegación entre meses
    document.getElementById('prevMonth').addEventListener('click', goToPreviousMonth);
    document.getElementById('nextMonth').addEventListener('click', goToNextMonth);
    
    // Toggle del formulario
    document.getElementById('toggleForm').addEventListener('click', toggleForm);
    
    // Validación de fecha y hora
    document.getElementById('date').addEventListener('change', updateTimeValidation);
    
    // Selección de roles mejorada
    setupRoleSelection();
    
    // Cerrar modal con ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeModal();
        }
    });
    
    // Cerrar modal haciendo click fuera
    document.getElementById('eventDetails').addEventListener('click', function(e) {
        if (e.target === this) {
            closeModal();
        }
    });
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
}

function getRandomColor() {
    const colors = ['#F95738', '#EE964B', '#F4D35E', '#0D3B66'];
    return colors[Math.floor(Math.random() * colors.length)];
}

function setupRoleSelection() {
    const roleSelect = document.getElementById('roleSelect');
    
    roleSelect.addEventListener('click', function(e) {
        e.preventDefault();
        const option = e.target;
        if (option.tagName === 'OPTION') {
            option.selected = !option.selected;
            highlightSelectedRoles();
            createRippleEffect(e);
        }
    });

    roleSelect.addEventListener('keydown', function(e) {
        if (e.key === ' ') {
            e.preventDefault();
            const focusedOption = document.querySelector('#roleSelect option:focus');
            if (focusedOption) {
                focusedOption.selected = !focusedOption.selected;
                highlightSelectedRoles();
            }
        }
    });
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

function highlightSelectedRoles() {
    const options = document.querySelectorAll('#roleSelect option');
    options.forEach(option => {
        if (option.selected) {
            option.style.background = 'linear-gradient(135deg, var(--accent4), #1a5080)';
            option.style.color = 'var(--white)';
            option.style.fontWeight = '600';
        } else {
            option.style.background = '';
            option.style.color = '';
            option.style.fontWeight = '';
        }
    });
}

function toggleForm() {
    const formContent = document.getElementById('formContent');
    const toggleBtn = document.getElementById('toggleForm');
    const icon = toggleBtn.querySelector('i');
    
    if (formContent.style.display === 'none') {
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
    currentDate.setMonth(currentDate.getMonth() - 1);
    createCalendar();
    showToast('Mes anterior', 'info');
}

function goToNextMonth() {
    currentDate.setMonth(currentDate.getMonth() + 1);
    createCalendar();
    showToast('Siguiente mes', 'info');
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
}

function getSelectedRoles() {
    const roleSelect = document.getElementById('roleSelect');
    const selectedOptions = Array.from(roleSelect.selectedOptions);
    const selectedRoles = selectedOptions.map(option => option.value);
    
    return selectedRoles.length > 0 ? selectedRoles : ['Estudiante'];
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
            });
    }, 1000);
}

function addEvent() {
    const title = document.getElementById("title").value;
    const description = document.getElementById("description").value;
    const date = document.getElementById("date").value;
    const time = document.getElementById("time").value;
    const roles = getSelectedRoles();

    // Validaciones básicas
    if (!title || !description || !date || !time || roles.length === 0) {
        showToast("⚠️ Rellena todos los campos y selecciona al menos un rol", 'error');
        return;
    }

    // Validar que la fecha no sea del pasado
    if (!validarFechaFutura(date, time)) {
        return;
    }

    // Mostrar indicador de carga
    const submitBtn = document.querySelector('.submit-btn');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creando evento...';
    submitBtn.disabled = true;

    fetch("/admin/eventos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            nombre: title,
            descripcion: description,
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
        // Limpiar selección de roles
        const roleSelect = document.getElementById('roleSelect');
        Array.from(roleSelect.options).forEach(option => option.selected = false);
        highlightSelectedRoles();
        
        showToast("🎉 Evento agregado con éxito", 'success');
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

function showEventDetails(ev, index) {
    selectedEventIndex = index;
    document.getElementById("detailTitle").textContent = ev.title;
    document.getElementById("detailDate").textContent = ev.date;
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
    
    // Configurar botón de eliminar
    const deleteBtn = document.getElementById("deleteBtn");
    deleteBtn.onclick = () => deleteEvent(ev.id);
    
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
    }, 300);
}

function deleteEvent(id) {
    if (!confirm('¿Está seguro de que desea eliminar este evento?')) {
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

// Exportar funciones para uso global
window.addEvent = addEvent;
window.closeModal = closeModal;