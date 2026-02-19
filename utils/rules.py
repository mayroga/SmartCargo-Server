# utils/rules.py
from config import MAX_HEIGHT_PAX, MAX_HEIGHT_FRT, MAX_WEIGHT_SHORING, ULD_TYPES, MSJ_ASESORIA

def validar_embarque(data):
    """
    Analiza los datos del formulario y retorna una lista de consejos técnicos
    y un veredicto final de asesoría.
    """
    sugerencias = []
    puede_volar = True

    # 1. Validación de Seguridad y Gobierno (CBP/TSA)
    if data.highValue == "yes" and not data.itnNumber:
        sugerencias.append(MSJ_ASESORIA["itn_miss"])
        puede_volar = False

    # 2. Validación de Dimensiones y Altura
    if data.pieceHeight > MAX_HEIGHT_FRT:
        sugerencias.append(f"{MSJ_ASESORIA['height_crit']} (Máx: {MAX_HEIGHT_FRT}\")")
        puede_volar = False
    elif data.pieceHeight > MAX_HEIGHT_PAX:
        sugerencias.append(f"⚠ Restricción: Altura > {MAX_HEIGHT_PAX}\". Solo apto para avión CARGUERO.")

    # 3. Validación de Integridad de Madera (NIMF-15)
    if data.nimf15 == "no":
        sugerencias.append(MSJ_ASESORIA["nimf_error"])
        puede_volar = False

    # 4. Análisis de Peso y Shoring
    if data.pieceWeight > MAX_WEIGHT_SHORING:
        sugerencias.append(MSJ_ASESORIA["weight_warn"])

    # 5. Validación de ULD (Pallet)
    pallet_info = ULD_TYPES.get(data.palletType.upper())
    if pallet_info:
        if data.pieceHeight > pallet_info["max_height"]:
            sugerencias.append(f"❌ La altura excede la capacidad técnica del pallet {data.palletType}.")
            puede_volar = False
    
    # 6. Integridad Física
    if data.damagedBoxes == "yes":
        sugerencias.append("⚠ Cajas Dañadas: Se recomienda re-empacar para evitar rechazo en el counter.")
        puede_volar = False
    
    if data.overhang > 0:
        sugerencias.append(MSJ_ASESORIA["overhang_crit"])
        puede_volar = False

    # 7. Contenidos Críticos (DGR/Fitosanitario)
    if data.dangerousGoods == "yes":
        sugerencias.append(MSJ_ASESORIA["dgr_warn"])
    
    if data.origin == "yes":
        sugerencias.append("⚠ Origen Animal/Vegetal: Verifique Certificado Fitosanitario / FDA.")

    # Resultado Final
    veredicto = "Aprobado para Recepción" if puede_volar else "Requiere Corrección"
    
    return {
        "status": veredicto,
        "detalle": sugerencias
    }
