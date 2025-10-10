
        document.addEventListener('DOMContentLoaded', () => {
            const tableBody = document.getElementById('profesores-table-body');
            const prevPageBtn = document.getElementById('prevPage');
            const nextPageBtn = document.getElementById('nextPage');
            const pageInfo = document.getElementById('pageInfo');

            let currentPage = 1;
            const itemsPerPage = 10;
            let allProfesores = [];
            let filteredProfesores = [];

            function renderTable(profesores) {
                tableBody.innerHTML = ''; 
                
                // Calcular índices para la página actual
                const startIndex = (currentPage - 1) * itemsPerPage;
                const endIndex = startIndex + itemsPerPage;
                const currentProfesores = profesores.slice(startIndex, endIndex);

                currentProfesores.forEach(profesor => {
                    const row = document.createElement('tr');
                    
                    const userId = profesor.id_usuario; 

                    const estadoClase = profesor.estado_cuenta === 'activa' ? 'badge-success' : 'badge-danger';
                    const estadoTexto = profesor.estado_cuenta === 'activa' ? 'Activo' : 'Inactivo';

                    row.innerHTML = `
                        <td><input type="checkbox" class="row-checkbox"></td>
                        <td>${profesor.no_identidad}</td>
                        <td><span class="avatar"><i class="fa-solid fa-user"></i></span></td>
                        <td><a href="#">${profesor.nombre_completo}</a></td>
                        <td>${profesor.correo}</td>
                        <td><span class="tag tag-profesor">${profesor.rol}</span></td>
                        <td><span class="badge ${estadoClase}">${estadoTexto}</span></td>
                        <td>${profesor.curso_asignado}</td>
                        <td>${profesor.materia_area}</td>
                        <td>${profesor.sede_asignada}</td>
                        <td class="actions-cell">
                            <a href="/admin/editar_usuario/${userId}" class="btn-action edit" title="Editar"><i class="fas fa-edit"></i></a>
                            <form action="/admin/eliminar_usuario/${userId}" method="POST" style="display:inline;" onsubmit="return confirm('¿Estás seguro de que quieres eliminar este usuario?');">
                                <button type="submit" class="btn-action delete" title="Eliminar"><i class="fas fa-trash-alt"></i></button>
                            </form>
                        </td>
                    `;
                    tableBody.appendChild(row);
                });

                updatePagination(profesores.length);
            }

            function updatePagination(totalItems) {
                const totalPages = Math.ceil(totalItems / itemsPerPage);
                
                pageInfo.textContent = `Página ${currentPage} de ${totalPages}`;
                
                prevPageBtn.disabled = currentPage === 1;
                nextPageBtn.disabled = currentPage === totalPages || totalPages === 0;
            }

            function changePage(direction) {
                const totalPages = Math.ceil(filteredProfesores.length / itemsPerPage);
                
                if (direction === 'next' && currentPage < totalPages) {
                    currentPage++;
                } else if (direction === 'prev' && currentPage > 1) {
                    currentPage--;
                }
                
                renderTable(filteredProfesores);
            }

            async function fetchProfesores() {
                try {
                    const response = await fetch('/admin/api/profesores');
                    const data = await response.json();

                    if (response.ok) {
                        allProfesores = data.data;
                        filteredProfesores = [...allProfesores];
                        currentPage = 1;
                        renderTable(filteredProfesores);
                    } else {
                        console.error('Error al obtener datos de la API:', data.error);
                        tableBody.innerHTML = `<tr><td colspan="11">Error al cargar los datos. Intente de nuevo más tarde.</td></tr>`;
                    }
                } catch (error) {
                    console.error('Error de red o del servidor:', error);
                    tableBody.innerHTML = `<tr><td colspan="11">No se pudo conectar con el servidor.</td></tr>`;
                }
            }

            // Event listeners para paginación
            prevPageBtn.addEventListener('click', () => changePage('prev'));
            nextPageBtn.addEventListener('click', () => changePage('next'));

            fetchProfesores();

            // Actualizar cada 30 segundos en lugar de 3 para mejor rendimiento
            setInterval(fetchProfesores, 30000);
        });
    