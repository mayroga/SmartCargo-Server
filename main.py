from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fpdf import FPDF
import os, re, json, datetime, httpx

app = FastAPI(title="SMARTCARGO CERTIFIED")

# ---------------- STATIC ----------------
if not os.path.exists("frontend"):
    os.makedirs("frontend")

app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def root():
    return FileResponse("frontend/index.html")

# ---------------- API KEYS ----------------
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# ---------------- REGEX VALIDATION ----------------
AWB_REGEX = r"^\d{3}-\d{8}$"
ZIP_REGEX = r"^\d{5}$"
IATA_REGEX = r"^[A-Z]{3}$"

# ---------------- MODEL ----------------
class CargoForm(BaseModel):
    clientId:str|None=""
    highValue:str|None=""
    itnNumber:str|None=""
    awbMaster:str|None=""
    originAirport:str|None=""
    destinationAirport:str|None=""
    pieceHeight:float|None=0
    pieceWeight:float|None=0
    totalWeight:float|None=0
    needsShoring:str|None=""
    nimf15:str|None=""
    cargoType:str|None=""
    dgrDocs:str|None=""
    fitoDocs:str|None=""
    zipCode:str|None=""

# ---------------- MOTOR POR AUTORIDAD ----------------
def evaluar(data:CargoForm):
    resultado = {
        "status":"VUELA",
        "autoridades":{
            "CBP":[],
            "TSA":[],
            "IATA":[],
            "USDA":[]
        }
    }

    # -------- CBP --------
    if data.highValue=="yes" and not data.itnNumber:
        resultado["autoridades"]["CBP"].append(
            "❌ Valor >2500 USD requiere ITN/AES. Fuente: CBP 15 CFR §30."
        )
        resultado["status"]="NO VUELA"

    if not re.match(ZIP_REGEX,data.zipCode or ""):
        resultado["autoridades"]["CBP"].append(
            "❌ ZIP inválido USA (5 dígitos requeridos)."
        )
        resultado["status"]="NO VUELA"

    # -------- TSA --------
    if not data.clientId:
        resultado["autoridades"]["TSA"].append(
            "⚠️ Known Shipper no validado. Requiere inspección 48h."
        )

    # -------- IATA --------
    if not re.match(AWB_REGEX,data.awbMaster or ""):
        resultado["autoridades"]["IATA"].append(
            "❌ Formato AWB inválido (123-12345678)."
        )
        resultado["status"]="NO VUELA"

    if not re.match(IATA_REGEX,data.originAirport or ""):
        resultado["autoridades"]["IATA"].append(
            "❌ Código aeropuerto origen inválido (3 letras IATA)."
        )
        resultado["status"]="NO VUELA"

    if data.pieceHeight:
        if data.pieceHeight>96:
            resultado["autoridades"]["IATA"].append(
                "❌ Altura >96 in. RECHAZO TOTAL."
            )
            resultado["status"]="NO VUELA"
        elif data.pieceHeight>63:
            resultado["autoridades"]["IATA"].append(
                "⚠️ Altura >63 in. Main Deck Only (Carguero)."
            )

    if data.pieceWeight and data.pieceWeight>150 and data.needsShoring!="si":
        resultado["autoridades"]["IATA"].append(
            "❌ >150kg requiere shoring (tablas 2in)."
        )
        resultado["status"]="NO VUELA"

    if data.cargoType=="DGR" and data.dgrDocs!="si":
        resultado["autoridades"]["IATA"].append(
            "❌ DGR sin 2 originales Shipper's Declaration (IATA 4.2)."
        )
        resultado["status"]="NO VUELA"

    # -------- USDA --------
    if data.nimf15!="si":
        resultado["autoridades"]["USDA"].append(
            "❌ NIMF-15 obligatorio en pallets de madera."
        )
        resultado["status"]="NO VUELA"

    return resultado

# ---------------- IA ----------------
async def explicar(texto):
    prompt=f"Explica legalmente y solución práctica: {texto}"
    try:
        async with httpx.AsyncClient() as client:
            r=await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization":f"Bearer {OPENAI_KEY}"},
                json={"model":"gpt-4o-mini",
                      "messages":[{"role":"user","content":prompt}]}
            )
            return r.json()["choices"][0]["message"]["content"]
    except:
        try:
            async with httpx.AsyncClient() as client:
                r=await client.post(
                    "https://api.gemini.com/v1/generate",
                    headers={"Authorization":f"Bearer {GEMINI_KEY}"},
                    json={"prompt":prompt}
                )
                return r.json().get("output","IA no disponible")
        except:
            return "IA no disponible"

# ---------------- ENDPOINT EVALUAR ----------------
@app.post("/evaluar")
async def evaluar_carga(data:CargoForm):
    resultado=evaluar(data)

    explicaciones=[]
    for aut,items in resultado["autoridades"].items():
        for item in items:
            texto=await explicar(item)
            explicaciones.append({"autoridad":aut,"hallazgo":item,"explicacion":texto})

    return JSONResponse({
        "status":resultado["status"],
        "autoridades":resultado["autoridades"],
        "explicaciones":explicaciones
    })

# ---------------- PDF ----------------
@app.post("/generar_pdf")
async def generar_pdf(data:CargoForm):
    resultado=evaluar(data)

    pdf=FPDF()
    pdf.add_page()
    pdf.set_font("Arial","B",40)
    pdf.set_text_color(200,0,0 if resultado["status"]=="NO VUELA" else 150)
    pdf.rotate(45,50,150)
    pdf.text(30,150,resultado["status"])
    pdf.rotate(0)

    pdf.set_font("Arial","",12)
    pdf.ln(40)

    for aut,items in resultado["autoridades"].items():
        pdf.cell(0,10,aut,ln=True)
        for i in items:
            pdf.multi_cell(0,8,"- "+i)

    filename="frontend/certificado.pdf"
    pdf.output(filename)
    return {"url":"/static/certificado.pdf"}
