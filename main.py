from fastapi import FastAPI, Request
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

# --- DICCIONARIO MAESTRO AMPLIADO (REGLAS ESTRICTAS MIA) ---
PAPERWORK_DATABASE = {
    "GENERAL": [
        "1 AWB Original + 3 Copias",
        "1 Commercial Invoice Original + 2 Copias",
        "1 Packing List detallado",
        "1 Carta Responsabilidad Shipper (Firma Original)"
    ],
    "DGR": [
        "1 AWB Original + 4 Copias",
        "3 Shipper's Declaration (Borde Rojo Original)",
        "1 MSDS (Hoja de Seguridad)",
        "1 DG Checklist (Aceptación Aerolínea) -> SIN ESTO = REJECT AUTOMÁTICO"
    ],
    "PER": [
        "1 AWB Original + 3 Copias",
        "1 Certificado Fitosanitario / USDA (Original)",
        "1 Commercial Invoice + Packing List",
        "1 Temperature Log (Si aplica)"
    ],
    "PHR": [
        "1 AWB Original + 3 Copias",
        "1 Certificado de Calidad / Lote",
        "1 Temperature Declaration",
        "1 Invoice / Packing List"
    ],
    "HUM": [
        "1 AWB Original + 3 Copias",
        "1 Certificado de Defunción",
        "1 Embalming Certificate",
        "1 Funeral Home Letter / Autorización (MUY ESTRICTO)"
    ],
    "DRY": [
        "AWB con notación 'DRY ICE'",
        "Declaración IATA de CO2 Sólido",
        "Marcaje visible de KG de Hielo Seco en bulto",
        "MSDS (Si está asociado a DG o Pharma)"
    ]
}

class Piece(BaseModel):
    l: float
    w: float
    h: float
    p: float
    packaging: str  # boxes, drums, skips, metal, crates, engine, pallets

class PreCheckRequest(BaseModel):
    user_role: str  # SHIPPER, FORWARDER, TRUCKER, WAREHOUSE
    cargo_type: str
    uld_type: str
    pieces: List[Piece]
    raw_text: str

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/precheck")
async def precheck(data: PreCheckRequest):
    instructions = []
    total_vol = 0
    total_weight = 0
    reject = False
    
    # Bloqueo si no hay información
    if not data.pieces:
        return {"status": "ERROR", "instructions": ["NO HAY DATOS: Ingrese piezas para diagnóstico."]}

    # Auditoría por Rol (Soluciones Directas)
    role_prefix = f"[{data.user_role}] "
    
    for i, p in enumerate(data.pieces):
        total_weight += p.p
        vol = (p.l * p.w * p.h) / 166
        total_vol += vol
        
        # Validación de Altura por ULD
        if data.uld_type == "AKE" and p.h > 63:
            instructions.append(f"❌ {role_prefix}PIEZA #{i+1}: Altura {p.h}in excede AKE (LD3). RE-UBICAR EN PMC O CARGUERO.")
            reject = True
        elif p.h > 63:
            instructions.append(f"⚠️ {role_prefix}PIEZA #{i+1}: Altura {p.h}in incompatible con Belly. Solo Avión Carguero.")

        # Soluciones por tipo de embalaje
        if "WOOD" in p.packaging.upper() or "PALLET" in p.packaging.upper():
            text = data.raw_text.upper()
            if "SELLO" not in text and "ISPM" not in text:
                instructions.append(f"❌ {role_prefix}ORDEN: Llevar pallet a FUMIGAR o cambiar por PLÁSTICO. Sin sello no entra a Avianca.")
                reject = True

    # Análisis de Texto de Riesgos
    text = data.raw_text.upper()
    if any(x in text for x in ["ROTO", "DAÑADO", "MOJADO", "WET"]):
        instructions.append(f"❌ {role_prefix}RIESGO TSA: Empaque comprometido. RE-EMBALAR ANTES DE LLEGAR AL COUNTER.")
        reject = True

    # Respuesta de Asesoría Resolutiva
    return {
        "status": "READY" if not reject else "REJECT/HOLD",
        "instructions": instructions if instructions else ["Carga en cumplimiento. Proceder a pesaje y counter."],
        "chargeable_weight": round(max(total_weight, total_vol), 2),
        "required_docs": PAPERWORK_DATABASE.get(data.cargo_type, PAPERWORK_DATABASE["GENERAL"]),
        "uld_position": "LOWER DECK" if data.uld_type == "AKE" else "MAIN/LOWER DECK (PMC/PAG)"
    }

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
