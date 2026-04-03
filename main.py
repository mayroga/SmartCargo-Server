from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import re

app = FastAPI(title="AL CIELO - SmartCargo Advisory by May Roga")

# Configuración de carpetas estáticas para la interfaz
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
    # Diccionario de respuesta
    errores = []
    soluciones = []
    lang = data.get("lang", "es")
    
    # 1. Extracción de datos del formulario y análisis
    texto_analisis = data.get("analisisTexto", "").upper()
    codigo = data.get("codigoCarga", "")
    awb = data.get("awb", "").strip()
    piezas = int(data.get("piezas") or 0)
    peso = float(data.get("pesoTotal") or 0)
    alto = float(data.get("alto") or 0)
    
    # Checkboxes de seguridad y counter
    chk_seguridad = data.get("chkSeguridad", False) # TSA Screening
    chk_sobres = data.get("chkSobres", False)       # Envelopes
    chk_manifiesto = data.get("chkManifiesto", False) # Ground Manifest
    chk_wood = data.get("chkWood", False)           # NIMF-15
    chk_dgr = data.get("chkDGR", False)             # DGD Present
    
    # 2. LÓGICA DE ASESORÍA Y RESOLUCIÓN (Protocolo Avianca/IATA/CBP)

    # Situación: Identificación AWB
    if not re.match(r"^\d{3}-\d{8}$", awb):
        errores.append("AWB con formato incorrecto o ausente." if lang=="es" else "Invalid or missing AWB.")
        soluciones.append("📞 Sugerencia: Contactar al Forwarder para rectificar la guía física. No se puede procesar en sistema sin 11 dígitos válidos.")

    # Situación: Dimensiones en Bellies (PAX) vs Carguero
    if alto > 160 and alto <= 244:
        # Altura de carguero
        errores.append("Carga excede altura para aviones de pasajeros (Bellies)." if lang=="es" else "Height exceeds passenger aircraft limit.")
        soluciones.append("✈️ Acción: Verificar disponibilidad en B767F (Carguero). Si el vuelo es PAX, se sugiere re-estibar la carga o cambiar a pallet PMC para Main Deck.")
    elif alto > 244:
        # Exceso total
        errores.append("Altura fuera de rango operativo (Excede 244cm)." if lang=="es" else "Height out of operational range.")
        soluciones.append("🛠️ Solución técnica: Realizar 'Breakdown' inmediato. Desarmar el pallet y re-estibar en unidades más pequeñas para cumplir con el contorno del avión.")

    # Situación: Seguridad TSA / Screening
    if not chk_seguridad:
        errores.append("Falta validación de Known Shipper / TSA Screening." if lang=="es" else "Missing TSA Screening / Known Shipper validation.")
        soluciones.append("🛡️ Acción: Mover carga al área de inspección (Rayos X / ETD) antes de ingresar a zona estéril. Cumplir con norma TSA.")

    # Situación: Madera y Aduana (CBP)
    if not chk_wood:
        errores.append("Madera sin sello NIMF-15 detectada." if lang=="es" else "Non-treated wood (ISPM-15) detected.")
        soluciones.append("🪵 Acción preventiva: Para evitar multas de CBP, se sugiere cambiar por pallet de plástico o llevar a fumigación certificada antes del despacho.")

    # Situación: Mercancía Peligrosa (DGR) - MSDS y DGD
    if codigo == "DGR" or "DRY ICE" in texto_analisis or "LITHIUM" in texto_analisis:
        if not chk_dgr:
            errores.append("Alerta DGR: Falta Declaración de Mercancías Peligrosas (DGD)." if lang=="es" else "DGR Alert: Missing Shipper's Declaration.")
            soluciones.append("🚨 Resolución: No recibir carga. Solicitar al Shipper 3 copias originales con borde rojo y verificar que el UN Number coincida con el MSDS.")

    # Situación: Consolidado y Manejo de Sobres (Avianca Standard)
    if "CONSOL" in texto_analisis or "CONSOLIDADO" in texto_analisis:
        if not chk_sobres:
            errores.append("Inconsistencia en documentos de consolidado." if lang=="es" else "Consolidated documentation inconsistency.")
            soluciones.append("📂 Instrucción: Organizar sobres. HAWBs originales dentro del sobre de Avianca; copias pegadas al pallet en sobre canguro visible.")

    # Situación: Peso de Pallet
    if peso > 6800:
        errores.append("Peso excede la capacidad máxima estructural del pallet (6800kg)." if lang=="es" else "Weight exceeds pallet structural capacity.")
        soluciones.append("⚖️ Sugerencia: Dividir la carga en dos unidades (Pallets PMC/PAG) para no comprometer la seguridad del vuelo.")

    # Situación: INTERLINES / TRANSFER / COMAT (Detección por texto)
    if any(x in texto_analisis for x in ["INTERLINE", "TRANSFER", "COMAT"]):
        soluciones.append("🔄 Nota de Asesoría: Verificar que la transferencia tenga el sello de 'Transfer' y el manifiesto de conexión actualizado.")

    # 3. Estado Final de la Asesoría
    if not errores:
        status = "VUELO AUTORIZADO (FLY READY)" if lang=="es" else "FLIGHT AUTHORIZED (FLY READY)"
    else:
        status = "CARGA EN RETENCIÓN (ON HOLD)" if lang=="es" else "CARGO ON HOLD"

    return {
        "status": status,
        "errores": errores,
        "soluciones": soluciones
    }

if __name__ == "__main__":
    # Puerto configurado para despliegue
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
