import os, json, base64
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

if not os.path.exists("static"): os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/evaluar")
async def evaluar(data: str = Form(...), fotos: list[UploadFile] = File(None)):
    payload = json.loads(data)
    texto = payload.get("dictado", "").upper()
    bultos = payload.get("detalle_bultos", [])
    
    alertas = []
    soluciones = []
    
    # --- ASESORÍA TÉCNICA (DOT/IATA/CBP) ---
    # Seguridad y Mercancías Peligrosas
    if any(w in texto for w in ["BATTERY", "BATERIA", "LITHIUM", "DGR", "PELIGROSA"]):
        if not payload['docs'].get('msds'):
            alertas.append("❌ Carga DGR detectada sin MSDS/DGD.")
            soluciones.append("💡 Solicitar Declaración de Mercancías Peligrosas y MSDS actualizada.")

    # Embalaje (CBP/Aduana)
    if payload.get("tipo_pallet") == "Wood" and not payload['chk'].get('fumigado'):
        alertas.append("❌ Pallet de madera sin sello NIMF-15 visible.")
        soluciones.append("💡 Rectificar: Cambiar por pallet plástico o madera certificada antes del ingreso.")

    # --- CÁLCULOS Y AERONAVEGABILIDAD ---
    rows_html = ""
    total_kg = 0
    max_h = 0
    for b in bultos:
        try:
            c, l, w, h, p = int(b['cant']), float(b['l']), float(b['w']), float(b['h']), float(b['p'])
            total_kg += (c * p)
            if h > max_h: max_h = h
            rows_html += f"<tr><td>{c}</td><td>{l}x{w}x{h}</td><td>{p}</td></tr>"
        except: continue

    equipo = "PAX (BELLY)" if max_h <= 160 else "FREIGHTER (MAIN DECK)"
    if max_h > 244:
        alertas.append("❌ Altura excede límites de bodega (Max 244cm).")
        soluciones.append("💡 Re-paletizar para bajar altura o coordinar carga sobredimensionada.")

    # Procesar Fotos
    img_data = []
    if fotos:
        for f in fotos:
            content = await f.read()
            encoded = base64.b64encode(content).decode('utf-8')
            img_data.append(f"data:image/jpeg;base64,{encoded}")

    status = "RECHAZADO / HOLD" if alertas else "LISTO PARA VUELO"
    
    tabla = f"""
    <table>
        <tr><th>PCS</th><th>DIMS (cm)</th><th>KG/U</th></tr>
        {rows_html}
    </table>
    <div style='margin-top:10px; background:#f1f5f9; padding:10px; border-radius:5px;'>
        <strong>TOTAL:</strong> {total_kg} KG | <strong>EQUIPO:</strong> {equipo}
    </div>
    """

    return {
        "status": status,
        "tabla": tabla,
        "alertas": alertas,
        "soluciones": soluciones,
        "fotos": img_data
    }
