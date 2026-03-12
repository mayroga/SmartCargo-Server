let pieceCount = 0;
const maxPieces = 5;

function toggleCurtain(id) {
  const el = document.getElementById(id);
  el.style.display = (el.style.display === 'block') ? 'none' : 'block';
}

// ====================== Piezas y Dimensiones ======================
function addPiece() {
  if (pieceCount >= maxPieces) return alert("Máximo 5 piezas.");
  pieceCount++;
  const container = document.getElementById("piecesContainer");
  const div = document.createElement("div");
  div.id = `piece${pieceCount}`;
  div.innerHTML = `
    <h4>Pieza ${pieceCount}</h4>
    <label>Largo (cm):</label><input type="number" class="largo" oninput="calcularVolumen()">
    <label>Ancho (cm):</label><input type="number" class="ancho" oninput="calcularVolumen()">
    <label>Alto (cm):</label><input type="number" class="alto" oninput="calcularVolumen()">
    <label>Peso (kg):</label><input type="number" class="peso" oninput="calcularVolumen()">
    <label>Volumen:</label><input type="text" class="volumen" readonly>
    <p class="alert"></p>
  `;
  container.appendChild(div);
  calcularVolumen();
}

function calcularVolumen() {
  let alerts = [];
  let totalVolume = 0;
  let tallest = 0, widest = 0, longest = 0, heaviest = 0;

  for (let i=1;i<=pieceCount;i++){
    const div = document.getElementById(`piece${i}`);
    if(!div) continue;
    const L = parseFloat(div.querySelector(".largo").value) || 0;
    const W = parseFloat(div.querySelector(".ancho").value) || 0;
    const H = parseFloat(div.querySelector(".alto").value) || 0;
    const P = parseFloat(div.querySelector(".peso").value) || 0;

    const volumeM3 = (L*W*H)/1000000;
    div.querySelector(".volumen").value = `${volumeM3.toFixed(3)} m³ (${(volumeM3*35.3147).toFixed(2)} ft³)`;
    totalVolume += volumeM3;

    if(H>tallest) tallest=H;
    if(W>widest) widest=W;
    if(L>longest) longest=L;
    if(P>heaviest) heaviest=P;

    const alertEl = div.querySelector("p.alert");
    let alertMsg = "";
    if(H>244) alertMsg+="ALERTA: Altura excede carguero (244cm). ";
    else if(H>160) alertMsg+="ADVERTENCIA: Altura excede pasajero (160cm). ";
    if(L>318 || W>244) alertMsg+="ALERTA: Dimensiones exceden máximo permitido. ";
    if(P>6800) alertMsg+="ALERTA: Peso excede pallet (6800kg).";
    alertEl.innerText = alertMsg;
  }

  const alertDim = document.getElementById("alertDimensiones");
  alertDim.innerText = tallest>0 ? `Volumen total: ${totalVolume.toFixed(3)} m³` : "";
}

// ====================== Documentos ======================
function mostrarDocumentos() {
  const tipo = document.getElementById('tipoCarga').value;
  fetch("/static/cargo_rules.json")
  .then(r=>r.json())
  .then(data=>{
    const docs = data[tipo];
    if(!docs){
      document.getElementById("documentos").innerText = "Documentos no disponibles.";
      return;
    }
    let html = `<strong>Documentos obligatorios:</strong> ${docs.documents.join(", ")}<br>
                <strong>Copias dentro/afuera:</strong> ${docs.copies_inside}/${docs.copies_outside}<br>
                <strong>Notas:</strong> ${docs.notes}`;
    document.getElementById("documentos").innerHTML = html;
  });
}

// ====================== Rol Alternativo ======================
function actualizarRol() {
  const rol = document.getElementById('rol').value;
  let opciones = "";
  if(rol==="Chofer" || rol==="Camionero") opciones="Forwarder, Dueño, Counter";
  if(rol==="Forwarder") opciones="Chofer, Dueño, Counter";
  document.getElementById("rolAlternativo").innerText = opciones;
}

// ====================== Validación y Simulación ======================
function validarCarga() {
  const resultDiv = document.getElementById("resultadoValidacion");
  resultDiv.innerHTML = "<strong>Validación ejecutada:</strong> Revise alertas y documentos obligatorios.";
}

function simularVuelo() {
  const resultDiv = document.getElementById("resultadoVuelo");
  // Ejemplo: reemplazar con datos reales de backend
  const vuelo = "AV11";
  const salida = "21:45";
  const cutoff = "18:00";
  const capacidad = 3;
  resultDiv.innerHTML = `<strong>Simulación de vuelo:</strong><br>
                         Vuelo: ${vuelo}<br>
                         Salida: ${salida}<br>
                         Cutoff: ${cutoff}<br>
                         Capacidad disponible: ${capacidad} pallets<br>
                         <strong>Resultado:</strong> TU CARGA VUELA HOY.`;
}
