from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os

app = FastAPI(title="AL CIELO - SmartCargo Advisory MIA")

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- BASE DE DATOS DOCUMENTAL (REGLAS DE ORO AV-MIA) ---
PAPERWORK_DATABASE = {
    "GENERAL": [
        "1 AWB Original (Azul/Verde) + 3 Copias",
        "1 Commercial Invoice Original + 2 Copias",
        "1 Packing List Detallado",
        "1 Carta de Responsabilidad (Firma Original)"
    ],
    "DGR": [
        "1 AWB Original + 4 Copias",
        "3 Shipper's Declaration (Bordes Rojos Originales)",
        "1 MSDS (Hoja de Seguridad)",
        "1 Checklist de Aceptación DG (AV-Check)"
    ],
    "PER": [
        "1 AWB Original + 3 Copias",
        "1 Certificado Fitosanitario (USDA/ICA/SENASA) Original",
        "1 Factura Comercial con Incoterms",
        "1 Registro de Temperatura (Si aplica)"
    ],
    "PHR": [
        "1 AWB Original + 3 Copias",
        "1 Certificado de Calidad / Lote",
        "1 Declaración de Control de Temperatura",
        "1 Packing List / Invoice"
    ],
    "HUM": [
        "1 AWB Original + 3 Copias",
        "1 Certificado de Defunción (Original)",
        "1 Embalming Certificate (Original)",
        "1 Funeral Home Letter / Autorización"
    ],
    "DRY": [
        "1 AWB con notación 'DRY ICE'",
        "1 Declaración IATA de CO2 Sólido",
        "Marcaje visible de KG de Hielo Seco en bulto",
        "1 MSDS (Si es subsidiario de DG/PHR)"
    ]
}

# --- MODELOS DE DATOS ---
class Piece(BaseModel):
    l: float  # Pulgadas
    w: float  # Pulgadas
    h: float  # Pulgadas
    p: float  # Kilos

class PreCheckRequest(BaseModel):
    cargo_type: str
    uld_type: str
    pieces: List[Piece]
    raw_text: str

# --- RUTAS ---
@app.get("/", response_class=HTMLResponse)
async def home():
    try:
        with open("static/app.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "ERROR: static/app.html no encontrado."

@app.post("/precheck")
async def precheck(data: PreCheckRequest):
    instructions = []
    total_vol_weight = 0
    total_actual_weight = 0
    status = "READY"
    
    # 1. Validación de Datos Mínimos
    if not data.pieces or not data.uld_type:
        return JSONResponse(
            status_code=400, 
            content={"status": "REJECT", "instructions": ["ERROR: Faltan datos de piezas o tipo de ULD."]}
        )

    # 2. Auditoría Pieza por Pieza (Cálculos MIA)
    for i, p in enumerate(data.pieces):
        # Peso Real
        total_actual_weight += p.p
        
        # Volumen Automático (Factor IATA 166 para Pulgadas/Kilos)
        # Formula: (L * W * H) / 166
        vol_p = (p.l * p.w * p.h) / 166
        total_vol_weight += vol_p
        
        # Alerta de Altura Crítica (Regla de Avianca: Bellies vs Freighter)
        if p.h > 63:
            instructions.append(f"⚠️ PIEZA #{i+1} ALTA ({p.h} in): Excede límite de Belly. Solo apto para avión CARGUERO.")
            if data.uld_type == "AKE":
                instructions.append(f"❌ RECHAZO: ULD AKE no permite altura de {p.h} in.")
                status = "HOLD"

    # 3. Análisis de Texto (Aura Scan)
    text = data.raw_text.upper()
    
    # Regla USDA / Madera
    if ("MADERA" in text or "PALLET" in text) and "SELLO" not in text and "ISPM" not in text:
        instructions.append("❌ RECHAZO USDA: Madera sin sello ISPM15 detectada. ¡PARA EL CAMIÓN! Cambiar pallet ahora.")
        status = "HOLD"
    
    # Regla TSA / Integridad
    if any(word in text for word in ["ROTO", "MOJADO", "DAÑADO", "WET", "BROKEN"]):
        instructions.append("❌ RIESGO TSA: Embalaje comprometido. Rectificar con film industrial o re-empaquetar.")
        status = "HOLD"

    # 4. Cálculo de Peso Cargable (Chargeable Weight)
    # Se toma el mayor entre el peso real y el volumen total
    chargeable_weight = round(max(total_actual_weight, total_vol_weight), 2)

    # 5. Respuesta Final de Asesoría
    return {
        "status": status,
        "instructions": instructions if instructions else ["Todo en orden. Documentación y carga cumplen con el estándar MIA."],
        "summary": {
            "total_actual_kg": round(total_actual_weight, 2),
            "total_vol_kg": round(total_vol_weight, 2),
            "chargeable_weight": chargeable_weight,
            "uld_selected": data.uld_type
        },
        "required_pouch": PAPERWORK_DATABASE.get(data.cargo_type, PAPERWORK_DATABASE["GENERAL"])
    }

# Montar archivos estáticos (CSS, JS, Imágenes)
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    # Puerto 8000 para desarrollo, Render suele usar variables de entorno
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
