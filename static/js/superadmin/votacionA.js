const form = document.getElementById("form-candidato");
const lista = document.getElementById("lista-candidatos");
const resultados = document.getElementById("resultados");
const fotoPreview = document.getElementById("foto-preview"); // div o img para mostrar previsualización

const modalEditar = new bootstrap.Modal(document.getElementById("modalEditar"));
const formEditar = document.getElementById("form-editar");
const fotoPreviewEditar = document.getElementById("foto-preview-editar");

// --------------------
// Helper: fetch con manejo de errores
// --------------------
async function apiFetch(url, opts = {}) {
  try {
    const res = await fetch(url, { credentials: "same-origin", ...opts });
    const data = await res.json();
    return { ok: res.ok, status: res.status, data };
  } catch (err) {
    console.error("Error en apiFetch:", err);
    return { ok: false, status: 0, data: {} };
  }
}

// --------------------
// Previsualización de la foto
// --------------------
function mostrarFotoPreview(input, previewEl) {
  const file = input.files[0];
  if (!file) {
    previewEl.src = "";
    return;
  }
  const reader = new FileReader();
  reader.onload = e => previewEl.src = e.target.result;
  reader.readAsDataURL(file);
}

document.getElementById("foto").addEventListener("change", e => mostrarFotoPreview(e.target, fotoPreview));
document.getElementById("edit-foto").addEventListener("change", e => mostrarFotoPreview(e.target, fotoPreviewEditar));

// --------------------
// Mostrar resultados de votos
// --------------------
function mostrarResultados(candidatos) {
  resultados.innerHTML = "";

  if (!Array.isArray(candidatos) || candidatos.length === 0) {
    resultados.innerHTML = "<p class='text-muted'>No hay resultados disponibles.</p>";
    return;
  }

  const grouped = {};
  candidatos.forEach(c => {
    const cat = c.categoria || "Sin categoría";
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(c);
  });

  Object.keys(grouped).forEach(cat => {
    const resDiv = document.createElement("div");
    resDiv.innerHTML = `<h4>Resultados de ${cat}</h4>`;

    grouped[cat].forEach(c => {
      const nombre = c.nombre || "Sin nombre";
      const tarjeton = c.tarjeton || "N/A";
      const votos = c.votos ?? 0;
      resDiv.innerHTML += `<p>${nombre} (${tarjeton}): ${votos} votos</p>`;
    });

    resultados.appendChild(resDiv);
  });
}

// --------------------
// Cargar lista de candidatos
// --------------------
function cargarLista(candidatos) {
  lista.innerHTML = "";
  candidatos.forEach(c => {
    const div = document.createElement("div");
    div.className = "candidato border rounded p-3 my-2 d-flex justify-content-between align-items-start";
    div.innerHTML = `
      <div>
        <h3>${c.nombre} ${c.apellido || ""}</h3>
        <p><strong>Categoría:</strong> ${c.categoria}</p>
        <p><strong>Tarjetón:</strong> ${c.tarjeton}</p>
        <p><strong>Propuesta:</strong> ${c.propuesta}</p>
        ${c.foto ? `<img src="/static/images/candidatos/${c.foto}" width="150">` : ""}
      </div>
      <div>
        <button class="btn btn-warning btn-editar" data-id="${c.id}">Editar</button>
        <button class="btn btn-danger btn-eliminar" data-id="${c.id}">Eliminar</button>
      </div>
    `;
    lista.appendChild(div);
  });
  mostrarResultados(candidatos);
}

// --------------------
// Validación y envío de formulario
// --------------------
async function enviarFormulario(form, listaEl) {
  const formData = new FormData(form);
  const nombre = formData.get("nombre")?.trim();
  const apellido = formData.get("apellido")?.trim() || "";
  const tarjeton = formData.get("tarjeton")?.trim();
  const categoria = formData.get("categoria")?.trim();
  const propuesta = formData.get("propuesta")?.trim();
  const foto = formData.get("foto");

  if (!nombre || !tarjeton || !categoria || !propuesta || !foto?.name) {
    return alert("Por favor completa todos los campos, incluida la foto.");
  }

  // Evitar duplicados por nombre+apellido y tarjetón
  const duplicado = Array.from(listaEl.children).some(div => {
    const existingNombre = div.querySelector("h3")?.textContent?.trim() || "";
    const existingTarjeton = div.querySelector("p:nth-of-type(2)")?.textContent.replace("Tarjetón:", "").trim() || "";
    return (existingNombre.toLowerCase() === `${nombre} ${apellido}`.toLowerCase() || existingTarjeton === tarjeton);
  });

  if (duplicado) return alert("Ya existe un candidato con ese nombre o tarjetón.");

  // Renombrar foto para evitar sobrescribir
  const timestamp = Date.now();
  const extension = foto.name.split(".").pop();
  formData.set("foto", new File([foto], `${timestamp}.${extension}`, { type: foto.type }));

  const res = await apiFetch(form.action, { method: "POST", body: formData });
  if (!res.ok || !res.data.ok) return alert(res.data.error || "Error al crear candidato");

  cargarLista(res.data.candidatos);
  form.reset();
  if (form === formEditar) modalEditar.hide();
  else if (form === form) fotoPreview.src = "";
}

// --------------------
// Eventos
// --------------------
form?.addEventListener("submit", e => { e.preventDefault(); enviarFormulario(form, lista); });
formEditar?.addEventListener("submit", e => { e.preventDefault(); enviarFormulario(formEditar, lista); });

// Eliminar candidato
lista?.addEventListener("click", async e => {
  const btn = e.target.closest(".btn-eliminar");
  if (!btn) return;
  if (!confirm("¿Eliminar este candidato?")) return;

  const res = await apiFetch(`/admin/candidatos/${btn.dataset.id}`, { method: "DELETE" });
  if (!res.ok || !res.data.ok) return alert(res.data.error || "Error al eliminar");
  cargarLista(res.data.candidatos);
});

document.addEventListener("DOMContentLoaded", () => {
  const lista = document.getElementById("lista-candidatos");
  const modalEditar = new bootstrap.Modal(document.getElementById("modalEditar"));
  const formEditar = document.getElementById("form-editar");

  // Click en editar
  lista?.addEventListener("click", e => {
    const btn = e.target.closest(".btn-editar");
    if (!btn) return;

    const card = btn.closest(".candidato");
    const idEdit = btn.dataset.id;

    // Rellenar campos
    document.getElementById("edit-id").value = idEdit;
    document.getElementById("edit-nombre").value = card.querySelector("h3").textContent;
    document.getElementById("edit-tarjeton").value = card.querySelector("p:nth-of-type(2)").textContent.replace("Tarjetón:", "").trim();
    document.getElementById("edit-propuesta").value = card.querySelector("p:nth-of-type(3)").textContent.replace("Propuesta:", "").trim();
    document.getElementById("edit-categoria").value = card.querySelector("p:nth-of-type(1)").textContent.replace("Categoría:", "").trim();
    document.getElementById("edit-foto").value = ""; // limpiar input

    modalEditar.show();
  });

  // Guardar cambios
  formEditar?.addEventListener("submit", async e => {
    e.preventDefault();

    const id = document.getElementById("edit-id").value;
    const nombre = document.getElementById("edit-nombre").value.trim();
    const tarjeton = document.getElementById("edit-tarjeton").value.trim();
    const propuesta = document.getElementById("edit-propuesta").value.trim();
    const categoria = document.getElementById("edit-categoria").value;
    const fotoInput = document.getElementById("edit-foto");

    // Validar campos
    if (!nombre || !tarjeton || !propuesta || !categoria) {
      return alert("Todos los campos son obligatorios.");
    }

    // Validar tarjetón único
    const tarjetasExistentes = Array.from(document.querySelectorAll(".candidato")).filter(c => c.querySelector(".btn-editar").dataset.id !== id)
      .map(c => c.querySelector("p:nth-of-type(2)").textContent.replace("Tarjetón:", "").trim());

    if (tarjetasExistentes.includes(tarjeton)) {
      return alert("Este número de tarjetón ya está en uso.");
    }

    // Preparar FormData
    const formData = new FormData();
    formData.append("nombre", nombre);
    formData.append("tarjeton", tarjeton);
    formData.append("propuesta", propuesta);
    formData.append("categoria", categoria);
    if (fotoInput.files.length > 0) {
      formData.append("foto", fotoInput.files[0]);
    }

    // Enviar cambios al backend
    const res = await fetch(`/admin/candidatos/${id}`, {
      method: "POST",
      body: formData,
      credentials: "same-origin"
    });

    const data = await res.json();
    if (!res.ok || !data.ok) return alert(data.error || "Error al editar candidato");

    // Recargar lista y cerrar modal
    cargarLista(data.candidatos);
    modalEditar.hide();
  });
});


async function cargarUltimoHorario() {
  const res = await fetch("/admin/ultimo-horario", { credentials: "same-origin" });
  const data = await res.json();
  if (data.inicio && data.fin) {
    document.getElementById("inicio").value = data.inicio;
    document.getElementById("fin").value = data.fin;

    // Opcional: mostrar horario actual en el DOM
    const horarioActual = document.getElementById("horario-actual");
    if (horarioActual) {
      horarioActual.textContent = `${data.inicio} - ${data.fin}`;
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  cargarUltimoHorario();
});

// --------------------
// Inicializar candidatos
// --------------------
async function initCandidatos() {
  const res = await apiFetch("/admin/listar-candidatos");
  console.log("Respuesta de listar-candidatos:", res);

  if (res.ok && Array.isArray(res.data) && res.data.length > 0) {
    cargarLista(res.data);
  } else {
    console.warn("No se pudieron cargar los candidatos o la lista está vacía:", res.data);
    lista.innerHTML = "<p class='text-muted'>No hay candidatos registrados.</p>";
  }
}

document.addEventListener("DOMContentLoaded", initCandidatos);
