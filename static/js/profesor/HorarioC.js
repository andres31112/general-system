// Horas definidas para el horario
const horas = [
    "08:00 - 09:00",
    "09:00 - 10:00",
    "10:00 - 10:15", // Descanso
    "10:15 - 11:00",
    "11:00 - 12:00",
    "12:00 - 12:30", // Descanso
    "12:30 - 13:00",
    "13:00 - 14:00"
];

// Días de la semana
const dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"];

// Generar tabla en el DOM
document.addEventListener("DOMContentLoaded", function () {
    const cuerpoHorario = document.getElementById("cuerpo-horario");

    horas.forEach(hora => {
        const fila = document.createElement("tr");

        // Celda de la hora
        const celdaHora = document.createElement("td");
        celdaHora.classList.add("hour-label");
        celdaHora.textContent = hora;
        fila.appendChild(celdaHora);

        // Celdas por día
        dias.forEach(dia => {
            const celda = document.createElement("td");

            // Marcar descansos
            if (hora === "10:00 - 10:15" || hora === "12:00 - 12:30") {
                celda.textContent = "Descanso";
                celda.classList.add("break-row");
            } else {
                celda.textContent = "Libre"; // Por defecto
                celda.classList.add("inactive-slot");
            }

            fila.appendChild(celda);
        });

        cuerpoHorario.appendChild(fila);
    });
});
