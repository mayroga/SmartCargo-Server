from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import re

app = FastAPI(title="AL CIELO - SmartCargo Advisory")

# Configuración de carpetas estáticas
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home():
    html_path = os.path.join("static", "app.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Error: app.html no encontrado en /static</h1>")

@app.post("/api/evaluar")
async def api_evaluar_carga(data: dict):
    errores = []
    soluciones = []
    lang = data.get("lang", "es")
    
    # Extracción de datos
    texto = data.get("analisisTexto", "").upper()
    codigo = data.get("codigoCarga", "")
    awb = data.get("awb", "").strip()
    alto = float(data.get("alto") or 0)
    peso = float(data.get("pesoTotal") or 0)
    
    # Checkboxes de seguridad
    chk_wood = data.get("chkWood", False)
    chk_seguridad = data.get("chkSeguridad", False)
    chk_sobres = data.get("chkSobres", False)

    # --- LÓGICA DE ASESORÍA Y RESOLUCIÓN ---

    # 1. Validación de AWB (IATA)
    if not re.match(r"^\d{3}-\d{8}$", awb):
        errores.append("AWB fuera de formato estándar (11 dígitos)." if lang=="es" else "Invalid AWB format.")
        soluciones.append("📞 Acción: Contactar al Forwarder para corregir Guía Aérea. Si es Avianca, debe iniciar con 045.")

    # 2. Altura y Equipo (Bellies vs Main Deck)
    if alto > 160 and alto <= 243:
        errores.append("Carga para Main Deck (Carguero)." if lang=="es" else "Main Deck cargo only.")
        soluciones.append("✈️ Solución: Esta carga no entra en aviones de pasajeros (PAX). Coordinar transferencia a vuelo carguero B767F.")
    elif alto > 243:
        errores.append("Exceso de altura crítico (Out of Gauge)." if lang=="es" else "Critical over-height.")
        soluciones.append("🛠️ Acción directa: El chofer debe desarmar el pallet (breakdown) y re-estibar a máximo 160cm para cumplir contornos.")

    # 3. Protocolo Aduana (CBP / NIMF-15)
    if not chk_wood:
        errores.append("Madera sin sello NIMF-15 (Peligro de multa)." if lang=="es" else "Untreated wood detected (CBP Risk).")
        soluciones.append("🪵 Acción: Cambiar el pallet por uno de plástico o llevar a fumigación inmediata. No ingresar a zona estéril así.")

    # 4. Seguridad TSA (Screening)
    if not chk_seguridad:
        errores.append("Falta validación TSA / Screening." if lang=="es" else "Missing TSA Screening.")
        soluciones.append("🛡️ Protocolo: Llevar carga al área de inspección (Rayos X / ETD) inmediatamente.")

    # 5. Mercancía Peligrosa (DGR / Lithium / Dry Ice)
    if codigo == "DGR" or any(x in texto for x in ["LITHIUM", "BATTERY", "DRY ICE", "UN3481"]):
        errores.append("Alerta: Mercancía Peligrosa detectada." if lang=="es" else "DGR Alert: Dangerous Goods.")
        soluciones.append("🚨 Resolución: Verificar 3 copias de DGD con borde rojo original. Comprobar etiquetas de ventilación si lleva Hielo Seco.")

    # 6. Consolidados y Sobres (Avianca Standard)
    if "CONSOL" in texto or not chk_sobres:
        errores.append("Sobres de documentos incompletos." if lang=="es" else "Incomplete document envelopes.")
        soluciones.append("📂 Instrucción: HAWBs originales dentro del sobre de Avianca; copias pegadas al pallet en sobre canguro.")

    # 7. Peso de Pallet (IAAT)
    if peso > 6800:
        errores.append("Peso excede límite estructural del pallet." if lang=="es" else "Pallet structural weight limit exceeded.")
        soluciones.append("⚖️ Sugerencia: Dividir la carga en dos unidades (PMC/PAG) para seguridad del vuelo.")

    # Estado Final
    status = "VUELO AUTORIZADO (FLY READY)" if not errores else "CARGA EN RETENCIÓN (ON HOLD)"
    if lang == "en":
        status = "FLY READY" if not errores else "CARGO ON HOLD"

    return {
        "status": status,
        "errores": errores,
        "soluciones": soluciones
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
