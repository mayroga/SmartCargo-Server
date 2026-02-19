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
# Configuración de FastAPI
# -------------------------
app = FastAPI(title="SMARTCARGO INFALIBLE")

# Permitir CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Directorio Frontend
if not os.path.exists("frontend"):
    os.makedirs("frontend")
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# -------------------------
# API Keys
# -------------------------
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# -------------------------
# Modelo de datos
# -------------------------
class CargoForm(BaseModel):
    awbMaster: str
    awbHouse: str | None = ""
    shipperName: str
    shipperAddress: str
    shipperPhone: str
    consigneeName: str
    consigneeAddress: str
    consigneePhone: str
    referenceNumber: str
    originAirport: str
    destinationAirport: str
    departureDate: str
    cargoType: str
    dgrDocs: str | None = ""
    fitoDocs: str | None = ""
    highValue: str
    itnNumber: str | None = ""
    zipCode: str
    numPieces: int
    totalWeight: float
    dimensions: str
    pieceHeight: float
    needsShoring: str
    nimf15: str
    damaged: str
    overhang: str

# -------------------------
# Página principal
# -------------------------
@app.get("/", response_class=HTMLResponse)
async def home():
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        return f.read()

# -------------------------
# Función IA: OpenAI principal, Gemini respaldo
# -------------------------
async def evaluar_ia(data: dict):
    prompt = f"""
Evaluar pre-check de carga Avianca Cargo con estos datos:
{json.dumps(data, indent=2)}

Devuelve JSON con:
- status: LISTO PARA VOLAR / NO LISTO
- detalle: lista de explicaciones y correcciones necesarias
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
            output = r["choices"][0]["message"]["content"]
            return eval(output)
    except Exception as e_openai:
        # Si falla OpenAI, usamos Gemini
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.gemini.com/v1/generate",
                    headers={"Authorization": f"Bearer {GEMINI_KEY}"},
                    json={"prompt": prompt, "max_tokens":500}
                )
                r = resp.json()
                return eval(r.get("output","{'status':'ERROR IA','detalle':['Gemini no respondió']}"))
        except Exception as e_gemini:
            return {"status":"ERROR IA","detalle":[str(e_openai), str(e_gemini)]}

# -------------------------
# Función reglas duras (simulación real)
# -------------------------
def evaluar_reglas_duras(data: CargoForm):
    detalles = []
    status = "LISTO PARA VOLAR"

    # Peso máximo
    if data.totalWeight > 10000:
        status = "NO LISTO"
        detalles.append("❌ Peso total excede límite de avión.")

    # Altura pieza
    if data.pieceHeight > 96:
        status = "NO LISTO"
        detalles.append("❌ Altura pieza excede límite, no entra en avión.")

    elif data.pieceHeight > 63:
        detalles.append("⚠️ Solo entra en avión carguero (Main Deck).")

    # Shoring
    if data.needsShoring == "si":
        detalles.append("🛠 Shoring requerido para piezas >150kg.")

    # DGR
    if data.cargoType == "DGR" and data.dgrDocs != "si":
        status = "NO LISTO"
        detalles.append("❌ Faltan Shipper's Declaration originales.")

    # PER / FDA
    if data.cargoType == "PER" and data.fitoDocs != "si":
        status = "NO LISTO"
        detalles.append("❌ Certificado FDA/Fitosanitario faltante.")

    # ITN
    if data.highValue == "yes" and not data.itnNumber:
        status = "NO LISTO"
        detalles.append("❌ ITN/AES requerido para valor >$2,500 USD.")

    # Daños
    if data.damaged == "yes":
        status = "NO LISTO"
        detalles.append("❌ Cajas dañadas o mojadas.")

    return {"status": status, "detalles": detalles}

# -------------------------
# Endpoint principal de evaluación
# -------------------------
@app.post("/evaluar")
async def evaluar(request: Request):
    data_json = await request.json()
    data_model = CargoForm(**data_json)

    # Evaluación reglas duras
    resultado_reglas = evaluar_reglas_duras(data_model)

    # Explicaciones IA
    explicaciones = []
    for d in resultado_reglas["detalles"]:
        texto = await evaluar_ia({"detalle": d})
        explicaciones.append({"error": d, "explicacion": texto.get("detalle",[d])})

    # Log completo
    log = {
        "fecha": str(datetime.datetime.now()),
        "awbMaster": data_model.awbMaster,
        "resultado": resultado_reglas,
        "explicaciones": explicaciones
    }
    with open("registro_evaluaciones.json", "a", encoding="utf-8") as f:
        f.write(json.dumps(log, ensure_ascii=False) + "\n")

    return JSONResponse({
        "status": resultado_reglas["status"],
        "detalle": resultado_reglas["detalles"],
        "explicaciones": explicaciones
    })

# -------------------------
# Generación de PDF completo
# -------------------------
@app.post("/generar_pdf")
async def generar_pdf(data: CargoForm):
    pdf = FPDF()
    pdf.add_page()

    # Título
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(226,6,19)
    pdf.cell(0,10,"SMARTCARGO - PRE COUNTER REPORT", ln=True, align="C")

    pdf.set_font("Arial", '', 10)
    pdf.set_text_color(0,0,0)
    pdf.cell(0,10,f"Generado: {datetime.datetime.now()}", ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 14)
    color = (40,167,69) if evaluar_reglas_duras(data)["status"]=="LISTO PARA VOLAR" else (220,53,69)
    pdf.set_fill_color(*color)
    pdf.set_text_color(255,255,255)
    pdf.cell(0,12,evaluar_reglas_duras(data)["status"], ln=True, align="C", fill=True)

    pdf.ln(5)
    pdf.set_font("Arial", '', 11)
    fields = vars(data)
    for key, value in fields.items():
        pdf.multi_cell(0,8,f"{key}: {value}")

    # Detalles de reglas duras
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(0,0,0)
    pdf.cell(0,10,"Detalles y alertas:", ln=True)
    for d in evaluar_reglas_duras(data)["detalles"]:
        pdf.multi_cell(0,8,f"- {d}")

    filename = "frontend/reporte_smartcargo.pdf"
    pdf.output(filename)
    return {"url": "/static/reporte_smartcargo.pdf"}
