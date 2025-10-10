document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("votacionForm");
    const loadingSpinner = document.getElementById("loadingSpinner");
    const btnLimpiar = document.getElementById("btnLimpiar");
    const confirmModal = new bootstrap.Modal(document.getElementById('confirmModal'));
    const btnConfirmarVoto = document.getElementById('confirmarVoto');
    let votosSeleccionados = {};

    // Inicializar resumen
    actualizarResumen();

    function parseHorarioString(s) {
        if (!s) return null;
        const parts = s.split(":").map(Number);
        const now = new Date();
        return new Date(now.getFullYear(), now.getMonth(), now.getDate(), parts[0] || 0, parts[1] || 0, parts[2] || 0);
    }

    async function verificarEstado() {
        try {
            mostrarLoading(true);
            console.log('🔍 Verificando estado para usuario:', usuarioId);
            
            const res = await fetch(`/estudiante/estado/${usuarioId}`);
            console.log('📡 Estado - Respuesta HTTP:', res.status, res.statusText);
            
            if (!res.ok) {
                throw new Error(`Error HTTP: ${res.status} - ${res.statusText}`);
            }
            
            const data = await res.json();
            console.log('📦 Estado - Datos recibidos:', data);

            if (data.error) {
                throw new Error(data.error);
            }

            if (data.ya_voto) {
                mostrarError("Ya realizaste tu voto. No puedes votar nuevamente.");
                return;
            }

            const inicio = parseHorarioString(data.inicio);
            const fin = parseHorarioString(data.fin);
            const ahora = new Date();
            let abierta = false;
            
            console.log('⏰ Horarios:', { 
                inicio: data.inicio, 
                fin: data.fin,
                ahora: ahora.toLocaleTimeString() 
            });
            
            if (inicio && fin) {
                abierta = inicio <= fin ? 
                    (ahora >= inicio && ahora <= fin) : 
                    (ahora >= inicio || ahora <= fin);
            }

            console.log('🔓 Votación abierta:', abierta);

            if (!abierta) {
                const mensaje = data.inicio && data.fin ? 
                    `La votación está cerrada.\nHorario: ${data.inicio} - ${data.fin}` :
                    "La votación no está disponible en este momento.";
                mostrarError(mensaje);
                return;
            }

            // Mostrar formulario y cargar candidatos
            mostrarLoading(false);
            form.style.display = "block";
            await cargarCandidatos();

        } catch (err) {
            console.error('❌ Error en verificarEstado:', err);
            mostrarError(err.message || "Error al verificar el estado de la votación.");
        }
    }

    function mostrarLoading(mostrar) {
        if (loadingSpinner) {
            loadingSpinner.style.display = mostrar ? 'block' : 'none';
        }
        if (form && !mostrar) {
            form.style.display = 'block';
        }
    }

    function mostrarError(mensaje) {
        // Crear alerta personalizada en lugar de usar alert()
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-danger alert-dismissible fade show';
        alertDiv.style.position = 'fixed';
        alertDiv.style.top = '20px';
        alertDiv.style.left = '50%';
        alertDiv.style.transform = 'translateX(-50%)';
        alertDiv.style.zIndex = '9999';
        alertDiv.style.minWidth = '400px';
        alertDiv.style.textAlign = 'center';
        alertDiv.innerHTML = `
            <i class="fas fa-exclamation-triangle me-2"></i>
            <strong>Error:</strong> ${mensaje}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            <div class="mt-2">
                <button class="btn btn-sm btn-outline-danger" id="reintentarBtn">
                    <i class="fas fa-redo me-1"></i>Reintentar
                </button>
                <button class="btn btn-sm btn-outline-secondary ms-2" id="salirBtn">
                    <i class="fas fa-home me-1"></i>Ir al Dashboard
                </button>
            </div>
        `;
        
        document.body.appendChild(alertDiv);

        // Event listeners para los botones
        document.getElementById('reintentarBtn').addEventListener('click', () => {
            alertDiv.remove();
            verificarEstado();
        });

        document.getElementById('salirBtn').addEventListener('click', () => {
            alertDiv.remove();
            window.location.href = "/estudiante/dashboard";
        });

        // Auto-remover después de 15 segundos
        setTimeout(() => {
            if (alertDiv.parentElement) {
                alertDiv.remove();
            }
        }, 15000);
    }

    async function cargarCandidatos() {
        try {
            console.log('🔍 Iniciando carga de candidatos...');
            
            const res = await fetch("/estudiante/candidatos");
            console.log('📡 Candidatos - Respuesta HTTP:', res.status, res.statusText);
            
            if (!res.ok) {
                throw new Error(`Error del servidor: ${res.status} ${res.statusText}`);
            }
            
            const data = await res.json();
            console.log('📦 Candidatos - Datos recibidos:', data);
            
            // Validar estructura de datos
            if (!data || typeof data !== 'object') {
                throw new Error("Formato de datos inválido del servidor");
            }
            
            // Verificar cada categoría
            const categorias = ['personero', 'contralor', 'cabildante'];
            let totalCandidatos = 0;
            
            categorias.forEach(cat => {
                const candidatos = data[cat] || [];
                console.log(`👥 ${cat}:`, candidatos.length, 'candidatos');
                totalCandidatos += candidatos.length;
                
                // Renderizar cada categoría
                renderCandidatos(cat, candidatos);
            });
            
            console.log(`✅ Candidatos cargados: ${totalCandidatos} total`);
            
            if (totalCandidatos === 0) {
                mostrarNotificacion("ℹ️ No hay candidatos registrados para esta votación", "info");
            } else {
                mostrarNotificacion(`✅ Se cargaron ${totalCandidatos} candidatos`, "success");
            }

        } catch (error) {
            console.error("❌ Error cargando candidatos:", error);
            
            // Renderizar opciones vacías para que el usuario pueda votar en blanco
            renderCandidatos("personero", []);
            renderCandidatos("contralor", []);
            renderCandidatos("cabildante", []);
            
            mostrarNotificacion("⚠️ No se pudieron cargar los candidatos, pero puedes votar en blanco", "warning");
        }
    }

    function renderCandidatos(categoria, lista) {
        const contenedor = document.getElementById(`opciones-${categoria}`);
        if (!contenedor) {
            console.error(`❌ Contenedor no encontrado: opciones-${categoria}`);
            return;
        }

        console.log(`🎨 Renderizando ${categoria}:`, lista.length, 'candidatos');
        contenedor.innerHTML = "";

        // Verificar si hay candidatos
        if (lista.length === 0) {
            const mensaje = document.createElement('div');
            mensaje.className = 'col-12 text-center';
            mensaje.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    No hay candidatos disponibles para ${categoria}
                </div>
            `;
            contenedor.appendChild(mensaje);
        }

        // Renderizar candidatos
        lista.forEach((c, index) => {
            const fotoURL = `/static/images/candidatos/${c.foto || 'default.png'}`;
            const col = document.createElement("div");
            col.classList.add("col-md-6", "col-lg-4");
            col.innerHTML = `
                <div class="card h-100 candidate-card" data-categoria="${categoria}" data-id="${c.id}">
                    <img src="${fotoURL}" class="card-img-top" alt="Foto de ${c.nombre}" 
                         onerror="this.onerror=null; this.src='/static/images/candidatos/default.png'">
                    <div class="card-body text-center">
                        <h5 class="card-title">${c.nombre || 'Nombre no disponible'}</h5>
                        <span class="tarjeton">Tarjetón ${c.tarjeton || 'N/A'}</span>
                        <p class="card-text">${c.propuesta || 'Sin propuesta disponible'}</p>
                        <input class="form-check-input d-none" type="radio" 
                               name="${categoria}" value="${c.id}" id="${categoria}-${c.id}">
                    </div>
                </div>
            `;
            contenedor.appendChild(col);
            console.log(`   ✅ Candidato ${index + 1}: ${c.nombre}`);
        });

        // Voto en blanco (siempre disponible)
        const blanco = document.createElement("div");
        blanco.classList.add("col-md-6", "col-lg-4");
        blanco.innerHTML = `
            <div class="card h-100 candidate-card" data-categoria="${categoria}" data-id="blanco">
                <div class="card-body text-center d-flex flex-column justify-content-center">
                    <i class="fas fa-file-invoice mb-2" style="font-size: 2rem; color: var(--accent4);"></i>
                    <h5 class="fw-bold">Voto en Blanco</h5>
                    <p class="small text-muted">No seleccionar ningún candidato</p>
                    <input class="form-check-input d-none" type="radio" 
                           name="${categoria}" value="blanco" id="${categoria}-blanco">
                </div>
            </div>
        `;
        contenedor.appendChild(blanco);
        console.log(`   ✅ Voto en blanco agregado para ${categoria}`);

        // Event listeners para las tarjetas
        const cards = contenedor.querySelectorAll(".candidate-card");
        console.log(`   🎯 ${cards.length} tarjetas con event listeners`);
        
        cards.forEach(card => {
            card.addEventListener("click", () => {
                seleccionarCandidato(categoria, card);
            });
        });
    }

    function seleccionarCandidato(categoria, card) {
        const contenedor = card.parentElement.parentElement;
        const cardId = card.dataset.id;
        const cardNombre = cardId === 'blanco' ? 
            'Voto en Blanco' : 
            card.querySelector('.card-title')?.textContent || 'Candidato';
        
        console.log(`🎯 Seleccionado: ${categoria} - ${cardNombre}`);
        
        // Remover selección anterior
        contenedor.querySelectorAll(".candidate-card").forEach(c => {
            c.classList.remove("selected-card");
        });
        
        // Seleccionar nueva tarjeta
        card.classList.add("selected-card");
        const input = card.querySelector("input[type=radio]");
        if (input) input.checked = true;
        
        // Guardar selección
        votosSeleccionados[categoria] = {
            id: cardId,
            nombre: cardNombre
        };
        
        actualizarResumen();
        
        // Mostrar confirmación visual
        mostrarNotificacion(`✅ Seleccionado: ${cardNombre} para ${categoria}`, "success");
    }

    function actualizarResumen() {
        const categorias = ['personero', 'contralor', 'cabildante'];
        
        categorias.forEach(cat => {
            const elemento = document.getElementById(`resumen-${cat}`);
            if (elemento) {
                const valor = elemento.querySelector('.resumen-value');
                
                if (votosSeleccionados[cat]) {
                    valor.textContent = votosSeleccionados[cat].nombre;
                    valor.classList.add('selected');
                } else {
                    valor.textContent = 'No seleccionado';
                    valor.classList.remove('selected');
                }
            }
        });
        
        console.log('📊 Resumen actualizado:', votosSeleccionados);
    }

    function limpiarSeleccion() {
        console.log('🧹 Limpiando selección...');
        
        // Limpiar selecciones visuales
        document.querySelectorAll('.candidate-card').forEach(card => {
            card.classList.remove('selected-card');
        });
        
        // Limpiar inputs
        document.querySelectorAll('input[type="radio"]').forEach(input => {
            input.checked = false;
        });
        
        // Limpiar objeto de votos
        votosSeleccionados = {};
        
        // Actualizar resumen
        actualizarResumen();
        
        // Mostrar confirmación
        mostrarNotificacion('✅ Selección limpiada correctamente', 'success');
    }

    function mostrarNotificacion(mensaje, tipo = 'info') {
        // Crear notificación toast
        const toast = document.createElement('div');
        const iconClass = tipo === 'success' ? 'fa-check-circle' : 
                         tipo === 'warning' ? 'fa-exclamation-triangle' : 
                         tipo === 'danger' ? 'fa-exclamation-circle' : 'fa-info-circle';
        
        toast.className = `alert alert-${tipo} alert-dismissible fade show`;
        toast.style.position = 'fixed';
        toast.style.top = '20px';
        toast.style.right = '20px';
        toast.style.zIndex = '9999';
        toast.style.minWidth = '300px';
        toast.innerHTML = `
            <i class="fas ${iconClass} me-2"></i>
            ${mensaje}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(toast);
        
        // Auto-remover después de 5 segundos
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 5000);
    }

    function mostrarConfirmacion() {
        const votoFinalResumen = document.getElementById('votoFinalResumen');
        let html = '';
        
        Object.keys(votosSeleccionados).forEach(cat => {
            const nombreCategoria = cat.charAt(0).toUpperCase() + cat.slice(1);
            const esBlanco = votosSeleccionados[cat].id === 'blanco';
            
            html += `
                <div class="d-flex justify-content-between mb-2 p-2 bg-light rounded">
                    <strong>${nombreCategoria}:</strong>
                    <span class="${esBlanco ? 'text-muted' : 'text-success fw-bold'}">
                        ${votosSeleccionados[cat].nombre}
                    </span>
                </div>
            `;
        });
        
        votoFinalResumen.innerHTML = html || '<p class="text-muted text-center">No hay selecciones</p>';
        confirmModal.show();
        
        console.log('📋 Mostrando confirmación:', votosSeleccionados);
    }

    async function enviarVoto() {
        try {
            btnConfirmarVoto.disabled = true;
            btnConfirmarVoto.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Enviando...';

            console.log('📤 Enviando voto:', { estudiante_id: usuarioId, votos: votosSeleccionados });

            const res = await fetch("/estudiante/votar", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    estudiante_id: usuarioId, 
                    votos: Object.keys(votosSeleccionados).reduce((acc, cat) => {
                        acc[cat] = votosSeleccionados[cat].id;
                        return acc;
                    }, {})
                })
            });

            console.log('📡 Voto - Respuesta HTTP:', res.status, res.statusText);

            const resp = await res.json();
            console.log('📦 Voto - Respuesta del servidor:', resp);

            if (resp.error) {
                throw new Error(resp.error);
            }

            if (resp.mensaje) {
                mostrarNotificacion('✅ ' + resp.mensaje, 'success');
                confirmModal.hide();
                
                // Redirigir después de 2 segundos
                setTimeout(() => {
                    window.location.href = "/estudiante/dashboard";
                }, 2000);
                
                return;
            }

            throw new Error("Respuesta inesperada del servidor.");

        } catch (err) {
            console.error('❌ Error enviando voto:', err);
            mostrarNotificacion('❌ ' + err.message, 'danger');
        } finally {
            btnConfirmarVoto.disabled = false;
            btnConfirmarVoto.innerHTML = '<i class="fas fa-paper-plane me-2"></i>Confirmar Voto';
        }
    }

    // Event Listeners
    if (btnLimpiar) {
        btnLimpiar.addEventListener("click", limpiarSeleccion);
    } else {
        console.error('❌ Botón limpiar no encontrado');
    }
    
    if (btnConfirmarVoto) {
        btnConfirmarVoto.addEventListener("click", enviarVoto);
    } else {
        console.error('❌ Botón confirmar voto no encontrado');
    }

    if (form) {
        form.addEventListener("submit", (e) => {
            e.preventDefault();
            
            // Validar que todas las categorías tengan selección
            const categorias = ["personero", "contralor", "cabildante"];
            const faltantes = categorias.filter(cat => !votosSeleccionados[cat]);
            
            if (faltantes.length > 0) {
                mostrarNotificacion(`⚠️ Debes seleccionar una opción en: ${faltantes.join(', ')}`, 'warning');
                return;
            }
            
            mostrarConfirmacion();
        });
    } else {
        console.error('❌ Formulario no encontrado');
    }

    // Iniciar verificación
    console.log('🚀 Iniciando aplicación de votación...');
    console.log('👤 Usuario ID:', usuarioId);
    verificarEstado();
});