from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime

app = Flask(__name__, static_folder="static")

# =========================================================
# 🧠 VALIDACIÓN OPERATIVA REAL
# =========================================================

def validate(data):

    errors = []
    warnings = []
    score = 100

    # =========================
    # DG CHECK
    # =========================
    if data.get("dg") == "yes":

        if not data.get("msds"):
            errors.append("Falta MSDS (obligatorio para DG)")
            score -= 30

        if not data.get("shippers_declaration"):
            errors.append("Falta declaración del shipper")
            score -= 40

        if data.get("aircraft") == "passenger":
            errors.append("DG no permitido en avión de pasajeros sin aprobación")
            score -= 50

    # =========================
    # CARGA
    # =========================
    if data.get("special") == "yes":
        warnings.append("Carga especial: requiere revisión de aerolínea")
        score -= 10

    # =========================
    # MOVIMIENTO
    # =========================
    if data.get("movement") not in ["local", "transfer", "comat"]:
        errors.append("Movimiento inválido")
        score -= 40

    # =========================
    # PIEZAS
    # =========================
    pieces = data.get("pieces", [])

    total_weight = 0
    total_volume = 0

    for p in pieces:
        try:
            l = float(p.get("length", 0))
            w = float(p.get("width", 0))
            h = float(p.get("height", 0))
            kg = float(p.get("weight", 0))

            volume = (l * w * h) / 6000  # estándar cargo air
            total_weight += kg
            total_volume += volume

        except:
            errors.append("Error en medidas de pieza")

    # =========================
    # RESULTADO FINAL
    # =========================
    if len(errors) == 0 and score >= 80:
        status = "LISTO PARA COUNTER"
        level = "green"
    elif score >= 50:
        status = "REVISAR ANTES DE IR"
        level = "yellow"
    else:
        status = "NO LISTO PARA ENVÍO"
        level = "red"

    return {
        "status": status,
        "level": level,
        "score": max(0, score),
        "errors": errors,
        "warnings": warnings,
        "total_weight": total_weight,
        "total_volume": total_volume,
        "timestamp": datetime.utcnow().isoformat()
    }


# =========================================================
# 🌐 FRONT
# =========================================================

@app.route("/")
def home():
    return send_from_directory("static", "app.html")


@app.route("/api/check", methods=["POST"])
def check():
    data = request.get_json()
    return jsonify(validate(data))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
