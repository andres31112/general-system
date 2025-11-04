document.addEventListener("DOMContentLoaded", () => {
    console.log('🚀 Sistema de votación iniciado');
    console.log('👤 Usuario ID:', usuarioId);

    const form = document.getElementById("votacionForm");
    const alertaEstado = document.getElementById("alertaEstado");
    const mensajeEstado = document.getElementById("mensajeEstado");
    const resumenSeleccion = document.getElementById("resumenSeleccion");
    const btnLimpiar = document.getElementById("btnLimpiar");
    const modalConfirmacion = document.getElementById("modalConfirmacion");
    const btnCancelar = document.getElementById("btnCancelar");
    const btnConfirmar = document.getElementById("btnConfirmar");
    const listaConfirmacion = document.getElementById("listaConfirmacion");
    const tiempoRestante = document.getElementById("tiempoRestante");

    let tiempoLimite = null;
    let intervalo = null;

    // Función para verificar estado
    async function verificarEstado() {
        try {
            mostrarAlerta("🔍 Verificando estado de la votación...", "info");
            
            const res = await fetch(`/estudiante/estado/${usuarioId}`);
            const data = await res.json();

            if (data.error) {
                mostrarAlerta("❌ Error: " + data.error, "error");
                return;
            }

            if (data.ya_voto) {
                mostrarAlerta("✅ Ya realizaste tu voto anteriormente.", "success");
                setTimeout(() => window.location.href = "/estudiante/dashboard", 3000);
                return;
            }

            const inicio = parseHorarioString(data.inicio);
            const fin = parseHorarioString(data.fin);
            const ahora = new Date();
            let abierta = false;
            
            if (inicio && fin) {
                abierta = inicio <= fin ? 
                    (ahora >= inicio && ahora <= fin) : 
                    (ahora >= inicio || ahora <= fin);
            }

            if (!abierta) {
                mostrarAlerta(`⏰ La votación está cerrada.\nHorario: ${data.inicio} - ${data.fin}`, "warning");
                setTimeout(() => window.location.href = "/estudiante/dashboard", 3000);
                return;
            }

            // Configurar temporizador
            tiempoLimite = fin;
            intervalo = setInterval(actualizarTiempoRestante, 1000);
            actualizarTiempoRestante();

            mostrarAlerta("✅ La votación está abierta. Puedes proceder a votar.", "success");
            setTimeout(() => {
                alertaEstado.style.display = "none";
                form.style.display = "block";
                cargarCandidatos();
            }, 2000);

        } catch (err) {
            console.error('Error en verificarEstado:', err);
            mostrarAlerta("❌ Error al verificar el estado de la votación.", "error");
        }
    }

    function parseHorarioString(s) {
        if (!s) return null;
        const parts = s.split(":").map(Number);
        const now = new Date();
        return new Date(now.getFullYear(), now.getMonth(), now.getDate(), parts[0] || 0, parts[1] || 0, parts[2] || 0);
    }

    function actualizarTiempoRestante() {
        if (!tiempoLimite) return;
        
        const ahora = new Date();
        const diferencia = tiempoLimite - ahora;
        
        if (diferencia <= 0) {
            clearInterval(intervalo);
            tiempoRestante.textContent = "00:00:00";
            alert("⏰ El tiempo de votación ha finalizado.");
            window.location.href = "/estudiante/dashboard";
            return;
        }
        
        const horas = Math.floor(diferencia / (1000 * 60 * 60));
        const minutos = Math.floor((diferencia % (1000 * 60 * 60)) / (1000 * 60));
        const segundos = Math.floor((diferencia % (1000 * 60)) / 1000);
        
        tiempoRestante.textContent = 
            `${horas.toString().padStart(2, '0')}:${minutos.toString().padStart(2, '0')}:${segundos.toString().padStart(2, '0')}`;
    }

    function mostrarAlerta(mensaje, tipo) {
        alertaEstado.style.display = "block";
        mensajeEstado.textContent = mensaje;
        
        // Reset classes
        alertaEstado.className = "alerta-estado";
        
        // Add type class
        if (tipo === "error") {
            alertaEstado.style.borderLeftColor = "var(--color-rojo)";
            alertaEstado.style.background = "#FFE6E6";
        } else if (tipo === "warning") {
            alertaEstado.style.borderLeftColor = "var(--color-naranja)";
            alertaEstado.style.background = "#FFF3E0";
        } else if (tipo === "success") {
            alertaEstado.style.borderLeftColor = "var(--color-verde)";
            alertaEstado.style.background = "#E8F5E8";
        } else {
            alertaEstado.style.borderLeftColor = "var(--color-azul)";
            alertaEstado.style.background = "var(--color-azul-claro)";
        }
    }

    function cargarCandidatos() {
        console.log('🔄 Cargando candidatos...');
        fetch("/estudiante/candidatos")
            .then(res => res.json())
            .then(data => {
                console.log('✅ Candidatos cargados para:', Object.keys(data));
                renderCandidatos("personero", data.personero || []);
                renderCandidatos("contralor", data.contralor || []);
                renderCandidatos("cabildante", data.cabildante || []);
            })
            .catch(err => {
                console.error("Error cargando candidatos:", err);
                mostrarAlerta("❌ Error al cargar los candidatos.", "error");
            });
    }

    function renderCandidatos(categoria, lista) {
        const contenedor = document.getElementById(`opciones-${categoria}`);
        contenedor.innerHTML = "";

        lista.forEach(c => {
            const fotoURL = `/static/images/candidatos/${c.foto || 'default.png'}`;
            const col = document.createElement("div");
            col.classList.add("col-md-4", "mb-4");
            col.innerHTML = `
                <div class="card h-100 candidate-card" data-categoria="${categoria}" data-id="${c.id}">
                    <img src="${fotoURL}" class="card-img-top" alt="Foto de ${c.nombre}" 
                         onerror="this.src='/static/images/candidatos/default.png'">
                    <div class="card-body text-center">
                        <h5 class="card-title">${c.nombre}</h5>
                        <div class="tarjeton">Tarjetón ${c.tarjeton}</div>
                        <p class="propuesta">${c.propuesta || 'Sin propuesta disponible'}</p>
                        <input class="form-check-input d-none" type="radio" 
                               name="${categoria}" value="${c.id}" id="${categoria}-${c.id}">
                    </div>
                </div>
            `;
            contenedor.appendChild(col);
        });

        // Voto en blanco
        const blanco = document.createElement("div");
        blanco.classList.add("col-12", "text-center", "mb-3");
        blanco.innerHTML = `
            <div class="card candidate-card" data-categoria="${categoria}" data-id="blanco">
                <div class="card-body">
                    <h5>Voto en Blanco</h5>
                    <input class="form-check-input d-none" type="radio" 
                           name="${categoria}" value="blanco" id="${categoria}-blanco">
                </div>
            </div>
        `;
        contenedor.appendChild(blanco);

        // Agregar event listeners
        contenedor.querySelectorAll(".candidate-card").forEach(card => {
            card.addEventListener("click", () => {
                const categoria = card.dataset.categoria;
                
                // Remover selección anterior en esta categoría
                contenedor.querySelectorAll(".candidate-card").forEach(c => {
                    c.classList.remove("selected-card");
                });
                
                // Seleccionar nueva tarjeta
                card.classList.add("selected-card");
                const input = card.querySelector("input[type=radio]");
                if (input) input.checked = true;
                
                // Actualizar resumen
                actualizarResumen();
            });
        });
    }

    function actualizarResumen() {
        const categorias = ["personero", "contralor", "cabildante"];
        let algunaSeleccionada = false;

        categorias.forEach(cat => {
            const checked = form.querySelector(`input[name="${cat}"]:checked`);
            const elementoResumen = document.getElementById(`resumen-${cat}`);
            
            if (checked) {
                algunaSeleccionada = true;
                if (checked.value === "blanco") {
                    elementoResumen.textContent = "Voto en Blanco";
                    elementoResumen.style.color = "var(--color-gris-oscuro)";
                } else {
                    const card = checked.closest(".candidate-card");
                    const nombre = card.querySelector(".card-title").textContent;
                    elementoResumen.textContent = nombre;
                    elementoResumen.style.color = "var(--color-azul)";
                }
            } else {
                elementoResumen.textContent = "No seleccionado";
                elementoResumen.style.color = "var(--color-gris-oscuro)";
            }
        });

        // Mostrar/ocultar resumen
        if (algunaSeleccionada) {
            resumenSeleccion.style.display = "block";
        } else {
            resumenSeleccion.style.display = "none";
        }
    }

    function limpiarSeleccion() {
        form.querySelectorAll("input[type=radio]").forEach(input => {
            input.checked = false;
        });
        
        form.querySelectorAll(".candidate-card").forEach(card => {
            card.classList.remove("selected-card");
        });
        
        resumenSeleccion.style.display = "none";
    }

    function mostrarModalConfirmacion() {
        const categorias = ["personero", "contralor", "cabildante"];
        listaConfirmacion.innerHTML = "";

        categorias.forEach(cat => {
            const checked = form.querySelector(`input[name="${cat}"]:checked`);
            const li = document.createElement("li");
            
            if (checked) {
                if (checked.value === "blanco") {
                    li.textContent = `${cat.charAt(0).toUpperCase() + cat.slice(1)}: Voto en Blanco`;
                } else {
                    const card = checked.closest(".candidate-card");
                    const nombre = card.querySelector(".card-title").textContent;
                    li.textContent = `${cat.charAt(0).toUpperCase() + cat.slice(1)}: ${nombre}`;
                }
            } else {
                li.textContent = `${cat.charAt(0).toUpperCase() + cat.slice(1)}: No seleccionado`;
                li.style.color = "var(--color-rojo)";
            }
            
            listaConfirmacion.appendChild(li);
        });

        modalConfirmacion.style.display = "flex";
    }

    function ocultarModalConfirmacion() {
        modalConfirmacion.style.display = "none";
    }

    async function enviarVoto() {
        const categorias = ["personero", "contralor", "cabildante"];
        const votos = {};

        // Validar selección en cada categoría
        for (const cat of categorias) {
            const checked = form.querySelector(`input[name="${cat}"]:checked`);
            if (!checked) {
                mostrarAlerta(`⚠️ Debes seleccionar una opción en ${cat}.`, "warning");
                ocultarModalConfirmacion();
                return;
            }
            votos[cat] = checked.value;
        }

        try {
            form.classList.add("loading");
            btnConfirmar.disabled = true;
            btnConfirmar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enviando...';

            const datosEnvio = {
                estudiante_id: parseInt(usuarioId),
                votos: votos
            };

            console.log('📤 Enviando voto:', datosEnvio);

            const res = await fetch("/estudiante/votar", {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(datosEnvio)
            });

            const resp = await res.json();

            if (resp.error) {
                mostrarAlerta("❌ " + resp.error, "error");
                return;
            }

            if (resp.mensaje) {
                mostrarAlerta("✅ " + resp.mensaje, "success");
                setTimeout(() => window.location.href = "/estudiante/dashboard", 2000);
                return;
            }

            mostrarAlerta("⚠️ Respuesta inesperada del servidor.", "warning");
            
        } catch (err) {
            console.error('Error al enviar voto:', err);
            mostrarAlerta("❌ Error al registrar tu voto.", "error");
        } finally {
            form.classList.remove("loading");
            btnConfirmar.disabled = false;
            btnConfirmar.innerHTML = '<i class="fas fa-check"></i> Confirmar Voto';
            ocultarModalConfirmacion();
        }
    }

    // Event Listeners
    btnLimpiar.addEventListener("click", limpiarSeleccion);
    
    form.addEventListener("submit", (e) => {
        e.preventDefault();
        mostrarModalConfirmacion();
    });

    btnCancelar.addEventListener("click", ocultarModalConfirmacion);
    btnConfirmar.addEventListener("click", enviarVoto);

    // Cerrar modal al hacer clic fuera
    modalConfirmacion.addEventListener("click", (e) => {
        if (e.target === modalConfirmacion) {
            ocultarModalConfirmacion();
        }
    });

    // Iniciar verificación
    verificarEstado();
});