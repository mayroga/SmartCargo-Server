# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="SMARTCARGO-AIPA Pre-Check")

# CORS para frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo de entrada de usuario
class CargoInput(BaseModel):
    fase: int
    pregunta_id: int
    respuesta: str

# ============================
# PREGUNTAS E INSTRUCCIONES
# ============================
PREGUNTAS = {
    # FASE 1: Identificación y Seguridad (TSA/CBP)
    1: {"fase": 1, "pregunta": "Ingrese su ID de Cliente o código SCAC de la empresa de transporte.",
        "instruccion": "Valida Known Shipper. Si no lo es, inspección física 24-48h."},
    2: {"fase": 1, "pregunta": "¿El valor de su mercancía por código arancelario supera los $2,500 USD?",
        "instruccion": "Se requiere ITN/AES; multa federal $10,000 si falta."},
    3: {"fase": 1, "pregunta": "¿Su carga es para un solo destino o es un consolidado de varios clientes?",
        "instruccion": "Si consolidado, active Manifiesto de Carga; si directa, pase a la Guía Master."},

    # FASE 2: Anatomía de la Carga (Técnico Avianca)
    4: {"fase": 2, "pregunta": "¿Cuál es la medida de la pieza más alta, incluyendo la base de madera (estiba)?",
        "instruccion": "Si >63\", solo puede volar en avión Carguero; si >96\", no puede volar en Avianca."},
    5: {"fase": 2, "pregunta": "¿Alguna pieza pesa más de 150 kg (330 lbs)?",
        "instruccion": "Debe usar base de madera (skids/shoring) para distribuir peso."},
    6: {"fase": 2, "pregunta": "¿Su estiba de madera tiene el sello NIMF-15 visible en dos lados?",
        "instruccion": "Sin sello, USDA/CBP ordenará retorno inmediato; use pallet plástico o certificado."},

    # FASE 3: Contenidos Críticos (IATA/DOT)
    7: {"fase": 3, "pregunta": "¿Su mercancía contiene baterías de litio, líquidos, aerosoles, perfumes o imanes?",
        "instruccion": "Requiere 2 originales de Shipper’s Declaration con bordes rojos."},
    8: {"fase": 3, "pregunta": "¿Su carga es de origen animal, vegetal o para consumo humano (medicinas/comida)?",
        "instruccion": "Debe presentar Certificado Fitosanitario o Prior Notice FDA, fuera del sobre."},

    # FASE 4: Check-list Documental Final
    9: {"fase": 4, "pregunta": "¿Tiene listos los 3 originales y 6 copias de la Guía Aérea (AWB)?",
        "instruccion": "El agente no hace copias; falta = pérdida de turno."},
    10: {"fase": 4, "pregunta": "¿El código postal del destinatario coincide con la guía y factura?",
         "instruccion": "El sistema bloquea guías con códigos postales incompletos; verifique dígito por dígito."},

    # FASE 5: Instrucción de Logística de Arribo
    11: {"fase": 5, "pregunta": "¿A qué hora estima que su chofer llegará al counter de Avianca en Miami?",
         "instruccion": "Cut-off es 4h antes del vuelo; llegada tardía = cargos por Storage y pérdida de reserva."},

    # FASE 6: Integridad Física y Embalaje (Bodega)
    12: {"fase": 6, "pregunta": "¿La mercancía está asegurada con flejes o solo con plástico?",
         "instruccion": "Cargas pesadas DEBEN llevar flejes; si se mueve, counter rechazará la carga."},
    13: {"fase": 6, "pregunta": "¿Cada bulto tiene escrito el número de AWB?",
         "instruccion": "Si se cae la etiqueta, carga huérfana; obligatorio marcar físicamente."},
    14: {"fase": 6, "pregunta": "¿Hay cajas rotas, aplastadas o con esquinas dobladas?",
         "instruccion": "Cargas con daño preexistente = rechazo; cambie caja antes de enviar."},
    15: {"fase": 6, "pregunta": "¿El plástico que envuelve el pallet está tenso y cubre toda la carga?",
         "instruccion": "Si no, riesgo de seguridad; el counter puede devolver el camión."},
    16: {"fase": 6, "pregunta": "¿Existen etiquetas viejas de otros vuelos o aerolíneas?",
         "instruccion": "Eliminar etiquetas viejas; generan confusión en escáners y retenciones."},

    # FASE 7: Seguridad y Restricciones Visuales (TSA)
    17: {"fase": 7, "pregunta": "¿La carga está limpia de olores, aceites o grasa?",
         "instruccion": "Manchas indican fuga de químicos; detiene proceso por riesgo DGR."},
    18: {"fase": 7, "pregunta": "¿Los bultos tienen etiquetas 'Frágil', 'Este Lado Arriba' o 'No Estibar'?",
         "instruccion": "'No Estibar' = posible aumento de flete; alertar al usuario."},
    19: {"fase": 7, "pregunta": "¿El número de piezas coincide con la Guía Aérea?",
         "instruccion": "Sistema Avianca no permite ingresos parciales; corrija documento antes de llegar."},

    # FASE 8: Requisitos Específicos de Equipos y Contenedores
    20: {"fase": 8, "pregunta": "¿Está enviando tanques o cilindros?",
         "instruccion": "Deben estar vacíos y con certificación; válvulas protegidas."},
    21: {"fase": 8, "pregunta": "¿Su pallet tiene 'Overhang' (carga sobresale de la base)?",
         "instruccion": "Sobresaliente = re-estibar; carga debe alinearse con borde del pallet."},
}

# ============================
# ENDPOINTS
# ============================

# Obtener pregunta según fase y pregunta_id
@app.get("/get_question/{fase}/{pregunta_id}")
async def get_question(fase: int, pregunta_id: int):
    if pregunta_id in PREGUNTAS:
        return PREGUNTAS[pregunta_id]
    return JSONResponse(status_code=404, content={"error": "Pregunta no encontrada"})

# Enviar respuesta y recibir alerta
@app.post("/submit_answer")
async def submit_answer(input: CargoInput):
    alerta = ""
    r = input.respuesta.strip().lower()

    # ============================
    # REGLAS AUTOMÁTICAS POR PREGUNTA
    # ============================

    # FASE 1
    if input.pregunta_id == 1 and r == "":
        alerta = "⚠ Debe ingresar su ID o SCAC para Known Shipper."
    if input.pregunta_id == 2 and r in ["sí", "si", "yes"]:
        alerta = "⚠ ITN requerido. Multa federal $10,000 si no lo entrega."
    if input.pregunta_id == 3 and r in ["consolidado", "multiple"]:
        alerta = "⚠ Debe generar Manifiesto de Carga y Houses exactas."

    # FASE 2
    if input.pregunta_id == 4:
        try:
            altura = float(r.replace('"',''))
            if altura > 96:
                alerta = "⚠ Altura excede límite; carga no entra en ningún avión Avianca."
            elif altura > 63:
                alerta = "⚠ Solo puede volar en avión Carguero (Freighter)."
        except:
            alerta = "Ingrese altura válida en pulgadas."
    if input.pregunta_id == 5 and any(x in r for x in ["sí","si","yes"]):
        alerta = "⚠ Pieza >150kg; obligatorio usar base de madera (shoring)."
    if input.pregunta_id == 6 and "nimf" not in r:
        alerta = "⚠ Pallet sin sello NIMF-15; use pallet plástico o certificado."

    # FASE 3
    if input.pregunta_id == 7 and any(x in r for x in ["sí","si","yes"]):
        alerta = "⚠ Mercancía DGR; requiere 2 originales Shipper’s Declaration."
    if input.pregunta_id == 8 and any(x in r for x in ["sí","si","yes"]):
        alerta = "⚠ Requiere Certificado Fitosanitario o Prior Notice FDA."

    # FASE 4
    if input.pregunta_id == 9 and "no" in r:
        alerta = "⚠ Faltan originales/copias; pérdida de turno en el counter."
    if input.pregunta_id == 10 and "no" in r:
        alerta = "⚠ Código postal incorrecto; sistema bloquea guía."

    # FASE 5
    if input.pregunta_id == 11:
        alerta = "⚠ Recuerde: Cut-off 4h antes del vuelo; llegada tardía = cargos Storage."

    # FASE 6
    if input.pregunta_id == 12 and "plástico" in r:
        alerta = "⚠ Tanques/motores pesados deben tener flejes metálicos."
    if input.pregunta_id == 13 and "no" in r:
        alerta = "⚠ Cada bulto debe tener número AWB visible; carga huérfana si no."
    if input.pregunta_id == 14 and "sí" in r:
        alerta = "⚠ Cajas dañadas = rechazo; cambiar antes de enviar."
    if input.pregunta_id == 15 and "no" in r:
        alerta = "⚠ Plástico flojo = riesgo; counter puede devolver camión."
    if input.pregunta_id == 16 and "sí" in r:
        alerta = "⚠ Etiquetas viejas deben eliminarse para evitar confusión."

    # FASE 7
    if input.pregunta_id == 17 and "no" in r:
        alerta = "⚠ Limpie olores/aceites; riesgo DGR."
    if input.pregunta_id == 18 and "no estibar" in r:
        alerta = "⚠ Costo de flete puede aumentar; restricción de carga."
    if input.pregunta_id == 19 and "no" in r:
        alerta = "⚠ Número de piezas no coincide; corrija documento."

    # FASE 8
    if input.pregunta_id == 20 and any(x in r for x in ["sí","si","yes"]):
        alerta = "⚠ Tanques/cilindros deben estar vacíos y con certificación; válvulas protegidas."
    if input.pregunta_id == 21 and any(x in r for x in ["sí","si","yes"]):
        alerta = "⚠ Overhang detectado; re-estibar carga para alinear con borde del pallet."

    return {"fase": input.fase, "pregunta_id": input.pregunta_id, "alerta": alerta}
