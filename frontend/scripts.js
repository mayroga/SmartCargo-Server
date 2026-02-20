let piezas = [];

function validarCliente(){
    const cliente = {
        nombre: document.getElementById("nombre").value,
        contacto: document.getElementById("contacto").value,
        tipo_cliente: document.getElementById("tipo_cliente").value,
        tipo_envio: document.getElementById("tipo_envio").value,
        tipo_mercancia: document.getElementById("tipo_mercancia").value
    };

    axios.post("http://127.0.0.1:8000/validar_cliente", cliente)
    .then(res=>{
        let alertasDiv = document.getElementById("alertas_cliente");
        alertasDiv.innerHTML = res.data.alertas.join("<br>");
        let docDiv = document.getElementById("documentos");
        docDiv.innerHTML = "<b>Documentos requeridos:</b><br>" + res.data.documentos_requeridos.join("<br>");
    })
    .catch(err=>console.log(err));
}

function agregarPieza(){
    const pieza = {
        descripcion: document.getElementById("descripcion").value,
        largo_cm: parseFloat(document.getElementById("largo_cm").value),
        ancho_cm: parseFloat(document.getElementById("ancho_cm").value),
        alto_cm: parseFloat(document.getElementById("alto_cm").value),
        peso_kg: parseFloat(document.getElementById("peso_kg").value),
        en_pallet: document.getElementById("en_pallet").value === "true"
    };
    piezas.push(pieza);
    actualizarTabla();
}

function actualizarTabla(){
    axios.post("http://127.0.0.1:8000/validar_carga", {piezas: piezas, cliente:{nombre:"",contacto:"",tipo_cliente:"",tipo_envio:"",tipo_mercancia:""}})
    .then(res=>{
        let tabla = document.getElementById("tabla_piezas");
        tabla.innerHTML = `<tr>
            <th>Descripción</th><th>Largo cm/in</th><th>Ancho cm/in</th><th>Alto cm/in</th>
            <th>Peso kg/lb</th><th>Volumen m³</th><th>Peso cobrable kg/lb</th><th>Alertas</th></tr>`;
        res.data.resultado.forEach(p=>{
            tabla.innerHTML += `<tr>
                <td>${p.descripcion}</td>
                <td>${p.largo_cm} / ${p.largo_in}</td>
                <td>${p.ancho_cm} / ${p.ancho_in}</td>
                <td>${p.alto_cm} / ${p.alto_in}</td>
                <td>${p.peso_kg} / ${p.peso_lb}</td>
                <td>${p.volumen_m3}</td>
                <td>${p.peso_cobrable_kg} / ${p.peso_cobrable_lb}</td>
                <td>${p.alertas.join("<br>")}</td>
            </tr>`;
        });
    });
}

function generarReporte(){
    const solicitud = {cliente:{nombre:"",contacto:"",tipo_cliente:"",tipo_envio:"",tipo_mercancia:""}, piezas:piezas};
    axios.post("http://127.0.0.1:8000/reporte_final", solicitud)
    .then(res=>{
        let div = document.getElementById("reporte_final");
        div.innerHTML = `<h3>Reporte Final</h3>
        <b>Estado de carga:</b> ${res.data.estado_carga}<br>
        <b>Errores detectados:</b><br>
        ${JSON.stringify(res.data.errores,null,2).replace(/\n/g,"<br>").replace(/ /g,"&nbsp;")}
        <br><b>Instrucciones finales:</b><br>${res.data.instrucciones_finales.join("<br>")}`;
    });
}
