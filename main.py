from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import json
import os

app = FastAPI(title="SMARTCARGO Validation Engine")

# =======================
# Archivos estáticos
# =======================
app.mount("/static", StaticFiles(directory="static"), name="static")

# =======================
# Cargar reglas
# =======================
CARGO_RULES_PATH = "static/cargo_rules.json"
AVI_RULES_PATH = "static/avianca_rules.json"

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

cargo_rules = load_json(CARGO_RULES_PATH)
avianca_rules = load_json(AVI_RULES_PATH)

# =======================
# Rutas
# =======================
@app.get("/", response_class=HTMLResponse)
async def home():
    try:
        with open("static/app.html", "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except Exception as e:
        return HTMLResponse(f"<h1>Error cargando interfaz</h1><p>{e}</p>")

@app.get("/health")
async def health():
    return {"status":"ok"}

@app.get("/cargo_rules")
async def get_cargo_rules():
    return JSONResponse({"cargo_rules": cargo_rules, "avianca_rules": avianca_rules})

@app.post("/validate_shipment")
async def validate_shipment(data: dict):
    errors = []
    cargo_type = data.get("cargo_type")
    documents = data.get("documents", [])
    pieces = data.get("pieces", 0)
    gross_weight = data.get("gross_weight", 0)
    volume = data.get("volume", 0)
    security = data.get("security", {})

    # Documentos obligatorios cargo_type
    required_docs = cargo_rules.get(cargo_type, {}).get("documents", [])
    for doc in required_docs:
        if doc not in documents:
            errors.append(f"Falta documento: {doc}")

    # Checklist Avianca simplificado
    for doc in avianca_rules.get("folder_order", []):
        if "invoice" in doc and "invoice" not in documents:
            errors.append("Invoice no cumple checklist Avianca")
        if "packing_list" in doc and "packing_list" not in documents:
            errors.append("Packing List no cumple checklist Avianca")

    # Validación física
    if pieces <= 0: errors.append("Número de piezas inválido")
    if gross_weight <= 0: errors.append("Peso inválido")
    if volume <= 0: errors.append("Volumen inválido")

    # Seguridad
    if not security.get("known_shipper", False): errors.append("Shipper no autorizado")
    if security.get("screening") != "xray": errors.append("No se ha realizado screening X-Ray")
    if not security.get("regulated_agent", False): errors.append("No es Regulated Agent")

    status = "GREEN" if len(errors) == 0 else "RED"
    message = "Shipment acceptable" if status=="GREEN" else "Do not go to counter"

    return JSONResponse({
        "status": status,
        "message": message,
        "errors": errors
    })
