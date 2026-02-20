from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import math

app = FastAPI(title="Avianca Cargo - Prevención de Errores")

# ---------------------------
# MODELOS DE DATOS
# ---------------------------
class Cliente(BaseModel):
    nombre: str
    contacto: str
    tipo_cliente: str
    tipo_envio: str
    tipo_mercancia: str

class Pieza(BaseModel):
    descripcion: str
    largo_cm: float
    ancho_cm: float
    alto_cm: float
    peso_kg: float
    en_pallet: bool

class Solicitud(BaseModel):
    cliente: Cliente
    piezas: list[Pieza]

# ---------------------------
# CONSTANTES AVIANA CARGO
# ---------------------------
LIMITES_AVIONES = {
    "pasajero": {"alto_cm": 160, "ancho_cm": 120, "peso_kg": 150},
    "carguero": {"alto_cm": 300, "ancho_cm": 250, "peso_kg": 500},
}

# ---------------------------
# FUNCIONES AUXILIARES
# ---------------------------
def cm_to_in(cm):
    return round(cm / 2.54, 2)

def kg_to_lb(kg):
    return round(kg * 2.20462, 2)

def calcular_volumen_cm3(largo_cm, ancho_cm, alto_cm):
    return largo_cm * ancho_cm * alto_cm

def calcular_volumen_m3(largo_cm, ancho_cm, alto_cm):
    return round(calcular_volumen_cm3(largo_cm, ancho_cm, alto_cm)/1_000_000, 3)

def peso_cobrable(peso_kg, volumen_m3):
    peso_volumetrico_kg = volumen_m3 * 167  # factor estándar Avianca Cargo
    return max(peso_kg, peso_volumetrico_kg)

def detectar_DGR(descripcion):
    keywords = ["bateria de litio", "liquido inflamable", "gas", "explosivo", "aerosol"]
    descripcion_lower = descripcion.lower()
    for k in keywords:
        if k in descripcion_lower:
            return True
    return False

def verificar_reglas(pieza, tipo_avion):
    limites = LIMITES_AVIONES[tipo_avion]
    alertas = []

    if pieza.alto_cm > limites["alto_cm"]:
        alertas.append(f"Pieza demasiado alta ({pieza.alto_cm} cm), límite {limites['alto_cm']} cm. Reubique en carguero si es posible.")
    if pieza.ancho_cm > limites["ancho_cm"]:
        alertas.append(f"Pieza demasiado ancha ({pieza.ancho_cm} cm), límite {limites['ancho_cm']} cm. Reubique o reempaque.")
    if pieza.peso_kg > limites["peso_kg"]:
        alertas.append(f"Pieza demasiado pesada ({pieza.peso_kg} kg), límite {limites['peso_kg']} kg. Use shoring o divida carga.")

    if detectar_DGR(pieza.descripcion):
        alertas.append("DG detectado: coloque Shipper's Declaration y etiquetas rojas visibles.")

    return alertas

# ---------------------------
# ENDPOINTS
# ---------------------------

@app.post("/validar_cliente")
async def validar_cliente(cliente: Cliente):
    alertas = []

    if not cliente.nombre:
        alertas.append("⚠️ Llene el campo nombre completo antes de avanzar.")
    if not cliente.contacto:
        alertas.append("⚠️ Llene el campo contacto antes de avanzar.")
    if not cliente.tipo_cliente:
        alertas.append("⚠️ Llene el campo tipo_cliente antes de avanzar.")
    if not cliente.tipo_envio:
        alertas.append("⚠️ Llene el campo tipo_envio antes de avanzar.")
    if not cliente.tipo_mercancia:
        alertas.append("⚠️ Llene el campo tipo_mercancia antes de avanzar.")

    # Papelería inicial según tipo_envio y tipo_mercancia
    documentos = []
    copias = {}
    if cliente.tipo_envio.lower() == "consolidado":
        documentos.append("Manifiesto + HAWB por cliente")
        copias["AWB"] = {"originales": 3, "copias": 6}
    else:
        documentos.append("Guía Master + Factura + Packing List")
        copias["AWB"] = {"originales": 3, "copias": 3}

    if cliente.tipo_mercancia.lower() == "dg":
        documentos.append("Shipper’s Declaration")
        documentos.append("Etiquetas rojas visibles en cada bulto")
    elif cliente.tipo_mercancia.lower() == "perecedera":
        documentos.append("Certificado sanitario")
    elif cliente.tipo_mercancia.lower() == "human remains":
        documentos.append("Permisos especiales + embalaje específico")
    elif cliente.tipo_mercancia.lower() == "medicamentos":
        documentos.append("FDA / permisos médicos")

    return {"alertas": alertas, "documentos_requeridos": documentos, "copias": copias}

@app.post("/validar_carga")
async def validar_carga(solicitud: Solicitud):
    resultado = []
    for pieza in solicitud.piezas:
        volumen_m3 = calcular_volumen_m3(pieza.largo_cm, pieza.ancho_cm, pieza.alto_cm)
        peso_calc = peso_cobrable(pieza.peso_kg, volumen_m3)
        alertas = verificar_reglas(pieza, tipo_avion="pasajero")  # default pasajero, puede ajustarse según selección

        resultado.append({
            "descripcion": pieza.descripcion,
            "largo_cm": pieza.largo_cm,
            "largo_in": cm_to_in(pieza.largo_cm),
            "ancho_cm": pieza.ancho_cm,
            "ancho_in": cm_to_in(pieza.ancho_cm),
            "alto_cm": pieza.alto_cm,
            "alto_in": cm_to_in(pieza.alto_cm),
            "peso_kg": pieza.peso_kg,
            "peso_lb": kg_to_lb(pieza.peso_kg),
            "volumen_m3": volumen_m3,
            "peso_cobrable_kg": round(peso_calc,2),
            "peso_cobrable_lb": round(kg_to_lb(peso_calc),2),
            "alertas": alertas
        })
    return {"resultado": resultado}

@app.post("/reporte_final")
async def reporte_final(solicitud: Solicitud):
    carga_val = await validar_carga(solicitud)
    errores = []
    for pieza in carga_val["resultado"]:
        if pieza["alertas"]:
            errores.append({pieza["descripcion"]: pieza["alertas"]})

    estado = "✅ Aprobada" if not errores else "⚠️ Correcciones requeridas"
    instrucciones = [
        "Entregar documentos: AWB originales y copias según tipo de envío, Shipper’s Declaration si DG, Certificado sanitario si perecedera",
        "Etiquetas visibles en cada bulto y sobre rojo para DG",
        "Ajustes de piezas según alertas",
        "Confirmar medidas y peso antes de presentar al counter"
    ]

    return {"estado_carga": estado, "errores": errores, "instrucciones_finales": instrucciones}
