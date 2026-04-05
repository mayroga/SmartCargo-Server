from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os

app = FastAPI(title="AL CIELO - SmartCargo Advisory")

# Configuración de seguridad y conexión
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ESTÁNDARES TÉCNICOS AVIANCA (PULGADAS) ---
LIMITS = {
    "PAX_MAX_H": 63,       # Altura máxima Avión de Pasajeros (Belly)
    "CARGO_STD_H": 96,     # Altura estándar Avión Carguero
    "CARGO_MAX_H": 118,    # Altura máxima permitida (Main Deck)
    "ABSOLUTE_MAX": 125    # Límite físico absoluto para seguridad aérea
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
    pieces: List[Piece]
    raw_text: str

# --- NAVEGACIÓN PRINCIPAL ---
@app.get("/")
async def serve_app():
    # Carga la interfaz maestra directamente
    return FileResponse(os.path.join('static', 'app.html'))

# --- MOTOR DE ASESORÍA INTELIGENTE ---
@app.post("/precheck")
async def precheck(data: PreCheckRequest):
    instructions = []
    total_vol = 0
    total_weight = 0
    status = "READY"
    role = data.user_role
    
    # Procesamiento pieza por pieza
    for i, p in enumerate(data.pieces):
        total_weight += p.p
        # Fórmula IATA: (L x W x H) / 166 para Libras, pero aquí estandarizamos a KGv
        vol_kg = (p.l * p.w * p.h) / 166 
        total_vol += vol_kg
        
        # 1. Validación de Altura (El punto más crítico en Avianca)
        if p.h > LIMITS["ABSOLUTE_MAX"]:
            instructions.append(f"PIEZA #{i+1}: ERROR DE MEDIDA. {p.h}in es imposible de cargar. Verifique dimensiones.")
            status = "REJECT"
        elif p.h > LIMITS["CARGO_MAX_H"]:
            instructions.append(f"PIEZA #{i+1}: SOBREPASADA ({p.h}in). Requiere equipo especial y posición central.")
            status = "HOLD"
        elif p.h > LIMITS["PAX_MAX_H"]:
            instructions.append(f"PIEZA #{i+1}: SOLO CARGUERO. Excede las 63in permitidas en aviones de pasajeros.")
        else:
            instructions.append(f"PIEZA #{i+1}: DIMENSIONES ÓPTIMAS. Apta para cualquier tipo de avión.")

    # 2. Análisis de Texto (Madera y Empaque)
    text_check = data.raw_text.upper()
    if ("MADERA" in text_check or "PALLET" in text_check) and ("SELLO" not in text_check and "ISPM" not in text_check):
        instructions.append("⚠️ DETECTADO: Madera sin sello visible.")
        instructions.append("💡 SOLUCIÓN A: Cambiar a Pallet de Plástico (No requiere certificación).")
        instructions.append("💡 SOLUCIÓN B: Llevar a fumigación inmediata en estación MIA.")
        status = "HOLD" if status != "REJECT" else "REJECT"

    if "ROTO" in text_check or "DAÑADO" in text_check:
        instructions.append("❌ ALERTA: Empaque dañado. TSA rechazará la carga en el counter.")
        status = "REJECT"

    # Cálculo de Peso Cobrable (El mayor entre Bruto y Volumétrico)
    chargeable = round(max(total_weight, total_vol), 2)

    return {
        "status": status,
        "instructions": instructions,
        "chargeable_weight": f"{chargeable} KG",
        "advice": "Presentar reporte PDF en rampa para agilizar la estiba."
    }

# Montaje de archivos estáticos para Render
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    # Render asigna el puerto automáticamente mediante la variable PORT
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
