// frontend/scripts.js
// SMARTCARGO-AIPA: Lógica de navegación y envío de respuestas

let faseActual = 1;
let preguntaActual = 1;
const TOTAL_PREGUNTAS = 21;

async function cargarPregunta() {
    try {
        const res = await axios.get(`/get_question/${faseActual}/${preguntaActual}`);
        document.getElementById('fase-info').innerText = `Fase ${res.data.fase}`;
        document.getElementById('pregunta-text').innerText = res.data.pregunta;
        document.getElementById('instruccion-text').innerText = res.data.instruccion;
        document.getElementById('alerta-text').innerText = "";
        document.getElementById('respuesta-input').value = "";
    } catch (err) {
        document.getElementById('pregunta-text').innerText = "✅ Pre-check completado. Todas las preguntas respondidas.";
        document.getElementById('instruccion-text').innerText = "";
        document.getElementById('respuesta-input').style.display = "none";
        document.querySelector('.btn-group').style.display = "none";
    }
}

async function enviarRespuesta(valor) {
    const input = document.getElementById('respuesta-input');
    if (valor !== 'manual') input.value = valor;
    await enviarRespuestaManual();
}

async function enviarRespuestaManual() {
    const inputVal = document.getElementById('respuesta-input').value.trim();
    if (inputVal === "") {
        document.getElementById('alerta-text').innerText = "⚠ Ingrese su respuesta antes de continuar.";
        return;
    }

    try {
        const res = await axios.post('/submit_answer', {
            fase: faseActual,
            pregunta_id: preguntaActual,
            respuesta: inputVal
        });
        document.getElementById('alerta-text').innerText = res.data.alerta || "✔ Respuesta registrada correctamente.";

        // Avanzar pregunta
        preguntaActual++;
        if (preguntaActual > TOTAL_PREGUNTAS) {
            document.getElementById('pregunta-text').innerText = "✅ Pre-check completo. Puede proceder al counter de Avianca.";
            document.getElementById('instruccion-text').innerText = "";
            document.getElementById('respuesta-input').style.display = "none";
            document.querySelector('.btn-group').style.display = "none";
            return;
        }

        // Avanzar fase según rango
        if ([4,6,8,10,11,12,14,16,17,19,20,21].includes(preguntaActual)) {
            faseActual++;
        }

        setTimeout(cargarPregunta, 500);

    } catch (err) {
        console.error(err);
        document.getElementById('alerta-text').innerText = "❌ Error enviando respuesta.";
    }
}

// Cargar la primera pregunta al inicio
window.onload = cargarPregunta;
