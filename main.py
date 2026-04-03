import os, re, json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="AL CIELO - SmartCargo Advisory")

# Crear carpeta para archivos estáticos si no existe
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
async def api_evaluar_carga(request: Request):
    data = await request.json()
    errores = []
    soluciones = []
    lang = data.get("lang", "es")
    
    # Análisis del Cuadro de Texto Inteligente (Pre-chequeo)
    texto_analisis = data.get("analisisTexto", "").upper()
    es_consolidado = any(word in texto_analisis for word in ["CONSOLIDADO", "CONSOLIDATED", "CONSOL"])
    es_peligrosa = any(word in texto_analisis for word in ["DGR", "PELIGROSA", "HAZMAT", "UN3481", "BATERIA"])

    # Datos Técnicos
    awb = data.get("awb", "").strip()
    codigo = data.get("codigoCarga", "")
    alto = float(data.get("alto") or 0)
    peso_total = float(data.get("pesoTotal") or 0)
    piezas = int(data.get("piezas") or 0)

    # 1. Validación de Documentación de Counter (Sobres y Manifiestos)
    if es_consolidado:
        msg_err = "Carga Consolidada: Requiere revisión de HAWBs." if lang=="es" else "Consolidated Cargo: HAWB review required."
        msg_sol = "💡 Tip de Counter: Sobres con Originales DENTRO y Copias FUERA, ordenadas." if lang=="es" else "💡 Counter Tip: Envelopes with Originals INSIDE and Copies OUTSIDE, sorted."
        errores.append(msg_err)
        soluciones.append(msg_sol)

    # 2. Validación AWB (IATA)
    if not re.match(r"^\d{3}-\d{8}$", awb):
        errores.append("AWB Incorrecto (Formato XXX-XXXXXXXX)." if lang=="es" else "Invalid AWB (Format XXX-XXXXXXXX).")
        soluciones.append("💡 Corregir guía aérea antes de procesar." if lang=="es" else "💡 Correct air waybill before processing.")

    # 3. Aeronavegabilidad (Dimensiones/Peso)
    if alto > 160:
        msg = "Dimensiones: Solo Avión Carguero (Main Deck)." if lang=="es" else "Dimensions: Freighter Only (Main Deck)."
        errores.append(msg)
        soluciones.append("💡 Verificar disponibilidad en Boeing 767F/A330F." if lang=="es" else "💡 Check availability on B767F/A330F.")
    
    if alto > 244:
        errores.append("ERROR CRÍTICO: Excede altura máxima de 244cm." if lang=="es" else "CRITICAL ERROR: Exceeds 244cm height limit.")

    # 4. Seguridad (TSA / CBP)
    if es_peligrosa and codigo != "DGR":
        errores.append("Inconsistencia: Texto detecta DGR pero código es GEN." if lang=="es" else "Inconsistency: Text detects DGR but code is GEN.")
        soluciones.append("💡 Cambiar tipo de carga a DGR y adjuntar DGD." if lang=="es" else "💡 Change cargo type to DGR and attach DGD.")

    if not data.get("chkSeguridad"):
        errores.append("Falta Inspección TSA / Rayos X." if lang=="es" else "TSA Screening / X-Ray Missing.")

    # Estado Final
    if lang == "es":
        status = "RECHAZADO" if errores else "LISTO PARA VUELO"
    else:
        status = "REJECTED" if errores else "FLY READY"

    return {
        "status": status,
        "errores": errores,
        "soluciones": soluciones,
        "es_consolidado": es_consolidado,
        "peso_tasable": max(peso_total, (float(data.get("largo",0))*float(data.get("ancho",0))*alto/6000))
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
