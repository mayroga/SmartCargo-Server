from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn, os

app = FastAPI(title="SMARTCARGO CORE V3")

if not os.path.exists("static"): os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html", encoding="utf-8") as f:
        return f.read()

@app.post("/api/validar")
async def validar(data: dict):

    alertas = []
    soluciones = []

    piezas = data.get("piezas", [])

    if len(piezas) == 0:
        alertas.append("NO HAY PIEZAS REGISTRADAS")
        soluciones.append("Debe ingresar al menos 1 pieza con peso y dimensiones.")
        return {"status":"STOP", "alertas":alertas, "soluciones":soluciones}

    total_real = 0
    total_vol = 0
    max_h = 0

    for i,p in enumerate(piezas):
        try:
            l = float(p["l"])
            w = float(p["w"])
            h = float(p["h"])
            peso = float(p["peso"])

            if l<=0 or w<=0 or h<=0 or peso<=0:
                alertas.append(f"DATOS INVÁLIDOS PIEZA {i+1}")
                soluciones.append("No se permiten valores 0. Verifique dimensiones reales.")
                continue

            vol = (l*w*h)/166

            total_real += peso
            total_vol += vol

            if h > max_h:
                max_h = h

            # ALTURA
            if h > 63:
                alertas.append(f"ALTURA EXCESIVA PIEZA {i+1}")
                soluciones.append("Mover a vuelo carguero (CAO).")

        except:
            alertas.append(f"ERROR EN PIEZA {i+1}")
            soluciones.append("Revisar datos numéricos.")

    tipo = data.get("tipo")

    # DGR
    if tipo == "DGR":
        alertas.append("CARGA DGR DETECTADA")
        soluciones.append("Requiere Shipper Declaration + embalaje UN.")

    # PER
    if tipo == "PER":
        alertas.append("CONTROL DE TEMPERATURA REQUERIDO")
        soluciones.append("Agregar gel pack o dry ice certificado.")

    status = "APROBADO" if len(alertas)==0 else "STOP / HOLD"

    return {
        "status": status,
        "peso_cobrable": round(max(total_real,total_vol),2),
        "alertas": alertas,
        "soluciones": soluciones,
        "tipo_avion": "CAO" if max_h>63 else "PAX"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
