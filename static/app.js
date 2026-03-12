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
    else if(alto > 160) alertMsg += "Solo vuela en carguero. ";
    if(largo > 318 || ancho > 244) alertMsg += "Dimensiones exceden límites. ";
    if(pesoTotal > 6800) alertMsg += "Peso excede límite pallet 6800kg.";
    document.getElementById('alertDimensiones').innerText = alertMsg;
}

// Enviar datos al backend
async function evaluarCarga() {
    const data = {
        rol: document.getElementById('rolUsuario').value,
        awb: document.getElementById('awb').value.trim(),
        codigo: document.getElementById('codigoCarga').value,
        piezas: parseInt(document.getElementById('piezas').value) || 0,
        pesoTotal: parseFloat(document.getElementById('pesoTotal').value) || 0,
        pesoPieza: parseFloat(document.getElementById('pesoPieza').value) || 0,
        largo: parseFloat(document.getElementById('largo').value) || 0,
        ancho: parseFloat(document.getElementById('ancho').value) || 0,
        alto: parseFloat(document.getElementById('alto').value) || 0,
        knownShipper: document.getElementById('knownShipper').value,
        horaCamion: document.getElementById('horaCamion').value,
        cutoff: document.getElementById('cutoff').value,
        description: document.getElementById('codigoCarga').value.toLowerCase(),
        destination: document.getElementById('destino').value,
        shipper_type: document.getElementById('rolUsuario').value
    };

    const response = await fetch("/validate_shipment", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify(data)
    });
    const result = await response.json();
    document.getElementById('resultadoFinal').innerText =
        `${result.status}\nErrores: ${result.errors.join(" | ")}\nAdvertencias: ${result.warnings.join(" | ")}\nRiesgos: ${result.risks.join(" | ")}\nAircraft: ${result.aircraft_recommendation}`;
}

// Opciones de rol dinámicas
function updateRolFields() {
    const rol = document.getElementById('rolUsuario').value;
    let aviso = document.getElementById('avisoRol');
    if(!aviso){
        aviso = document.createElement("p");
        aviso.id = "avisoRol";
        aviso.style.fontStyle = "italic";
        document.getElementById('faseUniversal').appendChild(aviso);
    }
    aviso.innerText =
        rol==="Chofer" || rol==="AgenteWarehouse" ? "Recuerde: Revise sellos y manifiestos." :
        rol==="Forwarder" ? "Recuerde: Validar documentación y AWB." : "";
}

// Cortinas inteligentes
document.addEventListener("DOMContentLoaded", ()=>{
    var coll = document.getElementsByClassName("collapsible");
    for (let i = 0; i < coll.length; i++) {
        coll[i].addEventListener("click", function() {
            this.classList.toggle("active");
            var content = this.nextElementSibling;
            content.style.display = (content.style.display === "block") ? "none" : "block";
        });
    }
});
