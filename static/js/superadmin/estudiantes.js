// static/js/estudiantes/directorio.js
document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.getElementById('estudiantes-table-body');
    const searchBar = document.querySelector('.search-bar input[type="search"]');

    // Función para renderizar los datos en la tabla
    function renderTable(estudiantes) {
        tableBody.innerHTML = ''; // Limpiar cualquier contenido previo

        if (estudiantes.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="6" class="text-center">No se encontraron estudiantes.</td></tr>`;
            return;
        }

        estudiantes.forEach(estudiante => {
            const row = document.createElement('tr');

            // Determinar la clase del badge según el estado de la cuenta
            const estadoClase = estudiante.estado_cuenta === 'activa' ? 'badge-success' : 'badge-danger';
            const estadoTexto = estudiante.estado_cuenta === 'activa' ? 'Activa' : 'Inactiva';

            // El avatar es un icono simple, ya que no se tiene la URL de la imagen
            const avatar = `<span class="avatar"><i class="fa-solid fa-user"></i></span>`;

            row.innerHTML = `
                <td>${estudiante.no_identidad}</td>
                <td>${estudiante.nombre_completo}</td>
                <td>${estudiante.correo}</td>
                <td>${estudiante.curso || 'N/A'}</td>
                <td>${estudiante.sede || 'N/A'}</td>
                <td><span class="badge ${estadoClase}">${estadoTexto}</span></td>
            `;
            tableBody.appendChild(row);
        });
    }

    // Función para obtener los datos de la API
    async function fetchEstudiantes() {
        try {
            // ✅ CORRECCIÓN: Usar la URL correcta del blueprint /admin
            const response = await fetch('/admin/api/directorio/estudiantes');
            const data = await response.json();

            if (response.ok) {
                renderTable(data.data);
            } else {
                console.error('Error al obtener datos de la API:', data.error);
                tableBody.innerHTML = `<tr><td colspan="6">Error al cargar los datos. Intente de nuevo más tarde.</td></tr>`;
            }
        } catch (error) {
            console.error('Error de red o del servidor:', error);
            tableBody.innerHTML = `<tr><td colspan="6">No se pudo conectar con el servidor.</td></tr>`;
        }
    }

    // Llamar a la función para cargar los datos al iniciar la página
    fetchEstudiantes();

    // Lógica de búsqueda
    searchBar.addEventListener('input', async (e) => {
        const query = e.target.value.toLowerCase();
        // ✅ CORRECCIÓN: Usar la URL correcta del blueprint /admin
        try {
            const response = await fetch(`/admin/api/directorio/estudiantes?q=${query}`);
            const data = await response.json();
            if (response.ok) {
                renderTable(data.data);
            } else {
                console.error('Error en la búsqueda:', data.error);
            }
        } catch (error) {
            console.error('Error de red durante la búsqueda:', error);
        }
    });
});