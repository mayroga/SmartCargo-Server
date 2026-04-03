import os, json, io, base64
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI(title="AL CIELO - SmartCargo Advisory")

if not os.path.exists("static"): os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/diagnostico")
async def diagnosticar(data: str = Form(...), fotos: list[UploadFile] = File(None)):
    payload = json.loads(data)
    texto_analizar = payload.get("dictado", "").upper()
    bultos = payload.get("detalle_bultos", [])
    docs = payload.get("docs", {})
    
    alertas = []
    soluciones = []
    
    # --- FISCALIZACIÓN DE SEGURIDAD Y DOCUMENTACIÓN ---
    
    # Análisis de Carga Consolidada (IATA/TSA)
    if any(word in texto_analizar for word in ["CONSOLIDADO", "CONSOL", "HAWB"]):
        if not docs.get('manifiesto'):
            alertas.append("❌ ERROR CRÍTICO: Carga consolidada detectada sin Manifiesto HAWB.")
            soluciones.append("💡 ACCIÓN: Exigir Manifiesto. Verificar sobres: Originales fuera, copias dentro.")

    # Análisis de Mercancía Peligrosa (DGR/IATA)
    if any(word in texto_analizar for word in ["DGR", "PELIGROSA", "BATTERY", "UN3481", "LITHIUM", "QUIMICOS"]):
        if not docs.get('msds'):
            alertas.append("❌ RIESGO DGR: Detectada posible mercancía peligrosa sin MSDS/DGD.")
            soluciones.append("💡 ACCIÓN: Retener carga. Solicitar Declaración de Mercancía Peligrosa (DGD) firmada.")

    # Análisis de Perecederos (Avianca Cargo)
    if any(word in texto_analizar for word in ["PER", "FRESH", "FRUTA", "PESCADO", "PERISHABLE", "ICE"]):
        alertas.append("⚠️ PRIORIDAD PER: Carga perecedera detectada.")
        soluciones.append("💡 ACCIÓN: Priorizar en Bellies. Revisar fitosanitarios originales y cadena de frío.")

    # --- VALIDACIÓN TÉCNICA DE MEDIDAS ---
    max_h = 0
    t_peso = 0
    t_vol = 0
    
    for b in bultos:
        try:
            h = float(b['h'])
            cant = int(b['cant'])
            t_peso += (cant * float(b['p']))
            t_vol += (cant * float(b['l']) * float(b['w']) * h / 1000000)
            if h > max_h: max_h = h
        except: continue

    # Determinación de Aeronave
    vuelo = "PAX (BELLY)" if max_h <= 160 else "FREIGHTER (MAIN DECK)"
    
    if max_h > 244:
        alertas.append("❌ RECHAZO TÉCNICO: Altura excede límite de aeronavegabilidad (244cm).")
        soluciones.append("💡 ACCIÓN: Solicitar re-paletización inmediata o despiece para Main Deck.")
    elif max_h > 160:
        alertas.append("📝 NOTA: Altura superior a 160cm. Solo apto para avión CARGUERO.")
        soluciones.append("💡 ACCIÓN: Confirmar disponibilidad de espacio en Main Deck.")

    # --- PROCESAMIENTO DE IMÁGENES ---
    img_data = []
    if fotos:
        for f in fotos:
            content = await f.read()
            encoded = base64.b64encode(content).decode('utf-8')
            img_data.append(f"data:image/jpeg;base64,{encoded}")

    status = "STOP / RECHAZADO" if any("❌" in a for a in alertas) else "LISTO PARA VUELO"
    
    return {
        "status": status,
        "vuelo": vuelo,
        "alertas": alertas,
        "soluciones": soluciones,
        "fotos": img_data,
        "resumen": {"peso": round(t_peso, 2), "vol": round(t_vol, 3)}
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
