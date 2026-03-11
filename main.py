from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json, datetime

app=FastAPI(title="SMARTCARGO Server")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])
app.mount("/static",StaticFiles(directory="static"),name="static")

with open("static/cargo_rules.json","r",encoding="utf-8") as f:cargo_rules=json.load(f)
with open("static/avianca_rules.json","r",encoding="utf-8") as f:avianca_rules=json.load(f)

@app.get("/",response_class=HTMLResponse)
async def home():
    with open("static/app.html","r",encoding="utf-8") as f:return HTMLResponse(f.read())

@app.get("/health")
async def health():return {"status":"ok"}

def validate_shipment(data,rules,c_rules):
    errors=[]
    corrections=[]
    cargo_type=data["cargo_type"]
    docs_required=c_rules.get(cargo_type,{}).get("documents",[])
    copies_inside=c_rules.get(cargo_type,{}).get("copies_inside",1)
    copies_outside=c_rules.get(cargo_type,{}).get("copies_outside",1)
    for doc in docs_required:
        if doc not in data["documents"]:
            errors.append(f"Falta documento obligatorio: {doc}")
            corrections.append(f"Subir {doc} válido con {copies_inside} copias dentro y {copies_outside} afuera")
    if data["pieces"]<=0:errors.append("Número de piezas inválido");corrections.append("Ingresar número de piezas válido")
    if data["gross_weight"]<=0:errors.append("Peso bruto inválido");corrections.append("Ingresar peso correcto")
    if data["volume"]<=0:errors.append("Volumen inválido");corrections.append("Ingresar volumen correcto")
    for check in avianca_rules.get("document_quality",[]):
        for doc in data["documents"]:
            if check=="no_tachaduras" and "tachadura" in doc.lower():errors.append(f"{doc} tiene tachaduras");corrections.append(f"Corregir {doc}")
            if check=="no_borrones" and "borrón" in doc.lower():errors.append(f"{doc} tiene borrones");corrections.append(f"Corregir {doc}")
            if check=="letra_legible" and "ilegible" in doc.lower():errors.append(f"{doc} ilegible");corrections.append(f"Reescribir {doc}")
    if not data["security"]["known_shipper"]:errors.append("Shipper desconocido");corrections.append("Verificar Known Shipper")
    if not data["security"]["regulated_agent"]:errors.append("No Regulated Agent");corrections.append("Verificar agente regulado")
    status="GREEN" if len(errors)==0 else "RED"
    return {"status":status,"errors":errors,"corrections":corrections,"timestamp":datetime.datetime.now().strftime("%m/%d/%Y, %I:%M:%S %p")}

@app.post("/validate_shipment")
async def validate(data:dict):
    result=validate_shipment(data,avianca_rules,cargo_rules)
    return JSONResponse(result)
