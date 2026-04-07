from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime

app = Flask(__name__, static_folder="static")

# =========================================================
# 🧠 SAFE VALIDATION ENGINE (NO CRASH VERSION)
# =========================================================

def validate(data):

    data = data or {}

    errors = []
    warnings = []
    score = 100

    dg = data.get("dg", "no")
    msds = data.get("msds", "no")
    shipper = data.get("shippers_declaration", "no")
    aircraft = data.get("aircraft", "cargo")
    movement = data.get("movement", "local")
    special = data.get("special", "no")

    pieces = data.get("pieces") or []

    # =========================
    # DG LOGIC
    # =========================
    if dg == "yes":

        if msds != "yes":
            errors.append("Falta MSDS")
            score -= 30

        if shipper != "yes":
            errors.append("Falta declaración del shipper")
            score -= 40

        if aircraft == "passenger":
            errors.append("DG no permitido en pasajeros")
            score -= 50

    # =========================
    # MOVEMENT
    # =========================
    if movement not in ["local", "transfer", "comat"]:
        errors.append("Movimiento inválido")
        score -= 40

    # =========================
    # SPECIAL CARGO
    # =========================
    if special == "yes":
        warnings.append("Carga especial requiere revisión")
        score -= 10

    # =========================
    # PIECES SAFE LOOP
    # =========================
    total_weight = 0
    total_volume = 0

    for p in pieces:
        try:
            l = float(p.get("length", 0) or 0)
            w = float(p.get("width", 0) or 0)
            h = float(p.get("height", 0) or 0)
            kg = float(p.get("weight", 0) or 0)

            volume = (l * w * h) / 6000

            total_weight += kg
            total_volume += volume

        except:
            errors.append("Error en pieza")

    score = max(0, min(score, 100))

    if len(errors) == 0 and score >= 80:
        status = "OK PARA COUNTER"
        level = "green"
    elif score >= 50:
        status = "REVISAR"
        level = "yellow"
    else:
        status = "NO LISTO"
        level = "red"

    return {
        "status": status,
        "level": level,
        "score": score,
        "errors": errors,
        "warnings": warnings,
        "total_weight": total_weight,
        "total_volume": total_volume,
        "timestamp": datetime.utcnow().isoformat()
    }

# =========================================================
# ROUTES SAFE
# =========================================================

@app.route("/")
def home():
    return send_from_directory("static", "app.html")


@app.route("/api/check", methods=["POST"])
def check():
    try:
        data = request.get_json(force=True)
        return jsonify(validate(data))
    except Exception as e:
        return jsonify({
            "status": "SERVER ERROR",
            "error": str(e),
            "level": "red"
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
