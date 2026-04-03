from fastapi import FastAPI, Request
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

@app.post("/api/auditoria_mortal")
async def auditoria_mortal(data: dict):
    # --- LOGICA DE PESO TÉCNICO (COUNTER/TSA/IATA) ---
    perfil = data.get("perfil", "Desconocido")
    naturaleza = data.get("naturaleza", "GEN")
    piezas = data.get("piezas", [])
    pouch = data.get("pouch", {})
    alertas, soluciones = [], []
    
    # 1. VALIDACIÓN DE IDENTIDAD Y ROL
    if not data.get("id_chofer") or not data.get("id_awb"):
        alertas.append("FALLO DE IDENTIFICACIÓN: Datos mínimos de AWB o ID ausentes.")
        soluciones.append("Es obligatorio registrar AWB y ID del portador para iniciar la cadena de custodia.")

    # 2. DOCUMENTACIÓN SEGÚN NATURALEZA (EL SOBRE)
    docs_requeridos = {
        "GEN": ["Factura Original", "Packing List"],
        "DGR": ["DGD (Shipper's Declaration)", "MSDS", "Etiquetas de Clase"],
        "PER": ["Certificado Fitosanitario", "Factura", "Guía de Temperatura"],
        "VAL": ["Manifiesto de Valores", "Custodia Armada", "Sello de Seguridad"]
    }
    
    reqs = docs_requeridos.get(naturaleza, [])
    for r in reqs:
        if r not in pouch.get("documentos_fisicos", []):
            alertas.append(f"FALTA DOCUMENTO: {r}")
            soluciones.append(f"Para carga {naturaleza}, es obligatorio presentar {r} en original y sin tachaduras.")

    # 3. AUDITORÍA FÍSICA PIEZA POR PIEZA
    p_real_total, p_vol_total = 0, 0
    for i, p in enumerate(piezas):
        l, w, h, cant = float(p['l']), float(p['w']), float(p['h']), int(p['cant'])
        p_real = float(p['p_real']) * cant
        v_total = (l * w * h * cant) / 166 # Formula IATA Lbs
        
        p_real_total += p_real
        p_vol_total += v_total
        
        if h > 63 and data.get("equipo") == "PAX":
            alertas.append(f"PIEZA #{i+1}: Supera 63\" de altura.")
            soluciones.append(f"No apta para Belly (Pasajeros). Debe volar en Freighter o Main Deck.")

    # 4. PROCESAMIENTO DE VOZ/TEXTO (EL BOTÓN INTELIGENTE)
    analisis_voz = data.get("analisis_voz", "").upper()
    if "DAÑO" in analisis_voz or "HUECO" in analisis_voz or "MOJADO" in analisis_voz:
        alertas.append("ALERTA DE INTEGRIDAD: Reporte de muelle indica daños físicos.")
        soluciones.append("No aceptar hasta que el Shipper firme Carta de Responsabilidad (LOI).")

    return {
        "status": "RECHAZO TÉCNICO" if alertas else "FLY READY",
        "perfil_auditado": perfil,
        "chargeable": round(max(p_real_total, p_vol_total), 2),
        "real": round(p_real_total, 2),
        "alertas": alertas,
        "soluciones": soluciones
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
