from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json
import datetime
import os

app = FastAPI(title="SMARTGOSERVER")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Static
app.mount("/static", StaticFiles(directory="static"), name="static")

# -------------------------------
# CARGAR REGLAS DESDE JSON
# -------------------------------
def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

BASE_DIR = os.path.dirname(__file__)
cargo_rules = load_json(os.path.join(BASE_DIR, "static/cargo_rules.json"))
avianca_rules = load_json(os.path.join(BASE_DIR, "static/avianca_rules.json"))

# -------------------------------
# VALIDACIÓN DE VOLUMEN
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
    volume = round(L*W*H,3)
    return volume

# -------------------------------
# VALIDACIÓN AVIANA
# -------------------------------
def avianca_validation(data):
    errores = []
    advertencias = []

    aircraft_limits = avianca_rules["aircraft_limits"]
    max_height_freighter = aircraft_limits.get("max_height_freighter_in",96)*0.0254*100  # cm
    max_height_belly = aircraft_limits.get("max_height_belly_in",63)*0.0254*100  # cm
    max_pallet_weight = aircraft_limits.get("max_pallet_weight_kg",6800)

    alto = data.get("tallest_piece",0)
    largo = data.get("longest_piece",0)
    ancho = data.get("widest_piece",0)
    peso = data.get("heaviest_piece",0)

    if peso > max_pallet_weight:
        errores.append(f"🔴 Excede peso máximo pallet ({max_pallet_weight}kg)")

    if alto > max_height_freighter:
        errores.append(f"🔴 Altura excede carguero ({max_height_freighter}cm)")
    elif alto > max_height_belly:
        advertencias.append(f"🟡 Solo puede ir en Main Deck / Freighter")

    if largo + ancho + alto > 254:
        advertencias.append("🟡 Oversize cargo. Verificar estiba.")
    if peso > 50:
        advertencias.append("🟡 Carga pesada (>50kg). Verificar shoring.")

    return errores, advertencias

# -------------------------------
# RECOMENDACIÓN AVIÓN
# -------------------------------
def aircraft_recommendation(data):
    alto = data.get("tallest_piece",0)
    aircraft_limits = avianca_rules["aircraft_limits"]
    max_height_belly = aircraft_limits.get("max_height_belly_in",63)*0.0254*100
    max_height_freighter = aircraft_limits.get("max_height_freighter_in",96)*0.0254*100

    if alto <= max_height_belly:
        return "B787 Belly / A330 Lower Deck"
    if alto <= max_height_freighter:
        return "A330-200F Main Deck"
    return "NO AIRCRAFT AVAILABLE"

# -------------------------------
# MOTOR DE RIESGO
# -------------------------------
def risk_engine(data):
    riesgos = []
    probabilidad_hold = 0

    descripcion = data.get("description","").lower()
    destino = data.get("destination","")
    shipper = data.get("shipper_type","unknown")

    dgr_keywords = ["battery","lithium","aerosol","perfume","chemical","paint","fuel","gas"]
    food_keywords = ["food","meat","fish","fruit","vegetable"]
    plant_keywords = ["plant","seed","flower","wood","soil"]

    for w in dgr_keywords:
        if w in descripcion:
            riesgos.append("Posible DGR oculto")
            probabilidad_hold += 25
            break

    if destino.upper() == "USA":
        for w in food_keywords:
            if w in descripcion:
                riesgos.append("Posible inspección CBP")
                probabilidad_hold += 20
                break
        for w in plant_keywords:
            if w in descripcion:
                riesgos.append("Posible inspección USDA")
                probabilidad_hold += 20
                break

    if shipper == "unknown":
        riesgos.append("Shipper desconocido")
        probabilidad_hold += 15

    high_risk = probabilidad_hold >= 50
    return riesgos, probabilidad_hold, high_risk

# -------------------------------
# VALIDACIÓN PRINCIPAL
# -------------------------------
def validate_shipment(data):
    errores = []
    advertencias = []

    volume = calculate_volume(data)
    e,a = avianca_validation(data)
    errores.extend(e)
    advertencias.extend(a)

    aircraft = aircraft_recommendation(data)
    riesgos, probabilidad_hold, high_risk = risk_engine(data)

    # ESTADO FINAL
    if errores:
        status = "🔴 NO FLY"
    elif advertencias:
        status = "🟡 FIX BEFORE COUNTER"
    else:
        status = "🟢 READY FOR COUNTER"

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
# ENDPOINTS
# -------------------------------
@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html","r",encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/health")
async def health():
    return {"status":"ok"}

@app.post("/validate_shipment")
async def validate(data: dict):
    result = validate_shipment(data)
    return JSONResponse(result)
