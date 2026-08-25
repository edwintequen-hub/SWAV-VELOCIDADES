// ======================================================
// SWAV - MATRIZ OPERACIONAL V2
// ======================================================

let datosOriginales = [];
let datosFiltrados = [];

// ======================================================
// INICIO
// ======================================================

document.addEventListener("DOMContentLoaded", async () => {

    await cargarDatos();

});

// ======================================================
// CARGAR DATOS
// ======================================================

async function cargarDatos(){

    try{

        const response = await fetch("/api/matriz");

        datosOriginales = await response.json();

        datosFiltrados = [...datosOriginales];

        console.log("Datos cargados:", datosOriginales.length);

    }catch(error){

        console.error(error);

        alert("No fue posible cargar la matriz.");

    }

}

// ======================================================
// CARGAR COMBOS
// ======================================================

function cargarCombos(){

    llenarCombo(
        "cmbUnidad",
        [...new Set(datosOriginales.map(x => x.unidad))]
    );

    llenarCombo(
        "cmbTipoDia",
        [...new Set(datosOriginales.map(x => x.tipo_dia))]
    );

    llenarCombo(
        "cmbServicioUsuario",
        [...new Set(datosOriginales.map(x => x.servicio_usuario))]
    );

    llenarCombo(
        "cmbServicioEmpresa",
        [...new Set(datosOriginales.map(x => x.servicio_empresa))]
    );

}

// ======================================================

function llenarCombo(id, datos){

    const combo = document.getElementById(id);

    combo.innerHTML = "<option value=''>Todos</option>";

    datos
        .sort()
        .forEach(valor => {

            combo.innerHTML += `
                <option value="${valor}">
                    ${valor}
                </option>
            `;

        });

}

// ======================================================
// EVENTOS
// ======================================================

document.addEventListener("change", (e) => {

    if (

        e.target.id === "cmbUnidad" ||
        e.target.id === "cmbTipoDia" ||
        e.target.id === "cmbServicioUsuario" ||
        e.target.id === "cmbServicioEmpresa" ||
        e.target.id === "cmbEstado"

    ) {

        aplicarFiltros();

    }

});

// ======================================================
// FILTROS
// ======================================================

function aplicarFiltros() {

    const unidad = document.getElementById("cmbUnidad").value;

    const tipoDia = document.getElementById("cmbTipoDia").value;

    const usuario = document.getElementById("cmbServicioUsuario").value;

    const empresa = document.getElementById("cmbServicioEmpresa").value;

    datosFiltrados = datosOriginales.filter(f => {

        if (unidad && f.unidad !== unidad)
            return false;

        if (tipoDia && f.tipo_dia !== tipoDia)
            return false;

        if (usuario && f.servicio_usuario !== usuario)
            return false;

        if (empresa && f.servicio_empresa !== empresa)
            return false;

        return true;

    });

    console.log("Filas:", datosFiltrados.length);

}