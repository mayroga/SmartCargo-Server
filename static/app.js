let cargoRules = {};
let aviancaRules = {};
let allDocuments = new Set();

/* -----------------------------
Cargar reglas desde backend
------------------------------*/

async function loadRules(){
    const cargo = await fetch("/static/cargo_rules.json");
    cargoRules = await cargo.json();

    const avi = await fetch("/static/avianca_rules.json");
    aviancaRules = await avi.json();

    buildDocumentLibrary();
}

loadRules();

/* -----------------------------
Construir biblioteca global de documentos
------------------------------*/

function buildDocumentLibrary(){

    Object.keys(cargoRules).forEach(type=>{
        let docs = cargoRules[type].documents || [];
        docs.forEach(d=>allDocuments.add(d));
    });

    const docList = document.getElementById("documents");

    if(docList){
        docList.innerHTML = "";

        allDocuments.forEach(doc=>{
            let opt = document.createElement("option");
            opt.value = doc;
            opt.textContent = doc;
            docList.appendChild(opt);
        });
    }

}

/* -----------------------------
Autocompletar documentos según carga
------------------------------*/

function autofillDocs(){

    const cargoType = document.getElementById("cargo_type").value;

    if(!cargoRules[cargoType]) return;

    const docs = cargoRules[cargoType].documents;

    const docField = document.getElementById("documents_input");

    docField.value = docs.join(", ");
}

/* -----------------------------
Cálculo volumen
------------------------------*/

function calculateVolume(){

    let l = parseFloat(document.getElementById("length").value);
    let w = parseFloat(document.getElementById("width").value);
    let h = parseFloat(document.getElementById("height").value);

    if(!l || !w || !h) return;

    let vol = (l*w*h)/1728;

    document.getElementById("volume").value = vol.toFixed(3);

}

document.getElementById("length")?.addEventListener("input",calculateVolume);
document.getElementById("width")?.addEventListener("input",calculateVolume);
document.getElementById("height")?.addEventListener("input",calculateVolume);

/* -----------------------------
Control fases UI
------------------------------*/

document.querySelectorAll(".phase").forEach(p=>{
    p.addEventListener("click",()=>{
        let content = document.getElementById("phase"+p.dataset.phase);

        if(content.style.display==="block")
            content.style.display="none";
        else
            content.style.display="block";
    });
});

/* -----------------------------
Recolectar UN numbers
------------------------------*/

function parseUN(){

    const raw = document.getElementById("un_numbers").value;

    if(!raw) return [];

    return raw.split(",")
        .map(x=>x.trim().toUpperCase())
        .filter(x=>x.startsWith("UN"));

}

/* -----------------------------
Enviar validación
------------------------------*/

document.getElementById("validateBtn").addEventListener("click",()=>{

    const data = {

        mawb: document.getElementById("mawb").value.trim(),

        hawb: document.getElementById("hawb").value.trim(),

        airline: document.getElementById("airline").value.trim(),

        flight_number: document.getElementById("flight_number").value.trim(),

        flight_date: document.getElementById("flight_date").value,

        origin: document.getElementById("origin").value.trim(),

        destination: document.getElementById("destination").value.trim(),

        cargo_type: document.getElementById("cargo_type").value,

        pieces: parseInt(document.getElementById("pieces").value),

        gross_weight: parseFloat(document.getElementById("gross_weight").value),

        length: parseFloat(document.getElementById("length").value),

        width: parseFloat(document.getElementById("width").value),

        height: parseFloat(document.getElementById("height").value),

        volume: parseFloat(document.getElementById("volume").value),

        /* medidas críticas */

        tallest_piece: parseFloat(document.getElementById("tallest_piece").value),

        longest_piece: parseFloat(document.getElementById("longest_piece").value),

        widest_piece: parseFloat(document.getElementById("widest_piece").value),

        heaviest_piece: parseFloat(document.getElementById("heaviest_piece").value),

        documents: document.getElementById("documents_input")
            .value
            .split(",")
            .map(d=>d.trim())
            .filter(d=>d),

        un_numbers: parseUN(),

        security:{

            known_shipper: document.getElementById("known_shipper").value==="true",

            screening: document.getElementById("screening").value,

            regulated_agent: document.getElementById("regulated_agent").value==="true"

        },

        role: document.getElementById("role").value

    };

    fetch("/validate_shipment",{

        method:"POST",

        headers:{
            "Content-Type":"application/json"
        },

        body:JSON.stringify(data)

    })
    .then(r=>r.json())
    .then(res=>{

        let txt = "";

        if(res.status==="GREEN")
            txt+="GREEN ✅ CARGA APROBADA\n\n";
        else
            txt+="RED ❌ CARGA BLOQUEADA\n\n";

        if(res.errors.length>0){

            txt+="ERRORES DETECTADOS\n";

            res.errors.forEach(e=>{
                txt+="• "+e+"\n";
            });

        }

        if(res.corrections.length>0){

            txt+="\nSOLUCIONES RECOMENDADAS\n";

            res.corrections.forEach(c=>{
                txt+="• "+c+"\n";
            });

        }

        txt+=`\nValidado por ${res.role} @ ${res.timestamp}`;

        document.getElementById("result").innerText = txt;

        /* pintar fases */

        for(let i=1;i<=8;i++){

            let pid="phase"+i;

            let box=document.getElementById(pid);

            if(res.phases[pid].length===0)
                box.innerHTML="Sin alertas";
            else
                box.innerHTML=res.phases[pid].join("<br>");

        }

    });

});

/* -----------------------------
Validación técnica frontend
------------------------------*/

function checkAircraftLimits(){

    let height = parseFloat(document.getElementById("tallest_piece").value);

    if(height>96){
        alert("❌ Altura mayor a 96 pulgadas. No puede volar en Avianca.");
    }

    if(height>63 && height<=96){
        alert("⚠️ Solo puede volar en avión carguero (Freighter)");
    }

}

document.getElementById("tallest_piece")?.addEventListener("change",checkAircraftLimits);

/* -----------------------------
Cambio tipo carga
------------------------------*/

document.getElementById("cargo_type")?.addEventListener("change",autofillDocs);
