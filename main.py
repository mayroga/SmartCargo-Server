# main.py
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fpdf import FPDF
import os, datetime, json, shutil, httpx

app = FastAPI(title="SMARTCARGO INFALIBLE – VERSIÓN FINAL")

# -------------------------
# Crear carpeta frontend y archivos
# -------------------------
if not os.path.exists("frontend"):
    os.makedirs("frontend")

if not os.path.exists("uploads"):
    os.makedirs("uploads")

# Montar carpeta estática
app.mount("/static", StaticFiles(directory="frontend"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# -------------------------
# API Keys
# -------------------------
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# -------------------------
# Modelo de carga
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
    pouchOrganized: str | None = ""

# -------------------------
# Evaluación de reglas duras
# -------------------------
def evaluar_reglas_duras(data: dict):
    detalles = []
    status = "✅ VUELA"

    # Regla 1: Pouch organizado
    if data.get("pouchOrganized","") != "si":
        detalles.append("❌ Pouch físico no organizado. No cumple protocolo de envío.")
        status = "❌ NO VUELA"

    # Regla 2: ITN para valor alto
    itn = data.get("itnNumber","")
    if data.get("highValue") == "yes":
        if not itn or not itn.startswith("X"):
            detalles.append("❌ ITN ausente o formato inválido (Debe iniciar con X).")
            status = "❌ NO VUELA"

    # Regla 3: Dimensiones
    try:
        h = float(data.get("pieceHeight",0))
        if h > 96:
            detalles.append("❌ Altura excede límite de avión carguero (>96 in).")
            status = "❌ NO VUELA"
        elif h > 63:
            detalles.append("⚠️ Altura >63 in. Solo apto para carguero, no pasajeros.")
            if status != "❌ NO VUELA": status = "⚠️ REQUIERE REVISIÓN EN MOSTRADOR"
    except:
        detalles.append("⚠️ Altura inválida o no ingresada.")
        if status != "❌ NO VUELA": status = "⚠️ REQUIERE REVISIÓN EN MOSTRADOR"

    # Regla 4: Peso y Shoring
    try:
        w = float(data.get("totalWeight",0))
        if w > 150 and data.get("needsShoring") != "si":
            detalles.append("❌ Peso >150kg sin Shoring. Riesgo estructural.")
            status = "❌ NO VUELA"
    except:
        detalles.append("⚠️ Peso total inválido o no ingresado.")
        if status != "❌ NO VUELA": status = "⚠️ REQUIERE REVISIÓN EN MOSTRADOR"

    # Regla 5: Carga crítica y documentos
    if data.get("cargoType") in ["DGR","PER","BIO"]:
        if data.get("dgrDocs") != "si":
            detalles.append(f"❌ {data.get('cargoType')} sin documentos DGR completos.")
            status = "❌ NO VUELA"
        if data.get("fitoDocs") != "si" and data.get("cargoType") in ["PER","BIO"]:
            detalles.append(f"❌ {data.get('cargoType')} sin certificados FDA/Fitosanitarios.")
            status = "❌ NO VUELA"

    # Regla 6: Embalaje
    if data.get("packaging") not in ["straps","STRAPS"]:
        detalles.append("❌ Embalaje insuficiente para carga pesada.")
        status = "❌ NO VUELA"

    # Regla 7: Overhang
    if data.get("overhang") == "yes":
        detalles.append("❌ Overhang detectado. Re-estibar necesario.")
        status = "❌ NO VUELA"

    # Regla 8: Código postal
    if not data.get("zipCode"):
        detalles.append("❌ Código postal vacío.")
        status = "❌ NO VUELA"

    return {"status": status, "detalles": detalles}

# -------------------------
# IA para explicaciones unificadas
# -------------------------
async def explicar_con_ia_una_vez(detalles):
    if not detalles:
        return "No hay errores, carga lista para volar."
    texto = "\n".join(detalles)
    prompt = f"Eres AL CIELO de Avianca Cargo. Explica cada error de la lista a continuación, indicando causa, consecuencia y solución:\n{texto}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_KEY}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages":[{"role":"user","content":prompt}],
                    "temperature":0
                },
                timeout=30
            )
            result = resp.json()
            return result["choices"][0]["message"]["content"]
    except:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.gemini.com/v1/generate",
                    headers={"Authorization": f"Bearer {GEMINI_KEY}"},
                    json={"prompt":prompt,"max_tokens":500},
                    timeout=30
                )
                result = resp.json()
                return result.get("output","No se pudo generar explicación IA")
        except Exception as e:
            return f"No se pudo generar explicación IA: {str(e)}"

# -------------------------
# Endpoint Evaluar (con archivos)
# -------------------------
@app.post("/evaluar")
async def evaluar(
    clientId: str = Form(...),
    shipmentType: str = Form(""),
    highValue: str = Form(""),
    itnNumber: str = Form(""),
    awbMaster: str = Form(""),
    awbHouse: str = Form(""),
    referenceNumber: str = Form(""),
    originAirport: str = Form(""),
    destinationAirport: str = Form(""),
    departureDate: str = Form(""),
    pieceHeight: float = Form(0),
    numPieces: int = Form(0),
    totalWeight: float = Form(0),
    dimensions: str = Form(""),
    needsShoring: str = Form(""),
    nimf15: str = Form(""),
    overhang: str = Form(""),
    damaged: str = Form(""),
    cargoType: str = Form(""),
    dgrDocs: str = Form(""),
    fitoDocs: str = Form(""),
    arrivalTime: str = Form(""),
    packaging: str = Form(""),
    labels: str = Form(""),
    fragile: str = Form(""),
    shipperName: str = Form(""),
    shipperAddress: str = Form(""),
    shipperPhone: str = Form(""),
    consigneeName: str = Form(""),
    consigneeAddress: str = Form(""),
    consigneePhone: str = Form(""),
    zipCode: str = Form(""),
    pouchOrganized: str = Form(""),
    files: list[UploadFile] = File([])
):
    data = {
        k:v for k,v in locals().items() if k != "files"
    }

    # Guardar fotos
    for f in files:
        path = os.path.join("uploads", f.filename)
        with open(path,"wb") as buffer:
            shutil.copyfileobj(f.file, buffer)

    resultado = evaluar_reglas_duras(data)
    explicacion = await explicar_con_ia_una_vez(resultado["detalles"])

    log = {
        "fecha": str(datetime.datetime.now()),
        "cliente": data.get("clientId"),
        "resultado": resultado,
        "explicacion": explicacion
    }

    with open("registro_evaluaciones.json","a",encoding="utf-8") as f:
        f.write(json.dumps(log,ensure_ascii=False)+"\n")

    return JSONResponse({
        "status": resultado["status"],
        "detalles": resultado["detalles"],
        "explicacion": explicacion
    })

# -------------------------
# Endpoint Generar PDF
# -------------------------
@app.post("/generar_pdf")
async def generar_pdf(
    clientId: str = Form(...),
    shipmentType: str = Form(""),
    highValue: str = Form(""),
    itnNumber: str = Form(""),
    awbMaster: str = Form(""),
    awbHouse: str = Form(""),
    referenceNumber: str = Form(""),
    originAirport: str = Form(""),
    destinationAirport: str = Form(""),
    departureDate: str = Form(""),
    pieceHeight: float = Form(0),
    numPieces: int = Form(0),
    totalWeight: float = Form(0),
    dimensions: str = Form(""),
    needsShoring: str = Form(""),
    nimf15: str = Form(""),
    overhang: str = Form(""),
    damaged: str = Form(""),
    cargoType: str = Form(""),
    dgrDocs: str = Form(""),
    fitoDocs: str = Form(""),
    arrivalTime: str = Form(""),
    packaging: str = Form(""),
    labels: str = Form(""),
    fragile: str = Form(""),
    shipperName: str = Form(""),
    shipperAddress: str = Form(""),
    shipperPhone: str = Form(""),
    consigneeName: str = Form(""),
    consigneeAddress: str = Form(""),
    consigneePhone: str = Form(""),
    zipCode: str = Form(""),
    pouchOrganized: str = Form(""),
):
    data = {
        k:v for k,v in locals().items()
    }

    resultado = evaluar_reglas_duras(data)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.add_page()
    pdf.set_font("Arial","B",16)
    pdf.cell(0,10,"REPORTE SMARTCARGO",ln=True,align="C")
    pdf.ln(5)

    for k,v in data.items():
        pdf.set_font("Arial","",12)
        pdf.multi_cell(0,8,f"{k}: {v}")

    pdf.ln(5)
    pdf.set_font("Arial","B",14)
    pdf.multi_cell(0,8,"ERRORES DETECTADOS:")
    pdf.set_font("Arial","",12)
    for item in resultado["detalles"]:
        pdf.multi_cell(0,8,f"- {item}")

    filename = f"uploads/reporte_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    pdf.output(filename)

    return FileResponse(filename, media_type="application/pdf", filename=os.path.basename(filename))
