from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import re

app = FastAPI(title="SMARTGOSERVER - Asesoría Técnica de Carga")

# Carpeta estática
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Página principal
@app.get("/", response_class=HTMLResponse)
async def home():
    html_path = os.path.join("static", "app.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Error: app.html no encontrado en /static</h1>")

# API de evaluación de carga
@app.post("/api/evaluar")
async def api_evaluar_carga(data: dict):
    errores = []
    soluciones = []

    # Extraer datos
    rol = data.get("rolUsuario", "")
    awb = data.get("awb", "").strip()
    codigo = data.get("codigoCarga", "")
    piezas = int(data.get("piezas") or 0)
    pesoTotal = float(data.get("pesoTotal") or 0)
    alto = float(data.get("alto") or 0)
    pesoVol = float(data.get("pesoVolumetrico") or 0)
    known = data.get("knownShipper", "")
    horaCamion = data.get("horaCamion", "")
    cutoff = data.get("cutoff", "18:00")

    # Checklist usuario
    dryIce = data.get("chkDryIce", False)
    dgr = data.get("chkDGR", False)
    animales = data.get("chkAnimales", False)
    perecederos = data.get("chkPerecederos", False)
    embalaje = data.get("chkEmbalaje", False)
    etiquetas = data.get("chkEtiquetas", False)
    fleje = data.get("chkFleje", False)
    orientacion = data.get("chkOrientacion", False)

    # Validaciones básicas
    if not rol: errores.append("Seleccione rol del usuario.")
    if not re.match(r"^\d{3}-\d{8}$", awb):
        errores.append("Formato AWB inválido (XXX-12345675).")
        soluciones.append("Corregir la guía con 3 dígitos, guion y 8 números.")
    if piezas < 1: errores.append("Número de piezas inválido.")
    if not codigo: errores.append("Seleccione tipo de carga.")
    if not known: errores.append("Indique si es Known Shipper.")
    if alto > 244: errores.append("Alto excede límite carguero (244cm).")
    if 160 < alto <= 244: errores.append("Solo puede ir en Main Deck (carguero).")
    if pesoTotal > 6800: errores.append("Peso excede límite pallet 6800kg.")
    if pesoVol > pesoTotal: errores.append("Peso volumétrico mayor que peso real.")
    if horaCamion and horaCamion > cutoff: errores.append("Camión llega después de cutoff.")

    # Validaciones checklist inteligentes por tipo de carga
    tipo_checklist_obligatorio = {
        "GEN": {"DryIce": False, "DGR": False, "Animales": False, "Perecederos": False, "Embalaje": True, "Etiquetas": True, "Fleje": True, "Orientacion": True},
        "PER": {"DryIce": True, "DGR": False, "Animales": False, "Perecederos": True, "Embalaje": True, "Etiquetas": True, "Fleje": True, "Orientacion": True},
        "HUM": {"DryIce": False, "DGR": False, "Animales": False, "Perecederos": False, "Embalaje": True, "Etiquetas": True, "Fleje": True, "Orientacion": True},
        "VAL": {"DryIce": False, "DGR": False, "Animales": False, "Perecederos": False, "Embalaje": True, "Etiquetas": True, "Fleje": True, "Orientacion": True},
        "AVI": {"DryIce": False, "DGR": False, "Animales": True, "Perecederos": False, "Embalaje": True, "Etiquetas": True, "Fleje": True, "Orientacion": True},
        "DGR": {"DryIce": False, "DGR": True, "Animales": False, "Perecederos": False, "Embalaje": True, "Etiquetas": True, "Fleje": True, "Orientacion": True},
    }

    checklist_usuario = {
        "DryIce": dryIce,
        "DGR": dgr,
        "Animales": animales,
        "Perecederos": perecederos,
        "Embalaje": embalaje,
        "Etiquetas": etiquetas,
        "Fleje": fleje,
        "Orientacion": orientacion
    }

    # Validación proactiva
    for item, requerido in tipo_checklist_obligatorio.get(codigo, {}).items():
        marcado = checklist_usuario.get(item, False)
        if requerido and not marcado:
            errores.append(f"Falta {item} obligatorio para tipo de carga {codigo}.")
            soluciones.append(f"Marcar {item} correctamente según normativas.")
        elif not requerido and marcado:
            errores.append(f"{item} no aplica para tipo de carga {codigo}, remover selección.")
            soluciones.append(f"Desmarcar {item} para cumplir reglas del tipo de carga.")

    # Estado final
    status = "READY" if not errores else "RECHAZADO"
    if errores and len(errores) <= 3: status = "ALERTA"

    return {
        "status": status,
        "errores": errores,
        "soluciones": soluciones
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=True)
