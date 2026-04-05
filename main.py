import json
import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI(title="AL CIELO - CONTROL DOCUMENTAL PRO")

# Static
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html", encoding="utf-8") as f:
        return f.read()

# 🔴 MOTOR CENTRAL (CONTROL + PREVENCIÓN)
def validar_documentos(data):
    errores = []
    soluciones = []

    awb_piezas = data.get("awb_piezas")
    packing_piezas = data.get("packing_piezas")

    awb_valor = data.get("awb_valor")
    invoice_valor = data.get("invoice_valor")

    peso_awb = data.get("awb_peso")
    peso_real = data.get("peso_total")

    itn = data.get("itn")

    # 🔴 CRUCES CRÍTICOS
    if awb_piezas != packing_piezas:
        errores.append("PIEZAS NO COINCIDEN (AWB vs PACKING)")
        soluciones.append("Corregir cantidad antes de presentar en counter")

    if awb_valor != invoice_valor:
        errores.append("VALOR NO COINCIDE (AWB vs INVOICE)")
        soluciones.append("Ajustar valor declarado para evitar problema aduanal")

    if peso_awb != peso_real:
        errores.append("PESO DIFERENTE (AWB vs FÍSICO)")
        soluciones.append("Re-pesar carga y actualizar AWB")

    if awb_valor and awb_valor > 2500 and not itn:
        errores.append("FALTA ITN (AES REQUERIDO)")
        soluciones.append("Generar ITN antes de ir al counter")

    return errores, soluciones


@app.post("/api/validar")
async def validar(data: dict):

    alertas = []
    soluciones = []
    acciones = []

    # DATOS
    piezas = data.get("piezas", [])
    texto = data.get("texto", "").upper()

    total_real = 0
    total_vol = 0

    for p in piezas:
        l = float(p.get("l", 0))
        w = float(p.get("w", 0))
        h = float(p.get("h", 0))
        peso = float(p.get("peso", 0))

        total_real += peso
        total_vol += (l * w * h) / 166

    peso_cobrable = round(max(total_real, total_vol), 2)

    # 🔴 VALIDACIÓN DOCUMENTAL
    errores_doc, soluciones_doc = validar_documentos({
        "awb_piezas": data.get("awb_piezas"),
        "packing_piezas": data.get("packing_piezas"),
        "awb_valor": data.get("awb_valor"),
        "invoice_valor": data.get("invoice_valor"),
        "awb_peso": data.get("awb_peso"),
        "peso_total": total_real,
        "itn": data.get("itn")
    })

    alertas.extend(errores_doc)
    soluciones.extend(soluciones_doc)

    # 🔴 PREVENCIÓN INTELIGENTE
    if "MADERA" in texto and "ISPM" not in texto:
        alertas.append("MADERA SIN CERTIFICACIÓN")
        soluciones.append("Usar pallet certificado o plástico")

    if "BATERIA" in texto:
        alertas.append("POSIBLE DGR (BATERÍAS)")
        soluciones.append("Verificar UN3480 / etiqueta requerida")

    if "MOJADO" in texto or "ROTO" in texto:
        alertas.append("CARGA COMPROMETIDA")
        soluciones.append("Re-embalar antes de aceptación")

    # 🔴 ACCIÓN OPERATIVA
    if not alertas:
        estado = "✅ FLY READY"
        acciones.append("Proceder directo a counter")
    else:
        estado = "⛔ HOLD"
        acciones.append("NO PRESENTAR EN COUNTER")
        acciones.append("Corregir antes de intentar despacho")

    return JSONResponse({
        "estado": estado,
        "peso_cobrable": peso_cobrable,
        "alertas": alertas,
        "soluciones": soluciones,
        "acciones": acciones
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
