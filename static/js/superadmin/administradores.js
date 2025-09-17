// static/js/superadmin/superadmins.js
document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.getElementById('superadmins-table-body');
    const searchBar = document.querySelector('.search-bar input[type="search"]');

    function renderTable(superadmins) {
        tableBody.innerHTML = '';

        if (superadmins.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="4" class="text-center">No se encontraron superadmins.</td></tr>`;
            return;
        }

        superadmins.forEach(superadmin => {
            const row = document.createElement('tr');
            const estadoClase = superadmin.estado_cuenta === 'activa' ? 'badge-success' : 'badge-danger';
            const estadoTexto = superadmin.estado_cuenta === 'activa' ? 'Activa' : 'Inactiva';

            row.innerHTML = `
                <td>${superadmin.no_identidad}</td>
                <td>${superadmin.nombre_completo}</td>
                <td>${superadmin.correo}</td>
                <td><span class="badge ${estadoClase}">${estadoTexto}</span></td>
            `;
            tableBody.appendChild(row);
        });
    }

    async function fetchData(query = '') {
        try {
            const response = await fetch(`/admin/api/superadmins?q=${query}`);
            const data = await response.json();
            if (response.ok) {
                renderTable(data.data);
            } else {
                console.error('Error al obtener datos de la API:', data.error);
                tableBody.innerHTML = `<tr><td colspan="4">Error al cargar los datos. Intente de nuevo más tarde.</td></tr>`;
            }
        } catch (error) {
            console.error('Error de red o del servidor:', error);
            tableBody.innerHTML = `<tr><td colspan="4">No se pudo conectar con el servidor.</td></tr>`;
        }
    }

    fetchData();

    searchBar.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        fetchData(query);
    });
});