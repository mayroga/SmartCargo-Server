from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

app = FastAPI()
if not os.path.exists("static"): os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html", "r", encoding="utf-8") as f: return f.read()

@app.post("/api/evaluar")
async def evaluar(data: dict):
    errores, soluciones = [], []
    alto = data.get("alto", 0)
    codigo = data.get("codigo", "")
    awb = data.get("awb", "")

    # 1. Validación AWB
    if not awb.startswith("045"):
        errores.append("AWB no pertenece a Avianca (045).")
        soluciones.append("Verificar con el cliente si es una guía Interline o COMAT.")

    # 2. Regla de Altura Avianca
    if alto > 160:
        errores.append(f"Altura de {alto}cm excede límite de avión de pasajeros (Bellies).")
        soluciones.append("Solicitar espacio en avión carguero B767F o realizar 'Breakdown' (re-estibar a <160cm).")
    else:
        soluciones.append("Altura apta para Bellies y Main Deck.")

    # 3. Seguridad y Naturaleza
    if codigo == "DGR" and not data.get("chkDGR"):
        errores.append("Carga DGR declarada pero sin confirmación de Shipper's Declaration.")
        soluciones.append("🚨 NO RECIBIR. Solicitar DGD original con borde rojo y verificar UN Number.")

    if not data.get("chkEmbalaje"):
        errores.append("Embalaje dañado / Pallet roto.")
        soluciones.append("Re-embalar o cambiar pallet de madera por plástico para evitar rechazo en counter.")

    status = "CARGA EN RETENCIÓN (ON HOLD)" if errores else "VUELO AUTORIZADO (FLY READY)"
    
    return {"status": status, "errores": errores, "soluciones": soluciones}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
