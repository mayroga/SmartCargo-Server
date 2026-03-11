let cargoRules={}, aviancaRules={};
fetch("/static/cargo_rules.json").then(r=>r.json()).then(r=>cargoRules=r);
fetch("/static/avianca_rules.json").then(r=>r.json()).then(r=>aviancaRules=r);

function calculateVolume(){ 
    let l=parseFloat(document.getElementById("length").value);
    let w=parseFloat(document.getElementById("width").value);
    let h=parseFloat(document.getElementById("height").value);
    document.getElementById("volume").value=(l*w*h).toFixed(3);
}
document.getElementById("length").addEventListener("input",calculateVolume);
document.getElementById("width").addEventListener("input",calculateVolume);
document.getElementById("height").addEventListener("input",calculateVolume);

document.querySelectorAll(".phase").forEach(p=>{
    p.addEventListener("click",()=>{
        let content=document.getElementById("phase"+p.dataset.phase);
        content.style.display=content.style.display==="block"?"none":"block";
    });
});

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
        length: parseFloat(document.getElementById("length").value),
        width: parseFloat(document.getElementById("width").value),
        height: parseFloat(document.getElementById("height").value),
        volume: parseFloat(document.getElementById("volume").value),
        gross_weight: parseFloat(document.getElementById("gross_weight").value),
        documents: document.getElementById("documents").value.split(",").map(d=>d.trim()).filter(d=>d),
        security:{
            known_shipper: document.getElementById("known_shipper").value==="true",
            screening: document.getElementById("screening").value,
            regulated_agent: document.getElementById("regulated_agent").value==="true"
        },
        role: document.getElementById("role").value
    };
    fetch("/validate_shipment",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)})
    .then(r=>r.json()).then(res=>{
        let txt=`${res.status==="GREEN"?"GREEN ✅":"RED ❌"}\n`;
        if(res.errors.length>0) txt+="Documentos faltantes o errores:\n• "+res.errors.join("\n• ")+"\n";
        if(res.corrections.length>0) txt+="Correcciones sugeridas:\n• "+res.corrections.join("\n• ")+"\n";
        txt+=`Trazabilidad: ${res.role} @ ${res.timestamp}`;
        document.getElementById("result").innerText=txt;
        ["phase1","phase2","phase3","phase4","phase5","phase6","phase7","phase8"].forEach(pid=>{
            document.getElementById(pid).innerHTML=res.phases[pid].join("<br>")||"Sin alertas";
        });
    });
});
