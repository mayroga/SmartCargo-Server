from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SMARTCARGO-AIPA", description="Pre-chequeo técnico para Avianca Cargo Miami")

# Permitir acceso desde cualquier origen (para frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Preguntas e instrucciones fase por fase
questions = [
    # Fase 1: Identificación y Seguridad (TSA/CBP)
    {
        "id": 1,
        "fase": "Fase 1: Identificación y Seguridad",
        "question": "Ingrese su ID de Cliente o código SCAC de la empresa de transporte.",
        "instruction": "Esto valida que usted es un Known Shipper (Embarcador Conocido). Si no lo es, su carga será sometida a una inspección física obligatoria de 24 a 48 horas."
    },
    {
        "id": 2,
        "fase": "Fase 1: Identificación y Seguridad",
        "question": "¿El valor de su mercancía por código arancelario supera los $2,500 USD?",
        "instruction": "Si la respuesta es SÍ, es OBLIGATORIO el número de ITN (AES). Ingréselo ahora para que aparezca en la Guía Aérea. Sin esto, la multa federal es de $10,000 USD."
    },
    {
        "id": 3,
        "fase": "Fase 1: Identificación y Seguridad",
        "question": "¿Su carga es para un solo destino o es un consolidado de varios clientes?",
        "instruction": "Si es consolidado, la App activará la sección de Manifiesto de Carga. Si es directa, pasaremos a la validación de Guía Master única."
    },

    # Fase 2: Anatomía de la Carga (Filtro Técnico Avianca)
    {
        "id": 4,
        "fase": "Fase 2: Anatomía de la Carga",
        "question": "¿Cuál es la medida de la pieza más alta, incluyendo la base de madera (estiba)?",
        "instruction": "Si mide más de 63 pulgadas, solo puede volar en avión Carguero (Freighter). Si mide más de 96 pulgadas, no puede volar en ningún avión de Avianca. Ajuste la altura ahora."
    },
    {
        "id": 5,
        "fase": "Fase 2: Anatomía de la Carga",
        "question": "¿Alguna pieza pesa más de 150 kg (330 lbs)?",
        "instruction": "Si es así, debe tener una base de madera (skids/shoring) para distribuir el peso en el piso del avión. De lo contrario, el jefe de patio rechazará la carga por riesgo de daños estructurales."
    },
    {
        "id": 6,
        "fase": "Fase 2: Anatomía de la Carga",
        "question": "¿Su estiba (pallet) de madera tiene el sello NIMF-15 (espiga de trigo) visible en dos lados?",
        "instruction": "Sin el sello de fumigación, USDA/CBP ordenará el retorno inmediato de la carga. Cámbielo por un pallet de plástico si no está certificado."
    },

    # Fase 3: Contenidos Críticos (Filtro IATA/DOT)
    {
        "id": 7,
        "fase": "Fase 3: Contenidos Críticos",
        "question": "¿Su mercancía contiene baterías de litio, líquidos, aerosoles, perfumes o imanes?",
        "instruction": "Estos son artículos de Mercancía Peligrosa (DGR). Requiere 2 originales de la Shipper’s Declaration con bordes rojos. Omitirlo es un delito federal."
    },
    {
        "id": 8,
        "fase": "Fase 3: Contenidos Críticos",
        "question": "¿Su carga es de origen animal, vegetal o para consumo humano (medicinas/comida)?",
        "instruction": "Usted debe presentar el Certificado Fitosanitario Original o el Prior Notice de la FDA. Estos papeles deben ir FUERA del sobre para entrega inmediata al agente."
    },

    # Fase 4: Check-list Documental Final
    {
        "id": 9,
        "fase": "Fase 4: Check-list Documental Final",
        "question": "¿Tiene listos los 3 originales y 6 copias de la Guía Aérea (AWB)?",
        "instruction": "El agente de counter no hace copias. Si falta una, el chofer será enviado a una oficina externa, perdiendo su turno en la fila."
    },
    {
        "id": 10,
        "fase": "Fase 4: Check-list Documental Final",
        "question": "¿El código postal (Zip Code) del destinatario está escrito en la guía y coincide con la factura?",
        "instruction": "El sistema de Avianca bloquea guías con códigos postales incompletos. Verifique dígito por dígito ahora."
    },

    # Fase 5: Instrucción de Logística de Arribo
    {
        "id": 11,
        "fase": "Fase 5: Logística de Arribo",
        "question": "¿A qué hora estima que su chofer llegará al counter de Avianca en Miami?",
        "instruction": "El cierre de recepción (Cut-off) para su vuelo es 4 horas antes de la salida. Si llega después, se aplicarán cargos por Storage (almacenaje) y perderá la reserva."
    },

    # Fase 6: Integridad Física y Embalaje
    {
        "id": 12,
        "fase": "Fase 6: Integridad Física y Embalaje",
        "question": "¿La mercancía está asegurada a la estiba con flejes (straps) o solo con plástico (shrink wrap)?",
        "instruction": "Si envía tanques, motores o piezas pesadas, el plástico no es suficiente. El counter rechazará la carga si no tiene flejes metálicos o de alta resistencia. La carga que se mueve es carga que no vuela."
    },
    {
        "id": 13,
        "fase": "Fase 6: Integridad Física y Embalaje",
        "question": "¿Cada bulto tiene escrito el número de Guía Aérea (AWB) con marcador permanente o etiqueta?",
        "instruction": "Si el plástico se rompe y la etiqueta se cae, la carga queda huérfana. Es obligatorio que el número de guía esté escrito físicamente en la caja o el pallet para que el counter lo acepte."
    },
    {
        "id": 14,
        "fase": "Fase 6: Integridad Física y Embalaje",
        "question": "¿Hay cajas rotas, aplastadas o con esquinas dobladas?",
        "instruction": "Avianca no acepta carga con 'daño pre-existente' sin anotarlo en la guía. Si el daño es mucho, el counter rechazará la carga para evitar reclamos al seguro. Cambie la caja antes de enviarla."
    },
    {
        "id": 15,
        "fase": "Fase 6: Integridad Física y Embalaje",
        "question": "¿El plástico que envuelve el pallet está tenso y cubre desde la base de madera hasta el tope?",
        "instruction": "Un pallet mal envuelto (suelto) es un riesgo de seguridad. Si el agente de counter ve que la carga se puede ladeado, ordenará el re-envoltorio con costo extra o devolverá el camión."
    },
    {
        "id": 16,
        "fase": "Fase 6: Integridad Física y Embalaje",
        "question": "¿Existen etiquetas viejas de otros vuelos o de otras aerolíneas en las cajas?",
        "instruction": "Esto genera confusión en los escáners de la bodega. Elimine toda etiqueta vieja. Una etiqueta de 'Bogotá' en una carga que va a 'Lima' causará que la carga se pierda o sea retenida por seguridad."
    },

    # Fase 7: Seguridad y Restricciones Visuales
    {
        "id": 17,
        "fase": "Fase 7: Seguridad y Restricciones Visuales",
        "question": "¿La carga está 'limpia' de olores fuertes, aceites o manchas de grasa?",
        "instruction": "Manchas de aceite en la base del pallet indican fuga de químicos o motores mal drenados. Esto detiene el proceso por riesgo de Mercancía Peligrosa no declarada."
    },
    {
        "id": 18,
        "fase": "Fase 7: Seguridad y Restricciones Visuales",
        "question": "¿Los bultos tienen etiquetas de 'Frágil', 'Este Lado Arriba' (Arrow labels) o 'No Estibar'?",
        "instruction": "Si pone 'No Estibar', la aplicación debe advertirle que el costo del flete puede subir, ya que no se podrá poner nada encima en la bodega del avión."
    },
    {
        "id": 19,
        "fase": "Fase 7: Seguridad y Restricciones Visuales",
        "question": "¿El número de piezas físico es exactamente igual al que escribió en la Guía Aérea?",
        "instruction": "Si la guía dice 10 bultos y el chofer entrega 9, el counter no recibirá nada. El sistema de Avianca no permite ingresos parciales. Corrija el documento antes de llegar."
    },

    # Fase 8: Requisitos Específicos de Equipos y Contenedores
    {
        "id": 20,
        "fase": "Fase 8: Requisitos Específicos de Equipos y Contenedores",
        "question": "¿Está enviando tanques o cilindros?",
        "instruction": "Deben estar vacíos y con una certificación de que no tienen presión. Si tienen válvulas, deben estar protegidas por una tapa o jaula para evitar aperturas accidentales."
    },
    {
        "id": 21,
        "fase": "Fase 8: Requisitos Específicos de Equipos y Contenedores",
        "question": "¿Su pallet tiene 'Overhang' (la carga sobresale de la base de madera)?",
        "instruction": "Si la carga sobresale, no encajará en las posiciones del avión. El counter le obligará a re-estibar. La carga debe estar alineada con los bordes del pallet."
    },
]

@app.get("/questions")
async def get_questions():
    return JSONResponse(content=questions)

@app.post("/submit_answer")
async def submit_answer(request: Request):
    data = await request.json()
    q_id = data.get("id")
    answer = data.get("answer")

    # Borrar espacios y normalizar
    if isinstance(answer, str):
        answer = answer.strip().lower()

    alert = ""
    # Lógica de alertas básicas según tu guía
    if q_id == 2 and answer in ["sí", "si", "yes"]:
        alert = "ALERTA: Sin ITN (AES) no puede volar. Multa federal $10,000 USD."
    if q_id == 4:
        try:
            height = float(answer)
            if height > 96:
                alert = "ALERTA: La carga NO cabe en ningún avión de Avianca."
            elif height > 63:
                alert = "INSTRUCCIÓN: Solo puede volar en avión Carguero (Freighter)."
        except:
            alert = "Ingrese un valor numérico válido para la altura."
    if q_id == 5:
        try:
            weight = float(answer)
            if weight > 150:
                alert = "INSTRUCCIÓN: Use base de madera (shoring) para distribuir peso."
        except:
            alert = "Ingrese un valor numérico válido para el peso."
    if q_id == 21 and answer in ["sí", "si", "yes"]:
        alert = "ALERTA: Overhang detectado. Re-estibar la carga."

    return JSONResponse(content={"alert": alert})
