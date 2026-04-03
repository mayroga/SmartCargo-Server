from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

app = FastAPI(title="AL CIELO - ENGINE V3")

if not os.path.exists("static"): os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Parámetros Técnicos de Carga Aérea (MIA/VCP/BOG)
REGLAS = {
    "PREFIJOS_OK": ["045", "729"],
    "FACTOR_VOL": 6000, 
    "LIMITE_H_PAX": 63.0,
    "CRITICOS": ["DAÑO", "ROTO", "OLOR", "FUGA", "MOJADO", "SIN SELLO", "ABIERTO"]
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
    
    # Validación de Prefijo (Seguridad Documental)
    awb = data.get("awb", "")
    if not any(awb.startswith(p) for p in REGLAS["PREFIJOS_OK"]):
        alertas.append("PREFIJO NO AUTORIZADO")
        explicaciones.append("El AWB no inicia con 045 o 729 (Avianca/Tampa).")
        riesgos.append("Rechazo inmediato en el counter de recepción.")

    # Auditoría Física de Piezas
    piezas = data.get("piezas", [])
    total_real = 0
    total_vol = 0
    
    for i, p in enumerate(piezas):
        try:
            l, w, h, cant = float(p['l']), float(p['w']), float(p['h']), int(p['cant'])
            peso_u = float(p['peso'])
            
            total_real += (peso_u * cant)
            # Cálculo automático de volumen
            vol_calc = ((l * w * h) / REGLAS["FACTOR_VOL"]) * cant
            total_vol += vol_calc
            
            if h > REGLAS["LIMITE_H_PAX"]:
                alertas.append(f"ALTURA EXCEDIDA - PIEZA {i+1}")
                explicaciones.append(f"Altura de {h}in supera la capacidad de Bellies (Avión PAX).")
                riesgos.append("La carga será 'vire' (offload) o requerirá freighter (CAO).")
        except: continue

    # Evaluación de Riesgo por Observaciones
    obs = data.get("observaciones", "").upper()
    for palabra in REGLAS["CRITICOS"]:
        if palabra in obs:
            alertas.append(f"ANOMALÍA DETECTADA: {palabra}")
            explicaciones.append(f"El reporte indica presencia de {palabra.lower()} en el embalaje.")
            riesgos.append("Responsabilidad legal y posible rechazo por seguridad TSA/CBP.")

    status = "STOP - RECHAZADO" if alertas else "READY TO FLY"
    
    return {
        "status": status,
        "p_cobrable": round(max(total_real, total_vol), 2),
        "alertas": alertas,
        "explicaciones": explicaciones,
        "riesgos": riesgos
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
