// ===== SMARTCARGO CLIENTE =====
let cargoRules = {};
let aviancaRules = {};

// Cargar reglas desde JSON
async function loadRules() {
    const cargoRes = await fetch("/static/cargo_rules.json");
    cargoRules = await cargoRes.json();

    const aviRes = await fetch("/static/avianca_rules.json");
    aviancaRules = await aviRes.json();
}

// Función principal de validación en cliente
async function validateShipment() {
    const role = document.getElementById("role").value;
    const cargo_type = document.getElementById("cargo_type").value;
    const documentsInput = document.getElementById("documents").value.split(",").map(d => d.trim()).filter(d => d);
    const pieces = parseInt(document.getElementById("pieces").value);
    const gross_weight = parseFloat(document.getElementById("gross_weight").value);
    const volume = parseFloat(document.getElementById("volume").value);
    const known_shipper = document.getElementById("known_shipper").value === "true";
    const screening = document.getElementById("screening").value;
    const regulated_agent = document.getElementById("regulated_agent").value === "true";

    // Trazabilidad
    const trace = {
        uploaded_by: role,
        timestamp: new Date().toISOString(),
        errors_detected: []
    };

    // Validación documentos según tipo de carga
    const requiredDocs = cargoRules[cargo_type]?.documents || [];
    requiredDocs.forEach(doc => {
        if(!documentsInput.includes(doc)) {
            trace.errors_detected.push(`Falta documento obligatorio: ${doc}`);
        }
    });

    // Validación checklist Avianca (simplificada)
    aviancaRules.folder_order.forEach(doc => {
        if(doc.includes("invoice") && !documentsInput.includes("invoice")) {
            trace.errors_detected.push(`Invoice no cumple checklist Avianca`);
        }
        if(doc.includes("packing_list") && !documentsInput.includes("packing_list")) {
            trace.errors_detected.push(`Packing List no cumple checklist Avianca`);
        }
    });

    // Validación física
    if(pieces <= 0) trace.errors_detected.push("Número de piezas inválido");
    if(gross_weight <= 0) trace.errors_detected.push("Peso inválido");
    if(volume <= 0) trace.errors_detected.push("Volumen inválido");

    // Validación seguridad
    if(!known_shipper) trace.errors_detected.push("Shipper no autorizado");
    if(screening !== "xray") trace.errors_detected.push("No se ha realizado screening X-Ray");
    if(!regulated_agent) trace.errors_detected.push("No es Regulated Agent");

    // Resultado final
    const status = trace.errors_detected.length === 0 ? "GREEN" : "RED";

    // Mostrar resultado según rol
    const resultDiv = document.getElementById("result");
    const traceDiv = document.getElementById("trace");
    resultDiv.style.display = "block";
    traceDiv.innerHTML = "";

    if(status === "GREEN"){
        resultDiv.className = "result green";
        switch(role){
            case "truck": resultDiv.innerHTML = "GREEN LIGHT ✅<br>Puedes ir al warehouse"; break;
            case "forwarder": resultDiv.innerHTML = "GREEN LIGHT ✅<br>Todos los documentos correctos"; break;
            case "warehouse": resultDiv.innerHTML = "ACEPTAR ✅"; break;
            case "owner": resultDiv.innerHTML = "ESTATUS: GREEN<br>Riesgo: Bajo"; break;
        }
    } else {
        resultDiv.className = "result red";
        switch(role){
            case "truck": resultDiv.innerHTML = "RED LIGHT ❌<br>No vayas al warehouse"; break;
            case "forwarder": resultDiv.innerHTML = "RED LIGHT ❌<br>Documentos faltantes o errores:"; break;
            case "warehouse": resultDiv.innerHTML = "HOLD / RECHAZAR ❌"; break;
            case "owner": resultDiv.innerHTML = "ESTATUS: RED<br>Riesgo: Alto"; break;
        }

        // Mostrar errores
        trace.errors_detected.forEach(err => {
            const li = document.createElement("div");
            li.textContent = "• " + err;
            traceDiv.appendChild(li);
        });
    }

    // Mostrar trazabilidad
    const timeDiv = document.createElement("div");
    timeDiv.style.marginTop = "10px";
    timeDiv.style.fontSize = "12px";
    timeDiv.style.opacity = "0.7";
    timeDiv.textContent = `Trazabilidad: ${trace.uploaded_by} @ ${new Date(trace.timestamp).toLocaleString()}`;
    traceDiv.appendChild(timeDiv);
}

// Evento botón
document.getElementById("validateBtn").addEventListener("click", validateShipment);

// Cargar reglas al inicio
loadRules();
