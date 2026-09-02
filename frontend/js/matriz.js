// ======================================================
// SWAV
// MATRIZ OPERACIONAL V3
// ======================================================

let datosOriginales = [];

let datosFiltrados = [];


// ======================================================
// INICIO
// ======================================================

document.addEventListener(
    "DOMContentLoaded",
    async () => {

        configurarEstado();

        configurarComboChecks();

        await cargarMatriz();

    }
);


// ======================================================
// CONTEXTO RECIBIDO DESDE DASHBOARD
// ======================================================

function aplicarContextoDesdeDashboard() {

    const params =
        new URLSearchParams(
            window.location.search
        );

    const normalizar = valor =>
        String(valor ?? "")
        .trim()
        .toUpperCase();

    const unidad =
        normalizar(
            params.get("unidad")
        );

    const servicioRecibido =
        normalizar(
            params.get("servicio")
        );

    const ruta =
        normalizar(
            params.get("ruta")
        );

    const sentido =
        normalizar(
            params.get("sentido")
        );

    const periodoValor =
        params.get("periodo");

    const periodo =
        periodoValor !== null
            ? Number(periodoValor)
            : null;

    const fecha =
        String(
            params.get("fecha") || ""
        )
        .trim();

    // ==================================================
    // UNIDAD
    // ==================================================

    if (unidad) {

        const comboUnidad =
            document.getElementById(
                "cmbUnidad"
            );

        if (comboUnidad) {

            const opcion =
                [...comboUnidad.options]
                .find(
                    item =>
                        normalizar(
                            item.value
                        ) === unidad
                );

            if (opcion) {
                comboUnidad.value =
                    opcion.value;
            }
        }
    }

    // ==================================================
    // RESOLVER SERVICIO USUARIO REAL DE LA MATRIZ
    //
    // El Dashboard puede traer el servicio operacional
    // de HistoricoRegistro.
    //
    // La Matriz filtra por fila.servicio_usuario.
    //
    // Usamos la RUTA para encontrar la fila correcta
    // y obtener el servicio_usuario oficial.
    // ==================================================

    let servicioUsuario =
        servicioRecibido;

    if (ruta) {

        const filaPorRuta =
            datosOriginales.find(
                fila =>
                    normalizar(
                        fila.servicio_empresa
                    ) === ruta
            );

        if (
            filaPorRuta &&
            filaPorRuta.servicio_usuario
        ) {
            servicioUsuario =
                normalizar(
                    filaPorRuta.servicio_usuario
                );
        }
    }

    console.log(
        "Contexto Dashboard -> Matriz",
        {
            unidad,
            servicioRecibido,
            servicioUsuario,
            ruta,
            sentido,
            periodo,
            fecha
        }
    );

    // ==================================================
    // FILTRAR SERVICIO USUARIO
    // ==================================================

    if (servicioUsuario) {

        const todos =
            document.getElementById(
                "servicioUsuarioTodos"
            );

        const checks = [
            ...document.querySelectorAll(
                ".servicio-usuario-checkbox"
            )
        ];

        let encontrados = 0;

        checks.forEach(
            check => {

                const coincide =
                    normalizar(
                        check.value
                    ) === servicioUsuario;

                check.checked =
                    coincide;

                if (coincide) {
                    encontrados++;
                }
            }
        );

        if (todos) {

            todos.checked =
                encontrados ===
                checks.length &&
                checks.length > 0;
        }

        if (encontrados === 0) {

            console.warn(
                "No se encontro servicio_usuario:",
                servicioUsuario,
                "Ruta:",
                ruta
            );

        } else {

            console.log(
                "Servicio Matriz filtrado:",
                servicioUsuario
            );
        }

        actualizarTextoServicioUsuario();
    }

    return {
        unidad,
        servicio:
            servicioUsuario,
        servicioRecibido,
        ruta,
        sentido,
        periodo:
            Number.isFinite(periodo)
            && periodo >= 1
            && periodo <= 24
                ? periodo
                : null,
        fecha
    };
}



function obtenerUnidadDashboardMatriz() {

    const combo =
        document.getElementById(
            "cmbUnidad"
        );

    if (combo && combo.options.length > 0) {

        const unidadCombo =
            String(
                combo.value || ""
            )
            .trim()
            .toUpperCase();

        if (
            unidadCombo === "U8"
            ||
            unidadCombo === "U9"
        ) {
            return unidadCombo;
        }

        // Si el usuario selecciono Todas,
        // no debemos volver a tomar la unidad
        // antigua desde la URL.
        return null;
    }

    // Respaldo solamente durante carga inicial.
    const params =
        new URLSearchParams(
            window.location.search
        );

    const unidadUrl =
        String(
            params.get("unidad") || ""
        )
        .trim()
        .toUpperCase();

    if (
        unidadUrl === "U8"
        ||
        unidadUrl === "U9"
    ) {
        return unidadUrl;
    }

    return null;
}


// ======================================================
// ULTIMA UNIDAD R1.6 PROCESADA
// ======================================================

function convertirFechaDashboardAValor(
    valor
) {

    const texto =
        String(
            valor || ""
        ).trim();

    const match =
        texto.match(
            /^(\d{2})\/(\d{2})\/(\d{4})\s+(\d{2}):(\d{2})/
        );

    if (!match) {
        return 0;
    }

    const dia =
        Number(match[1]);

    const mes =
        Number(match[2]) - 1;

    const anio =
        Number(match[3]);

    const hora =
        Number(match[4]);

    const minuto =
        Number(match[5]);

    return new Date(
        anio,
        mes,
        dia,
        hora,
        minuto,
        0
    ).getTime();
}


async function obtenerUltimaUnidadProcesada() {

    const unidades = [
        "U8",
        "U9"
    ];

    const resultados =
        await Promise.all(
            unidades.map(
                async unidad => {

                    try {

                        const response =
                            await fetch(
                                "/api/dashboard?unidad="
                                + encodeURIComponent(
                                    unidad
                                ),
                                {
                                    cache: "no-store"
                                }
                            );

                        if (!response.ok) {

                            return null;
                        }

                        const dashboard =
                            await response.json();

                        return {
                            unidad:
                                String(
                                    dashboard.unidad
                                    || unidad
                                )
                                .trim()
                                .toUpperCase(),

                            ultimaImportacion:
                                dashboard.ultima_importacion
                                || "",

                            valorFecha:
                                convertirFechaDashboardAValor(
                                    dashboard.ultima_importacion
                                )
                        };

                    }
                    catch (error) {

                        console.warn(
                            "No fue posible consultar "
                            + "ultima importacion "
                            + unidad,
                            error
                        );

                        return null;
                    }
                }
            )
        );

    const validos =
        resultados
            .filter(Boolean)
            .filter(
                item =>
                    item.unidad === "U8"
                    ||
                    item.unidad === "U9"
            )
            .sort(
                (a, b) =>
                    b.valorFecha
                    -
                    a.valorFecha
            );

    if (
        validos.length === 0
    ) {

        return null;
    }

    return validos[0].unidad;
}


// ======================================================
// CARGAR MATRIZ
// ======================================================

async function cargarMatriz() {

    try {

        // ==================================================
        // CONSERVAR UNIDAD SELECCIONADA
        // ==================================================

        const unidadSeleccionadaAntes =
            obtenerUnidadDashboardMatriz();

        // ==================================================
        // UNIDAD OBJETIVO
        //
        // 1. Si usuario eligio U8/U9, respetarla.
        // 2. Si esta en Todas al iniciar, usar la ultima
        //    unidad R1.6 realmente procesada.
        // ==================================================

        // ==================================================
        // UNIDAD DESDE URL
        // Permite tener U8 y U9 abiertas simultaneamente
        // en ventanas independientes.
        // ==================================================

        const paramsUnidadInicial =
            new URLSearchParams(
                window.location.search
            );

        const unidadDesdeUrl =
            String(
                paramsUnidadInicial.get("unidad")
                || ""
            )
            .trim()
            .toUpperCase();

        const unidadUrlValida =
            (
                unidadDesdeUrl === "U8"
                ||
                unidadDesdeUrl === "U9"
            )
                ? unidadDesdeUrl
                : null;


        const unidadObjetivo =
            unidadSeleccionadaAntes
            ||
            unidadUrlValida
            ||
            await obtenerUltimaUnidadProcesada();


        const response =
            await fetch(
                (
                    unidadObjetivo
                        ? "/api/matriz?unidad="
                            + encodeURIComponent(
                                unidadObjetivo
                            )
                        : "/api/matriz"
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

        const datosRecibidos =
            await response.json();

        // ==================================================
        // SEGURIDAD FINAL DE UNIDAD
        // La matriz nunca puede mezclar U8 y U9.
        // ==================================================

        datosOriginales =
            unidadObjetivo
                ? datosRecibidos.filter(
                    fila =>
                        String(
                            fila.unidad || ""
                        )
                        .trim()
                        .toUpperCase()
                        ===
                        String(
                            unidadObjetivo
                        )
                        .trim()
                        .toUpperCase()
                )
                : datosRecibidos;

        cargarCombos();

        // ==================================================
        // RESTAURAR UNIDAD SELECCIONADA
        // cargarCombos() reconstruye cmbUnidad.
        // ==================================================

        const comboUnidadRecargado =
            document.getElementById(
                "cmbUnidad"
            );

        if (
            comboUnidadRecargado
            &&
            unidadObjetivo
        ) {

            const existeUnidadSeleccionada = [
                ...comboUnidadRecargado.options
            ].some(
                opcion =>
                    String(
                        opcion.value || ""
                    )
                    .trim()
                    .toUpperCase()
                    === unidadObjetivo
            );

            if (existeUnidadSeleccionada) {

                comboUnidadRecargado.value =
                    unidadObjetivo;

            }
        }

        // ==================================================
        // UNIDAD ACTIVA = ULTIMA UNIDAD R1.6 PROCESADA
        // ==================================================
        //
        // Dashboard y Matriz deben abrir mostrando
        // la misma unidad operacional.
        //
        // El usuario puede cambiar manualmente a
        // U8, U9 o Todas posteriormente.
        // ==================================================

        try {

            const unidadDashboard =
                obtenerUnidadDashboardMatriz();

            if (!unidadDashboard) {
                throw new Error(
                    "SIN_UNIDAD_DASHBOARD"
                );
            }

            const responseDashboard =
                await fetch(
                    "/api/dashboard?unidad="
                    + encodeURIComponent(
                        unidadDashboard
                    ),
                    {
                        cache: "no-store"
                    }
                );

            if (responseDashboard.ok) {

                const dashboard =
                    await responseDashboard.json();

                // ==============================================
                // CONTEXTO OPERACIONAL DE LA MATRIZ
                // MISMA FUENTE QUE EL DASHBOARD
                // ==============================================

                const ponerTexto = (
                    id,
                    valor
                ) => {

                    const elemento =
                        document.getElementById(id);

                    if (elemento) {
                        elemento.textContent =
                            valor ?? "-";
                    }

                };

                ponerTexto(
                    "matrizTotalExpediciones",
                    dashboard.general?.expediciones ?? 0
                );

                ponerTexto(
                    "matrizUnidadActiva",
                    dashboard.unidad || "-"
                );

                ponerTexto(
                    "matrizFechaOperacional",
                    dashboard.fecha || "-"
                );

                ponerTexto(
                    "matrizUltimaActualizacion",
                    dashboard.ultima_importacion || "-"
                );

                const estadoOperacional =
                    document.getElementById(
                        "matrizEstadoOperacional"
                    );

                if (estadoOperacional) {
                    estadoOperacional.textContent =
                        "Operativo";
                }

                const unidadActiva =
                    String(
                        dashboard.unidad || ""
                    )
                    .trim()
                    .toUpperCase();

                const comboUnidad =
                    document.getElementById(
                        "cmbUnidad"
                    );

                if (
                    comboUnidad &&
                    unidadActiva &&
                    unidadActiva !== "--"
                ) {

                    const existeUnidad = [
                        ...comboUnidad.options
                    ].some(
                        opcion =>
                            String(
                                opcion.value || ""
                            )
                            .trim()
                            .toUpperCase()
                            === unidadActiva
                    );

                    if (existeUnidad) {

                        comboUnidad.value =
                            unidadActiva;

                    }

                }

            }

        }
        catch (errorUnidad) {

            console.warn(
                "No fue posible determinar "
                + "la ultima unidad procesada.",
                errorUnidad
            );

        }

        const contextoDashboard =
            aplicarContextoDesdeDashboard();

        aplicarFiltros();

        // ==================================================
        // SI VIENE DESDE "VER DETALLE"
        // ABRIR AUTOMATICAMENTE EL PERIODO DEL EVENTO
        // ==================================================

        if (
            contextoDashboard.periodo !== null
        ) {

            setTimeout(
                () => {

                    const celdas = [
                        ...document.querySelectorAll(
                            `.celda-matriz[data-periodo="${contextoDashboard.periodo}"]`
                        )
                    ];

                    let celdaObjetivo = null;

                    // --------------------------------------
                    // BUSCAR CELDA DEL SERVICIO FILTRADO
                    // --------------------------------------

                    for (const celda of celdas) {

                        const fila =
                            celda.closest("tr");

                        if (!fila) {
                            continue;
                        }

                        const rutaCelda =
                            String(
                                celda.dataset.servicio || ""
                            )
                            .trim()
                            .toUpperCase();

                        // ----------------------------------
                        // PRIORIDAD 1:
                        // RUTA EXACTA DEL EVENTO
                        // ----------------------------------

                        if (
                            contextoDashboard.ruta &&
                            rutaCelda !==
                                contextoDashboard.ruta
                        ) {
                            continue;
                        }

                        const textoFila =
                            String(
                                fila.textContent || ""
                            )
                            .trim()
                            .toUpperCase();

                        // ----------------------------------
                        // PRIORIDAD 2:
                        // SERVICIO USUARIO RESUELTO
                        // ----------------------------------

                        if (
                            contextoDashboard.servicio &&
                            !textoFila.includes(
                                contextoDashboard.servicio
                            )
                        ) {
                            continue;
                        }

                        celdaObjetivo = celda;
                        break;
                    }

                    // Si no encontramos por texto,
                    // usar primera celda del periodo.
                    if (
                        !celdaObjetivo &&
                        celdas.length > 0
                    ) {
                        celdaObjetivo =
                            celdas[0];
                    }

                    if (celdaObjetivo) {

                        celdaObjetivo.scrollIntoView(
                            {
                                behavior: "smooth",
                                block: "center",
                                inline: "center"
                            }
                        );

                        celdaObjetivo.click();
                    }

                },
                250
            );
        }

    }

    catch (error) {

        console.error(error);

        alert(
            "No fue posible cargar la matriz."
        );

    }

}


// ======================================================
// FORMATO PERIODO
// ======================================================

function periodoAHora(periodo) {

    const numero = Number(periodo);

    if (
        !Number.isFinite(numero) ||
        numero < 1 ||
        numero > 24
    ) {
        return 0;
    }

    // Regla SWAV:
    // PERIODO = Hour(HoraInicio) + 1
    return numero - 1;

}


// ======================================================
// FORMATO RANGO DEL PERÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂODO
// ======================================================

function periodoARango(periodo) {

    const numero = Number(periodo);

    if (
        !Number.isFinite(numero) ||
        numero < 1 ||
        numero > 24
    ) {
        return "-";
    }

    const horaNumero = numero - 1;

    const hora = String(
        horaNumero
    ).padStart(2, "0");

    return `${hora}:00 - ${hora}:59`;

}

// ======================================================
// COMBOS
// ======================================================

function cargarCombos() {

    llenarCombo(
        "cmbUnidad",
        [
            "U8",
            "U9"
        ]
    );


    llenarCombo(
        "cmbTipoDia",
        [
            ...new Set(
                datosOriginales
                    .map(x => x.tipo_dia)
                    .filter(Boolean)
            )
        ]
    );


    cargarComboServicioUsuario();

}


// ======================================================
// COMBO CHECK - SERVICIO USUARIO / INDICADOR
// ======================================================

function cargarComboServicioUsuario() {

    const menu =
        document.getElementById(
            "servicioUsuarioMenu"
        );

    if (!menu) {
        return;
    }


    const servicios = [
        ...new Set(
            datosOriginales
                .map(
                    fila =>
                        fila.servicio_usuario
                )
                .filter(Boolean)
        )
    ].sort();


    menu.innerHTML = `

        <label class="estado-option">

            <input
                type="checkbox"
                id="servicioUsuarioTodos"
                value="TODOS"
                checked
            >

            <span>
                Todos
            </span>

        </label>

        ${servicios.map(
            servicio => `

                <label class="estado-option">

                    <input
                        type="checkbox"
                        class="servicio-usuario-checkbox"
                        value="${servicio}"
                        checked
                    >

                    <span>
                        ${servicio}
                    </span>

                </label>

            `
        ).join("")}

    `;


    actualizarTextoServicioUsuario();
}


function obtenerServiciosUsuarioSeleccionados() {

    const todos =
        document.getElementById(
            "servicioUsuarioTodos"
        );

    const checks = [
        ...document.querySelectorAll(
            ".servicio-usuario-checkbox"
        )
    ];


    if (todos && todos.checked) {

        return checks.map(
            check => check.value
        );

    }


    return checks
        .filter(
            check => check.checked
        )
        .map(
            check => check.value
        );
}


function obtenerIndicadoresSeleccionados() {

    const todos =
        document.getElementById(
            "indicadorTodos"
        );

    const checks = [
        ...document.querySelectorAll(
            ".indicador-checkbox"
        )
    ];


    if (todos && todos.checked) {

        return [
            "IP",
            "IE"
        ];

    }


    return checks
        .filter(
            check => check.checked
        )
        .map(
            check =>
                String(
                    check.value || ""
                )
                .trim()
                .toUpperCase()
        )
        .filter(Boolean);
}


function actualizarTextoServicioUsuario() {

    const boton =
        document.getElementById(
            "btnServicioUsuario"
        );

    const todos =
        document.getElementById(
            "servicioUsuarioTodos"
        );

    const checks = [
        ...document.querySelectorAll(
            ".servicio-usuario-checkbox"
        )
    ];


    if (!boton) {
        return;
    }


    const seleccionados =
        checks.filter(
            check => check.checked
        );


    if (
        todos?.checked
        ||
        seleccionados.length === checks.length
    ) {

        boton.textContent = "Todos";

        return;
    }


    if (seleccionados.length === 0) {

        boton.textContent =
            "Ninguno";

        return;
    }


    if (seleccionados.length === 1) {

        boton.textContent =
            seleccionados[0].value;

        return;
    }


    boton.textContent =
        `${seleccionados.length} seleccionados`;
}


function actualizarTextoIndicador() {

    const boton =
        document.getElementById(
            "btnIndicador"
        );

    const todos =
        document.getElementById(
            "indicadorTodos"
        );

    const checks = [
        ...document.querySelectorAll(
            ".indicador-checkbox"
        )
    ];


    if (!boton) {
        return;
    }


    const seleccionados =
        checks.filter(
            check => check.checked
        );


    if (
        todos?.checked
        ||
        seleccionados.length === checks.length
    ) {

        boton.textContent =
            "Todos";

        return;
    }


    if (seleccionados.length === 0) {

        boton.textContent =
            "Ninguno";

        return;
    }


    boton.textContent =
        seleccionados
            .map(
                check => check.value
            )
            .join(" + ");
}


function configurarComboChecks() {

    const botonServicio =
        document.getElementById(
            "btnServicioUsuario"
        );

    const menuServicio =
        document.getElementById(
            "servicioUsuarioMenu"
        );

    const botonIndicador =
        document.getElementById(
            "btnIndicador"
        );

    const menuIndicador =
        document.getElementById(
            "indicadorMenu"
        );


    // --------------------------------------------------
    // ABRIR / CERRAR SERVICIO USUARIO
    // --------------------------------------------------

    botonServicio?.addEventListener(
        "click",
        event => {

            event.stopPropagation();

            menuIndicador?.classList.remove(
                "mostrar"
            );

            menuServicio?.classList.toggle(
                "mostrar"
            );

        }
    );


    // --------------------------------------------------
    // ABRIR / CERRAR INDICADOR
    // --------------------------------------------------

    botonIndicador?.addEventListener(
        "click",
        event => {

            event.stopPropagation();

            menuServicio?.classList.remove(
                "mostrar"
            );

            menuIndicador?.classList.toggle(
                "mostrar"
            );

        }
    );


    // --------------------------------------------------
    // CAMBIOS SERVICIO USUARIO
    // --------------------------------------------------

    document.addEventListener(
        "change",
        event => {

            if (
                event.target.id ===
                "servicioUsuarioTodos"
            ) {

                const checks = [
                    ...document.querySelectorAll(
                        ".servicio-usuario-checkbox"
                    )
                ];

                checks.forEach(
                    check => {

                        check.checked =
                            event.target.checked;

                    }
                );

                actualizarTextoServicioUsuario();

                aplicarFiltros();

                return;
            }


            if (
                event.target.classList.contains(
                    "servicio-usuario-checkbox"
                )
            ) {

                const checks = [
                    ...document.querySelectorAll(
                        ".servicio-usuario-checkbox"
                    )
                ];

                const todos =
                    document.getElementById(
                        "servicioUsuarioTodos"
                    );

                const marcados =
                    checks.filter(
                        check => check.checked
                    );


                if (todos) {

                    todos.checked =
                        marcados.length ===
                        checks.length;

                }


                actualizarTextoServicioUsuario();

                aplicarFiltros();

                return;
            }


            // ------------------------------------------
            // TODOS INDICADOR
            // ------------------------------------------

            if (
                event.target.id ===
                "indicadorTodos"
            ) {

                const checks = [
                    ...document.querySelectorAll(
                        ".indicador-checkbox"
                    )
                ];

                checks.forEach(
                    check => {

                        check.checked =
                            event.target.checked;

                    }
                );

                actualizarTextoIndicador();

                aplicarFiltros();

                return;
            }


            // ------------------------------------------
            // IP / IE
            // ------------------------------------------

            if (
                event.target.classList.contains(
                    "indicador-checkbox"
                )
            ) {

                const checks = [
                    ...document.querySelectorAll(
                        ".indicador-checkbox"
                    )
                ];

                const todos =
                    document.getElementById(
                        "indicadorTodos"
                    );

                const marcados =
                    checks.filter(
                        check => check.checked
                    );


                if (todos) {

                    todos.checked =
                        marcados.length ===
                        checks.length;

                }


                actualizarTextoIndicador();

                aplicarFiltros();

            }

        }
    );


    // --------------------------------------------------
    // CERRAR AL HACER CLICK AFUERA
    // --------------------------------------------------

    document.addEventListener(
        "click",
        event => {

            if (
                !event.target.closest(
                    "#servicioUsuarioDropdown"
                )
            ) {

                menuServicio?.classList.remove(
                    "mostrar"
                );

            }


            if (
                !event.target.closest(
                    "#indicadorDropdown"
                )
            ) {

                menuIndicador?.classList.remove(
                    "mostrar"
                );

            }

        }
    );


    actualizarTextoIndicador();
}


function llenarCombo(
    id,
    datos
) {

    const combo =
        document.getElementById(id);

    if (!combo) {
        return;
    }

    combo.innerHTML =
        "<option value=''>Todos</option>";


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
// ESTADO
// ======================================================

function configurarEstado() {

    const boton =
        document.getElementById(
            "btnEstado"
        );

    const menu =
        document.getElementById(
            "estadoMenu"
        );

    const todos =
        document.getElementById(
            "estadoTodos"
        );

    const checks =
        document.querySelectorAll(
            ".estado-checkbox"
        );


    if (
        !boton ||
        !menu ||
        !todos
    ) {
        return;
    }


    // --------------------------------------------------
    // ABRIR / CERRAR
    // --------------------------------------------------

    boton.addEventListener(
        "click",
        event => {

            event.stopPropagation();

            menu.classList.toggle(
                "mostrar"
            );

        }
    );


    // --------------------------------------------------
    // TODOS
    // --------------------------------------------------

    todos.addEventListener(
        "change",
        () => {

            checks.forEach(check => {

                check.checked =
                    todos.checked;

            });

            actualizarTextoEstado();

            aplicarFiltros();

        }
    );


    // --------------------------------------------------
    // ESTADOS INDIVIDUALES
    // --------------------------------------------------

    checks.forEach(check => {

        check.addEventListener(
            "change",
            () => {

                const seleccionados =
                    obtenerEstadosSeleccionados();


                if (
                    seleccionados.length ===
                    checks.length
                ) {

                    todos.checked = true;

                }

                else {

                    todos.checked = false;

                }


                actualizarTextoEstado();

                aplicarFiltros();

            }
        );

    });


    // --------------------------------------------------
    // CERRAR AL HACER CLICK AFUERA
    // --------------------------------------------------

    document.addEventListener(
        "click",
        event => {

            if (
                !event.target.closest(
                    "#estadoDropdown"
                )
            ) {

                menu.classList.remove(
                    "mostrar"
                );

            }

        }
    );


    actualizarTextoEstado();

}


// ======================================================
// OBTENER ESTADOS SELECCIONADOS
// ======================================================

function obtenerEstadosSeleccionados() {

    const todos =
        document.getElementById(
            "estadoTodos"
        );

    const checks =
        document.querySelectorAll(
            ".estado-checkbox"
        );


    // --------------------------------------------------
    // TODOS
    // --------------------------------------------------

    if (todos && todos.checked) {

        return [
            "OK",
            "SIMPLE",
            "COMPLEJO"
        ];

    }


    // --------------------------------------------------
    // ESTADOS SELECCIONADOS
    // --------------------------------------------------

    return [
        ...checks
    ]
    .filter(
        checkbox => checkbox.checked
    )
    .map(
        checkbox =>
            String(
                checkbox.value || ""
            )
            .trim()
            .toUpperCase()
    )
    .filter(Boolean);

}


// ======================================================
// TEXTO DEL BOTÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œN ESTADO
// ======================================================

function actualizarTextoEstado() {

    const boton =
        document.getElementById(
            "btnEstado"
        );

    const checks =
        document.querySelectorAll(
            ".estado-checkbox"
        );


    if (!boton) {
        return;
    }


    const seleccionados =
        obtenerEstadosSeleccionados();


    if (
        seleccionados.length ===
        checks.length
    ) {

        boton.textContent =
            "Todos";

        return;

    }


    if (
        seleccionados.length === 0
    ) {

        boton.textContent =
            "Ninguno";

        return;

    }


    const nombres = {

        OK: "Normal",

        SIMPLE: "Simple",

        COMPLEJO: "Complejo"

    };


    boton.textContent =
        seleccionados
            .map(
                estado =>
                    nombres[estado]
            )
            .join(" + ");

}


// ======================================================
// EVENTOS
// ======================================================

document.addEventListener(
    "change",
    async event => {

        if (
            event.target.id ===
            "cmbUnidad"
        ) {

            await cargarMatriz();

            return;
        }

        if (
            event.target.id ===
            "cmbTipoDia"
        ) {

            aplicarFiltros();
        }
    }
);


// ======================================================
// FILTROS
// ======================================================

function aplicarFiltros() {

    const unidad =
        document.getElementById(
            "cmbUnidad"
        )?.value || "";


    const tipoDia =
        document.getElementById(
            "cmbTipoDia"
        )?.value || "";


    const serviciosUsuario =
        obtenerServiciosUsuarioSeleccionados();


    const indicadores =
        obtenerIndicadoresSeleccionados();


    const estados =
        obtenerEstadosSeleccionados();


    datosFiltrados =
        datosOriginales.filter(
            fila => {

                // --------------------------------------
                // UNIDAD
                // --------------------------------------

                if (
                    unidad &&
                    fila.unidad !== unidad
                ) {

                    return false;

                }


                // --------------------------------------
                // TIPO DIA
                // --------------------------------------

                if (
                    tipoDia &&
                    fila.tipo_dia !== tipoDia
                ) {

                    return false;

                }


                // --------------------------------------
                // SERVICIO USUARIO
                // --------------------------------------

                if (
                    serviciosUsuario.length > 0
                    &&
                    !serviciosUsuario.includes(
                        fila.servicio_usuario
                    )
                ) {

                    return false;

                }


                // --------------------------------------
                // INDICADOR IP / IE
                // --------------------------------------

                if (
                    indicadores.length > 0
                ) {

                    const tieneIndicador =
                        Object.values(
                            fila.periodos || {}
                        )
                        .some(
                            dato => {

                                const indicador =
                                    String(
                                        dato?.indicador_tiempo_espera ??
                                        dato?.indicador ??
                                        ""
                                    )
                                    .trim()
                                    .toUpperCase();


                                return (
                                    indicador
                                    &&
                                    indicadores.includes(
                                        indicador
                                    )
                                );

                            }
                        );


                    if (!tieneIndicador) {

                        return false;

                    }

                }


                // --------------------------------------
                // ESTADO
                // --------------------------------------

                if (
                    estados.length > 0
                ) {

                    const tieneEstado =
                        Object.values(
                            fila.periodos || {}
                        )
                        .some(
                            dato => {

                                if (
                                    !dato ||
                                    !dato.clasificacion
                                ) {

                                    return false;

                                }


                                return estados.includes(
                                    String(
                                        dato.clasificacion
                                    )
                                    .toUpperCase()
                                );

                            }
                        );


                    if (!tieneEstado) {

                        return false;

                    }

                }


                return true;

            }
        );


    actualizarContadores(
        datosFiltrados
    );


    construirTabla(
        datosFiltrados
    );

}


// ======================================================
// CONTADORES
// ======================================================

async function actualizarContadores(
    datos
) {

    // ==================================================
    // CONTADORES OFICIALES DEL DASHBOARD
    // ==================================================
    //
    // Matriz y Dashboard deben mostrar exactamente
    // el mismo universo operacional:
    //
    // NORMAL   = dashboard.clasificacion.ok
    // SIMPLE   = dashboard.clasificacion.simple
    // COMPLEJO = dashboard.clasificacion.complejo
    //
    // Adicionalmente se muestran los eventos
    // separados por indicador IP / IE.
    // ==================================================

    try {

        const unidadDashboard =
            obtenerUnidadDashboardMatriz();

        if (!unidadDashboard) {

            console.info(
                "Matriz en modo Todas: "
                + "no se consulta Dashboard por unidad."
            );

            return;
        }

        const response =
            await fetch(
                "/api/dashboard?unidad="
                + encodeURIComponent(
                    unidadDashboard
                ),
                {
                    cache: "no-store"
                }
            );

        if (!response.ok) {

            throw new Error(
                "HTTP " + response.status
            );

        }

        const dashboard =
            await response.json();


        // --------------------------------------------------
        // CONTADORES GENERALES
        // --------------------------------------------------

        const normal =
            document.getElementById(
                "contadorNormal"
            );

        const simple =
            document.getElementById(
                "contadorSimple"
            );

        const complejo =
            document.getElementById(
                "contadorComplejo"
            );


        if (normal) {

            normal.textContent =
                Number(
                    dashboard.clasificacion?.ok
                    ?? 0
                );

        }


        if (simple) {

            simple.textContent =
                Number(
                    dashboard.clasificacion?.simple
                    ?? 0
                );

        }


        if (complejo) {

            complejo.textContent =
                Number(
                    dashboard.clasificacion?.complejo
                    ?? 0
                );

        }


        // --------------------------------------------------
        // CONTADORES IP / IE
        // --------------------------------------------------

        const contadores = {

            contadorIpSimple:
                dashboard.ip?.simples ?? 0,

            contadorIpComplejo:
                dashboard.ip?.complejos ?? 0,

            contadorIeSimple:
                dashboard.ie?.simples ?? 0,

            contadorIeComplejo:
                dashboard.ie?.complejos ?? 0,

            contadorIpTotal:
                dashboard.ip?.eventos ?? 0,

            contadorIeTotal:
                dashboard.ie?.eventos ?? 0

        };


        Object.entries(
            contadores
        ).forEach(
            ([id, valor]) => {

                const elemento =
                    document.getElementById(
                        id
                    );

                if (elemento) {

                    elemento.textContent =
                        Number(valor);

                }

            }
        );

    }

    catch (error) {

        console.error(
            "Error actualizando contadores "
            + "oficiales de Matriz:",
            error
        );

    }

}


// ======================================================
// DETERMINAR SI UN PERÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂODO TIENE ESTADO SELECCIONADO
// ======================================================

function periodoTieneEstado(
    fila,
    periodo,
    estados
) {

    const dato =
        fila.periodos?.[periodo] ??
        fila.periodos?.[
            String(periodo)
        ];


    if (!dato) {

        return false;

    }


    const estado =
        String(
            dato.clasificacion || ""
        )
        .toUpperCase();


    return estados.includes(
        estado
    );

}


// ======================================================
// OBTENER PERÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂODOS VISIBLES
// ======================================================

function obtenerPeriodosVisibles(
    datos
) {

    const periodos =
        new Set();


    const estados =
        obtenerEstadosSeleccionados();


    datos.forEach(
        fila => {

            Object.keys(
                fila.periodos || {}
            )
            .forEach(
                periodo => {

                    const numero =
                        Number(periodo);


                    if (
                        estados.length === 0
                    ) {

                        return;

                    }


                    if (
                        periodoTieneEstado(
                            fila,
                            numero,
                            estados
                        )
                    ) {

                        periodos.add(
                            numero
                        );

                    }

                }
            );

        }
    );


    return [
        ...periodos
    ]
    .sort(
        (a, b) =>
            a - b
    );

}


// ======================================================
// TABLA
// ======================================================

function construirTabla(
    datos
) {

    const encabezado =
        document.getElementById(
            "encabezado"
        );


    const cuerpo =
        document.getElementById(
            "cuerpo"
        );


    if (
        !encabezado ||
        !cuerpo
    ) {

        return;

    }


    encabezado.innerHTML =
        "";

    cuerpo.innerHTML =
        "";


    const periodos =
        obtenerPeriodosVisibles(
            datos
        );


    // ==================================================
    // SIN DATOS
    // ==================================================

    if (
        datos.length === 0
    ) {

        encabezado.innerHTML = `
            <tr>
                <th>
                    Sin resultados
                </th>
            </tr>
        `;

        return;

    }


    // ==================================================
    // ENCABEZADO
    // ==================================================

    encabezado.innerHTML = `

        <tr>

            <th>
                Servicio Usuario
            </th>

            <th>
                Servicio Empresa
            </th>

            ${periodos
                .map(
                    periodo => {

                        const horaInicio =
                            String(periodoAHora(periodo))
                                .padStart(2, "0") + ":00";

                        const horaFin =
                            String(periodoAHora(periodo))
                                .padStart(2, "0") + ":59";

                        return `

                            <th class="periodo-header">

                                <div class="periodo-numero">
                                    ${periodo}
                                </div>

                                <div class="periodo-hora">
                                    ${horaInicio} - ${horaFin}
                                </div>

                            </th>

                        `;

                    }
                )
                .join("")
            }

            <th>
                Promedio
            </th>

        </tr>

    `;


    // ==================================================
    // FILAS
    // ==================================================

    datos.forEach(
        fila => {

            const tr =
                document.createElement(
                    "tr"
                );


            // ------------------------------------------
            // SERVICIO USUARIO
            // ------------------------------------------

            const tdUsuario =
                document.createElement(
                    "td"
                );


            tdUsuario.textContent =
                fila.servicio_usuario ||
                "-";


            tr.appendChild(
                tdUsuario
            );


            // ------------------------------------------
            // SERVICIO EMPRESA
            // ------------------------------------------

            const tdEmpresa =
                document.createElement(
                    "td"
                );


            tdEmpresa.textContent =
                fila.servicio_empresa ||
                "-";


            tr.appendChild(
                tdEmpresa
            );


            // ------------------------------------------
            // VALORES
            // ------------------------------------------

            const valores =
                [];


            periodos.forEach(
                periodo => {

                    const td =
                        document.createElement(
                            "td"
                        );


                    td.classList.add(
                        "celda-matriz"
                    );


                    td.dataset.servicio =
                        fila.servicio_empresa;


                    td.dataset.periodo =
                        periodo;


                    const dato =
                        fila.periodos?.[
                            periodo
                        ] ??
                        fila.periodos?.[
                            String(periodo)
                        ];


                    // ----------------------------------
                    // SIN DATO
                    // ----------------------------------

                    if (!dato) {

                        td.innerHTML =
                            "-";

                        tr.appendChild(
                            td
                        );

                        return;

                    }


                    const clasificacion =
                        String(
                            dato.clasificacion ||
                            ""
                        )
                        .toUpperCase();


                    // ----------------------------------
                    // SI EL ESTADO NO ESTÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â SELECCIONADO
                    // ----------------------------------

                    const estados =
                        obtenerEstadosSeleccionados();


                    if (
                        !estados.includes(
                            clasificacion
                        )
                    ) {

                        td.innerHTML =
                            "-";

                        tr.appendChild(
                            td
                        );

                        return;

                    }


                    // ----------------------------------
                    // REDUCCIÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œN
                    // ----------------------------------

                    const reduccion =
                        Number(
                            dato.reduccion
                        );


                    if (
                        dato.reduccion !==
                            null &&
                        dato.reduccion !==
                            undefined &&
                        !Number.isNaN(
                            reduccion
                        )
                    ) {

                        valores.push(
                            reduccion
                        );

                    }


                    // ----------------------------------
                    // CLASE
                    // ----------------------------------

                    if (
                        clasificacion ===
                        "OK"
                    ) {

                        td.classList.add(
                            "normal"
                        );

                    }

                    else if (
                        clasificacion ===
                        "SIMPLE"
                    ) {

                        td.classList.add(
                            "simple"
                        );

                    }

                    else if (
                        clasificacion ===
                        "COMPLEJO"
                    ) {

                        td.classList.add(
                            "complejo"
                        );

                    }


                    // ----------------------------------
                    // SEMAFORO
                    // ----------------------------------

                    let claseSemaforo =
                        "semaforo-ok";

                    if (
                        clasificacion ===
                        "SIMPLE"
                    ) {

                        claseSemaforo =
                            "semaforo-simple";

                    }

                    else if (
                        clasificacion ===
                        "COMPLEJO"
                    ) {

                        claseSemaforo =
                            "semaforo-complejo";

                    }

                    // ----------------------------------
                    // PORCENTAJE
                    // ----------------------------------

                    let porcentaje =
                        "-";


                    if (
                        dato.reduccion !==
                            null &&
                        dato.reduccion !==
                            undefined &&
                        !Number.isNaN(
                            reduccion
                        )
                    ) {

                        porcentaje =
                            reduccion.toFixed(
                                1
                            ) + "%";

                    }


                    // ----------------------------------
                    // VELOCIDAD
                    // ----------------------------------

                    let velocidad =
                        "-";


                    if (
                        dato.velocidad_real !==
                            null &&
                        dato.velocidad_real !==
                            undefined &&
                        !Number.isNaN(
                            Number(
                                dato.velocidad_real
                            )
                        )
                    ) {

                        velocidad =
                            Number(
                                dato.velocidad_real
                            )
                            .toFixed(1)
                            +
                            " km/h";

                    }


                    // ----------------------------------
                    // CONTENIDO
                    // ----------------------------------

                    td.innerHTML = `

                        <div class="indicador-matriz">
                            ${
                                String(
                                    dato.indicador_tiempo_espera ??
                                    dato.indicador ??
                                    ""
                                )
                                .trim()
                                .toUpperCase() || "-"
                            }
                        </div>

                        <div class="porcentaje">
                            ${porcentaje}
                        </div>

                        <div class="velocidad">
                            ${velocidad}
                        </div>

                    `;


                    // ----------------------------------
                    // CLICK
                    // ----------------------------------

                    td.addEventListener(
                        "click",
                        () => {

                            document
                                .querySelectorAll(
                                    ".celda-matriz"
                                )
                                .forEach(
                                    celda => {

                                        celda.classList.remove(
                                            "seleccionada"
                                        );

                                    }
                                );


                            document
                                .querySelectorAll(
                                    "#cuerpo tr"
                                )
                                .forEach(
                                    filaHTML => {

                                        filaHTML.classList.remove(
                                            "fila-seleccionada"
                                        );

                                    }
                                );


                            td.classList.add(
                                "seleccionada"
                            );


                            tr.classList.add(
                                "fila-seleccionada"
                            );


                            cargarRegistro(
                                fila.servicio_empresa,
                                Number(
                                    periodo
                                )
                            );


                            document
                                .getElementById(
                                    "registro"
                                )
                                ?.scrollIntoView(
                                    {
                                        behavior:
                                            "smooth",

                                        block:
                                            "start"
                                    }
                                );

                        }
                    );


                    tr.appendChild(
                        td
                    );

                }
            );


            // ------------------------------------------
            // PROMEDIO
            // ------------------------------------------

            const tdPromedio =
                document.createElement(
                    "td"
                );


            if (
                valores.length > 0
            ) {

                const promedio =
                    valores.reduce(
                        (
                            a,
                            b
                        ) =>
                            a + b,
                        0
                    )
                    /
                    valores.length;


                tdPromedio.textContent =
                    promedio.toFixed(
                        1
                    ) + "%";


                if (
                    promedio >= 15
                ) {

                    tdPromedio.classList.add(
                        "promedio-alto"
                    );

                }

                else if (
                    promedio >= 5
                ) {

                    tdPromedio.classList.add(
                        "promedio-medio"
                    );

                }

            }

            else {

                tdPromedio.textContent =
                    "-";

            }


            tr.appendChild(
                tdPromedio
            );


            cuerpo.appendChild(
                tr
            );

        }
    );

}


// ======================================================
// DETALLE DEL REGISTRO
// ======================================================

function cargarRegistro(
    servicioEmpresa,
    periodo
) {

    const contenedor =
        document.getElementById(
            "registro"
        );


    if (!contenedor) {
        return;
    }


    let encontrado =
        null;


    // ==================================================
    // BUSCAR
    // ==================================================

    for (
        const fila of datosFiltrados
    ) {

        if (
            fila.servicio_empresa !==
            servicioEmpresa
        ) {

            continue;

        }


        const dato =
            fila.periodos?.[
                String(periodo)
            ] ??
            fila.periodos?.[
                periodo
            ];


        if (dato) {

            encontrado = {

                servicioUsuario:
                    fila.servicio_usuario,

                servicioEmpresa:
                    fila.servicio_empresa,

                periodo:
                    Number(periodo),

                ...dato

            };


            break;

        }

    }


    // ==================================================
    // NO ENCONTRADO
    // ==================================================

    if (!encontrado) {

        contenedor.innerHTML =
            "";

        return;

    }


    // ==================================================
    // PPU
    // ==================================================

    const ppus =
        Array.isArray(
            encontrado.ppu
        )
            ? encontrado.ppu
            : [];


    // ==================================================
    // VALORES EXACTOS DE LAS PPU DEL PERIODO
    // ==================================================
    // Se muestran los mismos valores de la tabla inferior.
    // No se promedian.
    // No se recalculan.
    // ==================================================

    // ==================================================
    // PROMEDIOS PPU DEL PERIODO - PRESENTACION
    // ==================================================

    const velocidadesValidas =
        ppus
            .filter(
                ppu =>
                    ppu.velocidad_real !== null &&
                    ppu.velocidad_real !== undefined &&
                    ppu.velocidad_real !== ""
            )
            .map(ppu => Number(ppu.velocidad_real))
            .filter(valor => Number.isFinite(valor));

    const reduccionesValidas =
        ppus
            .filter(
                ppu =>
                    ppu.reduccion !== null &&
                    ppu.reduccion !== undefined &&
                    ppu.reduccion !== ""
            )
            .map(ppu => Number(ppu.reduccion))
            .filter(valor => Number.isFinite(valor));


    const velocidadPromedioPPU =
        velocidadesValidas.length > 0

            ? (
                velocidadesValidas.reduce(
                    (total, valor) => total + valor,
                    0
                )
                /
                velocidadesValidas.length
              ).toFixed(1) + " km/h"

            : "-";


    const reduccionPromedioPPU =
        reduccionesValidas.length > 0

            ? (
                reduccionesValidas.reduce(
                    (total, valor) => total + valor,
                    0
                )
                /
                reduccionesValidas.length
              ).toFixed(2) + " %"

            : "-";

    let htmlPPU =
        "";


    if (
        ppus.length === 0
    ) {

        htmlPPU = `

            <div
                class="alert alert-secondary mb-0"
            >

                No hay PPU registradas
                para este perÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­odo.

            </div>

        `;

    }

    else {

        htmlPPU = `

            <div class="table-responsive">

                <table
                    class="table table-sm
                           table-hover
                           table-bordered
                           align-middle
                           mb-0"
                >

                    <thead class="table-light">

                        <tr>

                            <th>
                                PPU
                            </th>

                            <th>
                                Servicio Empresa
                            </th>

                            <th>
                                Indicador
                            </th>

                            <th>
                                Hora Inicio
                            </th>

                            <th>
                                Hora Fin
                            </th>

                            <th>
                                Velocidad Real PPU
                            </th>

                            <th>
                                Velocidad Teórica
                            </th>

                            <th>
                                Reducción
                            </th>

                            <th>
                                Estado
                            </th>

                        </tr>

                    </thead>


                    <tbody>

                        ${ppus.map(
                            ppu => `

                            <tr>

                                <td>

                                    <strong>
                                        ${
                                            ppu.patente
                                            ??
                                            "-"
                                        }
                                    </strong>
</td>


                                <td>

                                    ${
                                        ppu.servicio_empresa
                                        ??
                                        encontrado.servicioEmpresa
                                    }

                                </td>


                                <td class="ppu-indicador-celda">

                                    <strong>
                                        ${
                                            String(
                                                ppu.indicador
                                                ??
                                                "-"
                                            )
                                            .trim()
                                            .toUpperCase()
                                        }
                                    </strong>
</td>


                                <td class="text-center">
                                    ${
                                        ppu.inicio_servicio
                                            ? String(
                                                ppu.inicio_servicio
                                              )
                                              .trim()
                                              .split(" ")
                                              .pop()
                                            : "-"
                                    }
                                </td>


                                <td class="text-center">
                                    ${
                                        ppu.fin_servicio
                                            ? String(
                                                ppu.fin_servicio
                                              )
                                              .trim()
                                              .split(" ")
                                              .pop()
                                            : "-"
                                    }
                                </td>


                                <td>

                                    ${
                                        ppu.velocidad_real !==
                                            null &&
                                        ppu.velocidad_real !==
                                            undefined

                                        ? Number(
                                            ppu.velocidad_real
                                          )
                                          .toFixed(1)
                                          +
                                          " km/h"

                                        : "-"
                                    }

                                </td>


                                <td>

                                    ${
                                        ppu.velocidad_teorica !==
                                            null &&
                                        ppu.velocidad_teorica !==
                                            undefined

                                        ? Number(
                                            ppu.velocidad_teorica
                                          )
                                          .toFixed(2)
                                          +
                                          " km/h"

                                        : "-"
                                    }

                                </td>


                                <td>

                                    ${
                                        ppu.reduccion !==
                                            null &&
                                        ppu.reduccion !==
                                            undefined

                                        ? Number(
                                            ppu.reduccion
                                          )
                                          .toFixed(2)
                                          +
                                          " %"

                                        : "-"
                                    }

                                </td>


                                <td class="text-center">

                                    ${
                                        (() => {

                                            const estadoPPU = String(
                                                ppu.estado ?? "-"
                                            )
                                            .trim()
                                            .toUpperCase();

                                            let claseEstado = "estado-ppu-ok";

                                            if (estadoPPU === "SIMPLE") {
                                                claseEstado = "estado-ppu-simple";
                                            }
                                            else if (estadoPPU === "COMPLEJO") {
                                                claseEstado = "estado-ppu-complejo";
                                            }

                                            return `
                                                <span class="estado-ppu ${claseEstado}">
                                                    ${estadoPPU}
                                                </span>
                                            `;

                                        })()
                                    }

                                </td>

                            </tr>

                        `
                        ).join("")}

                    </tbody>

                </table>

            </div>

        `;

    }


    // ==================================================
    // DETALLE COMPACTO
    // ==================================================

    contenedor.innerHTML = `

        <div class="card shadow-sm mt-4 detalle-evento">

            <!-- ==================================================
                ENCABEZADO
                ================================================== -->

            <div class="card-header bg-primary text-white detalle-header">

                <h5 class="mb-0">

                    <i class="bi bi-clipboard2-data-fill me-2"></i>

                    Detalle del Evento Operacional

                </h5>

            </div>


            <div class="card-body">


                <!-- ==================================================
                    FILA 1
                    ================================================== -->

                <div class="row detalle-fila">


                    <!-- SERVICIO USUARIO -->

                    <div class="col detalle-item">

                        <div class="detalle-icon">

                            <i class="bi bi-bus-front-fill"></i>

                        </div>

                        <div>

                            <b>
                                Servicio Usuario
                            </b>

                            <span>
                                ${encontrado.servicioUsuario}
                            </span>

                        </div>

                    </div>


                    <!-- SERVICIO EMPRESA -->

                    <div class="col detalle-item">

                        <div class="detalle-icon">

                            <i class="bi bi-bus-front"></i>

                        </div>

                        <div>

                            <b>
                                Servicio Empresa
                            </b>

                            <span>
                                ${encontrado.servicioEmpresa}
                            </span>

                        </div>

                    </div>


                    <!-- VELOCIDAD REAL -->

                    <div class="col detalle-item">

                        <div class="detalle-icon">

                            <i class="bi bi-speedometer2"></i>

                        </div>

                        <div>

                            <b>
                                Velocidad Real Promedio
                            </b>

                            <span>

                                ${velocidadPromedioPPU}

                            </span>

                        </div>

                    </div>


                    <!-- VELOCIDAD TEÓRICA -->

                    <div class="col detalle-item">

                        <div class="detalle-icon">

                            <i class="bi bi-speedometer"></i>

                        </div>

                        <div>

                            <b>
                                Velocidad Teórica
                            </b>

                            <span>

                                ${
                                    encontrado.velocidad_teorica !== null &&
                                    encontrado.velocidad_teorica !== undefined

                                    ? Number(
                                        encontrado.velocidad_teorica
                                    ).toFixed(2)
                                    + " km/h"

                                    : "-"
                                }

                            </span>

                        </div>

                    </div>


                    <!-- REDUCCIÓN -->

                    <div class="col detalle-item">

                        <div class="detalle-icon detalle-icon-red">

                            <i class="bi bi-graph-down-arrow"></i>

                        </div>

                        <div>

                            <b>
                                Reducción Promedio
                            </b>

                            <span class="${
                                encontrado.clasificacion === "COMPLEJO"
                                    ? "reduccion-complejo"
                                    : encontrado.clasificacion === "SIMPLE"
                                    ? "reduccion-simple"
                                    : ""
                            }">

                                ${reduccionPromedioPPU}

                            </span>

                        </div>

                    </div>


                </div>


                <hr>


                <!-- ==================================================
                    FILA 2
                    ================================================== -->

                <div class="row detalle-fila detalle-fila-secundaria">


                    <!-- PERÍODO -->

                    <div class="col-md-3 detalle-item">

                        <div class="detalle-icon">

                            <i class="bi bi-clock-fill"></i>

                        </div>

                        <div>

                            <b>
                                Período
                            </b>

                            <span>

                                ${Number(encontrado.periodo)}
                                \u00B7 ${periodoARango(encontrado.periodo)}

                            </span>

                        </div>

                    </div>


                                        <!-- INDICADOR IP / IE -->

                    <div class="col-md-3 detalle-item">

                        <div class="detalle-icon">

                            <i class="bi bi-bar-chart-fill"></i>

                        </div>

                        <div>

                            <b>
                                Indicador
                            </b>

                            <span class="${
                                String(
                                    encontrado.indicador_tiempo_espera ??
                                    encontrado.indicador ??
                                    ""
                                ).toUpperCase() === "IE"
                                    ? "indicador-ie"
                                    : "indicador-ip"
                            }">

                                ${
                                    encontrado.indicador_tiempo_espera ??
                                    encontrado.indicador ??
                                    "-"
                                }

                            </span>

                        </div>

                    </div>


<!-- CLASIFICACIÓN -->

                    <div class="col-md-3 detalle-item">

                        <div class="detalle-icon detalle-icon-estado">

                            ${
                                encontrado.clasificacion === "COMPLEJO"

                                ? `<i class="bi bi-exclamation-triangle-fill"></i>`

                                : encontrado.clasificacion === "SIMPLE"

                                ? `<i class="bi bi-exclamation-circle-fill"></i>`

                                : `<i class="bi bi-check-circle-fill"></i>`
                            }

                        </div>

                        <div>

                            <b>
                                Clasificación
                            </b>

                            <span class="
                                detalle-clasificacion
                                ${
                                    encontrado.clasificacion === "COMPLEJO"
                                    ? "clasificacion-complejo"
                                    : encontrado.clasificacion === "SIMPLE"
                                    ? "clasificacion-simple"
                                    : "clasificacion-normal"
                                }
                            ">

                                ${encontrado.clasificacion}

                            </span>

                        </div>

                    </div>


                    <!-- EXPEDICIONES -->

                    <div class="col-md-3 detalle-item">

                        <div class="detalle-icon">

                            <i class="bi bi-calendar3"></i>

                        </div>

                        <div>

                            <b>
                                Total de Expediciones
                            </b>

                            <span>
                                ${encontrado.expediciones ?? 0}
                            </span>

                        </div>

                    </div>


                </div>


                <hr>


                <!-- ==================================================
                    PPU
                    ================================================== -->

                <div class="detalle-ppu">


                    <h6 class="fw-bold mb-3">

                        <i class="bi bi-bus-front-fill me-2"></i>

                        PPU del período · Velocidades individuales

                    </h6>


                    ${htmlPPU}


                </div>


            </div>

        </div>

    `;

}










// =========================================================
// SWAV_SELECTOR_UNIDAD_MATRIZ_V1
// SELECTOR DE UNIDAD POR URL
// NO UTILIZA localStorage
// =========================================================

(function instalarSelectorUnidadMatriz() {

    function unidadActualMatriz() {

        const params =
            new URLSearchParams(
                window.location.search
            );

        const unidad =
            String(
                params.get("unidad")
                || ""
            )
            .trim()
            .toUpperCase();

        if (
            unidad === "U8"
            ||
            unidad === "U9"
        ) {
            return unidad;
        }

        const combo =
            document.getElementById(
                "cmbUnidad"
            );

        const unidadCombo =
            String(
                combo?.value
                || ""
            )
            .trim()
            .toUpperCase();

        if (
            unidadCombo === "U8"
            ||
            unidadCombo === "U9"
        ) {
            return unidadCombo;
        }

        return null;
    }


    function actualizarNavegacionMatriz(
        unidad
    ) {

        if (
            unidad !== "U8"
            &&
            unidad !== "U9"
        ) {
            return;
        }

        document
            .querySelectorAll(
                'a[href="/dashboard"], '
                + 'a[href="/dashboard/u8"], '
                + 'a[href="/dashboard/u9"]'
            )
            .forEach(
                enlace => {

                    enlace.href =
                        unidad === "U9"
                            ? "/dashboard/u9"
                            : "/dashboard/u8";
                }
            );
    }


    function crearSelectorMatriz() {

        if (
            document.getElementById(
                "swavSelectorUnidad"
            )
        ) {
            return;
        }

        const unidad =
            unidadActualMatriz();

        if (
            unidad !== "U8"
            &&
            unidad !== "U9"
        ) {
            return;
        }

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
                                "/matriz?unidad="
                                +
                                encodeURIComponent(
                                    nuevaUnidad
                                );
                        }
                    );
                }
            );

        actualizarNavegacionMatriz(
            unidad
        );
    }


    function instalarEstiloSelectorMatriz() {

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
                    rgba(20,45,80,0.10);

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


    function iniciarSelectorMatriz() {

        instalarEstiloSelectorMatriz();

        crearSelectorMatriz();
    }


    if (
        document.readyState ===
        "loading"
    ) {

        document.addEventListener(
            "DOMContentLoaded",
            iniciarSelectorMatriz
        );

    }
    else {

        iniciarSelectorMatriz();
    }

})();

