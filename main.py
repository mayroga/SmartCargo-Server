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
    awb = data.get("awb", "")
    alto = data.get("alto", 0)
    codigo = data.get("codigo", "")

    # Reglas de Negocio SmartCargo
    if not awb.startswith("045"):
        errores.append("Prefijo No-Avianca.")
        soluciones.append("Revisar si es un vuelo compartido o Interline.")

    if alto > 160:
        errores.append("Exceso de altura para Bellies.")
        soluciones.append("Llevar a muelle de carguero o solicitar breakdown inmediato.")

    if not data.get("chkWood"):
        errores.append("Madera sin tratamiento visible.")
        soluciones.append("Cambiar por pallet plástico para evitar multa CBP.")

    if codigo == "DGR" and not data.get("chkDGR"):
        errores.append("Falta DGD de Mercancía Peligrosa.")
        soluciones.append("No recibir carga. Exigir Shipper's Declaration original.")

    status = "RECHAZADA / ON HOLD" if errores else "APROBADA / FLY READY"
    
    return {"status": status, "errores": errores, "soluciones": soluciones}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
