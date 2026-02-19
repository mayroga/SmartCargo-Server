# config.py
# Configuración global SMARTCARGO-AIPA

import os

# API Keys (pueden estar en Render o entorno local)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Configuración del app
APP_NAME = "SMARTCARGO-AIPA"
VERSION = "1.0"
TOTAL_PREGUNTAS = 21

# Límites técnicos de Avianca Cargo
MAX_HEIGHT_PASSENGER = 63   # pulgadas
MAX_HEIGHT_FREIGHTER = 96   # pulgadas
MAX_WEIGHT_SINGLE = 150     # kg por pieza sin shoring
PALLET_SIZES = {
    "PMC": {"base": (125,96), "height":96, "rating_kg":6800},
    "PAG": {"base": (125,88), "height":96, "rating_kg":4626},
    "PAJ": {"base": (125,88), "height":63, "rating_kg":4626},
    "PQA": {"base": (125,96), "height":96, "rating_kg":11340},
}

# Mensajes de alerta estándar
ALERTAS = {
    "peso_excede": "⚠ Peso excede 150kg: use shoring obligatorio.",
    "altura_carguero": "⚠ Altura >63'': solo en Freighter.",
    "altura_maxima": "❌ Altura excede límite de aviones Avianca.",
    "itn_faltante": "⚠ Ingrese ITN (AES) obligatorio. Multa federal $10,000."
}
