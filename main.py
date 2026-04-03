from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import json

app = FastAPI()

# Asegurar directorio estático
if not os.path.exists("static"): 
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Carga de base de conocimientos técnicos de Avianca y Carga General
def get_rules(filename):
    path = f"static/{filename}"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/evaluar")
async def evaluar(data: dict):
    # Cargar reglas en tiempo real para cada consulta
    AVIANCA = get_rules("avianca_rules.json")
    CARGO = get_rules("cargo_rules.json")
    
    errores, soluciones = [], []
    codigos = data.get("codigos", [])
    awb = data.get("awb", "").strip()
    id_chofer = data.get("idChofer", "").strip()
    uld = data.get("uldSugerido", "")
    destino = data.get("destino", "USA")
    
    # 1. SEGURIDAD Y ACCESO (Protocolo TSA/CBP)
    if not awb.startswith("045"):
        errores.append("Prefijo AWB incorrecto para la red Avianca.")
        soluciones.append("Rectificar Master AWB. Si es transferencia, validar guía original.")
    
    if not id_chofer:
        errores.append("Ausencia de identificación del transportista.")
        soluciones.append("Presentar Licencia o ID de Seguridad para registro en el Manifiesto de Carga.")

    # 2. DOCUMENTACIÓN ESPECÍFICA (Lógica de Counter Humano)
    for cod in codigos:
        regla_tipo = CARGO.get(cod, {})
        if regla_tipo:
            # Validación de copias y sobres
            copias = regla_tipo.get("copies_outside", 1)
            soluciones.append(f"Adjuntar {copias} copias originales de {cod} en el sobre exterior.")
            
            # Casos críticos (DGR/AVI/PER)
            if cod == "DGR" and not data.get("chkDGR"):
                errores.append("Declaración de Mercancías Peligrosas (DGD) no confirmada.")
                soluciones.append("Emitir DGD con bordes rojos, firmada por personal certificado IATA.")
            
            if cod == "PER" and "temperature_range" in regla_tipo:
                soluciones.append(f"Rango térmico requerido: {regla_tipo['temperature_range']}.")

    # 3. RESTRICCIONES FÍSICAS Y DE AERONAVE
    if uld == "LD3":
        limite_h = AVIANCA.get("aircraft_limits", {}).get("max_height_belly_in", 63)
        soluciones.append(f"Restricción Belly: Altura máxima de {limite_h} pulgadas para carga en bodega de pasajeros.")
    elif uld == "PMC":
        soluciones.append("Pallet PMC: Verificar integridad de la malla y que no exceda el contorno (Overhang).")

    # 4. ADUANA Y DESTINO (CBP / DIAN / SAT)
    requisitos_pais = AVIANCA.get("country_specific", {}).get(destino, [])
    for req in requisitos_pais:
        soluciones.append(f"Cumplimiento {destino}: Verificar {req.replace('_', ' ')} antes del cierre de vuelo.")

    # ESTATUS FINAL (Sin términos prohibidos)
    status = "REVISIÓN TÉCNICA REQUERIDA (HOLD)" if errores else "CARGA APTA PARA DESPACHO (FLY READY)"
    
    return {
        "status": status,
        "errores": errores,
        "soluciones": soluciones,
        "prechequeo": data.get("prechequeo", "").upper()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
