    document.addEventListener('DOMContentLoaded', () => {
        const tableBody = document.getElementById('padres-table-body');
        const searchBar = document.querySelector('.search-bar input[type="search"]');
        const prevPageBtn = document.getElementById('prevPage');
        const nextPageBtn = document.getElementById('nextPage');
        const pageInfo = document.getElementById('pageInfo');

        let currentPage = 1;
        const itemsPerPage = 10;
        let allPadres = [];
        let filteredPadres = [];

        function renderTable(padres) {
            tableBody.innerHTML = '';

            if (padres.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="7">
                            <div class="empty-state">
                                <i class="fas fa-users"></i>
                                <h3>No hay padres/tutores registrados</h3>
                                <p>Comience agregando el primer padre o tutor al sistema</p>
                                <a href="{{ url_for('admin.crear_usuario', rol='padre') }}" class="btn-create">
                                    <i class="fas fa-user-plus me-2"></i>
                                    Crear Primer Padre/Tutor
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
            const currentPadres = padres.slice(startIndex, endIndex);

            currentPadres.forEach(padre => {
                const row = document.createElement('tr');
                const userId = padre.id_usuario;
                const estadoClase = padre.estado_cuenta === 'activa' ? 'badge-success' : 'badge-danger';
                const estadoTexto = padre.estado_cuenta === 'activa' ? 'Activa' : 'Inactiva';
                const hijosAsignados = padre.hijos_asignados && padre.hijos_asignados.length > 0 ? 
                    padre.hijos_asignados.join(', ') : 'Sin hijos asignados';

                row.innerHTML = `
                    <td>${padre.no_identidad}</td>
                    <td>${padre.nombre_completo}</td>
                    <td>${padre.correo}</td>
                    <td>${padre.telefono || 'N/A'}</td>
                    <td>${hijosAsignados}</td>
                    <td><span class="badge ${estadoClase}">${estadoTexto}</span></td>
                    <td class="actions-cell">
                        <a href="/admin/editar_usuario/${userId}" class="btn-action edit" title="Editar">
                            <i class="fas fa-edit"></i>
                        </a>
                        <form action="/admin/eliminar_usuario/${userId}" method="POST" style="display:inline;" onsubmit="return confirm('¿Estás seguro de que quieres eliminar este usuario?');">
                            <button type="submit" class="btn-action delete" title="Eliminar">
                                <i class="fas fa-trash-alt"></i>
                            </button>
                        </form>
                    </td>
                `;
                tableBody.appendChild(row);
            });

            updatePagination(padres.length);
        }

        function updatePagination(totalItems) {
            const totalPages = Math.ceil(totalItems / itemsPerPage);
            
            pageInfo.textContent = `Página ${currentPage} de ${totalPages}`;
            
            prevPageBtn.disabled = currentPage === 1;
            nextPageBtn.disabled = currentPage === totalPages || totalPages === 0;
        }

        function changePage(direction) {
            const totalPages = Math.ceil(filteredPadres.length / itemsPerPage);
            
            if (direction === 'next' && currentPage < totalPages) {
                currentPage++;
            } else if (direction === 'prev' && currentPage > 1) {
                currentPage--;
            }
            
            renderTable(filteredPadres);
        }

        async function fetchData(query = '') {
            try {
                const response = await fetch(`/admin/api/padres?q=${query}`);
                const data = await response.json();
                if (response.ok) {
                    allPadres = data.data;
                    filteredPadres = [...allPadres];
                    currentPage = 1;
                    renderTable(filteredPadres);
                } else {
                    console.error('Error al obtener datos de la API:', data.error);
                    tableBody.innerHTML = `<tr><td colspan="7">Error al cargar los datos. Intente de nuevo más tarde.</td></tr>`;
                }
            } catch (error) {
                console.error('Error de red o del servidor:', error);
                tableBody.innerHTML = `<tr><td colspan="7">No se pudo conectar con el servidor.</td></tr>`;
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
                filteredPadres = [...allPadres];
            } else {
                filteredPadres = allPadres.filter(padre => 
                    padre.nombre_completo.toLowerCase().includes(query) ||
                    padre.no_identidad.toLowerCase().includes(query) ||
                    padre.correo.toLowerCase().includes(query)
                );
            }
            
            renderTable(filteredPadres);
        });

        // Actualizar cada 30 segundos
        setInterval(() => fetchData(), 30000);
    });
