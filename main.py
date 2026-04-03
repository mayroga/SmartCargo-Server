from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

app = FastAPI(title="SMARTCARGO OS")

if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

REGLAS = {
    "RATIO_VOL": 166,
    "MAX_H_PAX": 63
}

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/validar")
async def validar(data: dict):

    alertas = []
    explicaciones = []
    riesgos = []

    piezas = data.get("piezas", [])

    total_real = 0
    total_vol = 0

    for i, p in enumerate(piezas):
        l = float(p.get("l",0))
        w = float(p.get("w",0))
        h = float(p.get("h",0))
        peso = float(p.get("peso",0))
        cant = int(p.get("cant",1))

        total_real += peso * cant
        total_vol += (l*w*h*cant)/REGLAS["RATIO_VOL"]

        if h > REGLAS["MAX_H_PAX"]:
            alertas.append(f"EXCESO ALTURA PIEZA {i+1}")
            explicaciones.append("Excede límite belly aircraft")
            riesgos.append("Reubicación a carguero o rechazo")

    p_cobrable = max(total_real, total_vol)

    return {
        "status": "FLY READY (ASESORADO)" if not alertas else "CONDICIONAL (REVISAR)",
        "peso_real": round(total_real,2),
        "peso_vol": round(total_vol,2),
        "peso_cobrable": round(p_cobrable,2),
        "alertas": alertas,
        "explicaciones": explicaciones,
        "riesgos": riesgos
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
