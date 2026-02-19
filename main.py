from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fpdf import FPDF
import datetime

app = FastAPI()
app.mount("/static", StaticFiles(directory="frontend"), name="static")

class CargoForm(BaseModel):
    # Fase 1
    fase1_known_shipper: str
    fase1_itn: str
    fase1_destino: str

    # Fase 2
    fase2_altura: float
    fase2_peso: float
    fase2_nimf15: str
    fase2_tipo_pallet: str
    fase2_largo: float
    fase2_ancho: float
    fase2_punto_peso: float

    # Fase 3
    fase3_dgr: str
    fase3_fitosanitario: str

    # Fase 4
    fase4_awb: str
    fase4_zip: str

    # Fase 5
    fase5_hora_arribo: str

    # Fase 6
    fase6_flejes: str
    fase6_etiqueta: str
    fase6_danio: str
    fase6_plastico: str
    fase6_etiqueta_vieja: str

    # Fase 7
    fase7_limpieza: str
    fase7_etiqueta_fris: str
    fase7_num_piezas: int

    # Fase 8
    fase8_tanques: str
    fase8_overhang: str

def calcular_ULD(data: CargoForm):
    info = []
    status = "Puede volar"

    # Definición técnica de pallets
    uld_types = {
        "PMC": {"largo":125, "ancho":96, "max_height":96, "rating":6800},
        "PAG": {"largo":125, "ancho":88, "max_height":96, "rating":4626},
        "PAJ": {"largo":125, "ancho":88, "max_height":63, "rating":4626},
        "PQA": {"largo":125, "ancho":96, "max_height":96, "rating":11340},
    }

    pallet = uld_types.get(data.fase2_tipo_pallet.upper(), None)
    if pallet:
        # Altura
        if data.fase2_altura > pallet["max_height"]:
            info.append(f"Altura {data.fase2_altura}\" excede límite de {pallet['max_height']}\" para {data.fase2_tipo_pallet}.")
            status="No puede volar"
        # Peso concentrado
        psi = 0
        if data.fase2_punto_peso > 150:
            area = data.fase2_largo * data.fase2_ancho
            psi = data.fase2_punto_peso*2.20462 / area
            info.append(f"Peso concentrado {data.fase2_punto_peso}kg -> PSI: {psi:.2f}.")
            if psi>2:  # arbitrario para ejemplo
                info.append("PSI demasiado alto, requiere Shoring o redistribución.")
                status="No puede volar"
        # Overhang
        if data.fase8_overhang.lower()=="si":
            info.append("Carga sobresale del pallet (Overhang). Re-estibar.")
            status="No puede volar"
    else:
        info.append(f"Pallet {data.fase2_tipo_pallet} no reconocido.")
        status="No puede volar"

    return {"detalle": info, "status":status}

def evaluar_carga(data: CargoForm):
    resultado = []
    status = "Puede volar"

    # Fase 1
    if data.fase1_known_shipper.lower() != "si":
        resultado.append("Fase 1: Known Shipper NO. Riesgo inspección 24-48h.")
        status="No puede volar"
    if data.fase1_itn.strip()=="":
        resultado.append("Fase 1: ITN faltante para mercancía > $2,500 USD.")
        status="No puede volar"
    if data.fase1_destino.lower()=="consolidado":
        resultado.append("Fase 1: Consolidado detectado. Revisar Manifest Houses.")

    # Fase 2
    uld_result = calcular_ULD(data)
    resultado += uld_result["detalle"]
    if uld_result["status"]=="No puede volar":
        status="No puede volar"
    if data.fase2_nimf15.lower()!="si":
        resultado.append("Fase 2: Pallet sin sello NIMF-15. Retorno inmediato.")
        status="No puede volar"

    # Fase 3
    if data.fase3_dgr.lower()=="si":
        resultado.append("Fase 3: Mercancía peligrosa, requiere Shipper’s Declaration y DGR.")
    if data.fase3_fitosanitario.lower()!="si":
        resultado.append("Fase 3: Certificado fitosanitario/FDA faltante. No despachar.")
        status="No puede volar"

    # Fase 4
    if data.fase4_awb.strip()=="" or data.fase4_zip.strip()=="":
        resultado.append("Fase 4: AWB o Zip Code incompleto.")
        status="No puede volar"

    # Fase 5
    try:
        hora=int(data.fase5_hora_arribo.split(":")[0])
        if hora>16: 
            resultado.append("Fase 5: Arribo después del Cut-off. Cargo podría perder reserva.")
            status="No puede volar"
    except:
        resultado.append("Fase 5: Hora inválida.")

    # Fase 6
    campos6=[data.fase6_flejes, data.fase6_etiqueta, data.fase6_danio, data.fase6_plastico, data.fase6_etiqueta_vieja]
    if any(c.lower()!="si" for c in campos6):
        resultado.append("Fase 6: Integridad física y embalaje incompleto. Revisar instrucciones.")
        status="No puede volar"

    # Fase 7
    campos7=[data.fase7_limpieza, data.fase7_etiqueta_fris]
    if any(c.lower()!="si" for c in campos7):
        resultado.append("Fase 7: Restricciones visuales y limpieza incorrectas.")
        status="No puede volar"
    if data.fase7_num_piezas<=0:
        resultado.append("Fase 7: Número de piezas incorrecto.")
        status="No puede volar"

    # Fase 8
    if data.fase8_tanques.lower()!="no":
        resultado.append("Fase 8: Tanques deben estar vacíos y certificados.")
        status="No puede volar"
    if data.fase8_overhang.lower()=="si":
        resultado.append("Fase 8: Overhang detectado. Re-estibar carga.")
        status="No puede volar"

    return {"status":status,"detalle":resultado}

@app.post("/evaluar")
async def evaluar(form: CargoForm):
    res = evaluar_carga(form)
    return JSONResponse(content=res)

@app.post("/generar_pdf")
async def generar_pdf(form: CargoForm):
    res = evaluar_carga(form)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0,10,f"Reporte SMARTCARGO-AIPA - {datetime.datetime.now()}", ln=True)
    pdf.cell(0,10,f"Veredicto: {res['status']}", ln=True)
    pdf.ln(5)
    for linea in res["detalle"]:
        pdf.multi_cell(0,8,f"- {linea}")
    filename = f"frontend/reporte_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(filename)
    return JSONResponse(content={"filename": filename, "veredicto": res['status']})
