from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List
import json
import os

app = FastAPI(title="SmartCargo Advisory MIA")

# ==========================================
# CONFIGURACIÓN DE COMUNICACIÓN (CORS)
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Carga de Reglas
def load_db():
    try:
        with open("static/avianca_rules.json", "r") as f: av = json.load(f)
        with open("static/cargo_rules.json", "r") as f: cg = json.load(f)
        return av, cg
    except: return {}, {}

AV_RULES, CG_RULES = load_db()

# Modelos de Datos
class CargoRequest(BaseModel):
    cargo_type: str
    weight_kg: float
    height_in: float
    uld_type: str
    dg: bool = False
    lithium: bool = False
    wood_packaging: bool = False
    raw_text: str = ""

# ==========================================
# ENDPOINTS
# ==========================================

# 1. Servir el Frontend
@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("static/app.html", "r", encoding="utf-8") as f:
        return f.read()

# 2. El Cerebro de Validación
@app.post("/precheck")
async def precheck(data: CargoRequest):
    instructions = []
    physical_errors = []
    risks = []
    
    # Lógica de Altura Avianca MIA
    if data.height_in > 63:
        instructions.append("⚠️ CARGA ALTA: Solo vuela en CARGUERO. Rectifica la reserva ahora.")
    
    # Lógica Aura Scan (Texto)
    text = data.raw_text.upper()
    if (data.wood_packaging or "MADERA" in text) and "SELLO" not in text:
        risks.append("USDA_WARNING")
        instructions.append("❌ MADERA SIN SELLO: ¡Para el camión! Cambia el pallet o no entrarás a la terminal.")

    if data.dg or data.cargo_type == "DGR":
        instructions.append("📋 DG CHECK: 3 copias de Shipper Declaration con bordes rojos.")

    # Decisión
    decision = "ACCEPTED" if not physical_errors and "USDA_WARNING" not in risks else "REJECTED"
    if data.height_in > 63 or data.dg: decision = "CONDITIONAL"

    return {
        "COUNTER_SIMULATION": {
            "required_documents": CG_RULES.get(data.cargo_type, {}).get("documents", ["AWB", "Invoice"]),
            "physical_errors": physical_errors,
            "risk_flags": risks
        },
        "FINAL_DECISION": decision,
        "COUNTER_INSTRUCTIONS": instructions if instructions else ["Todo listo. Pouch organizado."]
    }

# Montar carpeta static para archivos extra
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
