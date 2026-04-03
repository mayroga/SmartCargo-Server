import os
import json
import io
import re
import base64
from PIL import Image  # El "Cerebro" que procesa los bytes
import google.generativeai as genai
from openai import OpenAI
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI(title="AL CIELO - SmartCargo Advisory Server")

# Configuración de Claves (Render Environment)
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")

# Inicialización de Clientes
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

client_openai = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

# Directorio estático
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- MOTOR DE PROCESAMIENTO DE IMAGEN (EL CEREBRO) ---
def procesar_imagen_para_ia(file_bytes):
    """
    Optimiza la imagen para planes gratuitos:
    Redimensiona a max 1024px y comprime a JPEG 70%
    """
    try:
        img = Image.open(io.BytesIO(file_bytes))
        # Convertir a RGB (evita errores con transparencias PNG)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        # Redimensionar proporcionalmente
        max_size = 1024
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Guardar en buffer optimizado
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=70, optimize=True)
        return buffer.getvalue()
    except Exception as e:
        print(f"Error en procesamiento de imagen: {e}")
        return None

@app.get("/", response_class=HTMLResponse)
async def home():
    html_path = os.path.join("static", "app.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>AL CIELO: Error - app.html no encontrado</h1>")

@app.post("/api/evaluar")
async def api_evaluar_carga(
    data: str = Form(...), 
    foto: UploadFile = File(None)
):
    payload = json.loads(data)
    
    # 1. Procesar Detalle de Bultos (Multi-partida)
    bultos = payload.get("detalle_bultos", [])
    t_piezas = 0
    t_peso_real = 0
    t_volumen = 0
    analisis_dimensiones = ""

    for b in bultos:
        c = int(b.get('cant', 0))
        l, w, h = float(b.get('l', 0)), float(b.get('w', 0)), float(b.get('h', 0))
        p = float(b.get('p', 0))
        
        t_piezas += c
        t_peso_real += (c * p)
        t_volumen += (c * (l * w * h) / 1000000)
        
        if h > 160: analisis_dimensiones = "⚠️ REQUIERE CARGUERO (Main Deck)."
        if h > 244: analisis_dimensiones = "❌ RECHAZADO: Excede altura máxima."

    peso_volumetrico = t_volumen * 167
    peso_tasable = max(t_peso_real, peso_volumetrico)

    # 2. El "Cerebro" procesa la foto si existe
    img_optimizada = None
    if foto:
        raw_bytes = await foto.read()
        img_optimizada = procesar_imagen_para_ia(raw_bytes)

    # 3. Prompt de Especialista Avianca (IAAT/DOT/CBP)
    prompt_tecnico = f"""
    Actúa como Especialista Senior de Carga Avianca. 
    Analiza esta solicitud de "AL CIELO":
    - Rol: {payload.get('rol')} | Guía: {payload.get('awb')} | Tipo: {payload.get('tipo')}
    - Totales: {t_piezas} piezas | {t_peso_real:.2f}kg Real | {peso_volumetrico:.2f}kg Vol.
    - Peso Tasable: {peso_tasable:.2f} kg.
    - Detalle Bultos: {json.dumps(bultos)}
    - Checklist Seguridad: {json.dumps(payload.get('chk'))}

    REGLAS DE RESPUESTA:
    1. Responde con una TABLA de cumplimiento técnica.
    2. Dictamina si vuela o no y bajo qué condiciones.
    3. Si hay imagen, describe etiquetas de seguridad (DGR, Orientación) visibles.
    4. Da una INSTRUCCIÓN DIRECTA (ej: 'Rechazar por falta de fleje' o 'Proceder a Bellies').
    5. Prohibido mencionar IA o modelos de lenguaje.
    6. Idioma: Español.
    """

    res_ia = ""
    metodo = "Gemini"

    try:
        # Intento primario con Gemini
        model = genai.GenerativeModel('gemini-1.5-flash')
        if img_optimizada:
            contenido = [prompt_tecnico, {"mime_type": "image/jpeg", "data": img_optimizada}]
        else:
            contenido = [prompt_tecnico]
        
        response = model.generate_content(contenido)
        res_ia = response.text
    except Exception as e:
        print(f"Falla Gemini: {e}")
        # Salto a OpenAI (Backup)
        try:
            metodo = "OpenAI (Backup)"
            messages = [{"role": "user", "content": [{"type": "text", "text": prompt_tecnico}]}]
            if img_optimizada:
                b64 = base64.b64encode(img_optimizada).decode('utf-8')
                messages[0]["content"].append({
                    "type": "image_url", 
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                })
            
            chat_res = client_openai.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=800
            )
            res_ia = chat_res.choices[0].message.content
        except Exception as e2:
            print(f"Falla OpenAI: {e2}")
            res_ia = "Error en los sistemas de asesoría. Revise las API Keys o créditos."
            metodo = "Ninguno"

    return {
        "status": "COMPLETO",
        "asesoria_tecnica": res_ia,
        "peso_tasable": round(peso_tasable, 2),
        "fuente": metodo
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
