import os
import json
import io
import re
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image # Cerebro de procesamiento de imagen
import uvicorn

app = FastAPI(title="AL CIELO - SmartCargo Engine")

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

# --- MOTOR DE PROCESAMIENTO TÉCNICO ---
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
    bultos = payload.get("detalle_bultos", [])
    tipos_carga = payload.get("tipos_carga", []) # Lista de naturalezas (DGR, GEN, PER, etc.)
    tipo_pallet = payload.get("tipo_pallet", "Wood")
    
    # 1. Análisis de Medidas y Pesos (Lógica CargoLink)
    t_piezas = 0
    t_peso_real = 0
    t_volumen = 0
    max_h = 0
    alertas = []
    
    for b in bultos:
        try:
            cant = int(b.get('cant', 0))
            l = float(b.get('l', 0))
            w = float(b.get('w', 0))
            h = float(b.get('h', 0))
            p = float(b.get('p', 0))

            t_piezas += cant
            t_peso_real += (cant * p)
            t_volumen += (cant * (l * w * h) / 1000000)
            if h > max_h: max_h = h
        except (ValueError, TypeError):
            continue

    peso_volumetrico = t_volumen * 167
    peso_tasable = max(t_peso_real, peso_volumetrico)

    # 2. Dictamen de Aeronavegabilidad
    vuelo = "PAX (BELLY)" if lang == "es" else "PAX (BELLY)"
    status = "APROBADO" if lang == "es" else "APPROVED"

    if max_h > 160:
        vuelo = "CARGUERO (MAIN DECK)" if lang == "es" else "FREIGHTER (MAIN DECK)"
    
    if max_h > 244:
        status = "RECHAZADO" if lang == "es" else "REJECTED"
        msg = "Altura excede límite de 244cm" if lang == "es" else "Height exceeds 244cm limit"
        alertas.append(f"❌ {msg}")

    # 3. Validación de Naturalezas Múltiples
    # Si es DGR o Dry Ice, verificar si el usuario marcó el checklist de seguridad
    if ("DGR" in tipos_carga or "ICE" in tipos_carga):
        if not payload.get('chk', {}).get('dgr', False):
            msg = "Falta Declaración DGR / MSDS" if lang == "es" else "Missing DGR Declaration / MSDS"
            alertas.append(f"⚠️ {msg}")
            status = "PENDIENTE" if lang == "es" else "PENDING"

    # 4. Procesamiento de Fotos de Referencia (Sin guardado en disco)
    fotos_validas = 0
    if fotos:
        for f in fotos:
            try:
                content = await f.read()
                # Python "lee" los bytes para validar que sea una imagen real
                img = Image.open(io.BytesIO(content))
                img.verify() 
                fotos_validas += 1
            except Exception:
                continue

    # 5. Construcción del Reporte Técnico (Tabla HTML para el Front-end)
    # Se genera dinámicamente según el idioma
    labels = {
        "es": ["Parámetro", "Estado/Valor", "Instrucción Técnica", "Proceder al despacho"],
        "en": ["Parameter", "State/Value", "Technical Instruction", "Proceed to dispatch"]
    }[lang]

    tabla_html = f"""
    <table style="width:100%; border-collapse:collapse; margin-top:10px; font-family:sans-serif;">
        <tr style="background:#0a3d62; color:white;">
            <th style="padding:8px; border:1px solid #ddd;">{labels[0]}</th>
            <th style="padding:8px; border:1px solid #ddd;">{labels[1]}</th>
        </tr>
        <tr><td style="padding:8px; border:1px solid #ddd;">AWB</td><td style="padding:8px; border:1px solid #ddd;">{payload.get('awb', 'N/A')}</td></tr>
        <tr><td style="padding:8px; border:1px solid #ddd;">STATUS</td><td style="padding:8px; border:1px solid #ddd; font-weight:bold;">{status}</td></tr>
        <tr><td style="padding:8px; border:1px solid #ddd;">AIRCRAFT</td><td style="padding:8px; border:1px solid #ddd;">{vuelo}</td></tr>
        <tr><td style="padding:8px; border:1px solid #ddd;">CHARGEABLE WT</td><td style="padding:8px; border:1px solid #ddd;">{peso_tasable:.2f} KG</td></tr>
        <tr><td style="padding:8px; border:1px solid #ddd;">ULD/PALLET</td><td style="padding:8px; border:1px solid #ddd;">{tipo_pallet}</td></tr>
        <tr><td style="padding:8px; border:1px solid #ddd;">EVIDENCE</td><td style="padding:8px; border:1px solid #ddd;">{fotos_validas} Files OK</td></tr>
    </table>
    
    <div style="margin-top:15px; padding:10px; border-left:4px solid #0a3d62; background:#f4f4f4;">
        <strong>{labels[2]}:</strong><br>
        {labels[3] if status in ["APROBADO", "APPROVED"] else "STOP: Correct discrepancies highlighted in red."}
    </div>
    """

    return {
        "status": status,
        "asesoria_tecnica": tabla_html,
        "peso_tasable": round(peso_tasable, 2),
        "alertas": alertas,
        "fuente": "AL CIELO Core Engine (Python)"
    }

if __name__ == "__main__":
    # Render usa la variable de entorno PORT
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
