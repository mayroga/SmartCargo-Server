from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fpdf import FPDF
import os
import json
import datetime
import httpx
import shutil

app = FastAPI(title="SMARTCARGO INFALIBLE")

# Carpetas
if not os.path.exists("frontend"):
    os.makedirs("frontend")
if not os.path.exists("uploads"):
    os.makedirs("uploads")

app.mount("/static", StaticFiles(directory="frontend"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# API Keys
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# -------------------------
# Evaluación reglas duras
# -------------------------
def evaluar_reglas_duras(data: dict):
    detalles = []
    status = "LISTO PARA VOLAR ✅"

    # Fase 1
    if not data.get("clientId"):
        detalles.append("❌ ID de cliente vacío: Validación Known Shipper no posible.")
        status = "NO VUELA ❌"
    if data.get("highValue")=="yes" and not data.get("itnNumber"):
        detalles.append("❌ Valor > $2,500 USD sin ITN.")
        status = "NO VUELA ❌"
    if not data.get("awbMaster"):
        detalles.append("❌ AWB Master no proporcionado.")
        status = "NO VUELA ❌"

    # Fase 2
    try:
        pieceHeight = float(data.get("pieceHeight","0"))
        totalWeight = float(data.get("totalWeight","0"))
    except:
        pieceHeight = 0
        totalWeight = 0

    if pieceHeight>63:
        detalles.append("⚠️ Altura > 63 in. Solo avión carguero. >96 in no permitido.")
        status = "NO VUELA ❌"
    if totalWeight>150 and data.get("needsShoring")!="si":
        detalles.append("❌ Pieza >150kg sin shoring.")
        status = "NO VUELA ❌"
    if data.get("nimf15")!="si":
        detalles.append("❌ Pallet sin NIMF-15.")
        status = "NO VUELA ❌"
    if data.get("damaged")=="yes":
        detalles.append("⚠️ Daños preexistentes detectados.")

    # Fase 3
    cargoType = data.get("cargoType")
    if cargoType in ["DGR","PER","BIO"]:
        if data.get("dgrDocs")!="si":
            detalles.append(f"❌ {cargoType} sin documentación DGR.")
            status = "NO VUELA ❌"
        if data.get("fitoDocs")!="si" and cargoType in ["PER","BIO"]:
            detalles.append(f"❌ {cargoType} sin certificado FDA/Fitosanitario.")
            status = "NO VUELA ❌"

    # Fase final
    if not data.get("arrivalTime"):
        detalles.append("⚠️ Hora de llegada no definida.")
    if data.get("packaging") not in ["straps","STRAPS"]:
        detalles.append("❌ Embalaje insuficiente.")
        status = "NO VUELA ❌"
    if data.get("overhang")=="yes":
        detalles.append("❌ Overhang detectado.")
        status = "NO VUELA ❌"
    if not data.get("zipCode"):
        detalles.append("❌ Código postal vacío.")
        status = "NO VUELA ❌"

    for i in range(len(detalles)):
        detalles[i]+=" | Solución: Revise documentación y medidas según AL CIELO."

    return {"status": status, "detalles": detalles}

# -------------------------
# IA explicativa
# -------------------------
async def explicar_con_ia(texto):
    prompt = f"""
Eres un asistente AL CIELO para Avianca Cargo.
Explica detalladamente el siguiente hallazgo, indicando la causa, consecuencias legales y solución:
{texto}
"""
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
                    json={"prompt": prompt,"max_tokens":500},
                    timeout=30
                )
                result = resp.json()
                return result.get("output","No se pudo generar explicación IA")
        except Exception as e2:
            return f"No se pudo generar explicación IA: {str(e2)}"

# -------------------------
# Endpoint Evaluar con archivos
# -------------------------
@app.post("/evaluar")
async def evaluar(
    clientId: str = Form(""),
    shipmentType: str = Form(""),
    highValue: str = Form(""),
    itnNumber: str = Form(""),
    awbMaster: str = Form(""),
    awbHouse: str = Form(""),
    referenceNumber: str = Form(""),
    originAirport: str = Form(""),
    destinationAirport: str = Form(""),
    departureDate: str = Form(""),
    pieceHeight: str = Form("0"),
    numPieces: str = Form("0"),
    totalWeight: str = Form("0"),
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
    zipCode: str = Form(""),
    fotoCarga: UploadFile = File(None),
    docsCertificados: UploadFile = File(None)
):
    data = dict(
        clientId=clientId, shipmentType=shipmentType, highValue=highValue,
        itnNumber=itnNumber, awbMaster=awbMaster, awbHouse=awbHouse,
        referenceNumber=referenceNumber, originAirport=originAirport,
        destinationAirport=destinationAirport, departureDate=departureDate,
        pieceHeight=pieceHeight, numPieces=numPieces, totalWeight=totalWeight,
        dimensions=dimensions, needsShoring=needsShoring, nimf15=nimf15,
        overhang=overhang, damaged=damaged, cargoType=cargoType,
        dgrDocs=dgrDocs, fitoDocs=fitoDocs, arrivalTime=arrivalTime,
        packaging=packaging, zipCode=zipCode
    )

    # Guardar archivos
    uploaded_files=[]
    for file in [fotoCarga, docsCertificados]:
        if file:
            file_path = os.path.join("uploads", file.filename)
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            uploaded_files.append("/uploads/"+file.filename)

    resultado = evaluar_reglas_duras(data)
    explicaciones=[]
    for item in resultado["detalles"]:
        texto_ia = await explicar_con_ia(item)
        explicaciones.append({"error": item, "explicacion": texto_ia})

    log={"fecha": str(datetime.datetime.now()), "cliente": clientId, "resultado": resultado, "archivos": uploaded_files}
    with open("registro_evaluaciones.json", "a", encoding="utf-8") as f:
        f.write(json.dumps(log, ensure_ascii=False)+"\n")

    return JSONResponse({"status": resultado["status"], "detalles": resultado["detalles"], "explicaciones": explicaciones, "archivos": uploaded_files})
