let faseIndex = 0;
let preguntaIndex = 0;
let cargoData = {};
let reglas = {};
let cargoRules = {};

async function cargarReglas() {
  reglas = await fetch("avianca_rules.json").then(r => r.json());
  cargoRules = await fetch("cargo_rules.json").then(r => r.json());
  mostrarPregunta();
}

function mostrarPregunta() {
  let fase = cargoRules.FASES[faseIndex];
  let pregunta = fase.Preguntas[preguntaIndex];
  let container = document.getElementById("pregunta-container");
  container.innerHTML = `
    <p><b>${fase.Fase}:</b> ${pregunta.Pregunta}</p>
    <input type="text" id="respuesta"/>
    <button onclick="guardarRespuesta()">Siguiente</button>
    <p>${pregunta.Instruccion}</p>
  `;
}

function guardarRespuesta() {
  let resp = document.getElementById("respuesta").value;
  if(!cargoData[cargoRules.FASES[faseIndex].Fase]) cargoData[cargoRules.FASES[faseIndex].Fase]={};
  cargoData[cargoRules.FASES[faseIndex].Fase][preguntaIndex] = resp;

  preguntaIndex++;
  if(preguntaIndex >= cargoRules.FASES[faseIndex].Preguntas.length) {
    preguntaIndex=0;
    faseIndex++;
  }

  if(faseIndex >= cargoRules.FASES.length) {
    calcularResultado();
  } else {
    mostrarPregunta();
  }
}

function calcularResultado() {
  let res = "🟢 ACEPTADO";
  // Validaciones críticas
  let faseIdent = cargoData["Identificación y Seguridad"];
  let faseDim = cargoData["Dimensiones y peso"];
  let faseDoc = cargoData["Documentación"];
  let faseCut = cargoData["Llegada y Cutoff"];

  // Ejemplo simple de bloqueos
  if(faseCut && faseCut[0] > reglas.Cutoff) res = "🔴 RECHAZADO";
  if(faseDim && (parseInt(faseDim[0])>reglas.Avion.MaxCargueroCm)) res="🔴 RECHAZADO";
  if(faseIdent && faseIdent[1].toUpperCase()=='NO') res="🟡 ACEPTADO CON ALERTA";

  document.getElementById("pregunta-container").innerHTML="";
  document.getElementById("resultado").innerHTML=`<h2>Resultado final: ${res}</h2>`;
}

cargarReglas();
