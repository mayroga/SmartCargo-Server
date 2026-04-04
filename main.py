from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn, os

app = FastAPI(title="SMARTCARGO SERVER PRO V4")

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
    docs = []

    piezas = data.get("piezas", [])
    tipo = data.get("tipo", "GENERAL")

    if len(piezas) == 0:
        return {
            "status":"STOP",
            "alertas":["NO HAY CARGA"],
            "soluciones":["Debe registrar al menos una pieza"]
        }

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
                alertas.append(f"PIEZA {i+1} INVÁLIDA")
                soluciones.append("Ingrese dimensiones reales (no 0)")
                continue

            vol = (l*w*h)/166

            total_real += peso
            total_vol += vol

            if h > max_h: max_h = h

            if h > 63:
                alertas.append(f"ALTURA EXCESIVA PZA {i+1}")
                soluciones.append("Mover a carguero CAO")

        except:
            alertas.append(f"ERROR PIEZA {i+1}")
            soluciones.append("Verificar datos numéricos")

    # 🔴 MOTOR POR TIPO DE CARGA
    if tipo == "DGR":
        docs += ["Shipper Declaration (3 copias)", "MSDS", "UN Packaging Cert"]
        alertas.append("CARGA DGR")
        soluciones.append("Requiere especialista DG + etiquetas IATA")

    if tipo == "PER":
        docs += ["Certificado sanitario", "Control temperatura"]
        soluciones.append("Usar gel pack o dry ice certificado")

    if tipo == "VAL":
        docs += ["Manifiesto VAL", "Custodia armada"]
        soluciones.append("Coordinación seguridad aeropuerto")

    if tipo == "HUM":
        docs += ["Acta defunción", "Permiso tránsito"]
        soluciones.append("Manejo prioritario y respetuoso")

    status = "APROBADO" if len(alertas)==0 else "STOP / HOLD"

    return {
        "status": status,
        "peso_cobrable": round(max(total_real,total_vol),2),
        "alertas": alertas,
        "soluciones": soluciones,
        "documentos": docs,
        "avion": "CAO" if max_h>63 else "PAX"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
