from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime

app = Flask(__name__, static_folder="static")

def validate_cargo(data):
    errors = []
    warnings = []
    score = 100
    
    actor = data.get("actor")
    cargo_type = data.get("cargo_type")
    aircraft = data.get("aircraft")
    packaging = data.get("packaging")
    pieces = data.get("pieces", [])
    
    # 1. SEGMENTACIÓN POR ACTOR (Documentación)
    if actor == "driver":
        warnings.append("Camionero: Asegúrese de tener el ID vigente y el número de cita (Dock Token) para Avianca MIA.")
        if not pieces:
            errors.append("No se puede verificar carga sin dimensiones físicas.")
            score -= 20

    if actor == "forwarder" and data.get("consol") == "consol":
        warnings.append("Consolidado: Requiere Master AWB y House AWBs vinculados correctamente.")

    # 2. SEGMENTACIÓN POR TIPO DE CARGA (IATA / TSA)
    if cargo_type == "dg":
        errors.append("DG: Requiere Shipper's Declaration firmada y MSDS visible.")
        if aircraft == "pax":
            errors.append("RECHAZO: Mercancía Peligrosa prohibida o altamente restringida en vuelos PAX.")
            score -= 60
        warnings.append("Asesoría: Verifique etiquetas Clase 9 / ELI-ELM si contiene Litio.")

    if cargo_type == "per":
        warnings.append("PER: Prioridad de cadena de frío. Verifique tiempo de exposición en rampa MIA.")
    
    if cargo_type == "avi":
        errors.append("AVI: Requiere LAR (Live Animals Regulations) y certificado de salud.")
        score -= 10

    # 3. TRATAMIENTO DE EMBALAJE (Fumigación / Seguridad)
    if packaging == "pallet_wd":
        warnings.append("MADERA: Debe mostrar sello ISPM15 visible. Si está dañado, cambiar por pallet plástico.")
    
    if packaging == "uld":
        warnings.append("ULD: Verifique integridad estructural. Cualquier golpe en la base es motivo de rechazo por seguridad de vuelo.")

    # 4. DIMENSIONES Y POSICIÓN (Lógica de Aeronave Avianca)
    total_weight = 0
    total_vol = 0
    
    # Límites aproximados por posición (A330 PAX vs 767F)
    max_h = 160 if aircraft == "pax" else 240
    
    for p in pieces:
        try:
            l = float(p.get("l", 0))
            w = float(p.get("w", 0))
            h = float(p.get("h", 0))
            kg = float(p.get("kg", 0))
            
            total_weight += kg
            total_vol += (l * w * h) / 1000000 # m3
            
            if h > max_h:
                errors.append(f"RECHAZO: Altura {h}cm excede el límite de {max_h}cm para avión {aircraft.upper()}.")
                score -= 40
                
            # Regla de contorneo (Overhang)
            if l > 317 or w > 244:
                errors.append(f"RECHAZO: Dimensiones exceden base de pallet estándar (PMC/P6P).")
                score -= 30
        except ValueError:
            errors.append("Error en formato de medidas.")

    # 5. SEGMENTACIÓN DE RIESGO TSA
    if data.get("movement") == "transfer":
        warnings.append("TRANSFER: Verifique que el sello de seguridad (Seal) coincida con el manifiesto de origen.")

    # RESULTADO FINAL
    if score >= 90 and not errors:
        status = "LISTO PARA COUNTER"
        level = "green"
    elif score >= 60:
        status = "REVISAR Y CORREGIR"
        level = "yellow"
    else:
        status = "NO APTO / RECHAZO"
        level = "red"

    return {
        "status": status,
        "level": level,
        "score": max(0, score),
        "errors": errors,
        "warnings": warnings,
        "total_weight": total_weight,
        "total_vol": total_vol,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

@app.route("/")
def home():
    return send_from_directory("static", "app.html")

@app.route("/api/check", methods=["POST"])
def check():
    data = request.get_json()
    result = validate_cargo(data)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
