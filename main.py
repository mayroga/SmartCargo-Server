from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import json
import os

app = FastAPI()

# Directorio para archivos estáticos
if not os.path.exists("static"): os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

def load_json(filename):
    path = f"static/{filename}"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    return {}

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html", "r", encoding="utf-8") as f: return f.read()

@app.post("/api/evaluar")
async def evaluar(data: dict):
    AVIANCA = load_json("avianca_rules.json")
    CARGO_RULES = load_json("cargo_rules.json")
    
    errores, soluciones = [], []
    
    # --- FASE 1: IDENTIFICACIÓN Y SEGURIDAD (TSA) ---
    awb = data.get("awb", "").strip()
    id_entidad = data.get("idChofer", "").strip()
    shipper_status = data.get("shipperStatus", "Unknown")

    if not awb.startswith("045"):
        errores.append("Prefijo AWB inválido para Avianca Cargo (045).")
        soluciones.append("Solicitar re-emisión de guía o verificar si es transferencia Interline autorizada.")

    if shipper_status == "Unknown":
        errores.append("Shipper No Conocido (Unknown Shipper).")
        soluciones.append("Aplicar Security Screening obligatorio (X-Ray/ETD) según TSA. Tiempo de espera estimado: +2h.")

    # --- FASE 2: AUDITORÍA FÍSICA Y EMBALAJE (IATA) ---
    l, w, h = float(data.get("length", 0)), float(data.get("width", 0)), float(data.get("height", 0))
    peso_real = float(data.get("pesoReal", 0))
    tipo_empaque = data.get("tipoEmpaque", "")
    
    # Cálculo de Peso Volumétrico (Fórmula IATA: L*W*H / 166 para lb o 6000 para kg)
    peso_vol = (l * w * h) / 166 
    chargeable = max(peso_real, peso_vol)

    if h > 63 and data.get("uld") == "LD3":
        errores.append(f"Altura de {h}\" excede límite de Belly (Avión PAX).")
        soluciones.append("Re-estibar carga a máximo 63\" o solicitar cambio a carguero (Freighter).")

    if tipo_empaque == "WOOD" and not data.get("chkNIMF"):
        errores.append("Embalaje de madera sin sello NIMF-15 visible.")
        soluciones.append("La carga será retenida por USDA. Opción: Sustituir por pallet plástico o fumigar en estación autorizada.")

    # --- FASE 3: DOCUMENTACIÓN Y CARGA ESPECIAL ---
    codigos = data.get("codigos", [])
    for cod in codigos:
        regla = CARGO_RULES.get(cod, {})
        if regla:
            # Validación de copias (Resolutor de Counter)
            docs = regla.get("documents", [])
            soluciones.append(f"REQ {cod}: Presentar {regla.get('copies_outside', 1)} copias de: {', '.join(docs)}.")
            
            if cod == "DGR" and not data.get("chkDGR"):
                errores.append("Falta Shipper's Declaration (DGD) para Mercancía Peligrosa.")
                soluciones.append("Contactar a un DGR Specialist para emitir DGD con bordes rojos y UN Number verificado.")

    # --- FASE 4: INTERPRETACIÓN DE NOTAS (PRE-CHEQUEO) ---
    notas_tecnicas = data.get("prechequeo", "").upper()
    if "DAÑO" in notas_tecnicas or "MOJADO" in notas_tecnicas:
        errores.append("Daño estructural o humedad detectada en el embalaje.")
        soluciones.append("Reparar embalaje o emitir 'Letter of Indemnity' (LOI) si la aerolínea lo autoriza bajo protesta.")

    status = "RECHAZO TÉCNICO (REVISAR DISCREPANCIAS)" if errores else "VUELO AUTORIZADO (FLY READY)"
    
    return {
        "status": status,
        "errores": errores,
        "soluciones": soluciones,
        "chargeable_weight": round(chargeable, 2),
        "notas_finales": notas_tecnicas
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
