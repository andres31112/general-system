// static/js/superadmin/padres.js
document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.getElementById('padres-table-body');
    const searchBar = document.querySelector('.search-bar input[type="search"]');

    function renderTable(padres) {
        tableBody.innerHTML = '';

        if (padres.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="5" class="text-center">No se encontraron padres.</td></tr>`;
            return;
        }

        padres.forEach(padre => {
            const row = document.createElement('tr');
            const estadoClase = padre.estado_cuenta === 'activa' ? 'badge-success' : 'badge-danger';
            const estadoTexto = padre.estado_cuenta === 'activa' ? 'Activa' : 'Inactiva';
            const hijosAsignados = padre.hijos_asignados && padre.hijos_asignados.length > 0 ? padre.hijos_asignados.join(', ') : 'N/A';

            row.innerHTML = `
                <td>${padre.no_identidad}</td>
                <td>${padre.nombre_completo}</td>
                <td>${padre.correo}</td>
                <td>${hijosAsignados}</td>
                <td><span class="badge ${estadoClase}">${estadoTexto}</span></td>
            `;
            tableBody.appendChild(row);
        });
    }

    async function fetchData(query = '') {
        try {
            const response = await fetch(`/admin/api/padres?q=${query}`);
            const data = await response.json();
            if (response.ok) {
                renderTable(data.data);
            } else {
                console.error('Error al obtener datos de la API:', data.error);
                tableBody.innerHTML = `<tr><td colspan="5">Error al cargar los datos. Intente de nuevo más tarde.</td></tr>`;
            }
        } catch (error) {
            console.error('Error de red o del servidor:', error);
            tableBody.innerHTML = `<tr><td colspan="5">No se pudo conectar con el servidor.</td></tr>`;
        }
    }

    fetchData();

    searchBar.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        fetchData(query);
    });
});