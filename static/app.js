// =============================
// VARIABLES
// =============================

let currentIndex = 0;
let answers = {};
let questions = [];
let cargoRules = {};
let aviancaRules = {};


// =============================
// CARGAR DATOS DEL SERVER
// =============================

async function loadData() {

    // preguntas desde FastAPI
    const qResp = await fetch('/questions');
    const qData = await qResp.json();
    questions = qData.preguntas;

    // reglas cargo
    const cargoResp = await fetch('/cargo_rules');
    cargoRules = await cargoResp.json();

    // reglas avianca
    const aviancaResp = await fetch('/avianca_rules');
    aviancaRules = await aviancaResp.json();

    renderQuestion();
}


// =============================
// MOSTRAR PREGUNTA
// =============================

function renderQuestion() {

    const container = document.getElementById('question-container');
    container.innerHTML = '';

    if (currentIndex >= questions.length) {
        finalizeCheck();
        return;
    }

    const q = questions[currentIndex];

    const block = document.createElement('div');
    block.className = 'question-block';


    // texto pregunta

    const questionText = document.createElement('div');
    questionText.className = 'question-text';
    questionText.textContent =
        (currentIndex + 1) + ". " + q.pregunta;

    block.appendChild(questionText);


    // porque

    const whyBox = document.createElement('div');
    whyBox.className = 'why';
    whyBox.textContent = q.porque || "";
    block.appendChild(whyBox);


    // instruccion

    const instructionBox = document.createElement('div');
    instructionBox.className = 'instruction';
    instructionBox.textContent = q.instruccion || "";
    block.appendChild(instructionBox);


    // input

    const inputEl = document.createElement('input');
    inputEl.type = 'text';
    inputEl.placeholder = "Escriba respuesta";
    block.appendChild(inputEl);


    container.appendChild(block);

}


// =============================
// BOTON NEXT
// =============================

document.getElementById('next-btn').addEventListener('click', () => {

    const container = document.getElementById('question-container');

    const inputEl = container.querySelector('input');

    if (!inputEl.value) {
        alert("Responda antes de continuar");
        return;
    }

    const q = questions[currentIndex];

    // guardar respuesta por clave

    if (q.alerta_condicional && q.alerta_condicional.si) {

        answers[q.alerta_condicional.si] = true;

    }

    answers["respuesta_" + q.id] = inputEl.value;

    currentIndex++;

    renderQuestion();

});


// =============================
// FINALIZAR
// =============================

async function finalizeCheck() {

    document.getElementById('question-container').innerHTML = "";

    document.getElementById('next-btn').style.display = "none";


    // enviar al server

    const resp = await fetch('/validate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(answers)
    });

    const result = await resp.json();


    let html = "<h2>Reporte RFC</h2>";

    if (result.alertas.length > 0) {

        html += "<h3>Alertas:</h3><ul>";

        result.alertas.forEach(a => {

            html += "<li>"
                + a.accion +
                " (" + a.tipo + ")</li>";

        });

        html += "</ul>";

    }


    if (result.RFC) {

        html += "<p style='color:green;font-weight:bold'>RFC = SI</p>";

    } else {

        html += "<p style='color:red;font-weight:bold'>RFC = NO</p>";

    }


    document.getElementById('summary').innerHTML = html;

    document.getElementById('summary').style.display = "block";

}


// =============================
// INIT
// =============================

loadData();
