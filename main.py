from flask import Flask, request, jsonify, send_from_directory
import os

app = Flask(__name__, static_folder="static")

# =========================================================
# 🧠 LÓGICA DE ASESORÍA (CBP, TSA, IATA)
# =========================================================

def validate_cargo(data):
    errors = []
    warnings = []
    score = 100
    
    # Extracción de datos
    actor = data.get("actor")
    cargo_type = data.get("cargo_type")
    aircraft = data.get("aircraft")
    packaging = data.get("packaging")
    pieces = data.get("pieces", [])
    
    # Reglas de Negocio Específicas
    if not pieces:
        errors.append("No hay piezas registradas para verificar.")
        score = 0
    
    if cargo_type == "dg":
        if aircraft == "pax":
            errors.append("PROHIBIDO: DG no vuela en avión de pasajeros (PAX).")
            score -= 60
        warnings.append("DG: Requiere Shipper's Declaration y MSDS original.")

    if packaging == "pallet_wd":
        warnings.append("MADERA: Verificar sello ISPM15 para evitar rechazo en counter.")

    total_weight = 0
    total_vol = 0
    max_h = 160 if aircraft == "pax" else 244

    for p in pieces:
        try:
            l, w, h, kg = float(p['l']), float(p['w']), float(p['h']), float(p['kg'])
            total_weight += kg
            total_vol += (l * w * h) / 1000000
            if h > max_h:
                errors.append(f"RECHAZO: Altura {h}cm excede límite de {max_h}cm.")
                score -= 40
        except (ValueError, KeyError):
            errors.append("Datos de pieza incompletos o inválidos.")

    # Estado Final
    if score >= 90 and not errors:
        status, level = "LISTO PARA COUNTER", "green"
    elif score >= 60:
        status, level = "REVISAR ACCIONES", "yellow"
    else:
        status, level = "NO APTO / RECHAZO", "red"

    return {
        "status": status, "level": level, "score": max(0, score),
        "errors": errors, "warnings": warnings,
        "total_weight": total_weight, "total_vol": total_vol
    }

# =========================================================
# 🌐 RUTAS DE CONEXIÓN
# =========================================================

@app.route("/")
def index():
    # Sirve el archivo app.html desde la carpeta static
    return send_from_directory(app.static_folder, "app.html")

@app.route("/api/check", methods=["POST"])
def check():
    # Recibe el JSON del frontend
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Procesa y retorna respuesta
    result = validate_cargo(data)
    return jsonify(result)

if __name__ == "__main__":
    # Puerto 5000 por defecto
    app.run(host="0.0.0.0", port=5000, debug=True)
