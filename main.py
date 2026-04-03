import os, json, io, base64
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
import uvicorn

app = FastAPI(title="AL CIELO - Counter Specialist")

if not os.path.exists("static"): os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/evaluar")
async def api_evaluar(data: str = Form(...), fotos: list[UploadFile] = File(None)):
    payload = json.loads(data)
    l = payload.get("lang", "es")
    bultos = payload.get("detalle_bultos", [])
    naturalezas = payload.get("tipos_carga", [])
    
    # --- LOGICA DE COUNTER AVIANCA ---
    status = "READY TO FLY" if l=="en" else "LISTO PARA VUELO"
    recomendaciones = []
    
    # 1. Validación de Documentación Técnica
    docs_faltantes = [d for d, v in payload.get('docs', {}).items() if not v]
    if docs_faltantes:
        status = "ACTION REQUIRED" if l=="en" else "ACCIÓN REQUERIDA"
        for d in docs_faltantes:
            msg = f"Falta {d}. Solicitar a Shipper/Agente." if l=="es" else f"Missing {d}. Request from Shipper."
            recomendaciones.append(f"📄 {msg}")

    # 2. Análisis de Altura y Estiba
    max_h = max([float(b['h']) for b in bultos]) if bultos else 0
    vuelo = "PAX (BELLY)" if max_h <= 160 else "FREIGHTER (MAIN DECK)"
    
    if max_h > 160 and max_h <= 244:
        msg = "Confirmar posición en Main Deck con Control de Carga." if l=="es" else "Confirm Main Deck position with Load Control."
        recomendaciones.append(f"✈️ {msg}")
    elif max_h > 244:
        status = "RECHAZADO" if l=="es" else "REJECTED"
        recomendaciones.append("❌ Excede altura máxima (244cm). Re-estibar en pallets bajos.")

    # 3. Soluciones Inmediatas (Poder de Conocimiento)
    if "DGR" in naturalezas and not payload.get('chk', {}).get('dgr'):
        recomendaciones.append("💡 SOLUCIÓN: Contactar DGR Specialist para verificar etiquetas de riesgo.")
    
    if payload.get('tipo_pallet') == "Wood" and not payload.get('chk', {}).get('fumigado'):
        recomendaciones.append("💡 SOLUCIÓN: Cambiar por pallet de plástico o verificar sello NIMF-15 para evitar rechazo en destino.")

    # 4. Procesar Fotos para Visualización (Base64 temporal para el reporte)
    preview_fotos = []
    if fotos:
        for f in fotos:
            content = await f.read()
            encoded = base64.b64encode(content).decode('utf-8')
            preview_fotos.append(f"data:image/jpeg;base64,{encoded}")

    return {
        "status": status,
        "vuelo": vuelo,
        "recomendaciones": recomendaciones,
        "fotos": preview_fotos,
        "agente": "AL CIELO Counter AI"
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
