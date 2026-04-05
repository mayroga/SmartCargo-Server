from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os

# Configuración de la Aplicación Maestra
app = FastAPI(title="AL CIELO - SmartCargo Advisory")

# Control de acceso total para el Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ESTÁNDARES TÉCNICOS AVIANCA (PULGADAS) ---
LIMITS = {
    "PAX_MAX_H": 63,       # Altura máxima Avión de Pasajeros (Belly)
    "CARGO_STD_H": 96,     # Altura estándar Avión Carguero (A330F)
    "CARGO_MAX_H": 118,    # Altura máxima permitida (Main Deck High Contour)
    "ABSOLUTE_MAX": 125    # Límite físico absoluto por seguridad estructural
}

# Modelos de Datos Estrictos
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

# --- NAVEGACIÓN Y SERVICIO DE INTERFAZ ---
@app.get("/")
async def serve_app():
    """Sirve la aplicación 'AL CIELO' desde la raíz para evitar errores 404."""
    index_path = os.path.join('static', 'app.html')
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"detail": "Archivo app.html no encontrado en /static"})

# --- MOTOR DE ASESORÍA PROFESIONAL ---
@app.post("/precheck")
async def precheck(data: PreCheckRequest):
    instructions = []
    total_vol_kg = 0
    total_weight_kg = 0
    status = "READY"
    role_tag = f"[{data.user_role}]"
    
    # Procesamiento inteligente de cada grupo de piezas
    for i, p in enumerate(data.pieces):
        total_weight_kg += p.p
        
        # Cálculo IATA: (L x W x H) / 166 para libras -> convertido a factor KG (6000 cm3/kg o 166 in3/lb)
        # Aquí usamos el factor estándar de 166 para peso volumétrico en libras/pulgadas
        vol_lb = (p.l * p.w * p.h) / 166
        vol_kg = vol_lb * 0.453592  # Conversión precisa a KG para el reporte
        total_vol_kg += vol_kg
        
        # 1. Validación Maestra de Altura
        if p.h > LIMITS["ABSOLUTE_MAX"]:
            instructions.append(f"PIEZA #{i+1}: RECHAZO CRÍTICO. Altura de {p.h}in excede límites de seguridad.")
            status = "REJECT"
        elif p.h > LIMITS["CARGO_MAX_H"]:
            instructions.append(f"PIEZA #{i+1}: ALERTA. {p.h}in requiere posición central en Main Deck (Carguero).")
            status = "HOLD" if status != "REJECT" else "REJECT"
        elif p.h > LIMITS["PAX_MAX_H"]:
            instructions.append(f"PIEZA #{i+1}: SOLO CARGUERO. Altura {p.h}in no apta para aviones de pasajeros.")
        else:
            instructions.append(f"PIEZA #{i+1}: OK. Dimensiones aptas para PAX y Carguero.")

    # 2. Análisis de Integridad y Normativa (Madera/Daños)
    text_analysis = data.raw_text.upper()
    
    # Lógica de Madera ISPM15
    if any(x in text_analysis for x in ["MADERA", "WOOD", "PALLET"]):
        if not any(x in text_analysis for x in ["SELLO", "STAMP", "ISPM", "CERTIF"]):
            instructions.append("⚠️ ASESORÍA: Madera sin sello visible detectada.")
            instructions.append("💡 OPCIÓN A: Sustituir por Pallet de Plástico (Acceso inmediato).")
            instructions.append("💡 OPCIÓN B: Coordinar fumigación en zona primaria MIA.")
            if status == "READY": status = "HOLD"

    # Lógica de Daños (TSA Compliance)
    if any(x in text_analysis for x in ["ROTO", "MOJADO", "DAÑADO", "OPEN", "WET"]):
        instructions.append("❌ RECHAZO: Empaque vulnerado. No pasará inspección de seguridad (TSA).")
        status = "REJECT"

    # Cálculo final de Peso Cobrable (Max entre real y volumétrico)
    chargeable = round(max(total_weight_kg, total_vol_kg), 2)

    return {
        "status": status,
        "instructions": instructions,
        "chargeable_weight": f"{chargeable} KG",
        "advice": "Este reporte es una asesoría preventiva. Verifique con el manual DGR si la carga contiene químicos."
    }

# --- CONFIGURACIÓN DE ARCHIVOS ESTÁTICOS ---
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# --- ARRANQUE DEL SERVIDOR ---
if __name__ == "__main__":
    import uvicorn
    # Render utiliza la variable de entorno 'PORT'
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
