import os, re, json
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="AL CIELO - SmartCargo Advisory")

if not os.path.exists("static"): os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/evaluar")
async def api_evaluar_carga(data: dict):
    errores = []
    soluciones = []
    
    # Datos Técnicos
    awb = data.get("awb", "").strip()
    codigo = data.get("codigoCarga", "")
    piezas = int(data.get("piezas") or 0)
    peso_total = float(data.get("pesoTotal") or 0)
    alto = float(data.get("alto") or 0)
    peso_vol = float(data.get("pesoVolumetrico") or 0)
    cutoff = data.get("cutoff", "18:00")
    hora_camion = data.get("horaCamion", "")

    # 1. Validación de Guía (AWB)
    if not re.match(r"^\d{3}-\d{8}$", awb):
        errores.append("Formato AWB inválido (Debe ser XXX-XXXXXXXX).")
        soluciones.append("💡 Rectificar: Use 3 dígitos del transportista, guion y 8 correlativos.")

    # 2. Límites de Aeronavegabilidad (Avianca/General)
    if alto > 244:
        errores.append("Altura crítica: Excede el límite de carguero (244cm).")
        soluciones.append("💡 Rectificar: Re-paletizar o desglosar bultos para bajar la altura.")
    elif alto > 160:
        errores.append("Restricción de Equipo: Solo apto para MAIN DECK (Carguero).")
        soluciones.append("💡 Consultar: Verificar disponibilidad en avión carguero, no cabe en PAX.")

    if peso_total > 6800:
        errores.append("Exceso de peso: Límite estructural de pallet PMC/PAG (6800kg).")
        soluciones.append("💡 Solución: Dividir la carga en dos pallets independientes.")

    # 3. Lógica de Checklist por Tipo de Carga
    checks = {
        "DGR": (data.get("chkDGR"), "Declaración Shipper (DGD) x2 firmada y MSDS."),
        "PER": (data.get("chkPerecederos"), "Certificado Fitosanitario y etiquetas de 'Perishable'."),
        "AVI": (data.get("chkAnimales"), "Certificado Veterinario y contenedor reglamentario IATA LAR."),
        "GEN": (data.get("chkEmbalaje"), "Inspección de flejes y sellos de seguridad.")
    }

    if codigo in checks:
        marcado, consejo = checks[codigo]
        if not marcado:
            errores.append(f"Falta validación obligatoria para carga {codigo}.")
            soluciones.append(f"💡 Documentación: Asegurar {consejo}")

    # 4. Tiempo de Entrega (Logística)
    if hora_camion and hora_camion > cutoff:
        errores.append("Riesgo de Offload: El camión llega después del Cut-Off.")
        soluciones.append("💡 Acción: Solicitar extensión de horario o reprogramar reserva.")

    # Estado Final
    status = "RECHAZADO" if errores else "LISTO PARA VUELO"
    if 0 < len(errores) <= 2: status = "ALERTA / REVISIÓN"

    return {
        "status": status,
        "errores": errores,
        "soluciones": soluciones,
        "peso_tasable": max(peso_total, peso_vol)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
