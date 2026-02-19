# main.py
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from pathlib import Path
from fpdf import FPDF
from typing import List

app = FastAPI(title="SMARTCARGO-AIPA API")

# Configuración CORS para permitir frontend en Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ajusta según dominio frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Carpeta para subir fotos
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Modelo para recibir respuestas
class CargoData(BaseModel):
    shipmentType: str
    highValue: str
    itnNumber: str = ""
    knownShipper: str
    pieceHeight: float
    pieceWeight: float
    volumetricWeight: float
    nimf15: str
    straps: str
    oldLabels: str
    bateriasLitio: str
    xrayImpenetrable: str
    descripcionGuia: str
    pouchOrganized: str

# ---------------------
# Función de evaluación
# ---------------------
def evaluar_reglas(data: CargoData):
    detalles = []
    status = "✅ VUELA"

    # Fase I: Documentación y ITN
    if data.shipmentType == "consolidado":
        detalles.append("✅ Consolidado: Manifiesto revisado")
    if data.highValue == "yes":
        if not data.itnNumber or not data.itnNumber.startswith("X"):
            detalles.append("❌ ITN ausente o formato inválido")
            status = "❌ NO VUELA"

    if data.knownShipper != "yes":
        detalles.append("⚠️ Se requiere Known Shipper con sello de camión correcto")
        if status != "❌ NO VUELA":
            status = "⚠️ REQUIERE REVISIÓN"

    # Fase II: Altura y peso
    if data.pieceHeight > 96:
        detalles.append("❌ Altura excede límite de fuselaje (96 in)")
        status = "❌ NO VUELA"
    elif data.pieceHeight > 63:
        detalles.append("⚠️ Altura >63in: solo vuelos Cargueros")
        if status != "❌ NO VUELA":
            status = "⚠️ REQUIERE REVISIÓN"

    if data.pieceWeight > 150:
        detalles.append("⚠️ Peso >150kg: obligatorio usar skids/shoring")
        if status != "❌ NO VUELA":
            status = "⚠️ REQUIERE REVISIÓN"

    # Fase III: Integridad y embalaje
    if data.nimf15 != "yes":
        detalles.append("❌ Estibas sin sello NIMF-15")
        status = "❌ NO VUELA"
    if data.straps != "flejes":
        detalles.append("⚠️ Carga sin flejes, revisar estabilidad")
        if status != "❌ NO VUELA":
            status = "⚠️ REQUIERE REVISIÓN"
    if data.oldLabels != "yes":
        detalles.append("⚠️ Etiquetas viejas no eliminadas")
        if status != "❌ NO VUELA":
            status = "⚠️ REQUIERE REVISIÓN"

    # Fase IV: Contenidos peligrosos
    if data.bateriasLitio == "yes":
        detalles.append("⚠️ Baterías de litio declaradas")
        if status != "❌ NO VUELA":
            status = "⚠️ REQUIERE REVISIÓN"
    if data.xrayImpenetrable == "yes":
        detalles.append("⚠️ Carga impenetrable a Rayos X")
        if status != "❌ NO VUELA":
            status = "⚠️ REQUIERE REVISIÓN"

    # Fase V: Pouch
    if data.pouchOrganized != "yes":
        detalles.append("❌ Pouch mal organizado")
        status = "❌ NO VUELA"

    return {"status": status, "detalles": detalles}

# ---------------------
# Endpoint principal: Evaluar carga
# ---------------------
@app.post("/evaluar_carga")
async def evaluar_carga(data: CargoData, fotos: List[UploadFile] = File([])):
    # Guardar fotos
    fotos_urls = []
    for foto in fotos:
        file_path = UPLOAD_DIR / foto.filename
        with open(file_path, "wb") as f:
            f.write(await foto.read())
        fotos_urls.append(str(file_path))

    # Evaluación de reglas
    resultado = evaluar_reglas(data)

    return JSONResponse({"resultado": resultado, "fotos": fotos_urls})

# ---------------------
# Endpoint PDF
# ---------------------
@app.post("/generar_pdf")
async def generar_pdf(data: CargoData):
    pdf_filename = f"report_{data.shipmentType}.pdf"
    pdf_path = UPLOAD_DIR / pdf_filename

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, "SMARTCARGO-AIPA | Evaluación de Carga", ln=True, align="C")
    pdf.ln(10)

    # Añadir detalles
    pdf.cell(0, 10, f"Shipment Type: {data.shipmentType}", ln=True)
    pdf.cell(0, 10, f"High Value: {data.highValue}", ln=True)
    pdf.cell(0, 10, f"ITN: {data.itnNumber}", ln=True)
    pdf.cell(0, 10, f"Known Shipper: {data.knownShipper}", ln=True)
    pdf.cell(0, 10, f"Altura: {data.pieceHeight} in", ln=True)
    pdf.cell(0, 10, f"Peso: {data.pieceWeight} kg", ln=True)
    pdf.cell(0, 10, f"Volumétrico: {data.volumetricWeight}", ln=True)
    pdf.cell(0, 10, f"NIMF-15: {data.nimf15}", ln=True)
    pdf.cell(0, 10, f"Straps: {data.straps}", ln=True)
    pdf.cell(0, 10, f"Old Labels: {data.oldLabels}", ln=True)
    pdf.cell(0, 10, f"Baterías Litio: {data.bateriasLitio}", ln=True)
    pdf.cell(0, 10, f"Xray Impenetrable: {data.xrayImpenetrable}", ln=True)
    pdf.cell(0, 10, f"Descripción Guía: {data.descripcionGuia}", ln=True)
    pdf.cell(0, 10, f"Pouch: {data.pouchOrganized}", ln=True)

    # Evaluación de reglas
    resultado = evaluar_reglas(data)
    pdf.ln(10)
    pdf.cell(0, 10, f"Status: {resultado['status']}", ln=True)
    pdf.ln(5)
    pdf.cell(0, 10, "Detalles:", ln=True)
    for det in resultado["detalles"]:
        pdf.cell(0, 8, det, ln=True)

    pdf.output(str(pdf_path))

    return FileResponse(str(pdf_path), media_type="application/pdf", filename=pdf_filename)

# ---------------------
# Endpoint fotos (preview)
# ---------------------
@app.get("/uploads/{filename}")
async def get_foto(filename: str):
    file_path = UPLOAD_DIR / filename
    if file_path.exists():
        return FileResponse(str(file_path))
    return JSONResponse({"error": "Foto no encontrada"}, status_code=404)

