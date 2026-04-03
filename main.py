from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

app = FastAPI(title="SMARTCARGO-SERVER")

if not os.path.exists("static"): os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- PROTOCOLOS DE AUDITORÍA TÉCNICA ---
REGLAS_AVIANCA = {
    "MAX_ALTURA_PAX": 63.0,
    "PREFIJO": "045",
    "RATIO_VOL": 166,
    "DOCS_OBLIGATORIOS": {
        "GENERAL": ["AWB", "Factura Original", "Packing List"],
        "DGR": ["AWB", "Shipper's Declaration", "MSDS", "Factura Original"],
        "DRY_ICE": ["AWB", "Etiqueta Clase 9", "DGD de Hielo Seco"],
        "VALORES": ["AWB", "Manifiesto de Valores", "Custodia Armada"],
        "HUMAN_REMAINS": ["AWB", "Acta Defunción", "Certificado Embalsamamiento"]
    }
}

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html", "r", encoding="utf-8") as f: return f.read()

@app.post("/api/validar_carga")
async def validar_carga(data: dict):
    alertas = []
    explicaciones = []
    
    # 1. Identificación y Tráfico
    awb = data.get("awb", "")
    trafico = data.get("tipo_trafico", "") # COMAT, TRANSFER, INTERLINE, PAX, CAO
    
    if not awb.startswith(REGLAS_AVIANCA["PREFIJO"]):
        alertas.append("PREFIJO INVÁLIDO")
        explicaciones.append("El AWB no comienza con 045. Avianca Cargo rechazará la recepción. Multa potencial por intento de ingreso fallido a zona estéril.")

    # 2. Auditoría de Documentos (Lo que el cliente escribe y marca)
    naturaleza = data.get("naturaleza", "GENERAL")
    docs_escritos = data.get("docs_texto", "").upper()
    docs_marcados = data.get("docs_check", [])
    
    requeridos = REGLAS_AVIANCA["DOCS_OBLIGATORIOS"].get(naturaleza, [])
    
    for doc in requeridos:
        if doc.upper() not in docs_escritos and doc not in docs_marcados:
            alertas.append(f"FALTA: {doc}")
            explicaciones.append(f"Sin {doc}, Aduana (CBP) retendrá la mercancía. Retraso estimado: 48-72h. Multas administrativas por falta de soporte legal.")

    # 3. Auditoría Física (Pieza por Pieza)
    piezas = data.get("piezas", [])
    p_real_total = 0
    p_vol_total = 0
    
    for i, p in enumerate(piezas):
        l, w, h, cant = float(p['l']), float(p['w']), float(p['h']), int(p['cant'])
        p_real = float(p['p_real']) * cant
        vol_total = (l * w * h * cant) / REGLAS_AVIANCA["RATIO_VOL"]
        
        p_real_total += p_real
        p_vol_total += vol_total
        
        if h > REGLAS_AVIANCA["MAX_ALTURA_PAX"]:
            alertas.append(f"EXCESO ALTURA - PIEZA {i+1}")
            explicaciones.append(f"Altura de {h} pulg supera el límite de avión PAX (Belly). La carga será 'Vire' (Rechazo) a menos que se transfiera a vuelo Carguero (CAO).")

    return {
        "status": "RECHAZADO / HOLD" if alertas else "FLY READY",
        "peso_cobrable": round(max(p_real_total, p_vol_total), 2),
        "alertas": alertas,
        "explicaciones": explicaciones
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
