from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fpdf import FPDF
import os, json, datetime, httpx

app = FastAPI(title="SMARTCARGO INFALIBLE")

# -------------------------
# Carpeta Frontend
# -------------------------
if not os.path.exists("frontend"):
    os.makedirs("frontend")
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# -------------------------
# Endpoint raíz
# -------------------------
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
# Modelo de carga
# -------------------------
class CargoForm(BaseModel):
    clientId: str | None = ""
    shipmentType: str | None = ""
    highValue: str | None = ""
    itnNumber: str | None = ""
    awbMaster: str | None = ""
    awbHouse: str | None = ""
    pieceHeight: float | None = 0
    numPieces: int | None = 0
    totalWeight: float | None = 0
    needsShoring: str | None = ""
    nimf15: str | None = ""
    overhang: str | None = ""
    damaged: str | None = ""
    cargoType: str | None = ""
    dgrDocs: str | None = ""
    fitoDocs: str | None = ""
    arrivalTime: str | None = ""
    packaging: str | None = ""
    zipCode: str | None = ""

# -------------------------
# Reglas duras y flujo condicional
# -------------------------
def evaluar_reglas_duras(data: CargoForm):
    detalles = []
    status = "LISTO PARA VOLAR"

    # ---- FASE 1: Identidad ----
    if not data.clientId:
        detalles.append("❌ ID Cliente vacío. Validación Known Shipper no posible.")
        status = "NO LISTO"
    if data.highValue == "yes" and not data.itnNumber:
        detalles.append("❌ Valor > $2,500 USD sin ITN. Multa federal $10,000.")
        status = "NO LISTO"
    if not data.awbMaster:
        detalles.append("❌ AWB Master no proporcionado.")
        status = "NO LISTO"

    # ---- FASE 2: Anatomía de la carga ----
    if data.pieceHeight and data.pieceHeight > 63:
        detalles.append("⚠️ Altura > 63 in: Solo avión carguero. >96 in no cabe en ningún avión.")
        status = "NO LISTO"
    if data.totalWeight and data.totalWeight > 150 and data.needsShoring != "si":
        detalles.append("❌ Pieza >150kg sin shoring. Riesgo estructural.")
        status = "NO LISTO"
    if data.nimf15 != "si":
        detalles.append("❌ Pallet sin NIMF-15. Retorno USDA/CBP.")
        status = "NO LISTO"
    if data.damaged == "yes":
        detalles.append("⚠️ Daños detectados. Counter puede rechazar la carga.")
        status = "NO LISTO"

    # ---- FASE 3: Contenidos críticos ----
    if data.cargoType in ["DGR","PER","BIO"]:
        if data.dgrDocs != "si":
            detalles.append(f"❌ {data.cargoType} sin documentos DGR completos.")
            status = "NO LISTO"
        if data.fitoDocs != "si" and data.cargoType in ["PER","BIO"]:
            detalles.append(f"❌ {data.cargoType} sin certificados FDA/Fitosanitarios.")
            status = "NO LISTO"

    # ---- FASE FINAL: Logística ----
    if not data.arrivalTime:
        detalles.append("⚠️ Hora de llegada no definida. Cut-off 4h antes de salida.")
    if data.packaging not in ["straps","STRAPS"]:
        detalles.append("❌ Embalaje insuficiente. Shrink wrap solo no aceptado.")
        status = "NO LISTO"
    if data.overhang == "yes":
        detalles.append("❌ Overhang detectado. Reestibar necesario.")
        status = "NO LISTO"
    if not data.zipCode:
        detalles.append("❌ Código postal vacío. Bloqueo automático del sistema.")
        status = "NO LISTO"

    # Agregar mensaje de solución
    for i in range(len(detalles)):
        detalles[i] += " | Solución: Revise documentación y embalaje según AL CIELO."

    return {"status": status, "detalles": detalles}

# -------------------------
# IA explicaciones
# -------------------------
async def explicar_con_ia(texto):
    prompt = f"""
    Eres un asistente AL CIELO para Avianca Cargo.
    Explica detalladamente el siguiente hallazgo, indicando causa, consecuencias legales y solución:
    {texto}
    """
    # OpenAI
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
        # Gemini fallback
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.gemini.com/v1/generate",
                    headers={"Authorization": f"Bearer {GEMINI_KEY}"},
                    json={"prompt":prompt, "max_tokens":500},
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
    for item in resultado["detalles"]:
        texto_ia = await explicar_con_ia(item)
        explicaciones.append({"error": item, "explicacion": texto_ia})

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
# Endpoint Generar PDF
# -------------------------
@app.post("/generar_pdf")
async def generar_pdf(data: CargoForm):
    resultado = evaluar_reglas_duras(data)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    secciones = [
        ("Fase 1: Identificación y Seguridad", [
            f"ID Cliente: {data.clientId}",
            f"Tipo de envío: {data.shipmentType}",
            f"Valor alto: {data.highValue}",
            f"ITN: {data.itnNumber}",
            f"AWB Master: {data.awbMaster}",
            f"AWB House: {data.awbHouse}"
        ]),
        ("Fase 2: Anatomía de la Carga", [
            f"Altura pieza: {data.pieceHeight} in",
            f"Número de piezas: {data.numPieces}",
            f"Peso total: {data.totalWeight} kg",
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
        ("Fase Final: Logística", [
            f"Llegada: {data.arrivalTime}",
            f"Embalaje: {data.packaging}",
            f"Código Postal: {data.zipCode}"
        ]),
        ("Resultado Evaluación", resultado["detalles"])
    ]

    for titulo, items in secciones:
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.set_text_color(255,255,255)
        pdf.set_fill_color(226,6,19)
        pdf.cell(0,12,titulo, ln=True, fill=True)
        pdf.ln(5)
        pdf.set_text_color(0,0,0)
        pdf.set_font("Arial", "", 12)
        for item in items:
            pdf.multi_cell(0,8,f"- {item}")
            pdf.ln(1)

    filename = "frontend/reporte_smartcargo.pdf"
    pdf.output(filename)
    return {"url": "/static/reporte_smartcargo.pdf"}
