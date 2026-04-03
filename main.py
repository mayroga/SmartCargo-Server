from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

app = FastAPI(title="AL CIELO | SMARTCARGO-SERVER")

if not os.path.exists("static"): os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- PROTOCOLOS DE ASESORÍA TÉCNICA (AVIANCA CARGO / IATA / DOT / CBP) ---
REGLAS_AVIANCA = {
    "PREFIJO": "045",
    "RATIO_VOL": 166,
    "LIMITES_ALTURA": {
        "PAX_BELLY": 63.0,
        "CAO_MAIN_DECK": 96.0,
        "COMAT_MAX": 45.0
    },
    "MATRIZ_DOCUMENTAL": {
        "GENERAL": ["AWB", "Factura Comercial", "Packing List"],
        "DGR": ["AWB", "Shipper's Declaration", "MSDS", "Etiqueta Clase", "Factura"],
        "PER": ["AWB", "Certificado Fitosanitario", "Guía de Temperatura", "Invoice"],
        "VAL": ["AWB", "Manifiesto de Valores", "Custodia Armada", "Sello de Seguridad"],
        "HUM": ["AWB", "Acta Defunción", "Certificado Embalsamamiento", "Permiso Tránsito"],
        "AVI": ["AWB", "Certificado Veterinario", "Declaración de Contenedor IATA"]
    },
    "DESCRIPCIONES_PROHIBIDAS": ["GENERAL CARGO", "SACO", "CAJA", "MERCANCIA", "STC", "PALLET"]
}

@app.get("/", response_class=HTMLResponse)
async def home():
    try:
        with open("static/app.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "ERROR: static/app.html no encontrado. Verifique la ruta del servidor."

@app.post("/api/validar_carga")
async def validar_carga(data: dict):
    alertas = []
    explicaciones = []
    riesgos_legales = []
    
    # 1. AUDITORÍA DE IDENTIDAD (AWB & TSA)
    awb = data.get("awb", "").strip()
    known_shipper = data.get("known_shipper", False)
    
    if not awb.startswith(REGLAS_AVIANCA["PREFIJO"]):
        alertas.append("PREFIJO DE AEROLÍNEA ERRÓNEO")
        explicaciones.append(f"El prefijo no es de Avianca (045).")
        riesgos_legales.append("Rechazo inmediato en counter y pérdida de reserva.")

    if not known_shipper:
        alertas.append("SHIPPER DESCONOCIDO (TSA ALERT)")
        explicaciones.append("Carga sujeta a inspección física 100% o ETD.")
        riesgos_legales.append("Retraso mínimo de 24h por protocolos TSA en Miami.")

    # 2. AUDITORÍA DOCUMENTAL (POUCH & CBP)
    naturaleza = data.get("naturaleza", "GENERAL")
    docs_presentes = data.get("docs_texto", "").upper()
    docs_check = data.get("docs_check", [])
    descripcion = data.get("descripcion_carga", "").upper()
    
    if any(word in descripcion for word in REGLAS_AVIANCA["DESCRIPCIONES_PROHIBIDAS"]):
        alertas.append("DESCRIPCIÓN VAGA (CBP REJECTION)")
        explicaciones.append(f"Término '{descripcion}' prohibido por Aduana USA.")
        riesgos_legales.append("Multa federal de hasta $5,000 por manifiesto incorrecto.")

    requeridos = REGLAS_AVIANCA["MATRIZ_DOCUMENTAL"].get(naturaleza, [])
    for doc in requeridos:
        if doc.upper() not in docs_presentes and doc not in docs_check:
            alertas.append(f"DOCUMENTO FALTANTE: {doc}")
            explicaciones.append(f"Inconsistencia en el Pouch documental.")
            riesgos_legales.append("Retención de carga y cobro de almacenaje (Demurrage).")

    # 3. AUDITORÍA FÍSICA Y OPERATIVA (CAO VS PAX)
    piezas = data.get("piezas", [])
    p_real_total = 0
    p_vol_total = 0
    max_h = 0
    
    for i, p in enumerate(piezas):
        try:
            l, w, h, cant = float(p['l'] or 0), float(p['w'] or 0), float(p['h'] or 0), int(p['cant'] or 0)
            p_real = float(p['p_real'] or 0) * cant
            vol_total = (l * w * h * cant) / REGLAS_AVIANCA["RATIO_VOL"]
            
            p_real_total += p_real
            p_vol_total += vol_total
            if h > max_h: max_h = h
            
            if h > REGLAS_AVIANCA["LIMITES_ALTURA"]["PAX_BELLY"]:
                alertas.append(f"OVERSIZE PIEZA {i+1}")
                explicaciones.append(f"Altura de {h}\" excede límite PAX (63\").")
                riesgos_legales.append("La carga debe ser re-ruta a carguero (CAO).")
        except ValueError: continue

    p_cobrable = max(p_real_total, p_vol_total)

    return {
        "status": "RECHAZADO / HOLD" if alertas else "FLY READY",
        "p_cobrable": round(p_cobrable, 2),
        "alertas": alertas,
        "explicaciones": explicaciones,
        "riesgos": riesgos_legales,
        "recomendacion_vuelo": "CAO (CARGUERO)" if max_h > 63 else "CUALQUIER EQUIPO (PAX/CAO)"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
