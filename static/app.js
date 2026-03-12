let phase = 1;

let currentIndex = 0;

let questions = [];

let answers = {};

let aviancaQuestions = [];

let cargoQuestions = [];


// =======================
// LOAD
// =======================

async function loadData() {

    const a = await fetch('/questions');
    const aData = await a.json();

    aviancaQuestions = aData.preguntas;


    const c = await fetch('/cargo_rules');
    const cData = await c.json();

    cargoQuestions = [];

    cData.FASES.forEach(f => {

        f.Preguntas.forEach(p => {

            cargoQuestions.push({
                pregunta: p.Pregunta,
                instruccion: p.Instruccion
            });

        });

    });


    questions = aviancaQuestions;

    renderQuestion();

}


// =======================
// RENDER
// =======================

function renderQuestion() {

    const container =
        document.getElementById('question-container');

    container.innerHTML = "";


    if (currentIndex >= questions.length) {

        if (phase === 1) {

            phase = 2;

            questions = cargoQuestions;

            currentIndex = 0;

            renderQuestion();

            return;

        }

        finalizeCheck();

        return;

    }


    const q = questions[currentIndex];


    const div = document.createElement("div");

    div.innerHTML =

        "<b>" +
        (currentIndex + 1) +
        ". " +
        q.pregunta +
        "</b><br><br>" +

        (q.instruccion || "") +

        "<br><br>" +

        "<input id='ans'>";


    container.appendChild(div);

}


// =======================
// NEXT
// =======================

document
.getElementById("next-btn")
.addEventListener("click", () => {

    const input =
        document.getElementById("ans");

    if (!input.value) {

        alert("Responda");

        return;

    }

    answers[
        "p" +
        phase +
        "_" +
        currentIndex
    ] = input.value;


    currentIndex++;

    renderQuestion();

});


// =======================
// FINAL
// =======================

async function finalizeCheck() {

    const r = await fetch(
        "/validate",
        {
            method: "POST",
            headers: {
                "Content-Type":
                    "application/json"
            },
            body: JSON.stringify(answers)
        }
    );

    const result = await r.json();

    let html = "<h2>Resultado</h2>";

    if (result.alertas.length) {

        html += "<ul>";

        result.alertas.forEach(a => {

            html += "<li>" +
                a.accion +
                "</li>";

        });

        html += "</ul>";

    }


    if (result.RFC) {

        html +=
            "<h3 style='color:green'>RFC = SI</h3>";

    } else {

        html +=
            "<h3 style='color:red'>RFC = NO</h3>";

    }


    document
        .getElementById("question-container")
        .innerHTML = html;

}
