// Función calcular volumen y validar límites según Avianca
function calcularVolumen() {
    let largo = parseFloat(document.getElementById('largo').value) || 0;
    let ancho = parseFloat(document.getElementById('ancho').value) || 0;
    let alto = parseFloat(document.getElementById('alto').value) || 0;
    let peso = parseFloat(document.getElementById('peso').value) || 0;

    // Volumen en m³
    let volumen = (largo * ancho * alto)/1000000;
    document.getElementById('volumen').value = volumen.toFixed(3) + ' m³';

    // Validaciones de altura
    if(alto > 244){
        document.getElementById('alertAltura').innerText = "ALERTA: Altura excede límite de carguero (244 cm)";
    } else if(alto > 160){
        document.getElementById('alertAltura').innerText = "ADVERTENCIA: Altura excede límite pasajero (160 cm)";
    } else {
        document.getElementById('alertAltura').innerText = "";
    }

    // Validación de dimensiones
    if(largo > 318 || ancho > 244){
        document.getElementById('alertDim').innerText = "ALERTA: Largo/Ancho excede máximo permitido (318/244 cm)";
    } else {
        document.getElementById('alertDim').innerText = "";
    }

    // Validación de peso
    if(peso > 6800){
        document.getElementById('alertPeso').innerText = "ALERTA: Peso excede máximo permitido del pallet (6800 kg)";
    } else {
        document.getElementById('alertPeso').innerText = "";
    }
}

// Mostrar documentos según tipo de carga
function mostrarDocumentos() {
    let tipo = document.getElementById('tipoCarga').value;
    let docs = {
        "HUM": "Air Waybill, Death Certificate, Funeral Certificate, Embalming Certificate, Known Shipper / Screening / Regulated Agent",
        "PER": "Air Waybill, Packing List, Certificado Fitosanitario, FDA Prior Notice, Known Shipper / Screening / Regulated Agent",
        "DGR": "Air Waybill, Shipper’s Declaration x2, Certificado Fitosanitario si aplica, Known Shipper / Screening / Regulated Agent",
        "GEN": "Air Waybill, Packing List, Invoice, Known Shipper / Screening / Regulated Agent"
    };
    document.getElementById('documentos').innerText = docs[tipo] || "Air Waybill, Packing List, Invoice, Known Shipper / Screening / Regulated Agent";
}

// Actualizar rol alternativo
function actualizarRol() {
    let rol = document.getElementById('rol').value;
    let opciones = "";
    if(rol === "Chofer" || rol === "Camionero") opciones = "Forwarder, Dueño, Counter";
    if(rol === "Forwarder") opciones = "Chofer, Dueño, Counter";
    document.getElementById('rolAlternativo').innerText = opciones;
}

// Validación final simulada
function validarCarga() {
    alert("Validación ejecutada. Revise alertas visibles en pantalla.");
}
