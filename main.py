import os
import json
import re
import google.generativeai as genai
from openai import OpenAI
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI(title="SMARTGOSERVER - Asesoría Técnica de Carga")

# Configuración de Claves desde variables de entorno
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")

# Inicialización de servicios de IA
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

client_openai = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

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
    return HTMLResponse("<h1>Error: app.html no encontrado en la carpeta static</h1>")

async def asesoria_gemini(prompt, image_data=None):
    model = genai.GenerativeModel('gemini-1.5-flash')
    if image_data:
        content = [prompt, {"mime_type": "image/jpeg", "data": image_data}]
    else:
        content = [prompt]
    response = model.generate_content(content)
    return response.text

async def asesoria_openai(prompt, image_data=None):
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
        max_tokens=800
    )
    return response.choices[0].message.content

@app.post("/api/evaluar")
async def api_evaluar_carga(
    data: str = Form(...), 
    foto: UploadFile = File(None)
):
    payload = json.loads(data)
    errores = []
    
    # 1. Extracción y validación de bultos (Lógica CargoLink)
    bultos = payload.get("detalle_bultos", [])
    t_piezas = 0
    t_peso_real = 0
    t_volumen = 0
    tiene_sobredimension = False

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

            if h > 244:
                errores.append(f"RECHAZO: Bulto de {h}cm excede el límite máximo de altura.")
            elif h > 160:
                tiene_sobredimension = True
        except ValueError:
            continue

    # 2. Cálculos técnicos de cobro
    t_peso_vol = t_volumen * 167
    peso_tasable = max(t_peso_real, t_peso_vol)

    # 3. Validación de Guía (AWB)
    awb = payload.get("awb", "").strip()
    if awb and not re.match(r"^\d{3}-\d{8}$", awb):
        errores.append("AWB inválido. Debe ser XXX-XXXXXXXX.")

    # 4. Construcción del Prompt Profesional (Sin mencionar IA)
    prompt_tecnico = f"""
    Actúa como Especialista Senior en Carga Aérea (IAAT, DOT, CBP). 
    Analiza la siguiente carga para despacho:
    - Rol: {payload.get('rol')}
    - Tipo: {payload.get('tipo')}
    - Guía: {awb}
    - Total Piezas: {t_piezas}
    - Peso Real Total: {t_peso_real:.2f} kg
    - Peso Volumétrico: {t_peso_vol:.2f} kg
    - Peso Tasable (Chargeable Weight): {peso_tasable:.2f} kg
    - Detalle de bultos: {json.dumps(bultos)}
    - Checklist Seguridad: {json.dumps(payload.get('chk'))}

    INSTRUCCIONES:
    1. Responde con una TABLA de cumplimiento que incluya (Parámetro | Estado | Observación).
    2. Dictamina si la carga es apta para "Bellies" (Aviones de pasajeros) o requiere "Freighter" (Carguero).
    3. Si hay piezas que exceden límites, indica exactamente cuáles.
    4. Da una INSTRUCCIÓN DIRECTA final (ej: 'Re-etiquetar bultos 2 y 3 y enviar a zona de fumigación').
    5. Prohibido mencionar que eres una inteligencia artificial o modelo de lenguaje.
    6. Idioma: Español.
    """

    # 5. Procesamiento de imagen si existe
    img_bytes = await foto.read() if foto else None
    res_asesoria = ""
    fuente_usada = "Gemini"

    try:
        # Intento A: Gemini
        res_asesoria = await asesoria_gemini(prompt_tecnico, img_bytes)
    except Exception as e:
        # Intento B: OpenAI (Failover)
        try:
            res_asesoria = await asesoria_openai(prompt_tecnico, img_bytes)
            fuente_usada = "OpenAI (Backup)"
        except Exception as e2:
            res_asesoria = "Error en los sistemas de asesoría. Por favor, consulte el manual técnico de Avianca."
            fuente_usada = "Ninguna"

    # 6. Respuesta final
    status = "READY" if not errores else "RECHAZADO"
    
    return {
        "status": status,
        "errores": errores,
        "asesoria_tecnica": res_asesoria,
        "peso_tasable": round(peso_tasable, 2),
        "fuente": fuente_usada
    }

if __name__ == "__main__":
    # Puerto 10000 para compatibilidad con Render
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
