let cargoRules = {};
let aviancaRules = {};
fetch("/static/cargo_rules.json").then(r=>r.json()).then(r=>cargoRules=r);
fetch("/static/avianca_rules.json").then(r=>r.json()).then(r=>aviancaRules=r);

document.getElementById("validateBtn").addEventListener("click",()=>{
    const data={
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
        volume: parseFloat(document.getElementById("volume").value),
        documents: document.getElementById("documents").value.split(",").map(d=>d.trim()).filter(d=>d),
        security:{
            known_shipper: document.getElementById("known_shipper").value==="true",
            screening: document.getElementById("screening").value,
            regulated_agent: document.getElementById("regulated_agent").value==="true"
        }
    };
    fetch("/validate_shipment",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)})
    .then(r=>r.json()).then(res=>{
        let txt=`${res.status} ${res.status==="GREEN"?"✅ Shipment aceptable":"❌ NO ACEPTABLE"}\n`;
        if(res.errors.length>0){
            txt+="Documentos faltantes o errores:\n• "+res.errors.join("\n• ")+"\n";
        }
        if(res.corrections.length>0){
            txt+="Correcciones sugeridas:\n• "+res.corrections.join("\n• ")+"\n";
        }
        txt+=`Trazabilidad: forwarder @ ${res.timestamp}`;
        document.getElementById("result").innerText=txt;
    });
});
