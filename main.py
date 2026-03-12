from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime, time

app = FastAPI(title="SmartCargo-Server Backend")

# Permitir CORS para desarrollo y producción local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo de datos recibido desde el frontend
class Shipment(BaseModel):
    longest_piece: float
    widest_piece: float
    tallest_piece: float
    heaviest_piece: float
    description: str
    destination: str
    shipper_type: str
    units: str = "cm"

# Función educativa que genera instrucciones paso a paso
def generate_educational_instructions(data, errors, warnings):
    instructions = []
    
    # Validar AWB
    instructions.append("1. Verifique que su número de AWB tenga el formato correcto: 3 dígitos del carrier + '-' + 8 dígitos de guía.")
    
    # Validar tipo de carga
    if data.description == "":
        instructions.append("2. Seleccione el tipo de carga: General, Perecedero, Humano, Valores, Animales o Mercancía peligrosa.")
    else:
        instructions.append(f"2. La carga seleccionada es '{data.description}'. Asegúrese de contar con todos los documentos obligatorios.")

    # Validación de dimensiones
    instructions.append(f"3. Revise dimensiones y peso: Largo={data.longest_piece}{data.units}, Ancho={data.widest_piece}{data.units}, Alto={data.tallest_piece}{data.units}, Peso={data.heaviest_piece}kg.")
    
    if errors:
        instructions.append("4. Corrija los errores indicados antes de proceder.")
    else:
        instructions.append("4. Las dimensiones y peso están dentro de los límites normales. Proceda a validar seguridad y cutoff.")

    # Validación Known Shipper
    if data.shipper_type.lower() in ["chofer", "forwarder", "agentewarehouse"]:
        instructions.append("5. Confirme que el remitente esté registrado como Known Shipper si aplica. Esto acelera la autorización TSA.")
    
    # Mensajes de advertencias
    if warnings:
        instructions.append("6. Revise las siguientes advertencias para evitar problemas en el vuelo:")
        for w in warnings:
            instructions.append(f"   - {w}")

    instructions.append("7. Revise que el camión llegue antes del cutoff. Si no es posible, reprograme el vuelo.")
    instructions.append("8. Si la carga incluye mercancía peligrosa o Dry Ice, siga los procedimientos especiales de documentación y embalaje.")
    instructions.append("9. Asegúrese de que el pallet o soporte sea el adecuado según el tipo de carga y el avión disponible.")

    return instructions

# Endpoint para validar carga
@app.post("/validate_shipment")
async def validate_shipment(shipment: Shipment):
    errors = []
    warnings = []
    aircraft_recommendation = "Verificar disponibilidad de avión estándar"

    # Validaciones de dimensiones
    if shipment.tallest_piece > 244:
        errors.append("Alto excede límite carguero (244cm)")
    elif shipment.tallest_piece > 160:
        warnings.append("Alto > 160cm: Solo puede ir en Main Deck")
    if shipment.longest_piece > 318:
        errors.append("Largo excede límite de pallet/ULD")
    if shipment.widest_piece > 244:
        errors.append("Ancho excede límite de pallet/ULD")

    # Peso
    if shipment.heaviest_piece > 6800:
        errors.append("Peso excede límite por pallet (6800kg)")

    # Tipo de carga peligrosa
    if shipment.description.lower() in ["dgr", "mercancía peligrosa", "dry ice"]:
        warnings.append("Mercancía peligrosa detectada: Verifique Shipper Declaration y MSDS")
        aircraft_recommendation = "Carga especial: verificar avión con espacio seguro y permisos"

    # Generar instrucciones educativas
    instructions = generate_educational_instructions(shipment, errors, warnings)

    # Determinar status
    status = "✅ Carga apta para volar HOY" if not errors else "❌ Carga NO apta para volar HOY"

    return JSONResponse(content={
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "aircraft_recommendation": aircraft_recommendation,
        "instructions": instructions
    })

# Endpoint de prueba de estado
@app.get("/")
async def root():
    return {"message":"SmartCargo-Server activo ✅"}
