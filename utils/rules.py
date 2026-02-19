def evaluar_reglas_duras(data):

    errores = []
    bloqueado = False

    # TSA / ITN
    if data.highValue == "yes" and not data.itnNumber:
        errores.append("FALTA ITN PARA EXPORTACION MAYOR A $2500")
        bloqueado = True

    # Zip
    if data.zipCheck == "no":
        errores.append("ZIP CODE NO VALIDADO")
        bloqueado = True

    # DGR
    if data.cargoType == "DGR" and data.dgrDocs == "no":
        errores.append("MERCANCIA PELIGROSA SIN DECLARACION ORIGINAL")
        bloqueado = True

    # PER
    if data.cargoType == "PER" and data.fitoDocs == "no":
        errores.append("CARGA PERECEDERA SIN CERTIFICADO FITOSANITARIO")
        bloqueado = True

    # Altura
    if data.pieceHeight > 96:
        errores.append("ALTURA EXCEDE LIMITES DE FLEET")
        bloqueado = True
    elif data.pieceHeight > 63:
        errores.append("SOLO PUEDE VIAJAR EN CARGUERO")

    # NIMF
    if data.nimf15 == "no":
        errores.append("PALLET SIN SELLO NIMF-15")
        bloqueado = True

    # Daños
    if data.damaged == "yes":
        errores.append("CAJAS DANADAS DETECTADAS")
        bloqueado = True

    # Overhang
    if data.overhang == "yes":
        errores.append("OVERHANG DETECTADO EN PALLET")
        bloqueado = True

    return {
        "status": "VUELA" if not bloqueado else "NO VUELA",
        "detalles": errores if errores else ["CUMPLE CON REQUISITOS OPERATIVOS"]
    }
