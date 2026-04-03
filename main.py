import os
import json
import re
import google.generativeai as genai
from openai import OpenAI
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI(title="SMARTGOSERVER - Asesoría Técnica")

# Configuración de Claves desde Render
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")

# Inicializar Clientes
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
client_openai = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home():
    html_path = os.path.join("static", "app.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Error: app.html no encontrado</h1>")

async def asesoría_gemini(prompt, image_data=None):
    model = genai.GenerativeModel('gemini-1.5-flash')
    if image_data:
        content = [prompt, {"mime_type": "image/jpeg", "data": image_data}]
    else:
        content = [prompt]
    response = model.generate_content(content)
    return response.text

async def asesoría_openai(prompt, image_data=None):
    import base64
    messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    if image_data:
        base64_image = base64.b64encode(image_data).decode('utf-8')
        messages[0]["content"].append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
        })
    
    response = client_openai.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=500
    )
    return response.choices[0].message.content

@app.post("/api/evaluar")
async def api_evaluar_carga(
    data: str = Form(...), 
    foto: UploadFile = File(None)
):
    payload = json.loads(data)
    errores = []
    soluciones = []
    
    # Validaciones Lógicas de Negocio (Mantenemos tu lógica original)
    awb = payload.get("awb", "").strip()
    if not re.match(r"^\d{3}-\d{8}$", awb):
        errores.append("Formato AWB inválido.")
        soluciones.append("Corregir guía: 3 dígitos, guion, 8 dígitos.")
    
    alto = float(payload.get("alto") or 0)
    if alto > 244: 
        errores.append("Alto excede límite (244cm).")
        soluciones.append("Carga sobredimensionada: requiere equipo especial.")

    # Prompt de Especialista IAAT / DOT / CBP
    prompt_tecnico = f"""
    Eres Especialista Senior de Carga Avianca. Analiza: {json.dumps(payload)}.
    Si hay imagen, interprétala técnicamente.
    REGLAS: 
    - Responde con una TABLA de cumplimiento (Punto | Estado | Observación).
    - No menciones IA ni ChatGPT. 
    - Da una INSTRUCCIÓN DIRECTA (ej: 'Llevar pallet a fumigar').
    - Idioma: Español.
    """

    img_bytes = await foto.read() if foto else None
    res_ia = ""
    metodo_usado = "Gemini"

    try:
        # Intento primario con Gemini
        res_ia = await asesoría_gemini(prompt_tecnico, img_bytes)
    except Exception as e:
        # Salto automático a OpenAI si falla Gemini
        try:
            res_ia = await asesoría_openai(prompt_tecnico, img_bytes)
            metodo_usado = "OpenAI (Backup)"
        except Exception as e2:
            res_ia = "Error crítico: Ambos sistemas de asesoría están fuera de servicio."
            metodo_usado = "Ninguno"

    status = "READY" if not errores else "RECHAZADO"
    
    return {
        "status": status,
        "errores": errores,
        "soluciones": soluciones,
        "asesoria_tecnica": res_ia,
        "fuente": metodo_usado
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=True)
