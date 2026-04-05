from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os

app = FastAPI(title="AL CIELO - SmartCargo Advisory")

# Configuración de CORS para permitir peticiones desde cualquier origen
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
    "MAX_POSSIBLE_H": 125   # Altura máxima física
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
    uld_type: Optional[str] = None
    pieces: List[Piece]
    raw_text: str

# --- RUTA PRINCIPAL (FRONTEND) ---
@app.get("/")
async def read_index():
    # Esto soluciona el error "Not Found" al entrar al link de Render
    return FileResponse(os.path.join('static', 'app.html'))

# --- ENDPOINT DE ASESORÍA ---
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
        
        # Validación de Altura
        if p.h > LIMITS["MAX_POSSIBLE_H"]:
            instructions.append(f"❌ {role_tag} ERROR CRÍTICO: Altura de {p.h}in es físicamente imposible para el equipo actual.")
            status = "REJECT"
            continue

        if p.h <= LIMITS["BELLY_MAX_H"]:
            instructions.append(f"✅ {role_tag} Pieza #{i+1}: Dimensiones compatibles con PAX y Carguero.")
        elif p.h <= LIMITS["FREIGHTER_MAX_H"]:
            instructions.append(f"⚠️ {role_tag} Pieza #{i+1}: Excede altura de pasajeros (Belly). Solo para CARGUERO.")
        else:
            instructions.append(f"🚨 {role_tag} Pieza #{i+1}: Altura Crítica ({p.h}in). Requiere posición en centro de Main Deck.")

        # Opciones de Pallet/Madera
        pkg = p.packaging.upper()
        if "WD" in pkg or "MADERA" in pkg or "PALLET" in pkg:
            text = data.raw_text.upper()
            if "SELLO" not in text and "ISPM" not in text:
                instructions.append(f"💡 OPCIÓN A: Cambiar carga a Pallet de Plástico.")
                instructions.append(f"💡 OPCIÓN B: Tramitar fumigado inmediato con sello ISPM15.")
                status = "HOLD"

    if not data.uld_type or data.uld_type == "NONE":
        instructions.append(f"📦 INFO: Procesando como CARGA SUELTA (Loose Cargo).")
    
    chargeable = round(max(total_weight, total_vol), 2)

    return {
        "status": status,
        "instructions": instructions,
        "chargeable_weight": chargeable,
        "advice": "Coordinar con rampa para asegurar estiba correcta según el tipo de avión asignado."
    }

# Montaje de archivos estáticos
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    # Render usa la variable de entorno PORT
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
