from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os

app = FastAPI(title="Aura SmartCargo MIA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Diccionario Maestro de Papelería (Cantidades Reales MIA)
PAPERWORK_DATABASE = {
    "GENERAL": [
        "1 AWB Original (Azul/Verde) + 3 Copias",
        "1 Commercial Invoice Original + 2 Copias",
        "1 Packing List Detallado",
        "1 Carta de Responsabilidad (Firma Original)"
    ],
    "DGR": [
        "1 AWB Original + 4 Copias",
        "3 Shipper's Declaration (Bordes Rojos Originales)",
        "1 MSDS (Hoja de Seguridad)",
        "1 Checklist de Aceptación DG"
    ],
    "PER": [
        "1 AWB Original + 3 Copias",
        "1 Certificado Fitosanitario (USDA/ICA/SENASA) Original",
        "1 Factura Comercial con Incoterms",
        "1 Registro de Temperatura (Si aplica)"
    ],
    "PHR": [
        "1 AWB Original + 3 Copias",
        "1 Certificado de Calidad / Lote",
        "1 Declaración de Control de Temperatura"
    ],
    "BAT": [
        "1 AWB Original + 3 Copias",
        "1 Lithium Battery Declaration",
        "1 Test Summary UN38.3"
    ]
}

class Piece(BaseModel):
    l: float
    w: float
    h: float
    p: float

class PreCheckRequest(BaseModel):
    cargo_type: str
    uld_type: str
    pieces: List[Piece]
    raw_text: str

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/get_docs")
async def get_docs(data: dict):
    tipo = data.get("type", "GENERAL")
    return {"docs": PAPERWORK_DATABASE.get(tipo, PAPERWORK_DATABASE["GENERAL"])}

@app.post("/precheck")
async def precheck(data: PreCheckRequest):
    instructions = []
    total_vol = 0
    total_weight = 0
    
    for p in data.pieces:
        total_weight += p.p
        vol = (p.l * p.w * p.h) / 166
        total_vol += vol
        if p.h > 63:
            instructions.append(f"⚠️ PIEZA ALTA ({p.h} in): No entra en Belly. Exigir Carguero.")

    text = data.raw_text.upper()
    if "MADERA" in text and "SELLO" not in text:
        instructions.append("❌ RECHAZO USDA: Sin sello ISPM15 en madera. Cambiar pallet.")

    return {
        "status": "READY" if not instructions else "HOLD",
        "instructions": instructions,
        "chargeable_weight": round(max(total_weight, total_vol), 2)
    }

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
