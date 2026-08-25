// ==========================================================
// SISTEMA WEB ANÁLISIS DE VELOCIDADES
// Dashboard v3
// ==========================================================

let dashboard = null;

let graficoComparacion = null;
let graficoPeriodos = null;
let graficoTop = null;


// ==========================================================
// INICIO
// ==========================================================

document.addEventListener(
    "DOMContentLoaded",
    iniciarDashboard
);


// ==========================================================
// CARGAR DASHBOARD
// ==========================================================

async function iniciarDashboard() {

    mostrarLoading(true);

    try {

        const response = await fetch(
            "/api/dashboard"
        );

        if (!response.ok) {

            throw new Error(
                "Error HTTP " + response.status
            );

        }

        dashboard = await response.json();

        console.log(
            "Dashboard cargado",
            dashboard
        );


        // -------------------------------
        // KPIs
        // -------------------------------

        cargarKPIs();

        // -------------------------------
        // INDICADORES IP / IE
        // -------------------------------

        cargarIndicadoresIPIE();


        // -------------------------------
        // INDICADORES IP / IE
        // -------------------------------



        // -------------------------------
        // EVENTOS
        // -------------------------------

        cargarEventosPrioritarios();


        // -------------------------------
        // GRÁFICOS
        // -------------------------------

        crearGraficoComparacion();

        crearGraficoTop();

        crearGraficoPeriodos();


        // -------------------------------
        // MATRIZ
        // -------------------------------

        crearMatrizOperacional();


        // -------------------------------
        // TABLA / DETALLE
        // -------------------------------

        crearTabla();


        // -------------------------------
        // INFORMACIÓN
        // -------------------------------

        cargarInformacionSistema();

    }

    catch (error) {

        console.error(
            "Error cargando Dashboard:",
            error
        );

    }

    finally {

        mostrarLoading(false);

    }

}


// ==========================================================
// LOADING
// ==========================================================

function mostrarLoading(mostrar) {

    const loading =
        document.getElementById("loading");

    if (!loading) {
        return;
    }

    loading.style.display =
        mostrar ? "flex" : "none";

}


// ==========================================================
// UTILIDADES
// ==========================================================

function numero(valor) {

    const n = Number(valor);

    return Number.isFinite(n)
        ? n
        : 0;

}


function texto(valor) {

    if (
        valor === null ||
        valor === undefined
    ) {

        return "--";

    }

    return String(valor);

}


function porcentaje(valor) {

    return numero(valor)
        .toFixed(2) + " %";

}


// ==========================================================
// KPI
// ==========================================================


// ==========================================================
// INDICADORES IP / IE
// ==========================================================

function cargarIndicadoresIPIE() {

    if (!dashboard) {
        return;
    }

    const ip = dashboard.ip || {};
    const ie = dashboard.ie || {};


    // ======================================================
    // IP
    // ======================================================

    const ipExpediciones =
        document.getElementById("ipExpediciones");

    if (ipExpediciones) {
        ipExpediciones.textContent =
            numero(ip.expediciones)
                .toLocaleString("es-CL");
    }


    const ipOK =
        document.getElementById("ipOK");

    if (ipOK) {
        ipOK.textContent =
            numero(ip.ok)
                .toLocaleString("es-CL");
    }


    const ipSimple =
        document.getElementById("ipSimple");

    if (ipSimple) {
        ipSimple.textContent =
            numero(ip.simples)
                .toLocaleString("es-CL");
    }


    const ipComplejo =
        document.getElementById("ipComplejo");

    if (ipComplejo) {
        ipComplejo.textContent =
            numero(ip.complejos)
                .toLocaleString("es-CL");
    }


    const ipEventos =
        document.getElementById("ipEventos");

    if (ipEventos) {
        ipEventos.textContent =
            numero(ip.eventos)
                .toLocaleString("es-CL");
    }


    // ======================================================
    // IE
    // ======================================================

    const ieExpediciones =
        document.getElementById("ieExpediciones");

    if (ieExpediciones) {
        ieExpediciones.textContent =
            numero(ie.expediciones)
                .toLocaleString("es-CL");
    }


    const ieOK =
        document.getElementById("ieOK");

    if (ieOK) {
        ieOK.textContent =
            numero(ie.ok)
                .toLocaleString("es-CL");
    }


    const ieSimple =
        document.getElementById("ieSimple");

    if (ieSimple) {
        ieSimple.textContent =
            numero(ie.simples)
                .toLocaleString("es-CL");
    }


    const ieComplejo =
        document.getElementById("ieComplejo");

    if (ieComplejo) {
        ieComplejo.textContent =
            numero(ie.complejos)
                .toLocaleString("es-CL");
    }


    const ieEventos =
        document.getElementById("ieEventos");

    if (ieEventos) {
        ieEventos.textContent =
            numero(ie.eventos)
                .toLocaleString("es-CL");
    }

}


function cargarKPIs() {

    if (!dashboard) {
        return;
    }

    const g =
        dashboard.general || {};

    const c =
        dashboard.clasificacion || {};


    // ------------------------------------------
    // Total de expediciones
    // ------------------------------------------

    const expediciones =
        document.getElementById(
            "totalExpediciones"
        );

    if (expediciones) {

        expediciones.textContent =
            numero(g.expediciones)
                .toLocaleString("es-CL");

    }


    // ------------------------------------------
    // Eventos simples
    // ------------------------------------------

    const simples =
        numero(c.simple);


    // ------------------------------------------
    // Eventos complejos
    // ------------------------------------------

    const complejos =
        numero(c.complejo);


    // ------------------------------------------
    // Total de eventos
    // Siempre = Simples + Complejos
    // ------------------------------------------

    const totalEventos =
        document.getElementById(
            "totalEventos"
        );

    if (totalEventos) {

        totalEventos.textContent =
            (
                simples +
                complejos
            ).toLocaleString("es-CL");

    }


    // ------------------------------------------
    // Eventos simples
    // ------------------------------------------

    const simple =
        document.getElementById(
            "totalSimple"
        );

    if (simple) {

        simple.textContent =
            simples.toLocaleString("es-CL");

    }


    // ------------------------------------------
    // Eventos complejos
    // ------------------------------------------

    const complejo =
        document.getElementById(
            "totalComplejo"
        );

    if (complejo) {

        complejo.textContent =
            complejos.toLocaleString("es-CL");

    }

}


// ==========================================================
// EVENTOS PRIORITARIOS
// ==========================================================

function cargarEventosPrioritarios() {

    console.log("Cargando eventos prioritarios combinados...");

    const eventos = Array.isArray(dashboard?.prioritarios)
        ? dashboard.prioritarios
        : [];

    console.log("Prioritarios recibidos:", eventos);
    console.log("Cantidad prioritarios:", eventos.length);


    // ======================================================
    // RESUMEN
    // ======================================================

    const complejos = eventos.filter(
        e => String(e.clasificacion || "").toUpperCase() === "COMPLEJO"
    ).length;

    const simples = eventos.filter(
        e => String(e.clasificacion || "").toUpperCase() === "SIMPLE"
    ).length;

    const ip = eventos.filter(
        e => String(e.indicador || "").toUpperCase() === "IP"
    ).length;

    const ie = eventos.filter(
        e => String(e.indicador || "").toUpperCase() === "IE"
    ).length;


    const total = eventos.length;


    // ======================================================
    // ACTUALIZAR TARJETAS DE RESUMEN
    // ======================================================

    const elementoComplejos =
        document.getElementById("prioritariosComplejos");

    const elementoSimples =
        document.getElementById("prioritariosSimples");

    const elementoIP =
        document.getElementById("prioritariosIP");

    const elementoIE =
        document.getElementById("prioritariosIE");

    const elementoTotal =
        document.getElementById("prioritariosTotal");


    if (elementoComplejos) {
        elementoComplejos.textContent = complejos;
    }

    if (elementoSimples) {
        elementoSimples.textContent = simples;
    }

    if (elementoIP) {
        elementoIP.textContent = ip;
    }

    if (elementoIE) {
        elementoIE.textContent = ie;
    }

    if (elementoTotal) {
        elementoTotal.textContent = total;
    }


    // ======================================================
    // TABLA
    // ======================================================

    const tabla =
        document.getElementById("tablaEventosPrioritarios");

    if (!tabla) {
        console.warn(
            "No se encontró #tablaEventosPrioritarios"
        );
        return;
    }


    if (eventos.length === 0) {

        tabla.innerHTML = `
            <tr>
                <td colspan="9" class="prioritarios-empty">
                    No existen eventos prioritarios.
                </td>
            </tr>
        `;

        return;
    }


    tabla.innerHTML = eventos.map((evento, indice) => {

        const prioridad = indice + 1;

        const indicador =
            String(evento.indicador || "--").toUpperCase();

        const clasificacion =
            String(evento.clasificacion || "--").toUpperCase();

        const servicio =
            evento.servicio ?? "--";

        const ruta =
            evento.ruta ?? "--";

        const periodo =
            evento.periodo ?? "--";

        const reduccionNumero =
            Number(evento.reduccion ?? 0);

        const reduccion =
            `${reduccionNumero.toFixed(2)} %`;


        // La API actual no define todavía una categoría
        // ALTO/MEDIO independiente.
        // Por ahora mostramos la clasificación real.
        const claseClasificacion =
            clasificacion === "COMPLEJO"
                ? "prioritario-complejo"
                : "prioritario-simple";


        // Fecha/hora: usar la fecha operacional real.
        const fechaHora =
            evento.fecha_operacional
                ? String(evento.fecha_operacional)
                    .split("-")
                    .reverse()
                    .join("/")
                : (
                    evento.fecha_hora ??
                    evento.fechaHora ??
                    evento.fecha ??
                    evento.hora ??
                    "--"
                );


        const claseIndicador =
            indicador === "IE"
                ? "prioritario-indicador-ie"
                : "prioritario-indicador-ip";


        const clasePrioridad =
            clasificacion === "COMPLEJO"
                ? "prioridad-complejo"
                : "prioridad-simple";


        return `
            <tr>

                <td>
                    <span class="prioridad-badge ${clasePrioridad}">
                        ${prioridad}
                    </span>
                </td>


                <td>
                    <span class="prioritario-tipo ${claseClasificacion}">
                        ${clasificacion}
                    </span>
                </td>


                <td>
                    <span class="indicador-badge ${claseIndicador}">
                        ${indicador}
                    </span>
                </td>


                <td>
                    <strong>${servicio}</strong>
                </td>


                <td>
                    ${ruta}
                </td>


                <td>
                    ${periodo}
                </td>


                <td>
                    <strong class="prioritario-reduccion">
                        ${reduccion}
                    </strong>
                </td>


                <td>
                    ${fechaHora}
                </td>


                <td>
                    <button
                        type="button"
                        class="prioritario-detalle"
                        data-prioritario-index="${indice}">
                        <i class="fa-solid fa-eye"></i>
                        Ver detalle
                    </button>
                </td>

            </tr>
        `;

    }).join("");


    console.log(
        "Tabla de prioritarios actualizada correctamente."
    );

}

function crearGraficoComparacion() {

    const canvas =
        document.getElementById(
            "graficoDistribucionEventos"
        );

    if (!canvas) {
        return;
    }


    const ip =
        dashboard?.ip || {};

    const ie =
        dashboard?.ie || {};


    const etiquetas = [
        "IP Simples",
        "IP Complejos",
        "IE Simples",
        "IE Complejos"
    ];


    const valores = [
        Number(ip.simples || 0),
        Number(ip.complejos || 0),
        Number(ie.simples || 0),
        Number(ie.complejos || 0)
    ];


    if (graficoComparacion) {

        graficoComparacion.destroy();

    }


    graficoComparacion =
        new Chart(
            canvas,
            {

                type: "doughnut",

                data: {

                    labels: etiquetas,

                    datasets: [
                        {

                            data: valores,

                            borderWidth: 2

                        }
                    ]

                },

                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    plugins: {

                        legend: {

                            position: "right"

                        },

                        tooltip: {

                            callbacks: {

                                label:
                                    function(context) {

                                        const valor =
                                            context.raw || 0;

                                        const total =
                                            valores.reduce(
                                                (
                                                    suma,
                                                    actual
                                                ) =>
                                                    suma +
                                                    actual,
                                                0
                                            );

                                        const porcentaje =
                                            total > 0
                                                ? (
                                                    valor /
                                                    total *
                                                    100
                                                ).toFixed(1)
                                                : "0.0";

                                        return (
                                            context.label +
                                            ": " +
                                            valor +
                                            " (" +
                                            porcentaje +
                                            "%)"
                                        );

                                    }

                            }

                        }

                    }

                }

            }
        );

}
function crearGraficoTop() {

    const canvas =
        document.getElementById(
            "graficoTopServicios"
        );

    if (!canvas) {
        return;
    }


    const datos =
        Array.isArray(dashboard?.top_servicios)
            ? dashboard.top_servicios
            : [];


    if (!datos.length) {
        return;
    }


    const datosOrdenados =
        [...datos]
            .sort(
                (a, b) =>
                    Number(b.eventos || 0) -
                    Number(a.eventos || 0)
            )
            .slice(0, 10);


    const etiquetas =
        datosOrdenados.map(
            x => texto(x.servicio)
        );


    const valores =
        datosOrdenados.map(
            x => Number(x.eventos || 0)
        );


    if (graficoTop) {
        graficoTop.destroy();
    }


    graficoTop =
        new Chart(
            canvas,
            {

                type: "bar",

                data: {

                    labels: etiquetas,

                    datasets: [
                        {

                            label:
                                "Eventos",

                            data: valores,

                            borderRadius: 6

                        }
                    ]

                },

                options: {

                    indexAxis: "y",

                    responsive: true,

                    maintainAspectRatio: false,

                    plugins: {

                        legend: {

                            display: false

                        }

                    },

                    scales: {

                        x: {

                            beginAtZero: true,

                            ticks: {

                                precision: 0

                            }

                        }

                    }

                }

            }
        );

}
function crearGraficoPeriodos() {

    const canvas =
        document.getElementById(
            "graficoPeriodos"
        );

    if (!canvas) {
        return;
    }


    const datos =
        Array.isArray(dashboard?.periodos)
            ? dashboard.periodos
            : [];


    if (!datos.length) {
        return;
    }


    const datosOrdenados =
        [...datos]
            .sort(
                (a, b) =>
                    Number(a.periodo || 0) -
                    Number(b.periodo || 0)
            );


    const etiquetas =
        datosOrdenados.map(
            x => "P" + x.periodo
        );


    const valores =
        datosOrdenados.map(
            x => Number(x.eventos || 0)
        );


    if (graficoPeriodos) {

        graficoPeriodos.destroy();

    }


    graficoPeriodos =
        new Chart(
            canvas,
            {

                type: "bar",

                data: {

                    labels: etiquetas,

                    datasets: [
                        {

                            label:
                                "Eventos",

                            data: valores,

                            borderRadius: 6

                        }
                    ]

                },

                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    plugins: {

                        legend: {

                            display: false

                        }

                    },

                    scales: {

                        y: {

                            beginAtZero: true,

                            ticks: {

                                precision: 0

                            }

                        }

                    }

                }

            }
        );

}
function crearTabla() {

    const tbody =
        document.querySelector(
            "#tablaRegistro tbody"
        );

    if (!tbody) {
        return;
    }


    tbody.innerHTML = "";


    const registros =
        dashboard?.registros || [];


    registros.forEach(
        reg => {

            const clase =
                claseClasificacion(
                    reg.clasificacion
                );


            tbody.innerHTML += `

                <tr class="${clase}">

                    <td>
                        ${texto(
                            reg.servicio
                        )}
                    </td>

                    <td>
                        ${texto(
                            reg.ruta
                        )}
                    </td>

                    <td>
                        ${texto(
                            reg.sentido
                        )}
                    </td>

                    <td>
                        ${texto(
                            reg.periodo
                        )}
                    </td>

                    <td>
                        ${numero(
                            reg.expediciones
                        )}
                    </td>

                    <td>
                        ${numero(
                            reg.buses
                        )}
                    </td>

                    <td>
                        ${numero(
                            reg.velocidad_real
                        ).toFixed(2)}
                    </td>

                    <td>
                        ${numero(
                            reg.velocidad_teorica
                        ).toFixed(2)}
                    </td>

                    <td>
                        ${porcentaje(
                            reg.reduccion
                        )}
                    </td>

                    <td>
                        ${texto(
                            reg.estado
                        )}
                    </td>

                </tr>

            `;

        }
    );

}


// ==========================================================
// INFORMACIÓN DEL SISTEMA
// ==========================================================

function cargarInformacionSistema() {

    const unidad =
        dashboard?.unidad;

    const fecha =
        dashboard?.fecha;

    const ultima =
        dashboard?.ultima_importacion;


    document
        .querySelectorAll(
            "#unidadActual"
        )
        .forEach(
            elemento => {

                if (unidad) {

                    elemento.textContent =
                        unidad;

                }

            }
        );


    const fechaActual =
        document.getElementById(
            "fechaActual"
        );

    if (
        fechaActual &&
        fecha
    ) {

        fechaActual.textContent =
            formatearFecha(fecha);

    }


    const ultimaImportacion =
        document.getElementById(
            "ultimaImportacion"
        );

    if (
        ultimaImportacion &&
        ultima
    ) {

        ultimaImportacion.textContent =
            ultima;

    }

}


// ==========================================================
// FORMATEAR FECHA
// ==========================================================

function formatearFecha(
    fecha
) {

    try {

        return new Date(
            fecha
        ).toLocaleString(
            "es-CL"
        );

    }

    catch {

        return texto(fecha);

    }

}










// ==========================================================
// DESCARGA AUTOMATICA R1.6
// CONTROL VISUAL SIN ROMPER DISEÑO
// ==========================================================

async function descargarR16(unidad)
{

    const btnU8 =
        document.getElementById("btn-r16-U8");


    const btnU9 =
        document.getElementById("btn-r16-U9");


    const estado =
        document.getElementById("estado-r16");


    const botonActivo =
        unidad === "U8"
            ? btnU8
            : btnU9;


    const botonOtro =
        unidad === "U8"
            ? btnU9
            : btnU8;



    botonActivo.disabled = true;
    botonOtro.disabled = true;



    botonActivo.classList.add(
        "procesando"
    );


    const icono =
        botonActivo.querySelector(
            ".r16-icon i"
        );


    const small =
        botonActivo.querySelector(
            ".r16-text small"
        );



    if(icono)
    {
        icono.className =
        "fa-solid fa-spinner fa-spin";
    }


    if(small)
    {
        small.innerHTML =
        "PROCESANDO";
    }



    estado.innerHTML =
    `
    <span>●</span>
    Procesando R1.6 ${unidad}
    `;



    try
    {

        const respuesta =
            await fetch(
                "/api/sinoptico/r16download/" + unidad,
                {
                    method:"POST"
                }
            );


        const datos =
            await respuesta.json();



        if(!respuesta.ok)
        {
            throw new Error(
                datos.detail ||
                "Error R1.6"
            );
        }



        estado.innerHTML =
        `
        <span style="color:#16a34a">
        ●
        </span>

        <div>

        <strong>
        R1.6 ${unidad} actualizado
        </strong>

        <br>

        <small>
        Archivo generado correctamente
        </small>

        </div>
        `;


    }
    catch(error)
    {

        estado.innerHTML =
        `
        <span>●</span>
        Error R1.6 ${unidad}
        `;

    }
    finally
    {

        botonActivo.disabled = false;
        botonOtro.disabled = false;


        botonActivo.classList.remove(
            "procesando"
        );


        if(icono)
        {
            icono.className =
            "fa-solid fa-cloud-arrow-down";
        }


        if(small)
        {
            small.innerHTML =
            "ACTUALIZAR";
        }

    }

}






