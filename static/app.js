// Variables globales
let currentIndex = 0;
let answers = [];
let questions = [];
let cargoRules = {};
let aviancaRules = {};

// Cargar los JSON de forma asíncrona
async function loadData() {
    const qResp = await fetch('static/cargo_questions.json');
    questions = await qResp.json();

    const cargoResp = await fetch('static/cargo_rules.json');
    cargoRules = await cargoResp.json();

    const aviancaResp = await fetch('static/avianca_rules.json');
    aviancaRules = await aviancaResp.json();

    renderQuestion();
}

// Renderiza la pregunta actual
function renderQuestion() {
    const container = document.getElementById('question-container');
    container.innerHTML = '';

    if(currentIndex >= questions.length) {
        finalizeCheck();
        return;
    }

    const q = questions[currentIndex];

    const block = document.createElement('div');
    block.className = 'question-block';

    const questionText = document.createElement('div');
    questionText.className = 'question-text';
    questionText.textContent = `${currentIndex + 1}. ${q.pregunta}`;
    block.appendChild(questionText);

    const alertBox = document.createElement('div');
    alertBox.className = 'alert';
    alertBox.textContent = q.alerta || '';
    block.appendChild(alertBox);

    const instructionBox = document.createElement('div');
    instructionBox.className = 'instruction';
    instructionBox.textContent = q.instruccion;
    block.appendChild(instructionBox);

    // Select o input según tipo
    let inputEl;
    if(q.tipo === 'boolean') {
        inputEl = document.createElement('select');
        inputEl.innerHTML = '<option value="">--Seleccione--</option><option value="Sí">Sí</option><option value="No">No</option>';
    } else {
        inputEl = document.createElement('input');
        inputEl.type = 'text';
        inputEl.placeholder = 'Ingrese su respuesta';
    }
    block.appendChild(inputEl);

    // Mostrar instrucción según selección
    inputEl.addEventListener('change', () => {
        instructionBox.style.display = inputEl.value ? 'block' : 'none';

        // Mostrar alerta condicional
        if(q.critica && inputEl.value === q.critica.valor) {
            alertBox.style.display = 'block';
        } else {
            alertBox.style.display = 'none';
        }
    });

    container.appendChild(block);
}

// Avanzar a la siguiente pregunta
document.getElementById('next-btn').addEventListener('click', () => {
    const container = document.getElementById('question-container');
    const inputEl = container.querySelector('input, select');
    if(!inputEl.value) {
        alert('Por favor responda antes de continuar.');
        return;
    }

    // Guardar respuesta
    answers.push({pregunta: questions[currentIndex].pregunta, respuesta: inputEl.value});
    currentIndex++;
    renderQuestion();
});

// Función de veredicto final
function finalizeCheck() {
    document.getElementById('question-container').innerHTML = '';
    document.getElementById('next-btn').style.display = 'none';

    let summaryText = '<h2>Reporte de Validación RFC</h2><ul>';

    answers.forEach(ans => {
        summaryText += `<li><strong>${ans.pregunta}</strong>: ${ans.respuesta}</li>`;
    });

    // Validaciones críticas (ejemplo: ITN, NIMF-15)
    let bloqueos = [];
    answers.forEach(ans => {
        if(ans.pregunta.includes('valor de su mercancía') && ans.respuesta === 'Sí') {
            bloqueos.push('Falta ITN para mercancía >$2,500 USD.');
        }
        if(ans.pregunta.includes('estibas de madera') && ans.respuesta === 'No') {
            bloqueos.push('Falta sello NIMF-15, cambio a pallet de plástico.');
        }
        if(ans.pregunta.includes('flejes') && ans.respuesta === 'No') {
            bloqueos.push('Falta flejes, riesgo de movimiento en vuelo.');
        }
    });

    if(bloqueos.length) {
        summaryText += '<h3>Bloqueos Críticos:</h3><ul>';
        bloqueos.forEach(b => summaryText += `<li>${b}</li>`);
        summaryText += '</ul>';
        summaryText += '<p style="color:red; font-weight:bold;">La carga NO está lista para volar (RFC = NO)</p>';
    } else {
        summaryText += '<p style="color:green; font-weight:bold;">La carga está lista para volar (RFC = SÍ)</p>';
    }

    summaryText += '</ul>';
    const summaryDiv = document.getElementById('summary');
    summaryDiv.innerHTML = summaryText;
    summaryDiv.style.display = 'block';
}

// Inicializar
loadData();
