import os
import json
import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fpdf import FPDF
import httpx

# -------------------------
# FastAPI Setup
# -------------------------
app = FastAPI(title="SMARTCARGO - AL CIELO")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Frontend directory
if not os.path.exists("frontend"):
    os.makedirs("frontend")
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# -------------------------
# API Keys
# -------------------------
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# -------------------------
# Modelo de datos Cargo
# -------------------------
class CargoForm(BaseModel):
    # Fase 1: Identificación
    clientId: str
    shipmentType: str
    highValue: str
    itnNumber: str | None = ""
    # Datos AWB
    awbMaster: str
    awbHouse: str | None = ""
    referenceNumber: str
    originAirport: str
    destinationAirport: str
    departureDate: str
    shipperName: str
    shipperAddress: str
    shipperPhone: str
    consigneeName: str
    consigneeAddress: str
    consigneePhone: str
    zipCode: str
    # Fase 2: Anatomía carga
    pieceHeight: float
    numPieces: int
    totalWeight: float
    dimensions: str
    needsShoring: str
    nimf15: str
    overhang: str
    damaged: str
    # Fase 3: Contenidos críticos
    cargoType: str
    dgrDocs: str | None = ""
    fitoDocs: str | None = ""
    # Fase 4-8: Check final
    arrivalTime: str | None = ""
    packaging: str | None = ""
    labels: str | None = ""
    fragile: str | None = ""

# -------------------------
# Página principal
# -------------------------
@app.get("/", response_class=HTMLResponse)
async def home():
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        return f.read()

# -------------------------
# Función IA simulada (OpenAI principal, Gemini respaldo)
# -------------------------
async def evaluar_ia(data: dict):
    prompt = f"""
AL CIELO: Evalúa la carga con los siguientes datos, devuelve JSON con:
- status: LISTO PARA VOLAR / NO LISTO
- detalles: lista de alertas o correcciones necesarias
{json.dumps(data, indent=2)}
"""
    # Primero OpenAI
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_KEY}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0
                }
            )
            r = resp.json()
            return eval(r["choices"][0]["message"]["content"])
    except Exception as e_openai:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.gemini.com/v1/generate",
                    headers={"Authorization": f"Bearer {GEMINI_KEY}"},
                    json={"prompt": prompt, "max_tokens":500}
                )
                r = resp.json()
                return eval(r.get("output","{'status':'ERROR IA','detalles':[str(e_openai)]}"))
        except Exception as e_gemini:
            return {"status":"ERROR IA","detalles":[str(e_openai), str(e_gemini)]}

# -------------------------
# Evaluación reglas duras y legales
# -------------------------
def evaluar_reglas_duras(data: CargoForm):
    status = "LISTO PARA VOLAR"
    detalles = []

    # Fase 1: Known Shipper
    if not data.clientId:
        status = "NO LISTO"
        detalles.append("❌ Cliente no registrado / SCAC inválido. Se requiere inspección física.")

    # ITN obligatorio para mercancía > $2,500
    if data.highValue.lower() == "yes" and not data.itnNumber:
        status = "NO LISTO"
        detalles.append("❌ ITN (AES) obligatorio para valor > $2,500 USD.")

    # Fase 2: Altura pieza
    if data.pieceHeight > 96:
        status = "NO LISTO"
        detalles.append("❌ Altura excede límite de Avianca. No puede volar.")
    elif data.pieceHeight > 63:
        detalles.append("⚠️ Solo puede volar en avión Carguero (Freighter).")

    # Peso > 150 kg
    if data.needsShoring.lower() == "si":
        detalles.append("🛠 Shoring obligatorio para piezas >150 kg.")

    # Fase 3: Contenidos críticos
    if data.cargoType.upper() == "DGR" and data.dgrDocs.lower() != "si":
        status = "NO LISTO"
        detalles.append("❌ Faltan Shipper's Declaration originales para mercancía peligrosa.")

    if data.cargoType.upper() in ["PER","BIO"] and data.fitoDocs.lower() != "si":
        status = "NO LISTO"
        detalles.append("❌ Certificado FDA / Fitosanitario faltante.")

    # Daños
    if data.damaged.lower() == "yes":
        status = "NO LISTO"
        detalles.append("❌ Bultos dañados, modificar embalaje antes de entregar.")

    # Overhang
    if data.overhang.lower() == "yes":
        status = "NO LISTO"
        detalles.append("❌ Carga sobresale de pallet, reestibar obligatoriamente.")

    return {"status": status, "detalles": detalles}

# -------------------------
# Endpoint de evaluación
# -------------------------
@app.post("/evaluar")
async def evaluar(request: Request):
    data_json = await request.json()
    data_model = CargoForm(**data_json)

    resultado_reglas = evaluar_reglas_duras(data_model)

    explicaciones = []
    for d in resultado_reglas["detalles"]:
        texto = await evaluar_ia({"detalle": d})
        explicaciones.append({"error": d, "explicacion": texto.get("detalles",[d])})

    log = {
        "fecha": str(datetime.datetime.now()),
        "awbMaster": data_model.awbMaster,
        "resultado": resultado_reglas,
        "explicaciones": explicaciones
    }
    with open("registro_evaluaciones.json","a",encoding="utf-8") as f:
        f.write(json.dumps(log,ensure_ascii=False)+"\n")

    return JSONResponse({
        "status": resultado_reglas["status"],
        "detalles": resultado_reglas["detalles"],
        "explicaciones": explicaciones
    })

# -------------------------
# Generación PDF secciones
# -------------------------
@app.post("/generar_pdf")
async def generar_pdf(data: CargoForm):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Función para agregar secciones
    def add_section(title, content: dict):
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.set_text_color(226,6,19)
        pdf.cell(0,10,title, ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Arial", '', 12)
        pdf.set_text_color(0,0,0)
        for k,v in content.items():
            pdf.multi_cell(0,8,f"{k}: {v}")
        pdf.ln(5)

    # Fase 1: Identificación y Seguridad
    fase1 = {k:getattr(data,k) for k in ["clientId","shipmentType","highValue","itnNumber","awbMaster","awbHouse","referenceNumber","originAirport","destinationAirport","departureDate"]}
    add_section("Fase 1: Identificación y Seguridad", fase1)

    # Fase 2: Anatomía de la carga
    fase2 = {k:getattr(data,k) for k in ["pieceHeight","numPieces","totalWeight","dimensions","needsShoring","nimf15","overhang","damaged"]}
    add_section("Fase 2: Anatomía de la Carga", fase2)

    # Fase 3: Contenidos críticos
    fase3 = {k:getattr(data,k) for k in ["cargoType","dgrDocs","fitoDocs"]}
    add_section("Fase 3: Contenidos Críticos", fase3)

    # Fase 4-8: Check final y embalaje
    fase4 = {k:getattr(data,k) for k in ["arrivalTime","packaging","labels","fragile","shipperName","shipperAddress","shipperPhone","consigneeName","consigneeAddress","consigneePhone","zipCode"]}
    add_section("Fase 4-8: Check-list y Logística", fase4)

    # Alertas de reglas duras
    fase_alertas = {f"Alerta {i+1}": d for i,d in enumerate(evaluar_reglas_duras(data)["detalles"])}
    add_section("Alertas y Recomendaciones AL CIELO", fase_alertas)

    filename = "frontend/reporte_smartcargo.pdf"
    pdf.output(filename)

    return {"url": "/static/reporte_smartcargo.pdf"}
