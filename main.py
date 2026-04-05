from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os

app = FastAPI()

class Piece(BaseModel):
    l: float; w: float; h: float; p: float; packaging: str

class PreCheckRequest(BaseModel):
    user_role: str; cargo_type: str; uld_type: str; pieces: List[Piece]; raw_text: str

@app.post("/precheck")
async def precheck(data: PreCheckRequest):
    instructions = []
    total_vol_kg = 0
    total_weight_kg = 0
    status = "READY"
    
    # 1. Auditoría Estructural (Medidas Avianca)
    for i, p in enumerate(data.pieces):
        total_weight_kg += p.p
        vol_kg = (p.l * p.w * p.h) / 166
        total_vol_kg += vol_kg
        
        # Conflicto AKE (PAX)
        if data.uld_type == "AKE" and p.h > 63:
            instructions.append(f"PIEZA #{i+1}: Altura {p.h}in incompatible con contenedor AKE (Máx 63in).")
            status = "HOLD"
        
        # Límite absoluto Main Deck
        if p.h > 118:
            instructions.append(f"PIEZA #{i+1}: RECHAZO. Altura excede límites de carguero (118in).")
            status = "REJECT"

    # 2. Protocolo de Madera (Asesoría Preventiva)
    text = data.raw_text.upper()
    if "MADERA" in text or "PALLET" in text:
        if "SELLO" not in text and "ISPM" not in text:
            instructions.append("⚠️ MADERA: No se menciona sello ISPM15. Riesgo de multa CBP.")
            instructions.append("💡 SOLUCIÓN A: Re-embalar en plástico. SOLUCIÓN B: Solicitar fumigación en rampa.")
            if status == "READY": status = "HOLD"

    # 3. Lógica de Cobro (Chargeable)
    chargeable = round(max(total_weight_kg, total_vol_kg), 2)
    
    return {
        "status": status,
        "instructions": instructions,
        "chargeable_weight": f"{chargeable}",
        "uld_position": f"{data.uld_type} - STANDBY"
    }

app.mount("/", StaticFiles(directory="static", html=True), name="static")
