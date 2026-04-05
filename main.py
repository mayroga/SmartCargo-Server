from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict

import json

app = FastAPI(title="Counter Pre-Acceptance System")

# =========================
# LOAD RULES (NO MODULOS NUEVOS)
# =========================

with open("static/avianca_rules.json", "r") as f:
    AVIATION_RULES = json.load(f)

with open("static/cargo_rules.json", "r") as f:
    CARGO_RULES = json.load(f)


# =========================
# INPUT MODEL (COUNTER FORM)
# =========================

class CargoRequest(BaseModel):
    cargo_type: str
    documents: List[str]
    weight_kg: float
    height_in: float
    uld_type: str

    dg: bool = False
    lithium: bool = False
    perishable: bool = False
    human_remains: bool = False
    high_value: bool = False


# =========================
# CORE COUNTER LOGIC
# =========================

def document_check(cargo_type, docs):
    required = CARGO_RULES.get(cargo_type, {}).get("documents", [])
    missing = [d for d in required if d not in docs]

    return missing, required


def physical_check(weight, height, uld_type):
    limits = AVIATION_RULES["aircraft_limits"]
    uld = AVIATION_RULES["uld_types"].get(uld_type, {})

    errors = []

    if height > limits["max_height_freighter_in"]:
        errors.append("ALTURA EXCEDE LIMITE AVIACION")

    if weight > limits["max_piece_weight_kg"]:
        errors.append("PESO EXCEDE LIMITE AVIACION")

    if uld and weight > uld.get("max_weight_kg", 0):
        errors.append("EXCEDE LIMITE ULD")

    return errors


def risk_engine(data):
    risks = []

    if data.dg:
        risks.append("DANGEROUS_GOODS")

    if data.lithium:
        risks.append("LITHIUM_BATTERY")

    if data.perishable:
        risks.append("PERISHABLE")

    if data.human_remains:
        risks.append("HUMAN_REMAINS")

    if data.high_value:
        risks.append("HIGH_VALUE")

    return risks


# =========================
# DECISION ENGINE (LO QUE REALMENTE IMPORTA)
# =========================

def decision(missing_docs, physical_errors, risks):

    if len(missing_docs) == 0 and len(physical_errors) == 0:
        return "ACCEPTED"

    if "DANGEROUS_GOODS" in risks and len(missing_docs) == 0:
        return "CONDITIONAL"

    return "REJECTED"


def action_plan(missing_docs, physical_errors, risks):

    actions = []

    for d in missing_docs:
        actions.append(f"FALTANTE DOCUMENTO: {d} → ENTREGAR ANTES DE LLEGAR A COUNTER")

    for e in physical_errors:
        actions.append(f"ERROR FISICO: {e} → REETIQUETAR O REACOMODAR")

    if "DANGEROUS_GOODS" in risks:
        actions.append("DG DETECTADO → REVISAR SHIPPER DECLARATION IATA")

    if "LITHIUM_BATTERY" in risks:
        actions.append("LITHIUM → VERIFICAR SECCION IATA IA/IB/II")

    return actions


# =========================
# MAIN ENDPOINT (COUNTER SIMULATOR)
# =========================

@app.post("/precheck")
def precheck(data: CargoRequest):

    missing_docs, required = document_check(data.cargo_type, data.documents)
    physical_errors = physical_check(data.weight_kg, data.height_in, data.uld_type)
    risks = risk_engine(data)

    final_decision = decision(missing_docs, physical_errors, risks)

    return {
        "COUNTER_SIMULATION": {
            "required_documents": required,
            "missing_documents": missing_docs,
            "physical_errors": physical_errors,
            "risk_flags": risks
        },

        "FINAL_DECISION": final_decision,

        "COUNTER_INSTRUCTIONS": action_plan(
            missing_docs,
            physical_errors,
            risks
        )
    }
