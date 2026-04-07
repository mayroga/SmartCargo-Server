from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# =========================
# DATA MODEL
# =========================
class CargoRequest(BaseModel):
    dg: str = "no"
    msds: str = "no"
    shipper: str = "no"
    aircraft: str = "cargo"
    movement: str = "local"
    special: str = "no"
    pieces: list = []


# =========================
# ENGINE LOGIC
# =========================
def check_cargo(data):

    errors = []
    warnings = []
    score = 100

    if data.dg == "yes":

        if data.msds == "no":
            errors.append("Falta MSDS")
            score -= 30

        if data.shipper == "no":
            errors.append("Falta declaración shipper")
            score -= 40

        if data.aircraft == "passenger":
            errors.append("DG no permitido en pasajeros")
            score -= 50

    if data.movement not in ["local", "transfer", "comat"]:
        errors.append("Movimiento inválido")
        score -= 40

    if data.special == "yes":
        warnings.append("Carga especial requiere revisión")
        score -= 10

    total_weight = 0
    total_volume = 0

    for p in data.pieces:
        try:
            l = float(p.get("length", 0))
            w = float(p.get("width", 0))
            h = float(p.get("height", 0))
            kg = float(p.get("weight", 0))

            volume = (l * w * h) / 6000

            total_weight += kg
            total_volume += volume

        except:
            errors.append("Error en piezas")

    score = max(0, min(score, 100))

    if len(errors) == 0 and score >= 80:
        status = "LISTO"
        level = "green"
    elif score >= 50:
        status = "REVISAR"
        level = "yellow"
    else:
        status = "NO LISTO"
        level = "red"

    return {
        "status": status,
        "level": level,
        "score": score,
        "errors": errors,
        "warnings": warnings,
        "total_weight": total_weight,
        "total_volume": total_volume
    }


# =========================
# API ENDPOINT
# =========================
@app.post("/check")
def check(request: CargoRequest):
    return check_cargo(request)
