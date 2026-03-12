// Mostrar documentos según tipo de carga
function mostrarDocumentos() {
    const tipo = document.getElementById('codigoCarga').value;
    const docs = {
        "GEN": ["AWB", "Packing List", "Invoice", "Known Shipper / Screening"],
        "PER": ["AWB", "Packing List", "Certificado Fitosanitario", "FDA Prior Notice", "Known Shipper / Screening"],
        "HUM": ["AWB", "Death Certificate", "Embalming Certificate", "Funeral Letter", "Known Shipper / Screening"],
        "VAL": ["AWB", "Invoice", "Seguro / Declaración de valor"],
        "AVI": ["AWB", "Certificado sanitario animal", "Known Shipper / Screening"],
        "DGR": ["AWB", "Shipper Declaration x2", "MSDS", "Known Shipper / Screening"]
    };
    document.getElementById('documentosObligatorios').innerText = docs[tipo]?.join(", ") || "Seleccione un tipo de carga";
}

// Calcular volumen y peso volumétrico con alertas inmediatas
function calcularVolumen() {
    const L = parseFloat(document.getElementById('largo').value)||0;
    const W = parseFloat(document.getElementById('ancho').value)||0;
    const H = parseFloat(document.getElementById('alto').value)||0;
    const pesoTotal = parseFloat(document.getElementById('pesoTotal').value)||0;

    const volumen = (L*W*H)/1000000;
    document.getElementById('volumen').value = volumen.toFixed(3)+' m³';

    const pesoVol = volumen * 167;
    document.getElementById('pesoVolumetrico').value = pesoVol.toFixed(2);

    let alertMsg = "";
    if(H>244) alertMsg += "⚠ Alto excede carguero (244cm). ";
    else if(H>160) alertMsg += "⚠ Solo vuela en Main Deck. ";
    if(L>318 || W>244) alertMsg += "⚠ Dimensiones exceden límites. ";
    if(pesoTotal>6800) alertMsg += "⚠ Peso excede límite pallet 6800kg.";
    document.getElementById('alertDimensiones').innerText = alertMsg;
}

// Tips según rol
function updateRolFields() {
    const rol = document.getElementById('rolUsuario').value;
    const aviso = document.getElementById('avisoRol');
    aviso.innerText =
        rol==="Chofer" || rol==="AgenteWarehouse" ? "Tip: Revise sellos y manifiestos." :
        rol==="Forwarder" ? "Tip: Valide documentación y AWB." : "";
}

// Evaluación completa con fetch al backend
async function evaluarCarga() {
    document.getElementById('resultadoFinal').innerText = "Procesando carga...";

    const data = {
        longest_piece: parseFloat(document.getElementById('alto').value)||0,
        widest_piece: parseFloat(document.getElementById('ancho').value)||0,
        tallest_piece: parseFloat(document.getElementById('alto').value)||0,
        heaviest_piece: parseFloat(document.getElementById('pesoTotal').value)||0,
        description: document.getElementById('codigoCarga').value,
        destination: document.getElementById('destino').value,
        shipper_type: document.getElementById('rolUsuario').value,
        units: "cm"
    };

    try {
        const response = await fetch("/validate_shipment", {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body: JSON.stringify(data)
        });
        if(!response.ok) throw new Error("Error de comunicación con el servidor");

        const result = await response.json();

        let output = result.status + "\n\nInstrucciones educativas:\n";
        if(result.errors.length>0){
            result.errors.forEach((e,i)=> output += `${i+1}. ${e}\n`);
        }
        if(result.warnings.length>0){
            result.warnings.forEach((w,i)=> output += `⚠ Advertencia: ${w}\n`);
        }
        output += "\nRecomendación de avión: "+result.aircraft_recommendation;
        document.getElementById('resultadoFinal').innerText = output;
    } catch(err) {
        document.getElementById('resultadoFinal').innerText = "❌ Error: "+err.message;
    }
}

// Inicializar collapsibles al cargar la página
document.addEventListener("DOMContentLoaded", function() {
    const coll = document.getElementsByClassName("collapsible");
    for (let i=0;i<coll.length;i++){
        coll[i].addEventListener("click",function(){
            this.classList.toggle("active");
            const content = this.nextElementSibling;
            content.style.display = (content.style.display==="block") ? "none" : "block";
        });
    }
});
