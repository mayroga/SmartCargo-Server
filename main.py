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

class Piece(BaseModel):
    l: float
    w: float
    h: float
    p: float
    qty: int
    packaging: str
    unit: str  # "IN" o "CM"

class PreCheckRequest(BaseModel):
    user_role: str
    cargo_type: str
    pieces: List[Piece]
    raw_text: str
    destination: str

@app.post("/precheck")
async def precheck(data: PreCheckRequest):
    instructions = []
    reject = False
    max_h_in = 0
    total_actual_kg = 0
    total_vol_kg = 0

    # Diccionario de Autoridad: Glosario Legal
    glossary = {
        "IATA": "Asociación Internacional de Transporte Aéreo (Dicta reglas globales).",
        "TSA": "Administración de Seguridad en el Transporte (Obligatorio en USA).",
        "CBP": "Aduanas y Protección Fronteriza (Control de madera y contrabando).",
        "ISPM15": "Norma Internacional de Medidas Fitosanitarias para Madera.",
        "DGR": "Mercancías Peligrosas (Requiere certificación técnica).",
        "AWB": "Guía Aérea (Contrato de transporte)."
    }

    # 1. Lógica Documental Específica por Tipo de Carga
    doc_map = {
        "GENERAL": ["AWB Original", "Commercial Invoice (FOB)", "Packing List"],
        "DGR": ["Shipper's Declaration (Borde Rojo)", "MSDS (Hoja de Seguridad)", "AWB con frases de manejo"],
        "PER": ["Certificado Fitosanitario", "Factura con tiempo de vida útil"],
        "PHR": ["Termógrafo (Data Logger)", "Protocolo de temperatura"],
        "HUMANS": ["Certificado de Defunción", "Permiso de Tránsito Funerario", "Embalaje Hermético"],
        "LIVE_ANIMALS": ["Certificado Veterinario de Salud", "IATA Live Animals Checklist", "Permiso de Importación"],
        "DRY_ICE": ["Declaración de cantidad neta", "Etiquetas Clase 9", "Marcado de UN1845"]
    }
    
    required_docs = doc_map.get(data.cargo_type, ["AWB Original"])
    required_docs.extend(["Carta de Responsabilidad TSA", "ID del Driver"])

    # 2. Auditoría de Piezas (Conversión y Medidas)
    for i, p in enumerate(data.pieces):
        # Convertir a Pulgadas para lógica de avión si viene en CM
        l_in = p.l if p.unit == "IN" else p.l / 2.54
        w_in = p.w if p.unit == "IN" else p.w / 2.54
        h_in = p.h if p.unit == "IN" else p.h / 2.54
        
        if h_in > max_h_in: max_h_in = h_in

        # Cálculo de Pesos
        p_weight = p.p * p.qty
        p_vol = (l_in * w_in * h_in * p.qty) / 166
        total_actual_kg += p_weight
        total_vol_kg += p_vol

        # Validaciones de Embalaje con Autoridad
        if p.packaging == "BOX" and p.p > 68:
            instructions.append(f"❌ ERROR PIEZA #{i+1}: Caja de {p.p}kg excede límite de manejo manual. ACCIÓN: Debe paletizar para evitar rechazo en counter.")
            reject = True
        
        if p.packaging == "DRUM" and data.cargo_type != "DGR":
             instructions.append(f"⚠️ PIEZA #{i+1} (TAMBOR): Verificar que no contenga líquidos prohibidos o corrosivos según IATA.")

    # 3. AURA SCAN (Análisis de Texto y Riesgos)
    text = data.raw_text.upper()
    if any(word in text for word in ["ROTO", "DAÑADO", "MOJADO", "HOYO", "WET"]):
        instructions.append("❌ RECHAZO SEGURIDAD (TSA): Daño físico detectado. SOLUCIÓN: Re-embalar. Ninguna carga con acceso al interior será aceptada.")
        reject = True
    
    if any(p.packaging in ["PALLET_WD", "CRATE"] for p in data.pieces):
        if "SELLO" not in text and "ISPM" not in text:
            instructions.append("🛑 ALERTA CBP: Madera sin sello ISPM15 visible. SOLUCIÓN: El Trucker debe verificar sello físico o llevar a estación de fumigación en MIA antes de Avianca.")

    # 4. Tabla de Aeronaves
    fleet = [
        {"model": "A330-200F", "deck": "Main Deck", "max_h": 96},
        {"model": "A330-200F", "deck": "High Position", "max_h": 118},
        {"model": "A330/A321", "deck": "Belly (Pasajeros)", "max_h": 63}
    ]
    
    compatibility = []
    for air in fleet:
        status = "OK" if max_h_in <= air["max_h"] else "NO CABE"
        compatibility.append({
            "model": air["model"],
            "deck": air["deck"],
            "status": status,
            "limit_h": air["max_h"],
            "reason": "Dentro del contorno" if status == "OK" else f"Excede por {round(max_h_in - air['max_h'], 1)}in"
        })

    chargeable = max(total_actual_kg, total_vol_kg)

    return {
        "status": "REJECT" if reject else "READY",
        "instructions": instructions,
        "required_docs": required_docs,
        "chargeable_weight": round(chargeable, 2),
        "aircraft_compatibility": compatibility,
        "glossary": glossary
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
