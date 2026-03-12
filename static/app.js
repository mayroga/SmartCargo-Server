// ===============================
// SMARTGOSERVER PRE-CHECK ENGINE
// ===============================

async function validarCarga() {

    let largo = parseFloat(document.getElementById('largo').value) || 0
    let ancho = parseFloat(document.getElementById('ancho').value) || 0
    let alto = parseFloat(document.getElementById('alto').value) || 0
    let peso = parseFloat(document.getElementById('peso').value) || 0

    let tipo = document.getElementById('tipoCarga').value
    let destino = document.getElementById('destino').value
    let rol = document.getElementById('rol').value

    let data = {

        role: rol,

        cargo_type: tipo || "GENERAL",

        pieces: 1,

        units: "cm",

        longest_piece: largo,

        widest_piece: ancho,

        tallest_piece: alto,

        heaviest_piece: peso,

        gross_weight: peso,

        uld_type: "PMC",

        documents: [
            "air_waybill",
            "commercial_invoice",
            "packing_list"
        ],

        security: {
            known_shipper: true,
            regulated_agent: true,
            screening: "xray"
        }
    }

    let response = await fetch("/validate_shipment", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    })

    let result = await response.json()

    mostrarResultado(result)
}


// ===============================
// RESULTADO PRECHECK
// ===============================

function mostrarResultado(result) {

    let container = document.getElementById("resultado")

    if (!container) {

        container = document.createElement("div")
        container.id = "resultado"
        container.className = "section"
        document.body.appendChild(container)

    }

    let estado = ""
    let mensaje = ""

    if (result.status === "GREEN") {

        estado = "🟢 READY FOR COUNTER"
        mensaje = "La carga puede presentarse en el counter."

    } else {

        let bloqueante = false

        result.errors.forEach(e => {

            if (
                e.includes("No puede volar") ||
                e.includes("demasiado larga") ||
                e.includes("sobresale")
            ) {
                bloqueante = true
            }

        })

        if (bloqueante) {

            estado = "🔴 NO FLY TODAY"
            mensaje = "Existe un error crítico. La carga no puede volar hoy."

        } else {

            estado = "🟡 FIX BEFORE COUNTER"
            mensaje = "Debe corregir estos puntos antes de ir al counter."

        }

    }

    let erroresHTML = ""

    result.errors.forEach(e => {

        erroresHTML += `<li style="color:red">${e}</li>`

    })

    let correccionesHTML = ""

    result.corrections.forEach(c => {

        correccionesHTML += `<li>${c}</li>`

    })

    container.innerHTML = `

        <h2>RESULTADO PRE-CHECK</h2>

        <h3>${estado}</h3>

        <p>${mensaje}</p>

        <h3>Errores Detectados</h3>
        <ul>${erroresHTML}</ul>

        <h3>Correcciones</h3>
        <ul>${correccionesHTML}</ul>

        <hr>

        <b>Volumen calculado:</b> ${result.volume_m3} m³<br>
        <b>ULD:</b> ${result.cargo_type_fullname}<br>
        <b>Fecha:</b> ${result.timestamp}

    `
}


// ===============================
// CALCULO DE VOLUMEN EN FRONT
// ===============================

function calcularVolumen() {

    let largo = parseFloat(document.getElementById('largo').value) || 0
    let ancho = parseFloat(document.getElementById('ancho').value) || 0
    let alto = parseFloat(document.getElementById('alto').value) || 0

    let volumen = (largo * ancho * alto) / 1000000

    document.getElementById('volumen').value = volumen.toFixed(3) + " m³"

    if (alto > 244) {

        document.getElementById('alertAltura').innerText =
            "ALERTA: Altura excede límite carguero (96in / 244cm)"

    } else if (alto > 160) {

        document.getElementById('alertAltura').innerText =
            "ADVERTENCIA: Solo puede volar en carguero"

    } else {

        document.getElementById('alertAltura').innerText = ""

    }

    if (largo > 318 || ancho > 244) {

        document.getElementById('alertDim').innerText =
            "ALERTA: Dimensión excede pallet estándar"

    } else {

        document.getElementById('alertDim').innerText = ""

    }

}
