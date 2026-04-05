from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import os

app = FastAPI(title="AL CIELO - SmartCargo Advisory MIA")

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELOS DE DATOS ROBUSTOS ---
class Piece(BaseModel):
    l: float
    w: float
    h: float
    p: float
    qty: int
    packaging: str  # PALLET_WD, PALLET_PL, BOX, CRATE, OVERPACK

class PreCheckRequest(BaseModel):
    shipper_name: Optional[str] = "N/A"
    forwarder_name: Optional[str] = "N/A"
    trucker_name: Optional[str] = "N/A"
    cargo_type: str
    target_aircraft: str
    pieces: List[Piece]
    raw_text: str
    origin: str = "MIA"
    destination: str = "COL"

# --- LÓGICA DE ASESORÍA TÉCNICA ESPECIALIZADA ---
@app.post("/precheck")
async def precheck(data: PreCheckRequest):
    instructions = []
    technical_specs = []
    reject = False
    
    if not data.pieces:
        return JSONResponse(status_code=400, content={"status": "ERROR", "message": "No se detectaron piezas para auditar."})

    # Matriz de Aeronaves Avianca Cargo / MIA Operations
    AIRCRAFT_DATA = [
        {"model": "A330-200F", "deck": "Main Deck", "max_h": 96, "max_w_pos": 6800},
        {"model": "A330-200F", "deck": "Main Deck (High)", "max_h": 118, "max_w_pos": 6800},
        {"model": "B767-300F", "deck": "Main Deck", "max_h": 96, "max_w_pos": 5400},
        {"model": "A330/A321", "deck": "Belly (Lower)", "max_h": 63, "max_w_pos": 4000}
    ]

    total_actual_weight = 0
    total_vol_weight = 0
    max_h_found = 0

    # 1. AUDITORÍA FÍSICA Y DIMENSIONAL
    for i, p in enumerate(data.pieces):
        p_weight = p.p * p.qty
        p_vol = (p.l * p.w * p.h * p.qty) / 166
        total_actual_weight += p_weight
        total_vol_weight += p_vol
        
        if p.h > max_h_found:
            max_h_found = p.h

        # Validación de Peso por Pieza (Manejo Manual vs Mecánico)
        if p.p > 150 and p.packaging == "BOX":
            instructions.append(f"⚠️ PIEZA #{i+1}: Peso individual de {p.p}kg en CAJA excede límite manual. ACCIÓN: Montar en Pallet para evitar rechazo en recepción.")

        # Validación de Altura Crítica
        if p.h > 118:
            instructions.append(f"❌ ERROR CRÍTICO: Pieza #{i+1} mide {p.h}in. Excede el contorno máximo de A330F (118in). RECHAZO INMEDIATO.")
            reject = True
        elif p.h > 96:
            technical_specs.append(f"✈️ REQUIERE POSICIÓN ALTA: Pieza #{i+1} ({p.h}in) solo puede ir en centro de carguero A330F.")
        elif p.h > 63:
            technical_specs.append(f"✈️ SOLO CARGUERO: Pieza #{i+1} ({p.h}in) no es apta para aviones de pasajeros (Bellies).")
        else:
            technical_specs.append(f"✅ VERSATILIDAD: Pieza #{i+1} apta para cualquier equipo (Pax/Carguero).")

    # 2. AUDITORÍA DE EMBALAJE (AURA SCAN LOGIC)
    text_analysis = data.raw_text.upper()
    
    # Detección de Madera ISPM15 (CBP Compliance)
    needs_wood_check = any(p.packaging == "PALLET_WD" or p.packaging == "CRATE" for p in data.pieces)
    if needs_wood_check:
        if "SELLO" not in text_analysis and "ISPM" not in text_analysis:
            instructions.append("⚠️ MADERA DETECTADA: No se confirma sello ISPM15. SOLUCIÓN: El Trucker debe verificar sello físico o llevar a fumigar en MIA antes del counter para evitar multas de CBP.")

    # Detección de Daños (TSA/IATA Safety)
    risk_keywords = ["ROTO", "MOJADO", "WET", "DAÑADO", "SIN FLEJE", "BROKEN", "HOYO"]
    if any(word in text_analysis for word in risk_keywords):
        instructions.append("❌ RECHAZO DE SEGURIDAD: Empaque comprometido detectado por AURA SCAN. ACCIÓN: Re-embalar antes de entregar. No pasará inspección de seguridad.")
        reject = True

    # 3. DOCUMENTACIÓN (PAPELERÍA Y PERMISOS)
    required_docs = ["AWB Original (1+3)", "Commercial Invoice (FOB)", "Packing List", "Shipper ID"]
    if data.cargo_type == "DGR":
        required_docs.extend(["Shipper's Declaration (3 Copias)", "MSDS Actualizada"])
    elif data.cargo_type == "PER":
        required_docs.append("Certificado Fitosanitario Original")

    # 4. RESULTADO FINAL
    chargeable_weight = max(total_actual_weight, total_vol_weight)
    
    status = "REJECT" if reject else "READY"
    if not instructions and not reject:
        instructions.append("Carga cumple con estándares operativos de Avianca Cargo MIA. Proceder a pesaje.")

    return {
        "status": status,
        "instructions": instructions,
        "technical_specs": technical_specs,
        "chargeable_weight": round(chargeable_weight, 2),
        "required_docs": required_docs,
        "aircraft_compatibility": [
            {
                "model": air["model"],
                "deck": air["deck"],
                "status": "OK" if max_h_found <= air["max_h"] else "NO CABE",
                "limit_h": air["max_h"]
            } for air in AIRCRAFT_DATA
        ]
    }

# --- SERVICIOS DE ARCHIVOS ---
@app.get("/", response_class=HTMLResponse)
async def home():
    try:
        with open("static/app.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Error: static/app.html no encontrado.</h1>"

if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
