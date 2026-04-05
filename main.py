from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# -----------------------------
# MODELO DE DATOS
# -----------------------------
class DocumentCheck(BaseModel):
    awb: bool
    invoice: bool
    packing_list: bool
    house_awb: Optional[bool] = False
    itn: Optional[bool] = False
    sli: Optional[bool] = False
    clean_order: bool
    readable: bool
    no_damage: bool
    weight_match: bool
    pieces_match: bool

# -----------------------------
# MOTOR DE VALIDACIÓN (CORE)
# -----------------------------
def evaluate(doc: DocumentCheck):

    errors = []
    warnings = []

    # 🔴 CORTINA 1: ORDEN FÍSICO
    if not doc.awb:
        errors.append("FALTA MASTER AWB (CRÍTICO)")
    if not doc.invoice:
        errors.append("FALTA COMMERCIAL INVOICE")
    if not doc.packing_list:
        errors.append("FALTA PACKING LIST")
    if not doc.clean_order:
        errors.append("ORDEN FÍSICO INCORRECTO EN SOBRE")

    # 🔴 CORTINA 2: CALIDAD DOCUMENTAL
    if not doc.readable:
        errors.append("DOCUMENTOS NO LEGIBLES")
    if not doc.no_damage:
        errors.append("DOCUMENTOS DAÑADOS O SUCIOS")

    # 🔴 CORTINA 3: COHERENCIA OPERATIVA
    if not doc.weight_match:
        errors.append("DISCREPANCIA DE PESO (AWB vs REAL)")
    if not doc.pieces_match:
        errors.append("DISCREPANCIA DE PIEZAS")

    # 🔴 CORTINA 4: SEGURIDAD / LEGAL
    if not doc.itn:
        warnings.append("ITN NO CONFIRMADO (SI APLICA)")

    # DECISIÓN FINAL
    if len(errors) > 0:
        status = "RECHAZO / HOLD"
    elif len(warnings) > 0:
        status = "REVISIÓN MANUAL"
    else:
        status = "APROBADO PARA COUNTER"

    return {
        "status": status,
        "errors": errors,
        "warnings": warnings
    }

# -----------------------------
# ENDPOINT PRINCIPAL
# -----------------------------
@app.post("/check")
def check_document(doc: DocumentCheck):
    return evaluate(doc)
