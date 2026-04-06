from flask import Flask, request, jsonify, render_template
from datetime import datetime

app = Flask(__name__)

# =========================================================
# 🧠 SIMULATION KNOWLEDGE BASE (NO PERSISTENCIA OPERATIVA)
# =========================================================

RULES = [
    {
        "id": "DG_PASSENGER_AIRCRAFT",
        "layer": "IATA_SIM",
        "severity": "HIGH",
        "condition": lambda d: d.get("dg") == "yes" and d.get("aircraft") == "passenger",
        "message": "DG detected on PASSENGER aircraft requires enhanced screening simulation"
    },
    {
        "id": "MISSING_MSDS_DG",
        "layer": "IATA_SIM",
        "severity": "HIGH",
        "condition": lambda d: d.get("dg") == "yes" and not d.get("msds"),
        "message": "MSDS missing for DG shipment simulation"
    },
    {
        "id": "CONSOLIDATED_UNITARY_CONFLICT",
        "layer": "OPS_SIM",
        "severity": "MEDIUM",
        "condition": lambda d: d.get("consolidated") == "yes" and d.get("unitary") == "yes",
        "message": "Conflict: Consolidated and Unitary declared simultaneously"
    },
    {
        "id": "SPECIAL_CARGO_FLAG",
        "layer": "AIRLINE_SIM",
        "severity": "MEDIUM",
        "condition": lambda d: d.get("special") == "yes",
        "message": "Special cargo requires airline approval simulation layer"
    },
    {
        "id": "INVALID_MOVEMENT",
        "layer": "OPS_SIM",
        "severity": "HIGH",
        "condition": lambda d: d.get("movement") not in ["local", "transfer", "comat"],
        "message": "Invalid movement type detected"
    },
    {
        "id": "DG_WITHOUT_DECLARATION",
        "layer": "IATA_SIM",
        "severity": "HIGH",
        "condition": lambda d: d.get("dg") == "yes" and not d.get("shippers_declaration"),
        "message": "Shipper Declaration missing for DG shipment"
    },
    {
        "id": "TYPE_A_DG_COMPATIBILITY",
        "layer": "PACKAGING_SIM",
        "severity": "LOW",
        "condition": lambda d: d.get("packaging") == "type_a" and d.get("dg") == "no",
        "message": "Packaging Type A used for NON-DG (check efficiency simulation)"
    },
    {
        "id": "TYPE_B_DG_OK",
        "layer": "PACKAGING_SIM",
        "severity": "INFO",
        "condition": lambda d: d.get("packaging") == "type_b" and d.get("dg") == "yes",
        "message": "Packaging Type B compatible with DG simulation rules"
    }
]


# =========================================================
# 🧠 DECISION ENGINE
# =========================================================

def simulate_decision(data):
    triggered_rules = []

    for rule in RULES:
        try:
            if rule["condition"](data):
                triggered_rules.append(rule)
        except:
            continue

    # SCORE SYSTEM (SIMULATED OPERATIONS)
    score = 100

    for r in triggered_rules:
        if r["severity"] == "HIGH":
            score -= 35
        elif r["severity"] == "MEDIUM":
            score -= 20
        elif r["severity"] == "LOW":
            score -= 5
        else:
            score -= 1

    # FINAL STATE MACHINE
    if score >= 85:
        status = "RELEASE"
        level = "green"
    elif score >= 60:
        status = "CONDITIONAL RELEASE"
        level = "yellow"
    elif score >= 30:
        status = "HOLD FOR REVIEW"
        level = "orange"
    else:
        status = "SIMULATION REJECT"
        level = "red"

    return {
        "status": status,
        "level": level,
        "score": score,
        "triggered_rules": triggered_rules,
        "timestamp": datetime.utcnow().isoformat()
    }


# =========================================================
# 🌐 ROUTES
# =========================================================

@app.route("/")
def home():
    return render_template("app.html")


@app.route("/api/simulate", methods=["POST"])
def simulate():
    data = request.json
    result = simulate_decision(data)
    return jsonify(result)


# =========================================================
# 🚀 RUN
# =========================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
