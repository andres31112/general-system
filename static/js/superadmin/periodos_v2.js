// VERSIÓN SUPER SIMPLIFICADA - DEBUG
console.log('=== ARCHIVO CARGADO ===');

let ciclos = [];
let periodos = {};

// CARGAR CICLOS
async function cargarCiclos() {
    console.log('1. Iniciando cargarCiclos()');
    const container = document.getElementById('ciclosContainer');
    
    try {
        console.log('2. Haciendo fetch a /admin/api/ciclos');
        const response = await fetch('/admin/api/ciclos');
        console.log('3. Response recibido:', response.status);
        
        const data = await response.json();
        console.log('4. Data parseado:', data);
        
        ciclos = data.ciclos || [];
        console.log('5. Ciclos encontrados:', ciclos.length);
        
        // ACTUALIZAR UI
        if (ciclos.length === 0) {
            console.log('6. Mostrando mensaje de "sin ciclos"');
            container.innerHTML = `
                <div class="text-center py-5">
                    <h3>✅ Sistema funcionando!</h3>
                    <p>No hay ciclos académicos registrados</p>
                    <button class="btn btn-primary btn-lg" onclick="crearPrimerCiclo()">
                        Crear Primer Ciclo
                    </button>
                </div>
            `;
        } else {
            console.log('6. Mostrando', ciclos.length, 'ciclos');
            let html = '';
            ciclos.forEach(ciclo => {
                html += `
                    <div class="alert alert-success">
                        <h4>${ciclo.nombre}</h4>
                        <p>${ciclo.fecha_inicio} - ${ciclo.fecha_fin}</p>
                        <p>Estado: ${ciclo.estado}</p>
                    </div>
                `;
            });
            container.innerHTML = html;
        }
        
        console.log('7. UI actualizada exitosamente');
        
    } catch (error) {
        console.error('ERROR:', error);
        container.innerHTML = `
            <div class="alert alert-danger">
                <h4>Error:</h4>
                <p>${error.message}</p>
            </div>
        `;
    }
}

// CREAR CICLO
function crearPrimerCiclo() {
    console.log('Botón clickeado');
    const nombre = prompt('Nombre del ciclo (ej: 2024-2025):');
    if (!nombre) {
        console.log('Usuario canceló');
        return;
    }
    
    const inicio = prompt('Fecha inicio (YYYY-MM-DD):');
    if (!inicio) return;
    
    const fin = prompt('Fecha fin (YYYY-MM-DD):');
    if (!fin) return;
    
    console.log('Creando ciclo:', { nombre, inicio, fin });
    
    fetch('/admin/api/ciclos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            nombre: nombre,
            fecha_inicio: inicio,
            fecha_fin: fin
        })
    })
    .then(r => r.json())
    .then(data => {
        console.log('Respuesta:', data);
        if (data.success) {
            alert('✅ Ciclo creado!');
            cargarCiclos();
        } else {
            alert('❌ Error: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('❌ Error: ' + error.message);
    });
}

// FUNCIÓN GLOBAL PARA ACTUALIZAR
function cargarDatos() {
    console.log('cargarDatos() llamado');
    cargarCiclos();
}

// FUNCIÓN GLOBAL PARA NUEVO CICLO
function mostrarModalNuevoCiclo() {
    console.log('mostrarModalNuevoCiclo() llamado');
    crearPrimerCiclo();
}

// INICIALIZAR
console.log('8. Esperando DOM...');
document.addEventListener('DOMContentLoaded', function() {
    console.log('9. DOM LISTO - Iniciando carga');
    cargarCiclos();
});

console.log('10. Script completado');
