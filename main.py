# main.py
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from fpdf import FPDF
from typing import List

app = FastAPI(title="SMARTCARGO-AIPA API")

# ------------------------
# Configuración CORS
# ------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambia a tu frontend si quieres restringir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------
# Carpeta uploads
# ------------------------
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# ------------------------
# Modelo CargoData
# ------------------------
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

# ------------------------
# Función de evaluación
# ------------------------
def evaluar_reglas(data: CargoData):
    detalles = []
    status = "✅ VUELA"

    # Fase I
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

    # Fase II
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

    # Fase III
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

    # Fase IV
    if data.bateriasLitio == "yes":
        detalles.append("⚠️ Baterías de litio declaradas")
        if status != "❌ NO VUELA":
            status = "⚠️ REQUIERE REVISIÓN"
    if data.xrayImpenetrable == "yes":
        detalles.append("⚠️ Carga impenetrable a Rayos X")
        if status != "❌ NO VUELA":
            status = "⚠️ REQUIERE REVISIÓN"

    # Fase V
    if data.pouchOrganized != "yes":
        detalles.append("❌ Pouch mal organizado")
        status = "❌ NO VUELA"

    return {"status": status, "detalles": detalles}

# ------------------------
# Endpoint POST /evaluar
# ------------------------
@app.post("/evaluar")
@app.post("/evaluar/")  # Trailing slash opcional
async def evaluar(
    shipmentType: str = Form(...),
    highValue: str = Form(...),
    itnNumber: str = Form(""),
    knownShipper: str = Form(...),
    pieceHeight: float = Form(...),
    pieceWeight: float = Form(...),
    volumetricWeight: float = Form(...),
    nimf15: str = Form(...),
    straps: str = Form(...),
    oldLabels: str = Form(...),
    bateriasLitio: str = Form(...),
    xrayImpenetrable: str = Form(...),
    descripcionGuia: str = Form(...),
    pouchOrganized: str = Form(...),
    fotos: List[UploadFile] = File([])
):
    # Guardar fotos
    fotos_urls = []
    for foto in fotos:
        file_path = UPLOAD_DIR / foto.filename
        with open(file_path, "wb") as f:
            f.write(await foto.read())
        fotos_urls.append(str(file_path))

    # Crear CargoData y evaluar reglas
    data = CargoData(
        shipmentType=shipmentType,
        highValue=highValue,
        itnNumber=itnNumber,
        knownShipper=knownShipper,
        pieceHeight=pieceHeight,
        pieceWeight=pieceWeight,
        volumetricWeight=volumetricWeight,
        nimf15=nimf15,
        straps=straps,
        oldLabels=oldLabels,
        bateriasLitio=bateriasLitio,
        xrayImpenetrable=xrayImpenetrable,
        descripcionGuia=descripcionGuia,
        pouchOrganized=pouchOrganized
    )
    resultado = evaluar_reglas(data)

    return JSONResponse({"status": resultado["status"], "detalles": resultado["detalles"], "fotos": fotos_urls})

# ------------------------
# Endpoint POST /generar_pdf
# ------------------------
@app.post("/generar_pdf")
@app.post("/generar_pdf/")
async def generar_pdf(
    shipmentType: str = Form(...),
    highValue: str = Form(...),
    itnNumber: str = Form(""),
    knownShipper: str = Form(...),
    pieceHeight: float = Form(...),
    pieceWeight: float = Form(...),
    volumetricWeight: float = Form(...),
    nimf15: str = Form(...),
    straps: str = Form(...),
    oldLabels: str = Form(...),
    bateriasLitio: str = Form(...),
    xrayImpenetrable: str = Form(...),
    descripcionGuia: str = Form(...),
    pouchOrganized: str = Form(...),
    fotos: List[UploadFile] = File([])
):
    # Guardar fotos (opcional)
    for foto in fotos:
        file_path = UPLOAD_DIR / foto.filename
        with open(file_path, "wb") as f:
            f.write(await foto.read())

    # Crear CargoData y evaluar reglas
    data = CargoData(
        shipmentType=shipmentType,
        highValue=highValue,
        itnNumber=itnNumber,
        knownShipper=knownShipper,
        pieceHeight=pieceHeight,
        pieceWeight=pieceWeight,
        volumetricWeight=volumetricWeight,
        nimf15=nimf15,
        straps=straps,
        oldLabels=oldLabels,
        bateriasLitio=bateriasLitio,
        xrayImpenetrable=xrayImpenetrable,
        descripcionGuia=descripcionGuia,
        pouchOrganized=pouchOrganized
    )
    resultado = evaluar_reglas(data)

    # Generar PDF
    pdf_filename = f"report_{shipmentType}.pdf"
    pdf_path = UPLOAD_DIR / pdf_filename
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, "SMARTCARGO-AIPA | Evaluación de Carga", ln=True, align="C")
    pdf.ln(10)

    # Datos
    for field, value in data.dict().items():
        pdf.cell(0, 10, f"{field}: {value}", ln=True)
    pdf.ln(5)
    pdf.cell(0, 10, f"Status: {resultado['status']}", ln=True)
    pdf.ln(5)
    pdf.cell(0, 10, "Detalles:", ln=True)
    for det in resultado["detalles"]:
        pdf.cell(0, 8, det, ln=True)

    pdf.output(str(pdf_path))
    return JSONResponse({"filename": pdf_filename})

# ------------------------
# Endpoint GET /download/{filename}
# ------------------------
@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = UPLOAD_DIR / filename
    if file_path.exists():
        return FileResponse(str(file_path), media_type="application/pdf", filename=filename)
    return JSONResponse({"detail": "Archivo no encontrado"}, status_code=404)
