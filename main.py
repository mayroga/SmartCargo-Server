from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

app = FastAPI(title="AURA SMARTCARGO ADVISORY")

# Crear carpeta static si no existe y montar para archivos CSS/JS/IMG
if not os.path.exists("static"): 
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- PROTOCOLO DE ASESORÍA MIA-AVIANCA ---
@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/asesorar")
async def asesorar(data: dict):
    # 1. Extracción de datos enviados por el HTML
    awb = data.get("awb", "").strip()
    naturaleza = data.get("naturaleza", "GEN")
    tipo_vuelo = data.get("tipo_vuelo", "PAX")
    piezas = data.get("piezas", [])
    pouch = data.get("pouch", [])
    
    soluciones = []
    acciones = []
    
    # 2. Validación de Prefijo (045 Avianca / 729 Tampa)
    prefix = awb[:3]
    if prefix not in ["045", "729"]:
        soluciones.append(f"PREFIJO {prefix} AJENO A RED AVIANCA.")
        acciones.append("ASESORÍA: Verificar si es carga INTERLINE o COMAT. De lo contrario, solicitar re-emisión de AWB.")

    # 3. Validación de Dimensiones y Equipo (Belly vs CAO)
    total_real = 0
    total_vol = 0
    max_h = 0
    
    for i, p in enumerate(piezas):
        try:
            l, w, h = float(p['l']), float(p['w']), float(p['h'])
            c = int(p['cant'])
            p_r = float(p['p_real'])
            
            total_real += p_r * c
            total_vol += (l * w * h * c) / 166
            if h > max_h: max_h = h
            
            if h > 63 and tipo_vuelo == "PAX":
                soluciones.append(f"PIEZA {i+1} CON ALTURA DE {h}in EXCEDE LIMITE PAX.")
                acciones.append("SOLUCIÓN: La carga no cabe en avión de pasajeros. Solicitar reserva en CARGUERO (CAO).")
        except: continue

    # 4. Validación de Papelería (Pouch)
    docs_minimos = {
        "DGR": ["DGD", "MSDS", "CHECKLIST"],
        "PER": ["PHITO", "SANITARY"],
        "GEN": ["INVOICE", "PACKING LIST"]
    }
    
    faltantes = [d for d in docs_minimos.get(naturaleza, []) if d not in pouch]
    if faltantes:
        soluciones.append(f"FALTAN DOCUMENTOS CRÍTICOS EN POUCH.")
        acciones.append(f"ACCIÓN: Solicitar urgentemente: {', '.join(faltantes)} para evitar retención en Aduana.")

    return {
        "status": "PLAN DE VUELO GENERADO",
        "p_cobrable": round(max(total_real, total_vol), 2),
        "equipo": "CAO" if max_h > 63 else "PAX/CAO OK",
        "soluciones": soluciones,
        "acciones": acciones
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
