import os
import json
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CARGO_RULES_FILE = os.path.join(BASE_DIR, "static", "cargo_rules.json")
AVIANCA_RULES_FILE = os.path.join(BASE_DIR, "static", "avianca_rules.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ✅ SOLO ESTOS DOS
cargo_rules = load_json(CARGO_RULES_FILE)
avianca_rules = load_json(AVIANCA_RULES_FILE)


@app.get("/")
def root():
    return {"status": "SmartCargo Server OK"}


@app.get("/questions")
def get_questions():
    return JSONResponse({
        "preguntas": avianca_rules.get("preguntas", [])
    })


@app.get("/cargo_rules")
def get_cargo_rules():
    return JSONResponse(cargo_rules)


@app.get("/avianca_rules")
def get_avianca_rules():
    return JSONResponse(avianca_rules)


@app.post("/validate")
def validate_cargo(respuestas: dict):

    resultado = {
        "RFC": True,
        "alertas": []
    }

    preguntas = avianca_rules.get("preguntas", [])

    for q in preguntas:

        alerta = q.get("alerta_condicional")

        if not alerta:
            continue

        condicion = alerta.get("si")

        if condicion in respuestas and respuestas[condicion]:

            resultado["RFC"] = False

            resultado["alertas"].append({
                "id": q.get("id"),
                "pregunta": q.get("pregunta"),
                "accion": alerta.get("accion"),
                "tipo": alerta.get("tipo")
            })

    # validar altura

    avion = avianca_rules.get("Avion", {})

    alto = respuestas.get("alto")

    if alto:

        if alto > avion.get("MaxCargueroCm", 244):

            resultado["RFC"] = False

            resultado["alertas"].append({
                "tipo": "critica",
                "accion": "Altura excede carguero"
            })

    return JSONResponse(resultado)
