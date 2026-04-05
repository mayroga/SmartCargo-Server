from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List
import os

app = FastAPI(title="AL CIELO - SmartCargo Advisory")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

LIMITS = {
    "PAX_MAX_H": 63,
    "CARGO_STD_H": 96,
    "CARGO_MAX_H": 118,
    "ABSOLUTE_MAX": 125
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

@app.get("/")
async def serve_app():
    index_path = os.path.join('static', 'app.html')
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"detail": "App no encontrada"})

@app.post("/precheck")
async def precheck(data: PreCheckRequest):
    instructions = []
    total_vol_kg = 0
    total_weight_kg = 0
    status = "READY"
    
    for i, p in enumerate(data.pieces):
        total_weight_kg += p.p
        vol_lb = (p.l * p.w * p.h) / 166
        vol_kg = vol_lb * 0.453592
        total_vol_kg += vol_kg
        
        # Validación de Altura
        if p.h > LIMITS["ABSOLUTE_MAX"]:
            instructions.append(f"PIEZA #{i+1}: RECHAZO. Altura {p.h}in excede límite físico.")
            status = "REJECT"
        elif p.h > LIMITS["PAX_MAX_H"]:
            instructions.append(f"PIEZA #{i+1}: SOLO CARGUERO. Altura {p.h}in excede límite PAX.")
            if status != "REJECT": status = "HOLD"
        else:
            instructions.append(f"PIEZA #{i+1}: OK para PAX/Carguero.")

    # Análisis de texto
    text = data.raw_text.upper()
    if any(x in text for x in ["MADERA", "WOOD", "PALLET"]):
        if not any(x in text for x in ["SELLO", "STAMP", "ISPM"]):
            instructions.append("⚠️ MADERA: Sin sello visible. Cambie a plástico o fumigue.")
            if status == "READY": status = "HOLD"

    if any(x in text for x in ["ROTO", "MOJADO", "DAÑADO", "WET"]):
        instructions.append("❌ DAÑO: Empaque inaceptable según TSA.")
        status = "REJECT"

    chargeable = round(max(total_weight_kg, total_vol_kg), 2)

    return {
        "status": status,
        "instructions": instructions,
        "chargeable_weight": f"{chargeable} KG",
        "advice": "Asesoría preventiva basada en normativas IATA/DOT."
    }

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
