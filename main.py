from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fpdf import FPDF
import datetime

app = FastAPI()

app.mount("/static", StaticFiles(directory="frontend"), name="static")

class CargoForm(BaseModel):
    fase1_known_shipper: str
    fase1_itn: str
    fase1_destino: str
    fase2_altura: float
    fase2_peso: float
    fase2_nimf15: str
    fase3_dgr: str
    fase3_fitosanitario: str
    fase4_awb: str
    fase4_zip: str
    fase5_hora_arribo: str
    fase6_flejes: str
    fase6_etiqueta: str
    fase6_danio: str
    fase6_plastico: str
    fase6_etiqueta_vieja: str
    fase7_limpieza: str
    fase7_etiqueta_fris: str
    fase7_num_piezas: int
    fase8_tanques: str
    fase8_overhang: str

def evaluar_carga(data: CargoForm):
    resultado = []
    status = "Puede volar"
    
    # Fase 1
    if data.fase1_known_shipper.lower() != "si":
        resultado.append("Fase 1: Known Shipper NO. Riesgo inspección 24-48h.")
        status = "No puede volar"
    if data.fase1_itn.strip() == "" and data.fase1_itn.lower() != "n/a":
        resultado.append("Fase 1: ITN faltante para mercancía > $2,500 USD.")
        status = "No puede volar"
    if data.fase1_destino.lower() == "consolidado":
        resultado.append("Fase 1: Consolidado detectado. Revisar Manifest Houses.")

    # Fase 2
    if data.fase2_altura > 96:
        resultado.append(f"Fase 2: Altura {data.fase2_altura}\" > 96\", no cabe en avión.")
        status = "No puede volar"
    elif data.fase2_altura > 63:
        resultado.append(f"Fase 2: Altura {data.fase2_altura}\" > 63\", solo Freighter.")
    if data.fase2_peso > 150 and data.fase6_flejes.lower() != "si":
        resultado.append(f"Fase 2: Peso {data.fase2_peso} kg requiere shoring/flejes.")
        status = "No puede volar"
    if data.fase2_nimf15.lower() != "si":
        resultado.append("Fase 2: Pallet sin sello NIMF-15. Retorno inmediato.")
        status = "No puede volar"

    # Fase 3
    if data.fase3_dgr.lower() == "si":
        resultado.append("Fase 3: Mercancía peligrosa, requiere DGR/2 originales Shipper.")
    if data.fase3_fitosanitario.lower() != "si":
        resultado.append("Fase 3: Certificado fitosanitario/FDA faltante. No despachar.")
        status = "No puede volar"

    # Fase 4
    if data.fase4_awb.strip() == "" or data.fase4_zip.strip() == "":
        resultado.append("Fase 4: AWB o Zip Code incompleto.")
        status = "No puede volar"

    # Fase 5
    try:
        hora = int(data.fase5_hora_arribo.split(":")[0])
        if hora > 16:
            resultado.append("Fase 5: Arribo después del Cut-off. Cargo podría perder reserva.")
            status = "No puede volar"
    except:
        resultado.append("Fase 5: Hora inválida.")

    # Fase 6
    campos6 = [data.fase6_flejes, data.fase6_etiqueta, data.fase6_danio, data.fase6_plastico, data.fase6_etiqueta_vieja]
    for i, c in enumerate(campos6):
        if c.lower() != "si":
            resultado.append(f"Fase 6: Campo {i+1} incompleto. Corregir antes de envío.")
            status = "No puede volar"

    # Fase 7
    campos7 = [data.fase7_limpieza, data.fase7_etiqueta_fris]
    for i, c in enumerate(campos7):
        if c.lower() != "si":
            resultado.append(f"Fase 7: Campo {i+1} visual/restricción incorrecta.")
            status = "No puede volar"
    if data.fase7_num_piezas <= 0:
        resultado.append("Fase 7: Número de piezas incorrecto.")
        status = "No puede volar"

    # Fase 8
    if data.fase8_tanques.lower() != "no":
        resultado.append("Fase 8: Tanques deben estar vacíos y certificados.")
        status = "No puede volar"
    if data.fase8_overhang.lower() != "no":
        resultado.append("Fase 8: Overhang detectado. Re-estibar carga.")
        status = "No puede volar"

    # IA en tiempo real: sugerencias
    sugerencias = []
    if status == "No puede volar":
        sugerencias.append("Revise todos los campos en rojo y siga instrucciones específicas de cada fase para corregir errores.")
    else:
        sugerencias.append("Carga lista. Verifique medidas y documentos antes de entrega final.")

    return {"status": status, "detalle": resultado, "sugerencias": sugerencias}

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
    pdf.cell(0, 10, f"Reporte de Prechequeo Avianca Cargo - {datetime.datetime.now()}", ln=True)
    pdf.cell(0,10,f"Veredicto: {res['status']}", ln=True)
    pdf.ln(5)
    for linea in res["detalle"]:
        pdf.multi_cell(0, 8, f"- {linea}")
    pdf.ln(5)
    for s in res["sugerencias"]:
        pdf.multi_cell(0,8,f"Sugerencia: {s}")
    filename = f"reporte_carga_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(f"frontend/{filename}")
    return JSONResponse(content={"filename": filename, "veredicto": res['status']})
