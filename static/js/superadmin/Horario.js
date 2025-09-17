        // ========================================
        // INICIALIZACIÓN Y CONFIGURACIÓN GLOBAL
        // ========================================
        document.addEventListener('DOMContentLoaded', function () {
            
            // ========================================
            // REFERENCIAS A ELEMENTOS DEL DOM
            // Cacheo de elementos para mejor rendimiento
            // ========================================
            
            // Elementos del gráfico y canvas
            const ctx = document.getElementById('horarioGeneralChart').getContext('2d');
            
            // Controles de configuración de horario
            const dayCheckboxes = document.querySelectorAll('.day-checkbox');
            const scheduleSelectorDropdown = document.getElementById('scheduleSelectorDropdown');
            const generalStartTimeInput = document.getElementById('general-start-time');
            const generalEndTimeInput = document.getElementById('general-end-time');
            
            // Botones de acción principal
            const createScheduleBtn = document.getElementById('create-schedule-btn');
            const assignScheduleBtn = document.getElementById('assign-schedule-btn');
            const deleteScheduleBtn = document.getElementById('delete-schedule-btn');
            
            // Controles de descansos
            const addBreakBtn = document.getElementById('add-break-btn');
            const breakStartTimeInput = document.getElementById('break-start-time');
            const breakDurationInput = document.getElementById('break-duration');
            const breakList = document.getElementById('break-list');
            
            // Controles de materias
            const addSubjectBtn = document.getElementById('add-subject-btn');
            const newSubjectNameInput = document.getElementById('new-subject-name');
            const subjectsList = document.getElementById('global-subjects-list');
            const additionalSettingsBtn = document.getElementById('additional-settings-btn');

            // Elementos de layout y navegación
            const courseListPanel = document.getElementById('course-list-panel');
            const managementPanel = document.getElementById('management-panel');
            const horarioCursoTabEl = document.getElementById('horario-curso-tab');
            const horarioGeneralTabEl = document.getElementById('horario-general-tab');
            const scheduleDisplay = document.getElementById('schedule-display-content');
            const mainColumn = document.getElementById('main-column');
            const sideColumn = document.getElementById('side-column');

            // Inicialización de modales Bootstrap
            const createScheduleModal = new bootstrap.Modal(document.getElementById('createScheduleModal'));
            const assignScheduleModal = new bootstrap.Modal(document.getElementById('assignScheduleModal'));
            const alertModal = new bootstrap.Modal(document.getElementById('alertModal'));
            const confirmModal = new bootstrap.Modal(document.getElementById('confirmModal'));
            const additionalSettingsModal = new bootstrap.Modal(document.getElementById('additional-settings-modal'));

            // ========================================
            // VARIABLES DE ESTADO DE LA APLICACIÓN
            // ========================================
            
            // Datos principales del sistema (desde Flask)
            let horarios = {{ horarios | tojson | safe }};  // Horarios generales desde el servidor
            let allSubjects = [];                            // Lista de todas las materias/asignaturas
            let currentSchedule = horarios[0] || null;       // Horario actualmente seleccionado
            
            // Datos locales (almacenados en localStorage)
            let courseAssignments = {};                      // Asignaciones curso-horario
            let allTeachers = [];                           // Lista de profesores disponibles
            let allClassrooms = [];                         // Lista de salones disponibles

            // ========================================
            // GESTIÓN DE CAMBIOS DE PESTAÑAS
            // Control del layout responsivo
            // ========================================
            
            /**
             * Evento: Mostrar pestaña "Horario General"
             * Cambia el layout para mostrar el panel de gestión
             * y ocultar la lista lateral de cursos
             */
            horarioGeneralTabEl.addEventListener('shown.bs.tab', () => {
                sideColumn.classList.add('d-none');           // Oculta columna lateral
                managementPanel.classList.remove('d-none');   // Muestra panel de gestión
                mainColumn.classList.remove('col-lg-8');      // Cambia a columna completa
                mainColumn.classList.add('col-lg-12');
            });
            
            /**
             * Evento: Mostrar pestaña "Horario de Curso"
             * Restaura el layout de dos columnas
             */
            horarioCursoTabEl.addEventListener('shown.bs.tab', () => {
                managementPanel.classList.add('d-none');      // Oculta panel de gestión
                sideColumn.classList.remove('d-none');       // Muestra columna lateral
                mainColumn.classList.remove('col-lg-12');     // Restaura layout de dos columnas
                mainColumn.classList.add('col-lg-8');
            });

            // ========================================
            // FUNCIONES DE UTILIDAD
            // Helpers para conversiones y UI
            // ========================================
            
            /**
             * Convierte hora en formato 24h a formato 12h con AM/PM
             * @param {string} time - Hora en formato "HH:MM"
             * @returns {string} Hora formateada con AM/PM
             */
            const formatTime12 = time => {
                if (!time) return '';
                const [h, m] = time.split(':').map(Number);
                const hour = h % 12 || 12;                    // Convierte 0 a 12 para medianoche
                const ampm = h >= 12 ? 'PM' : 'AM';
                return `${hour.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')} ${ampm}`;
            };
            
            /**
             * Convierte hora "HH:MM" a número decimal para cálculos matemáticos
             * Ejemplo: "14:30" -> 14.5
             * @param {string} time - Hora en formato "HH:MM"
             * @returns {number} Hora en formato decimal
             */
            const timeToDecimal = time => {
                if (!time) return 0;
                const [h, m] = time.split(':').map(Number);
                return h + m / 60;
            };
            
            /**
             * Convierte número decimal a formato "HH:MM"
             * Ejemplo: 14.5 -> "14:30"
             * @param {number} decimal - Hora en formato decimal
             * @returns {string} Hora en formato "HH:MM"
             */
            const decimalToTime = decimal => {
                const h = Math.floor(decimal);
                const m = Math.round((decimal - h) * 60);
                return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
            };
            
            /**
             * Muestra un modal de alerta con mensaje personalizado
             * @param {string} message - Mensaje a mostrar al usuario
             * @param {string} title - Título del modal (opcional)
             */
            const showAlert = (message, title = 'Notificación') => {
                document.getElementById('alertModalBody').innerHTML = message;
                document.querySelector('#alertModal .modal-title').textContent = title;
                alertModal.show();
            };
            
            /**
             * Muestra un modal de confirmación con callback
             * @param {string} message - Mensaje de confirmación
             * @param {Function} callback - Función a ejecutar si se confirma
             */
            const showConfirm = (message, callback) => {
                document.getElementById('confirmModalBody').textContent = message;
                document.getElementById('confirmActionBtn').onclick = () => { 
                    callback(); 
                    confirmModal.hide(); 
                };
                confirmModal.show();
            };

            // ========================================
            // GESTIÓN DE PERSISTENCIA DE DATOS
            // Manejo de localStorage para datos locales
            // ========================================
            
            /**
             * Guarda datos locales en localStorage del navegador
             * Incluye asignaciones de cursos, profesores y salones
             */
            function saveLocalData() {
                localStorage.setItem('courseAssignments', JSON.stringify(courseAssignments));
                localStorage.setItem('allTeachers', JSON.stringify(allTeachers));
                localStorage.setItem('allClassrooms', JSON.stringify(allClassrooms));
            }

            /**
             * Carga datos locales desde localStorage
             * Inicializa con datos por defecto si no existen
             * Migra formatos antiguos si es necesario
             */
            function loadLocalData() {
                const savedAssignments = localStorage.getItem('courseAssignments');
                
                // Carga listas con datos por defecto
                allTeachers = JSON.parse(localStorage.getItem('allTeachers')) || 
                             ['Prof. García', 'Prof. López', 'Prof. Martínez'];
                allClassrooms = JSON.parse(localStorage.getItem('allClassrooms')) || 
                               ['Aula 101', 'Laboratorio A', 'Aula 203'];

                // Carga asignaciones de cursos
                if (savedAssignments) {
                    courseAssignments = JSON.parse(savedAssignments);
                    
                    // Migración de formato antiguo a nuevo
                    Object.keys(courseAssignments).forEach(key => {
                        if (typeof courseAssignments[key] === 'string') {
                            // Convierte formato antiguo (solo string) a nuevo formato (objeto)
                            courseAssignments[key] = { 
                                scheduleName: courseAssignments[key], 
                                subjects: {}, 
                                resources: [] 
                            };
                        } else {
                            // Asegura que el objeto tenga todas las propiedades necesarias
                            courseAssignments[key].resources = courseAssignments[key].resources || [];
                        }
                    });
                }
                saveLocalData();  // Guarda los datos migrados
            }

            // ========================================
            // COMUNICACIÓN CON EL SERVIDOR FLASK
            // APIs para obtener datos del backend
            // ========================================
            
            /**
             * Obtiene datos del servidor Flask mediante APIs REST
             * Carga la lista de materias/asignaturas disponibles
             */
            async function fetchData() {
                try {
                    // Obtiene materias desde la API de Flask
                    const subjectsResponse = await fetch('/admin/api/materias');
                    allSubjects = await subjectsResponse.json();
                } catch (e) {
                    console.error("Error al cargar datos del servidor:", e);
                    showAlert("Error al conectar con el servidor. Algunas funciones pueden no estar disponibles.");
                }
            }

            // ========================================
            // FUNCIONES DE ACTUALIZACIÓN DE INTERFAZ
            // ========================================
            
            /**
             * Actualiza toda la interfaz de usuario
             * Sincroniza la UI con el estado actual de los datos
             */
            function updateUI() {
                // Actualiza controles de horario actual
                if (currentSchedule) {
                    generalStartTimeInput.value = currentSchedule.horaInicio || '';
                    generalEndTimeInput.value = currentSchedule.horaFin || '';
                    
                    // Actualiza checkboxes de días de la semana
                    dayCheckboxes.forEach(cb => 
                        cb.checked = currentSchedule.diasSemana && 
                                   currentSchedule.diasSemana.includes(cb.value)
                    );
                } else {
                    // Limpia controles si no hay horario seleccionado
                    generalStartTimeInput.value = '';
                    generalEndTimeInput.value = '';
                    dayCheckboxes.forEach(cb => cb.checked = false);
                }
                
                // Actualiza todos los componentes de la interfaz
                renderScheduleDropdown();
                renderBreakList();
                renderGlobalResourcesUI();
                updateChart();
                updateSummaryCards();
            }

            /**
             * Actualiza las tarjetas de resumen del dashboard
             * Calcula y muestra estadísticas actuales del sistema
             */
            function updateSummaryCards() {
                const totalCourses = document.querySelectorAll('.course-row').length;
                const totalTeachers = allTeachers.length;
                const activeSchedules = horarios.length;

                document.getElementById('total-courses').textContent = totalCourses;
                document.getElementById('total-teachers').textContent = totalTeachers;
                document.getElementById('active-schedules').textContent = activeSchedules;
            }

            /**
             * Renderiza el dropdown de selección de horarios
             * Crea opciones dinámicas basadas en horarios disponibles
             */
            function renderScheduleDropdown() {
                const scheduleListEl = document.getElementById('schedule-list');
                scheduleListEl.innerHTML = '';
                
                horarios.forEach(schedule => {
                    const li = document.createElement('li');
                    const a = document.createElement('a');
                    a.className = 'dropdown-item';
                    a.href = '#';
                    a.textContent = schedule.nombre;
                    
                    // Event listener para selección de horario
                    a.addEventListener('click', e => {
                        e.preventDefault();
                        currentSchedule = schedule;
                        updateUI();
                    });
                    
                    li.appendChild(a);
                    scheduleListEl.appendChild(li);
                });
                
                // Actualiza el texto del botón dropdown
                scheduleSelectorDropdown.textContent = currentSchedule ? currentSchedule.nombre : 'Seleccionar';
            }

            /**
             * Renderiza la lista de descansos del horario actual
             * Muestra períodos de descanso ordenados por hora
             */
            function renderBreakList() {
                const breakList = document.getElementById('break-list');
                breakList.innerHTML = '';
                
                if (!currentSchedule || !currentSchedule.descansos) return;
                
                // Ordena descansos por hora de inicio y los renderiza
                currentSchedule.descansos
                    .sort((a, b) => timeToDecimal(a.horaInicio) - timeToDecimal(b.horaInicio))
                    .forEach(breakItem => {
                        const li = document.createElement('li');
                        li.className = 'list-group-item d-flex justify-content-between align-items-center';
                        li.innerHTML = `
                            <span>${breakItem.horaInicio} (${breakItem.duracion} min)</span>
                            <button class="btn btn-danger btn-sm delete-break-btn" data-break-id="${breakItem.id}">
                                <i class="fa-solid fa-trash-alt"></i>
                            </button>
                        `;
                        breakList.appendChild(li);
                    });
            }

            /**
             * Renderiza la lista global de materias/asignaturas
             * Muestra todas las materias disponibles con opción de eliminar
             */
            function renderGlobalResourcesUI() {
                const listEl = document.getElementById('global-subjects-list');
                listEl.innerHTML = '';
                
                allSubjects
                    .sort((a, b) => a.nombre.localeCompare(b.nombre))  // Ordena alfabéticamente
                    .forEach(item => {
                        const li = document.createElement('li');
                        li.className = 'list-group-item d-flex justify-content-between align-items-center';
                        li.innerHTML = `
                            <span>${item.nombre}</span>
                            <button class="btn btn-outline-danger btn-sm delete-subject-btn" data-subject-id="${item.id}">
                                <i class="fa-solid fa-trash-alt"></i>
                            </button>
                        `;
                        listEl.appendChild(li);
                    });
            }

            // ========================================
            // LÓGICA DE CÁLCULO DE HORARIOS
            // Algoritmos para procesar bloques de clase y descansos
            // ========================================
            
            /**
             * Calcula los bloques de clase basado en horario general y descansos
             * Divide el horario en segmentos de clase, excluyendo períodos de descanso
             * 
             * @param {Object} schedule - Objeto horario con horaInicio, horaFin y descansos
             * @returns {Array} Array de bloques {start, end} en formato "HH:MM"
             */
            const calculateClassBlocks = (schedule) => {
                if (!schedule.horaInicio || !schedule.horaFin) return [];
                
                // Ordena descansos por hora de inicio
                const sortedBreaks = [...(schedule.descansos || [])]
                    .sort((a, b) => timeToDecimal(a.horaInicio) - timeToDecimal(b.horaInicio));
                
                // Comienza con un bloque completo del día
                let blocks = [{ start: schedule.horaInicio, end: schedule.horaFin }];
                
                // Procesa cada descanso para dividir los bloques
                sortedBreaks.forEach(breakItem => {
                    const breakStart = timeToDecimal(breakItem.horaInicio);
                    
                    // Calcula hora de fin del descanso basado en duración
                    const breakEnd = breakStart + (breakItem.duracion / 60);
                    let newBlocks = [];
                    
                    // Divide cada bloque existente según el descanso
                    blocks.forEach(block => {
                        const blockStart = timeToDecimal(block.start);
                        const blockEnd = timeToDecimal(block.end);
                        
                        // Si el descanso no afecta este bloque, lo mantiene intacto
                        if (breakStart >= blockEnd || breakEnd <= blockStart) { 
                            newBlocks.push(block); 
                        } else {
                            // Divide el bloque: antes y después del descanso
                            if (breakStart > blockStart) {
                                newBlocks.push({ 
                                    start: block.start, 
                                    end: decimalToTime(breakStart) 
                                });
                            }
                            if (breakEnd < blockEnd) {
                                newBlocks.push({ 
                                    start: decimalToTime(breakEnd), 
                                    end: block.end 
                                });
                            }
                        }
                    });
                    blocks = newBlocks;
                });
                
                // Filtra bloques válidos (con duración > 0)
                return blocks.filter(b => timeToDecimal(b.start) < timeToDecimal(b.end));
            };

            /**
             * Actualiza el gráfico de Chart.js con datos del horario actual
             * Visualiza bloques de clase por día de la semana
             */
            function updateChart() {
                if (!window.horarioGeneralChart) return;
                
                // Limpia el gráfico si no hay horario seleccionado
                if (!currentSchedule || !currentSchedule.diasSemana) {
                    window.horarioGeneralChart.data.datasets = [];
                    window.horarioGeneralChart.data.labels = [];
                    window.horarioGeneralChart.update();
                    return;
                }
                
                // Procesa días seleccionados
                const selectedDays = currentSchedule.diasSemana.split(',').filter(d => d);
                let allTimePoints = [];
                window.horarioGeneralChart.data.datasets = [];
                const classBlocksByDay = {};
                let maxSegments = 0;
                
                // Calcula bloques para cada día
                selectedDays.forEach(day => {
                    const blocks = calculateClassBlocks(currentSchedule);
                    classBlocksByDay[day] = blocks;
                    if (blocks.length > maxSegments) maxSegments = blocks.length;
                });

                // Crea datasets para cada segmento de clase
                for (let i = 0; i < maxSegments; i++) {
                    window.horarioGeneralChart.data.datasets.push({
                        label: `Bloque ${i + 1}`,
                        data: [],
                        backgroundColor: [],
                        borderWidth: 1,
                        borderRadius: 5
                    });
                }
                
                // Obtiene color primario del CSS
                const colorPrimario = getComputedStyle(document.documentElement)
                    .getPropertyValue('--color-primario');
                
                // Llena datos para cada día y segmento
                selectedDays.forEach(day => {
                    const blocks = classBlocksByDay[day];
                    for (let i = 0; i < maxSegments; i++) {
                        window.horarioGeneralChart.data.datasets[i].backgroundColor.push(colorPrimario);
                        if (blocks[i]) {
                            // Convierte bloque a formato de Chart.js [inicio, fin]
                            const segment = [timeToDecimal(blocks[i].start), timeToDecimal(blocks[i].end)];
                            window.horarioGeneralChart.data.datasets[i].data.push(segment);
                            allTimePoints.push(...segment);
                        } else {
                            window.horarioGeneralChart.data.datasets[i].data.push(null);
                        }
                    }
                });
                
                // Ajusta escala Y del gráfico automáticamente
                const yMin = allTimePoints.length > 0 ? Math.floor(Math.min(...allTimePoints)) - 0.5 : 6;
                const yMax = allTimePoints.length > 0 ? Math.ceil(Math.max(...allTimePoints)) + 0.5 : 18;
                
                window.horarioGeneralChart.options.scales.y.min = yMin;
                window.horarioGeneralChart.options.scales.y.max = yMax;
                window.horarioGeneralChart.data.labels = selectedDays;
                window.horarioGeneralChart.update();
            }

            // ========================================
            // INICIALIZACIÓN DEL GRÁFICO CHART.JS
            // Configuración del gráfico principal
            // ========================================
            
            /**
             * Configura e inicializa el gráfico de horarios generales
             * Utiliza Chart.js para visualización interactiva
             */
            window.horarioGeneralChart = new Chart(ctx, {
                type: 'bar',                               // Gráfico de barras horizontales
                data: { labels: [], datasets: [] },       // Datos iniciales vacíos
                options: {
                    responsive: true,                      // Se adapta al contenedor
                    maintainAspectRatio: false,           // Permite altura fija
                    indexAxis: 'x',                       // Barras verticales
                    scales: {
                        x: { 
                            stacked: true,                 // Permite múltiples bloques por día
                            title: { display: true, text: 'Días de la Semana' } 
                        },
                        y: {
                            stacked: false,
                            title: { display: true, text: 'Horas' },
                            ticks: {
                                stepSize: 1,               // Intervalos de 1 hora
                                callback: (value) => formatTime12(decimalToTime(value))  // Formato 12h
                            }
                        }
                    },
                    plugins: {
                        legend: { display: false },        // Oculta leyenda
                        tooltip: {
                            callbacks: {
                                // Tooltip personalizado con formato de hora
                                label: (context) => 
                                    `Bloque: ${context.label} - ${formatTime12(decimalToTime(context.raw[0]))} a ${formatTime12(decimalToTime(context.raw[1]))}`
                            }
                        }
                    }
                }
            });

            // ========================================
            // EVENT LISTENERS - INTEGRACIÓN CON FLASK
            // Manejo de eventos que requieren comunicación con el servidor
            // ========================================
            
            /**
             * Botón: Crear nuevo horario general
             */
            createScheduleBtn.addEventListener('click', () => createScheduleModal.show());

            /**
             * Botón: Guardar nuevo horario (dentro del modal)
             * Envía datos al servidor Flask via API REST
             */
            document.getElementById('save-new-schedule-btn').addEventListener('click', async () => {
                const newName = document.getElementById('new-schedule-name').value.trim();
                if (!newName) return showAlert("El nombre no puede estar vacío.");

                try {
                    // POST a la API de Flask para crear horario
                    const response = await fetch('/admin/api/horarios', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ nombre: newName })
                    });
                    const newSchedule = await response.json();
                    
                    if (response.ok) {
                        horarios.push(newSchedule);           // Añade a la lista local
                        currentSchedule = newSchedule;        // Selecciona el nuevo horario
                        updateUI();                           // Actualiza la interfaz
                        createScheduleModal.hide();           // Cierra el modal
                        showAlert("Horario creado exitosamente.", "Éxito");
                    } else {
                        showAlert(newSchedule.error || "Error al crear el horario.", "Error");
                    }
                } catch (e) {
                    showAlert("Error al conectar con el servidor.", "Error de Conexión");
                }
            });

            /**
             * Botón: Eliminar horario seleccionado
             * Requiere confirmación del usuario antes de proceder
             */
            deleteScheduleBtn.addEventListener('click', () => {
                if (!currentSchedule) return showAlert("No hay horario seleccionado.");
                
                showConfirm(`¿Eliminar el horario "${currentSchedule.nombre}"?`, async () => {
                    try {
                        // DELETE a la API de Flask
                        const response = await fetch(`/admin/api/horarios`, {
                            method: 'DELETE',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ id: currentSchedule.id })
                        });
                        const result = await response.json();
                        
                        if (response.ok) {
                            // Remueve de la lista local y selecciona otro horario
                            horarios = horarios.filter(h => h.id !== currentSchedule.id);
                            currentSchedule = horarios[0] || null;
                            updateUI();
                            showAlert("Horario eliminado exitosamente.", "Éxito");
                        } else {
                            showAlert(result.error || "Error al eliminar el horario.", "Error");
                        }
                    } catch (e) {
                        showAlert("Error al conectar con el servidor.", "Error de Conexión");
                    }
                });
            });

            /**
             * Input: Hora de inicio del horario general
             * Actualiza el horario en el servidor cuando cambia
             */
            generalStartTimeInput.addEventListener('change', async () => {
                if (!currentSchedule) return;
                currentSchedule.horaInicio = generalStartTimeInput.value;
                
                try {
                    // PUT a la API de Flask para actualizar
                    const response = await fetch(`/admin/api/horarios`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            id: currentSchedule.id, 
                            horaInicio: currentSchedule.horaInicio 
                        })
                    });
                    const result = await response.json();
                    if (!response.ok) showAlert(result.error || "Error al actualizar la hora.");
                    updateUI();  // Actualiza gráfico y UI
                } catch (e) { 
                    showAlert("Error al conectar con el servidor."); 
                }
            });

            /**
             * Input: Hora de fin del horario general
             */
            generalEndTimeInput.addEventListener('change', async () => {
                if (!currentSchedule) return;
                currentSchedule.horaFin = generalEndTimeInput.value;
                
                try {
                    const response = await fetch(`/admin/api/horarios`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            id: currentSchedule.id, 
                            horaFin: currentSchedule.horaFin 
                        })
                    });
                    const result = await response.json();
                    if (!response.ok) showAlert(result.error || "Error al actualizar la hora.");
                    updateUI();
                } catch (e) { 
                    showAlert("Error al conectar con el servidor."); 
                }
            });
            
            /**
             * Checkboxes: Días de la semana
             * Actualiza los días activos del horario
             */
            dayCheckboxes.forEach(c => c.addEventListener('change', async () => {
                if (!currentSchedule) return;
                
                // Construye string de días seleccionados
                const selectedDays = Array.from(dayCheckboxes)
                    .filter(i => i.checked)
                    .map(i => i.value)
                    .join(',');
                
                currentSchedule.diasSemana = selectedDays;
                
                try {
                    const response = await fetch(`/admin/api/horarios`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            id: currentSchedule.id, 
                            diasSemana: currentSchedule.diasSemana 
                        })
                    });
                    const result = await response.json();
                    if (!response.ok) showAlert(result.error || "Error al actualizar los días.");
                    updateUI();  // Actualiza gráfico con nuevos días
                } catch (e) { 
                    showAlert("Error al conectar con el servidor."); 
                }
            }));
            
            /**
             * Botón: Añadir período de descanso
             * Crea un nuevo descanso en el horario seleccionado
             */
            addBreakBtn.addEventListener('click', async () => {
                if (!currentSchedule) return showAlert('Por favor, seleccione un horario primero.');
                
                const start = breakStartTimeInput.value;
                const duration = parseInt(breakDurationInput.value, 10);
                
                if (!start || !duration || duration <= 0) {
                    return showAlert('Ingrese una hora y duración válidas.');
                }
                
                try {
                    // POST a la API de descansos de Flask
                    const response = await fetch(`/admin/api/horarios/${currentSchedule.id}/breaks`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ horaInicio: start, duracion: duration })
                    });
                    const newBreak = await response.json();
                    
                    if (response.ok) {
                        // Añade el descanso a la lista local
                        currentSchedule.descansos = currentSchedule.descansos || [];
                        currentSchedule.descansos.push(newBreak);
                        updateUI();
                        
                        // Limpia el formulario
                        breakStartTimeInput.value = '';
                        breakDurationInput.value = '';
                        showAlert("Descanso añadido exitosamente.", "Éxito");
                    } else {
                        showAlert(newBreak.error || "Error al añadir el descanso.", "Error");
                    }
                } catch (e) { 
                    showAlert("Error al conectar con el servidor."); 
                }
            });

            /**
             * Lista de descansos: Eliminar descanso específico
             * Event delegation para botones de eliminar dinámicos
             */
            breakList.addEventListener('click', async e => {
                const button = e.target.closest('button.delete-break-btn');
                if (button && currentSchedule) {
                    const breakId = button.dataset.breakId;
                    
                    showConfirm(`¿Eliminar este descanso?`, async () => {
                        try {
                            const response = await fetch(`/admin/api/horarios/${currentSchedule.id}/breaks`, {
                                method: 'DELETE',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ id: breakId })
                            });
                            const result = await response.json();
                            
                            if (response.ok) {
                                // Remueve de la lista local
                                currentSchedule.descansos = currentSchedule.descansos
                                    .filter(b => b.id != breakId);
                                updateUI();
                                showAlert("Descanso eliminado exitosamente.", "Éxito");
                            } else {
                                showAlert(result.error || "Error al eliminar el descanso.", "Error");
                            }
                        } catch (e) { 
                            showAlert("Error al conectar con el servidor."); 
                        }
                    });
                }
            });

            /**
             * Botón: Añadir nueva materia/asignatura
             */
            addSubjectBtn.addEventListener('click', async () => {
                const name = newSubjectNameInput.value.trim();
                if (!name) return showAlert("El nombre de la materia no puede estar vacío.");
                
                try {
                    const response = await fetch('/admin/api/materias', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ nombre: name })
                    });
                    const newSubject = await response.json();
                    
                    if (response.ok) {
                        allSubjects.push(newSubject);         // Añade a la lista local
                        renderGlobalResourcesUI();            // Actualiza la UI
                        newSubjectNameInput.value = '';       // Limpia el input
                        showAlert("Materia añadida exitosamente.", "Éxito");
                    } else {
                        showAlert(newSubject.error || "Error al añadir la materia.", "Error");
                    }
                } catch (e) { 
                    showAlert("Error al conectar con el servidor."); 
                }
            });

            /**
             * Lista de materias: Eliminar materia específica
             */
            subjectsList.addEventListener('click', async e => {
                const button = e.target.closest('button.delete-subject-btn');
                if (button) {
                    const subjectId = button.dataset.subjectId;
                    
                    showConfirm(`¿Eliminar esta materia?`, async () => {
                        try {
                            const response = await fetch(`/admin/api/materias/${subjectId}`, { 
                                method: 'DELETE' 
                            });
                            const result = await response.json();
                            
                            if (response.ok) {
                                // Remueve de la lista local
                                allSubjects = allSubjects.filter(s => s.id != subjectId);
                                renderGlobalResourcesUI();
                                showAlert("Materia eliminada exitosamente.", "Éxito");
                            } else {
                                showAlert(result.error || "Error al eliminar la materia.", "Error");
                            }
                        } catch (e) { 
                            showAlert("Error al conectar con el servidor."); 
                        }
                    });
                }
            });

            // ========================================
            // EVENT LISTENERS - FUNCIONALIDADES LOCALES
            // Eventos que manejan datos en localStorage
            // ========================================
            
            /**
             * Botón: Asignar horario a cursos específicos
             * Abre modal con lista de cursos disponibles
             */
            assignScheduleBtn.addEventListener('click', () => {
                if (!currentSchedule) {
                    return showAlert('Por favor, seleccione un horario para asignar.');
                }
                
                // Actualiza el título del modal
                document.getElementById('schedule-name-to-assign').textContent = `"${currentSchedule.nombre}"`;
                const courseListContainer = document.getElementById('course-assignment-list');
                courseListContainer.innerHTML = '';

                // Obtiene todos los nombres de cursos del DOM
                const allCourseNames = Array.from(document.querySelectorAll('.course-row'))
                    .map(row => row.dataset.courseName);
                
                // Crea checkboxes para cada curso
                allCourseNames.forEach(courseName => {
                    const assignment = courseAssignments[courseName];
                    const isAssignedToThis = assignment?.scheduleName === currentSchedule.nombre;
                    const isAssignedToOther = assignment?.scheduleName && 
                                            assignment.scheduleName !== currentSchedule.nombre;

                    const listItem = document.createElement('label');
                    listItem.className = `list-group-item d-flex justify-content-between align-items-center ${isAssignedToOther ? 'disabled' : ''}`;
                    listItem.innerHTML = `
                        <div>
                            <input class="form-check-input me-2" type="checkbox" value="${courseName}" 
                                   ${isAssignedToThis ? 'checked' : ''} ${isAssignedToOther ? 'disabled' : ''}>
                            ${courseName}
                        </div>
                        ${isAssignedToOther ? `<span class="badge bg-secondary rounded-pill">${assignment.scheduleName}</span>` : ''}
                    `;
                    courseListContainer.appendChild(listItem);
                });
                
                assignScheduleModal.show();
            });
            /**
             * Botón: Guardar asignaciones de cursos a horarios
             * Procesa checkboxes y actualiza localStorage
             */
            document.getElementById('save-assignment-btn').addEventListener('click', () => {
                const checkboxes = document.querySelectorAll('#course-assignment-list input[type="checkbox"]');
                
                checkboxes.forEach(checkbox => {
                    if(checkbox.disabled) return;  // Ignora checkboxes deshabilitados
                    
                    const courseName = checkbox.value;
                    if (checkbox.checked) {
                        // Asigna el horario al curso
                        if (!courseAssignments[courseName]) {
                            courseAssignments[courseName] = { 
                                scheduleName: null, 
                                subjects: {}, 
                                resources: [] 
                            };
                        }
                        courseAssignments[courseName].scheduleName = currentSchedule.nombre;
                    } else {
                        // Desasigna el horario del curso si estaba asignado a este horario
                        if (courseAssignments[courseName]?.scheduleName === currentSchedule.nombre) {
                            courseAssignments[courseName].scheduleName = null;
                        }
                    }
                });
                
                saveLocalData();                    // Persiste en localStorage
                assignScheduleModal.hide();         // Cierra el modal
                showAlert('Asignaciones guardadas correctamente.', 'Éxito');
            });

            /**
             * Event listener: Selección de cursos en las tablas
             * Maneja clicks en filas de cursos para mostrar su horario
             */
            document.getElementById('sedeTabContent').addEventListener('click', function(e) {
                const row = e.target.closest('.course-row');
                if (!row) return;

                // Cambia automáticamente a la pestaña de horario de curso
                bootstrap.Tab.getOrCreateInstance(horarioCursoTabEl).show();
                
                // Resalta la fila seleccionada
                document.querySelectorAll('.course-row').forEach(r => r.classList.remove('table-primary'));
                row.classList.add('table-primary');
                
                const courseName = row.dataset.courseName;
                const assignment = courseAssignments[courseName];
                const scheduleName = assignment?.scheduleName;

                // Verifica si el curso tiene horario asignado
                if (!scheduleName || !horarios.find(h => h.nombre === scheduleName)) {
                    scheduleDisplay.innerHTML = `
                        <div class="p-4 d-flex flex-column align-items-center justify-content-center h-100">
                            <div>Este curso no tiene un horario asignado.</div>
                            <div class="mt-2">Puede asignarle uno desde la pestaña 'Horario General'.</div>
                        </div>
                    `;
                    return;
                }
                
                // Renderiza la grilla de horario para el curso
                renderCourseScheduleGrid(courseName, scheduleName);
            });

            // ========================================
            // RENDERIZADO DE HORARIOS POR CURSO
            // Funciones para mostrar horarios específicos de cada curso
            // ========================================
            
            /**
             * Renderiza la grilla interactiva de horario para un curso específico
             * Crea una tabla con slots de tiempo y dropdowns para asignar materias
             * 
             * @param {string} courseName - Nombre del curso
             * @param {string} scheduleName - Nombre del horario asignado al curso
             */
            function renderCourseScheduleGrid(courseName, scheduleName) {
                const scheduleData = horarios.find(h => h.nombre === scheduleName);
                if (!scheduleData) 
                    return;

                const days = scheduleData.diasSemana ? 
                           scheduleData.diasSemana.split(',').filter(d => d) : [];
                const courseResources = courseAssignments[courseName]?.resources || [];

                // Calcula la línea de tiempo completa (clases + descansos)
                const timeline = [];
                
                // Añade bloques de clase para cada día
                days.forEach(day => {
                    const classBlocks = calculateClassBlocks(scheduleData);
                    classBlocks.forEach(block => {
                        let currentTime = timeToDecimal(block.start);
                        const endTime = timeToDecimal(block.end);
                        const slotDuration = 1; // 1 hora por slot por defecto
                        
                        // Divide cada bloque en slots de 1 hora
                        while (currentTime < endTime - 0.01) {
                            const slotEnd = Math.min(currentTime + slotDuration, endTime);
                            timeline.push({ 
                                type: 'class', 
                                day: day, 
                                start: currentTime, 
                                end: slotEnd 
                            });
                            currentTime = slotEnd;
                        }
                    });

                    // Añade períodos de descanso a la línea de tiempo
                    (scheduleData.descansos || []).forEach(b => {
                        const breakStart = timeToDecimal(b.horaInicio);
                        const breakEnd = breakStart + b.duracion / 60;
                        timeline.push({ 
                            type: 'break', 
                            day: day, 
                            start: breakStart, 
                            end: breakEnd 
                        });
                    });
                });
                
                if (timeline.length === 0) {
                    scheduleDisplay.innerHTML = `
                        <div class="d-flex align-items-center justify-content-center h-100">
                            No hay horas de clase definidas en este horario.
                        </div>
                    `;
                    return;
                }
                
                // Agrupa eventos por franjas horarias idénticas
                const eventsBySlot = timeline.reduce((acc, event) => {
                    const key = `${event.start.toFixed(5)}-${event.end.toFixed(5)}`;
                    if (!acc[key]) {
                        acc[key] = { 
                            start: event.start, 
                            end: event.end, 
                            type: event.type, 
                            events: [] 
                        };
                    }
                    acc[key].events.push(event);
                    return acc;
                }, {});

                const sortedSlots = Object.values(eventsBySlot).sort((a, b) => a.start - b.start);

                // Genera HTML del header con botones de acción
                let headerHTML = `
                    <div class="schedule-grid-container p-3">
                        <div class="schedule-grid-header d-flex justify-content-between align-items-center mb-3">
                            <h5 class="text-principal mb-0">Horario de ${courseName}</h5>
                            <div class="btn-group" role="group">
                                <button class="btn btn-sm btn-primary" id="save-schedule-btn" title="Guardar cambios">
                                    <i class="fa-solid fa-save me-1"></i>Guardar
                                </button>
                                <button class="btn btn-sm btn-danger" id="clear-schedule-btn" title="Limpiar todas las materias">
                                    <i class="fa-solid fa-trash me-1"></i>Limpiar
                                </button>
                                <button class="btn btn-sm btn-secondary" id="pdf-schedule-btn" title="Exportar a PDF">
                                    <i class="fa-solid fa-file-pdf me-1"></i>PDF
                                </button>
                            </div>
                        </div>
                `;
                
                // Genera HTML de la tabla de horarios
                let tableHTML = `
                    <div class="table-responsive">
                        <table class="table schedule-grid" id="schedule-grid-table">
                            <thead>
                                <tr>
                                    <th class="hour-label">Hora</th>
                `;
                
                // Añade columnas para cada día
                days.forEach(day => { 
                    tableHTML += `<th>${day}</th>`; 
                });
                tableHTML += `</tr></thead><tbody>`;

                // Genera filas para cada slot de tiempo
                sortedSlots.forEach(slot => {
                    const hourLabel = `${formatTime12(decimalToTime(slot.start))} - ${formatTime12(decimalToTime(slot.end))}`;
                    
                    if (slot.type === 'break') {
                        // Fila especial para períodos de descanso
                        tableHTML += `
                            <tr class="break-row" style="height: auto; min-height: 40px;">
                                <td class="hour-label">${hourLabel}</td>
                                <td colspan="${days.length}">Descanso</td>
                            </tr>
                        `;
                    } else {
                        // Fila normal para períodos de clase
                        tableHTML += `<tr><td class="hour-label">${hourLabel}</td>`;
                        
                        days.forEach(day => {
                            const eventOnThisDay = slot.events.find(e => e.day === day);
                            if (eventOnThisDay) {
                                // Crea clave única para identificar este slot
                                const timeKey = `${decimalToTime(eventOnThisDay.start).replace(":", "")}_${day}`;
                                const savedSubject = courseAssignments[courseName]?.subjects?.[day]?.[timeKey] || '';
                                
                                // Crea dropdown para seleccionar materia
                                let selectHTML = `
                                    <div>
                                        <select class="form-select form-select-sm subject-select" 
                                                data-day="${day}" data-time-key="${timeKey}">
                                            <option value="">Asignar...</option>
                                `;
                                
                                // Añade opciones basadas en recursos del curso
                                courseResources.forEach(res => {
                                    selectHTML += `
                                        <option value="${res.subject}" ${savedSubject === res.subject ? 'selected' : ''}>
                                            ${res.subject}
                                        </option>
                                    `;
                                });
                                
                                selectHTML += `
                                        </select>
                                        <div class="subject-details"></div>
                                    </div>
                                `;
                                tableHTML += `<td>${selectHTML}</td>`;
                            } else {
                                // Slot inactivo (no hay clase en este día/hora)
                                tableHTML += `<td class="inactive-slot"></td>`;
                            }
                        });
                        tableHTML += `</tr>`;
                    }
                });

                tableHTML += `</tbody></table></div></div>`;
                scheduleDisplay.innerHTML = headerHTML + tableHTML;

                // Configura event listeners para los dropdowns de materias
                scheduleDisplay.querySelectorAll('.subject-select').forEach(select => {
                    updateSubjectDetails(select, courseResources);
                    select.addEventListener('change', () => updateSubjectDetails(select, courseResources));
                });
            }

            /**
             * Actualiza la información adicional de la materia (profesor/salón)
             * Se muestra debajo del dropdown de materia
             * 
             * @param {HTMLElement} selectElement - Elemento select de materia
             * @param {Array} courseResources - Lista de recursos del curso
             */
            function updateSubjectDetails(selectElement, courseResources) {
                const detailsDiv = selectElement.nextElementSibling;
                const selectedSubject = selectElement.value;
                if (!detailsDiv) return;
                
                if (!selectedSubject) {
                    detailsDiv.innerHTML = '';
                    return;
                }
                
                // Busca el recurso correspondiente a la materia seleccionada
                const resource = courseResources.find(r => r.subject === selectedSubject);
                if (resource) {
                    detailsDiv.innerHTML = `${resource.teacher} / ${resource.classroom}`;
                } else {
                    detailsDiv.innerHTML = '';
                }
            }

            // ========================================
            // EVENT LISTENERS PARA ACCIONES DEL HORARIO
            // Manejo de botones en la grilla de horario del curso
            // ========================================
            
            /**
             * Event listener para botones de acción en el horario de curso
             * Maneja guardar, limpiar y exportar PDF
             */
            scheduleDisplay.addEventListener('click', e => {
                const target = e.target.closest('button');
                if (!target) return;
                
                const activeCourseRow = document.querySelector('.course-row.table-primary');
                if (!activeCourseRow) return;
                const courseName = activeCourseRow.dataset.courseName;

                if (target.id === 'save-schedule-btn') {
                    // Guardar horario: recolecta todas las asignaciones
                    const newSubjects = {};
                    const inputs = scheduleDisplay.querySelectorAll('.subject-select');
                    
                    inputs.forEach(input => {
                        const { day, timeKey } = input.dataset;
                        const subject = input.value;
                        if (subject) {
                            if (!newSubjects[day]) newSubjects[day] = {};
                            newSubjects[day][timeKey] = subject;
                        }
                    });

                    // Actualiza la estructura de datos local
                    if (!courseAssignments[courseName]) {
                        courseAssignments[courseName] = { 
                            scheduleName: null, 
                            subjects: {}, 
                            resources: [] 
                        };
                    }
                    courseAssignments[courseName].subjects = newSubjects;
                    saveLocalData();
                    showAlert('Horario guardado correctamente.', 'Éxito');
                }
                else if (target.id === 'clear-schedule-btn') { 
                    // Limpiar horario: elimina todas las asignaciones de materias
                    showConfirm(
                        `¿Estás seguro de que quieres limpiar todas las materias del horario de ${courseName}?`, 
                        () => { 
                            if (courseAssignments[courseName]) { 
                                courseAssignments[courseName].subjects = {}; 
                                saveLocalData(); 
                                activeCourseRow.click(); // Refresca la vista
                                showAlert('El horario ha sido limpiado.', 'Éxito'); 
                            } 
                        }
                    ); 
                }
                else if (target.id === 'pdf-schedule-btn') { 
                    // Exportar PDF: genera y descarga el horario
                    generateAndDownloadPdf(courseName); 
                }
            });

            // ========================================
            // GENERACIÓN Y DESCARGA DE PDF
            // Funcionalidad para exportar horarios a PDF
            // ========================================
            
            /**
             * Genera y descarga un PDF del horario del curso
             * Utiliza html2canvas para capturar la tabla y jsPDF para crear el archivo
             * 
             * @param {string} courseName - Nombre del curso para el PDF
             */
            function generateAndDownloadPdf(courseName) {
                const originalTable = document.getElementById('schedule-grid-table');
                if (!originalTable) { 
                    return showAlert('No hay horario visible para generar el PDF.'); 
                }

                showAlert('Generando PDF...', 'Procesando');
                
                // Clona la tabla para procesamiento sin afectar la original
                const tableClone = originalTable.cloneNode(true);
                tableClone.id = '';
                tableClone.style.width = '1000px';  // Ancho fijo para mejor renderizado
                
                // Convierte dropdowns a texto plano para el PDF
                tableClone.querySelectorAll('td').forEach(td => {
                    const select = td.querySelector('.subject-select');
                    if (select) {
                        const subjectValue = select.value;
                        const detailsDiv = td.querySelector('.subject-details');
                        let contentHTML = '';

                        if (subjectValue) {
                            contentHTML = `<strong>${subjectValue}</strong>`;
                            if (detailsDiv && detailsDiv.textContent) {
                                contentHTML += `<span class="subject-details-pdf">${detailsDiv.textContent}</span>`;
                            }
                        }
                        td.innerHTML = contentHTML;
                    }
                });
                
                // Crea elemento temporal fuera de la vista para renderizado
                const tempDiv = document.createElement('div');
                tempDiv.style.position = 'absolute';
                tempDiv.style.left = '-9999px'; 
                tempDiv.style.padding = '10px';
                tempDiv.style.backgroundColor = 'white';
                tempDiv.appendChild(tableClone);
                document.body.appendChild(tempDiv);
                
                // Genera PDF usando html2canvas y jsPDF
                setTimeout(() => {
                    html2canvas(tempDiv.querySelector('table'), { 
                        scale: 2,                              // Alta resolución
                        backgroundColor: '#ffffff' 
                    })
                    .then(canvas => {
                        const { jsPDF } = window.jspdf;
                        const pdf = new jsPDF({ 
                            orientation: 'landscape',          // Orientación horizontal para tablas
                            unit: 'pt', 
                            format: 'a4' 
                        });

                        // Calcula dimensiones y posicionamiento óptimo
                        const page_width = pdf.internal.pageSize.getWidth();
                        const page_height = pdf.internal.pageSize.getHeight();
                        const margin = 30;
                        const title_height = 20;

                        const available_width = page_width - (margin * 2);
                        const available_height = page_height - (margin * 2) - title_height;

                        const canvas_width = canvas.width;
                        const canvas_height = canvas.height;

                        // Calcula escala para ajustar a la página
                        const width_ratio = available_width / canvas_width;
                        const height_ratio = available_height / canvas_height;
                        const scale = Math.min(width_ratio, height_ratio);

                        const final_img_width = canvas_width * scale;
                        const final_img_height = canvas_height * scale;
                        const pos_x = margin + (available_width - final_img_width) / 2;
                        const pos_y = margin + title_height;

                        // Añade título e imagen al PDF
                        pdf.text(`Horario de ${courseName}`, margin, margin);
                        pdf.addImage(
                            canvas.toDataURL('image/png'), 
                            'PNG', 
                            pos_x, pos_y, 
                            final_img_width, final_img_height
                        );
                        
                        // Descarga el archivo
                        pdf.save(`horario_${courseName}.pdf`);
                        showAlert('PDF generado exitosamente.', 'Éxito');
                    })
                    .catch(err => { 
                        console.error('Error al generar PDF:', err); 
                        showAlert('Error al generar el PDF.', 'Error'); 
                    })
                    .finally(() => { 
                        document.body.removeChild(tempDiv); 
                    });
                }, 200);  // Pequeño delay para asegurar renderizado
            }

            // ========================================
            // GESTIÓN DE RECURSOS ADICIONALES
            // Configuración de materias, profesores y salones por curso
            // ========================================
            
            /**
             * Botón: Abrir configuración de recursos adicionales
             * Permite configurar materias, profesores y salones para un curso
             */
            additionalSettingsBtn.addEventListener('click', () => {
                const activeCourseRow = document.querySelector('.course-row.table-primary');
                if (!activeCourseRow) {
                    return showAlert('Por favor, primero seleccione un curso de la lista.');
                }
                
                const courseName = activeCourseRow.dataset.courseName;
                document.getElementById('settings-course-name').textContent = courseName;
                
                // Popula dropdown de materias con datos del servidor
                populateResourceSelects('subject-name-select', allSubjects.map(s => s.nombre));
                
                // Limpia formulario
                document.getElementById('teacher-name-input').value = '';
                document.getElementById('classroom-name-input').value = '';

                renderResourceList(courseName);
                additionalSettingsModal.show();
            });

            /**
             * Popula un elemento select con opciones dinámicas
             * @param {string} selectId - ID del elemento select
             * @param {Array} optionsArray - Array de opciones a mostrar
             */
            function populateResourceSelects(selectId, optionsArray) {
                const select = document.getElementById(selectId);
                select.innerHTML = '<option value="">Seleccionar...</option>';
                optionsArray.forEach(option => {
                    select.innerHTML += `<option value="${option}">${option}</option>`;
                });
            }

            /**
             * Renderiza la tabla de recursos configurados para un curso
             * @param {string} courseName - Nombre del curso
             */
            function renderResourceList(courseName) {
                const resourceListEl = document.getElementById('resource-list');
                resourceListEl.innerHTML = '';
                const resources = courseAssignments[courseName]?.resources || [];
                
                resources.forEach((res, index) => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${res.subject}</td>
                        <td>${res.teacher}</td>
                        <td>${res.classroom}</td>
                        <td>
                            <button class="btn btn-sm btn-outline-danger" data-index="${index}">
                                <i class="fa-solid fa-trash"></i>
                            </button>
                        </td>
                    `;
                    resourceListEl.appendChild(tr);
                });
            }

            /**
             * Botón: Añadir nuevo recurso al curso
             * Combina materia + profesor + salón como un recurso
             */
            document.getElementById('add-resource-btn').addEventListener('click', () => {
                const courseName = document.getElementById('settings-course-name').textContent;
                const subject = document.getElementById('subject-name-select').value;
                const teacher = document.getElementById('teacher-name-input').value.trim();
                const classroom = document.getElementById('classroom-name-input').value.trim();

                // Validación de campos requeridos
                if (!subject || !teacher || !classroom) {
                    return showAlert('Todos los campos son obligatorios.');
                }
                
                // Inicializa estructura de datos si no existe
                if (!courseAssignments[courseName]) {
                    courseAssignments[courseName] = { 
                        scheduleName: null, 
                        subjects: {}, 
                        resources: [] 
                    };
                }
                
                // Verifica duplicados de materia
                if(courseAssignments[courseName].resources.some(r => r.subject === subject)) {
                    return showAlert(`La materia "${subject}" ya ha sido añadida a este curso.`);
                }

                // Añade el nuevo recurso
                courseAssignments[courseName].resources.push({ subject, teacher, classroom });
                
                // Actualiza listas globales si es necesario
                if (!allTeachers.includes(teacher)) allTeachers.push(teacher);
                if (!allClassrooms.includes(classroom)) allClassrooms.push(classroom);
                
                saveLocalData();
                renderResourceList(courseName);

                // Limpia el formulario
                document.getElementById('subject-name-select').selectedIndex = 0;
                document.getElementById('teacher-name-input').value = '';
                document.getElementById('classroom-name-input').value = '';

                // Refresca la vista del horario si está activa
                const activeCourseRow = document.querySelector('.course-row.table-primary');
                if (activeCourseRow && activeCourseRow.dataset.courseName === courseName) {
                    activeCourseRow.click();
                }
                
                showAlert('Recurso añadido exitosamente.', 'Éxito');
            });

            /**
             * Lista de recursos: Eliminar recurso específico
             * Event delegation para botones dinámicos
             */
            document.getElementById('resource-list').addEventListener('click', e => {
                const button = e.target.closest('button');
                if(button){
                    const courseName = document.getElementById('settings-course-name').textContent;
                    const index = button.dataset.index;
                    
                    // Elimina el recurso del array
                    courseAssignments[courseName].resources.splice(index, 1);
                    saveLocalData();
                    renderResourceList(courseName);
                    
                    // Refresca la vista del horario si está activa
                    const activeCourseRow = document.querySelector('.course-row.table-primary');
                    if (activeCourseRow && activeCourseRow.dataset.courseName === courseName) {
                        activeCourseRow.click();
                    }
                    
                    showAlert('Recurso eliminado exitosamente.', 'Éxito');
                }
            });

            // ========================================
            // INICIALIZACIÓN DE LA APLICACIÓN
            // Carga inicial de datos y configuración de la UI
            // ========================================
            
            /** * Secuencia de inicialización de la aplicación
             * 1. Carga datos locales desde localStorage
             * 2. Obtiene datos del servidor Flask
             * 3. Actualiza toda la interfaz de usuario
             */
            loadLocalData();    // Carga configuraciones locales
            fetchData();        // Obtiene datos del servidor
            updateUI();         // Sincroniza la interfaz
        });
          