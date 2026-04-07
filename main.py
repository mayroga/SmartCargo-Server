from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()

# =========================================================
# 🧠 MOTOR DE CLASIFICACIÓN DE CARGA
# =========================================================

def classify_cargo(raw_text):
    text = raw_text.lower()

    if any(x in text for x in ["dg", "dangerous", "peligrosa", "un ", "hazard"]):
        return "DANGEROUS GOODS"

    if any(x in text for x in ["pharma", "medicamento", "vacuna"]):
        return "PHARMA"

    if any(x in text for x in ["animal", "live animal", "avi"]):
        return "LIVE ANIMALS"

    if any(x in text for x in ["human remains", "cenizas", "cadaver"]):
        return "HUMAN REMAINS"

    if any(x in text for x in ["dry ice", "hielo seco", "un1845"]):
        return "DRY ICE"

    if any(x in text for x in ["perecedero", "perishable", "fresco"]):
        return "PERISHABLE"

    if any(x in text for x in ["consol", "consolidado"]):
        return "CONSOLIDATED"

    if any(x in text for x in ["transfer", "tránsito"]):
        return "TRANSFER"

    if any(x in text for x in ["comat"]):
        return "COMAT"

    return "GENERAL CARGO"


# =========================================================
# 📋 REGLAS POR TIPO DE CARGA
# =========================================================

def apply_rules(cargo_type, raw_text, pieces):
    errors = []
    warnings = []
    fixes = []
    docs = ["Air Waybill (AWB)"]

    # ================= DG =================
    if cargo_type == "DANGEROUS GOODS":
        docs += ["Shipper Declaration (3 originales)", "MSDS", "DG Checklist"]
        errors.append("Carga DG requiere Shipper Declaration firmada.")
        warnings.append("Verificar número UN, clase y etiquetas.")
        fixes.append("Generar Shipper Declaration con formato válido.")
        return errors, warnings, fixes, docs, "REJECT"

    # ================= PHARMA =================
    if cargo_type == "PHARMA":
        docs += ["Factura Comercial", "Certificado de Temperatura"]
        warnings.append("Requiere control estricto de temperatura.")
        fixes.append("Confirmar rango de temperatura y embalaje térmico.")
        return errors, warnings, fixes, docs, "RISK"

    # ================= LIVE ANIMALS =================
    if cargo_type == "LIVE ANIMALS":
        docs += ["Certificado Veterinario", "Permiso de Importación"]
        errors.append("Debe cumplir regulaciones de transporte animal.")
        warnings.append("Verificar ventilación y contenedor aprobado.")
        fixes.append("Usar contenedor certificado IATA Live Animals.")
        return errors, warnings, fixes, docs, "REJECT"

    # ================= HUMAN REMAINS =================
    if cargo_type == "HUMAN REMAINS":
        docs += ["Certificado de Defunción", "Permiso Sanitario"]
        warnings.append("Manejo especial y prioridad.")
        fixes.append("Verificar embalaje hermético y documentación legal.")
        return errors, warnings, fixes, docs, "RISK"

    # ================= DRY ICE =================
    if cargo_type == "DRY ICE":
        docs += ["Declaración de Hielo Seco"]
        warnings.append("Dry Ice genera CO2, verificar ventilación.")
        fixes.append("Declarar peso exacto de hielo seco.")
        return errors, warnings, fixes, docs, "RISK"

    # ================= PERISHABLE =================
    if cargo_type == "PERISHABLE":
        docs += ["Certificado Fitosanitario"]
        warnings.append("Cadena de frío requerida.")
        fixes.append("Confirmar tiempo de tránsito y temperatura.")
        return errors, warnings, fixes, docs, "RISK"

    # ================= CONSOL =================
    if cargo_type == "CONSOLIDATED":
        docs += ["Master AWB", "House AWB", "Manifest"]
        warnings.append("Carga consolidada requiere desglose completo.")
        fixes.append("Validar consistencia entre MAWB y HAWB.")
        return errors, warnings, fixes, docs, "RISK"

    # ================= TRANSFER =================
    if cargo_type == "TRANSFER":
        docs += ["Documentos de tránsito"]
        warnings.append("Carga en conexión, verificar tiempos.")
        fixes.append("Confirmar conexión y manejo interlineal.")
        return errors, warnings, fixes, docs, "RISK"

    # ================= COMAT =================
    if cargo_type == "COMAT":
        docs += ["Documentación interna aerolínea"]
        warnings.append("Material de aerolínea, manejo especial.")
        fixes.append("Confirmar autorización interna.")
        return errors, warnings, fixes, docs, "RISK"

    # ================= GENERAL =================
    docs += ["Factura Comercial"]
    fixes.append("Carga general sin restricciones especiales.")
    return errors, warnings, fixes, docs, "READY"


# =========================================================
# ⚖️ VALIDACIÓN DE PIEZAS Y DIMENSIONES
# =========================================================

def validate_pieces(pieces):
    warnings = []
    total_weight = 0

    for i, p in enumerate(pieces):
        kg = p.get("kg", 0)
        h = p.get("h", 0)

        total_weight += kg

        if h > 160:
            warnings.append(f"Pieza {i+1} supera 160cm: requiere avión carguero.")

        if kg == 0:
            warnings.append(f"Pieza {i+1} sin peso declarado.")

    return warnings, total_weight


# =========================================================
# 🚀 ENDPOINT PRINCIPAL
# =========================================================

@app.post("/precheck")
async def precheck(request: Request):
    data = await request.json()

    raw_text = data.get("raw_text", "")
    pieces = data.get("pieces", [])

    cargo_type = classify_cargo(raw_text)

    errors, warnings, fixes, docs, status = apply_rules(
        cargo_type, raw_text, pieces
    )

    piece_warnings, total_weight = validate_pieces(pieces)
    warnings.extend(piece_warnings)

    # Ajuste final de estado
    if errors:
        status = "REJECT"
    elif warnings and status != "REJECT":
        status = "RISK"

    driver_message = "Carga lista para counter."
    if status == "REJECT":
        driver_message = "No ir al counter. Corregir errores."
    elif status == "RISK":
        driver_message = "Puede ir con riesgo de observación."

    return {
        "status": status,
        "driver_message": driver_message,
        "cargo_type_detected": cargo_type,
        "errors": errors,
        "warnings": warnings,
        "fixes": fixes,
        "required_docs": docs,
        "total_weight": total_weight
    }


# =========================================================
# 🌐 STATIC FILES
# =========================================================

if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")


# =========================================================
# ▶️ RUN
# =========================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
