from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fpdf import FPDF
from utils.rules import evaluar_reglas_duras
from utils.ai_engine import explicar_con_ia
import datetime
import os
import json

app = FastAPI(title="SMARTCARGO INFALIBLE")

# -------------------------
# Static
# -------------------------
if not os.path.exists("frontend"):
    os.makedirs("frontend")

app.mount("/static", StaticFiles(directory="frontend"), name="static")


# -------------------------
# Modelo de Evaluación
# -------------------------
class CargoForm(BaseModel):
    clientId: str
    shipmentType: str
    highValue: str
    itnNumber: str | None = ""
    zipCheck: str
    cargoType: str
    dgrDocs: str | None = ""
    fitoDocs: str | None = ""
    pieceHeight: float
    needsShoring: str
    nimf15: str
    damaged: str
    overhang: str


# -------------------------
# Página Principal
# -------------------------
@app.get("/", response_class=HTMLResponse)
async def home():
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        return f.read()


# -------------------------
# Evaluación Principal
# -------------------------
@app.post("/evaluar")
async def evaluar(data: CargoForm):

    resultado = evaluar_reglas_duras(data)

    # IA explica cada hallazgo
    explicaciones = []
    for item in resultado["detalles"]:
        texto_ia = await explicar_con_ia(item)
        explicaciones.append({
            "error": item,
            "explicacion": texto_ia
        })

    log = {
        "fecha": str(datetime.datetime.now()),
        "cliente": data.clientId,
        "resultado": resultado,
        "explicaciones": explicaciones
    }

    with open("registro_evaluaciones.json", "a") as f:
        f.write(json.dumps(log) + "\n")

    return JSONResponse({
        "status": resultado["status"],
        "detalles": resultado["detalles"],
        "explicaciones": explicaciones
    })


# -------------------------
# PDF Profesional Completo
# -------------------------
@app.post("/generar_pdf")
async def generar_pdf(data: CargoForm):

    resultado = evaluar_reglas_duras(data)

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(226, 6, 19)
    pdf.cell(0, 10, "SMARTCARGO - PRE COUNTER REPORT", ln=True, align="C")

    pdf.set_font("Arial", '', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"Generado: {datetime.datetime.now()}", ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 14)

    color = (40,167,69) if resultado["status"] == "VUELA" else (220,53,69)
    pdf.set_fill_color(*color)
    pdf.set_text_color(255,255,255)
    pdf.cell(0, 12, resultado["status"], ln=True, align="C", fill=True)

    pdf.ln(5)
    pdf.set_text_color(0,0,0)
    pdf.set_font("Arial", '', 11)

    for d in resultado["detalles"]:
        pdf.multi_cell(0, 8, f"- {d}")

    filename = "frontend/reporte_smartcargo.pdf"
    pdf.output(filename)

    return {"url": "/static/reporte_smartcargo.pdf"}
