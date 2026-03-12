from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import os
import json

app = FastAPI(title="SMARTGOSERVER - Asesoría Técnica de Carga")

# Montar carpeta de archivos estáticos
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Carpeta para plantillas HTML
templates = Jinja2Templates(directory="static")

# Ruta principal
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Devuelve la página principal app.html
    """
    html_path = os.path.join("static", "app.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    else:
        return HTMLResponse("<h1>Error: app.html no encontrado en /static</h1>")

# Ruta API para evaluación de carga (opcional)
@app.post("/api/evaluar")
async def api_evaluar_carga(data: dict):
    """
    Recibe JSON con los campos de la carga y devuelve resultado
    """
    errores = []

    # Extraer datos
    rol = data.get("rolUsuario", "")
    awb = data.get("awb", "").strip()
    codigo = data.get("codigoCarga", "")
    piezas = int(data.get("piezas", 0))
    pesoTotal = float(data.get("pesoTotal", 0))
    alto = float(data.get("alto", 0))
    pesoVol = float(data.get("pesoVolumetrico", 0))
    known = data.get("knownShipper", "")
    horaCamion = data.get("horaCamion", "")
    cutoff = data.get("cutoff", "18:00")

    # Validaciones
    if not rol:
        errores.append("Seleccione rol del usuario.")
    if not awb or not awb.match(r"^\d{3}-\d{8}$"):
        errores.append("Formato AWB inválido XXX-12345675.")
    if not codigo:
        errores.append("Seleccione tipo de carga.")
    if piezas < 1:
        errores.append("Número de piezas inválido.")
    if not known:
        errores.append("Indique si es Known Shipper.")
    if alto > 244:
        errores.append("Alto excede límite carguero.")
    if alto > 160 and alto <= 244:
        errores.append("Solo vuela en carguero, no en pasajero.")
    if pesoTotal > 6800:
        errores.append("Peso excede límite pallet.")
    if pesoVol > pesoTotal:
        errores.append("Peso volumétrico mayor que peso real, ajuste reserva.")
    if horaCamion and horaCamion > cutoff:
        errores.append("Camión llega después de cutoff, NO VUELA HOY.")

    # Resultado
    if len(errores) == 0:
        resultado = {"status": "aceptado", "mensaje": "🟢 Carga apta para vuelo hoy."}
    elif len(errores) <= 2:
        resultado = {"status": "aceptado_alerta", "mensaje": "🟡 Aceptado con alerta: " + " | ".join(errores)}
    else:
        resultado = {"status": "rechazado", "mensaje": "🔴 Rechazado: " + " | ".join(errores)}

    return resultado

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=True)
