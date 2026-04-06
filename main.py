from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List
import os
import json

app = FastAPI(title="AL CIELO - SmartCargo Advisory MIA")

# =========================
# CORS
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# PATHS
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# =========================
# LOAD RULES
# =========================
def load_rules():
    with open(os.path.join(STATIC_DIR, "avianca_rules.json")) as f:
        avianca = json.load(f)
    with open(os.path.join(STATIC_DIR, "cargo_rules.json")) as f:
        cargo = json.load(f)
    return avianca, cargo

AVI_RULES, CARGO_RULES = load_rules()

# =========================
# ROOT
# =========================
@app.get("/", response_class=HTMLResponse)
async def serve_app():
    file_path = os.path.join(STATIC_DIR, "app.html")
    if not os.path.exists(file_path):
        return HTMLResponse("<h1>ERROR: app.html no encontrado</h1>", status_code=500)
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

# =========================
# MODELS
# =========================
class Piece(BaseModel):
    l: float
    w: float
    h: float
    p: float
    qty: int
    packaging: str
    unit: str

class PreCheckRequest(BaseModel):
    user_role: str
    cargo_type: str
    pieces: List[Piece]
    raw_text: str
    destination: str

# =========================
# AI DETECTION
# =========================
def detect_cargo_type(text):
    text = text.upper()

    if "LITHIUM" in text:
        return "BAT"
    if any(x in text for x in ["UN", "DGR", "FLAMMABLE", "HAZ"]):
        return "DGR"
    if any(x in text for x in ["FOOD", "FLOWER", "FISH"]):
        return "PER"
    if any(x in text for x in ["PHARMA", "VACCINE"]):
        return "PHR"
    if "ANIMAL" in text:
        return "AVI"

    return "GENERAL"

# =========================
# DOCUMENTS
# =========================
def get_required_docs(cargo_type):
    return CARGO_RULES.get(cargo_type, CARGO_RULES["GENERAL"])["documents"]

# =========================
# VALIDATION ENGINE
# =========================
def validate(data, text, cargo_type):
    errors = []
    warnings = []

    text = text.upper()

    # DG
    if cargo_type == "DGR":
        if "UN" not in text:
            errors.append("❌ Falta UN Number")
        if "MSDS" not in text:
            errors.append("❌ Falta MSDS")
        if "DECLARATION" not in text:
            errors.append("❌ Falta Shipper Declaration")

    # Lithium
    if "LITHIUM" in text and "PI" not in text:
        errors.append("❌ Falta Packing Instruction (PI)")

    # Wood ISPM15
    if any(p.packaging in ["PALLET_WD", "CRATE"] for p in data["pieces"]):
        if AVI_RULES["usda_rules"]["wood_packaging_requires_ISPM15"]:
            if "ISPM" not in text:
                warnings.append("🟡 Madera sin sello ISPM15")

    # Peso
    max_weight = AVI_RULES["aircraft_limits"]["max_piece_weight_kg"]
    for i, p in enumerate(data["pieces"]):
        if p.p > max_weight:
            errors.append(f"❌ Pieza {i+1} excede {max_weight}kg")

    return errors, warnings

# =========================
# AUTO FIX
# =========================
def auto_fix(errors):
    fixes = []

    for e in errors:
        if "UN" in e:
            fixes.append("👉 Agregar UN Number + Clase + PG")
        if "MSDS" in e:
            fixes.append("👉 Adjuntar MSDS")
        if "Declaration" in e:
            fixes.append("👉 Completar Shipper Declaration firmada")
        if "PI" in e:
            fixes.append("👉 Agregar Packing Instruction correcta")

    return fixes

# =========================
# FINAL STATUS
# =========================
def get_status(errors, warnings):
    if errors:
        return "REJECT"
    if warnings:
        return "RISK"
    return "READY"

# =========================
# DRIVER MESSAGE
# =========================
def driver_msg(status):
    if status == "READY":
        return "🟢 Ve al counter sin problemas."
    if status == "RISK":
        return "🟡 Puede haber retrasos."
    return "🔴 NO vayas al counter."

# =========================
# MAIN ENDPOINT
# =========================
@app.post("/precheck")
async def precheck(data: PreCheckRequest):
    try:
        text = data.raw_text.upper()

        # AUTO DETECTION
        cargo_type = detect_cargo_type(text)

        # DOCS
        docs = get_required_docs(cargo_type)

        # VALIDATION
        errors, warnings = validate(data.dict(), text, cargo_type)

        # FIXES
        fixes = auto_fix(errors)

        # STATUS
        status = get_status(errors, warnings)

        return {
            "status": status,
            "cargo_type_detected": cargo_type,
            "required_docs": docs,
            "errors": errors,
            "warnings": warnings,
            "fixes": fixes,
            "driver_message": driver_msg(status),
            "raw_text": data.raw_text  # 🔥 necesario para comparación frontend
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# HEALTH
# =========================
@app.get("/health")
async def health():
    return {"status": "ok"}

# =========================
# RUN
# =========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
