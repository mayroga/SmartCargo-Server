from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json, datetime

app=FastAPI(title="SMARTGOSERVER")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])
app.mount("/static",StaticFiles(directory="static"),name="static")

with open("static/cargo_rules.json","r",encoding="utf-8") as f:cargo_rules=json.load(f)
with open("static/avianca_rules.json","r",encoding="utf-8") as f:avianca_rules=json.load(f)

@app.get("/",response_class=HTMLResponse)
async def home():
    with open("static/app.html","r",encoding="utf-8") as f:return HTMLResponse(f.read())

def validate_phases(data):
    phases={"phase1":[],"phase2":[],"phase3":[],"phase4":[],"phase5":[],"phase6":[],"phase7":[],"phase8":[]}
    if not data["security"]["known_shipper"]:phases["phase1"].append("⚠️ Known Shipper no validado")
    if data["gross_weight"]>150:phases["phase2"].append("⚠️ Peso individual >150kg: usar shoring")
    if data["cargo_type"]=="DGR" and any(b in data["documents"] for b in ["battery","liquid","aerosol"]):phases["phase3"].append("⚠️ Mercancía peligrosa: Shipper Declaration obligatorio")
    if len(data["documents"])<3:phases["phase4"].append("⚠️ Documentos incompletos para AWB")
    if data["role"]=="driver" and data["pieces"]<=0:phases["phase5"].append("⚠️ Número de piezas incorrecto")
    if data["height"]>2.4:phases["phase6"].append("⚠️ Altura >2.4m: solo carguero")
    if not data["security"]["screening"]=="xray":phases["phase7"].append("⚠️ Screening no cumple")
    if data["length"]>1.25 or data["width"]>1.25:phases["phase8"].append("⚠️ Overhang detectado")
    return phases

def validate_shipment(data):
    errors=[]
    corrections=[]
    cargo_type=data["cargo_type"]
    docs_required=cargo_rules.get(cargo_type,{}).get("documents",[])
    for doc in docs_required:
        if doc not in data["documents"]:
            errors.append(f"Falta documento obligatorio: {doc}")
            corrections.append(f"Subir {doc} válido con {cargo_rules[cargo_type]['copies_inside']} copias dentro y {cargo_rules[cargo_type]['copies_outside']} afuera")
    phases=validate_phases(data)
    status="GREEN" if len(errors)==0 else "RED"
    return {"status":status,"errors":errors,"corrections":corrections,"phases":phases,"timestamp":datetime.datetime.now().strftime("%m/%d/%Y, %I:%M:%S %p"),"role":data["role"]}

@app.post("/validate_shipment")
async def validate(data:dict):
    result=validate_shipment(data)
    return JSONResponse(result)
