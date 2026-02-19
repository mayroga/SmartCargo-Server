from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

app = FastAPI()

# CORS para frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Estructura de cada respuesta enviada desde frontend
class Answer(BaseModel):
    phase: str
    question: str
    answer: str

# Reglas críticas para determinar si la carga puede volar
CRITICAL_RULES = [
    {"question_contains": "altura", "max_value": 96, "message": "Carga excede altura máxima permitida."},
    {"question_contains": "peso", "max_value": 150, "message": "Carga excede peso máximo sin shoring."},
    {"question_contains": "ITN", "must_have": True, "message": "ITN obligatorio para valor > $2,500 USD."},
    {"question_contains": "NIMF-15", "must_have": True, "message": "Falta sello NIMF-15. Debe cambiar pallet o certificarlo."},
    {"question_contains": "baterías de litio", "must_have": True, "message": "Debe declarar DGR y Shipper's Declaration."},
    {"question_contains": "Overhang", "max_value": 0, "message": "Carga sobresale del pallet. Re-estibar."},
]

@app.post("/evaluate")
async def evaluate(answers: list[Answer]):
    report = []
    can_fly = True

    for ans in answers:
        alert = None
        suggestion = None
        # Validaciones específicas numéricas
        try:
            if "altura" in ans.question.lower():
                altura = float(ans.answer)
                if altura > 63 and altura <= 96:
                    suggestion = "Debe volar en Freighter."
                elif altura > 96:
                    alert = "Carga NO entra en ningún avión de Avianca."
                    can_fly = False
            if "peso" in ans.question.lower():
                peso = float(ans.answer)
                if peso > 150:
                    suggestion = "Usar base de madera (shoring) obligatoria."
        except:
            pass
        
        # Validaciones de sí/no u obligatorias
        for rule in CRITICAL_RULES:
            if rule["question_contains"].lower() in ans.question.lower():
                if "must_have" in rule:
                    if ans.answer.lower() in ["no", ""]:
                        alert = rule["message"]
                        can_fly = False
                        suggestion = "Rectificar antes de enviar al counter."

        report.append({
            "phase": ans.phase,
            "question": ans.question,
            "answer": ans.answer,
            "alert": alert,
            "suggestion": suggestion
        })

    final_status = "Carga puede volar" if can_fly else "Carga NO puede volar"

    return {"report": report, "status": final_status}

@app.post("/generate_pdf")
async def generate_pdf(request: Request):
    data = await request.json()
    report = data.get("report", [])
    status = data.get("status", "")

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    y = height - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Reporte de Inspección SMARTCARGO-AIPA")
    y -= 30
    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Estado Final: {status}")
    y -= 30

    for item in report:
        if y < 50:
            c.showPage()
            y = height - 40
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, f"Fase: {item['phase']}")
        y -= 15
        c.setFont("Helvetica", 10)
        c.drawString(50, y, f"Pregunta: {item['question']}")
        y -= 15
        c.drawString(50, y, f"Respuesta: {item['answer']}")
        y -= 15
        if item.get("alert"):
            c.setFillColorRGB(1,0,0)
            c.drawString(50, y, f"ALERTA: {item['alert']}")
            c.setFillColorRGB(0,0,0)
            y -= 15
        if item.get("suggestion"):
            c.setFillColorRGB(0,0,1)
            c.drawString(50, y, f"Sugerencia: {item['suggestion']}")
            c.setFillColorRGB(0,0,0)
            y -= 15
        y -= 10

    c.save()
    buffer.seek(0)
    return FileResponse(buffer, media_type='application/pdf', filename="reporte_smartcargo.pdf")
