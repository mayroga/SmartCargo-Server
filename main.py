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
    unit: str # "IN" o "CM"

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
    total_kg = 0
    
    # Glosario Técnico para el reporte
    glossary = {
        "ISPM15": "Sello internacional que certifica que la madera está libre de plagas (Exigido por CBP).",
        "TSA": "Administración de Seguridad en el Transporte. Exige que la carga no sea manipulable.",
        "HUM": "Human Remains (Restos Humanos). Carga de prioridad máxima con protocolos de dignidad.",
        "AVI": "Live Animals (Animales Vivos). Requiere ventilación y checklist de bienestar.",
        "DGD": "Shipper's Declaration for Dangerous Goods. Documento legal para químicos/baterías."
    }

    # 1. PROCESAMIENTO DE PIEZAS Y MEDIDAS (Conversión Dinámica)
    for i, p in enumerate(data.pieces):
        # Convertir todo a pulgadas para la validación de aviones
        h_in = p.h if p.unit == "IN" else p.h / 2.54
        if h_in > max_h_in: max_h_in = h_in
        total_kg += (p.p * p.qty)

        # Validación de Embalaje por tipo
        if p.packaging == "DRUM":
            instructions.append(f"📦 PIEZA #{i+1} (TAMBOR): Debe viajar sobre estiba y asegurado con flejes metálicos. No se acepta plástico (shrink wrap) como único soporte.")
        if p.packaging == "BOX" and h_in > 45:
            instructions.append(f"❌ ERROR PIEZA #{i+1}: Caja de cartón muy alta ({round(h_in,1)}in). Riesgo de colapso. ACCIÓN: Re-embalar en CRATE (Huacal) de madera.")
            reject = True

    # 2. LÓGICA ESPECÍFICA POR TIPO DE CARGA
    if data.cargo_type == "HUM":
        instructions.append("⚱️ PROTOCOLO HUM: Verificar certificado de defunción y embalsamamiento. La caja debe estar sellada herméticamente y dentro de un outer packaging discreto.")
    elif data.cargo_type == "AVI":
        instructions.append("🐾 PROTOCOLO AVI: El contenedor debe tener ventilación en los 4 lados y recipientes para agua/comida accesibles desde fuera.")
    elif data.cargo_type == "DGR_ICE":
        instructions.append("❄️ DRY ICE: Verificar que el embalaje permita la salida del gas (CO2). Si excede 2.5kg por bulto, requiere declaración de DGR.")

    # 3. AURA SCAN (Análisis de Fallas)
    text = data.raw_text.upper()
    if any(word in text for word in ["ROTO", "MOJADO", "DAÑADO", "HOYO"]):
        instructions.append("❌ RECHAZO TSA: Daño físico detectado. SOLUCIÓN: El almacén debe parchar o re-embalar antes de que el camión salga hacia Avianca.")
        reject = True
    if "SELLO" not in text and any(p.packaging in ["PALLET_WD", "CRATE"] for p in data.pieces):
        instructions.append("❌ FALLA CBP: No se menciona sello ISPM15 en madera. SOLUCIÓN: Llevar a fumigación inmediata en MIA Station.")
        reject = True

    # 4. COMPATIBILIDAD DE AVIONES (Lógica Avianca MIA)
    fleet = [
        {"model": "A330-200F", "deck": "Main Deck", "limit": 96},
        {"model": "A330-200F", "deck": "High Position", "limit": 118},
        {"model": "A330/A321", "deck": "Belly (Pax)", "limit": 63}
    ]
    
    aircraft_results = []
    for a in fleet:
        ok = max_h_in <= a["limit"]
        aircraft_results.append({
            "model": a["model"], "deck": a["deck"], "limit_h": a["limit"],
            "status": "OK" if ok else "NO CABE",
            "reason": "Altura permitida" if ok else f"Excede límite de {a['limit']}in"
        })

    return {
        "status": "REJECT" if reject else "READY",
        "instructions": instructions,
        "aircraft_compatibility": aircraft_results,
        "chargeable_weight": round(total_kg, 2),
        "glossary": glossary
    }

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html", "r", encoding="utf-8") as f: return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
