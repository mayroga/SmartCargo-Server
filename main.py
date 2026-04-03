from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import re

app = FastAPI(title="AL CIELO - SmartCargo Expert System")

if not os.path.exists("static"): os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- BASE DE CONOCIMIENTO TÉCNICO ---
IATA_TABLE = {
    "DGR": {"class": "Dangerous Goods", "docs": ["DGD (Original)", "MSDS", "Checksheet"]},
    "PER": {"class": "Perishable", "docs": ["Phytosanitary Cert", "Health Cert"]},
    "AVI": {"class": "Live Animals", "docs": ["Vet Health Cert", "IATA LAR Compliance"]},
    "HUM": {"class": "Human Remains", "docs": ["Death Certificate", "Embalming Cert"]},
    "VAL": {"class": "Valuable Cargo", "docs": ["Armed Escort", "Vulnerable Cargo Protocol"]}
}

@app.post("/api/evaluar")
async def evaluar_especialista(data: dict):
    errores = []
    soluciones = []
    alertas_gobierno = [] # Para evitar multas de CBP/TSA
    
    # Datos de entrada
    lang = data.get("lang", "es")
    awb = data.get("awb", "").strip()
    codigo = data.get("codigo", "GEN")
    alto_max = float(data.get("alto") or 0)
    peso_total = float(data.get("pesoTotal") or 0)
    texto_notas = data.get("analisisTexto", "").upper()
    
    # Checkboxes de cumplimiento
    chk_wood = data.get("chkWood", False)
    chk_dgr = data.get("chkDGR", False)
    chk_emb = data.get("chkEmb", False)

    # 1. VALIDACIÓN ESTRUCTURAL (AERONAVE)
    # Regla Avianca: Bellies (PAX) max 160cm. Main Deck (Freighter) max 244cm.
    if alto_max > 160 and alto_max <= 243:
        errores.append("Altura incompatible con aviones de pasajeros (PAX)." if lang=="es" else "Height exceeds PAX aircraft limits.")
        soluciones.append("✈️ ACCIÓN: Solicitar espacio en Carguero B767F o desarmar pallet para Bellies.")
    elif alto_max > 243:
        errores.append("Carga excede dimensiones máximas de puerta (Out of Gauge)." if lang=="es" else "OOG: Height exceeds door limits.")
        soluciones.append("🛠️ RESOLUCIÓN: Realizar 'Breakdown' (Desarme). La carga no entra en ningún equipo actual.")

    if peso_total > 4500: # Límite sugerido para evitar daños en rodillos de bodega
        soluciones.append("⚖️ AVISO: Peso elevado. Distribuir en dos ULDs para no exceder límites de presión por pie cuadrado.")

    # 2. PROTOCOLO CBP / DEPARTAMENTO DE AGRICULTURA (DOT)
    if not chk_wood:
        alertas_gobierno.append("⚠️ ALERTA CBP: Madera sin sello NIMF-15 detectada.")
        soluciones.append("🪵 ACCIÓN LEGAL: Cambiar inmediatamente a pallet plástico o fumigar. Multas estimadas: $1,000 - $15,000 USD.")

    # 3. SEGURIDAD TSA (KNOWN vs UNKNOWN)
    if data.get("seguridad") == "Unknown":
        errores.append("Shipper Desconocido (Unknown Shipper)." if lang=="es" else "Unknown Shipper Alert.")
        soluciones.append("🛡️ PROTOCOLO TSA: Aplicar inspección física 100% y Rayos X. Retener 48h si el perfil de riesgo lo indica.")

    # 4. MERCANCÍAS PELIGROSAS (DGR) E INCOMPATIBILIDADES
    if codigo == "DGR" or any(x in texto_notas for x in ["LITHIUM", "BATERIA", "UN3481", "DRY ICE"]):
        if not chk_dgr:
            errores.append("Falta DGD (Shipper's Declaration) para carga peligrosa.")
            soluciones.append("🚨 BLOQUEO: No recibir. Exigir original con borde rojo. Verificar UN Number contra MSDS.")
        
        # Detección de incompatibilidad (Ejemplo: Ácidos + Inflamables)
        if "ACID" in texto_notas and "FLAMMABLE" in texto_notas:
            errores.append("INCOMPATIBILIDAD QUÍMICA DETECTADA.")
            soluciones.append("🧪 ACCIÓN: Separar bultos según Tabla de Segregación IATA (mínimo 3 metros de distancia).")

    # 5. PROTOCOLO AVIANCA (Interline / COMAT)
    if not awb.startswith("045"):
        soluciones.append("🔄 INFO: AWB No-Avianca. Verificar si es Interline con sello de transferencia original.")

    # 6. ESTADO FINAL
    es_aprobada = len(errores) == 0
    status = "VUELO AUTORIZADO (FLY READY)" if es_aprobada else "CARGA EN RETENCIÓN (ON HOLD)"
    
    # Unificamos alertas de gobierno en la respuesta
    if alertas_gobierno:
        errores = alertas_gobierno + errores

    return {
        "status": status,
        "errores": errores,
        "soluciones": soluciones,
        "docs_requeridos": IATA_TABLE.get(codigo, {}).get("docs", ["AWB", "Manifest"])
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
