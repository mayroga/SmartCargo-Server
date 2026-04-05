from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os

app = FastAPI(title="AL CIELO - SmartCargo Advisory")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- LÍMITES TÉCNICOS AVIANCA ---
LIMITS = {
    "BELLY_MAX_H": 63,      # Pulgadas (A320/A330 Pax)
    "FREIGHTER_MAX_H": 96,  # Pulgadas (A330F Estándar)
    "FREIGHTER_CONTOUR": 118, # Pulgadas (Main Deck High Contour)
    "MAX_POSSIBLE_H": 125   # Altura máxima física (Pallet sobrepasado)
}

class Piece(BaseModel):
    l: float
    w: float
    h: float
    p: float
    packaging: str

class PreCheckRequest(BaseModel):
    user_role: str
    cargo_type: str
    uld_type: Optional[str] = None # Ya no es obligatorio
    pieces: List[Piece]
    raw_text: str

@app.post("/precheck")
async def precheck(data: PreCheckRequest):
    instructions = []
    total_vol = 0
    total_weight = 0
    status = "READY"
    role_tag = f"[{data.user_role}]"

    for i, p in enumerate(data.pieces):
        total_weight += p.p
        vol = (p.l * p.w * p.h) / 166
        total_vol += vol
        
        # --- VALIDACIÓN DE ALTURA LÓGICA ---
        if p.h > LIMITS["MAX_POSSIBLE_H"]:
            instructions.append(f"❌ {role_tag} ERROR CRÍTICO: Altura de {p.h}in es IMPOSIBLE. Verificar medidas (Máximo 125in).")
            status = "REJECT"
            continue

        # Sugerencia de Avión
        if p.h <= LIMITS["BELLY_MAX_H"]:
            instructions.append(f"✅ {role_tag} Pieza #{i+1}: Apta para Avión de Pasajeros y Carguero.")
        elif p.h <= LIMITS["FREIGHTER_MAX_H"]:
            instructions.append(f"⚠️ {role_tag} Pieza #{i+1}: EXEDE altura de Pasajeros. Mover a vuelo CARGUERO (A330F).")
        else:
            instructions.append(f"🚨 {role_tag} Pieza #{i+1}: Altura Crítica ({p.h}in). Requiere posición central en Main Deck del Carguero.")

        # --- OPCIONES DE MADERA / PALLETS ---
        if "WOOD" in p.packaging.upper() or "PALLET" in p.packaging.upper():
            text = data.raw_text.upper()
            if "SELLO" not in text and "ISPM" not in text:
                instructions.append(f"💡 OPCIÓN A: Cambiar carga a Pallet de Plástico (No requiere sello).")
                instructions.append(f"💡 OPCIÓN B: Llevar a estación de fumigado en MIA antes del cierre de vuelo.")
                status = "HOLD"

    # --- LÓGICA DE ULD O CARGA SUELTA ---
    if not data.uld_type or data.uld_type == "NONE":
        instructions.append(f"📦 INFO: Procesando como CARGA SUELTA (Loose Cargo). Se requiere estiba manual.")
    
    chargeable = round(max(total_weight, total_vol), 2)

    return {
        "status": status,
        "instructions": instructions,
        "chargeable_weight": chargeable,
        "advice": "Contactar a Supervisor de Rampa si la altura excede 96in para asegurar posición."
    }

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
