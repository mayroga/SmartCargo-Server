import os
import json
import re
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI(title="AL CIELO - Motor Lógico Independiente")

# Montar archivos estáticos
if not os.path.exists("static"): os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/evaluar")
async def api_evaluar_carga(data: str = Form(...), foto: UploadFile = File(None)):
    payload = json.loads(data)
    bultos = payload.get("detalle_bultos", [])
    chk = payload.get("chk", {})
    
    # --- CEREBRO LÓGICO DE PHYTON (Reglas de Avianca) ---
    reporte = []
    status = "APROBADO"
    
    # 1. Validación de Medidas
    t_piezas = 0
    t_peso_real = 0
    max_h = 0
    for b in bultos:
        cant = int(b['cant'])
        h = float(b['h'])
        t_piezas += cant
        t_peso_real += (cant * float(b['p']))
        if h > max_h: max_h = h

    # 2. Lógica de Aeronavegabilidad
    vuelo = "AVIÓN PASAJEROS (BELLIES)"
    if max_h > 160:
        vuelo = "AVIÓN CARGUERO (MAIN DECK)"
    if max_h > 244:
        status = "RECHAZADO"
        reporte.append("❌ ERROR: Altura excede el máximo permitido de 244cm.")

    # 3. Validación de Seguridad (Checklist)
    if not chk.get('embalaje'):
        status = "RECHAZADO"
        reporte.append("❌ EMBALAJE: No cumple con estándares de integridad.")
    
    if payload.get('tipo') == "DGR" and not chk.get('dgr'):
        status = "RECHAZADO"
        reporte.append("❌ DGR: Falta declaración de mercancía peligrosa.")

    # 4. Verificación de Foto (Python detecta si hay evidencia)
    foto_status = "✅ EVIDENCIA VISUAL RECIBIDA" if foto else "⚠️ SIN EVIDENCIA FOTOGRÁFICA"

    # --- CONSTRUCCIÓN DEL REPORTE FINAL (TABLA HTML) ---
    tabla_resumen = f"""
    <table style="width:100%; border:1px solid #0a3d62; border-collapse:collapse; margin-top:10px;">
        <tr style="background:#0a3d62; color:white;">
            <th style="padding:10px;">PARÁMETRO</th>
            <th style="padding:10px;">ESTADO</th>
        </tr>
        <tr><td style="padding:10px; border:1px solid #ddd;">ESTADO FINAL</td><td style="padding:10px; border:1px solid #ddd; font-weight:bold;">{status}</td></tr>
        <tr><td style="padding:10px; border:1px solid #ddd;">TIPO DE VUELO</td><td style="padding:10px; border:1px solid #ddd;">{vuelo}</td></tr>
        <tr><td style="padding:10px; border:1px solid #ddd;">PESO TOTAL</td><td style="padding:10px; border:1px solid #ddd;">{t_peso_real} KG</td></tr>
        <tr><td style="padding:10px; border:1px solid #ddd;">FOTO CARGA</td><td style="padding:10px; border:1px solid #ddd;">{foto_status}</td></tr>
    </table>
    
    <div style="margin-top:15px; padding:10px; background:#f9f9f9; border-left:5px solid #0a3d62;">
        <strong>INSTRUCCIÓN TÉCNICA:</strong><br>
        { "Proceder con el pesaje y etiquetado para despacho inmediato." if status == "APROBADO" else "DETENER CARGA. Corregir los puntos señalados arriba antes de re-evaluar." }
    </div>
    """

    return {
        "status": status,
        "asesoria_tecnica": tabla_resumen,
        "fuente": "Motor Lógico AL CIELO (Python Local)"
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
