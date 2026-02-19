// frontend/scripts.js
// Lógica de frontend SMARTCARGO-AIPA

const faseSelect = document.getElementById("fase");
const preguntaSelect = document.getElementById("pregunta");
const respuestaInput = document.getElementById("respuesta");
const alertaDiv = document.getElementById("alerta");
const enviarBtn = document.getElementById("enviar");

// Función para traer preguntas según fase y pregunta_id
async function getQuestion(fase, pregunta_id) {
    try {
        const res = await axios.get(`/get_question/${fase}/${pregunta_id}`);
        const data = res.data;
        preguntaSelect.innerText = data.pregunta;
        alertaDiv.innerText = "";
    } catch (error) {
        preguntaSelect.innerText = "Pregunta no encontrada";
        alertaDiv.innerText = "";
    }
}

// Enviar respuesta al backend
async function submitAnswer() {
    const payload = {
        fase: parseInt(faseSelect.value),
        pregunta_id: parseInt(preguntaSelect.dataset.id),
        respuesta: respuestaInput.value
    };

    try {
        const res = await axios.post("/submit_answer", payload);
        alertaDiv.innerText = res.data.alerta || "✅ Respuesta aceptada";
    } catch (error) {
        alertaDiv.innerText = "❌ Error enviando respuesta";
    }
}

// Eventos
enviarBtn.addEventListener("click", submitAnswer);

// Inicializar con primera pregunta
getQuestion(faseSelect.value, 1);
