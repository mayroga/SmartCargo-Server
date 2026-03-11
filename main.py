from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json, datetime

app = FastAPI(title="SMARTGOSERVER")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Cargar reglas
with open("static/cargo_rules.json","r",encoding="utf-8") as f:
    cargo_rules = json.load(f)
with open("static/avianca_rules.json","r",encoding="utf-8") as f:
    avianca_rules = json.load(f)

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html","r",encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/health")
async def health():
    return {"status":"ok"}

def validate_shipment(data, avi_rules, cargo_rules):
    errors = []
    corrections = []
    phases = {f"phase{i}":[] for i in range(1,9)}  # Inicializar 8 fases

    cargo_type = data.get("cargo_type","GENERAL")
    docs_required = cargo_rules.get(cargo_type,{}).get("documents",[])
    copies_inside = cargo_rules.get(cargo_type,{}).get("copies_inside",1)
    copies_outside = cargo_rules.get(cargo_type,{}).get("copies_outside",1)

    # --- Fase 1: Documentos requeridos ---
    for doc in docs_required:
        if doc not in data.get("documents",[]):
            msg = f"Fase 1: Falta documento obligatorio: {doc}"
            phases["phase1"].append(msg)
            errors.append(msg)
            corrections.append(f"Subir {doc} válido con {copies_inside} copias dentro y {copies_outside} afuera")

    # --- Fase 2: Validación de piezas ---
    if data.get("pieces",0) <= 0:
        msg = "Fase 2: Número de piezas inválido"
        phases["phase2"].append(msg)
        errors.append(msg)
        corrections.append("Ingresar número de piezas válido")

    # --- Fase 3: Validación de peso ---
    if data.get("gross_weight",0) <= 0:
        msg = "Fase 3: Peso bruto inválido"
        phases["phase3"].append(msg)
        errors.append(msg)
        corrections.append("Ingresar peso correcto")

    # --- Fase 4: Validación de volumen ---
    if data.get("volume",0) <= 0:
        msg = "Fase 4: Volumen inválido"
        phases["phase4"].append(msg)
        errors.append(msg)
        corrections.append("Ingresar volumen correcto")

    # --- Fase 5: Calidad de documentos ---
    for check in avi_rules.get("document_quality",[]):
        for doc in data.get("documents",[]):
            doc_lower = doc.lower()
            if check=="no_tachaduras" and "tachadura" in doc_lower:
                msg = f"Fase 5: {doc} tiene tachaduras"
                phases["phase5"].append(msg)
                errors.append(msg)
                corrections.append(f"Corregir {doc}")
            if check=="no_borrones" and "borrón" in doc_lower:
                msg = f"Fase 5: {doc} tiene borrones"
                phases["phase5"].append(msg)
                errors.append(msg)
                corrections.append(f"Corregir {doc}")
            if check=="letra_legible" and "ilegible" in doc_lower:
                msg = f"Fase 5: {doc} ilegible"
                phases["phase5"].append(msg)
                errors.append(msg)
                corrections.append(f"Reescribir {doc}")

    # --- Fase 6: Known Shipper ---
    if not data.get("security",{}).get("known_shipper",False):
        msg = "Fase 6: Shipper desconocido"
        phases["phase6"].append(msg)
        errors.append(msg)
        corrections.append("Verificar Known Shipper")

    # --- Fase 7: Regulated Agent ---
    if not data.get("security",{}).get("regulated_agent",False):
        msg = "Fase 7: No Regulated Agent"
        phases["phase7"].append(msg)
        errors.append(msg)
        corrections.append("Verificar agente regulado")

    # --- Fase 8: Screening ---
    screening = data.get("security",{}).get("screening","manual")
    if screening not in ["xray","manual"]:
        msg = f"Fase 8: Método de screening inválido: {screening}"
        phases["phase8"].append(msg)
        errors.append(msg)
        corrections.append("Usar método de screening válido (xray/manual)")

    status = "GREEN" if len(errors)==0 else "RED"
    return {
        "status": status,
        "errors": errors,
        "corrections": corrections,
        "phases": phases,
        "role": data.get("role","Desconocido"),
        "timestamp": datetime.datetime.now().strftime("%m/%d/%Y, %I:%M:%S %p")
    }

@app.post("/validate_shipment")
async def validate(data: dict):
    result = validate_shipment(data, avianca_rules, cargo_rules)
    return JSONResponse(result)
