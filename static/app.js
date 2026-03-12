// Mostrar documentos según tipo de carga y guía paso a paso
function mostrarDocumentos() {
    const tipo = document.getElementById('codigoCarga').value;
    const docs = {
        "GEN": "AWB, Packing List, Invoice, Known Shipper / Screening. Todo debe estar legible y con copia interna y externa.",
        "PER": "AWB, Packing List, Certificado Fitosanitario, FDA Prior Notice, Known Shipper. Revise temperatura 0C-8C.",
        "HUM": "AWB, Death Certificate, Embalming Certificate, Funeral Letter. Revise embalaje seguro y etiqueta Human Remains.",
        "VAL": "AWB, Invoice, Seguro / Declaración de valor. Revise embalaje reforzado.",
        "AVI": "AWB, Certificado sanitario animal, Known Shipper. Animales vivos, asegure ventilación y protección.",
        "DGR": "AWB, Shipper Declaration x2, MSDS. Revise etiquetas, embalaje, pallets y protecciones especiales."
    };
    document.getElementById('documentosObligatorios').innerText = docs[tipo] || "Seleccione un tipo de carga para ver documentos.";
}

// Calcular volumen y peso volumétrico y dar tips
function calcularVolumen() {
    const L = parseFloat(document.getElementById('largo').value) || 0;
    const W = parseFloat(document.getElementById('ancho').value) || 0;
    const H = parseFloat(document.getElementById('alto').value) || 0;
    const pesoTotal = parseFloat(document.getElementById('pesoTotal').value) || 0;

    const volumen = (L*W*H)/1000000;
    document.getElementById('volumen').value = volumen.toFixed(3)+' m³';
    const pesoVol = volumen * 167;
    document.getElementById('pesoVolumetrico').value = pesoVol.toFixed(2);

    let alertMsg = "";
    if(H>244) alertMsg += "Alto excede carguero (244cm). ";
    else if(H>160) alertMsg += "Solo vuela en Main Deck. ";
    if(L>318 || W>244) alertMsg += "Dimensiones exceden límites. ";
    if(pesoTotal>6800) alertMsg += "Peso excede límite pallet 6800kg.";
    document.getElementById('alertDimensiones').innerText = alertMsg;
}

// Evaluar carga y mostrar instrucciones educativas
async function evaluarCarga() {
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

    const response = await fetch("/validate_shipment",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify(data)
    });

    const result = await response.json();

    let output = result.status + "\n\nInstrucciones:\n";
    result.instructions.forEach((ins,i)=>{
        output += (i+1)+". "+ins+"\n";
    });

    if(result.errors.length>0){
        output += "\nErrores:\n"+result.errors.join("\n");
    }
    if(result.warnings.length>0){
        output += "\nAdvertencias:\n"+result.warnings.join("\n");
    }

    document.getElementById('resultadoFinal').innerText = output;
}
