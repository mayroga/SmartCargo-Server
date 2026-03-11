from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json
import datetime

app = FastAPI(title="SMARTGOSERVER")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

app.mount("/static", StaticFiles(directory="static"), name="static")

with open("static/cargo_rules.json","r",encoding="utf-8") as f:
    cargo_rules = json.load(f)

with open("static/avianca_rules.json","r",encoding="utf-8") as f:
    avianca_rules = json.load(f)

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

ULD_TYPES = {
    "PMC": {"width":96,"length":125,"height":96,"max_weight":6800},
    "PAG": {"width":88,"length":125,"height":96,"max_weight":4626},
    "PAJ": {"width":88,"length":125,"height":63,"max_weight":4626},
    "PQA": {"width":96,"length":125,"height":96,"max_weight":11340}
}

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html","r",encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/health")
async def health():
    return {"status":"ok"}

def detect_dangerous_goods(data, phases, errors, corrections):

    docs = data.get("documents", [])
    cargo_type = data.get("cargo_type", "")
    un_numbers = data.get("un_numbers", [])

    dg_detected = False

    if cargo_type in ["DGR","BAT","HAZ"]:
        dg_detected = True

    for d in docs:
        dl = d.lower()
        if "dangerous_goods_declaration" in dl:
            dg_detected = True
        if "msds" in dl:
            dg_detected = True

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

def validate_dimensions(data, phases, errors, corrections):

    tallest = data.get("tallest_piece",0)
    widest = data.get("widest_piece",0)
    longest = data.get("longest_piece",0)
    heaviest = data.get("heaviest_piece",0)

    if tallest > 96:
        msg = "Altura mayor a 96 pulgadas. No puede volar en Avianca"
        phases["phase2"].append(msg)
        errors.append(msg)

    elif tallest > 63:
        msg = "Altura mayor a 63 pulgadas. Solo puede volar en carguero"
        phases["phase2"].append(msg)
        corrections.append("Reservar vuelo Freighter")

    if widest > 125:
        msg = "Carga sobresale ancho pallet estándar"
        phases["phase2"].append(msg)
        errors.append(msg)

    if longest > 125:
        msg = "Carga demasiado larga para pallet estándar"
        phases["phase2"].append(msg)
        errors.append(msg)

    if heaviest > 150:
        msg = "Pieza mayor a 150kg requiere base de madera (shoring)"
        phases["phase2"].append(msg)
        corrections.append("Agregar base de madera para distribución de peso")

def validate_shipment(data, avi_rules, cargo_rules):

    errors = []
    corrections = []

    phases = {f"phase{i}":[] for i in range(1,9)}

    cargo_type = data.get("cargo_type","GENERAL")
    docs_required = cargo_rules.get(cargo_type,{}).get("documents",[])
    copies_inside = cargo_rules.get(cargo_type,{}).get("copies_inside",1)
    copies_outside = cargo_rules.get(cargo_type,{}).get("copies_outside",1)

    docs = data.get("documents",[])

    for doc in docs_required:
        if doc not in docs:

            msg = f"Fase 1: Falta documento obligatorio: {doc}"

            phases["phase1"].append(msg)
            errors.append(msg)

            corrections.append(
                f"Subir {doc} con {copies_inside} copias internas y {copies_outside} externas"
            )

    if data.get("pieces",0) <= 0:

        msg = "Fase 2: Número de piezas inválido"

        phases["phase2"].append(msg)
        errors.append(msg)
        corrections.append("Ingresar número correcto de piezas")

    validate_dimensions(data, phases, errors, corrections)

    if data.get("gross_weight",0) <= 0:

        msg = "Fase 3: Peso bruto inválido"

        phases["phase3"].append(msg)
        errors.append(msg)
        corrections.append("Ingresar peso correcto")

    detect_dangerous_goods(data, phases, errors, corrections)

    if data.get("volume",0) <= 0:

        msg = "Fase 4: Volumen inválido"

        phases["phase4"].append(msg)
        errors.append(msg)
        corrections.append("Ingresar volumen correcto")

    for check in avi_rules.get("document_quality",[]):

        for doc in docs:

            doc_lower = doc.lower()

            if check=="no_tachaduras" and "tachadura" in doc_lower:

                msg = f"Fase 5: {doc} tiene tachaduras"
                phases["phase5"].append(msg)
                errors.append(msg)
                corrections.append(f"Corregir {doc}")

            if check=="no_borrones" and "borron" in doc_lower:

                msg = f"Fase 5: {doc} tiene borrones"
                phases["phase5"].append(msg)
                errors.append(msg)
                corrections.append(f"Corregir {doc}")

            if check=="letra_legible" and "ilegible" in doc_lower:

                msg = f"Fase 5: {doc} ilegible"
                phases["phase5"].append(msg)
                errors.append(msg)
                corrections.append(f"Rehacer {doc}")

    if not data.get("security",{}).get("known_shipper",False):

        msg = "Fase 6: Shipper no registrado"

        phases["phase6"].append(msg)
        errors.append(msg)
        corrections.append("Validar Known Shipper TSA")

    if not data.get("security",{}).get("regulated_agent",False):

        msg = "Fase 7: Agente no regulado"

        phases["phase7"].append(msg)
        errors.append(msg)
        corrections.append("Validar agente regulado")

    screening = data.get("security",{}).get("screening","manual")

    if screening not in ["xray","manual"]:

        msg = f"Fase 8: Método de screening inválido: {screening}"

        phases["phase8"].append(msg)
        errors.append(msg)
        corrections.append("Usar método xray o manual")

    status = "GREEN" if len(errors)==0 else "RED"

    return {
        "status":status,
        "errors":errors,
        "corrections":corrections,
        "phases":phases,
        "role":data.get("role","Desconocido"),
        "timestamp":datetime.datetime.now().strftime("%m/%d/%Y, %I:%M:%S %p")
    }

@app.post("/validate_shipment")
async def validate(data: dict):

    result = validate_shipment(
        data,
        avianca_rules,
        cargo_rules
    )

    return JSONResponse(result)
