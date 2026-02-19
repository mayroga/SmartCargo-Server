# utils/rules.py
# Reglas automáticas de validación SMARTCARGO-AIPA

from config import ALERTAS, MAX_HEIGHT_PASSENGER, MAX_HEIGHT_FREIGHTER, MAX_WEIGHT_SINGLE

def validar_respuesta(pregunta_id: int, respuesta: str) -> str:
    """
    Evalúa la respuesta del usuario y retorna alerta si aplica.
    """
    r = respuesta.strip().lower()
    alerta = ""

    # ============================
    # FASE 1: Identificación y Seguridad
    if pregunta_id == 1 and r == "":
        alerta = "⚠ Debe ingresar su ID o SCAC para Known Shipper."
    if pregunta_id == 2 and r in ["sí", "si", "yes"]:
        alerta = ALERTAS["itn_faltante"]
    if pregunta_id == 3 and r in ["consolidado", "multiple"]:
        alerta = "⚠ Debe generar Manifiesto de Carga y Houses exactas."

    # ============================
    # FASE 2: Anatomía de la Carga
    if pregunta_id == 4:
        try:
            altura = float(r.replace('"',''))
            if altura > MAX_HEIGHT_FREIGHTER:
                alerta = ALERTAS["altura_maxima"]
            elif altura > MAX_HEIGHT_PASSENGER:
                alerta = ALERTAS["altura_carguero"]
        except:
            alerta = "Ingrese altura válida en pulgadas."
    if pregunta_id == 5 and any(x in r for x in ["sí","si","yes"]):
        alerta = ALERTAS["peso_excede"]
    if pregunta_id == 6 and "nimf" not in r:
        alerta = "⚠ Pallet sin sello NIMF-15; use pallet plástico o certificado."

    # ============================
    # FASE 3: Contenidos Críticos (DGR/IATA)
    if pregunta_id == 7 and any(x in r for x in ["sí","si","yes"]):
        alerta = "⚠ Mercancía DGR; requiere 2 originales Shipper’s Declaration."
    if pregunta_id == 8 and any(x in r for x in ["sí","si","yes"]):
        alerta = "⚠ Requiere Certificado Fitosanitario o Prior Notice FDA."

    # ============================
    # FASE 4: Check-list Documental
    if pregunta_id == 9 and "no" in r:
        alerta = "⚠ Faltan originales/copias; pérdida de turno en el counter."
    if pregunta_id == 10 and "no" in r:
        alerta = "⚠ Código postal incorrecto; sistema bloquea guía."

    # ============================
    # FASE 5: Logística de Arribo
    if pregunta_id == 11:
        alerta = "⚠ Recuerde: Cut-off 4h antes del vuelo; llegada tardía = cargos Storage."

    # ============================
    # FASE 6: Integridad Física y Embalaje
    if pregunta_id == 12 and "plástico" in r:
        alerta = "⚠ Tanques/motores pesados deben tener flejes metálicos."
    if pregunta_id == 13 and "no" in r:
        alerta = "⚠ Cada bulto debe tener número AWB visible; carga huérfana si no."
    if pregunta_id == 14 and "sí" in r:
        alerta = "⚠ Cajas dañadas = rechazo; cambiar antes de enviar."
    if pregunta_id == 15 and "no" in r:
        alerta = "⚠ Plástico flojo = riesgo; counter puede devolver camión."
    if pregunta_id == 16 and "sí" in r:
        alerta = "⚠ Etiquetas viejas deben eliminarse para evitar confusión."

    # ============================
    # FASE 7: Seguridad TSA
    if pregunta_id == 17 and "no" in r:
        alerta = "⚠ Limpie olores/aceites; riesgo DGR."
    if pregunta_id == 18 and "no estibar" in r:
        alerta = "⚠ Costo de flete puede aumentar; restricción de carga."
    if pregunta_id == 19 and "no" in r:
        alerta = "⚠ Número de piezas no coincide; corrija documento."

    # ============================
    # FASE 8: Equipos y Contenedores
    if pregunta_id == 20 and any(x in r for x in ["sí","si","yes"]):
        alerta = "⚠ Tanques/cilindros deben estar vacíos y con certificación; válvulas protegidas."
    if pregunta_id == 21 and any(x in r for x in ["sí","si","yes"]):
        alerta = "⚠ Overhang detectado; re-estibar carga para alinear con borde del pallet."

    return alerta
