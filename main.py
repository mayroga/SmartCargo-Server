from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

app = FastAPI(title="SMARTCARGO-SERVER-V2")

if not os.path.exists("static"): os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- PROTOCOLOS DE AUDITORÍA TÉCNICA AVIANCA / TSA / CBP ---
REGLAS = {
    "PREFIJO": "045",
    "RATIO_VOL": 166,
    "MAX_H_PAX": 63.0,
    "DOCS": {
        "GENERAL": ["AWB", "Factura Original", "Packing List"],
        "DGR": ["AWB", "Shipper's Declaration", "MSDS", "Factura Original", "UN-Packaging Cert"],
        "PER": ["AWB", "Factura", "Certificado Fitosanitario/Sanitario", "Packing List"],
        "VAL": ["AWB", "Manifiesto de Valores", "Custodia Armada", "Sello de Seguridad"],
        "HUM": ["AWB", "Acta Defunción", "Certificado Embalsamamiento", "Permiso Tránsito"]
    }
}

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html", "r", encoding="utf-8") as f: return f.read()

@app.post("/api/validar_carga")
async def validar_carga(data: dict):
    alertas = []
    explicaciones = []
    riesgos = []
    
    # FASE 1 & 2: IDENTIFICACIÓN Y SEGURIDAD TSA
    awb = data.get("awb", "")
    known = data.get("known_shipper")
    if not awb.startswith(REGLAS["PREFIJO"]):
        alertas.append("PREFIJO INVÁLIDO")
        explicaciones.append("El AWB debe iniciar con 045 para Avianca. No se puede procesar en este sistema.")
        riesgos.append("Rechazo inmediato en Gate.")

    if not known:
        alertas.append("SHIPPER DESCONOCIDO")
        explicaciones.append("Requiere Screening físico al 100% o K9 obligatorio según normativa TSA.")
        riesgos.append("Retraso operativo y costo extra de screening.")

    # FASE 3: AUDITORÍA DOCUMENTAL (POUCH)
    naturaleza = data.get("naturaleza", "GENERAL")
    docs_escritos = data.get("docs_texto", "").upper()
    docs_marcados = data.get("docs_check", [])
    
    for doc in REGLAS["DOCS"].get(naturaleza, []):
        if doc.upper() not in docs_escritos and doc not in docs_marcados:
            alertas.append(f"FALTA DOCUMENTO: {doc}")
            explicaciones.append(f"La ausencia de {doc} impide la entrada a zona estéril y el desaduanaje en destino.")
            riesgos.append("Multa CBP (Customs) y retención de carga (48h-72h).")

    # FASE 5: INSPECCIÓN FÍSICA (DIM & WEIGHT)
    piezas = data.get("piezas", [])
    p_real_total = 0
    p_vol_total = 0
    
    for i, p in enumerate(piezas):
        try:
            l, w, h, cant = float(p['l']), float(p['w']), float(p['h']), int(p['cant'])
            p_real = float(p['p_real']) * cant
            vol = (l * w * h * cant) / REGLAS["RATIO_VOL"]
            p_real_total += p_real
            p_vol_total += vol
            
            if h > REGLAS["MAX_H_PAX"]:
                alertas.append(f"EXCESO ALTURA - PIEZA {i+1}")
                explicaciones.append(f"Altura de {h}\" excede el límite de Boeing 787/Airbus A330 PAX (Belly).")
                riesgos.append("Vire de carga (Offload) o transferencia forzosa a carguero (CAO).")
        except: continue

    # FASE 6: REPORTE DEL INSPECTOR (DAÑOS/OLORES)
    voz = data.get("reporte_voz", "").upper()
    palabras_criticas = ["DAÑO", "ROTO", "OLOR", "FUGA", "MOJADO", "SIN SELLO"]
    for palabra in palabras_criticas:
        if palabra in voz:
            alertas.append(f"ANOMALÍA DETECTADA: {palabra}")
            explicaciones.append(f"El reporte técnico indica {palabra.lower()} en el embalaje.")
            riesgos.append("Responsabilidad legal de la aerolínea si se acepta así. NO FIRMAR SIN NOTA.")

    return {
        "status": "STOP / RECHAZADO" if alertas else "FLY READY (APROBADO)",
        "p_cobrable": round(max(p_real_total, p_vol_total), 2),
        "alertas": alertas,
        "explicaciones": explicaciones,
        "riesgos": riesgos
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
