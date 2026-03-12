from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import os

app = FastAPI(title="SMARTGOSERVER Backend")

# Permitir CORS para pruebas con app.html
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambiar a dominios de producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas de JSON
BASE_DIR = "static"
CARGO_QUESTIONS_FILE = os.path.join(BASE_DIR, "cargo_questions.json")
CARGO_RULES_FILE = os.path.join(BASE_DIR, "cargo_rules.json")
AVIANCA_RULES_FILE = os.path.join(BASE_DIR, "avianca_rules.json")


# Cargar JSON al iniciar
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

cargo_questions = load_json(CARGO_QUESTIONS_FILE)
cargo_rules = load_json(CARGO_RULES_FILE)
avianca_rules = load_json(AVIANCA_RULES_FILE)


# Ruta principal para probar
@app.get("/")
async def root():
    return {"message": "SMARTGOSERVER Backend en línea"}


# Obtener preguntas
@app.get("/api/questions")
async def get_questions():
    return cargo_questions


# Obtener reglas
@app.get("/api/rules")
async def get_rules():
    return {
        "cargo_rules": cargo_rules,
        "avianca_rules": avianca_rules
    }


# Recibir respuestas y evaluar RFC
@app.post("/api/validate")
async def validate_rfc(request: Request):
    """
    Recibe respuestas en formato JSON:
    {
        "answers": [
            {"pregunta": "...", "respuesta": "..."},
            ...
        ]
    }
    """
    data = await request.json()
    answers = data.get("answers", [])
    bloqueos = []
    observaciones = []

    # Validaciones críticas según tus 24 preguntas
    for ans in answers:
        pregunta = ans.get("pregunta", "")
        respuesta = ans.get("respuesta", "")

        if "valor de su mercancía" in pregunta and respuesta == "Sí":
            bloqueos.append("Falta ITN para mercancía >$2,500 USD.")
        if "estibas de madera" in pregunta and respuesta == "No":
            bloqueos.append("Falta sello NIMF-15, cambio a pallet de plástico.")
        if "flejes" in pregunta and respuesta == "No":
            bloqueos.append("Falta flejes, riesgo de movimiento en vuelo.")
        if "altura del bulto" in pregunta and respuesta != "":
            try:
                h = float(respuesta)
                if h > avianca_rules["Avion"]["MaxPasajeroCm"]:
                    observaciones.append("Altura >63 pulgadas: reservar en Carguero")
                if h > avianca_rules["Avion"]["MaxCargueroCm"]:
                    bloqueos.append("Altura >96 pulgadas: no puede volar en ningún avión")
            except ValueError:
                bloqueos.append("Altura inválida: revisar dato")

        if "pieza pesa más de 150" in pregunta and respuesta == "Sí":
            observaciones.append("Usar base de madera (shoring) para distribuir peso")

        if "peso volumétrico" in pregunta and respuesta == "":
            observaciones.append("Calcular peso volumétrico antes del despacho")

        if "baterías de litio" in pregunta and respuesta == "Sí":
            bloqueos.append("Declarar UN3480/3481 y presentar 2 originales Shipper's Declaration")

        if "Zip Code" in pregunta and respuesta == "":
            bloqueos.append("Código postal incorrecto o incompleto")

    rfc_status = "SÍ" if not bloqueos else "NO"

    return JSONResponse({
        "RFC": rfc_status,
        "bloqueos": bloqueos,
        "observaciones": observaciones,
        "answers": answers
    })
