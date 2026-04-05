from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import json
import os

app = FastAPI(title="SmartCargo Advisory MIA")

# =========================
# CARGA DE REGLAS REALES
# =========================
def load_db():
    try:
        with open("static/avianca_rules.json", "r") as f:
            av = json.load(f)
        with open("static/cargo_rules.json", "r") as f:
            cg = json.load(f)
        return av, cg
    except:
        return {}, {}

AV_RULES, CG_RULES = load_db()

class CargoRequest(BaseModel):
    cargo_type: str
    weight_kg: float
    height_in: float
    uld_type: str
    dg: bool = False
    lithium: bool = False
    wood_packaging: bool = False
    raw_text: str = ""

@app.post("/precheck")
def precheck(data: CargoRequest):
    instructions = []
    physical_errors = []
    risks = []
    
    # 1. ANALISIS DE DOCUMENTACIÓN (Basado en tipo)
    required_docs = CG_RULES.get(data.cargo_type, {}).get("documents", ["air_waybill", "commercial_invoice", "packing_list"])
    
    # 2. ANALISIS FISICO (Real de Avianca)
    limits = AV_RULES.get("aircraft_limits", {"max_height_belly_in": 63, "max_height_freighter_in": 118})
    
    if data.height_in > limits["max_height_freighter_in"]:
        physical_errors.append("ALTURA EXCEDE LIMITE MAXIMO AERONAVE")
        instructions.append("RE-ESTIBAR AHORA: La carga no entra ni en carguero. Reduce la altura de los bultos.")
    elif data.height_in > limits["max_height_belly_in"]:
        instructions.append("CAMBIO DE EQUIPO: Asegúrate que la reserva sea en CARGUERO. En PAX (Belly) será rechazada.")

    # 3. ANALISIS DE RIESGO AURA SCAN (Vida Real en MIA)
    text = data.raw_text.upper()
    
    if data.wood_packaging or "MADERA" in text:
        if "SELLO" not in text and "ISPM" not in text:
            risks.append("USDA_NON_COMPLIANCE")
            instructions.append("ACCION: Busca el sello ISPM15. Si no está, llama a un proveedor de pallets en MIA para cambio urgente.")

    if data.dg or "DG" in text or data.cargo_type == "DGR":
        risks.append("DANGEROUS_GOODS")
        instructions.append("DOCS: Verifica que la Shipper Declaration tenga las 3 copias con bordes rojos originales.")

    if data.lithium:
        instructions.append("ETIQUETADO: Verifica que la etiqueta UN3480/3481 sea visible y no esté tapada por el film.")

    # 4. DECISION FINAL
    decision = "ACCEPTED"
    if physical_errors or "USDA_NON_COMPLIANCE" in risks:
        decision = "REJECTED"
    elif risks or data.height_in > 63:
        decision = "CONDITIONAL"

    return {
        "COUNTER_SIMULATION": {
            "required_documents": required_docs,
            "physical_errors": physical_errors,
            "risk_flags": risks
        },
        "FINAL_DECISION": decision,
        "COUNTER_INSTRUCTIONS": instructions if instructions else ["Todo en orden. Procede al counter con el sobre organizado."]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
