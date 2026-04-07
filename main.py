from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os

app = FastAPI()

# =========================================================
# 🧠 LÓGICA DE SEGMENTACIÓN (TU SOLICITUD)
# =========================================================

@app.post("/precheck")
async def precheck(request: Request):
    data = await request.json()
    
    # Extraemos lo que envía tu HTML
    raw_text = data.get("raw_text", "").lower()
    pieces = data.get("pieces", [])
    destination = data.get("destination", "")
    
    # Variables de respuesta
    errors = []
    warnings = []
    required_docs = ["Air Waybill (AWB)", "Consol Manifest (si aplica)"]
    status = "READY"
    driver_message = "Carga verificada para entrega en counter."

    # 1. Segmentación por Tipo de Carga
    cargo_type = "GENERAL CARGO"
    if "dg" in raw_text or "dangerous" in raw_text or "peligrosa" in raw_text:
        cargo_type = "DANGEROUS GOODS (DG)"
        errors.append("Falta Shipper's Declaration para DG.")
        required_docs.append("MSDS (Hoja de Seguridad)")
        status = "REJECT"
    
    if "per" in raw_text or "fresco" in raw_text:
        cargo_type = "PERISHABLE (PER)"
        warnings.append("Carga perecedera: Prioridad de cadena de frío.")
        required_docs.append("Certificado Fitosanitario (si aplica)")

    # 2. Segmentación por Embalaje
    if "madera" in raw_text or "wood" in raw_text:
        warnings.append("Embalaje de madera detectado: Verificar sello NIMF-15.")

    # 3. Validación de Dimensiones (Lógica Avianca)
    total_kg = 0
    for p in pieces:
        total_kg += p.get("kg", 0)
        h = p.get("h", 0)
        if h > 160: # Límite estándar PAX
            warnings.append(f"Pieza con altura {h}cm requiere avión Cargo Only (CAO).")
            status = "RISK"

    return {
        "status": status,
        "driver_message": driver_message,
        "cargo_type_detected": cargo_type,
        "errors": errors,
        "warnings": warnings,
        "fixes": ["Ajustar declaración de peso" if total_kg == 0 else "Ninguna necesaria"],
        "required_docs": required_docs
    }

# =========================================================
# 🌐 SERVIDOR DE ARCHIVOS
# =========================================================

# Esto hace que cuando entres a la URL, vea tu carpeta 'static'
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
