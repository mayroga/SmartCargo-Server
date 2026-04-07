from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os

app = FastAPI()

# Modelo de datos para validación automática
class Piece(BaseModel):
    l: float
    w: float
    h: float
    kg: float

class CargoData(BaseModel):
    actor: str
    movement: str
    cargo_type: str
    aircraft: str
    consol: str
    packaging: str
    pieces: List[Piece]
    notes: Optional[str] = None

# =========================================================
# 🧠 ASESORÍA LOGÍSTICA (Lógica de Negocio)
# =========================================================

def process_cargo(data: CargoData):
    errors = []
    warnings = []
    score = 100
    
    # 1. Validación por Actor y Documentación
    if data.actor == "driver":
        warnings.append("CONDUCTOR: Presentar ID y Dock Token en counter.")
    
    if data.cargo_type == "dg":
        if data.aircraft == "pax":
            errors.append("RECHAZO: Mercancía Peligrosa prohibida en aviones de pasajeros.")
            score -= 60
        warnings.append("DG: Requiere Shipper's Declaration y MSDS original.")

    # 2. Embalaje y Estiba
    if data.packaging == "pallet_wd":
        warnings.append("MADERA: Verificar sello NIMF-15 (ISPM15).")
    elif data.packaging == "uld":
        warnings.append("ULD: Revisar base y paneles antes de aceptación.")

    # 3. Dimensiones por Aeronave
    total_weight = 0
    total_vol = 0
    # A330 PAX h=160cm | B767F h=244cm
    max_h = 160 if data.aircraft == "pax" else 244

    for p in data.pieces:
        total_weight += p.kg
        vol = (p.l * p.w * p.h) / 1000000
        total_vol += vol
        
        if p.h > max_h:
            errors.append(f"RECHAZO: Altura {p.h}cm excede el límite de {max_h}cm.")
            score -= 40
        if p.l > 317 or p.w > 244:
            errors.append("DIMENSIÓN: Excede base de pallet estándar (PMC).")
            score -= 30

    # Determinar Status
    if score >= 90 and not errors:
        status, level = "LISTO PARA COUNTER", "green"
    elif score >= 60:
        status, level = "REVISAR ANTES DE IR", "yellow"
    else:
        status, level = "NO APTO / RECHAZO", "red"

    return {
        "status": status,
        "level": level,
        "score": max(0, score),
        "errors": errors,
        "warnings": warnings,
        "total_weight": total_weight,
        "total_vol": round(total_vol, 3)
    }

# =========================================================
# 🌐 ENDPOINTS (Conexión Directa)
# =========================================================

@app.post("/api/check")
async def check_cargo(data: CargoData):
    return process_cargo(data)

# Montar carpeta static para servir el HTML y recursos
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
