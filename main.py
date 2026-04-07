from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()

def classify(raw):
    t=raw.lower()
    if "dg" in t or "un" in t: return "DG"
    if "pharma" in t: return "PHARMA"
    if "animal" in t: return "LIVE ANIMALS"
    if "human" in t: return "HUMAN REMAINS"
    if "dry ice" in t: return "DRY ICE"
    if "perecedero" in t: return "PERISHABLE"
    if "consol" in t: return "CONSOL"
    if "transfer" in t: return "TRANSFER"
    if "comat" in t: return "COMAT"
    return "GENERAL"

def rules(type):
    docs=["AWB"]
    err=[]; warn=[]; fix=[]; status="READY"

    if type=="DG":
        docs+=["Shipper DG","MSDS"]
        err.append("Falta DG Declaration")
        status="REJECT"

    if type=="PHARMA":
        docs+=["Temp Control"]
        warn.append("Temperatura crítica")
        status="RISK"

    if type=="LIVE ANIMALS":
        docs+=["Vet Cert"]
        err.append("Regulación animal")
        status="REJECT"

    if type=="DRY ICE":
        docs+=["Dry Ice Decl"]
        warn.append("CO2")
        status="RISK"

    if type=="PERISHABLE":
        warn.append("Cadena frío")
        status="RISK"

    if type=="CONSOL":
        docs+=["MAWB","HAWB"]
        warn.append("Consolidado")
        status="RISK"

    return err,warn,fix,docs,status

def validate(pieces):
    warn=[]; w=0
    for p in pieces:
        w+=p.get("kg",0)
        if p.get("h",0)>160: warn.append("Altura excedida PAX")
    return warn,w

@app.post("/precheck")
async def precheck(r:Request):

    d=await r.json()

    cargo=classify(d.get("raw_text",""))
    err,warn,fix,docs,status=rules(cargo)

    w2,weight=validate(d.get("pieces",[]))
    warn+=w2

    if err: status="REJECT"
    elif warn and status!="REJECT": status="RISK"

    msg="OK"
    if status=="REJECT": msg="NO IR AL COUNTER"
    if status=="RISK": msg="RIESGO"

    return {
        "status":status,
        "driver_message":msg,
        "cargo_type_detected":cargo,
        "errors":err,
        "warnings":warn,
        "fixes":fix,
        "required_docs":docs,
        "summary":{
            "awb":d.get("awb",""),
            "route":f"{d.get('origin','')}->{d.get('destination','')}",
            "weight":weight
        }
    }

if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__=="__main__":
    import uvicorn
    uvicorn.run(app,host="0.0.0.0",port=5000)
