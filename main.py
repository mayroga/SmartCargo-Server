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
    codigos = data.get("codigos", [])
    awb = data.get("awb", "")
    id_chofer = data.get("idChofer", "")
    
    # Validación de Identificación (Evitar "vire" de carga)
    if not awb.startswith("045"):
        errores.append("Prefijo AWB incorrecto para Avianca.")
        soluciones.append("Rectificar Master AWB o verificar si es transferencia Interline.")
    
    if not id_chofer:
        errores.append("Falta Identificación del Transportista.")
        soluciones.append("Registrar ID/Licencia para control de acceso y seguridad TSA.")

    # Lógica de Counter: Documentación
    if not data.get("chkFacturas"):
        errores.append("Facturas Comerciales no detectadas.")
        soluciones.append("Incluir 3 copias legibles de la factura comercial (dentro y fuera del sobre).")
    
    if "DGR" in codigos and not data.get("chkDGR"):
        errores.append("Falta Declaración de Mercancías Peligrosas (DGD).")
        soluciones.append("Presentar DGD con borde rojo, firmada y con UN Number verificado.")
    
    if "PER" in codigos or "AVI" in codigos:
        errores.append("Requiere permisos fitosanitarios/veterinarios originales.")
        soluciones.append("Asegurar que los originales van adheridos al sobre de la guía para inspección inmediata.")

    # Estado de la Asesoría
    status = "CARGA EN RETENCIÓN (ON HOLD)" if errores else "VUELO AUTORIZADO (FLY READY)"
    
    return {
        "status": status, 
        "errores": errores, 
        "soluciones": soluciones,
        "prechequeo": data.get("prechequeo", "")
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
