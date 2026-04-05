from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import os

app = FastAPI(title="AL CIELO - SmartCargo Advisory MIA")

# Configuración de CORS para evitar bloqueos de navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CARGA DE REGLAS MAESTRAS (JSON ESTRUCTURADO) ---
# Si los archivos no existen, el sistema usa valores por defecto para no romperse
def load_rules(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

AVIANCA_RULES = load_rules("static/avianca_rules.json")
CARGO_RULES = load_rules("static/cargo_rules.json")

# --- MODELOS DE DATOS ---
class Piece(BaseModel):
    l: float
    w: float
    h: float
    p: float
    packaging: str  # pallet_wd, pallet_pl, boxes, etc.

class PreCheckRequest(BaseModel):
    user_role: str
    cargo_type: str
    uld_type: Optional[str] = None
    pieces: List[Piece]
    raw_text: str
    origin_country: str = "USA"
    dest_country: str = "COL"

# --- LÓGICA DE ASESORÍA TÉCNICA ---
@app.post("/precheck")
async def precheck(data: PreCheckRequest):
    instructions = []
    total_weight = 0
    total_vol_weight = 0
    reject = False
    
    # 1. VALIDACIÓN DE ENTRADA
    if not data.pieces:
        return JSONResponse(status_code=400, content={"status": "ERROR", "instructions": ["No se detectaron piezas para auditar."]})

    # 2. DEFINICIÓN DE LÍMITES (BASADO EN AVIANCA CARGO)
    # Si es AKE o no hay ULD, el límite es Belly (63in). Si es PMC/PAG, es Main Deck (96in o 118in)
    limits = AVIANCA_RULES.get("aircraft_limits", {
        "max_height_belly_in": 63,
        "max_height_freighter_in": 96,
        "max_piece_weight_box_kg": 150
    })

    # 3. AUDITORÍA DE PIEZAS (DIMENSIONES Y PESO)
    for i, p in enumerate(data.pieces):
        total_weight += p.p
        vol_weight = (p.l * p.w * p.h) / 166
        total_vol_weight += vol_weight
        
        # Validación de Altura según tipo de ULD
        current_max_h = limits["max_height_belly_in"]
        if data.uld_type in ["PMC", "PAG"]:
            current_max_h = limits["max_height_freighter_in"]
        
        if p.h > current_max_h:
            instructions.append(f"❌ PIEZA #{i+1}: Altura de {p.h}in excede el límite de {current_max_h}in para este equipo. RE-PALLETIZAR.")
            reject = True

        # Alerta de seguridad por peso en cajas
        if p.p > limits["max_piece_weight_box_kg"] and "BOX" in p.packaging.upper():
            instructions.append(f"⚠️ PIEZA #{i+1}: Peso excesivo ({p.p}kg) para caja suelta. Sugerencia: Montar en Pallet para evitar daños.")

    # 4. AUDITORÍA DE EMBALAJE (AURA SCAN LOGIC)
    text_analysis = data.raw_text.upper()
    
    # Detección de Madera (ISPM15)
    needs_wood_check = any(x in p.packaging.upper() for x in ["PALLET_WD", "WOOD", "CRATE"])
    if needs_wood_check:
        if "SELLO" not in text_analysis and "ISPM" not in text_analysis:
            instructions.append("❌ ORDEN: Madera detectada sin confirmación de sello ISPM15. Llevar el pallet a fumigar o cambiar por plástico.")
            reject = True

    # Detección de daños físicos
    risk_keywords = ["ROTO", "MOJADO", "WET", "DAÑADO", "SIN FLEJE", "BROKEN"]
    if any(word in text_analysis for word in risk_keywords):
        instructions.append("❌ RECHAZO SEGURIDAD: Empaque comprometido detectado por AURA SCAN. No apto para inspección TSA/CBP.")
        reject = True

    # 5. ESTRUCTURA DE DOCUMENTACIÓN (PARA LA TABLA HTML)
    # Obtenemos la lista de documentos según el tipo de carga
    cargo_info = CARGO_RULES.get(data.cargo_type, {
        "documents": ["AWB (1+3)", "Commercial Invoice", "Packing List", "Cédula/ID Responsable"]
    })
    required_docs = list(cargo_info.get("documents", []))
    
    # 6. CÁLCULO DE PESO COBRABLE (EL MAYOR)
    chargeable = round(max(total_weight, total_vol_weight), 2)

    # 7. DETERMINACIÓN DE EQUIPO
    uld_status = "BELLY / CARGUERO"
    if any(p.h > 63 for p in data.pieces) or data.uld_type in ["PMC", "PAG"]:
        uld_status = "FREIGHTER ONLY (MAIN DECK)"

    # RESPUESTA FINAL COMPATIBLE CON EL FRONTEND
    return {
        "status": "READY" if not reject else "REJECT",
        "instructions": instructions if instructions else ["Carga cumple con estándares Avianca. Proceder a pesaje y aceptación."],
        "required_docs": required_docs,
        "chargeable_weight": chargeable,
        "uld_status": uld_status
    }

# --- SERVICIOS DE ARCHIVOS ---
@app.get("/", response_class=HTMLResponse)
async def home():
    try:
        with open("static/app.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Error: static/app.html no encontrado.</h1>"

# Montar la carpeta static para fotos, CSS y JS
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    # Ejecución en puerto 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
