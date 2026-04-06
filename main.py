from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List
import os

app = FastAPI(title="AL CIELO - SmartCargo Advisory MIA")

# =========================
# CORS (OPEN FOR ALL)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# STATIC FILES
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# =========================
# ROOT (SERVE HTML)
# =========================
@app.get("/", response_class=HTMLResponse)
async def serve_app():
    try:
        with open(os.path.join(STATIC_DIR, "app.html"), "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return HTMLResponse("<h1>Error cargando la aplicación</h1>", status_code=500)

# =========================
# MODELOS
# =========================
class Piece(BaseModel):
    l: float
    w: float
    h: float
    p: float
    qty: int
    packaging: str
    unit: str  # IN o CM

class PreCheckRequest(BaseModel):
    user_role: str
    cargo_type: str
    pieces: List[Piece]
    raw_text: str
    destination: str

# =========================
# ENDPOINT PRINCIPAL
# =========================
@app.post("/precheck")
async def precheck(data: PreCheckRequest):
    try:
        instructions = []
        reject = False
        max_h_in = 0
        total_actual_kg = 0
        total_vol_kg = 0

        # =========================
        # GLOSARIO
        # =========================
        glossary = {
            "IATA": "Asociación Internacional de Transporte Aéreo.",
            "TSA": "Administración de Seguridad en el Transporte (USA).",
            "CBP": "Aduanas y Protección Fronteriza.",
            "ISPM15": "Norma internacional para embalaje de madera.",
            "DGR": "Mercancías peligrosas.",
            "AWB": "Guía aérea."
        }

        # =========================
        # DOCUMENTOS
        # =========================
        doc_map = {
            "GENERAL": ["AWB Original", "Commercial Invoice", "Packing List"],
            "DGR": ["Shipper Declaration", "MSDS", "AWB DGR"],
            "PER": ["Certificado Fitosanitario", "Factura"],
            "PHR": ["Data Logger", "Control de temperatura"],
            "HUMANS": ["Certificado Defunción", "Permiso funerario"],
            "LIVE_ANIMALS": ["Certificado veterinario", "Checklist IATA"],
            "DRY_ICE": ["Declaración UN1845", "Etiqueta Clase 9"]
        }

        required_docs = doc_map.get(data.cargo_type, ["AWB"])
        required_docs.extend(["Carta TSA", "ID Driver"])

        # =========================
        # VALIDACIÓN PIEZAS
        # =========================
        for i, p in enumerate(data.pieces):
            l_in = p.l if p.unit == "IN" else p.l / 2.54
            w_in = p.w if p.unit == "IN" else p.w / 2.54
            h_in = p.h if p.unit == "IN" else p.h / 2.54

            max_h_in = max(max_h_in, h_in)

            p_weight = p.p * p.qty
            p_vol = (l_in * w_in * h_in * p.qty) / 166

            total_actual_kg += p_weight
            total_vol_kg += p_vol

            # REGLAS
            if p.packaging == "BOX" and p.p > 68:
                instructions.append(
                    f"❌ PIEZA {i+1}: Caja >68kg → Debe ir en pallet."
                )
                reject = True

            if p.packaging == "DRUM" and data.cargo_type != "DGR":
                instructions.append(
                    f"⚠️ PIEZA {i+1}: Tambor → Verificar contenido permitido."
                )

        # =========================
        # AURA SCAN
        # =========================
        text = data.raw_text.upper()

        if any(word in text for word in ["ROTO", "DAÑADO", "MOJADO", "WET"]):
            instructions.append(
                "❌ RECHAZO TSA: Carga dañada → Re-embalar."
            )
            reject = True

        if any(p.packaging in ["PALLET_WD", "CRATE"] for p in data.pieces):
            if "ISPM" not in text:
                instructions.append(
                    "🛑 ALERTA: Madera sin sello ISPM15."
                )

        # =========================
        # AERONAVES
        # =========================
        fleet = [
            {"model": "A330F", "deck": "Main", "max_h": 96},
            {"model": "A330F", "deck": "High", "max_h": 118},
            {"model": "A321", "deck": "Belly", "max_h": 63}
        ]

        compatibility = []

        for air in fleet:
            status = "OK" if max_h_in <= air["max_h"] else "NO CABE"
            compatibility.append({
                "model": air["model"],
                "deck": air["deck"],
                "status": status,
                "limit_h": air["max_h"],
                "reason": "OK" if status == "OK" else f"Excede {round(max_h_in - air['max_h'],1)} in"
            })

        chargeable = max(total_actual_kg, total_vol_kg)

        return {
            "status": "REJECT" if reject else "READY",
            "instructions": instructions,
            "required_docs": required_docs,
            "chargeable_weight": round(chargeable, 2),
            "aircraft_compatibility": compatibility,
            "glossary": glossary
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# HEALTH CHECK (IMPORTANTE PARA DEPLOY)
# =========================
@app.get("/health")
async def health():
    return {"status": "ok"}

# =========================
# RUN LOCAL
# =========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
