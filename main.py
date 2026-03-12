import os
import json
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# SOLO ESTOS DOS JSON
CARGO_RULES_FILE = os.path.join(BASE_DIR, "static", "cargo_rules.json")
AVIANCA_RULES_FILE = os.path.join(BASE_DIR, "static", "avianca_rules.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


app = FastAPI()


# Permitir acceso desde app.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# CARGAR JSON
# =========================

cargo_rules = load_json(CARGO_RULES_FILE)
avianca_rules = load_json(AVIANCA_RULES_FILE)


# =========================
# ENDPOINTS
# =========================

@app.get("/")
def root():
    return {"status": "SmartCargo Server OK"}


@app.get("/questions")
def get_questions():
    """
    Devuelve las 24 preguntas desde avianca_rules.json
    """
    preguntas = avianca_rules.get("preguntas", [])
    return JSONResponse({"preguntas": preguntas})


@app.get("/cargo_rules")
def get_cargo_rules():
    return JSONResponse(cargo_rules)


@app.get("/avianca_rules")
def get_avianca_rules():
    return JSONResponse(avianca_rules)


# =========================
# VALIDADOR PRINCIPAL
# =========================

@app.post("/validate")
def validate_cargo(respuestas: dict):
    """
    Valida usando:

    - avianca_rules.json -> preguntas + alertas
    - cargo_rules.json -> reglas técnicas

    Devuelve:

    RFC = True / False
    alertas = []
    """

    resultado = {
        "RFC": True,
        "alertas": []
    }

    preguntas = avianca_rules.get("preguntas", [])

    # =========================
    # VALIDAR PREGUNTAS
    # =========================

    for q in preguntas:

        alerta = q.get("alerta_condicional")

        if not alerta:
            continue

        condicion = alerta.get("si")

        if not condicion:
            continue

        # ✔️ evaluación simple:
        # si la clave existe en respuestas y es True

        if condicion in respuestas and respuestas[condicion]:

            resultado["RFC"] = False

            resultado["alertas"].append({
                "id": q.get("id"),
                "pregunta": q.get("pregunta"),
                "accion": alerta.get("accion"),
                "tipo": alerta.get("tipo")
            })

    # =========================
    # VALIDAR REGLAS AVION
    # =========================

    avion = avianca_rules.get("Avion", {})

    max_pasajero = avion.get("MaxPasajeroCm", 160)
    max_carguero = avion.get("MaxCargueroCm", 244)

    alto = respuestas.get("alto")

    if alto:

        if alto > max_carguero:
            resultado["RFC"] = False
            resultado["alertas"].append({
                "tipo": "critica",
                "accion": "Altura excede carguero"
            })

        elif alto > max_pasajero:
            resultado["alertas"].append({
                "tipo": "warning",
                "accion": "Solo puede ir en carguero"
            })

    # =========================
    # VALIDAR CUT OFF
    # =========================

    cutoff = avianca_rules.get("Cutoff")

    llegada = respuestas.get("hora_llegada")

    if cutoff and llegada:

        if llegada > cutoff:
            resultado["RFC"] = False
            resultado["alertas"].append({
                "tipo": "critica",
                "accion": "Llegada después del cutoff"
            })

    return JSONResponse(resultado)
