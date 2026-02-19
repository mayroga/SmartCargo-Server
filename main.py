from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fpdf import FPDF
import datetime
import os

app = FastAPI(title="SMARTCARGO-AIPA | Avianca Cargo Advisory")

# =========================
# Static Files
# =========================
if not os.path.exists("frontend"):
    os.makedirs("frontend")

app.mount("/static", StaticFiles(directory="frontend"), name="static")


# =========================
# Data Model (100% aligned with frontend)
# =========================
class CargoForm(BaseModel):
    clientId: str
    highValue: str
    itnNumber: str = ""
    shipmentType: str

    pieceHeight: float
    pieceWeight: float
    nimf15: str
    palletType: str

    dangerousGoods: str
    origin: str

    awbCopies: str
    zipCode: str

    arrivalTime: str

    straps: str
    awbOnBoxes: str
    damagedBoxes: str
    shrinkWrap: str
    oldLabels: str

    cleanCargo: str
    fragileLabels: str
    piecesMatch: str

    tanks: str
    overhang: float


# =========================
# Serve Frontend
# =========================
@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        return f.read()


# =========================
# Core Evaluation Engine
# =========================
def evaluar_carga(data: CargoForm):
    reporte = []
    aprobado = True

    # -------------------
    # FASE 1
    # -------------------
    if not data.clientId.strip():
        reporte.append("❌ ID Cliente / SCAC es obligatorio.")
        aprobado = False

    if data.highValue == "yes" and not data.itnNumber.strip():
        reporte.append("❌ ITN obligatorio para mercancía > $2,500 USD.")
        aprobado = False

    if data.shipmentType == "consolidated":
        reporte.append("⚠ Envío consolidado: verificar Houses y manifest.")

    # -------------------
    # FASE 2
    # -------------------
    if data.pieceHeight > 96:
        reporte.append("❌ Altura excede 96'' - No puede volar en Avianca.")
        aprobado = False
    elif data.pieceHeight > 63:
        reporte.append("⚠ Altura >63'' - Solo permitido en carguero.")

    if data.pieceWeight > 150:
        reporte.append("⚠ Peso >150kg - Requiere Shoring.")

    if data.nimf15 == "no":
        reporte.append("❌ Sin sello NIMF-15 - Rechazo inmediato.")
        aprobado = False

    # -------------------
    # FASE 3
    # -------------------
    if data.dangerousGoods == "yes":
        reporte.append("⚠ Mercancía peligrosa - Requiere DGR y declaración IATA.")

    if data.origin == "yes":
        reporte.append("⚠ Producto animal/vegetal - Puede requerir FDA/USDA.")

    # -------------------
    # FASE 4
    # -------------------
    if data.awbCopies == "no":
        reporte.append("❌ AWB incompleto - 3 originales + 6 copias requeridas.")
        aprobado = False

    if not data.zipCode.strip():
        reporte.append("❌ Zip Code obligatorio.")
        aprobado = False

    # -------------------
    # FASE 5
    # -------------------
    try:
        hora = int(data.arrivalTime.split(":")[0])
        if hora > 16:
            reporte.append("⚠ Arribo después del cut-off - Puede perder vuelo.")
    except:
        reporte.append("⚠ Hora inválida.")

    # -------------------
    # FASE 6
    # -------------------
    if data.straps == "no":
        reporte.append("❌ Falta flejado adecuado.")
        aprobado = False

    if data.damagedBoxes == "yes":
        reporte.append("❌ Cajas dañadas detectadas.")
        aprobado = False

    if data.shrinkWrap == "no":
        reporte.append("❌ Shrink wrap incorrecto.")
        aprobado = False

    if data.oldLabels == "yes":
        reporte.append("⚠ Remover etiquetas viejas.")

    # -------------------
    # FASE 7
    # -------------------
    if data.cleanCargo == "no":
        reporte.append("❌ Carga sucia o contaminada.")
        aprobado = False

    if data.piecesMatch == "no":
        reporte.append("❌ Número de piezas no coincide con AWB.")
        aprobado = False

    # -------------------
    # FASE 8
    # -------------------
    if data.tanks == "yes":
        reporte.append("❌ Tanques deben estar vacíos y certificados.")
        aprobado = False

    if data.overhang > 0:
        reporte.append("❌ Overhang detectado - Re-estibar.")
        aprobado = False

    return {
        "status": "APROBADO" if aprobado else "RECHAZADO",
        "detalle": reporte
    }


# =========================
# API Routes
# =========================
@app.post("/evaluar")
async def evaluar(form: CargoForm):
    return JSONResponse(content=evaluar_carga(form))


@app.post("/generar_pdf")
async def generar_pdf(form: CargoForm):
    resultado = evaluar_carga(form)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(0, 10, "SMARTCARGO-AIPA - Avianca Cargo Advisory", ln=True)
    pdf.cell(0, 10, f"Fecha: {datetime.datetime.now()}", ln=True)
    pdf.cell(0, 10, f"Veredicto: {resultado['status']}", ln=True)
    pdf.ln(5)

    for linea in resultado["detalle"]:
        pdf.multi_cell(0, 8, f"- {linea}")

    filename = "frontend/reporte_last.pdf"
    pdf.output(filename)

    return JSONResponse(content={"url": "/static/reporte_last.pdf"})
