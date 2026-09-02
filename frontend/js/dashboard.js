// ==========================================================
// SISTEMA WEB ANÁLISIS DE VELOCIDADES
// Dashboard v3
// ==========================================================

let dashboard = null;

const UNIDAD_DASHBOARD = (() => {

    const ruta =
        window.location.pathname
        .toLowerCase();

    if (
        ruta === "/dashboard/u9"
        ||
        ruta.endsWith("/dashboard/u9")
    ) {
        return "U9";
    }

    return "U8";

})();

let graficoComparacion = null;
let graficoPeriodos = null;
let graficoTop = null;

let intervaloDashboardAutomatico = null;
let dashboardActualizando = false;

let proximaActualizacionR16 = null;
let intervaloContadorDashboardR16 = null;
let intervaloEstadoDashboardR16 = null;


// ==========================================================
// INICIO
// ==========================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        iniciarDashboard();

        iniciarEstadoAutomaticoR16Dashboard();

        if (!intervaloDashboardAutomatico) {

            intervaloDashboardAutomatico =
                setInterval(
                    iniciarDashboard,
                    30000
                );

        }

    }
);



// ==========================================================
// ESTADO AUTOMATICO R1.6 - DASHBOARD
// ==========================================================

function formatearFechaHoraR16Dashboard(valor) {

    if (!valor) {
        return "--";
    }

    const fecha = new Date(valor);

    if (Number.isNaN(fecha.getTime())) {
        return valor;
    }

    return fecha.toLocaleString(
        "es-CL",
        {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: false
        }
    );
}


function actualizarContadorDashboardR16() {

    const elemento =
        document.getElementById(
            "contadorActualizacionR16"
        );

    const etiqueta =
        document.getElementById(
            "etiquetaContadorActualizacionR16"
        );

    if (!elemento) {
        return;
    }

    if (!proximaActualizacionR16) {

        if (etiqueta) {
            etiqueta.textContent =
                "Faltan";
        }

        elemento.textContent =
            "--:--:--";

        return;
    }

    const ahora =
        Date.now();

    const objetivo =
        proximaActualizacionR16.getTime();

    let diferencia =
        Math.floor(
            (objetivo - ahora) / 1000
        );

    // ==================================================
    // TODAVIA FALTA PARA LA EJECUCION
    // ==================================================

    if (diferencia > 0) {

        if (etiqueta) {
            etiqueta.textContent =
                "Faltan";
        }

        const horas =
            Math.floor(
                diferencia / 3600
            );

        diferencia %= 3600;

        const minutos =
            Math.floor(
                diferencia / 60
            );

        const segundos =
            diferencia % 60;

        elemento.textContent =
            String(horas).padStart(2, "0")
            + ":"
            + String(minutos).padStart(2, "0")
            + ":"
            + String(segundos).padStart(2, "0");

        return;
    }

    // ==================================================
    // LLEGO LA HORA
    // EL BACKEND ESTA DESCARGANDO / PROCESANDO
    // ==================================================

    if (etiqueta) {
        etiqueta.textContent =
            "Actualizando";
    }

    elemento.textContent =
        "ACTUALIZANDO";

}


async function cargarEstadoAutomaticoR16Dashboard() {

    try {

        const response =
            await fetch(
                "/api/configuracion/r16-auto",
                {
                    cache: "no-store"
                }
            );

        if (!response.ok) {
            throw new Error(
                "HTTP " + response.status
            );
        }

        const datos =
            await response.json();

        const ultima =
            document.getElementById(
                "ultimaImportacion"
            );

        const proxima =
            document.getElementById(
                "proximaActualizacionR16"
            );

        if (
            ultima &&
            datos.ultima_ejecucion
        ) {

            ultima.textContent =
                formatearFechaHoraR16Dashboard(
                    datos.ultima_ejecucion
                );

        }

        if (proxima) {

            proxima.textContent =
                formatearFechaHoraR16Dashboard(
                    datos.proxima_ejecucion
                );

        }

        if (datos.proxima_ejecucion) {

            const fecha =
                new Date(
                    datos.proxima_ejecucion
                );

            proximaActualizacionR16 =
                Number.isNaN(
                    fecha.getTime()
                )
                    ? null
                    : fecha;

        }
        else {

            proximaActualizacionR16 =
                null;

        }

        actualizarContadorDashboardR16();

    }
    catch (error) {

        console.error(
            "Error cargando estado automatico R1.6:",
            error
        );

    }

}


function iniciarEstadoAutomaticoR16Dashboard() {

    cargarEstadoAutomaticoR16Dashboard();

    if (!intervaloContadorDashboardR16) {

        intervaloContadorDashboardR16 =
            setInterval(
                actualizarContadorDashboardR16,
                1000
            );

    }

    if (!intervaloEstadoDashboardR16) {

        intervaloEstadoDashboardR16 =
            setInterval(
                cargarEstadoAutomaticoR16Dashboard,
                15000
            );

    }

}


// ==========================================================
// CARGAR DASHBOARD
// ==========================================================

async function iniciarDashboard() {

    if (dashboardActualizando) {
        return;
    }

    dashboardActualizando = true;

    mostrarLoading(true);

    try {

        const response = await fetch(
            "/api/dashboard?unidad="
            + encodeURIComponent(
                UNIDAD_DASHBOARD
            ),
            {
                cache: "no-store"
            }
        );

        if (!response.ok) {

            throw new Error(
                "Error HTTP " + response.status
            );

        }

        dashboard = await response.json();

        if (
            String(
                dashboard?.unidad || ""
            )
            .trim()
            .toUpperCase()
            !== UNIDAD_DASHBOARD
        ) {

            throw new Error(
                "Unidad incorrecta recibida. "
                + "Esperada: "
                + UNIDAD_DASHBOARD
                + " / Recibida: "
                + String(
                    dashboard?.unidad || "--"
                )
            );

        }

        console.log(
            "Dashboard cargado",
            dashboard
        );

        // -------------------------------
        // INFORMACION DEL SISTEMA
        // Se carga primero para que un error posterior
        // no impida mostrar fecha y ultima importacion
        // -------------------------------

        cargarInformacionSistema();


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

        dashboardActualizando = false;

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
            String(fecha);

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

    aplicarBotonR16PorUnidad();

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

function aplicarBotonR16PorUnidad() {

    const unidad =
        String(
            dashboard?.unidad || ""
        )
        .trim()
        .toUpperCase();

    const btnU8 =
        document.getElementById(
            "btn-r16-U8"
        );

    const btnU9 =
        document.getElementById(
            "btn-r16-U9"
        );

    if (btnU8) {

        btnU8.style.display =
            unidad === "U8"
                ? ""
                : "none";

    }

    if (btnU9) {

        btnU9.style.display =
            unidad === "U9"
                ? ""
                : "none";

    }

}


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

        // ==================================================
        // REFRESCAR DASHBOARD DESDE LA BD ACTUALIZADA
        // ==================================================

        console.log(
            "Resultado procesamiento R1.6:",
            datos
        );

        try {
            await iniciarDashboard();
        } catch(errorDashboard) {
            console.error("R1.6 OK - Error solo al refrescar Dashboard:", errorDashboard);
        }


        estado.innerHTML =
        `
        <span style="color:#16a34a">
        ?
        </span>

        <div>

            <strong>
                R1.6 ${unidad} actualizado
            </strong>

            <br>

            <small>
                Base de datos y Dashboard actualizados
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







/* ==========================================================
   INDICADORES OPERACIONALES REALES - VERSION GERENCIA
   ========================================================== */

function actualizarIndicadoresReales() {

    const g = dashboard?.general || {};

    const asignar = (id, valor) => {

        const elemento =
            document.getElementById(id);

        if (elemento) {
            elemento.textContent = valor;
        }

    };

    asignar(
        "auditExpediciones",
        Number(g.expediciones || 0)
            .toLocaleString("es-CL")
    );

    asignar(
        "auditRegistros",
        Number(g.registros || 0)
            .toLocaleString("es-CL")
    );

    asignar(
        "auditBuses",
        Number(g.buses || 0)
            .toLocaleString("es-CL")
    );

    asignar(
        "auditVelocidadReal",
        Number(g.velocidad_real || 0)
            .toFixed(2) + " km/h"
    );

    asignar(
        "auditVelocidadTeorica",
        Number(g.velocidad_teorica || 0)
            .toFixed(2) + " km/h"
    );

    asignar(
        "auditReduccion",
        Number(g.reduccion || 0)
            .toFixed(2) + "%"
    );

}


/* Actualizar cuando el dashboard termine de cargar */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        setTimeout(
            actualizarIndicadoresReales,
            800
        );

    }
);



// ==========================================================
// DASHBOARD -> MATRIZ OPERACIONAL
// NAVEGACION DESDE EVENTOS PRIORITARIOS
// ==========================================================

document.addEventListener(
    "click",
    event => {

        // --------------------------------------------------
        // VER DETALLE
        // --------------------------------------------------

        const botonDetalle =
            event.target.closest(
                ".prioritario-detalle"
            );

        if (botonDetalle) {

            const indice = Number(
                botonDetalle.dataset.prioritarioIndex
            );

            const eventos =
                Array.isArray(
                    dashboard?.prioritarios
                )
                    ? dashboard.prioritarios
                    : [];

            const evento =
                eventos[indice];

            if (!evento) {

                console.error(
                    "No se encontro el evento prioritario.",
                    indice
                );

                return;
            }

            const params =
                new URLSearchParams();

            const unidad =
                evento.unidad ||
                dashboard?.unidad ||
                "";

            const servicio =
                evento.servicio ||
                evento.servicio_usuario ||
                "";

            const fecha =
                evento.fecha_operacional ||
                dashboard?.fecha ||
                "";

            if (unidad) {
                params.set(
                    "unidad",
                    unidad
                );
            }

            if (servicio) {
                params.set(
                    "servicio",
                    servicio
                );
            }

            if (evento.ruta) {
                params.set(
                    "ruta",
                    evento.ruta
                );
            }

            if (evento.sentido) {
                params.set(
                    "sentido",
                    evento.sentido
                );
            }

            if (
                evento.periodo !== null &&
                evento.periodo !== undefined &&
                evento.periodo !== ""
            ) {
                params.set(
                    "periodo",
                    evento.periodo
                );
            }

            if (fecha) {
                params.set(
                    "fecha",
                    fecha
                );
            }

            window.location.href =
                "/matriz?" +
                params.toString();

            return;
        }


        // --------------------------------------------------
        // VER TODOS LOS EVENTOS
        // --------------------------------------------------

        const botonTodos =
            event.target.closest(
                "#btnVerTodosEventos"
            );

        if (botonTodos) {

            const params =
                new URLSearchParams();

            const unidad =
                dashboard?.unidad || "";

            const fecha =
                dashboard?.fecha || "";

            if (
                unidad &&
                unidad !== "--"
            ) {
                params.set(
                    "unidad",
                    unidad
                );
            }

            if (
                fecha &&
                fecha !== "--"
            ) {
                params.set(
                    "fecha",
                    fecha
                );
            }

            window.location.href =
                "/matriz?" +
                params.toString();
        }
    }
);


/* =========================================================
   SWAV - NAVEGACION MATRIZ SEGUN UNIDAD DEL DASHBOARD
   ========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        const enlaceMatriz =
            document.querySelector(
                'a.sidebar-item[href="/matriz"]'
            );

        if (!enlaceMatriz) {
            return;
        }

        const unidad =
            String(
                typeof UNIDAD_DASHBOARD !== "undefined"
                    ? UNIDAD_DASHBOARD
                    : ""
            )
            .trim()
            .toUpperCase();

        if (
            unidad !== "U8"
            &&
            unidad !== "U9"
        ) {
            return;
        }

        enlaceMatriz.href =
            "/matriz?unidad="
            +
            encodeURIComponent(unidad);

        console.info(
            "SWAV Matriz:",
            enlaceMatriz.href
        );
    }
);



// =========================================================
// SWAV_SELECTOR_UNIDAD_DASHBOARD_V1
// SELECTOR DE UNIDAD POR URL
// NO UTILIZA localStorage
// =========================================================

(function instalarSelectorUnidadDashboard() {

    function unidadActualDashboard() {

        const ruta =
            String(
                window.location.pathname || ""
            )
            .trim()
            .toLowerCase();

        if (
            ruta === "/dashboard/u9"
            ||
            ruta.endsWith("/dashboard/u9")
        ) {
            return "U9";
        }

        return "U8";
    }


    function actualizarNavegacionDashboard(
        unidad
    ) {

        const enlaces =
            document.querySelectorAll(
                'a[href="/matriz"], '
                + 'a[href^="/matriz?"]'
            );

        enlaces.forEach(
            enlace => {

                enlace.href =
                    "/matriz?unidad="
                    +
                    encodeURIComponent(
                        unidad
                    );
            }
        );
    }


    function crearSelectorDashboard() {

        if (
            document.getElementById(
                "swavSelectorUnidad"
            )
        ) {
            return;
        }

        const unidad =
            unidadActualDashboard();

        const contenedor =
            document.createElement(
                "div"
            );

        contenedor.id =
            "swavSelectorUnidad";

        contenedor.className =
            "swav-selector-unidad";

        contenedor.innerHTML = `
            <span class="swav-selector-etiqueta">
                Unidad:
            </span>

            <button
                type="button"
                class="swav-selector-boton ${
                    unidad === "U8"
                        ? "activo"
                        : ""
                }"
                data-unidad="U8"
            >
                U8
            </button>

            <button
                type="button"
                class="swav-selector-boton ${
                    unidad === "U9"
                        ? "activo"
                        : ""
                }"
                data-unidad="U9"
            >
                U9
            </button>
        `;

        document.body.appendChild(
            contenedor
        );

        contenedor
            .querySelectorAll(
                "[data-unidad]"
            )
            .forEach(
                boton => {

                    boton.addEventListener(
                        "click",
                        () => {

                            const nuevaUnidad =
                                boton.dataset.unidad;

                            if (
                                nuevaUnidad === unidad
                            ) {
                                return;
                            }

                            window.location.href =
                                nuevaUnidad === "U9"
                                    ? "/dashboard/u9"
                                    : "/dashboard/u8";
                        }
                    );
                }
            );

        actualizarNavegacionDashboard(
            unidad
        );
    }


    function instalarEstiloSelectorDashboard() {

        if (
            document.getElementById(
                "swavSelectorUnidadEstilo"
            )
        ) {
            return;
        }

        const style =
            document.createElement(
                "style"
            );

        style.id =
            "swavSelectorUnidadEstilo";

        style.textContent = `
            .swav-selector-unidad {
                position: fixed;
                top: 14px;
                right: 22px;

                z-index: 9999;

                display: flex;
                align-items: center;
                gap: 7px;

                padding: 7px 9px;

                background: rgba(255,255,255,0.97);

                border: 1px solid #d8e1ec;
                border-radius: 10px;

                box-shadow:
                    0 2px 10px
                    rgba(20, 45, 80, 0.10);

                font-family:
                    Arial,
                    sans-serif;
            }

            .swav-selector-etiqueta {
                margin-right: 3px;

                font-size: 12px;
                font-weight: 800;

                color: #1f3550;
            }

            .swav-selector-boton {
                min-width: 46px;

                padding: 6px 12px;

                border:
                    1px solid
                    #b9c9dc;

                border-radius: 7px;

                background: #ffffff;

                color: #1c4f83;

                font-size: 12px;
                font-weight: 800;

                cursor: pointer;

                transition:
                    all 0.15s ease;
            }

            .swav-selector-boton:hover {
                background: #edf5ff;
            }

            .swav-selector-boton.activo {
                background: #1769d2;
                border-color: #1769d2;

                color: #ffffff;

                box-shadow:
                    0 1px 4px
                    rgba(23,105,210,0.30);
            }
        `;

        document.head.appendChild(
            style
        );
    }


    function iniciarSelectorDashboard() {

        instalarEstiloSelectorDashboard();

        crearSelectorDashboard();
    }


    if (
        document.readyState ===
        "loading"
    ) {

        document.addEventListener(
            "DOMContentLoaded",
            iniciarSelectorDashboard
        );

    }
    else {

        iniciarSelectorDashboard();
    }

})();

