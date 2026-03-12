// Mostrar documentos según tipo de carga
function mostrarDocumentos() {
    const tipo = document.getElementById('codigoCarga').value;
    const docs = {
        "GEN": "AWB, Packing List, Invoice, Known Shipper / Screening",
        "PER": "AWB, Packing List, Certificado Fitosanitario, FDA Prior Notice, Known Shipper / Screening",
        "HUM": "AWB, Death Certificate, Embalming Certificate, Funeral Letter, Known Shipper / Screening",
        "VAL": "AWB, Invoice, Seguro / Declaración de valor",
        "AVI": "AWB, Certificado sanitario animal, Known Shipper / Screening",
        "DGR": "AWB, Shipper Declaration x2, MSDS, Known Shipper / Screening"
    };
    document.getElementById('documentosObligatorios').innerText = docs[tipo] || "Seleccione un tipo de carga";
}

// Calcular volumen y peso volumétrico
function calcularVolumen() {
    const largo = parseFloat(document.getElementById('largo').value) || 0;
    const ancho = parseFloat(document.getElementById('ancho').value) || 0;
    const alto = parseFloat(document.getElementById('alto').value) || 0;
    const pesoTotal = parseFloat(document.getElementById('pesoTotal').value) || 0;

    const volumen = (largo * ancho * alto) / 1000000;
    document.getElementById('volumen').value = volumen.toFixed(3) + ' m³';

    const pesoVol = volumen * 167;
    document.getElementById('pesoVolumetrico').value = pesoVol.toFixed(2);

    let alertMsg = "";
    if(alto > 244) alertMsg += "ALTO excede carguero (244cm). ";
    else if(alto > 160) alertMsg += "ALTO excede pasajero (160cm). ";
    if(largo > 318 || ancho > 244) alertMsg += "Dimensiones exceden límites. ";
    if(pesoTotal > 6800) alertMsg += "Peso excede límite pallet 6800kg.";
    document.getElementById('alertDimensiones').innerText = alertMsg;
}

// Evaluar carga y generar resultado final
function evaluarCarga() {
    const errores = [];
    const rol = document.getElementById('rolUsuario').value;
    const awb = document.getElementById('awb').value.trim();
    const codigo = document.getElementById('codigoCarga').value;
    const piezas = parseInt(document.getElementById('piezas').value) || 0;
    const pesoTotal = parseFloat(document.getElementById('pesoTotal').value) || 0;
    const alto = parseFloat(document.getElementById('alto').value) || 0;
    const pesoVol = parseFloat(document.getElementById('pesoVolumetrico').value) || 0;
    const known = document.getElementById('knownShipper').value;
    const horaCamion = document.getElementById('horaCamion').value;
    const cutoff = document.getElementById('cutoff').value;

    // Fase I: Validaciones esenciales
    if(!rol) errores.push("Seleccione rol del usuario.");
    if(!awb.match(/^\d{3}-\d{8}$/)) errores.push("Formato AWB inválido XXX-12345675.");
    if(!codigo) errores.push("Seleccione tipo de carga.");
    if(piezas < 1) errores.push("Número de piezas inválido.");
    if(!known) errores.push("Indique si es Known Shipper.");

    // Fase II/III: Dimensiones y peso
    if(alto > 244) errores.push("Alto excede límite carguero.");
    if(alto > 160 && alto <=244) errores.push("Solo vuela en carguero, no en pasajero.");
    if(pesoTotal > 6800) errores.push("Peso excede límite pallet.");
    if(pesoVol > pesoTotal) errores.push("Peso volumétrico mayor que peso real, ajuste reserva.");

    // Fase IV: Cutoff
    if(horaCamion && cutoff && horaCamion > cutoff) errores.push("Camión llega después de cutoff, NO VUELA HOY.");

    // Resultado final
    let resultado = "";
    if(errores.length === 0) resultado = "🟢 ACEPTADO - Carga apta para vuelo hoy.";
    else if(errores.length <= 2) resultado = "🟡 ACEPTADO CON ALERTA: " + errores.join(" | ");
    else resultado = "🔴 RECHAZADO: " + errores.join(" | ");

    document.getElementById('resultadoFinal').innerText = resultado;
}

// Opciones de rol dinámicas
function updateRolFields() {
    const rol = document.getElementById('rolUsuario').value;
    const aviso = document.getElementById('avisoRol') || null;
    if(!aviso) {
        const p = document.createElement("p");
        p.id = "avisoRol";
        p.style.fontStyle = "italic";
        document.getElementById('faseUniversal').appendChild(p);
    }
    document.getElementById('avisoRol').innerText = 
        rol==="Chofer" || rol==="AgenteWarehouse" ? "Recuerde: Revise sellos y manifiestos." :
        rol==="Forwarder" ? "Recuerde: Validar documentación y AWB." : "";
}
