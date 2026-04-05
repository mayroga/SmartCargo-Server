import json
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI(title="AL CIELO - SmartCargo Advisory Server")

# Configuración de directorios y archivos
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Carga de Base de Datos Normativa (Reglas de Avianca y Carga)
def cargar_reglas():
    try:
        with open("static/avianca_rules.json", encoding="utf-8") as f:
            avianca = json.load(f)
        with open("static/cargo_rules.json", encoding="utf-8") as f:
            cargo = json.load(f)
        return avianca, cargo
    except FileNotFoundError:
        return {}, {}

AVIANCA_RULES, CARGO_RULES = cargar_reglas()

@app.get("/", response_class=HTMLResponse)
async def home():
    try:
        with open("static/app.html", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Error: static/app.html no encontrado."

@app.post("/api/validar")
async def validar(data: dict):
    alertas = []
    soluciones = []
    explicaciones = []
    
    tipo_carga = data.get("tipo", "GENERAL")
    texto_dictado = data.get("input_texto", "").upper()
    piezas = data.get("piezas", [])
    rol = data.get("rol", "TRUCKER")

    # 1. VALIDACIÓN DE DOCUMENTACIÓN (Basado en cargo_rules.json)
    reglas_especificas = CARGO_RULES.get(tipo_carga, CARGO_RULES["GENERAL"])
    docs_requeridos = reglas_especificas.get("documents", [])

    # 2. AUDITORÍA FÍSICA Y LÍMITES DE AERONAVE (Basado en avianca_rules.json)
    limits = AVIANCA_RULES.get("aircraft_limits", {})
    total_real = 0
    total_vol = 0
    max_h = 0
    peso_excedido = False

    for i, p in enumerate(piezas):
        try:
            l, w, h = float(p.get("l", 0)), float(p.get("w", 0)), float(p.get("h", 0))
            peso = float(p.get("peso", 0))
            
            total_real += peso
            total_vol += (l * w * h) / 166
            if h > max_h: max_h = h

            # Validar peso por pieza individual
            if peso > limits.get("max_piece_weight_kg", 150):
                peso_excedido = True
        except ValueError:
            continue

    # Lógica de Avión (Belly vs Freighter)
    limit_h_pax = limits.get("max_height_belly_in", 63)
    tipo_avion = "PAX / BELLY"
    if max_h > limit_h_pax:
        tipo_avion = "FREIGHTER (CAO)"
        alertas.append(f"ALTURA EXCESIVA PARA PAX ({max_h} in)")
        soluciones.append("Mover carga a vuelo carguero.")
        explicaciones.append(f"La altura supera los {limit_h_pax} in permitidos en aviones de pasajeros.")

    if peso_excedido:
        alertas.append("PESO INDIVIDUAL EXCEDIDO")
        soluciones.append("Re-estibar en unidades más pequeñas o usar equipo especial.")
        explicaciones.append(f"Piezas sobrepasan el límite estándar de {limits.get('max_piece_weight_kg')} kg.")

    # 3. ASESORÍA TÉCNICA PREVENTIVA (IAAT / CBP / USDA)
    # Validación de Madera (Sello ISPM15)
    if any(palabra in texto_dictado for palabra in ["MADERA", "WOOD", "PALLET"]):
        if "ISPM15" not in texto_dictado and "SELLO" not in texto_dictado:
            alertas.append("FALLO FITOSANITARIO (USDA)")
            soluciones.append("Llevar el pallet a fumigar o cambiarlo por uno de plástico.")
            explicaciones.append("Todo embalaje de madera hacia USA requiere sello certificado ISPM15.")

    # Validación de Carga Peligrosa (DGR)
    if tipo_carga == "DGR" or "PELIGROSA" in texto_dictado:
        if "MSDS" not in texto_dictado:
            alertas.append("FALTA HOJA DE SEGURIDAD (MSDS)")
            soluciones.append("Solicitar MSDS al shipper antes de entregar en counter.")
            explicaciones.append("Regulación DOT requiere ficha técnica para materiales peligrosos.")

    # Validación de Seguridad (TSA)
    if "DAÑADA" in texto_dictado or "ROTA" in texto_dictado or "MOJADA" in texto_dictado:
        alertas.append("INTEGRIDAD DE CARGA COMPROMETIDA")
        soluciones.append("Rectificar embalaje y re-asegurar bultos.")
        explicaciones.append("Carga con daños físicos es rechazada por seguridad aérea (TSA).")

    # 4. DETERMINACIÓN DE ESTADO FINAL
    status = "FLY READY" if not alertas else "HOLD / RECTIFICAR"
    
    # Peso Cobrable (El mayor entre real y volumétrico)
    peso_cobrable = round(max(total_real, total_vol), 2)

    return JSONResponse(content={
        "status": status,
        "peso_cobrable": peso_cobrable,
        "alertas": alertas,
        "soluciones": soluciones,
        "explicaciones": explicaciones,
        "documentos": docs_requeridos,
        "avion": tipo_avion,
        "asesor": "SmartCargo Advisory by May Roga"
    })

if __name__ == "__main__":
    # Configurado para correr en Render o local
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
