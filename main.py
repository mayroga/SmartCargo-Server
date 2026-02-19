# main.py
import os
from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
from fpdf import FPDF
import tempfile
import shutil
import re

app = FastAPI(title="SMARTCARGO Infalible")

# Permitir CORS para frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambiar a tu dominio en producción
    allow_methods=["*"],
    allow_headers=["*"]
)

# Carpeta para almacenar archivos temporales
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Montar carpeta estática para servir PDFs si se desea
app.mount("/static", StaticFiles(directory=UPLOAD_DIR), name="static")


def evaluar_reglas_duras(data: dict):
    detalles = []
    status = "✅ VUELA"

    # ================== FASE I: UNIVERSAL ==================
    if data.get("shipmentType") == "consolidado" and not data.get("manifestHouses"):
        detalles.append("❌ ERROR: Falta Manifiesto de Houses en consolidado.")
        status = "❌ NO VUELA"

    itn = data.get("itnNumber", "")
    cargoValue = float(data.get("cargoValue", 0))
    if cargoValue > 2500 and (not itn or not itn.startswith('X')):
        detalles.append("❌ RECHAZO CBP: ITN ausente o formato inválido (Debe iniciar con X).")
        status = "❌ NO VUELA"

    if data.get("knownShipper") != "yes":
        detalles.append("❌ RECHAZO TSA: Known Shipper inválido o sello roto.")
        status = "❌ NO VUELA"

    # ================== FASE II: TÉCNICA ==================
    try:
        h = float(data.get("pieceHeight", 0))
        if h > 96:
            detalles.append("❌ RECHAZO TÉCNICO: Altura excede fuselaje (>96 in).")
            status = "❌ NO VUELA"
        elif h > 63:
            detalles.append("⚠️ AVISO: Altura >63 in, solo apto para vuelo Carguero.")
            if status != "❌ NO VUELA":
                status = "⚠️ REQUIERE CAMBIO DE RESERVA"
    except:
        pass

    try:
        w_unit = data.get("weightUnit","kg")
        pieceWeight = float(data.get("pieceWeight",0))
        if w_unit=="lb":
            pieceWeight = pieceWeight * 0.453592  # Convert lb a kg
        if pieceWeight > 150:
            detalles.append("❌ RECHAZO: Peso >150kg, obligatorio usar skids/shoring.")
            status = "❌ NO VUELA"
    except:
        pass

    # Volumetric Weight (solo aviso)
    detalles.append(f"Peso volumétrico calculado: {data.get('volumetricWeight')}")

    # ================== FASE III: INTEGRIDAD ==================
    if data.get("nimf15") != "yes":
        detalles.append("❌ Pallet sin sello NIMF-15, no despachar.")
        status = "❌ NO VUELA"

    if data.get("straps") != "flejes":
        detalles.append("⚠️ Advertencia: Flejes ausentes en carga pesada.")

    if data.get("oldLabels") != "yes":
        detalles.append("❌ Etiquetas antiguas no borradas, riesgo de misrouting.")
        status = "❌ NO VUELA"

    # ================== FASE IV: CRÍTICA (DGR/TSA) ==================
    if data.get("hasBatteries") == "yes":
        detalles.append("❌ Declarar UN3480/3481 y presentar 2 originales Shipper’s Declaration.")
        status = "❌ NO VUELA"

    if data.get("xrayBlocked") == "yes":
        detalles.append("⚠️ Rayos X bloqueados, embalaje debe permitir reapertura.")

    desc = data.get("description","")
    if not desc or "said to contain" in desc.lower():
        detalles.append("❌ Descripción genérica inválida (Use nombre real).")
        status = "❌ NO VUELA"

    # ================== FASE V: POUCH ==================
    if data.get("pouchOrganized") != "si":
        detalles.append("❌ Pouch mal organizado, no se puede evaluar.")
        status = "❌ NO VUELA"

    explicacion = "Se han evaluado todas las fases: Universal, Técnica, Integridad, Crítica y Pouch."
    return {"status": status, "detalles": detalles, "explicacion": explicacion}


@app.post("/evaluar")
async def evaluar(
    shipmentType: str = Form(...),
    manifestHouses: str = Form(""),
    cargoValue: float = Form(...),
    itnNumber: str = Form(""),
    knownShipper: str = Form(...),
    pieceHeight: float = Form(...),
    pieceWeight: float = Form(...),
    weightUnit: str = Form("kg"),
    volumetricWeight: float = Form(...),
    nimf15: str = Form(...),
    straps: str = Form(...),
    oldLabels: str = Form(...),
    hasBatteries: str = Form(...),
    xrayBlocked: str = Form(...),
    description: str = Form(...),
    pouchOrganized: str = Form(...),
    files: List[UploadFile] = File(default=[])
):
    # Guardar archivos temporalmente
    temp_dir = tempfile.mkdtemp()
    file_paths = []
    try:
        for f in files:
            path = os.path.join(temp_dir, f.filename)
            with open(path, "wb") as buffer:
                shutil.copyfileobj(f.file, buffer)
            file_paths.append(path)

        data = {
            "shipmentType": shipmentType,
            "manifestHouses": manifestHouses,
            "cargoValue": cargoValue,
            "itnNumber": itnNumber,
            "knownShipper": knownShipper,
            "pieceHeight": pieceHeight,
            "pieceWeight": pieceWeight,
            "weightUnit": weightUnit,
            "volumetricWeight": volumetricWeight,
            "nimf15": nimf15,
            "straps": straps,
            "oldLabels": oldLabels,
            "hasBatteries": hasBatteries,
            "xrayBlocked": xrayBlocked,
            "description": description,
            "pouchOrganized": pouchOrganized,
            "files": file_paths
        }

        resultado = evaluar_reglas_duras(data)
        return JSONResponse(content=resultado)

    finally:
        # limpiar temporal
        for f in file_paths:
            if os.path.exists(f):
                os.remove(f)
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.post("/generar_pdf")
async def generar_pdf(
    shipmentType: str = Form(...),
    manifestHouses: str = Form(""),
    cargoValue: float = Form(...),
    itnNumber: str = Form(""),
    knownShipper: str = Form(...),
    pieceHeight: float = Form(...),
    pieceWeight: float = Form(...),
    weightUnit: str = Form("kg"),
    volumetricWeight: float = Form(...),
    nimf15: str = Form(...),
    straps: str = Form(...),
    oldLabels: str = Form(...),
    hasBatteries: str = Form(...),
    xrayBlocked: str = Form(...),
    description: str = Form(...),
    pouchOrganized: str = Form(...),
    files: List[UploadFile] = File(default=[])
):
    # Crear PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial","B",14)
    pdf.cell(0,10,"SMARTCARGO - Reporte de Evaluación", ln=True, align="C")
    pdf.set_font("Arial","",12)
    pdf.ln(5)

    pdf.cell(0,10,f"Shipment Type: {shipmentType}", ln=True)
    pdf.cell(0,10,f"Cargo Value: {cargoValue}", ln=True)
    pdf.cell(0,10,f"ITN: {itnNumber}", ln=True)
    pdf.cell(0,10,f"Known Shipper: {knownShipper}", ln=True)
    pdf.cell(0,10,f"Piece Height: {pieceHeight} in", ln=True)
    pdf.cell(0,10,f"Piece Weight: {pieceWeight} {weightUnit}", ln=True)
    pdf.cell(0,10,f"Volumetric Weight: {volumetricWeight}", ln=True)
    pdf.cell(0,10,f"Pallet NIMF-15: {nimf15}", ln=True)
    pdf.cell(0,10,f"Straps: {straps}", ln=True)
    pdf.cell(0,10,f"Old Labels Removed: {oldLabels}", ln=True)
    pdf.cell(0,10,f"Batteries: {hasBatteries}", ln=True)
    pdf.cell(0,10,f"X-Ray Blocked: {xrayBlocked}", ln=True)
    pdf.cell(0,10,f"Description: {description}", ln=True)
    pdf.cell(0,10,f"Pouch Organized: {pouchOrganized}", ln=True)

    # Guardar imágenes
    temp_dir = tempfile.mkdtemp()
    try:
        y = pdf.get_y() + 5
        for f in files:
            img_path = os.path.join(temp_dir, f.filename)
            with open(img_path,"wb") as buffer:
                shutil.copyfileobj(f.file, buffer)
            pdf.image(img_path, x=10, y=y, w=60)
            y += 65

        pdf_path = os.path.join(UPLOAD_DIR, "reporte_smartcargo.pdf")
        pdf.output(pdf_path)
        return FileResponse(pdf_path, media_type='application/pdf', filename="reporte_smartcargo.pdf")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

