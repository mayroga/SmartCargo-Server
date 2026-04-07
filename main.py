from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os

app = FastAPI()

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
    packaging: str
    pieces: List[Piece]
    notes: Optional[str] = None

# =========================================================
# 🧠 ASESORÍA LOGÍSTICA SEGMENTADA (IATA / TSA / AVIANCA)
# =========================================================

def process_cargo(data: CargoData):
    errors = []
    warnings = []
    score = 100
    
    # 1. SEGMENTACIÓN POR ACTOR (Responsabilidad Legal)
    if data.actor == "driver":
        warnings.append("CONDUCTOR: Presentar ID físico, Dock Token y asegurar que el vehículo cumple con sellos TSA.")
    elif data.actor == "forwarder":
        warnings.append("FORWARDER: Validar coincidencia de MAWB/HAWB y estatus de Known Shipper.")

    # 2. SEGMENTACIÓN POR TIPO DE CARGA (Flujos Específicos)
    if data.cargo_type == "dg":
        score -= 50
        errors.append("DG: Requiere Shipper's Declaration original (3 copias) y MSDS.")
        if data.aircraft == "pax":
            errors.append("RECHAZO CRÍTICO: Mercancía Peligrosa prohibida en aviones de pasajeros.")
            score = 0
    
    elif data.cargo_type == "per":
        warnings.append("PERISHABLE: Prioridad en cadena de frío. Verifique tiempo de conexión en MIA.")
    
    elif data.cargo_type == "avi":
        errors.append("ANIMAL VIVO: Requiere LAR (IATA) y validación de kennel/contenedor.")
        score -= 20

    # 3. SEGMENTACIÓN POR EMBALAJE (Seguridad y Estiba)
    if data.packaging == "pallet_wd":
        warnings.append("MADERA: Sello ISPM15/NIMF15 obligatorio. Si hay daño estructural, habrá rechazo.")
    elif data.packaging == "metal":
        warnings.append("METAL: Verifique puntos de amarre y protección para no dañar el ULD/Piso del avión.")
    elif data.packaging == "uld":
        warnings.append("ULD: Comprobar red (Net) y base. No se acepta si tiene abolladuras en la base.")

    # 4. SEGMENTACIÓN POR AERONAVE (Medidas y Capacidades)
    total_weight = 0
    total_vol = 0
    # Límites de altura: PAX (A330/321) = 160cm | CARGO (767F) = 244cm
    max_h = 160 if data.aircraft == "pax" else 244

    for p in data.pieces:
        total_weight += p.kg
        vol = (p.l * p.w * p.h) / 1000000
        total_vol += vol
        
        if p.h > max_h:
            errors.append(f"RECHAZO MEDIDA: Altura {p.h}cm excede el límite de {max_h}cm para avión {data.aircraft.upper()}.")
            score -= 40
        if p.l > 317 or p.w > 244:
            errors.append("RECHAZO DIMENSIÓN: Supera la base del pallet estándar PMC.")
            score -= 30

    # 5. SEGMENTACIÓN POR FLUJO (Local vs Transfer vs COMAT)
    if data.movement == "transfer":
        warnings.append("TRANSFER: El manifiesto de transferencia debe estar sellado por Aduana/CBP.")
    elif data.movement == "comat":
        warnings.append("COMAT: Material de compañía requiere guía interna autorizada.")

    # DETERMINACIÓN DE ESTATUS FINAL
    if score >= 90 and not errors:
        status, level = "LISTO PARA COUNTER", "green"
    elif score >= 50:
        status, level = "REVISAR ACCIONES", "yellow"
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
# 🌐 CONEXIÓN Y SERVIDORES
# =========================================================

@app.post("/api/check")
async def check_cargo(data: CargoData):
    return process_cargo(data)

if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
