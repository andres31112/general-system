document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("votacionForm");

    function parseHorarioString(s) {
        if (!s) return null;
        const parts = s.split(":").map(Number);
        const now = new Date();
        return new Date(now.getFullYear(), now.getMonth(), now.getDate(), parts[0] || 0, parts[1] || 0, parts[2] || 0);
    }

    async function verificarEstado() {
        try {
            const res = await fetch(`/estudiante/estado/${usuarioId}`);
            const data = await res.json();

            if (data.error) {
                alert("❌ Error al verificar el estado.");
                window.location.href = "/estudiante/dashboard";
                return;
            }

            if (data.ya_voto) {
                alert("⚠️ Ya realizaste tu voto.");
                window.location.href = "/estudiante/dashboard";
                return;
            }

            const inicio = parseHorarioString(data.inicio);
            const fin = parseHorarioString(data.fin);
            const ahora = new Date();
            let abierta = false;
            if (inicio && fin) {
                abierta = inicio <= fin ? (ahora >= inicio && ahora <= fin) : (ahora >= inicio || ahora <= fin);
            }

            if (!abierta) {
                alert(`⚠️ La votación está cerrada.\nHorario: ${data.inicio} - ${data.fin}`);
                window.location.href = "/estudiante/dashboard";
                return;
            }

            form.style.display = "block";
            cargarCandidatos();

        } catch (err) {
            console.error(err);
            alert("❌ Error al verificar el estado de la votación.");
            window.location.href = "/estudiante/dashboard";
        }
    }

    function cargarCandidatos() {
        fetch("/estudiante/candidatos")
            .then(res => res.json())
            .then(data => {
                renderCandidatos("personero", data.personero || []);
                renderCandidatos("contralor", data.contralor || []);
                renderCandidatos("cabildante", data.cabildante || []);
            });
    }

    function renderCandidatos(categoria, lista) {
        const contenedor = document.getElementById(`opciones-${categoria}`);
        contenedor.innerHTML = "";

        lista.forEach(c => {
            const fotoURL = `/static/images/candidatos/${c.foto || 'default.png'}`;
            const col = document.createElement("div");
            col.classList.add("col-md-4", "mb-3");
            col.innerHTML = `
                <div class="card h-100 candidate-card" data-categoria="${categoria}" data-id="${c.id}">
                    <img src="${fotoURL}" class="card-img-top" alt="Foto de ${c.nombre}">
                    <div class="card-body text-center">
                        <h5 class="card-title">${c.nombre}</h5>
                        <p class="card-text"><strong>Tarjetón:</strong> ${c.tarjeton}</p>
                        <p class="card-text">${c.propuesta || ''}</p>
                        <input class="form-check-input d-none" type="radio" 
                               name="${categoria}" value="${c.id}" id="${categoria}-${c.id}">
                    </div>
                </div>
            `;
            contenedor.appendChild(col);
        });

        // Voto en blanco más pequeño
        const blanco = document.createElement("div");
        blanco.classList.add("col-12", "mb-3");
        blanco.innerHTML = `
            <div class="card h-100 border-secondary candidate-card d-flex justify-content-center align-items-center" 
                 data-categoria="${categoria}" data-id="blanco" style="height: 120px; max-width: 150px; margin: 0 auto;">
                <div class="card-body text-center">
                    <h5 class="fw-bold">Voto en Blanco</h5>
                    <input class="form-check-input d-none" type="radio" 
                           name="${categoria}" value="blanco" id="${categoria}-blanco">
                </div>
            </div>
        `;
        contenedor.appendChild(blanco);

        contenedor.querySelectorAll(".candidate-card").forEach(card => {
            card.addEventListener("click", () => {
                contenedor.querySelectorAll(".candidate-card").forEach(c => c.classList.remove("selected-card"));
                card.classList.add("selected-card");
                const input = card.querySelector("input[type=radio]");
                if (input) input.checked = true;
            });
        });
    }

    // Submit actualizado con validación robusta
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const categorias = ["personero", "contralor", "cabildante"];
        const votos = {};

        // Validar selección en cada categoría
        for (const cat of categorias) {
            const radios = form.querySelectorAll(`input[name="${cat}"]`);
            let seleccionado = false;
            radios.forEach(r => {
                if (r.checked) seleccionado = true;
            });

            if (!seleccionado) {
                alert(`⚠️ Debes seleccionar una opción en ${cat}.`);
                return;
            }

            const checked = form.querySelector(`input[name="${cat}"]:checked`);
            votos[cat] = checked ? checked.value : null;
        }

        // Enviar votos al backend
        try {
            const res = await fetch("/estudiante/votar", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ estudiante_id: usuarioId, votos })
            });

            const resp = await res.json();

            if (resp.error) {
                alert("❌ " + resp.error);
                window.location.href = "/estudiante/dashboard";
                return;
            }

            if (resp.mensaje) {
                alert("✅ " + resp.mensaje);
                window.location.href = "/estudiante/dashboard";
                return;
            }

            alert("Respuesta inesperada del servidor.");
        } catch (err) {
            console.error(err);
            alert("❌ Error al registrar tu voto.");
        }
    });

    verificarEstado();
});
