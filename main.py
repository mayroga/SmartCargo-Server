<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Smart Cargo - PreCheck System</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <style>
    body {
      font-family: Arial, sans-serif;
      background: #0b0f1a;
      color: #fff;
      margin: 0;
      padding: 0;
    }

    header {
      background: #111a2e;
      padding: 15px;
      text-align: center;
      font-size: 20px;
      font-weight: bold;
    }

    .container {
      padding: 15px;
    }

    textarea, input, select {
      width: 100%;
      padding: 10px;
      margin-top: 5px;
      margin-bottom: 10px;
      border-radius: 8px;
      border: none;
    }

    button {
      background: #1f6feb;
      color: white;
      padding: 12px;
      border: none;
      border-radius: 10px;
      width: 100%;
      font-size: 16px;
      margin-top: 10px;
    }

    .block {
      background: #111a2e;
      padding: 15px;
      margin-top: 15px;
      border-radius: 10px;
    }

    .status-green { color: #00ff88; font-weight: bold; }
    .status-yellow { color: #ffcc00; font-weight: bold; }
    .status-red { color: #ff3b3b; font-weight: bold; }

    .doc {
      padding: 5px;
      border-left: 3px solid #1f6feb;
      margin: 5px 0;
    }

    .error { color: #ff3b3b; }
    .warn { color: #ffcc00; }
  </style>
</head>

<body>

<header>🚀 SMART CARGO - PRE CHECK AVIATION SYSTEM</header>

<div class="container">

  <!-- =========================
  DATOS CLIENTE / OPERACIÓN
  ========================== -->
  <div class="block">
    <h3>📦 Datos del Cliente y Operación</h3>

    <input id="shipper" placeholder="Shipper">
    <input id="consignee" placeholder="Consignatario">
    <input id="awb" placeholder="Número AWB">
    <input id="airline" placeholder="Aerolínea">
    <input id="origin" placeholder="Origen">
    <input id="destination" placeholder="Destino">
    <input id="service" placeholder="Tipo de servicio">
    <input id="date" type="date">
  </div>

  <!-- =========================
  MERCANCÍA
  ========================== -->
  <div class="block">
    <h3>📦 Datos de la Mercancía</h3>

    <textarea id="raw_text" placeholder="Describe la carga (voz, texto, copia, pega...)"></textarea>

    <input id="pieces" placeholder="Piezas (JSON simple)">
  </div>

  <!-- =========================
  BOTONES INPUT
  ========================== -->
  <div class="block">
    <h3>🎤 Captura Inteligente</h3>

    <button onclick="startMic()">🎤 Micrófono</button>
    <button onclick="submitData()">🚀 Ejecutar PreCheck</button>
  </div>

  <!-- =========================
  RESULTADO FINAL
  ========================== -->
  <div id="result" class="block"></div>

</div>

<script>
async function submitData() {

  let pieces = [];

  try {
    pieces = JSON.parse(document.getElementById("pieces").value || "[]");
  } catch (e) {
    alert("Error en piezas JSON");
    return;
  }

  const payload = {
    user_role: "driver",
    cargo_type: "AUTO",
    raw_text: document.getElementById("raw_text").value,
    destination: document.getElementById("destination").value,
    pieces: pieces
  };

  const res = await fetch("/precheck", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });

  const data = await res.json();

  renderResult(data);
}

function renderResult(data) {

  let html = "";

  // =========================
  // STATUS FINAL
  // =========================
  let statusClass = "status-green";
  if (data.status === "RISK") statusClass = "status-yellow";
  if (data.status === "REJECT") statusClass = "status-red";

  html += `<h2>📊 Resultado Final</h2>`;
  html += `<p class="${statusClass}">${data.status}</p>`;
  html += `<p>${data.driver_message || ""}</p>`;

  // =========================
  // TIPO CARGA
  // =========================
  html += `<div class="block">
    <h3>🧠 Clasificación Automática</h3>
    <p>${data.cargo_type_detected}</p>
  </div>`;

  // =========================
  // ERRORES
  // =========================
  html += `<div class="block">
    <h3>❌ Errores Detectados</h3>`;

  (data.errors || []).forEach(e => {
    html += `<p class="error">${e}</p>`;
  });

  html += `</div>`;

  // =========================
  // WARNINGS
  // =========================
  html += `<div class="block">
    <h3>⚠️ Advertencias</h3>`;

  (data.warnings || []).forEach(w => {
    html += `<p class="warn">${w}</p>`;
  });

  html += `</div>`;

  // =========================
  // CORRECCIONES
  // =========================
  html += `<div class="block">
    <h3>🔧 Corrección Automática</h3>`;

  (data.fixes || []).forEach(f => {
    html += `<p>${f}</p>`;
  });

  html += `</div>`;

  // =========================
  // DOCUMENTOS
  // =========================
  html += `<div class="block">
    <h3>📑 Checklist Documental</h3>`;

  (data.required_docs || []).forEach(d => {
    html += `<div class="doc">${d}</div>`;
  });

  html += `</div>`;

  document.getElementById("result").innerHTML = html;
}

// =========================
// MIC FUNCTION (PLACEHOLDER)
// =========================
function startMic() {
  alert("Micrófono activado (integración futura WebSpeech API)");
}
</script>

</body>
</html>
