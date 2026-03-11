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

# Lista básica de UN numbers comunes en carga aérea
DG_UN_DATABASE = {
    "UN3480": "Lithium Ion Batteries",
    "UN3481": "Lithium Ion Batteries contained in equipment",
    "UN3090": "Lithium Metal Batteries",
    "UN3091": "Lithium Metal Batteries contained in equipment",
    "UN1203": "Gasoline",
    "UN1993": "Flammable Liquid N.O.S",
    "UN1845": "Dry Ice",
    "UN2814": "Infectious substances affecting humans",
    "UN3373": "Biological Substance Category B"
}

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html","r",encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/health")
async def health():
    return {"status":"ok"}

# ----------------------------------------------------
# DETECCIÓN AUTOMÁTICA DE MERCANCÍA PELIGROSA
# ----------------------------------------------------
def detect_dangerous_goods(data, phases, errors, corrections):

    docs = data.get("documents", [])
    cargo_type = data.get("cargo_type", "")
    un_numbers = data.get("un_numbers", [])

    dg_detected = False

    # detectar por tipo de carga
    if cargo_type in ["DGR", "BAT", "HAZ"]:
        dg_detected = True

    # detectar por documentos
    for d in docs:
        d_lower = d.lower()

        if "dangerous_goods_declaration" in d_lower:
            dg_detected = True

        if "msds" in d_lower:
            dg_detected = True

    # detectar por UN number
    for un in un_numbers:
        if un in DG_UN_DATABASE:
            dg_detected = True
            phases["phase3"].append(f"DG detectado: {un} - {DG_UN_DATABASE[un]}")

    if dg_detected:

        phases["phase3"].append("Carga clasificada como Dangerous Goods")

        required_docs = [
            "dangerous_goods_declaration",
            "msds",
            "UN_number_list"
        ]

        for r in required_docs:
            if r not in docs:
                msg = f"DG requiere documento: {r}"
                errors.append(msg)
                phases["phase3"].append(msg)
                corrections.append(f"Agregar {r} para cumplimiento IATA DGR")

    return dg_detected


# ----------------------------------------------------
# MOTOR DE VALIDACIÓN PRINCIPAL
# ----------------------------------------------------
def validate_shipment(data, avi_rules, cargo_rules):

    errors = []
    corrections = []

    phases = {f"phase{i}":[] for i in range(1,9)}

    cargo_type = data.get("cargo_type","GENERAL")

    docs_required = cargo_rules.get(cargo_type,{}).get("documents",[])
    copies_inside = cargo_rules.get(cargo_type,{}).get("copies_inside",1)
    copies_outside = cargo_rules.get(cargo_type,{}).get("copies_outside",1)

    docs = data.get("documents",[])

    # -----------------------------
    # FASE 1 DOCUMENTOS
    # -----------------------------
    for doc in docs_required:
        if doc not in docs:

            msg = f"Fase 1: Falta documento obligatorio: {doc}"

            phases["phase1"].append(msg)
            errors.append(msg)

            corrections.append(
                f"Subir {doc} válido con {copies_inside} copias dentro y {copies_outside} afuera"
            )

    # -----------------------------
    # FASE 2 PIEZAS
    # -----------------------------
    if data.get("pieces",0) <= 0:

        msg = "Fase 2: Número de piezas inválido"

        phases["phase2"].append(msg)
        errors.append(msg)

        corrections.append("Ingresar número de piezas válido")

    # -----------------------------
    # FASE 3 PESO
    # -----------------------------
    if data.get("gross_weight",0) <= 0:

        msg = "Fase 3: Peso bruto inválido"

        phases["phase3"].append(msg)
        errors.append(msg)

        corrections.append("Ingresar peso correcto")

    # -----------------------------
    # DETECCIÓN DG AUTOMÁTICA
    # -----------------------------
    dg_detected = detect_dangerous_goods(
        data,
        phases,
        errors,
        corrections
    )

    # -----------------------------
    # FASE 4 VOLUMEN
    # -----------------------------
    if data.get("volume",0) <= 0:

        msg = "Fase 4: Volumen inválido"

        phases["phase4"].append(msg)
        errors.append(msg)

        corrections.append("Ingresar volumen correcto")

    # -----------------------------
    # FASE 5 CALIDAD DOCUMENTAL
    # -----------------------------
    for check in avi_rules.get("document_quality",[]):

        for doc in docs:

            doc_lower = doc.lower()

            if check == "no_tachaduras" and "tachadura" in doc_lower:

                msg = f"Fase 5: {doc} tiene tachaduras"

                phases["phase5"].append(msg)
                errors.append(msg)

                corrections.append(f"Corregir {doc}")

            if check == "no_borrones" and "borrón" in doc_lower:

                msg = f"Fase 5: {doc} tiene borrones"

                phases["phase5"].append(msg)
                errors.append(msg)

                corrections.append(f"Corregir {doc}")

            if check == "letra_legible" and "ilegible" in doc_lower:

                msg = f"Fase 5: {doc} ilegible"

                phases["phase5"].append(msg)
                errors.append(msg)

                corrections.append(f"Reescribir {doc}")

    # -----------------------------
    # FASE 6 KNOWN SHIPPER
    # -----------------------------
    if not data.get("security",{}).get("known_shipper",False):

        msg = "Fase 6: Shipper desconocido"

        phases["phase6"].append(msg)
        errors.append(msg)

        corrections.append("Verificar Known Shipper")

    # -----------------------------
    # FASE 7 REGULATED AGENT
    # -----------------------------
    if not data.get("security",{}).get("regulated_agent",False):

        msg = "Fase 7: No Regulated Agent"

        phases["phase7"].append(msg)
        errors.append(msg)

        corrections.append("Verificar agente regulado")

    # -----------------------------
    # FASE 8 SCREENING
    # -----------------------------
    screening = data.get("security",{}).get("screening","manual")

    if screening not in ["xray","manual"]:

        msg = f"Fase 8: Método de screening inválido: {screening}"

        phases["phase8"].append(msg)
        errors.append(msg)

        corrections.append(
            "Usar método de screening válido (xray/manual)"
        )

    status = "GREEN" if len(errors)==0 else "RED"

    return {
        "status": status,
        "errors": errors,
        "corrections": corrections,
        "phases": phases,
        "role": data.get("role","Desconocido"),
        "timestamp": datetime.datetime.now().strftime("%m/%d/%Y, %I:%M:%S %p")
    }


# ----------------------------------------------------
# API VALIDACIÓN
# ----------------------------------------------------
@app.post("/validate_shipment")
async def validate(data: dict):

    result = validate_shipment(
        data,
        avianca_rules,
        cargo_rules
    )

    return JSONResponse(result)
