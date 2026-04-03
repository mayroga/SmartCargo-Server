from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import json

app = FastAPI()

if not os.path.exists("static"): 
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

# --- LÓGICA DE NEGOCIO AL CIELO ---
@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/app.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/auditoria_mortal")
async def auditoria_mortal(data: dict):
    # Extracción de datos del Pouch y Carga
    awb = data.get("awb", "")
    pouch = data.get("pouch", {})
    piezas = data.get("piezas", [])
    naturaleza = data.get("naturaleza", "GEN")
    shipper_status = data.get("shipper_status", "Unknown")
    equipo_sugerido = data.get("equipo", "PAX") # PAX (Belly) o CAO (Carguero)
    
    alertas, soluciones = [], []
    peso_real_total = 0
    volumen_total_lbs = 0
    
    # 1. AUDITORÍA DE PAPELERÍA (EL OJO DEL COUNTER)
    if not awb.startswith("045"):
        alertas.append("PREFIJO DE GUÍA INVÁLIDO: No corresponde a la red Avianca.")
        soluciones.append("Rectificar Master AWB. El prefijo debe ser 045 para ser aceptado en este muelle.")
    
    if pouch.get("tachaduras"):
        alertas.append("DOCUMENTO RECHAZADO: Se detectan tachaduras o borrones en la Guía o Factura.")
        soluciones.append("La normativa de Aduana prohíbe enmiendas. El Shipper debe re-emitir la documentación limpia de inmediato.")
    
    if not pouch.get("facturas_originales"):
        alertas.append("FALTA DOCUMENTACIÓN ORIGINAL: Solo se detectan copias.")
        soluciones.append("Presentar 3 juegos de Facturas Comerciales originales con firma autógrafa en tinta azul para evitar retención en destino.")

    if data.get("tipo_consolidado") == "CONSOLIDADA" and not pouch.get("manifest_house"):
        alertas.append("MANIFESTACIÓN INCOMPLETA: Master consolidada sin desglose de Houses (HAWB).")
        soluciones.append("Adjuntar el Manifiesto de Carga Consolidada para el cierre del vuelo.")

    # 2. AUDITORÍA FÍSICA Y REVENUE (PIEZA POR PIEZA)
    for i, p in enumerate(piezas):
        cant = int(p.get("cant", 1))
        l, w, h = float(p.get("l", 0)), float(p.get("w", 0)), float(p.get("h", 0))
        p_unitario = float(p.get("p_real", 0))
        
        # Cálculo de Peso Volumétrico (IATA Standard 166)
        # Fórmula: (L x W x H / 166) * Cantidad
        v_index_pieza = (l * w * h) / 166
        v_total_item = v_index_pieza * cant
        p_real_item = p_unitario * cant
        
        peso_real_total += p_real_item
        volumen_total_lbs += v_total_item
        
        # Validación de Altura (Belly vs Main Deck)
        if h > 63 and equipo_sugerido == "PAX":
            alertas.append(f"PIEZA #{i+1}: Altura de {h}\" excede el túnel de carga de avión PAX.")
            soluciones.append(f"Transferir pieza #{i+1} a un equipo Carguero (Main Deck) o solicitar al Shipper re-dimensionar el embalaje a máximo 63\".")

    # 3. SEGURIDAD TSA Y CARGA ESPECIAL
    if shipper_status == "Unknown":
        alertas.append("REMITENTE DESCONOCIDO (TSA): Carga de alto riesgo.")
        soluciones.append("La carga debe someterse a Inspección Tecnológica (X-Ray/ETD) obligatoria. El tiempo de aceptación se extiende 4 horas.")

    if naturaleza == "DGR":
        if not data.get("dgd_roja"):
            alertas.append("RIESGO DGR: Falta Shipper's Declaration for Dangerous Goods en formato original.")
            soluciones.append("La DGD debe tener bordes rojos y estar firmada por personal certificado IATA. No se aceptan copias en blanco y negro.")
    
    if naturaleza == "PER" and not data.get("cold_chain"):
        alertas.append("RUPTURA DE CADENA DE FRÍO: Carga perecedera sin hielo seco o gel pack suficiente.")
        soluciones.append("Trasladar de inmediato a cuarto frío (2-8°C) y re-abastecer refrigerante antes de la estiba.")

    # 4. INTERPRETACIÓN DE PRE-CHEQUEO (IA ADVISORY)
    pre = data.get("prechequeo", "").upper()
    if any(word in pre for word in ["OLOR", "DERRAME", "HUMEDAD", "GOLPE"]):
        alertas.append("DAÑO FÍSICO DETECTADO: El pre-chequeo indica irregularidades en el embalaje.")
        soluciones.append("Emitir Nota de Protesta y solicitar carta de responsabilidad (LOI) al transportista para proteger a la aerolínea.")

    chargeable_weight = max(peso_real_total, volumen_total_lbs)
    status = "RECHAZO TÉCNICO / HOLD" if alertas else "VUELO AUTORIZADO / FLY READY"

    return {
        "status": status,
        "alertas": alertas,
        "soluciones": soluciones,
        "chargeable": round(chargeable_weight, 2),
        "real": round(peso_real_total, 2),
        "revenue_method": "VOLUMÉTRICO" if volumen_total_lbs > peso_real_total else "PESO REAL",
        "pouch_status": "COMPLETO" if not alertas else "INCOMPLETO"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
