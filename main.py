# main.py

```python
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='static')

# -----------------------------
# CORE PRE-CHECK ENGINE
# -----------------------------

def evaluate_shipment(data):
    errors = []
    warnings = []

    # Required fields
    required_fields = ["shipper", "consignee", "cargo_type", "dg", "documents"]
    for f in required_fields:
        if not data.get(f):
            errors.append(f"Missing field: {f}")

    # DG logic
    if data.get("dg") == True:
        if not data.get("msds"):
            errors.append("DG cargo requires MSDS")
        if not data.get("dg_declaration"):
            errors.append("DG requires Shipper Declaration")

    # Cargo type rules
    if data.get("cargo_type") == "consolidated" and not data.get("consol_details"):
        warnings.append("Consolidated cargo missing details")

    if data.get("cargo_type") == "special":
        if not data.get("special_approval"):
            errors.append("Special cargo requires approval")

    # Embalaje check
    if not data.get("packaging_type"):
        warnings.append("Packaging type not specified")

    # Aircraft type
    if data.get("aircraft") == "passenger" and data.get("dg"):
        warnings.append("DG on passenger aircraft may be restricted")

    # Transfer logic
    if data.get("routing") == "transfer" and not data.get("transit_docs"):
        errors.append("Transfer cargo requires transit documentation")

    # Final decision
    if errors:
        status = "BLOCK"
    elif warnings:
        status = "RISK"
    else:
        status = "OK"

    return {
        "status": status,
        "errors": errors,
        "warnings": warnings
    }

# -----------------------------
# ROUTES
# -----------------------------

@app.route("/")
def index():
    return send_from_directory("static", "app.html")

@app.route("/api/check", methods=["POST"])
def check():
    data = request.json
    result = evaluate_shipment(data)
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
```

---

# static/app.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SmartCargo PreCheck</title>
    <style>
        body {
            font-family: Arial;
            background: #0b0f19;
            color: white;
            padding: 20px;
        }
        input, select {
            padding: 10px;
            margin: 5px;
            width: 300px;
        }
        button {
            padding: 10px 20px;
            background: #1f6feb;
            color: white;
            border: none;
            cursor: pointer;
        }
        .box {
            margin-top: 20px;
            padding: 15px;
            border-radius: 10px;
            background: #161b22;
        }
        .OK { color: #2ea043; }
        .RISK { color: #d29922; }
        .BLOCK { color: #f85149; }
    </style>
</head>
<body>

<h1>SMARTCARGO PRE-CHECK SYSTEM</h1>

<div>
    <input id="shipper" placeholder="Shipper"><br>
    <input id="consignee" placeholder="Consignee"><br>

    <select id="cargo_type">
        <option value="general">General</option>
        <option value="special">Special</option>
        <option value="consolidated">Consolidated</option>
        <option value="unitary">Unitary</option>
    </select><br>

    <select id="dg">
        <option value="false">Non-DG</option>
        <option value="true">DG</option>
    </select><br>

    <select id="aircraft">
        <option value="cargo">Cargo Aircraft</option>
        <option value="passenger">Passenger Aircraft</option>
    </select><br>

    <select id="routing">
        <option value="local">Local</option>
        <option value="transfer">Transfer</option>
        <option value="comat">COMAT</option>
    </select><br>

    <input id="documents" placeholder="Documents OK? (yes/no)"><br>
    <input id="msds" placeholder="MSDS (if DG)"><br>
    <input id="dg_declaration" placeholder="DG Declaration"><br>
    <input id="packaging_type" placeholder="Packaging Type A/B"><br>
    <input id="consol_details" placeholder="Consolidation Details"><br>
    <input id="special_approval" placeholder="Special Approval"><br>
    <input id="transit_docs" placeholder="Transit Docs"><br>

    <button onclick="check()">RUN PRECHECK</button>
</div>

<div class="box" id="result"></div>

<script>
async function check() {
    const data = {
        shipper: document.getElementById("shipper").value,
        consignee: document.getElementById("consignee").value,
        cargo_type: document.getElementById("cargo_type").value,
        dg: document.getElementById("dg").value === "true",
        aircraft: document.getElementById("aircraft").value,
        routing: document.getElementById("routing").value,
        documents: document.getElementById("documents").value,
        msds: document.getElementById("msds").value,
        dg_declaration: document.getElementById("dg_declaration").value,
        packaging_type: document.getElementById("packaging_type").value,
        consol_details: document.getElementById("consol_details").value,
        special_approval: document.getElementById("special_approval").value,
        transit_docs: document.getElementById("transit_docs").value
    };

    const res = await fetch("/api/check", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
    });

    const out = await res.json();

    document.getElementById("result").innerHTML = `
        <h2 class="${out.status}">STATUS: ${out.status}</h2>
        <h3>Errors</h3>
        <ul>${out.errors.map(e => `<li>${e}</li>`).join("")}</ul>
        <h3>Warnings</h3>
        <ul>${out.warnings.map(w => `<li>${w}</li>`).join("")}</ul>
    `;
}
</script>

</body>
</html>
```
