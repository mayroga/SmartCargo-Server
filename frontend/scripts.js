// frontend/scripts.js
// SMARTCARGO-AIPA | Frontend actualizado 2026
const BASE_URL = "https://smartcargo-server.onrender.com"; // Asegúrate que sea tu URL real

// Elementos del DOM
const form = document.getElementById("cargoForm");
const alertaDiv = document.getElementById("alerta");
const fotosInput = document.getElementById("fotos");
const fotosPreview = document.getElementById("fotosPreview");
const generarPDFBtn = document.getElementById("generarPDF");
const limpiarBtn = document.getElementById("limpiarForm");

// ------------------------
// Preview de fotos + zoom
// ------------------------
fotosInput.addEventListener("change", () => {
    fotosPreview.innerHTML = "";
    const files = fotosInput.files;
    for (let i = 0; i < files.length; i++) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = document.createElement("img");
            img.src = e.target.result;
            img.style.maxWidth = "150px";
            img.style.margin = "5px";
            img.style.cursor = "zoom-in";
            img.addEventListener("click", () => {
                const zoomDiv = document.createElement("div");
                zoomDiv.style.position = "fixed";
                zoomDiv.style.top = 0;
                zoomDiv.style.left = 0;
                zoomDiv.style.width = "100%";
                zoomDiv.style.height = "100%";
                zoomDiv.style.backgroundColor = "rgba(0,0,0,0.8)";
                zoomDiv.style.display = "flex";
                zoomDiv.style.justifyContent = "center";
                zoomDiv.style.alignItems = "center";
                zoomDiv.style.cursor = "zoom-out";
                const zoomImg = document.createElement("img");
                zoomImg.src = e.target.result;
                zoomImg.style.maxWidth = "90%";
                zoomImg.style.maxHeight = "90%";
                zoomDiv.appendChild(zoomImg);
                zoomDiv.addEventListener("click", () => document.body.removeChild(zoomDiv));
                document.body.appendChild(zoomDiv);
            });
            fotosPreview.appendChild(img);
        };
        reader.readAsDataURL(files[i]);
    }
});

// ------------------------
// Enviar formulario a /evaluar
// ------------------------
form.addEventListener("submit", async (e) => {
    e.preventDefault();
    alertaDiv.innerText = "⏳ Evaluando carga...";

    try {
        const formData = new FormData(form);

        // Agregar fotos manualmente
        for (let i = 0; i < fotosInput.files.length; i++) {
            formData.append("fotos", fotosInput.files[i]);
        }

        const res = await axios.post(`${BASE_URL}/evaluar`, formData, {
            headers: { "Content-Type": "multipart/form-data" },
        });

        if (res.data.status) {
            alertaDiv.innerHTML = `<strong>Resultado:</strong> ${res.data.status}<br><pre>${res.data.detalles.join("\n")}</pre>`;
        } else {
            alertaDiv.innerText = "❌ Error: No se obtuvo resultado del servidor";
        }
    } catch (error) {
        console.error(error);
        alertaDiv.innerText = "❌ Error conectando con servidor. Revise su conexión o la URL.";
    }
});

// ------------------------
// Generar PDF
// ------------------------
generarPDFBtn.addEventListener("click", async () => {
    alertaDiv.innerText = "⏳ Generando PDF...";

    try {
        const formData = new FormData(form);
        for (let i = 0; i < fotosInput.files.length; i++) {
            formData.append("fotos", fotosInput.files[i]);
        }

        const res = await axios.post(`${BASE_URL}/generar_pdf`, formData, {
            headers: { "Content-Type": "multipart/form-data" },
        });

        if (res.data.filename) {
            // Abrir PDF generado en nueva ventana
            window.open(`${BASE_URL}/download/${res.data.filename}`, "_blank");
            alertaDiv.innerText = "✅ PDF generado y listo para descargar";
        } else {
            alertaDiv.innerText = "❌ Error generando PDF";
        }
    } catch (error) {
        console.error(error);
        alertaDiv.innerText = "❌ Error conectando con servidor para PDF";
    }
});

// ------------------------
// Limpiar formulario
// ------------------------
limpiarBtn.addEventListener("click", () => {
    form.reset();
    fotosPreview.innerHTML = "";
    alertaDiv.innerText = "";
});
