from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fpdf import FPDF
import os, json, datetime, httpx

app = FastAPI(title="SMARTCARGO INFALIBLE")

# -------------------------
# Static
# -------------------------
if not os.path.exists("frontend"):
    os.makedirs("frontend")

app.mount("/static", StaticFiles(directory="frontend"), name="static")

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
# Evaluación Reglas Duras
# -------------------------
def evaluar_reglas_duras(data: CargoForm):
    detalles = []
    status = "LISTO PARA VOLAR"

    # Fase 1
    if not data.clientId:
        detalles.append({"campo":"clientId","mensaje":"❌ ID de cliente vacío: Validación Known Shipper no posible.","nivel":"CRITICO"})
        status = "NO LISTO"
    if data.highValue == "yes" and not data.itnNumber:
        detalles.append({"campo":"itnNumber","mensaje":"❌ Valor > $2,500 USD sin ITN. Multa federal $10,000.","nivel":"CRITICO"})
        status = "NO LISTO"
    if not data.awbMaster:
        detalles.append({"campo":"awbMaster","mensaje":"❌ AWB Master no proporcionado. No se puede generar guía correctamente.","nivel":"CRITICO"})
        status = "NO LISTO"

    # Fase 2
    if data.pieceHeight and data.pieceHeight > 63:
        detalles.append({"campo":"pieceHeight","mensaje":"⚠️ Altura > 63 pulgadas: Solo avión carguero.","nivel":"ADVERTENCIA"})
        if data.pieceHeight > 96: status="NO LISTO"
    if data.totalWeight and data.totalWeight > 150 and data.needsShoring != "si":
        detalles.append({"campo":"needsShoring","mensaje":"❌ Pieza >150kg sin shoring. Riesgo de daño.","nivel":"CRITICO"})
        status="NO LISTO"
    if data.nimf15 != "si":
        detalles.append({"campo":"nimf15","mensaje":"❌ Pallet sin NIMF-15. Retorno inmediato por USDA/CBP.","nivel":"CRITICO"})
        status="NO LISTO"
    if data.damaged == "yes":
        detalles.append({"campo":"damaged","mensaje":"⚠️ Daños preexistentes detectados. Counter puede rechazar la carga.","nivel":"ADVERTENCIA"})
        status="NO LISTO"

    # Fase 3
    if data.cargoType in ["DGR","PER","BIO"]:
        if data.dgrDocs != "si":
            detalles.append({"campo":"dgrDocs","mensaje":f"❌ {data.cargoType} sin documentación completa. Requiere Shipper's Declaration.","nivel":"CRITICO"})
            status="NO LISTO"
        if data.fitoDocs != "si" and data.cargoType in ["PER","BIO"]:
            detalles.append({"campo":"fitoDocs","mensaje":f"❌ {data.cargoType} sin certificado FDA/Fitosanitario.","nivel":"CRITICO"})
            status="NO LISTO"

    # Fase 4-8
    if not data.arrivalTime:
        detalles.append({"campo":"arrivalTime","mensaje":"⚠️ Hora de llegada no definida. Cut-off 4h antes de salida.","nivel":"ADVERTENCIA"})
    if data.packaging.lower() not in ["straps"]:
        detalles.append({"campo":"packaging","mensaje":"❌ Embalaje insuficiente. Shrink wrap solo no aceptado.","nivel":"CRITICO"})
        status="NO LISTO"
    if data.overhang=="yes":
        detalles.append({"campo":"overhang","mensaje":"❌ Overhang detectado. Debe re-estibar para avión.","nivel":"CRITICO"})
        status="NO LISTO"
    if not data.zipCode:
        detalles.append({"campo":"zipCode","mensaje":"❌ Código postal vacío. Bloqueo automático del sistema.","nivel":"CRITICO"})
        status="NO LISTO"

    # Agregar solución simple
    for d in detalles:
        d["mensaje"] += " | Solución: Revise documentación, corrija embalaje y medidas según AL CIELO."

    return {"status":status,"detalles":detalles}

# -------------------------
# IA explicaciones
# -------------------------
async def explicar_con_ia(texto):
    prompt = f"Eres un asistente AL CIELO para Avianca Cargo. Explica detalladamente: {texto}"
    # OpenAI principal
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_KEY}"},
                json={"model":"gpt-4o-mini","messages":[{"role":"user","content":prompt}],"temperature":0},
                timeout=30
            )
            result = resp.json()
            return result["choices"][0]["message"]["content"]
    except:
        # Gemini respaldo
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.gemini.com/v1/generate",
                    headers={"Authorization": f"Bearer {GEMINI_KEY}"},
                    json={"prompt":prompt,"max_tokens":500},
                    timeout=30
                )
                result = resp.json()
                return result.get("output","No se pudo generar explicación")
        except Exception as e2:
            return f"No se pudo generar explicación IA: {str(e2)}"

# -------------------------
# Endpoint Evaluar
# -------------------------
@app.post("/evaluar")
async def evaluar(data: CargoForm):
    resultado = evaluar_reglas_duras(data)
    explicaciones = []

    for d in resultado["detalles"]:
        texto_ia = await explicar_con_ia(d["mensaje"])
        explicaciones.append({"error":d["campo"],"nivel":d["nivel"],"explicacion":texto_ia})

    # Log
    log = {"fecha":str(datetime.datetime.now()),"cliente":data.clientId,"resultado":resultado,"explicaciones":explicaciones}
    with open("registro_evaluaciones.json","a",encoding="utf-8") as f:
        f.write(json.dumps(log,ensure_ascii=False)+"\n")

    return JSONResponse({"status":resultado["status"],"detalles":[d["mensaje"] for d in resultado["detalles"]],"explicaciones":explicaciones})

# -------------------------
# Endpoint PDF
# -------------------------
@app.post("/generar_pdf")
async def generar_pdf(data: CargoForm):
    resultado = evaluar_reglas_duras(data)
    pdf = FPDF()
    pdf.set_auto_page_break(True, margin=15)

    secciones = [
        ("Fase 1: Identificación y Seguridad", [
            f"ID Cliente: {data.clientId}",
            f"Tipo de envío: {data.shipmentType}",
            f"Valor alto: {data.highValue}",
            f"ITN: {data.itnNumber}",
            f"AWB Master: {data.awbMaster}",
            f"AWB House: {data.awbHouse}",
            f"Reference Number: {data.referenceNumber}",
            f"Origen/Destino: {data.originAirport} → {data.destinationAirport}",
            f"Fecha de salida: {data.departureDate}"
        ]),
        ("Fase 2: Anatomía de la Carga", [
            f"Altura pieza: {data.pieceHeight} inches",
            f"Número de piezas: {data.numPieces}",
            f"Peso total: {data.totalWeight} kg",
            f"Dimensiones: {data.dimensions}",
            f"Shoring: {data.needsShoring}",
            f"NIMF-15: {data.nimf15}",
            f"Overhang: {data.overhang}",
            f"Daños: {data.damaged}"
        ]),
        ("Fase 3: Contenidos Críticos", [
            f"Tipo carga: {data.cargoType}",
            f"Documentos DGR: {data.dgrDocs}",
            f"Certificados FDA/Fitosanitarios: {data.fitoDocs}"
        ]),
        ("Fase 4-8: Check-list y Logística", [
            f"Llegada al counter: {data.arrivalTime}",
            f"Embalaje: {data.packaging}",
            f"Etiquetas: {data.labels}",
            f"Fragilidad: {data.fragile}",
            f"Shipper: {data.shipperName}, {data.shipperAddress}, {data.shipperPhone}",
            f"Consignee: {data.consigneeName}, {data.consigneeAddress}, {data.consigneePhone}",
            f"Código Postal: {data.zipCode}"
        ]),
        ("Resultado Evaluación", [d["mensaje"] for d in resultado["detalles"]])
    ]

    for titulo, items in secciones:
        pdf.add_page()
        pdf.set_font("Arial","B",16)
        pdf.set_text_color(255,255,255)
        pdf.set_fill_color(226,6,19)
        pdf.cell(0,12,titulo,ln=True,fill=True)
        pdf.ln(5)
        pdf.set_text_color(0,0,0)
        pdf.set_font("Arial","",12)
        for item in items:
            pdf.multi_cell(0,8,f"- {item}")
            pdf.ln(1)

    filename = "frontend/reporte_smartcargo.pdf"
    pdf.output(filename)
    return {"url": "/static/reporte_smartcargo.pdf"}
