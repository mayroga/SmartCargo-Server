from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import os

app = FastAPI()

# --- CONFIGURACIÓN TÉCNICA MIA-OPERA ---
OPERACIONES = {
    "AIRLINE_045": "AVIANCA",
    "AIRLINE_729": "TAMPA CARGO",
    "EQUIPOS": {
        "PAX": {"max_h": 63, "desc": "Belly (Pasajeros)"},
        "CAO": {"max_h": 96, "desc": "Freighter (Carguero)"}
    },
    "TARIFA_MIN_MIA": 50.00,
    "RATIO": 166
}

@app.post("/api/asesorar")
async def asesorar(data: dict):
    # Extracción de datos del Agente
    awb = data.get("awb", "")
    tipo_vuelo = data.get("tipo_vuelo", "PAX")
    naturaleza = data.get("naturaleza", "GEN")
    piezas = data.get("piezas", [])
    pouch = data.get("pouch", []) # Documentos físicos confirmados
    
    soluciones = []
    acciones = []
    
    # 1. ASESORÍA DE IDENTIDAD (045/729)
    prefix = awb[:3]
    if prefix not in ["045", "729"]:
        soluciones.append(f"PREFIJO {prefix} NO RECONOCIDO EN COUNTER MIA.")
        acciones.append("ACCIÓN: Validar si es una INTERLINE o COMAT. Si es carga propia, re-emitir bajo 045.")
    
    # 2. ASESORÍA FÍSICA Y SEGURIDAD
    total_real = 0
    total_vol = 0
    max_h = 0
    
    for i, p in enumerate(piezas):
        l, w, h, c = float(p['l'] or 0), float(p['w'] or 0), float(p['h'] or 0), int(p['cant'] or 1)
        peso = float(p['p_real'] or 0)
        total_real += peso * c
        total_vol += (l * w * h * c) / OPERACIONES["RATIO"]
        if h > max_h: max_h = h
        
        # Validación de Equipo vs Altura
        if h > OPERACIONES["EQUIPOS"]["PAX"]["max_h"] and tipo_vuelo == "PAX":
            soluciones.append(f"PIEZA {i+1} EXCEDE ALTURA BELLY ({h} in).")
            acciones.append("SOLUCIÓN: Solicitar cambio a equipo CAO (Carguero) o re-dimensionar estiba si es posible.")

    # 3. ASESORÍA DOCUMENTAL (EL POUCH)
    docs_requeridos = {
        "DGR": ["DGD", "MSDS", "CHECKLIST"],
        "PER": ["PHITO", "SANITARY", "TEMP LOG"],
        "GEN": ["INVOICE", "PACKING LIST"]
    }
    
    faltantes = [d for d in docs_requeridos.get(naturaleza, []) if d not in pouch]
    if faltantes:
        soluciones.append(f"POUCH INCOMPLETO PARA {naturaleza}.")
        acciones.append(f"ACCIÓN: Faltan {', '.join(faltantes)}. Solicitar al Forwarder antes de que el Driver llegue al muelle.")

    return {
        "status": "REVISIÓN PROFESIONAL COMPLETADA",
        "p_cobrable": round(max(total_real, total_vol), 2),
        "equipo_sugerido": "CAO" if max_h > 63 else "PAX/CAO",
        "soluciones": soluciones,
        "acciones": acciones
    }
