
    document.addEventListener('DOMContentLoaded', () => {
        const tableBody = document.getElementById('superadmins-table-body');
        const searchBar = document.querySelector('.search-bar input[type="search"]');
        const prevPageBtn = document.getElementById('prevPage');
        const nextPageBtn = document.getElementById('nextPage');
        const pageInfo = document.getElementById('pageInfo');

        let currentPage = 1;
        const itemsPerPage = 10;
        let allSuperadmins = [];
        let filteredSuperadmins = [];

        function renderTable(superadmins) {
            tableBody.innerHTML = '';

            if (superadmins.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="5">
                            <div class="empty-state">
                                <i class="fas fa-user-shield"></i>
                                <h3>No hay administradores institucionales registrados</h3>
                                <p>Comience agregando el primer administrador institucional al sistema</p>
                                <a href="{{ url_for('admin.crear_usuario', rol='administrador_institucional') }}" class="btn-create">
                                    <i class="fas fa-user-plus me-2"></i>
                                    Crear Primer Administrador
                                </a>
                            </div>
                        </td>
                    </tr>
                `;
                return;
            }

            // Calcular índices para la página actual
            const startIndex = (currentPage - 1) * itemsPerPage;
            const endIndex = startIndex + itemsPerPage;
            const currentSuperadmins = superadmins.slice(startIndex, endIndex);

            currentSuperadmins.forEach(superadmin => {
                const row = document.createElement('tr');
                const userId = superadmin.id_usuario;
                const estadoClase = superadmin.estado_cuenta === 'activa' ? 'badge-success' : 'badge-danger';
                const estadoTexto = superadmin.estado_cuenta === 'activa' ? 'Activa' : 'Inactiva';

                row.innerHTML = `
                    <td>${superadmin.no_identidad}</td>
                    <td>${superadmin.nombre_completo}</td>
                    <td>${superadmin.correo}</td>
                    <td><span class="badge ${estadoClase}">${estadoTexto}</span></td>
                    <td class="actions-cell">
                        <a href="/admin/editar_usuario/${userId}" class="btn-action edit" title="Editar">
                            <i class="fas fa-edit"></i>
                        </a>
                
                    </td>
                `;
                tableBody.appendChild(row);
            });

            updatePagination(superadmins.length);
        }

        function updatePagination(totalItems) {
            const totalPages = Math.ceil(totalItems / itemsPerPage);
            
            pageInfo.textContent = `Página ${currentPage} de ${totalPages}`;
            
            prevPageBtn.disabled = currentPage === 1;
            nextPageBtn.disabled = currentPage === totalPages || totalPages === 0;
        }

        function changePage(direction) {
            const totalPages = Math.ceil(filteredSuperadmins.length / itemsPerPage);
            
            if (direction === 'next' && currentPage < totalPages) {
                currentPage++;
            } else if (direction === 'prev' && currentPage > 1) {
                currentPage--;
            }
            
            renderTable(filteredSuperadmins);
        }

        async function fetchData(query = '') {
            try {
                const response = await fetch(`/admin/api/superadmins?q=${query}`);
                const data = await response.json();
                if (response.ok) {
                    allSuperadmins = data.data;
                    filteredSuperadmins = [...allSuperadmins];
                    currentPage = 1;
                    renderTable(filteredSuperadmins);
                } else {
                    console.error('Error al obtener datos de la API:', data.error);
                    tableBody.innerHTML = `<tr><td colspan="5">Error al cargar los datos. Intente de nuevo más tarde.</td></tr>`;
                }
            } catch (error) {
                console.error('Error de red o del servidor:', error);
                tableBody.innerHTML = `<tr><td colspan="5">No se pudo conectar con el servidor.</td></tr>`;
            }
        }

        // Event listeners para paginación
        prevPageBtn.addEventListener('click', () => changePage('prev'));
        nextPageBtn.addEventListener('click', () => changePage('next'));

        fetchData();

        searchBar.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            currentPage = 1;
            
            if (query === '') {
                filteredSuperadmins = [...allSuperadmins];
            } else {
                filteredSuperadmins = allSuperadmins.filter(superadmin => 
                    superadmin.nombre_completo.toLowerCase().includes(query) ||
                    superadmin.no_identidad.toLowerCase().includes(query) ||
                    superadmin.correo.toLowerCase().includes(query)
                );
            }
            
            renderTable(filteredSuperadmins);
        });

        // Actualizar cada 30 segundos
        setInterval(() => fetchData(), 30000);
    });
