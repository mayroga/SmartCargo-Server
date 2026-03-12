import os
import json
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CARGO_QUESTIONS_FILE = os.path.join(BASE_DIR, "static", "cargo_questions.json")
CARGO_RULES_FILE = os.path.join(BASE_DIR, "static", "cargo_rules.json")
AVIANCA_RULES_FILE = os.path.join(BASE_DIR, "static", "avianca_rules.json")

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

app = FastAPI()

# Permitir que app.js acceda
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

cargo_questions = load_json(CARGO_QUESTIONS_FILE)
cargo_rules = load_json(CARGO_RULES_FILE)
avianca_rules = load_json(AVIANCA_RULES_FILE)

@app.get("/questions")
def get_questions():
    return JSONResponse(cargo_questions)

@app.get("/cargo_rules")
def get_cargo_rules():
    return JSONResponse(cargo_rules)

@app.get("/avianca_rules")
def get_avianca_rules():
    return JSONResponse(avianca_rules)

@app.post("/validate")
def validate_cargo(respuestas: dict):
    """
    Aquí va la lógica que combina:
    - cargo_questions
    - cargo_rules
    - avianca_rules
    para determinar si la carga es RFC o hay alertas críticas.
    """
    resultado = {"RFC": True, "alertas": []}

    # Ejemplo de validación simple
    for q in cargo_questions["preguntas"]:
        alerta = q.get("alerta_condicional")
        if alerta:
            # Si la condición se cumple en las respuestas, bloquea RFC
            condicion = alerta.get("si")
            # Para demo, evaluamos si la clave existe en respuestas
            if condicion in respuestas and respuestas[condicion]:
                resultado["RFC"] = False
                resultado["alertas"].append({
                    "pregunta": q["pregunta"],
                    "accion": alerta["accion"],
                    "tipo": alerta["tipo"]
                })

    return JSONResponse(resultado)
