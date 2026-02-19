from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fpdf import FPDF
import os
import datetime
import json
import httpx
from utils.rules import evaluar_reglas_duras
from utils.ai_engine import explicar_con_ia

# -------------------------
# Inicialización
# -------------------------
app = FastAPI(title="SMARTCARGO INFALIBLE")

# Carpeta frontend
if not os.path.exists("frontend"):
    os.makedirs("frontend")

# Montar carpeta estática
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Permitir CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Llaves IA
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# -------------------------
# Modelo de datos
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
    hasManifest: str | None = "si"

# -------------------------
# Página Principal
# -------------------------
@app.get("/", response_class=HTMLResponse)
async def home():
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        return f.read()

# -------------------------
# Función IA
# -------------------------
async def evaluar_ia(data: dict):
    prompt = f"""
    Evaluar pre-check de carga Avianca Cargo según estos datos:
    {data}

    Devuelve un JSON con:
    {{
        "status": "LISTO PARA VOLAR / NO LISTO",
        "detalle": ["explicación de cada problema o alerta"]
    }}
    """
    # Intentamos Gemini
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://api.gemini.com/v1/generate",
                headers={"Authorization": f"Bearer {GEMINI_KEY}"},
                json={"prompt": prompt, "max_tokens":500}
            )
            result = resp.json()
            return result.get("output")
    except Exception:
        # Si falla Gemini, usamos OpenAI
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENAI_KEY}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role":"user","content":prompt}],
                        "temperature":0
                    }
                )
                result = resp.json()
                # Convertimos respuesta en dict
                return eval(result["choices"][0]["message"]["content"])
        except Exception as e2:
            return {"status":"ERROR IA","detalle":[str(e2)]}

# -------------------------
# Evaluación Principal
# -------------------------
@app.post("/evaluar")
async def evaluar(data: CargoForm):
    # Reglas duras
    resultado = evaluar_reglas_duras(data)

    # IA explica cada hallazgo
    explicaciones = []
    for item in resultado["detalles"]:
        texto_ia = await explicar_con_ia(item)
        explicaciones.append({
            "error": item,
            "explicacion": texto_ia
        })

    # Evaluación IA general para status y detalle
    ia_result = await evaluar_ia(data.dict())
    if ia_result and "status" in ia_result:
        resultado["status"] = ia_result["status"]
        resultado["detalles"] = ia_result.get("detalle", resultado["detalles"])

    # Guardar log
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
# PDF Profesional
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

    # Estado con color
    color = (40,167,69) if "LISTO" in resultado["status"] else (220,53,69)
    pdf.set_fill_color(*color)
    pdf.set_text_color(255,255,255)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 12, resultado["status"], ln=True, align="C", fill=True)
    pdf.ln(5)

    pdf.set_text_color(0,0,0)
    pdf.set_font("Arial", '', 11)
    for d in resultado["detalles"]:
        pdf.multi_cell(0, 8, f"- {d}")

    filename = "frontend/reporte_smartcargo.pdf"
    pdf.output(filename)

    return {"url": "/static/reporte_smartcargo.pdf"}
