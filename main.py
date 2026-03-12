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

# -------------------------------
# CARGAR REGLAS
# -------------------------------
with open("static/cargo_rules.json","r",encoding="utf-8") as f:
    cargo_rules = json.load(f)

with open("static/avianca_rules.json","r",encoding="utf-8") as f:
    avianca_rules = json.load(f)

# -------------------------------
# BASE DG
# -------------------------------
DG_UN_DATABASE = {
    "UN3480": "Lithium Ion Batteries",
    "UN3481": "Lithium Ion Batteries contained in equipment",
    "UN3090": "Lithium Metal Batteries",
    "UN3091": "Lithium Metal Batteries contained in equipment",
    "UN1203": "Gasoline",
    "UN1993": "Flammable Liquid",
    "UN1845": "Dry Ice",
    "UN2814": "Infectious substances",
    "UN3373": "Biological Substance Category B"
}

# -------------------------------
# ULD TYPES
# -------------------------------
ULD_TYPES = {
    "PMC": {"width":96,"length":125,"height":96,"max_weight":6804,"full_name":"PMC Pallet P6P"},
    "PAG": {"width":88,"length":125,"height":96,"max_weight":4626,"full_name":"PAG Pallet P1P"},
    "PAJ": {"width":88,"length":125,"height":63,"max_weight":4626,"full_name":"PAJ Low Profile"},
    "PQA": {"width":96,"length":125,"height":96,"max_weight":11340,"full_name":"PQA Heavy Duty"}
}

# -------------------------------
# HOME
# -------------------------------
@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html","r",encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/health")
async def health():
    return {"status":"ok"}

# -------------------------------
# VOLUMEN
# -------------------------------
def calculate_volume(data):
    L = data.get("longest_piece",0)
    W = data.get("widest_piece",0)
    H = data.get("tallest_piece",0)
    units = data.get("units","cm")
    if units == "cm":
        L = L/100
        W = W/100
        H = H/100
    if units == "inches":
        L = L*0.0254
        W = W*0.0254
        H = H*0.0254
    return round(L*W*H,3)

# -------------------------------
# VALIDACIONES AVIANA
# -------------------------------
def avianca_validation(data):
    errores = []
    advertencias = []

    largo = data.get("longest_piece",0)
    ancho = data.get("widest_piece",0)
    alto = data.get("tallest_piece",0)
    peso = data.get("heaviest_piece",0)

    if peso > 50:
        advertencias.append("🟡 Carga pesada (>50kg). Verificar shoring.")

    if largo + ancho + alto > 254:
        advertencias.append("🟡 Oversize cargo. Requiere revisión de estiba.")

    if alto > 244:
        errores.append("🔴 Altura excede 244 cm. No puede volar en A330.")
    elif alto > 160:
        advertencias.append("Solo puede ir en Main Deck.")

    if peso > 6804:
        errores.append("🔴 Excede peso máximo pallet PMC (6804kg)")

    if largo > 358 or alto > 256:
        errores.append("🔴 No cabe por puerta de carga A330")

    return errores, advertencias

# -------------------------------
# RECOMENDACION AVION
# -------------------------------
def aircraft_recommendation(data):
    alto = data.get("tallest_piece",0)
    if alto <= 160:
        return "B787 Belly / A330 Lower Deck"
    if alto <= 244:
        return "A330-200F Main Deck"
    return "NO AIRCRAFT AVAILABLE"

# -------------------------------
# MOTOR RIESGO
# -------------------------------
def risk_engine(data):
    riesgos = []
    probabilidad_hold = 0
    descripcion = data.get("description","").lower()
    destino = data.get("destination","")
    shipper = data.get("shipper_type","unknown")

    # DGR oculto
    dgr_keywords = ["battery","lithium","aerosol","perfume","chemical","paint","fuel","gas"]
    for w in dgr_keywords:
        if w in descripcion:
            riesgos.append("Posible DGR oculto")
            probabilidad_hold += 25
            break

    # CBP
    food_keywords = ["food","meat","fish","fruit","vegetable"]
    if destino == "USA":
        for w in food_keywords:
            if w in descripcion:
                riesgos.append("Posible inspección CBP")
                probabilidad_hold += 20
                break

    # USDA
    plant_keywords = ["plant","seed","flower","wood","soil"]
    for w in plant_keywords:
        if w in descripcion:
            riesgos.append("Posible inspección USDA")
            probabilidad_hold += 20
            break

    # TSA
    if shipper == "unknown":
        riesgos.append("Shipper desconocido")
        probabilidad_hold += 15

    high_risk = probabilidad_hold >= 50
    return riesgos, probabilidad_hold, high_risk

# -------------------------------
# DOCUMENT CHECK ENGINE
# -------------------------------
def check_documents(data):
    """
    Revisa que la carga tenga:
    1. Todos los documentos obligatorios
    2. Originales y copias según reglas
    3. Calidad: legible, sin tachaduras, versión válida
    """
    errores = []
    tipo_carga = data.get("iata_code","GEN")
    documentos_presentes = data.get("documents",[])
    quality_check = data.get("document_quality",{})

    reglas = cargo_rules.get(tipo_carga, cargo_rules["GENERAL"])
    docs_obligatorios = reglas.get("documents",[])
    copies_inside = reglas.get("copies_inside",1)
    copies_outside = reglas.get("copies_outside",1)

    # Documentos faltantes
    for doc in docs_obligatorios:
        if doc not in documentos_presentes:
            errores.append(f"Documento faltante: {doc}")

    # Copias y calidad
    for doc in docs_obligatorios:
        doc_quality = quality_check.get(doc, {})
        if doc_quality.get("original_missing", False):
            errores.append(f"Original ausente: {doc}")
        if doc_quality.get("copies_inside",0) < copies_inside:
            errores.append(f"Copias dentro insuficientes: {doc}")
        if doc_quality.get("copies_outside",0) < copies_outside:
            errores.append(f"Copias fuera insuficientes: {doc}")
        if not doc_quality.get("legible", True):
            errores.append(f"Documento ilegible: {doc}")
        if not doc_quality.get("no_tachaduras", True):
            errores.append(f"Documento con tachaduras: {doc}")
        if not doc_quality.get("valid_version", True):
            errores.append(f"Documento con versión inválida: {doc}")

    return errores

# -------------------------------
# VALIDADOR PRINCIPAL
# -------------------------------
def validate_shipment(data):
    errores = []
    advertencias = []

    # Volumen
    volume = calculate_volume(data)

    # Reglas avianca
    e,a = avianca_validation(data)
    errores.extend(e)
    advertencias.extend(a)

    # Aircraft
    aircraft = aircraft_recommendation(data)

    # Riesgos
    riesgos,probabilidad_hold,high_risk = risk_engine(data)

    # Documentos
    doc_errors = check_documents(data)
    errores.extend(doc_errors)

    # Estado final
    if len(errores) > 0:
        status = "🔴 RECHAZADO"
    elif len(advertencias) > 0:
        status = "🟡 ACEPTADO CON ALERTA"
    else:
        status = "🟢 ACEPTADO"

    result = {
        "status": status,
        "errors": errores,
        "warnings": advertencias,
        "risks": riesgos,
        "high_risk": high_risk,
        "probabilidad_hold": probabilidad_hold,
        "aircraft_recommendation": aircraft,
        "volume_m3": volume,
        "timestamp": datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")
    }
    return result

# -------------------------------
# ENDPOINT
# -------------------------------
@app.post("/validate_shipment")
async def validate(data: dict):
    result = validate_shipment(data)
    return JSONResponse(result)
