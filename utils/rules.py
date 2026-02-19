# utils/rules.py
# Reglas técnicas y alertas SMARTCARGO-AIPA

def validar_respuesta(fase: int, pregunta_id: int, respuesta: str):
    """
    Retorna una alerta si la respuesta viola reglas críticas de Avianca Cargo.
    """
    alerta = None

    # Fase 1: Identificación y Seguridad
    if fase == 1:
        if pregunta_id == 2:  # Valor > $2500
            if respuesta.lower() in ['sí', 'si', 'yes'] and not respuesta.strip().isdigit():
                alerta = "⚠ Ingrese el número ITN (AES) obligatorio. Multa federal $10,000 si omite."
        elif pregunta_id == 3:  # Consolidado o directo
            if respuesta.lower() not in ['directa', 'consolidado']:
                alerta = "⚠ Respuesta inválida. Debe ser 'Directa' o 'Consolidado'."

    # Fase 2: Anatomía de la Carga
    if fase == 2:
        if pregunta_id == 4:  # Altura
            try:
                altura = float(respuesta)
                if altura > 96:
                    alerta = "❌ Altura excede límite de todos los aviones Avianca. Ajuste antes de continuar."
                elif altura > 63:
                    alerta = "⚠ Solo puede volar en avión Carguero (Freighter)."
            except ValueError:
                alerta = "⚠ Ingrese un número válido para altura en pulgadas."
        elif pregunta_id == 5:  # Peso > 150kg
            try:
                peso = float(respuesta)
                if peso > 150:
                    alerta = "⚠ Es obligatorio usar base de madera (shoring) para distribuir el peso."
            except ValueError:
                alerta = "⚠ Ingrese un número válido para peso en kg."

    # Fase 3: Contenidos Críticos
    if fase == 3:
        if pregunta_id == 10:  # Baterías
            if respuesta.lower() in ['sí', 'si', 'yes']:
                alerta = "⚠ Requiere 2 originales de Shipper’s Declaration (DGR). Omitirlo es delito federal."
        if pregunta_id == 11:  # Origen animal/vegetal
            if respuesta.lower() in ['sí', 'si', 'yes']:
                alerta = "⚠ Debe presentar Certificado Fitosanitario o Prior Notice FDA."

    # Fase 4: Documental final
    if fase == 4:
        if pregunta_id == 12:  # AWB
            if respuesta.lower() not in ['sí', 'si', 'yes']:
                alerta = "⚠ Faltan originales o copias de AWB. El chofer perderá su turno."

    # Fase 5: Logística de arribo
    if fase == 5:
        if pregunta_id == 13:  # Hora de llegada
            alerta = "⚠ Cut-off 4 horas antes del vuelo. Llegadas tarde generan cargos por storage."

    # Fase 6: Integridad física y embalaje
    if fase == 6:
        if pregunta_id in [14,15,16,17,18]:  # Flejes, etiquetas, plástico
            alerta = "⚠ Verifique embalaje, flejes y etiquetas. Carga puede ser rechazada."

    # Fase 7 y 8: Seguridad visual y contenedores
    if fase in [7,8]:
        alerta = "⚠ Verifique limpieza, etiquetas, número de piezas y Overhang de pallet."

    return alerta
