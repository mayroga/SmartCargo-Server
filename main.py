from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

app = FastAPI(title="AL CIELO - PRE-CHECK ADVISORY")

if not os.path.exists("static"): os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Reglas basadas en estándares Avianca/IATA
REGLAS = {
    "PREFIJO": "729", # Basado en la foto de Tampa Cargo / Avianca
    "FACTOR_VOL": 6000, # Factor estándar internacional para KG
    "MAX_H": 63.0, # Límite para aviones de pasajeros
    "DOCS_REQ": {
        "GENERAL": ["AWB Original", "Commercial Invoice", "Packing List"],
        "PHARMA": ["AWB", "Factura", "Temp Log", "Health Cert"],
        "DGR": ["AWB", "Shipper's Declaration", "MSDS", "UN Packing"],
    }
}

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/validar_precheck")
async def validar_precheck(data: dict):
    alertas = []
    explicaciones = []
    riesgos = []
    
    # Validar AWB
    awb = data.get("awb", "")
    if not awb.startswith("729") and not awb.startswith("045"):
        alertas.append("PREFIJO NO RECONOCIDO")
        explicaciones.append("El AWB no parece ser de Avianca/Tampa (045/729).")
        riesgos.append("Rechazo en counter por aerolínea incorrecta.")

    # Validar Piezas
    piezas = data.get("piezas", [])
    total_real = 0
    total_vol = 0
    
    for i, p in enumerate(piezas):
        try:
            l, w, h, cant = float(p['l']), float(p['w']), float(p['h']), int(p['cant'])
            peso_u = float(p['peso'])
            
            p_real = peso_u * cant
            # Cálculo de Volumen (L*W*H / 6000) * Cantidad
            p_vol = ((l * w * h) / REGLAS["FACTOR_VOL"]) * cant
            
            total_real += p_real
            total_vol += p_vol
            
            if h > REGLAS["MAX_H"]:
                alertas.append(f"PIEZA {i+1} DEMASIADO ALTA")
                explicaciones.append(f"Altura de {h}in excede el límite de bodega PAX.")
                riesgos.append("Vire de carga o costo extra por carguero (CAO).")
        except: continue

    # Reporte de daños
    obs = data.get("observaciones", "").upper()
    if any(x in obs for x in ["ROTO", "DAÑADO", "OLOR", "MOJADO"]):
        alertas.append("DAÑO FÍSICO DETECTADO")
        explicaciones.append("El reporte técnico indica mal estado del embalaje.")
        riesgos.append("La bodega rechazará la carga o exigirá carta de responsabilidad.")

    return {
        "status": "STOP - REVISAR" if alertas else "READY TO FLY",
        "peso_cobrable": round(max(total_real, total_vol), 2),
        "alertas": alertas,
        "explicaciones": explicaciones,
        "riesgos": riesgos
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
