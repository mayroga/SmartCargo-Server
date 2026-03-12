from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json
import datetime

app = FastAPI(title="SMARTGOSERVER")

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Carpeta estática
app.mount("/static", StaticFiles(directory="static"), name="static")

# Cargar reglas
with open("static/cargo_rules.json","r",encoding="utf-8") as f:
    cargo_rules = json.load(f)

with open("static/avianca_rules.json","r",encoding="utf-8") as f:
    avianca_rules = json.load(f)

# DG base
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

# ULD types
ULD_TYPES = {
    "PMC": {"width":96,"length":125,"height":96,"max_weight":6804,"full_name":"PMC Pallet P6P"},
    "PAG": {"width":88,"length":125,"height":96,"max_weight":4626,"full_name":"PAG Pallet P1P"},
    "PAJ": {"width":88,"length":125,"height":63,"max_weight":4626,"full_name":"PAJ Low Profile"},
    "PQA": {"width":96,"length":125,"height":96,"max_weight":11340,"full_name":"PQA Heavy Duty"}
}

# Home
@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html","r",encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/health")
async def health():
    return {"status":"ok"}

# -------------------------------
# Funciones auxiliares
# -------------------------------
def calculate_volume(data):
    L = data.get("longest_piece",0)
    W = data.get("widest_piece",0)
    H = data.get("tallest_piece",0)
    units = data.get("units","cm")
    if units == "cm":
        L /= 100
        W /= 100
        H /= 100
    elif units == "inches":
        L *= 0.0254
        W *= 0.0254
        H *= 0.0254
    return round(L*W*H,3)

def avianca_validation(data):
    errores = []
    advertencias = []
    L = data.get("longest_piece",0)
    W = data.get("widest_piece",0)
    H = data.get("tallest_piece",0)
    peso = data.get("heaviest_piece",0)

    if peso > 50:
        advertencias.append("Carga pesada (>50kg). Revise shoring.")
    if L + W + H > 254:
        advertencias.append("Oversize cargo. Requiere revisión de estiba.")
    if H > 244:
        errores.append("Altura excede límite carguero (244 cm).")
    elif H > 160:
        advertencias.append("Solo puede ir en Main Deck.")
    if peso > 6804:
        errores.append("Excede peso máximo pallet PMC (6804kg).")
    if L > 358 or H > 256:
        errores.append("No cabe por puerta de carga A330.")
    return errores, advertencias

def aircraft_recommendation(data):
    alto = data.get("tallest_piece",0)
    if alto <= 160:
        return "B787 Belly / A330 Lower Deck"
    if alto <= 244:
        return "A330-200F Main Deck"
    return "NO AIRCRAFT AVAILABLE"

def risk_engine(data):
    riesgos = []
    probabilidad_hold = 0
    descripcion = data.get("description","").lower()
    destino = data.get("destination","")
    shipper = data.get("shipper_type","unknown")

    dgr_keywords = ["battery","lithium","aerosol","perfume","chemical","paint","fuel","gas"]
    for w in dgr_keywords:
        if w in descripcion:
            riesgos.append("Posible DGR oculto")
            probabilidad_hold += 25
            break

    food_keywords = ["food","meat","fish","fruit","vegetable"]
    if destino=="USA":
        for w in food_keywords:
            if w in descripcion:
                riesgos.append("Posible inspección CBP")
                probabilidad_hold += 20
                break

    plant_keywords = ["plant","seed","flower","wood","soil"]
    for w in plant_keywords:
        if w in descripcion:
            riesgos.append("Posible inspección USDA")
            probabilidad_hold += 20
            break

    if shipper=="unknown":
        riesgos.append("Shipper desconocido")
        probabilidad_hold += 15

    high_risk = probabilidad_hold >= 50
    return riesgos, probabilidad_hold, high_risk

# -------------------------------
# Validador completo
# -------------------------------
def validate_shipment(data):
    errores = []
    advertencias = []
    recomendaciones = []

    volume = calculate_volume(data)
    e,a = avianca_validation(data)
    errores.extend(e)
    advertencias.extend(a)

    aircraft = aircraft_recommendation(data)
    riesgos, probabilidad_hold, high_risk = risk_engine(data)

    # Generar mensajes educativos paso a paso
    instrucciones = []

    # Estado general
    if len(errores) > 0:
        status = "🔴 NO FLY"
        instrucciones.append("Carga crítica. Revise cada campo y siga instrucciones para corregir problemas antes de presentarse en el counter.")
    elif len(advertencias) > 0:
        status = "🟡 FIX BEFORE COUNTER"
        instrucciones.append("Hay advertencias. Revise embalaje, peso y dimensiones antes de enviar.")
    else:
        status = "🟢 READY FOR COUNTER"
        instrucciones.append("Carga correcta. Puede proceder al counter, mantenga documentos listos y embalaje seguro.")

    # Mensajes educativos
    if volume > 2:
        instrucciones.append("El volumen es alto (>2 m³). Verifique estabilidad en pallets y equipo de carga.")

    if high_risk:
        instrucciones.append("Alto riesgo detectado. Revise mercancía peligrosa o desconocida.")

    # Recomendaciones por riesgo
    if "Posible DGR oculto" in riesgos:
        instrucciones.append("Revise DGR: etiquetas, declaración de mercancía peligrosa y MSDS.")

    result = {
        "status": status,
        "errors": errores,
        "warnings": advertencias,
        "risks": riesgos,
        "high_risk": high_risk,
        "probabilidad_hold": probabilidad_hold,
        "aircraft_recommendation": aircraft,
        "volume_m3": volume,
        "timestamp": datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S"),
        "instructions": instrucciones
    }

    return result

@app.post("/validate_shipment")
async def validate(data: dict):
    result = validate_shipment(data)
    return JSONResponse(result)
