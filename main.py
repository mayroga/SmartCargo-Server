# =========================================================
# 🧠 PRE COUNTER CARGO ENGINE (NO FLASK VERSION)
# =========================================================

def check_cargo(data):

    errors = []
    warnings = []
    score = 100

    dg = data.get("dg", "no")
    msds = data.get("msds", "no")
    shipper = data.get("shipper", "no")
    aircraft = data.get("aircraft", "cargo")
    movement = data.get("movement", "local")
    special = data.get("special", "no")
    pieces = data.get("pieces", [])

    # =========================
    # DG RULES
    # =========================
    if dg == "yes":

        if msds == "no":
            errors.append("Falta MSDS")
            score -= 30

        if shipper == "no":
            errors.append("Falta declaración del shipper")
            score -= 40

        if aircraft == "passenger":
            errors.append("DG no permitido en pasajeros")
            score -= 50

    # =========================
    # MOVIMIENTO
    # =========================
    if movement not in ["local", "transfer", "comat"]:
        errors.append("Movimiento inválido")
        score -= 40

    # =========================
    # ESPECIAL
    # =========================
    if special == "yes":
        warnings.append("Carga especial requiere revisión")
        score -= 10

    # =========================
    # PIEZAS
    # =========================
    total_weight = 0
    total_volume = 0

    for p in pieces:
        try:
            l = float(p.get("length", 0))
            w = float(p.get("width", 0))
            h = float(p.get("height", 0))
            kg = float(p.get("weight", 0))

            volume = (l * w * h) / 6000

            total_weight += kg
            total_volume += volume

        except:
            errors.append("Error en medidas de pieza")

    # =========================
    # SCORE FINAL
    # =========================
    score = max(0, min(score, 100))

    if len(errors) == 0 and score >= 80:
        status = "LISTO PARA COUNTER"
        level = "green"
    elif score >= 50:
        status = "REVISAR ANTES DEL COUNTER"
        level = "yellow"
    else:
        status = "NO LISTO PARA ENVIO"
        level = "red"

    return {
        "status": status,
        "level": level,
        "score": score,
        "errors": errors,
        "warnings": warnings,
        "total_weight": total_weight,
        "total_volume": total_volume
    }


# =========================================================
# 🧪 TEST LOCAL (OPCIONAL)
# =========================================================
if __name__ == "__main__":

    sample = {
        "dg": "yes",
        "msds": "no",
        "shipper": "no",
        "aircraft": "passenger",
        "movement": "local",
        "special": "no",
        "pieces": [
            {"length": 100, "width": 50, "height": 40, "weight": 20}
        ]
    }

    result = check_cargo(sample)

    print("RESULTADO PRE COUNTER")
    print(result)
