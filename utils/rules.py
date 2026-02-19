def asesorar_counter_avianca(data):
    reporte = []
    severidad_maxima = "OK"  # OK | OBSERVACION | BLOQUEO

    def marcar_bloqueo(mensaje):
        nonlocal severidad_maxima
        reporte.append(f"[CRITICO] {mensaje}")
        severidad_maxima = "BLOQUEO"

    def marcar_observacion(mensaje):
        nonlocal severidad_maxima
        if severidad_maxima != "BLOQUEO":
            severidad_maxima = "OBSERVACION"
        reporte.append(f"[ADVERTENCIA] {mensaje}")

    # ===============================
    # FASE 1: TSA / CBP
    # ===============================
    if data.highValue == "yes" and not data.itnNumber:
        marcar_bloqueo("Falta ITN. Multa CBP hasta $10,000. No despachar sin AES.")

    # ===============================
    # FASE 2: ANATOMIA AVIANCA
    # ===============================
    if data.pieceHeight > 96:
        marcar_bloqueo("Altura > 96\". No entra en ningún avión.")
    elif data.pieceHeight > 63:
        marcar_observacion("Altura > 63\". Solo permitido en carguero.")

    if data.pieceWeight > 150:
        marcar_observacion("Pieza >150kg. Requiere shoring certificado.")

    if data.nimf15 == "no":
        marcar_bloqueo("Madera sin sello NIMF-15. USDA puede rechazar.")

    # ===============================
    # FASE 4: DOCUMENTACION
    # ===============================
    if data.awbCopies == "no":
        marcar_bloqueo("Faltan originales y copias AWB.")

    # ===============================
    # FASE 6: INTEGRIDAD
    # ===============================
    if data.damagedBoxes == "yes":
        marcar_bloqueo("Cajas dañadas. Re-embalar antes de counter.")

    if data.straps == "no" and data.pieceWeight > 50:
        marcar_observacion("Flejado insuficiente para peso declarado.")

    if data.overhang > 0:
        marcar_bloqueo("Overhang detectado. No cumple con estándar ULD.")

    # ===============================
    # STATUS FINAL
    # ===============================
    if severidad_maxima == "BLOQUEO":
        status = "RECHAZO INMEDIATO"
    elif severidad_maxima == "OBSERVACION":
        status = "APROBADO CON OBSERVACIONES"
    else:
        status = "LISTO PARA DESPACHO"

    return {
        "status": status,
        "detalle": reporte if reporte else ["Carga cumple estándar operativo Avianca."]
    }
