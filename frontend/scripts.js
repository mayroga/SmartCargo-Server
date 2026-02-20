let items = [];

function agregarItem(){
    const container = document.getElementById("itemsContainer");
    const idx = items.length;
    const div = document.createElement("div");
    div.classList.add("item-box");
    div.innerHTML = `
        <h3>Pieza ${idx+1}</h3>
        <input type="text" placeholder="Descripción" id="desc_${idx}" required><br>
        <input type="number" placeholder="Largo (cm)" id="length_${idx}" required>
        <input type="number" placeholder="Ancho (cm)" id="width_${idx}" required>
        <input type="number" placeholder="Alto (cm)" id="height_${idx}" required><br>
        <input type="number" placeholder="Peso (kg)" id="weight_${idx}" required>
        <label>Pallet <input type="checkbox" id="pallet_${idx}"></label>
        <label>Daños <input type="checkbox" id="damaged_${idx}"></label>
        <label>NIMF-15 <input type="checkbox" id="nimf15_${idx}" checked></label>
        <label>Overhang <input type="checkbox" id="overhang_${idx}"></label>
    `;
    container.appendChild(div);
    items.push({});
}

async function evaluarCarga(){
    const client_name = document.getElementById("client_name").value;
    const contact = document.getElementById("contact").value;
    const client_type = document.getElementById("client_type").value;
    const shipment_type = document.getElementById("shipment_type").value;
    const cargo_type = document.getElementById("cargo_type").value;

    if(!client_name || !contact || !client_type || !shipment_type || !cargo_type){
        alert("⚠ Complete todos los campos de identificación antes de continuar.");
        return;
    }

    const cargoItems = items.map((_, idx) => ({
        description: document.getElementById(`desc_${idx}`).value,
        length_cm: parseFloat(document.getElementById(`length_${idx}`).value),
        width_cm: parseFloat(document.getElementById(`width_${idx}`).value),
        height_cm: parseFloat(document.getElementById(`height_${idx}`).value),
        weight_kg: parseFloat(document.getElementById(`weight_${idx}`).value),
        pallet: document.getElementById(`pallet_${idx}`).checked,
        damaged: document.getElementById(`damaged_${idx}`).checked ? "yes" : "no",
        nimf15: document.getElementById(`nimf15_${idx}`).checked ? "yes" : "no",
        overhang: document.getElementById(`overhang_${idx}`).checked ? "yes" : "no",
    }));

    const payload = {
        client_name, contact, client_type, shipment_type, cargo_type,
        items: cargoItems
    };

    try{
        const r = await axios.post("/evaluar", payload);
        const data = r.data;
        let html = `<h3>Estado: ${data.estado}</h3>`;
        html += "<ul>";
        data.items.forEach(i => {
            html += `<li>Pieza ${i.index}: Alertas: ${i.alertas.join(", ")} - Dimensiones: ${i.length_cm}x${i.width_cm}x${i.height_cm} cm / ${i.length_in}x${i.width_in}x${i.height_in} in - Peso: ${i.weight_kg} kg / ${i.weight_lb} lb - Volumen: ${i.volumen_m3} m3 - Peso cobrable: ${i.peso_cobrable} kg</li>`;
        });
        html += "</ul>";
        html += `<p>Reporte PDF: <a href="${data.pdf}" target="_blank">Descargar</a></p>`;
        document.getElementById("resultado").innerHTML = html;
    }catch(e){
        console.error(e);
        alert("Error evaluando la carga.");
    }
}
