from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os, json, datetime, httpx

app = FastAPI(title="SMARTCARGO INFALIBLE")

# Carpeta Frontend
if not os.path.exists("frontend"):
    os.makedirs("frontend")
app.mount("/static", StaticFiles(directory="frontend"), name="static")

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

class CargoForm(BaseModel):
    clientId: str | None = ""
    shipmentType: str | None = ""
    highValue: str | None = ""
    itnNumber: str | None = ""
    awbMaster: str | None = ""
    pieceHeight: float | None = 0
    totalWeight: float | None = 0
    needsShoring: str | None = ""
    nimf15: str | None = ""
    cargoType: str | None = ""
    dgrDocs: str | None = ""
    fitoDocs: str | None = ""
    zipCode: str | None = ""

# Motor jerárquico por fases
def evaluar_fases(data: CargoForm):
    fases = []
    status_general = "LISTO PARA VOLAR"

    # -------------------------
    # Fase 1: Identificación y Seguridad
    # -------------------------
    fase1_alertas = []
    fase1_ok = True
    if not data.clientId:
        fase1_alertas.append("❌ ID Cliente vacío")
        fase1_ok = False
    if data.highValue == "yes" and not data.itnNumber:
        fase1_alertas.append("❌ Valor > $2,500 USD sin ITN")
        fase1_ok = False
    if not data.awbMaster:
        fase1_alertas.append("❌ AWB Master no proporcionado")
        fase1_ok = False

    fases.append({"fase":1, "mostrar_siguiente":fase1_ok, "alertas":fase1_alertas})

    if not fase1_ok:
        status_general = "NO LISTO"

    # -------------------------
    # Fase 2: Anatomía de la carga
    # -------------------------
    fase2_alertas = []
    fase2_ok = True
    if data.pieceHeight and data.pieceHeight > 63:
        fase2_alertas.append("⚠️ Altura > 63in: Solo carguero. >96in no entra.")
        fase2_ok = False
    if data.totalWeight and data.totalWeight > 150 and data.needsShoring != "si":
        fase2_alertas.append("❌ Pieza >150kg sin shoring")
        fase2_ok = False
    if data.nimf15 != "si":
        fase2_alertas.append("❌ Pallet sin NIMF-15")
        fase2_ok = False
    fases.append({"fase":2, "mostrar_siguiente":fase2_ok, "alertas":fase2_alertas})
    if not fase2_ok:
        status_general = "NO LISTO"

    # -------------------------
    # Fase 3: Contenidos críticos
    # -------------------------
    fase3_alertas = []
    fase3_ok = True
    if data.cargoType in ["DGR","PER","BIO"]:
        if data.dgrDocs != "si":
            fase3_alertas.append(f"❌ {data.cargoType} sin DGR Docs")
            fase3_ok = False
        if data.fitoDocs != "si" and data.cargoType in ["PER","BIO"]:
            fase3_alertas.append(f"❌ {data.cargoType} sin certificados FDA/Fitosanitarios")
            fase3_ok = False
    fases.append({"fase":3, "mostrar_siguiente":fase3_ok, "alertas":fase3_alertas})
    if not fase3_ok:
        status_general = "NO LISTO"

    # -------------------------
    # Fase Final: Validación ZIP
    # -------------------------
    fase4_alertas = []
    if not data.zipCode:
        fase4_alertas.append("❌ Código Postal vacío")
        status_general = "NO LISTO"
    fases.append({"fase":4, "mostrar_siguiente":True, "alertas":fase4_alertas})

    return {"status":status_general, "fases":fases}

# IA explicativa
async def explicar_ia(alerta):
    prompt = f"Eres un asistente AL CIELO para Avianca Cargo. Explica detalladamente: {alerta}"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_KEY}"},
                json={"model":"gpt-4o-mini","messages":[{"role":"user","content":prompt}],"temperature":0},
                timeout=30
            )
            res = r.json()
            return res["choices"][0]["message"]["content"]
    except:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    "https://api.gemini.com/v1/generate",
                    headers={"Authorization": f"Bearer {GEMINI_KEY}"},
                    json={"prompt":prompt,"max_tokens":500},
                    timeout=30
                )
                res = r.json()
                return res.get("output","No se pudo generar explicación")
        except Exception as e:
            return f"No se pudo generar explicación IA: {str(e)}"

@app.post("/evaluar")
async def evaluar(data: CargoForm):
    resultado = evaluar_fases(data)
    explicaciones = []

    for fase in resultado["fases"]:
        for alerta in fase["alertas"]:
            explicacion = await explicar_ia(alerta)
            explicaciones.append({"alerta": alerta, "explicacion": explicacion})

    log = {"fecha": str(datetime.datetime.now()), "cliente": data.clientId, "resultado": resultado, "explicaciones": explicaciones}
    with open("registro_evaluaciones.json","a",encoding="utf-8") as f:
        f.write(json.dumps(log, ensure_ascii=False)+"\n")

    return JSONResponse({"status":resultado["status"], "fases":resultado["fases"], "explicaciones":explicaciones})
