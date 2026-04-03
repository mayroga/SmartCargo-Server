import os
import json
import io
import re
import base64
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
import uvicorn

app = FastAPI(title="AL CIELO - Counter Specialist Engine")

# Configuración de archivos estáticos
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home():
    html_path = os.path.join("static", "app.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>AL CIELO: Error - app.html no encontrado</h1>")

# --- MOTOR DE DIAGNÓSTICO TÉCNICO ---
@app.post("/api/evaluar")
async def api_evaluar_carga(
    data: str = Form(...), 
    fotos: list[UploadFile] = File(None)
):
    try:
        payload = json.loads(data)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Data Format")

    lang = payload.get("lang", "es")
    texto_input = payload.get("dictado", "").upper()
    bultos = payload.get("detalle_bultos", [])
    tipos_carga = payload.get("tipos_carga", []) 
    tipo_pallet = payload.get("tipo_pallet", "Wood")
    docs = payload.get("docs", {})
    
    alertas = []
    soluciones = []
    status = "APROBADO / READY" if lang == "es" else "APPROVED / READY"

    # 1. ANÁLISIS DE TEXTO LÓGICO (Diagnóstico de voz/pegado)
    # Escenario: Carga Consolidada
    if any(word in texto_input for word in ["CONSOLIDADO", "CONSOL", "CONSOLIDATED", "HAWB"]):
        if not docs.get('manifiesto'):
            status = "ACCION REQUERIDA"
            alertas.append("❌ ERROR: Carga consolidada detectada sin MANIFIESTO.")
            soluciones.append("💡 SOLUCIÓN: Exigir Manifiesto HAWB. Verificar que el sobre contenga Originales fuera y Copias dentro.")

    # Escenario: Peligrosas / Baterías
    if any(word in texto_input for word in ["DGR", "PELIGROSA", "DANGEROUS", "BATTERY", "BATERIA", "UN3481", "UN3090", "LITHIUM"]):
        if not docs.get('msds'):
            status = "DETENIDO / STOP"
            alertas.append("❌ RIESGO: Posible DGR detectada en descripción sin MSDS.")
            soluciones.append("💡 SOLUCIÓN: Retener bultos. Solicitar Declaración del Expedidor (DGD) y MSDS vigente.")

    # Escenario: Perecederos
    if any(word in texto_input for word in ["PER", "FRESH", "PERECEDERO", "FRUTA", "PESCADO", "FLOWERS"]):
        alertas.append("⚠️ AVISO: Carga Perecedera.")
        soluciones.append("💡 SOLUCIÓN: Verificar temperatura en bodega y priorizar en vuelo Belly (PAX).")

    # 2. ANÁLISIS FÍSICO (Medidas y Pesos)
    t_peso_real = 0
    t_volumen = 0
    max_h = 0
    
    for b in bultos:
        try:
            cant = int(b.get('cant', 1))
            l, w, h, p = float(b.get('l', 0)), float(b.get('w', 0)), float(b.get('h', 0)), float(b.get('p', 0))
            t_peso_real += (cant * p)
            t_volumen += (cant * (l * w * h) / 1000000)
            if h > max_h: max_h = h
        except: continue

    peso_tasable = max(t_peso_real, t_volumen * 167)
    vuelo = "PAX (BELLY)" if max_h <= 160 else "CARGUERO (MAIN DECK)"
    
    if max_h > 244:
        status = "RECHAZADO"
        alertas.append("❌ EXCESO: Altura sobrepasa los 244cm de seguridad.")
        soluciones.append("💡 SOLUCIÓN: Solicitar despiece de la estiba o re-paletización en ULD bajo.")

    # 3. VALIDACIÓN DE EMBALAJE
    if tipo_pallet == "Wood" and not payload.get('chk', {}).get('fumigado'):
        alertas.append("⚠️ EMBALAJE: Pallet de madera sin confirmación de sello.")
        soluciones.append("💡 SOLUCIÓN: Verificar sello NIMF-15 físicamente. Si no tiene, cambiar por plástico para evitar multas CBP.")

    # 4. PROCESAMIENTO DE FOTOS (Visualización en Reporte)
    fotos_base64 = []
    if fotos:
        for f in fotos:
            try:
                content = await f.read()
                img = Image.open(io.BytesIO(content))
                img.thumbnail((300, 300)) # Optimizar tamaño
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG")
                encoded = base64.b64encode(buffered.getvalue()).decode('utf-8')
                fotos_base64.append(f"data:image/jpeg;base64,{encoded}")
            except: continue

    # 5. CONSTRUCCIÓN DE TABLA TÉCNICA
    labels = {"es": ["CONCEPTO", "DETALLE"], "en": ["CONCEPT", "DETAIL"]}[lang]
    tabla_html = f"""
    <table style="width:100%; border-collapse:collapse; margin-bottom:15px; font-family:sans-serif; border: 2px solid #0a3d62;">
        <tr style="background:#0a3d62; color:white;">
            <th style="padding:10px; border:1px solid #ddd;">{labels[0]}</th>
            <th style="padding:10px; border:1px solid #ddd;">{labels[1]}</th>
        </tr>
        <tr><td style="padding:8px; border:1px solid #ddd;">ESTADO FINAL</td><td style="padding:8px; border:1px solid #ddd; font-weight:bold;">{status}</td></tr>
        <tr><td style="padding:8px; border:1px solid #ddd;">EQUIPO SUGERIDO</td><td style="padding:8px; border:1px solid #ddd;">{vuelo}</td></tr>
        <tr><td style="padding:8px; border:1px solid #ddd;">PESO TASABLE</td><td style="padding:8px; border:1px solid #ddd;">{peso_tasable:.2f} KG</td></tr>
        <tr><td style="padding:8px; border:1px solid #ddd;">CONTENEDOR</td><td style="padding:8px; border:1px solid #ddd;">{tipo_pallet}</td></tr>
    </table>
    """

    return {
        "status": status,
        "tabla": tabla_html,
        "alertas": alertas,
        "soluciones": soluciones,
        "fotos": fotos_base64,
        "agente": "AL CIELO - Counter Diagnostic"
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
