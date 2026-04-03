from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import json
from datetime import datetime

app = FastAPI(title="AL CIELO - SmartCargo AIPA")

# Persistencia de carpetas para auditoría
if not os.path.exists("static"): os.makedirs("static")
if not os.path.exists("auditorias_logs"): os.makedirs("auditorias_logs")

app.mount("/static", StaticFiles(directory="static"), name="static")

# --- MOTOR DE REGLAS DE NEGOCIO (PROFUNDIDAD TOTAL) ---
RULES = {
    "AIRLINE_PREFIX": "045", # Avianca
    "IATA_RATIO": 166,       # Lbs/Inch
    "MAX_BELLY_HEIGHT": 63,  # Pulgadas límite para aviones PAX
    "DOCS": {
        "GENERAL": ["AWB Original", "Commercial Invoice (3x)", "Packing List", "SLI"],
        "DGR": ["Shipper's Declaration (Red Border)", "MSDS", "NOTOC Prep", "Checklist IATA"],
        "PER": ["Phytosanitary Certificate", "Health Certificate", "Temperature Log", "DGD (if Dry Ice)"],
        "VAL": ["Armed Escort Record", "Seal Verification Form", "Vault Storage Receipt"],
        "AVI": ["Live Animals Regulations (LAR) Checklist", "Vet Health Cert", "Feeding Instructions"],
        "HUM": ["Death Certificate", "Embalming Certificate", "Transit Permit"]
    },
    "SECURITY_LEVELS": {
        "KNOWN": "Standard Screening (X-Ray)",
        "UNKNOWN": "Deep Screening (Physical Search + ETD + 4h Hold)"
    }
}

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/ejecutar_auditoria_total")
async def ejecutar_auditoria(data: dict):
    try:
        # 1. Identificación de la Cadena de Custodia
        perfil = data.get("perfil")
        awb = data.get("awb_full", "")
        driver_id = data.get("driver_id", "")
        origin = data.get("origin", "").upper()
        destination = data.get("destination", "").upper()
        
        log_id = f"{awb}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        alertas = []
        instrucciones = []
        diagnostico_tecnico = []

        # 2. Validación de Prefijo y Ruta (CBP/IATA)
        if not awb.startswith(RULES["AIRLINE_PREFIX"]):
            alertas.append(f"ERROR DE ADMISIÓN: Prefijo {awb[:3]} no pertenece a Avianca (045).")
            instrucciones.append("Re-dirigir al cliente a la aerolínea correspondiente o re-emitir guía.")

        # 3. Auditoría del Pouch (Contenido del Sobre)
        naturaleza = data.get("naturaleza", "GENERAL")
        docs_presentados = data.get("pouch_docs", [])
        docs_requeridos = RULES["DOCS"].get(naturaleza, [])
        
        for doc in docs_requeridos:
            if doc not in docs_presentados:
                alertas.append(f"DOCUMENTO AUSENTE: Falta {doc} en el sobre original.")
                instrucciones.append(f"Es obligatorio presentar {doc} en físico para cerrar el manifiesto.")

        if data.get("has_corrections"):
            alertas.append("ILEGIBILIDAD DETECTADA: El documento presenta tachaduras o correcciones manuales.")
            instrucciones.append("Proceder a la re-emisión del documento. Aduana no acepta tachones en la Guía Aérea.")

        # 4. Análisis Pieza por Pieza (Revenue & Estiba)
        piezas = data.get("piezas", [])
        peso_real_acumulado = 0
        peso_vol_acumulado = 0
        
        for idx, p in enumerate(piezas):
            l, w, h = float(p['l']), float(p['w']), float(p['h'])
            cant = int(p['cant'])
            p_real_unit = float(p['p_real'])
            
            # Cálculo de Volumen Unitario y Total
            vol_unit = (l * w * h) / RULES["IATA_RATIO"]
            vol_total_item = vol_unit * cant
            real_total_item = p_real_unit * cant
            
            peso_real_acumulado += real_total_item
            peso_vol_acumulado += vol_total_item
            
            # Validación Física de Aeronave
            if h > RULES["MAX_BELLY_HEIGHT"]:
                alertas.append(f"DIMENSIÓN CRÍTICA (Pieza #{idx+1}): Altura de {h}\" excede el límite de Aviones PAX.")
                instrucciones.append(f"Solicitar cambio de equipo a CARGUERO (CAO) o desarmar pallet para reducir altura.")

        # 5. Seguridad TSA (Status del Shipper)
        shipper_status = data.get("shipper_status", "UNKNOWN")
        diagnostico_tecnico.append(f"Protocolo de Seguridad: {RULES['SECURITY_LEVELS'][shipper_status]}")

        # 6. Análisis del Reporte de Voz/Muelle (NLP Simulado)
        reporte_voz = data.get("reporte_voz", "").upper()
        if any(x in reporte_voz for x in ["GOLPE", "HÚMEDO", "OLOR", "ROTO", "CAJA ABIERTA"]):
            alertas.append("ALERTA DE MUELLE: El reporte de inspección visual indica irregularidades físicas.")
            instrucciones.append("Emitir Nota de Protesta Inmediata. El cliente debe firmar la aceptación de daños previos.")

        # 7. Resultado Final
        chargeable_weight = max(peso_real_acumulado, peso_vol_acumulado)
        status_final = "RECHAZADO PARA VUELO" if len(alertas) > 0 else "LISTO PARA VUELO (FLY READY)"

        # Guardar Log de Auditoría
        with open(f"auditorias_logs/{log_id}.json", "w") as f:
            json.dump(data, f)

        return JSONResponse({
            "log_id": log_id,
            "status": status_final,
            "chargeable": round(chargeable_weight, 2),
            "real": round(peso_real_total, 2),
            "method": "Volumétrico (IATA 166)" if peso_vol_acumulado > peso_real_acumulado else "Peso Real",
            "alertas": alertas,
            "instrucciones": instrucciones,
            "diagnostico": diagnostico_tecnico
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
