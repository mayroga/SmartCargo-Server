from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fpdf import FPDF
import os
import json
import datetime
import httpx

app = FastAPI(title="SMARTCARGO INFALIBLE")

# -------------------------
# Carpeta Frontend
# -------------------------
if not os.path.exists("frontend"):
    os.makedirs("frontend")

app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def root():
    index_path = os.path.join("frontend", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "index.html no encontrado"}

# -------------------------
# API Keys
# -------------------------
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# -------------------------
# Modelo de Carga
# -------------------------
class CargoForm(BaseModel):
    clientId: str | None = ""
    shipmentType: str | None = ""
    highValue: str | None = ""
    itnNumber: str | None = ""
    awbMaster: str | None = ""
    awbHouse: str | None = ""
    referenceNumber: str | None = ""
    originAirport: str | None = ""
    destinationAirport: str | None = ""
    departureDate: str | None = ""
    pieceHeight: float | None = 0
    pieceWeight: float | None = 0
    numPieces: int | None = 0
    totalWeight: float | None = 0
    dimensions: str | None = ""
    needsShoring: str | None = ""
    nimf15: str | None = ""
    overhang: str | None = ""
    damaged: str | None = ""
    cargoType: str | None = ""
    dgrDocs: str | None = ""
    fitoDocs: str | None = ""
    arrivalTime: str | None = ""
    packaging: str | None = ""
    labels: str | None = ""
    fragile: str | None = ""
    shipperName: str | None = ""
    shipperAddress: str | None = ""
    shipperPhone: str | None = ""
    consigneeName: str | None = ""
    consigneeAddress: str | None = ""
    consigneePhone: str | None = ""
    zipCode: str | None = ""

# -------------------------
# Evaluación Reglas (Modo Advertencia)
# -------------------------
def evaluar_reglas_duras(data: CargoForm):

    detalles = []
    errores_criticos = 0

    # Fase 1
    if not data.clientId:
        detalles.append("❌ ID de cliente vacío: Validación Known Shipper no posible.")
        errores_criticos += 1

    if data.highValue == "yes" and not data.itnNumber:
        detalles.append("❌ Valor > $2,500 USD sin ITN.")
        errores_criticos += 1

    if not data.awbMaster:
        detalles.append("❌ AWB Master no proporcionado.")
        errores_criticos += 1

    # Fase 2
    if data.pieceHeight and data.pieceHeight > 63:
        detalles.append("⚠️ Altura > 63 pulgadas. Solo avión carguero.")

    if data.totalWeight and data.totalWeight > 150 and data.needsShoring != "si":
        detalles.append("❌ Pieza >150kg sin shoring.")
        errores_criticos += 1

    if data.nimf15 != "si":
        detalles.append("❌ Pallet sin NIMF-15.")
        errores_criticos += 1

    if data.damaged == "yes":
        detalles.append("⚠️ Daños preexistentes detectados.")

    # Fase 3
    if data.cargoType in ["DGR", "PER", "BIO"]:
        if data.dgrDocs != "si":
            detalles.append(f"❌ {data.cargoType} sin documentación completa.")
            errores_criticos += 1

        if data.fitoDocs != "si" and data.cargoType in ["PER", "BIO"]:
            detalles.append(f"❌ {data.cargoType} sin certificado sanitario.")
            errores_criticos += 1

    # Fase Final
    if data.packaging not in ["straps", "STRAPS"]:
        detalles.append("❌ Embalaje insuficiente.")
        errores_criticos += 1

    if data.overhang == "yes":
        detalles.append("❌ Overhang detectado.")

    if not data.zipCode:
        detalles.append("❌ Código postal vacío.")
        errores_criticos += 1

    # Determinar estado sin bloquear
    if errores_criticos == 0 and len(detalles) == 0:
        status = "LISTO PARA VOLAR"
    else:
        status = "LISTO CON ADVERTENCIAS"

    # Añadir recomendación automática
    detalles_final = []
    for d in detalles:
        detalles_final.append(d + " | Recomendación: Corregir antes de presentarse en counter según AL CIELO.")

    return {"status": status, "detalles": detalles_final}

# -------------------------
# IA SOLO EXPLICA
# -------------------------
async def explicar_con_ia(texto):

    prompt = f"""
    Eres AL CIELO, asistente técnico de carga aérea.
    Explica el siguiente hallazgo.
    NO tomes decisiones.
    NO determines si vuela o no.
    Solo explica causa, impacto operativo y cómo corregir.

    Hallazgo:
    {texto}
    """

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_KEY}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0
                },
                timeout=30
            )
            result = resp.json()
            return result["choices"][0]["message"]["content"]

    except Exception:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.gemini.com/v1/generate",
                    headers={"Authorization": f"Bearer {GEMINI_KEY}"},
                    json={"prompt": prompt},
                    timeout=30
                )
                result = resp.json()
                return result.get("output", "No se pudo generar explicación.")
        except Exception as e:
            return f"No se pudo generar explicación IA: {str(e)}"

# -------------------------
# Endpoint Evaluar
# -------------------------
@app.post("/evaluar")
async def evaluar(data: CargoForm):

    resultado = evaluar_reglas_duras(data)
    explicaciones = []

    for item in resultado["detalles"]:
        texto_ia = await explicar_con_ia(item)
        explicaciones.append({
            "error": item,
            "explicacion": texto_ia
        })

    log = {
        "fecha": str(datetime.datetime.now()),
        "cliente": data.clientId,
        "resultado": resultado,
        "explicaciones": explicaciones
    }

    with open("registro_evaluaciones.json", "a", encoding="utf-8") as f:
        f.write(json.dumps(log, ensure_ascii=False) + "\n")

    return JSONResponse({
        "status": resultado["status"],
        "detalles": resultado["detalles"],
        "explicaciones": explicaciones
    })

# -------------------------
# Endpoint PDF
# -------------------------
@app.post("/generar_pdf")
async def generar_pdf(data: CargoForm):

    resultado = evaluar_reglas_duras(data)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "SMARTCARGO - REPORTE DE EVALUACION", ln=True)

    pdf.set_font("Arial", "", 12)
    pdf.ln(5)
    pdf.cell(0, 8, f"Fecha: {datetime.datetime.now()}", ln=True)
    pdf.cell(0, 8, f"Cliente: {data.clientId}", ln=True)
    pdf.cell(0, 8, f"Resultado: {resultado['status']}", ln=True)

    pdf.ln(10)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Hallazgos:", ln=True)

    pdf.set_font("Arial", "", 12)
    for item in resultado["detalles"]:
        pdf.multi_cell(0, 8, "- " + item)

    filename = "frontend/reporte_smartcargo.pdf"
    pdf.output(filename)

    return {"url": "/static/reporte_smartcargo.pdf"}
