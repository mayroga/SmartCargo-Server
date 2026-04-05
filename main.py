from flask import Flask, request, jsonify, send_from_directory
import json
import os

app = Flask(__name__, static_folder="static")

# =========================
# LOAD RULES
# =========================

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

AVIATION_RULES = load_json("static/avianca_rules.json")
CARGO_RULES = load_json("static/cargo_rules.json")


# =========================
# CORE VALIDATION ENGINE
# =========================

def validate_documents(cargo_type, docs):
    required = CARGO_RULES.get(cargo_type, {}).get("documents", [])
    missing = [d for d in required if d not in docs]

    return {
        "cargo_type": cargo_type,
        "required_documents": required,
        "missing_documents": missing,
        "document_status": "FAIL" if missing else "PASS"
    }


def validate_weight(height_in, weight_kg, uld_type):
    aircraft = AVIATION_RULES["aircraft_limits"]

    height_limit = aircraft["max_height_freighter_in"]
    weight_limit = aircraft["max_piece_weight_kg"]

    errors = []

    if height_in > height_limit:
        errors.append(f"ALTURA EXCEDE LIMITE ({height_in} > {height_limit})")

    if weight_kg > weight_limit:
        errors.append(f"PESO EXCEDE LIMITE ({weight_kg} > {weight_limit})")

    uld = AVIATION_RULES["uld_types"].get(uld_type)

    if uld and weight_kg > uld.get("max_weight_kg", 0):
        errors.append("EXCEDE LIMITE ULD")

    return {
        "height_check": "PASS" if height_in <= height_limit else "FAIL",
        "weight_check": "PASS" if weight_kg <= weight_limit else "FAIL",
        "uld_check": "PASS" if not errors else "FAIL",
        "errors": errors
    }


def detect_risk_flags(data):
    flags = []

    if data.get("dg"):
        flags.append("DANGEROUS_GOODS")

    if data.get("lithium_batteries"):
        flags.append("LITHIUM_BATTERY")

    if data.get("perishable"):
        flags.append("PERISHABLE")

    if data.get("human_remains"):
        flags.append("HUMAN_REMAINS")

    if data.get("high_value"):
        flags.append("HIGH_VALUE")

    return flags


# =========================
# MAIN ENDPOINT
# =========================

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json

    cargo_type = data.get("cargo_type", "GENERAL")
    docs = data.get("documents", [])

    doc_result = validate_documents(cargo_type, docs)

    physical = validate_weight(
        data.get("height_in", 0),
        data.get("weight_kg", 0),
        data.get("uld_type", "")
    )

    risks = detect_risk_flags(data)

    return jsonify({
        "document_check": doc_result,
        "physical_check": physical,
        "risk_flags": risks,
        "overall_status": "REJECT" if (
            doc_result["missing_documents"] or physical["errors"]
        ) else "CLEARED"
    })


# =========================
# STATIC FRONTEND
# =========================

@app.route("/")
def home():
    return send_from_directory("static", "app.html")


if __name__ == "__main__":
    app.run(debug=True)
