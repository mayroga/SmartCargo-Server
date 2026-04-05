from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import os

app = FastAPI(title="AL CIELO - SmartCargo Advisory MIA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CARGA DE REGLAS MAESTRAS (JSON ESTRUCTURADO) ---
def load_rules(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

AVIANCA_RULES = load_rules("static/avianca_rules.json")
CARGO_RULES = load_rules("static/cargo_rules.json")

class Piece(BaseModel):
    l: float; w: float; h: float; p: float
    packaging: str  # wood, plastic, box, pallet, etc.

class PreCheckRequest(BaseModel):
    user_role: str
    cargo_type: str
    uld_type: str
    pieces: List[Piece]
    raw_text: str
    origin_country: str = "USA"
    dest_country: str = "COL"

@app.post("/precheck")
async def precheck(data: PreCheckRequest):
    instructions = []
    total_weight = 0
    total_vol_weight = 0
    reject = False
    
    # 1. VALIDACIÓN INICIAL DE DATOS
    if not data.pieces:
        return {"status": "ERROR", "instructions": ["DATOS FALTANTES: Se requiere ID de piezas."]}

    # 2. AUDITORÍA TÉCNICA DE AERONAVE (AVIANCA LIMITS)
    limits = AVIANCA_RULES.get("aircraft_limits", {})
    uld_info = AVIANCA_RULES.get("uld_types", {}).get(data.uld_type, {})
    
    for i, p in enumerate(data.pieces):
        p_weight = p.p
        total_weight += p_weight
        vol_weight = (p.l * p.w * p.h) / 166
        total_vol_weight += vol_weight
        
        # Validación de Altura Estricta
        max_h = limits.get("max_height_belly_in", 63) if data.uld_type == "AKE" else limits.get("max_height_freighter_in", 96)
        if p.h > max_h:
            instructions.append(f"❌ PIEZA #{i+1}: Altura {p.h}in excede límite de {data.uld_type}. RE-UBICAR O RE-PALLETIZAR.")
            reject = True

        # Validación de Peso Máximo por Pieza
        if p_weight > limits.get("max_piece_weight_kg", 150) and p.packaging.lower() == "boxes":
            instructions.append(f"⚠️ PIEZA #{i+1}: Peso excesivo para caja individual. Sugerido: MONTAR EN PALLET.")

    # 3. AUDITORÍA DE EMBALAJE (USDA/ISPM15)
    text = data.raw_text.upper()
    if any("WOOD" in p.packaging.upper() or "PALLET" in p.packaging.upper() for p in data.pieces):
        if "SELLO" not in text and "ISPM" not in text:
            instructions.append("❌ ORDEN: Madera sin sello ISPM15. FUMIGAR O CAMBIAR A PLÁSTICO INMEDIATAMENTE.")
            reject = True

    # 4. AUDITORÍA DOCUMENTAL (CARGO RULES & COUNTRY SPECIFIC)
    cargo_info = CARGO_RULES.get(data.cargo_type, CARGO_RULES.get("GENERAL"))
    required_docs = list(cargo_info.get("documents", []))
    
    # Añadir requisitos por país (USA/COL/ETC)
    country_docs = AVIANCA_RULES.get("country_specific", {}).get(data.origin_country, [])
    for d in country_docs:
        if d not in required_docs: required_docs.append(d)

    # 5. ALERTAS DE RIESGO OPERATIVO (TSA/CBP)
    if any(x in text for x in ["ROTO", "DAÑADO", "MOJADO", "WET", "SIN FLEJE"]):
        instructions.append("❌ RECHAZO TSA/CBP: Empaque comprometido. No apto para inspección de seguridad.")
        reject = True

    # 6. RESULTADO RESOLUTIVO (PESO COBRABLE)
    chargeable = round(max(total_weight, total_vol_weight), 2)
    
    return {
        "status": "READY TO FLY" if not reject else "REJECT / HOLD",
        "advisory_orders": instructions if instructions else ["Carga cumple con estándares Avianca. Proceder al counter."],
        "pouch_setup": {
            "required_documents": required_docs,
            "copies_inside": cargo_info.get("copies_inside", 1),
            "copies_outside": cargo_info.get("copies_outside", 1),
            "handling_codes": cargo_info.get("special_handling_codes", [])
        },
        "technical_data": {
            "chargeable_weight_kg": chargeable,
            "uld_max_capacity": uld_info.get("max_weight_kg", "N/A"),
            "aircraft_compatibility": "CARGUERO" if any(p.h > 63 for p in data.pieces) else "BELLY/CARGUERO"
        }
    }

# --- SERVICIOS ESTÁTICOS ---
@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html", "r", encoding="utf-8") as f:
        return f.read()

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
