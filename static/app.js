// =============================
// VARIABLES
// =============================

let currentIndex = 0;
let answers = {};
let questions = [];
let cargoRules = {};
let aviancaRules = {};


// =============================
// LOAD DATA
// =============================

async function loadData() {

    const qResp = await fetch('/questions');
    const qData = await qResp.json();
    questions = qData.preguntas;

    const cargoResp = await fetch('/cargo_rules');
    cargoRules = await cargoResp.json();

    const aviancaResp = await fetch('/avianca_rules');
    aviancaRules = await aviancaResp.json();

    renderQuestion();
}


// =============================
// RENDER
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


    const questionText = document.createElement('div');
    questionText.className = 'question-text';
    questionText.textContent =
        (currentIndex + 1) + ". " + q.pregunta;

    block.appendChild(questionText);


    if (q.porque) {

        const why = document.createElement('div');
        why.className = 'why';
        why.textContent = q.porque;
        block.appendChild(why);

    }


    if (q.instruccion) {

        const inst = document.createElement('div');
        inst.className = 'instruction';
        inst.textContent = q.instruccion;
        block.appendChild(inst);

    }


    const input = document.createElement('input');
    input.type = 'text';
    input.placeholder = "Respuesta";
    block.appendChild(input);


    container.appendChild(block);

}


// =============================
// NEXT
// =============================

document.getElementById('next-btn').addEventListener('click', () => {

    const container = document.getElementById('question-container');

    const input = container.querySelector('input');

    if (!input.value) {
        alert("Debe responder");
        return;
    }

    const q = questions[currentIndex];

    // guardar por id

    answers[q.id] = input.value;

    currentIndex++;

    renderQuestion();

});


// =============================
// FINAL
// =============================

async function finalizeCheck() {

    document.getElementById('question-container').innerHTML = "";
    document.getElementById('next-btn').style.display = "none";


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

        html += "<ul>";

        result.alertas.forEach(a => {

            html += "<li>" +
                a.accion +
                " (" + a.tipo + ")" +
                "</li>";

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


loadData();
