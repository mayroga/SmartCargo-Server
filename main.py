# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from utils.rules import validar_respuesta
from config import APP_NAME, VERSION, TOTAL_PREGUNTAS

app = FastAPI(title=APP_NAME, version=VERSION)

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

# Preguntas definidas
PREGUNTAS = {
    1: {"fase":1, "pregunta":"Ingrese su ID de Cliente o código SCAC de la empresa de transporte.",
        "instruccion":"Valida Known Shipper. Si no lo es, inspección física 24-48h."},
    2: {"fase":1, "pregunta":"¿El valor de su mercancía por código arancelario supera los $2,500 USD?",
        "instruccion":"Se requiere ITN/AES; multa federal $10,000 si falta."},
    3: {"fase":1, "pregunta":"¿Su carga es para un solo destino o es un consolidado de varios clientes?",
        "instruccion":"Si consolidado, active Manifiesto de Carga; si directa, pase a la Guía Master."},
    4: {"fase":2, "pregunta":"¿Cuál es la medida de la pieza más alta, incluyendo la base de madera (estiba)?",
        "instruccion":"Si >63\", solo puede volar en avión Carguero; si >96\", no puede volar en Avianca."},
    5: {"fase":2, "pregunta":"¿Alguna pieza pesa más de 150 kg (330 lbs)?",
        "instruccion":"Debe usar base de madera (skids/shoring) para distribuir peso."},
    6: {"fase":2, "pregunta":"¿Su estiba de madera tiene el sello NIMF-15 visible en dos lados?",
        "instruccion":"Sin sello, USDA/CBP ordenará retorno inmediato; use pallet plástico o certificado."},
    7: {"fase":3, "pregunta":"¿Su mercancía contiene baterías de litio, líquidos, aerosoles, perfumes o imanes?",
        "instruccion":"Requiere 2 originales de Shipper’s Declaration con bordes rojos."},
    8: {"fase":3, "pregunta":"¿Su carga es de origen animal, vegetal o para consumo humano (medicinas/comida)?",
        "instruccion":"Debe presentar Certificado Fitosanitario o Prior Notice FDA, fuera del sobre."},
    9: {"fase":4, "pregunta":"¿Tiene listos los 3 originales y 6 copias de la Guía Aérea (AWB)?",
        "instruccion":"El agente no hace copias; falta = pérdida de turno."},
    10: {"fase":4, "pregunta":"¿El código postal del destinatario coincide con la guía y factura?",
         "instruccion":"El sistema bloquea guías con códigos postales incompletos; verifique dígito por dígito."},
    11: {"fase":5, "pregunta":"¿A qué hora estima que su chofer llegará al counter de Avianca en Miami?",
         "instruccion":"Cut-off es 4h antes del vuelo; llegada tardía = cargos por Storage y pérdida de reserva."},
    12: {"fase":6, "pregunta":"¿La mercancía está asegurada con flejes o solo con plástico?",
         "instruccion":"Cargas pesadas DEBEN llevar flejes; si se mueve, counter rechazará la carga."},
    13: {"fase":6, "pregunta":"¿Cada bulto tiene escrito el número de AWB?",
         "instruccion":"Si se cae la etiqueta, carga huérfana; obligatorio marcar físicamente."},
    14: {"fase":6, "pregunta":"¿Hay cajas rotas, aplastadas o con esquinas dobladas?",
         "instruccion":"Cargas con daño preexistente = rechazo; cambie caja antes de enviar."},
    15: {"fase":6, "pregunta":"¿El plástico que envuelve el pallet está tenso y cubre toda la carga?",
         "instruccion":"Si no, riesgo de seguridad; el counter puede devolver el camión."},
    16: {"fase":6, "pregunta":"¿Existen etiquetas viejas de otros vuelos o aerolíneas?",
         "instruccion":"Eliminar etiquetas viejas; generan confusión en escáners y retenciones."},
    17: {"fase":7, "pregunta":"¿La carga está limpia de olores, aceites o grasa?",
         "instruccion":"Manchas indican fuga de químicos; detiene proceso por riesgo DGR."},
    18: {"fase":7, "pregunta":"¿Los bultos tienen etiquetas 'Frágil', 'Este Lado Arriba' o 'No Estibar'?",
         "instruccion":"'No Estibar' = posible aumento de flete; alertar al usuario."},
    19: {"fase":7, "pregunta":"¿El número de piezas coincide con la Guía Aérea?",
         "instruccion":"Sistema Avianca no permite ingresos parciales; corrija documento antes de llegar."},
    20: {"fase":8, "pregunta":"¿Está enviando tanques o cilindros?",
         "instruccion":"Deben estar vacíos y con certificación; válvulas protegidas."},
    21: {"fase":8, "pregunta":"¿Su pallet tiene 'Overhang' (carga sobresale de la base)?",
         "instruccion":"Sobresaliente = re-estibar; carga debe alinearse con borde del pallet."},
}

# ============================
# ENDPOINTS
# ============================

@app.get("/get_question/{fase}/{pregunta_id}")
async def get_question(fase: int, pregunta_id: int):
    if pregunta_id in PREGUNTAS:
        return PREGUNTAS[pregunta_id]
    return JSONResponse(status_code=404, content={"error": "Pregunta no encontrada"})

@app.post("/submit_answer")
async def submit_answer(input: CargoInput):
    alerta = validar_respuesta(input.pregunta_id, input.respuesta)
    return {"fase": input.fase, "pregunta_id": input.pregunta_id, "alerta": alerta}
