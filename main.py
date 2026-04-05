from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os

app = FastAPI(title="AL CIELO - SmartCargo Advisory MIA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELOS DE DATOS ---
class Piece(BaseModel):
    l: float
    w: float
    h: float
    p: float
    qty: int
    packaging: str # PALLET_WD, PALLET_PL, BOX, CRATE, DRUM, SKID

class PreCheckRequest(BaseModel):
    user_role: str
    cargo_type: str
    target_aircraft: str
    pieces: List[Piece]
    raw_text: str
    destination: str

# --- ASESORÍA TÉCNICA CON LÓGICA DE RESOLUCIÓN ---
@app.post("/precheck")
async def precheck(data: PreCheckRequest):
    instructions = []
    reject = False
    max_h_found = 0
    total_actual_weight = 0
    total_vol_weight = 0

    # Diccionario de definiciones para los "no expertos"
    definitions = {
        "ISPM15": "Norma Internacional para Medidas Fitosanitarias (Sello de fumigación en madera).",
        "TSA": "Administración de Seguridad en el Transporte (Gobierno USA).",
        "IATA": "Asociación Internacional de Transporte Aéreo.",
        "CBP": "Aduanas y Protección Fronteriza de los Estados Unidos."
    }

    # 1. Auditoría de Piezas y Embalaje
    for i, p in enumerate(data.pieces):
        p_weight = p.p * p.qty
        p_vol = (p.l * p.w * p.h * p.qty) / 166
        total_actual_weight += p_weight
        total_vol_weight += p_vol
        if p.h > max_h_found: max_h_found = p.h

        # Lógica por tipo de embalaje (Reglas TSA/IATA)
        if p.packaging == "DRUM" and p.p > 250:
            instructions.append(f"⚠️ PIEZA #{i+1} (TAMBOR): Peso elevado detectado. SOLUCIÓN: Asegurar que estén sobre pallets y con flejes metálicos para evitar movimiento en el avión.")
        
        if p.packaging == "BOX" and p.h > 40:
            instructions.append(f"⚠️ PIEZA #{i+1} (CAJAS): Altura inestable para cajas sueltas. SOLUCIÓN: Recomiendo paletizar y usar 'Shrink Wrap' (plástico estirable) para dar estabilidad.")

    # 2. Alertas Críticas de Seguridad (Rojo) y AURA SCAN
    text_analysis = data.raw_text.upper()
    
    # Madera sin sello (CBP)
    if any(p.packaging in ["PALLET_WD", "CRATE"] for p in data.pieces):
        if "SELLO" not in text_analysis and "ISPM" not in text_analysis:
            instructions.append("❌ ERROR CBP (ADUANA): Madera sin sello ISPM15 detectada. ACCIÓN: No entregue así. Debe fumigar el pallet en MIA o cambiarlo por uno plástico antes del counter.")
            reject = True

    # Daños físicos (TSA)
    risk_keywords = ["ROTO", "MOJADO", "WET", "DAÑADO", "BROKEN", "HOYO", "FLEJE SUELTO"]
    if any(word in text_analysis for word in risk_keywords):
        instructions.append("❌ RECHAZO SEGURIDAD (TSA): Empaque comprometido. SOLUCIÓN: Re-embalar la pieza inmediatamente. Avianca no aceptará carga con acceso al interior o humedad.")
        reject = True

    # 3. Sugerencia Automática de Avión (Lógica Avianca)
    aircraft_compatibility = []
    fleet = [
        {"model": "A330-200F", "deck": "Main Deck (Carguero)", "max_h": 96, "desc": "Avión puro de carga, ideal para pallets estándar."},
        {"model": "A330-200F", "deck": "High Position (Centro)", "max_h": 118, "desc": "Solo para carga sobredimensionada en el centro del avión."},
        {"model": "A330/A321", "deck": "Belly (Pasajeros)", "max_h": 63, "desc": "Carga que viaja 'en la barriga' del avión de pasajeros."}
    ]

    for air in fleet:
        status = "OK" if max_h_found <= air["max_h"] else "NO CABE"
        aircraft_compatibility.append({
            "model": air["model"],
            "deck": air["deck"],
            "status": status,
            "limit_h": air["max_h"],
            "note": air["desc"]
        })

    # 4. Contexto por Rol
    role_tips = {
        "SHIPPER": "Su prioridad es que la factura y el valor FOB coincidan con el Packing List para evitar retenciones de dinero.",
        "FORWARDER": "Revise que el Shipper's Declaration no tenga tachaduras, es un documento legal sensible.",
        "TRUCKER": "Asegúrese de tener su ID vigente y la Carta de Responsabilidad a mano para no perder el turno.",
        "WAREHOUSE": "Verifique que las etiquetas de destino estén visibles en al menos dos caras del pallet."
    }
    instructions.append(f"💡 CONSEJO PARA {data.user_role}: {role_tips.get(data.user_role, '')}")

    chargeable_weight = max(total_actual_weight, total_vol_weight)

    return {
        "status": "REJECT" if reject else "READY",
        "instructions": instructions,
        "chargeable_weight": round(chargeable_weight, 2),
        "aircraft_compatibility": aircraft_compatibility,
        "user_role": data.user_role
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
