import json
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI(title="AL CIELO - SmartCargo Advisory Engine")

# Configuración de archivos estáticos
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Carga de Base de Datos Maestra
def cargar_bases():
    try:
        with open("static/avianca_rules.json", encoding="utf-8") as f:
            avianca = json.load(f)
        with open("static/cargo_rules.json", encoding="utf-8") as f:
            cargo = json.load(f)
        return avianca, cargo
    except Exception:
        return {}, {}

AVIANCA_RULES, CARGO_RULES = cargar_bases()

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html", encoding="utf-8") as f:
        return f.read()

@app.post("/api/validar")
async def validar(data: dict):
    alertas = []
    soluciones = []
    explicaciones = []
    
    # Extracción de Datos de Identificación y Contexto
    awb = data.get("awb", "N/A")
    rol = data.get("rol", "TRUCKER")
    tipo_carga = data.get("tipo", "GENERAL")
    texto = data.get("input_texto", "").upper()
    piezas = data.get("piezas", [])

    # 1. VALIDACIÓN DE PAPELERÍA (Basado en el Rol y Tipo de Carga)
    reglas_tipo = CARGO_RULES.get(tipo_carga, CARGO_RULES["GENERAL"])
    docs_necesarios = reglas_tipo.get("documents", [])
    
    # 2. AUDITORÍA FÍSICA Y CAPACIDAD DE AERONAVE
    limits = AVIANCA_RULES.get("aircraft_limits", {})
    total_real = 0
    total_vol = 0
    max_h = 0
    piezas_pesadas = 0

    for p in piezas:
        try:
            l, w, h = float(p.get("l", 0)), float(p.get("w", 0)), float(p.get("h", 0))
            peso = float(p.get("peso", 0))
            total_real += peso
            total_vol += (l * w * h) / 166
            if h > max_h: max_h = h
            if peso > limits.get("max_piece_weight_kg", 150): piezas_pesadas += 1
        except: continue

    # Determinar Avión y ULD
    limit_h_pax = limits.get("max_height_belly_in", 63)
    tipo_avion = "PAX (BELLY)" if max_h <= limit_h_pax else "FREIGHTER (CAO)"

    if max_h > limit_h_pax:
        alertas.append(f"ALTURA EXCEDIDA PARA PAX ({max_h} in)")
        soluciones.append("Cambiar reserva a vuelo Carguero (Freighter).")
        explicaciones.append(f"El límite de altura en aviones de pasajeros es de {limit_h_pax} in.")

    if piezas_pesadas > 0:
        alertas.append(f"DETECTADAS {piezas_pesadas} PIEZAS CON SOBREPESO")
        soluciones.append("Re-estibar en unidades menores a 150kg o solicitar montacargas especial.")
        explicaciones.append("Piezas de más de 150kg requieren manejo especial y pueden dañar el piso del avión.")

    # 3. INTELIGENCIA DE ASESORÍA (IAAT, CBP, TSA, USDA)
    
    # Validación de Embalaje (Madera/Pallets)
    if any(k in texto for k in ["MADERA", "WOOD", "PALLET", "SKID", "CRATE"]):
        if "ISPM15" not in texto and "SELLO" not in texto:
            alertas.append("INCUMPLIMIENTO FITOSANITARIO (USDA)")
            soluciones.append("Llevar el pallet a fumigar o cambiarlo por plástico/metal.")
            explicaciones.append("CBP exige sello ISPM15 en madera para evitar plagas en USA.")

    # Validación de Mercancía Peligrosa (DGR)
    if tipo_carga == "DGR":
        if "MSDS" not in texto:
            alertas.append("FALTA HOJA DE SEGURIDAD (MSDS)")
            soluciones.append("El Shipper debe proveer el MSDS para clasificar el UN Number.")
            explicaciones.append("Norma DOT: No se puede volar DGR sin ficha técnica de seguridad.")
    
    # Validación de Integridad (TSA)
    if any(k in texto for k in ["ROTO", "MOJADO", "DERRAME", "ABIERTO", "CLAVOS"]):
        alertas.append("FALLO EN INTEGRIDAD FÍSICA (SEGURIDAD TSA)")
        soluciones.append("Re-embalar la mercancía o asegurar con film industrial.")
        explicaciones.append("TSA prohíbe el ingreso de bultos que presenten signos de manipulación o goteo.")

    # Validación de Restos Humanos / Animales Vivos
    if tipo_carga in ["HUM", "AVI"]:
        alertas.append(f"PRIORIDAD OPERATIVA: {tipo_carga}")
        soluciones.append("Notificar al Counter para escolta y carga prioritaria.")
        explicaciones.append("Este tipo de carga tiene tiempos de conexión críticos (Short Connection).")

    # 4. RESULTADO FINAL DEL DIAGNÓSTICO
    status = "FLY READY" if not alertas else "HOLD / RECTIFICAR"
    peso_cobrable = round(max(total_real, total_vol), 2)

    return JSONResponse(content={
        "status": status,
        "peso_cobrable": peso_cobrable,
        "alertas": alertas,
        "soluciones": soluciones,
        "explicaciones": explicaciones,
        "documentos": docs_necesarios,
        "avion": tipo_avion,
        "awb_referencia": awb,
        "rol_auditado": rol
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
