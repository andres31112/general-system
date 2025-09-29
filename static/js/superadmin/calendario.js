let events = [];
let currentUser = { name: "Ana", role: "Estudiante" };
const calendar = document.getElementById("calendar");
let selectedEventIndex = null;

function createCalendar() {
    calendar.innerHTML = '';
    const today = new Date();
    const year = today.getFullYear();
    const month = today.getMonth();
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    for (let i = 0; i < firstDay; i++) {
        const empty = document.createElement("div");
        calendar.appendChild(empty);
    }

    for (let day = 1; day <= daysInMonth; day++) {
        const dayDiv = document.createElement("div");
        dayDiv.classList.add("day");
        dayDiv.dataset.date = `${year}-${String(month+1).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
        dayDiv.innerHTML = `<strong>${day}</strong><div class="events"></div>`;
        calendar.appendChild(dayDiv);
    }

    renderEvents();
}

function loadEvents() {
    fetch("/admin/eventos")   // ✅ cambio aquí
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
        })
        .catch(err => {
            console.error("❌ Error cargando eventos:", err);
            alert("No se pudieron cargar los eventos");
        });
}


function addEvent() {
    const title = document.getElementById("title").value;
    const description = document.getElementById("description").value;
    const date = document.getElementById("date").value;
    const time = document.getElementById("time").value;
    const role = document.getElementById("roleSelect").value;

    if (!title || !description || !date || !time || !role) {
        alert("⚠️ Rellena todos los campos");
        return;
    }

    // ❌ Evitar duplicados en la misma fecha
    if (events.some(ev => ev.date === date)) {
        alert("⚠️ Ya existe un evento en esta fecha");
        return;
    }

    fetch("/admin/eventos", {    // 👈 CORREGIDO
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            nombre: title,
            descripcion: description,
            fecha: date,   // YYYY-MM-DD
            hora: time,    // HH:MM
            rol_destino: role
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
        alert("🎉 Evento agregado con éxito");
    })
    .catch(err => {
        console.error("❌ Error creando evento:", err);
        alert("⚠️ No se pudo crear el evento:\n" + err.message);
    });
}
function renderEvents() {
    document.querySelectorAll(".day").forEach(dayDiv => {
        const dayEventsDiv = dayDiv.querySelector(".events");
        dayEventsDiv.innerHTML = '';
        const date = dayDiv.dataset.date;

        events
            .filter(ev => ev.date === date)   // ✅ ahora muestra TODOS los eventos sin filtrar rol
            .forEach((ev, index) => {
                const evDiv = document.createElement("div");
                evDiv.classList.add("event");
                evDiv.textContent = `${ev.time} - ${ev.title} (${ev.role})`; // ✅ muestro también el rol
                evDiv.onclick = () => showEventDetails(ev, index);
                dayEventsDiv.appendChild(evDiv);
            });
    });
}



function showEventDetails(ev, index) {
    selectedEventIndex = index;
    document.getElementById("detailTitle").textContent = ev.title;
    document.getElementById("detailDate").textContent = `${ev.date} ${ev.time}`;
    document.getElementById("detailDescription").textContent = ev.description;
    document.getElementById("eventDetails").style.display = "block";
    const btn = document.getElementById("deleteBtn");
    btn.onclick = () => deleteEvent(ev.id);
}

function closeModal() {
    document.getElementById("eventDetails").style.display = "none";
}

function deleteEvent(id) {
    fetch(`/admin/eventos/${id}`, { method: "DELETE" })   // 👈 CORREGIDO
        .then(r => {
            if (!r.ok) throw new Error("Error al eliminar");
            return r.json();
        })
        .then(data => {
            console.log("✅ Evento eliminado:", data);
            closeModal();
            loadEvents();
        })
        .catch(err => {
            console.error("❌ Error eliminando evento:", err);
            alert("⚠️ No se pudo eliminar el evento");
        });
}

// Inicializar
createCalendar();
loadEvents();
