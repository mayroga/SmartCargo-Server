from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn, os

app = FastAPI(title="SMARTCARGO SERVER PRO FINAL")

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
    explicaciones = []

    piezas = data.get("piezas", [])
    tipo = data.get("tipo", "GENERAL")
    texto = data.get("input_texto", "").upper()

    if len(piezas) == 0:
        return {
            "status":"STOP",
            "alertas":["NO HAY CARGA REGISTRADA"],
            "soluciones":["Debe ingresar al menos una pieza física"],
            "explicaciones":["Sin carga no existe operación logística"],
            "documentos":[]
        }

    total_real = 0
    total_vol = 0
    max_h = 0
    fotos_ok = True

    for i,p in enumerate(piezas):

        try:
            l = float(p["l"])
            w = float(p["w"])
            h = float(p["h"])
            peso = float(p["peso"])
            foto = p.get("foto", False)

            if not foto:
                fotos_ok = False

            if l<=0 or w<=0 or h<=0 or peso<=0:
                alertas.append(f"PIEZA {i+1} INVÁLIDA")
                soluciones.append("Ingrese dimensiones reales mayores a 0")
                explicaciones.append("El sistema requiere datos físicos reales para cálculo aeronáutico")
                continue

            vol = (l*w*h)/166

            total_real += peso
            total_vol += vol

            if h > max_h: max_h = h

            if h > 63:
                alertas.append(f"ALTURA EXCESIVA PZA {i+1}")
                soluciones.append("Mover a vuelo carguero (CAO)")
                explicaciones.append("Altura supera límite belly aircraft")

        except:
            alertas.append(f"ERROR PIEZA {i+1}")
            soluciones.append("Verificar valores numéricos")
            explicaciones.append("Datos corruptos o incompletos")

    if not fotos_ok:
        alertas.append("FALTA FOTO DE CARGA")
        soluciones.append("Tomar foto visible de cada pieza")
        explicaciones.append("El counter exige evidencia visual del estado físico")

    # 🔴 MOTOR AVANZADO POR TIPO
    if tipo == "DGR":
        docs += [
            "Shipper Declaration (3 originales - pouch)",
            "MSDS (copia)",
            "UN Packaging Cert (copia externa)"
        ]
        alertas.append("CARGA PELIGROSA (DGR)")
        soluciones.append("Requiere DG Specialist + etiquetas IATA")
        explicaciones.append("Regulado por IATA DGR")

    if tipo == "PER":
        docs += [
            "Certificado sanitario",
            "Control de temperatura",
            "Registro cadena frío"
        ]
        soluciones.append("Usar gel pack / dry ice certificado")
        explicaciones.append("Carga sensible al tiempo")

    if tipo == "VAL":
        docs += [
            "Manifiesto VAL",
            "Custodia armada",
            "Seguro carga"
        ]
        soluciones.append("Coordinar seguridad aeropuerto")
        explicaciones.append("Carga de alto valor")

    if tipo == "HUM":
        docs += [
            "Acta defunción",
            "Permiso tránsito",
            "Certificado embalsamamiento"
        ]
        soluciones.append("Proceso prioritario")
        explicaciones.append("Carga sensible y regulada")

    if tipo == "AVI":
        docs += [
            "Certificado veterinario",
            "Jaula IATA",
            "Permiso importación"
        ]
        soluciones.append("Revisión bienestar animal")
        explicaciones.append("Live animals regulations")

    if tipo == "MED":
        docs += [
            "Registro sanitario",
            "Control temperatura",
            "Factura"
        ]
        soluciones.append("Validar cadena farmacéutica")
        explicaciones.append("Carga médica crítica")

    if tipo == "ICE":
        docs += [
            "Declaración Dry Ice",
            "Peso neto CO2",
            "Etiqueta UN1845"
        ]
        soluciones.append("Ventilación y límites de peso")
        explicaciones.append("Regulado como mercancía peligrosa parcial")

    status = "FLY READY" if len(alertas)==0 else "STOP / HOLD"

    return {
        "status": status,
        "peso_cobrable": round(max(total_real,total_vol),2),
        "alertas": alertas,
        "soluciones": soluciones,
        "explicaciones": explicaciones,
        "documentos": docs,
        "avion": "CAO" if max_h>63 else "PAX"
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
