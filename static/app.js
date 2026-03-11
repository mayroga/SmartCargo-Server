let cargoRules = {};
let aviancaRules = {};

// cargar reglas
async function loadRules(){
    try{
        const cargoRes = await fetch("/static/cargo_rules.json");
        cargoRules = await cargoRes.json();

        const aviancaRes = await fetch("/static/avianca_rules.json");
        aviancaRules = await aviancaRes.json();
    }catch(e){
        console.error("Error cargando reglas:",e);
    }
}

document.addEventListener("DOMContentLoaded",()=>{

    loadRules();

    // calcular volumen automáticamente
    function calculateVolume(){
        const l=parseFloat(document.getElementById("length").value)||0;
        const w=parseFloat(document.getElementById("width").value)||0;
        const h=parseFloat(document.getElementById("height").value)||0;

        if(l>0 && w>0 && h>0){
            const volume=(l*w*h).toFixed(3);
            document.getElementById("volume").value=volume;
        }
    }

    ["length","width","height"].forEach(id=>{
        const el=document.getElementById(id);
        if(el) el.addEventListener("input",calculateVolume);
    });

    // toggle fases tipo cortina
    document.querySelectorAll(".phase").forEach(p=>{
        p.addEventListener("click",()=>{
            const content=document.getElementById("phase"+p.dataset.phase);
            if(!content) return;

            if(content.style.display==="block"){
                content.style.display="none";
            }else{
                content.style.display="block";
            }
        });
    });

    // botón validar
    const validateBtn=document.getElementById("validateBtn");

    if(validateBtn){
        validateBtn.addEventListener("click",async()=>{

            const data={
                mawb: document.getElementById("mawb").value.trim(),
                hawb: document.getElementById("hawb").value.trim(),
                airline: document.getElementById("airline").value.trim(),
                flight_number: document.getElementById("flight_number").value.trim(),
                flight_date: document.getElementById("flight_date").value,
                origin: document.getElementById("origin").value.trim(),
                destination: document.getElementById("destination").value.trim(),
                cargo_type: document.getElementById("cargo_type").value,

                pieces: parseInt(document.getElementById("pieces").value)||0,

                length: parseFloat(document.getElementById("length").value)||0,
                width: parseFloat(document.getElementById("width").value)||0,
                height: parseFloat(document.getElementById("height").value)||0,

                volume: parseFloat(document.getElementById("volume").value)||0,
                gross_weight: parseFloat(document.getElementById("gross_weight").value)||0,

                documents: document.getElementById("documents").value
                    .split(",")
                    .map(d=>d.trim())
                    .filter(d=>d.length>0),

                security:{
                    known_shipper: document.getElementById("known_shipper").value==="true",
                    screening: document.getElementById("screening").value,
                    regulated_agent: document.getElementById("regulated_agent").value==="true"
                },

                role: document.getElementById("role").value || "unknown"
            };

            try{

                const response=await fetch("/validate_shipment",{
                    method:"POST",
                    headers:{
                        "Content-Type":"application/json"
                    },
                    body:JSON.stringify(data)
                });

                const res=await response.json();

                // resultado global
                let txt=`${res.status==="GREEN"?"GREEN ✅":"RED ❌"}\n`;

                if(res.errors && res.errors.length>0){
                    txt+="Errores detectados:\n• "+res.errors.join("\n• ")+"\n";
                }

                if(res.corrections && res.corrections.length>0){
                    txt+="Correcciones sugeridas:\n• "+res.corrections.join("\n• ")+"\n";
                }

                txt+=`Trazabilidad: ${res.role || "unknown"} @ ${res.timestamp}`;

                const resultDiv=document.getElementById("result");
                if(resultDiv) resultDiv.innerText=txt;

                // mostrar fases
                if(res.phases){

                    ["phase1","phase2","phase3","phase4","phase5","phase6","phase7","phase8"].forEach(pid=>{

                        const el=document.getElementById(pid);
                        if(!el) return;

                        const phaseData=res.phases[pid];

                        if(Array.isArray(phaseData) && phaseData.length>0){
                            el.innerHTML=phaseData.join("<br>");
                        }else{
                            el.innerHTML="Sin alertas";
                        }

                    });

                }

            }catch(err){

                console.error("Error validando:",err);

                const resultDiv=document.getElementById("result");
                if(resultDiv){
                    resultDiv.innerText="❌ Error conectando con el servidor";
                }

            }

        });
    }

});
