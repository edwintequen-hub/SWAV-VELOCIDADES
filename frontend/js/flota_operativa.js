(() => {

    "use strict";


    // ================================================================
    // ESTADO
    // ================================================================

    let datosActuales = null;


    // ================================================================
    // UTILIDADES
    // ================================================================

    const $ = (id) =>
        document.getElementById(id);


    function escapeHtml(valor) {

        return String(
            valor ?? ""
        )
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }


    function numero(valor) {

        const n = Number(valor);

        return Number.isFinite(n)
            ? n
            : 0;
    }


    function porcentaje(valor) {

        if (
            valor === null ||
            valor === undefined
        ) {
            return "—";
        }

        return (
            Number(valor)
                .toLocaleString(
                    "es-CL",
                    {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                    }
                )
            +
            " %"
        );
    }


    function periodoTexto(valor) {

        return (
            "P"
            +
            String(
                Number(valor) || 0
            ).padStart(
                2,
                "0"
            )
        );
    }


    function fechaCL(fecha) {

        if (!fecha) {
            return "";
        }

        const partes =
            String(fecha).split("-");

        if (partes.length !== 3) {
            return fecha;
        }

        return (
            partes[2]
            +
            "-"
            +
            partes[1]
            +
            "-"
            +
            partes[0]
        );
    }


    function clasePorcentaje(pct) {

        const n = numero(pct);

        if (n < 50) {
            return "status-critical";
        }

        if (n < 70) {
            return "status-warning";
        }

        return "status-good";
    }


    function textoEstado(pct) {

        const n = numero(pct);

        if (n < 50) {
            return "Mayor prioridad";
        }

        if (n < 70) {
            return "Revisar";
        }

        return "Mejor condición";
    }


    // ================================================================
    // QUERY PARAMS
    // ================================================================

    function queryParams(extra = {}) {

        const params =
            new URLSearchParams();


        const campos = {

            fecha_desde:
                $("fechaDesde").value,

            fecha_hasta:
                $("fechaHasta").value,

            unidad:
                $("unidad").value,

            terminal:
                $("terminal").value,

            servicio:
                $("servicio").value,

            periodo_inicial:
                $("periodoInicial").value,

            periodo_final:
                $("periodoFinal").value
        };


        Object.entries({
            ...campos,
            ...extra
        })
        .forEach(
            ([clave, valor]) => {

                if (
                    valor !== "" &&
                    valor !== null &&
                    valor !== undefined
                ) {

                    params.set(
                        clave,
                        valor
                    );
                }
            }
        );


        return params;
    }


    // ================================================================
    // FILTROS
    // ================================================================

    async function cargarFiltros() {

        const respuesta =
            await fetch(
                "/api/flota-operativa/filtros"
            );


        if (!respuesta.ok) {

            throw new Error(
                "No fue posible cargar los filtros."
            );
        }


        const datos =
            await respuesta.json();


        $("catalogoVersion").textContent =
            (
                "Catálogo "
                +
                (
                    datos.catalogo_version
                    ||
                    "sin versión"
                )
            );


        if (datos.fecha_hasta) {

            $("fechaDesde").value =
                datos.fecha_hasta;

            $("fechaHasta").value =
                datos.fecha_hasta;
        }


        for (
            const unidad
            of (datos.unidades || [])
        ) {

            $("unidad")
                .insertAdjacentHTML(
                    "beforeend",
                    `
                    <option value="${escapeHtml(unidad)}">
                        ${escapeHtml(unidad)}
                    </option>
                    `
                );
        }


        for (
            const terminal
            of (datos.terminales || [])
        ) {

            $("terminal")
                .insertAdjacentHTML(
                    "beforeend",
                    `
                    <option value="${escapeHtml(terminal.codigo)}">
                        ${escapeHtml(terminal.nombre)}
                        (${numero(terminal.asignada)})
                    </option>
                    `
                );
        }


        for (
            const servicio
            of (datos.servicios || [])
        ) {

            $("servicio")
                .insertAdjacentHTML(
                    "beforeend",
                    `
                    <option value="${escapeHtml(servicio)}">
                        ${escapeHtml(servicio)}
                    </option>
                    `
                );
        }


        for (
            const item
            of (datos.periodos || [])
        ) {

            const p =
                periodoTexto(
                    item.periodo
                );


            const inicio =
                String(
                    item.inicio || ""
                ).slice(
                    0,
                    5
                );


            const fin =
                String(
                    item.fin || ""
                ).slice(
                    0,
                    5
                );


            const etiqueta =
                (
                    `${p} · ${inicio}-${fin}`
                );


            $("periodoInicial")
                .insertAdjacentHTML(
                    "beforeend",
                    `
                    <option value="${item.periodo}">
                        ${etiqueta}
                    </option>
                    `
                );


            $("periodoFinal")
                .insertAdjacentHTML(
                    "beforeend",
                    `
                    <option value="${item.periodo}">
                        ${etiqueta}
                    </option>
                    `
                );
        }


        $("periodoInicial").value =
            "1";

        $("periodoFinal").value =
            "24";
    }


    // ================================================================
    // LOADING
    // ================================================================

    function setLoading(estado) {

        document.body.classList.toggle(
            "is-loading",
            estado
        );


        $("btnConsultar").disabled =
            estado;


        $("btnExportar").disabled =
            estado;
    }


    // ================================================================
    // CONSULTA
    // ================================================================

    async function consultar() {

        const periodoInicial =
            Number(
                $("periodoInicial").value
            );


        const periodoFinal =
            Number(
                $("periodoFinal").value
            );


        if (
            periodoInicial >
            periodoFinal
        ) {

            alert(
                "El período inicial no puede ser mayor que el período final."
            );

            return;
        }


        setLoading(
            true
        );


        try {

            const respuesta =
                await fetch(
                    (
                        "/api/flota-operativa/consulta?"
                        +
                        queryParams().toString()
                    )
                );


            const datos =
                await respuesta.json();


            if (!respuesta.ok) {

                throw new Error(
                    datos.detail
                    ||
                    "Error al consultar Flota Operativa."
                );
            }


            datosActuales =
                datos;


            render(
                datos
            );

        }
        catch (error) {

            console.error(
                error
            );

            alert(
                error.message
            );

        }
        finally {

            setLoading(
                false
            );
        }
    }


    // ================================================================
    // RENDER GENERAL
    // ================================================================

    function render(datos) {

        const total =
            datos.total_global
            ||
            {
                asignada: 0,
                operativa: 0,
                sin_transmision: 0,
                porcentaje_operativa: 0
            };


        renderCabeceraConsulta();

        renderKpis(
            total
        );

        renderResumenUnidades(
            datos.resumen_unidades
            ||
            [],
            datos.cobertura_fuente
            ||
            [],
            total,
            datos.resumen_terminal_global
            ||
            []
        );

        renderVistaOperacionPorUnidad(
            datos
        );

        // ============================================================
        // R8D2
        // BLOQUES INDEPENDIENTES:
        // un error visual en ranking no puede impedir Sin Tx
        // ============================================================

        try {


        } catch (error) {

            console.error(
                "ERROR RENDER PPU SIN TRANSMISION:",
                error
            );
        }


        try {


        } catch (error) {

            console.error(
                "ERROR RENDER TERMINALES APOYO:",
                error
            );
        }





        // ============================================================
        // R8D2 - BLOQUES INDEPENDIENTES
        // ============================================================

        try {

            renderSinTxDias(
                datos
            );

        } catch (error) {

            console.error(
                "ERROR R8D2 SIN TRANSMISION:",
                error
            );
        }


        try {

            renderRanking(
                datos.resumen_terminal_global
                ||
                []
            );

        } catch (error) {

            console.error(
                "ERROR R8D2 APOYO:",
                error
            );
        }


        $("horaConsulta").textContent =
            new Date()
                .toLocaleTimeString(
                    "es-CL",
                    {
                        hour12: false
                    }
                );
    }


    // ================================================================
    // CABECERA RESULTADO
    // ================================================================

    function renderCabeceraConsulta() {

        const desde =
            $("fechaDesde").value;


        const hasta =
            $("fechaHasta").value;


        let titulo =
            "Flota Operativa";


        if (
            desde &&
            hasta &&
            desde === hasta
        ) {

            titulo +=
                " — "
                +
                fechaCL(
                    desde
                );
        }
        else if (
            desde &&
            hasta
        ) {

            titulo +=
                " — "
                +
                fechaCL(
                    desde
                )
                +
                " al "
                +
                fechaCL(
                    hasta
                );
        }


        $("tituloConsulta").textContent =
            titulo;


        const pi =
            periodoTexto(
                $("periodoInicial").value
            );


        const pf =
            periodoTexto(
                $("periodoFinal").value
            );


        $("subtituloConsulta").textContent =
            (
                "Períodos seleccionados: "
                +
                pi
                +
                " a "
                +
                pf
            );
    }


    // ================================================================
    // KPI
    // ================================================================

    function renderKpis(total) {

        $("kpiAsignada").textContent =
            numero(
                total.asignada
            )
            .toLocaleString(
                "es-CL"
            );


        $("kpiOperativa").textContent =
            numero(
                total.operativa
            )
            .toLocaleString(
                "es-CL"
            );


        $("kpiSinTx").textContent =
            numero(
                total.sin_transmision
            )
            .toLocaleString(
                "es-CL"
            );


        $("kpiPorcentaje").textContent =
            porcentaje(
                total.porcentaje_operativa
            );
    }


    // ================================================================
    // RESUMEN EJECUTIVO U8 / U9 / TOTAL
    // ================================================================

    function renderResumenUnidades(
        filas,
        cobertura,
        total,
        terminales
    ) {

        const tbody =
            $("tbodyResumenUnidades");


        if (!tbody) {
            return;
        }


        const resumen =
            Array.isArray(filas)
            ? filas
            : [];


        if (!resumen.length) {

            tbody.innerHTML =
                `
                <tr>
                    <td colspan="5" class="empty-cell">
                        Sin información por unidad.
                    </td>
                </tr>
                `;

        }
        else {

            tbody.innerHTML =
                resumen
                .map(
                    fila => {

                        const esTotal =
                            String(
                                fila.unidad
                                ||
                                ""
                            )
                            .toUpperCase()
                            ===
                            "TOTAL";


                        const clase =
                            clasePorcentaje(
                                fila.porcentaje_operativa
                            );


                        return `
                        <tr class="${esTotal ? "unit-total-row" : ""}">

                            <td>
                                <strong>
                                    ${escapeHtml(fila.unidad)}
                                </strong>
                            </td>

                            <td class="num">
                                ${numero(fila.asignada)}
                            </td>

                            <td class="num operative-number">
                                ${numero(fila.operativa)}
                            </td>

                            <td class="num">
                                <span class="missing-number">
                                    ${numero(fila.sin_transmision)}
                                </span>
                            </td>

                            <td class="num">
                                <span class="pct-badge ${clase}">
                                    ${porcentaje(fila.porcentaje_operativa)}
                                </span>
                            </td>

                        </tr>
                        `;
                    }
                )
                .join("");

        }


        renderCoberturaR16(
            cobertura
        );


        renderDonutFlota(
            total
        );


        renderGraficoTerminales(
            terminales
        );
    }


    function renderCoberturaR16(filas) {

        const contenedor =
            $("coberturaR16");


        if (!contenedor) {
            return;
        }


        const cobertura =
            Array.isArray(filas)
            ? filas
            : [];


        if (!cobertura.length) {

            contenedor.innerHTML =
                `
                <span class="coverage-chip warning">
                    Cobertura R1.6 no disponible
                </span>
                `;

            return;
        }


        contenedor.innerHTML =
            cobertura
            .map(
                fila => {

                    const completa =
                        Boolean(
                            fila.dia_completo
                        );


                    return `
                    <span
                        class="coverage-chip ${completa ? "complete" : "warning"}">

                        <strong>
                            ${escapeHtml(fila.unidad)}
                        </strong>

                        hasta

                        <strong>
                            ${escapeHtml(fila.hasta || "--:--")}
                        </strong>

                        ${
                            completa
                            ? "? día completo"
                            : "? cobertura parcial"
                        }

                    </span>
                    `;
                }
            )
            .join("");
    }


    function renderDonutFlota(total) {

        const donut =
            $("donutFlota");


        if (!donut) {
            return;
        }


        const asignada =
            numero(
                total?.asignada
            );


        const operativa =
            numero(
                total?.operativa
            );


        const sinTx =
            numero(
                total?.sin_transmision
            );


        const pct =
            asignada > 0
            ? Math.max(
                0,
                Math.min(
                    100,
                    (
                        operativa
                        /
                        asignada
                    )
                    *
                    100
                )
            )
            : 0;


        donut.style.setProperty(
            "--flota-pct",
            pct
        );


        const pctNodo =
            $("donutPorcentaje");

        if (pctNodo) {

            pctNodo.textContent =
                porcentaje(
                    total?.porcentaje_operativa
                );
        }


        const trabajando =
            $("donutTrabajando");

        if (trabajando) {

            trabajando.textContent =
                operativa
                .toLocaleString(
                    "es-CL"
                );
        }


        const noTrabajando =
            $("donutNoTrabajando");

        if (noTrabajando) {

            noTrabajando.textContent =
                sinTx
                .toLocaleString(
                    "es-CL"
                );
        }
    }


    // ================================================================
    // IDENTIFICACION OPERACIONAL DE UNIDAD POR TERMINAL
    // U8 = ALFA
    // U9 = OMEGA
    // Solo presentacion frontend.
    // No modifica calculos ni datos del backend.
    // ================================================================

    function unidadPorTerminal(
        terminal
    ) {

        const codigo =
            String(
                terminal
                ||
                ""
            )
            .trim()
            .toUpperCase()
            .normalize("NFD")
            .replace(
                /[\u0300-\u036f]/g,
                ""
            );

        const terminalesU8 =
            new Set([
                "CONDELL",
                "EL RETIRO",
                "SANTA MARGARITA",
                "STA. MARGARITA",
                "STA MARGARITA",
                "SANTA MARTA",
                "STA. MARTA",
                "STA MARTA"
            ]);

        const terminalesU9 =
            new Set([
                "AGUIRRE LUCO",
                "A. LUCO",
                "A LUCO",
                "JUANITA",
                "PIE ANDINO"
            ]);

        if (
            terminalesU8.has(
                codigo
            )
        ) {
            return {
                codigo: "U8",
                empresa: "ALFA",
                texto: "U8 ? ALFA"
            };
        }

        if (
            terminalesU9.has(
                codigo
            )
        ) {
            return {
                codigo: "U9",
                empresa: "OMEGA",
                texto: "U9 ? OMEGA"
            };
        }

        return {
            codigo: "?",
            empresa: "",
            texto: "?"
        };
    }


    function ordenTerminalUnidad(
        fila
    ) {

        const terminal =
            String(
                fila.terminal
                ||
                fila.terminal_nombre
                ||
                ""
            )
            .trim()
            .toUpperCase();

        const orden = {
            "CONDELL": 10,
            "EL RETIRO": 20,
            "SANTA MARGARITA": 30,
            "SANTA MARTA": 40,

            "AGUIRRE LUCO": 110,
            "JUANITA": 120,
            "PIE ANDINO": 130
        };

        return orden[terminal] ?? 999;
    }


    function ordenarPorUnidadTerminal(
        filas
    ) {

        return [...filas].sort(
            (a, b) =>
                ordenTerminalUnidad(a)
                -
                ordenTerminalUnidad(b)
        );
    }


    function etiquetaUnidadTerminal(
        terminal
    ) {

        const unidad =
            unidadPorTerminal(
                terminal
            );

        return `
            <span
                class="
                    unidad-terminal-badge
                    unidad-${unidad.codigo.toLowerCase()}
                ">
                ${escapeHtml(
                    unidad.texto
                )}
            </span>
        `;
    }


    function renderGraficoTerminales(filas) {

        const contenedor =
            $("graficoTerminales");


        if (!contenedor) {
            return;
        }


        const terminales =
            ordenarPorUnidadTerminal(
                Array.isArray(filas)
                ? filas
                : []
            );


        if (!terminales.length) {

            contenedor.innerHTML =
                `
                <div class="empty-support">
                    Sin información.
                </div>
                `;

            return;
        }


        contenedor.innerHTML =
            terminales
            .map(
                fila => {

                    const asignada =
                        Math.max(
                            numero(
                                fila.asignada
                            ),
                            0
                        );


                    const operativa =
                        Math.max(
                            numero(
                                fila.operativa
                            ),
                            0
                        );


                    const sinTx =
                        Math.max(
                            numero(
                                fila.sin_transmision
                            ),
                            0
                        );


                    const pctOperativa =
                        asignada > 0
                        ?
                        (
                            operativa
                            /
                            asignada
                        )
                        *
                        100
                        :
                        0;


                    const pctSinTx =
                        asignada > 0
                        ?
                        (
                            sinTx
                            /
                            asignada
                        )
                        *
                        100
                        :
                        0;


                    return `
                    <div class="terminal-bar-row">

                        <div class="terminal-bar-header">

                            <strong>
                                ${escapeHtml(fila.terminal_nombre)}
                                ${etiquetaUnidadTerminal(
                                    fila.terminal
                                    ||
                                    fila.terminal_nombre
                                )}
                            </strong>

                            <span>
                                ${operativa}/${asignada}
                                ?
                                ${porcentaje(fila.porcentaje_operativa)}
                            </span>

                        </div>


                        <div class="terminal-bar-track">

                            <div
                                class="terminal-bar-working"
                                style="width:${pctOperativa.toFixed(2)}%">
                            </div>

                            <div
                                class="terminal-bar-not-working"
                                style="width:${pctSinTx.toFixed(2)}%">
                            </div>

                        </div>


                        <div class="terminal-bar-footer">

                            <span>
                                Trabajando
                                <strong>${operativa}</strong>
                            </span>

                            <span>
                                No trabajando
                                <strong>${sinTx}</strong>
                            </span>

                        </div>

                    </div>
                    `;
                }
            )
            .join("");
    }



    // ================================================================
    // TABLA GLOBAL TERMINALES
    // ================================================================

    function renderTerminales(
        filas,
        total
    ) {

        const ordenadas =
            ordenarPorUnidadTerminal(
                filas
            );


        $("countTerminal").textContent =
            (
                ordenadas.length
                +
                (
                    ordenadas.length === 1
                    ? " terminal"
                    : " terminales"
                )
            );


        if (!ordenadas.length) {

            $("tbodyTerminal").innerHTML =
                `
                <tr>
                    <td colspan="6" class="empty-cell">
                        Sin datos para la consulta.
                    </td>
                </tr>
                `;


            $("tfootTerminal").innerHTML =
                "";

            return;
        }


        $("tbodyTerminal").innerHTML =
            ordenadas
            .map(
                fila => {

                    const clase =
                        clasePorcentaje(
                            fila.porcentaje_operativa
                        );


                    const sinTx =
                        numero(
                            fila.sin_transmision
                        );


                    return `
                    <tr>

                        <td>
                            <div class="terminal-name">
                                <span>
                                    ${escapeHtml(
                                        fila.terminal_nombre
                                    )}
                                </span>

                                ${etiquetaUnidadTerminal(
                                    fila.terminal
                                    ||
                                    fila.terminal_nombre
                                )}
                            </div>
                        </td>

                        <td class="num">
                            ${numero(fila.asignada)}
                        </td>

                        <td class="num operative-number">
                            ${numero(fila.operativa)}
                        </td>

                        <td class="num">

                            <span class="missing-number">
                                ${sinTx}
                            </span>

                        </td>

                        <td class="num">

                            <span class="pct-badge ${clase}">
                                ${porcentaje(fila.porcentaje_operativa)}
                            </span>

                        </td>

                        <td>

                            <button
                                type="button"
                                class="btn-view-missing"
                                data-sintx-terminal="${escapeHtml(fila.terminal)}"
                                data-sintx-nombre="${escapeHtml(fila.terminal_nombre)}">

                                Ver ${sinTx} PPU

                            </button>

                        </td>

                    </tr>
                    `;
                }
            )
            .join("");


        $("tfootTerminal").innerHTML =
            `
            <tr>

                <td>
                    TOTAL
                </td>

                <td class="num">
                    ${numero(total.asignada)}
                </td>

                <td class="num">
                    ${numero(total.operativa)}
                </td>

                <td class="num">
                    ${numero(total.sin_transmision)}
                </td>

                <td class="num">
                    ${porcentaje(total.porcentaje_operativa)}
                </td>

                <td>

                    <button
                        type="button"
                        class="btn-view-all"
                        data-sintx-todos="1">

                        Ver todas

                    </button>

                </td>

            </tr>
            `;
    }




    // ================================================================
    // VISTA OPERACIONAL POR UNIDAD
    // ================================================================

    const TERMINALES_POR_UNIDAD = {

        U8: [
            "CONDELL",
            "EL RETIRO",
            "SANTA MARGARITA",
            "SANTA MARTA"
        ],

        U9: [
            "AGUIRRE LUCO",
            "JUANITA",
            "PIE ANDINO"
        ]
    };


    function normalizarTerminalUnidad(valor) {

        return String(
            valor ?? ""
        )
        .trim()
        .toUpperCase();
    }


    function porcentajeUnidad(
        operativa,
        asignada
    ) {

        const total = Number(
            asignada || 0
        );

        if (!total) {
            return 0;
        }

        return (
            Number(
                operativa || 0
            )
            /
            total
            *
            100
        );
    }


    function clasePorcentajeUnidad(valor) {

        const porcentaje = Number(
            valor || 0
        );

        if (porcentaje >= 75) {
            return "unidad-estado-bueno";
        }

        if (porcentaje >= 50) {
            return "unidad-estado-medio";
        }

        return "unidad-estado-bajo";
    }


    function buscarResumenUnidad(
        datos,
        unidad
    ) {

        return (
            (
                datos.resumen_unidades
                ||
                []
            )
            .find(
                fila =>
                    String(
                        fila.unidad ?? ""
                    )
                    .trim()
                    .toUpperCase()
                    === unidad
            )
            ||
            {
                unidad: unidad,
                asignada: 0,
                operativa: 0,
                sin_transmision: 0,
                porcentaje_operativa: 0
            }
        );
    }


    function buscarCoberturaUnidad(
        datos,
        unidad
    ) {

        return (
            (
                datos.cobertura_fuente
                ||
                []
            )
            .find(
                fila =>
                    String(
                        fila.unidad ?? ""
                    )
                    .trim()
                    .toUpperCase()
                    === unidad
            )
            ||
            null
        );
    }


    function terminalPerteneceUnidad(
        terminal,
        unidad
    ) {

        const codigo = normalizarTerminalUnidad(
            terminal
        );

        return (
            TERMINALES_POR_UNIDAD[
                unidad
            ]
            ||
            []
        )
        .includes(
            codigo
        );
    }


    function renderVistaOperacionPorUnidad(
        datos
    ) {

        renderUnidadOperacion(
            "U8",
            datos
        );

        renderUnidadOperacion(
            "U9",
            datos
        );
    }


    function renderUnidadOperacion(
        unidad,
        datos
    ) {

        const sufijo =
            unidad === "U8"
                ? "U8"
                : "U9";


        const resumen = buscarResumenUnidad(
            datos,
            unidad
        );


        // ------------------------------------------------------------
        // KPI
        // ------------------------------------------------------------

        const kpis =
            $(
                `kpisUnidad${sufijo}`
            );

        if (kpis) {

            const porcentaje = Number(
                resumen.porcentaje_operativa
                ||
                porcentajeUnidad(
                    resumen.operativa,
                    resumen.asignada
                )
            );

            kpis.innerHTML = `

                <div class="unidad-kpi">

                    <span>
                        Flota asignada
                    </span>

                    <strong>
                        ${numero(
                            resumen.asignada
                        )}
                    </strong>

                </div>


                <div class="unidad-kpi unidad-kpi-operativa">

                    <span>
                        Trabajando
                    </span>

                    <strong>
                        ${numero(
                            resumen.operativa
                        )}
                    </strong>

                </div>


                <div class="unidad-kpi unidad-kpi-sin">

                    <span>
                        No trabajando
                    </span>

                    <strong>
                        ${numero(
                            resumen.sin_transmision
                        )}
                    </strong>

                </div>


                <div class="
                    unidad-kpi
                    unidad-kpi-porcentaje
                    ${clasePorcentajeUnidad(
                        porcentaje
                    )}
                ">

                    <span>
                        % Operativa
                    </span>

                    <strong>
                        ${porcentaje.toFixed(2)}%
                    </strong>

                </div>
            `;
        }


        // ------------------------------------------------------------
        // COBERTURA R1.6
        // ------------------------------------------------------------

        const coberturaElemento =
            $(
                `coberturaUnidad${sufijo}`
            );

        const cobertura = buscarCoberturaUnidad(
            datos,
            unidad
        );

        if (coberturaElemento) {

            if (!cobertura) {

                coberturaElemento.textContent =
                    "Sin cobertura R1.6";

                coberturaElemento.className =
                    "unidad-cobertura unidad-cobertura-pendiente";

            } else {

                const desde =
                    cobertura.desde
                    ||
                    cobertura.primera_transmision
                    ||
                    "--:--";

                const hasta =
                    cobertura.hasta
                    ||
                    cobertura.ultima_transmision
                    ||
                    "--:--";

                const completa =
                    cobertura.completa
                    === true;

                coberturaElemento.innerHTML = `
                    <span>
                        R1.6
                    </span>
                    <strong>
                        ${desde} ? ${hasta}
                    </strong>
                    <small>
                        ${
                            completa
                                ? "Cobertura completa"
                                : "Cobertura parcial"
                        }
                    </small>
                `;

                coberturaElemento.className =
                    completa
                        ? "unidad-cobertura unidad-cobertura-ok"
                        : "unidad-cobertura unidad-cobertura-parcial";
            }
        }


        // ------------------------------------------------------------
        // TERMINALES GLOBAL
        // ------------------------------------------------------------

        const terminales = (
            datos.resumen_terminal_global
            ||
            []
        )
        .filter(
            fila =>
                terminalPerteneceUnidad(
                    fila.terminal,
                    unidad
                )
        );


        const terminalesElemento =
            $(
                `terminalesUnidad${sufijo}`
            );

        if (terminalesElemento) {

            if (!terminales.length) {

                terminalesElemento.innerHTML = `
                    <div class="empty-support">
                        Sin información para ${unidad}.
                    </div>
                `;

            } else {

                terminalesElemento.innerHTML =
                    terminales
                    .map(
                        fila => {

                            const porcentaje =
                                Number(
                                    fila.porcentaje_operativa
                                    ||
                                    0
                                );

                            return `

                                <div class="unidad-terminal-fila">

                                    <div class="unidad-terminal-nombre">

                                        <strong>
                                            ${
                                                fila.terminal_nombre
                                                ||
                                                fila.terminal
                                            }
                                        </strong>

                                        <span>
                                            ${
                                                numero(
                                                    fila.operativa
                                                )
                                            }
                                            trabajando de
                                            ${
                                                numero(
                                                    fila.asignada
                                                )
                                            }
                                        </span>

                                    </div>


                                    <div class="unidad-terminal-barra">

                                        <div
                                            class="unidad-terminal-barra-activa"
                                            style="
                                                width:
                                                ${
                                                    Math.max(
                                                        0,
                                                        Math.min(
                                                            100,
                                                            porcentaje
                                                        )
                                                    )
                                                }%;
                                            ">
                                        </div>

                                    </div>


                                    <div class="
                                        unidad-terminal-porcentaje
                                        ${
                                            clasePorcentajeUnidad(
                                                porcentaje
                                            )
                                        }
                                    ">

                                        ${porcentaje.toFixed(2)}%

                                    </div>

                                </div>
                            `;
                        }
                    )
                    .join("");
            }
        }


        // ------------------------------------------------------------
        // MATRIZ P01-P24
        // ------------------------------------------------------------

        const filasPeriodo = (
            datos.resumen_terminal
            ||
            []
        )
        .filter(
            fila =>
                terminalPerteneceUnidad(
                    fila.terminal,
                    unidad
                )
        );

        renderMatrizUnidad(
            unidad,
            filasPeriodo,
            terminales
        );
    }



    // ================================================================
    // R8F2 - DETALLE PPU OPERATIVAS POR TERMINAL / SERVICIO
    // ================================================================

    async function abrirDetalleOperativas(
        terminal,
        unidad
    ) {

        const fechaDesde =
            $("fechaDesde").value;

        const fechaHasta =
            $("fechaHasta").value;

        const periodoInicial =
            Number(
                $("periodoInicial").value
                ||
                1
            );

        const periodoFinal =
            Number(
                $("periodoFinal").value
                ||
                24
            );


        // ------------------------------------------------------------
        // MODAL
        // ------------------------------------------------------------

        // R8F:
        // Ver PPU debe mostrar exclusivamente la flota operativa real.
        // Cerramos cualquier modal de "sin transmisi?n" que pudiera
        // estar visible antes de abrir este detalle.

        for (const idModal of [
            "modalSinTx",
            "modalSinTxDias"
        ]) {

            const modalAnterior =
                $(idModal);

            if (modalAnterior) {

                modalAnterior.classList.add(
                    "hidden"
                );

                modalAnterior.setAttribute(
                    "aria-hidden",
                    "true"
                );
            }
        }

        document.body.classList.remove(
            "modal-open"
        );

        let modal =
            $("modalPpuOperativas");


        if (!modal) {

            modal =
                document.createElement(
                    "div"
                );

            modal.id =
                "modalPpuOperativas";

            modal.className =
                "ppu-operativas-overlay hidden";

            modal.innerHTML = `
                <div class="ppu-operativas-modal">

                    <div class="ppu-operativas-header">

                        <div>
                            <span class="modal-kicker">
                                FLOTA OPERATIVA REAL
                            </span>

                            <h3 id="ppuOperativasTitulo">
                                PPU en la calle
                            </h3>

                            <p id="ppuOperativasSubtitulo">
                            </p>
                        </div>

                        <button
                            type="button"
                            id="cerrarPpuOperativas"
                            class="ppu-operativas-cerrar"
                            aria-label="Cerrar">
                            &times;
                        </button>

                    </div>

                    <div class="ppu-operativas-resumen">

                        <strong id="ppuOperativasTotal">
                            Consultando...
                        </strong>

                        <span>
                            PPU con transmisi\u00F3n R1.6
                        </span>

                    </div>

                    <div class="ppu-operativas-tabla-wrap">

                        <table class="data-table ppu-operativas-tabla">

                            <thead>
                                <tr>
                                    <th>PPU</th>
                                    <th>Servicio</th>
                                    <th>Per\u00EDodo</th>
                                    <th>Primera transmisi\u00F3n</th>
                                    <th>\u00DAltima transmisi\u00F3n</th>
                                </tr>
                            </thead>

                            <tbody id="tbodyPpuOperativas">
                                <tr>
                                    <td
                                        colspan="5"
                                        class="empty-cell">
                                        Consultando PPU...
                                    </td>
                                </tr>
                            </tbody>

                        </table>

                    </div>

                </div>
            `;

            document.body.appendChild(
                modal
            );

            $("cerrarPpuOperativas")
                .addEventListener(
                    "click",
                    () => {
                        modal.classList.add(
                            "hidden"
                        );
                    }
                );

            modal.addEventListener(
                "click",
                evento => {

                    if (evento.target === modal) {

                        modal.classList.add(
                            "hidden"
                        );
                    }
                }
            );
        }


        modal.classList.remove(
            "hidden"
        );


        $("ppuOperativasTitulo").textContent =
            `${terminal} \u00B7 ${unidad}`;


        $("ppuOperativasSubtitulo").textContent =
            (
                `${fechaDesde} a ${fechaHasta}`
                +
                ` \u00B7 P${String(periodoInicial).padStart(2, "0")}`
                +
                ` a P${String(periodoFinal).padStart(2, "0")}`
            );


        const tbody =
            $("tbodyPpuOperativas");


        tbody.innerHTML = `
            <tr>
                <td
                    colspan="5"
                    class="empty-cell">
                    Consultando PPU y servicios...
                </td>
            </tr>
        `;


        // ------------------------------------------------------------
        // GENERAR FECHAS
        // ------------------------------------------------------------

        function fechasEntre(
            desde,
            hasta
        ) {

            const salida = [];

            const partesDesde =
                desde.split("-")
                .map(Number);

            const partesHasta =
                hasta.split("-")
                .map(Number);

            let actual =
                new Date(
                    Date.UTC(
                        partesDesde[0],
                        partesDesde[1] - 1,
                        partesDesde[2]
                    )
                );

            const final =
                new Date(
                    Date.UTC(
                        partesHasta[0],
                        partesHasta[1] - 1,
                        partesHasta[2]
                    )
                );


            while (actual <= final) {

                salida.push(
                    actual
                        .toISOString()
                        .slice(0, 10)
                );

                actual.setUTCDate(
                    actual.getUTCDate() + 1
                );
            }

            return salida;
        }


        const fechas =
            fechasEntre(
                fechaDesde,
                fechaHasta
            );


        // ------------------------------------------------------------
        // CONSULTAR ENDPOINT DETALLE EXISTENTE
        // ------------------------------------------------------------

        const peticiones = [];


        for (const fecha of fechas) {

            for (
                let periodo = periodoInicial;
                periodo <= periodoFinal;
                periodo++
            ) {

                const params =
                    new URLSearchParams();

                params.set(
                    "fecha",
                    fecha
                );

                params.set(
                    "periodo",
                    String(periodo)
                );

                params.set(
                    "terminal",
                    terminal
                );

                if (unidad) {

                    params.set(
                        "unidad",
                        unidad
                    );
                }


                peticiones.push(
                    fetch(
                        `/api/flota-operativa/detalle?${params.toString()}`
                    )
                    .then(
                        async respuesta => {

                            if (!respuesta.ok) {
                                return [];
                            }

                            const datos =
                                await respuesta.json();

                            return (
                                datos.registros
                                ||
                                []
                            )
                            .map(
                                fila => ({
                                    ...fila,
                                    periodo_consulta:
                                        periodo,
                                    fecha_consulta:
                                        fecha
                                })
                            );
                        }
                    )
                    .catch(
                        () => []
                    )
                );
            }
        }


        const respuestas =
            await Promise.all(
                peticiones
            );


        const registros =
            respuestas.flat();


        // ------------------------------------------------------------
        // AGRUPAR PPU + SERVICIO
        // ------------------------------------------------------------

        const agrupados =
            new Map();


        for (const fila of registros) {

            const ppu =
                String(
                    fila.ppu
                    ||
                    ""
                )
                .trim();

            const servicio =
                String(
                    fila.servicio
                    ||
                    "-"
                )
                .trim();

            if (!ppu) {
                continue;
            }

            const clave =
                `${ppu}|||${servicio}`;


            if (!agrupados.has(clave)) {

                agrupados.set(
                    clave,
                    {
                        ppu,
                        servicio,
                        periodos:
                            new Set(),
                        primera:
                            fila.primera_transmision
                            ||
                            "",
                        ultima:
                            fila.ultima_transmision
                            ||
                            ""
                    }
                );
            }


            const item =
                agrupados.get(clave);


            item.periodos.add(
                Number(
                    fila.periodo_consulta
                )
            );


            const primera =
                fila.primera_transmision
                ||
                "";

            const ultima =
                fila.ultima_transmision
                ||
                "";


            if (
                primera
                &&
                (
                    !item.primera
                    ||
                    primera < item.primera
                )
            ) {
                item.primera =
                    primera;
            }


            if (
                ultima
                &&
                (
                    !item.ultima
                    ||
                    ultima > item.ultima
                )
            ) {
                item.ultima =
                    ultima;
            }
        }


        const filas =
            [...agrupados.values()]
            .sort(
                (a, b) => {

                    const porPpu =
                        a.ppu.localeCompare(
                            b.ppu
                        );

                    if (porPpu !== 0) {
                        return porPpu;
                    }

                    return a.servicio.localeCompare(
                        b.servicio
                    );
                }
            );


        const ppusUnicas =
            new Set(
                filas.map(
                    fila =>
                        fila.ppu
                )
            );


        $("ppuOperativasTotal").textContent =
            `${ppusUnicas.size} PPU en la calle`;


        if (!filas.length) {

            tbody.innerHTML = `
                <tr>
                    <td
                        colspan="5"
                        class="empty-cell">
                        Sin PPU transmitiendo
                        para esta terminal
                        en el rango seleccionado.
                    </td>
                </tr>
            `;

            return;
        }


        tbody.innerHTML =
            filas
            .map(
                fila => {

                    const periodos =
                        [...fila.periodos]
                        .sort(
                            (a, b) =>
                                a - b
                        )
                        .map(
                            periodo =>
                                `P${String(periodo).padStart(2, "0")}`
                        )
                        .join(", ");

                    return `
                        <tr>

                            <td>
                                <strong>
                                    ${escapeHtml(fila.ppu)}
                                </strong>
                            </td>

                            <td>
                                <strong>
                                    ${escapeHtml(fila.servicio)}
                                </strong>
                            </td>

                            <td>
                                ${escapeHtml(periodos)}
                            </td>

                            <td>
                                ${escapeHtml(
                                    fila.primera
                                    ||
                                    "-"
                                )}
                            </td>

                            <td>
                                ${escapeHtml(
                                    fila.ultima
                                    ||
                                    "-"
                                )}
                            </td>

                        </tr>
                    `;
                }
            )
            .join("");
    }


    function renderMatrizUnidad(
        unidad,
        filasPeriodo,
        filasGlobal
    ) {

        const sufijo =
            unidad === "U8"
                ? "U8"
                : "U9";

        const contenedor =
            $(
                `matrizUnidad${sufijo}`
            );

        if (!contenedor) {
            return;
        }


        const periodoInicial =
            Number(
                $("periodoInicial").value
                ||
                1
            );

        const periodoFinal =
            Number(
                $("periodoFinal").value
                ||
                24
            );


        // ------------------------------------------------------------
        // MAPA TERMINAL / PERIODO
        // ------------------------------------------------------------

        const mapa =
            new Map();

        for (
            const fila
            of filasPeriodo
        ) {

            const terminal =
                normalizarTerminalUnidad(
                    fila.terminal
                );

            const periodo =
                Number(
                    fila.periodo
                );

            if (
                !terminal
                ||
                !Number.isFinite(periodo)
            ) {
                continue;
            }

            if (!mapa.has(terminal)) {

                mapa.set(
                    terminal,
                    new Map()
                );
            }

            mapa
                .get(terminal)
                .set(
                    periodo,
                    Number(
                        fila.operativa
                        ||
                        0
                    )
                );
        }


        // ------------------------------------------------------------
        // CABECERA
        // ------------------------------------------------------------

        let cabecera = `
            <th class="sticky-terminal">
                Terminal
            </th>

            <th class="num sticky-asignada">
                Asignada
            </th>
        `;


        for (
            let periodo = 1;
            periodo <= 24;
            periodo++
        ) {

            const seleccionado =
                (
                    periodo >= periodoInicial
                    &&
                    periodo <= periodoFinal
                );

            cabecera += `
                <th
                    class="
                        num
                        periodo-col
                        ${
                            seleccionado
                                ? "periodo-seleccionado"
                                : "periodo-fuera-rango"
                        }
                    ">
                    P${String(periodo).padStart(2, "0")}
                </th>
            `;
        }


        cabecera += `
            <th class="num matriz-total-calle">
                <span>
                    TOTAL
                </span>
                <small>
                    BUSES EN LA CALLE
                </small>
            </th>

            <th class="num matriz-sin-tx">
                Sin transmisi\u00f3n
            </th>

            <th class="num">
                % Operativa
            </th>

            <th>
                Acci\u00f3n
            </th>
        `;


        // ------------------------------------------------------------
        // CUERPO
        // ------------------------------------------------------------

        let cuerpo = "";

        // ============================================================
        // R8E2 - TOTALES DE LA UNIDAD
        // ============================================================

        const totalesPeriodo =
            new Map();

        for (
            let periodo = 1;
            periodo <= 24;
            periodo++
        ) {

            totalesPeriodo.set(
                periodo,
                0
            );
        }

        let totalAsignada = 0;
        let totalSinTransmision = 0;
        let totalOperativaGlobal = 0;


        for (
            const global
            of filasGlobal
        ) {

            const terminalCodigo =
                normalizarTerminalUnidad(
                    global.terminal
                );

            const periodos =
                mapa.get(
                    terminalCodigo
                )
                ||
                new Map();


            let celdas = "";

            totalAsignada +=
                Number(
                    global.asignada
                    ||
                    0
                );

            totalSinTransmision +=
                Number(
                    global.sin_transmision
                    ||
                    0
                );

            totalOperativaGlobal +=
                Number(
                    global.operativa
                    ||
                    0
                );


            for (
                let periodo = 1;
                periodo <= 24;
                periodo++
            ) {

                const valor =
                    periodos.get(
                        periodo
                    )
                    ??
                    0;

                totalesPeriodo.set(
                    periodo,
                    Number(
                        totalesPeriodo.get(
                            periodo
                        )
                        ||
                        0
                    )
                    +
                    Number(valor)
                );

                const seleccionado =
                    (
                        periodo >= periodoInicial
                        &&
                        periodo <= periodoFinal
                    );

                celdas += `
                    <td
                        class="
                            num
                            periodo-col
                            ${
                                seleccionado
                                    ? "periodo-seleccionado"
                                    : "periodo-fuera-rango"
                            }
                        ">
                        <strong>
                            ${numero(valor)}
                        </strong>
                    </td>
                `;
            }


            cuerpo += `
                <tr>

                    <td class="sticky-terminal">
                        <strong>
                            ${escapeHtml(
                                global.terminal_nombre
                                ||
                                global.terminal
                            )}
                        </strong>
                    </td>

                    <td class="num sticky-asignada">
                        <strong>
                            ${numero(global.asignada)}
                        </strong>
                    </td>

                    ${celdas}

                    <td class="num matriz-total-calle">
                        <strong>
                            ${numero(
                                global.operativa
                            )}
                        </strong>
                    </td>

                    <td class="num matriz-sin-tx">
                        <strong>
                            ${numero(
                                global.sin_transmision
                            )}
                        </strong>
                    </td>

                    <td class="num">
                        <span
                            class="
                                pct-badge
                                ${clasePorcentaje(
                                    global.porcentaje_operativa
                                )}
                            ">
                            ${porcentaje(
                                global.porcentaje_operativa
                            )}
                        </span>
                    </td>

                    <td>
                        <button
                            type="button"
                            class="btn-view-missing"
                            data-operativa-terminal="${escapeHtml(
                                global.terminal
                            )}"
                            data-operativa-nombre="${escapeHtml(
                                global.terminal_nombre
                                ||
                                global.terminal
                            )}"
                            data-unidad="${escapeHtml(unidad)}">
                            Ver PPU
                            (${numero(global.operativa)})
                        </button>
                    </td>

                </tr>
            `;
        }


        // ============================================================
        // FILA TOTAL DE LA UNIDAD
        // ============================================================

        let celdasTotalesPeriodo = "";


        for (
            let periodo = 1;
            periodo <= 24;
            periodo++
        ) {

            const seleccionado =
                (
                    periodo >= periodoInicial
                    &&
                    periodo <= periodoFinal
                );

            celdasTotalesPeriodo += `
                <td
                    class="
                        num
                        periodo-col
                        total-periodo
                        ${
                            seleccionado
                                ? "periodo-seleccionado"
                                : "periodo-fuera-rango"
                        }
                    ">
                    <strong>
                        ${numero(
                            totalesPeriodo.get(periodo)
                            ||
                            0
                        )}
                    </strong>
                </td>
            `;
        }


        const porcentajeTotalUnidad =
            totalAsignada > 0
                ? (
                    totalOperativaGlobal
                    /
                    totalAsignada
                ) * 100
                : 0;


        const filaTotal = `
            <tr class="matriz-unidad-total">

                <td class="sticky-terminal">
                    <strong>
                        TOTAL ${unidad}
                    </strong>
                </td>

                <td class="num sticky-asignada">
                    <strong>
                        ${numero(totalAsignada)}
                    </strong>
                </td>

                ${celdasTotalesPeriodo}

                <td class="num matriz-total-calle">
                    <strong>
                        ${numero(totalOperativaGlobal)}
                    </strong>
                </td>

                <td class="num matriz-sin-tx">
                    <strong>
                        ${numero(totalSinTransmision)}
                    </strong>
                </td>

                <td class="num">
                    <span
                        class="
                            pct-badge
                            ${clasePorcentaje(
                                porcentajeTotalUnidad
                            )}
                        ">
                        ${porcentaje(
                            porcentajeTotalUnidad
                        )}
                    </span>
                </td>

                <td class="matriz-total-accion">
                    &mdash;
                </td>

            </tr>
        `;


        contenedor.innerHTML = `
            <table class="
                data-table
                matriz-unidad-table
                matriz-periodos-table
            ">

                <thead>
                    <tr>
                        ${cabecera}
                    </tr>
                </thead>

                <tbody>
                    ${
                        cuerpo
                        ||
                        `
                        <tr>
                            <td
                                colspan="29"
                                class="empty-cell">
                                Sin informaci\u00f3n.
                            </td>
                        </tr>
                        `
                    }
                    ${
                        filasGlobal.length
                            ? filaTotal
                            : ""
                    }

                </tbody>

            </table>
        `;


        // ------------------------------------------------------------
        // BOTON VER PPU
        // reutiliza exactamente el detalle existente
        // ------------------------------------------------------------

        contenedor
            .querySelectorAll(
                ".btn-view-missing"
            )
            .forEach(
                boton => {

                    boton.addEventListener(
                        "click",
                        () => {

                            const terminal =
                                boton.dataset.operativaTerminal
                                ||
                                "";

                            abrirDetalleOperativas(
                                terminal,
                                unidad
                            );
                        }
                    );
                }
            );
    }


    // ================================================================
    // MATRIZ TERMINAL x P01-P24
    // ================================================================

    function renderMatrizPeriodos(
        filasPeriodo,
        filasGlobal,
        totalGlobal
    ) {

        const thead =
            $("theadMatrizPeriodos");

        const tbody =
            $("tbodyMatrizPeriodos");

        const tfoot =
            $("tfootMatrizPeriodos");


        if (
            !thead ||
            !tbody ||
            !tfoot
        ) {
            return;
        }


        const periodoInicial =
            Number(
                $("periodoInicial").value
                ||
                1
            );

        const periodoFinal =
            Number(
                $("periodoFinal").value
                ||
                24
            );


        // ------------------------------------------------------------
        // CABECERA P01-P24
        // ------------------------------------------------------------

        let cabecera = `
            <th class="sticky-terminal">
                Terminal
            </th>

            <th class="matriz-unidad">
                Und.
            </th>

            <th class="num sticky-asignada">
                Asignada
            </th>
        `;


        for (
            let periodo = 1;
            periodo <= 24;
            periodo++
        ) {

            const seleccionado =
                (
                    periodo >= periodoInicial
                    &&
                    periodo <= periodoFinal
                );


            cabecera += `
                <th
                    class="
                        num
                        periodo-col
                        ${
                            seleccionado
                            ? "periodo-seleccionado"
                            : "periodo-fuera-rango"
                        }
                    ">

                    P${String(periodo).padStart(2, "0")}

                </th>
            `;
        }


        cabecera += `
            <th class="num matriz-sin-tx">
                Sin transmisión
            </th>

            <th class="num">
                % Operativa
            </th>

            <th>
                Acción
            </th>
        `;


        thead.innerHTML =
            cabecera;


        // ------------------------------------------------------------
        // MAPA GLOBAL POR TERMINAL
        // ------------------------------------------------------------

        const globalPorTerminal =
            new Map();


        for (
            const fila
            of filasGlobal
        ) {

            globalPorTerminal.set(
                String(
                    fila.terminal
                    ||
                    ""
                ).toUpperCase(),
                fila
            );
        }


        // ------------------------------------------------------------
        // MAPA TERMINAL / PERIODO
        // ------------------------------------------------------------

        const matriz =
            new Map();


        for (
            const fila
            of filasPeriodo
        ) {

            const terminal =
                String(
                    fila.terminal
                    ||
                    ""
                ).toUpperCase();


            const periodo =
                Number(
                    fila.periodo
                );


            if (
                !terminal
                ||
                !Number.isFinite(periodo)
            ) {
                continue;
            }


            if (!matriz.has(terminal)) {

                matriz.set(
                    terminal,
                    new Map()
                );
            }


            matriz
                .get(terminal)
                .set(
                    periodo,
                    numero(
                        fila.operativa
                    )
                );
        }


        // ------------------------------------------------------------
        // TERMINALES
        // ------------------------------------------------------------

        const terminales =
            ordenarPorUnidadTerminal(
                filasGlobal
            );


        if (!terminales.length) {

            tbody.innerHTML =
                `
                <tr>
                    <td
                        colspan="30"
                        class="empty-cell">

                        Sin datos para la consulta.

                    </td>
                </tr>
                `;

            tfoot.innerHTML =
                "";

            return;
        }


        // ------------------------------------------------------------
        // TOTALES POR PERIODO
        // ------------------------------------------------------------

        const totalesPeriodo =
            new Array(25).fill(0);


        let cuerpo =
            "";


        for (
            const global
            of terminales
        ) {

            const terminalCodigo =
                String(
                    global.terminal
                    ||
                    ""
                ).toUpperCase();


            const periodosTerminal =
                matriz.get(
                    terminalCodigo
                )
                ||
                new Map();


            let celdasPeriodo =
                "";


            for (
                let periodo = 1;
                periodo <= 24;
                periodo++
            ) {

                const valor =
                    numero(
                        periodosTerminal.get(periodo)
                        ||
                        0
                    );


                const seleccionado =
                    (
                        periodo >= periodoInicial
                        &&
                        periodo <= periodoFinal
                    );


                if (seleccionado) {

                    totalesPeriodo[periodo] +=
                        valor;
                }


                celdasPeriodo += `
                    <td
                        class="
                            num
                            periodo-value
                            ${
                                seleccionado
                                ? "periodo-seleccionado"
                                : "periodo-fuera-rango"
                            }
                        ">

                        ${
                            seleccionado
                            ? valor
                            : "?"
                        }

                    </td>
                `;
            }


            cuerpo += `
                <tr>

                    <td class="sticky-terminal">

                        <strong>
                            ${escapeHtml(global.terminal_nombre)}
                        </strong>

                    </td>

                    <td class="num sticky-asignada">

                        ${numero(global.asignada)}

                    </td>

                    ${celdasPeriodo}

                    <td class="num matriz-sin-tx">

                        <strong>
                            ${numero(global.sin_transmision)}
                        </strong>

                    </td>

                    <td class="num">

                        <span
                            class="
                                pct-badge
                                ${clasePorcentaje(global.porcentaje_operativa)}
                            ">

                            ${porcentaje(global.porcentaje_operativa)}

                        </span>

                    </td>

                    <td>

                        <button
                            type="button"
                            class="btn-view-missing"
                            data-sintx-terminal="${escapeHtml(global.terminal)}"
                            data-sintx-nombre="${escapeHtml(global.terminal_nombre)}">

                            Ver PPU

                        </button>

                    </td>

                    <td class="matriz-unidad">
                        <span
                            class="unidad-terminal-mini">
                            ${escapeHtml(
                                unidadPorTerminal(
                                    global.terminal
                                    ||
                                    global.terminal_nombre
                                ).codigo
                            )}
                        </span>
                    </td>

                </tr>
            `;
        }


        tbody.innerHTML =
            cuerpo;


        // ------------------------------------------------------------
        // TOTAL
        // ------------------------------------------------------------

        let totalPeriodosHtml =
            "";


        for (
            let periodo = 1;
            periodo <= 24;
            periodo++
        ) {

            const seleccionado =
                (
                    periodo >= periodoInicial
                    &&
                    periodo <= periodoFinal
                );


            totalPeriodosHtml += `
                <td
                    class="
                        num
                        ${
                            seleccionado
                            ? "periodo-seleccionado"
                            : "periodo-fuera-rango"
                        }
                    ">

                    ${
                        seleccionado
                        ? totalesPeriodo[periodo]
                        : "?"
                    }

                </td>
            `;
        }


        tfoot.innerHTML =
            `
            <tr>

                <td class="sticky-terminal">
                    TOTAL
                </td>

                <td class="num sticky-asignada">

                    ${numero(totalGlobal.asignada)}

                </td>

                ${totalPeriodosHtml}

                <td class="num">

                    ${numero(totalGlobal.sin_transmision)}

                </td>

                <td class="num">

                    ${porcentaje(totalGlobal.porcentaje_operativa)}

                </td>

                <td>

                    <button
                        type="button"
                        class="btn-view-all"
                        data-sintx-todos="1">

                        Ver todas

                    </button>

                </td>

            </tr>
            `;


        const hora =
            $("ultimaActualizacionMatriz");


        if (hora) {

            hora.textContent =
                new Date()
                .toLocaleTimeString(
                    "es-CL",
                    {
                        hour12: false
                    }
                );
        }
    }



    // ================================================================
    // RANKING DE APOYO
    // ================================================================

    function renderRanking(filas) {

        const contenedor =
            $("rankingApoyo");

        if (!contenedor) {
            return;
        }


        // ============================================================
        // RELACION OFICIAL DEL MODULO FLOTA OPERATIVA
        // ============================================================

        const terminalesPorUnidad = {

            U8: [
                "CONDELL",
                "EL RETIRO",
                "SANTA MARGARITA",
                "SANTA MARTA"
            ],

            U9: [
                "AGUIRRE LUCO",
                "JUANITA",
                "PIE ANDINO"
            ]
        };


        const nombreUnidad = {
            U8: "ALFA",
            U9: "OMEGA"
        };


        const nombresTerminal = {

            "CONDELL":
                "Condell",

            "EL RETIRO":
                "El Retiro",

            "SANTA MARGARITA":
                "Santa Margarita",

            "SANTA MARTA":
                "Santa Marta",

            "AGUIRRE LUCO":
                "Aguirre Luco",

            "JUANITA":
                "Juanita",

            "PIE ANDINO":
                "Pie Andino"
        };


        function claveTerminal(valor) {

            return String(
                valor
                ??
                ""
            )
            .trim()
            .toUpperCase()
            .normalize("NFD")
            .replace(
                /[\u0300-\u036f]/g,
                ""
            )
            .replace(
                /\s+/g,
                " "
            );
        }


        function semaforo(porcentajeValor) {

            const valor =
                Number(
                    porcentajeValor
                    ??
                    0
                );

            if (valor < 5) {

                return {
                    clase: "apoyo-critico",
                    estado: "CR\u00cdTICO"
                };
            }

            if (valor < 12) {

                return {
                    clase: "apoyo-atencion",
                    estado: "ATENCI\u00d3N"
                };
            }

            return {
                clase: "apoyo-normal",
                estado: "NORMAL"
            };
        }


        // ============================================================
        // INDEXAR DATOS REALES POR TERMINAL
        // ============================================================

        const mapa =
            new Map();

        for (const fila of filas) {

            const clave =
                claveTerminal(
                    fila.terminal_nombre
                    ||
                    fila.terminal
                );

            if (!clave) {
                continue;
            }

            mapa.set(
                clave,
                fila
            );
        }


        function construirUnidad(unidad) {

            const terminalesEsperados =
                terminalesPorUnidad[unidad];

            const datosUnidad =
                terminalesEsperados
                .map(
                    terminal => {

                        const fila =
                            mapa.get(
                                terminal
                            );

                        if (!fila) {
                            return null;
                        }

                        return {
                            ...fila,
                            _terminalClave:
                                terminal
                        };
                    }
                )
                .filter(Boolean)
                .sort(
                    (a, b) => {

                        const pa =
                            Number(
                                a.porcentaje_operativa
                                ??
                                0
                            );

                        const pb =
                            Number(
                                b.porcentaje_operativa
                                ??
                                0
                            );

                        if (pa !== pb) {
                            return pa - pb;
                        }

                        return String(
                            a._terminalClave
                        ).localeCompare(
                            String(
                                b._terminalClave
                            ),
                            "es"
                        );
                    }
                );


            const tarjetas =
                datosUnidad
                .map(
                    (fila, indice) => {

                        const sem =
                            semaforo(
                                fila.porcentaje_operativa
                            );

                        const terminal =
                            nombresTerminal[
                                fila._terminalClave
                            ]
                            ||
                            fila.terminal_nombre
                            ||
                            fila.terminal;

                        return `
                            <article
                                class="
                                    apoyo-terminal-card
                                    ${sem.clase}
                                ">

                                <div class="apoyo-posicion">
                                    ${indice + 1}
                                </div>

                                <div class="apoyo-terminal-contenido">

                                    <div class="apoyo-terminal-titulo">

                                        <strong>
                                            ${escapeHtml(terminal)}
                                            ${unidad} \u00b7
                                            ${nombreUnidad[unidad]}
                                        </strong>

                                        <span>
                                            ${sem.estado}
                                        </span>

                                    </div>

                                    <div class="apoyo-metricas">

                                        <div>
                                            <small>
                                                OPERATIVA
                                            </small>

                                            <strong>
                                                ${numero(fila.operativa)}
                                                /
                                                ${numero(fila.asignada)}
                                            </strong>
                                        </div>

                                        <div>
                                            <small>
                                                SIN TRANSMISI\u00d3N
                                            </small>

                                            <strong>
                                                ${numero(
                                                    fila.sin_transmision
                                                )}
                                            </strong>
                                        </div>

                                        <div>
                                            <small>
                                                % OPERATIVA
                                            </small>

                                            <strong>
                                                ${porcentaje(
                                                    fila.porcentaje_operativa
                                                )}
                                            </strong>
                                        </div>

                                    </div>

                                </div>

                            </article>
                        `;
                    }
                )
                .join("");


            return `
                <section
                    class="
                        apoyo-unidad
                        apoyo-unidad-${unidad.toLowerCase()}
                    ">

                    <div class="apoyo-unidad-header">

                        <span class="unidad-badge">
                            ${unidad}
                        </span>

                        <div>

                            <strong>
                                ${unidad} \u00b7
                                ${nombreUnidad[unidad]}
                            </strong>

                            <small>
                                ${
                                    terminalesEsperados
                                    .map(
                                        terminal =>
                                            nombresTerminal[terminal]
                                    )
                                    .join(" \u00b7 ")
                                }
                            </small>

                        </div>

                    </div>

                    <div class="apoyo-terminal-lista">

                        ${
                            tarjetas
                            ||
                            `
                            <div class="empty-support">
                                Sin informaci\u00f3n disponible.
                            </div>
                            `
                        }

                    </div>

                </section>
            `;
        }


        contenedor.innerHTML = `

            <div class="apoyo-unidades-grid">

                ${construirUnidad("U8")}

                ${construirUnidad("U9")}

            </div>

            <div class="apoyo-semaforo-leyenda">

                <span class="leyenda-critico">
                    <i></i>
                    <strong>Cr\u00edtico</strong>
                    &lt; 5 %
                </span>

                <span class="leyenda-atencion">
                    <i></i>
                    <strong>Atenci\u00f3n</strong>
                    5 % a &lt; 12 %
                </span>

                <span class="leyenda-normal">
                    <i></i>
                    <strong>Normal</strong>
                    \u2265 12 %
                </span>

            </div>
        `;
    }



    let detalleSinTxDiasActual = [];
    let terminalSinTxDiasActual = "";


    function renderSinTxDias(datos) {

        const resumen =
            datos.resumen_sin_transmision_dias
            ||
            [];

        detalleSinTxDiasActual =
            datos.sin_transmision_detalle_dias
            ||
            [];


        const tbody =
            $("tbodySinTxDias");

        const tfoot =
            $("tfootSinTxDias");


        if (!tbody) {
            return;
        }


        const rango =
            Number(
                datos.dias_rango_sin_transmision
                ||
                0
            );

        const evaluables =
            Number(
                datos.dias_evaluables_sin_transmision
                ||
                0
            );

        const sinDatos =
            Number(
                datos.dias_sin_datos_sin_transmision
                ||
                0
            );


        const elRango =
            $("sinTxDiasRango");

        const elEvaluables =
            $("sinTxDiasEvaluables");

        const elSinDatos =
            $("sinTxDiasSinDatos");


        if (elRango) {
            elRango.textContent = rango;
        }

        if (elEvaluables) {
            elEvaluables.textContent = evaluables;
        }

        if (elSinDatos) {
            elSinDatos.textContent = sinDatos;
        }


        const aviso =
            $("sinTxAvisoCobertura");


        if (aviso) {

            const fechasSinDatos =
                datos.fechas_sin_datos_sin_transmision
                ||
                [];

            if (fechasSinDatos.length > 0) {

                aviso.classList.remove(
                    "hidden"
                );

                aviso.innerHTML =
                    `
                    <strong>
                        Días sin información:
                    </strong>

                    ${fechasSinDatos
                        .map(fechaCL)
                        .join(", ")}.

                    No se consideran como
                    días sin transmisión.
                    `;

            } else {

                aviso.classList.add(
                    "hidden"
                );

                aviso.innerHTML = "";
            }
        }


        if (!resumen.length) {

            tbody.innerHTML =
                `
                <tr>
                    <td
                        colspan="6"
                        class="empty-cell">

                        Sin información para
                        la consulta seleccionada.

                    </td>
                </tr>
                `;

            if (tfoot) {
                tfoot.innerHTML = "";
            }

            return;
        }


        const resumenOrdenado =
            ordenarPorUnidadTerminal(
                resumen
            );

        tbody.innerHTML =
            resumenOrdenado
            .map(
                fila => {

                    const tipos =
                        (
                            fila.tipos_bus
                            ||
                            []
                        )
                        .map(
                            item =>
                                `
                                <span class="tipo-bus-chip">

                                    ${escapeHtml(
                                        item.tipo_bus
                                        ||
                                        "-"
                                    )}

                                    <strong>
                                        ${numero(
                                            item.cantidad
                                        )}
                                    </strong>

                                </span>
                                `
                        )
                        .join("");


                    return `
                        <tr>

                            <td>
                                <div class="terminal-name">
                                    <strong>
                                        ${escapeHtml(
                                            fila.terminal_nombre
                                            ||
                                            fila.terminal
                                            ||
                                            "-"
                                        )}
                                    </strong>

                                    ${etiquetaUnidadTerminal(
                                        fila.terminal
                                        ||
                                        fila.terminal_nombre
                                    )}
                                </div>
                            </td>


                            <td class="num">

                                ${numero(
                                    fila.total_ppu
                                )}

                            </td>


                            <td>

                                <div class="tipo-bus-list">
                                    ${tipos || "—"}
                                </div>

                            </td>


                            <td class="num">

                                <strong class="sin-tx-numero">
                                    ${numero(
                                        fila.sin_transmision
                                    )}
                                </strong>

                            </td>


                            <td class="num">

                                <strong class="sin-tx-porcentaje">

                                    ${porcentaje(
                                        fila.porcentaje_sin_transmision
                                        ||
                                        0
                                    )}

                                </strong>

                            </td>


                            <td>

                                <button
                                    type="button"
                                    class="btn-ver-sin-tx-dias"
                                    data-terminal="${escapeHtml(
                                        fila.terminal
                                        ||
                                        ""
                                    )}">

                                    Ver detalles
                                    (${numero(
                                        fila.sin_transmision
                                    )})

                                </button>

                            </td>

                        </tr>
                    `;
                }
            )
            .join("");


        const totalAsignada =
            resumen.reduce(
                (acum, fila) =>
                    acum
                    +
                    Number(
                        fila.total_ppu
                        ||
                        0
                    ),
                0
            );


        const totalSinTx =
            resumen.reduce(
                (acum, fila) =>
                    acum
                    +
                    Number(
                        fila.sin_transmision
                        ||
                        0
                    ),
                0
            );


        const pct =
            totalAsignada > 0
            ?
            (
                totalSinTx
                /
                totalAsignada
                *
                100
            )
            :
            0;


        if (tfoot) {

            tfoot.innerHTML =
            `
            <tr>

                <td>
                    <strong>TOTAL</strong>
                </td>

                <td class="num">
                    <strong>
                        ${numero(totalAsignada)}
                    </strong>
                </td>

                <td>—</td>

                <td class="num">
                    <strong>
                        ${numero(totalSinTx)}
                    </strong>
                </td>

                <td class="num">

                    <strong class="sin-tx-porcentaje">
                        ${porcentaje(pct)}
                    </strong>

                </td>

                <td>

                    <button
                        type="button"
                        class="btn-ver-sin-tx-dias"
                        data-terminal="">

                        Ver todos
                        (${numero(totalSinTx)})

                    </button>

                </td>

            </tr>
            `;

        }


        document
            .querySelectorAll(
                ".btn-ver-sin-tx-dias"
            )
            .forEach(
                boton => {

                    boton.addEventListener(
                        "click",
                        () => {

                            abrirDetalleSinTxDias(
                                boton.dataset.terminal
                                ||
                                ""
                            );
                        }
                    );
                }
            );
    }


    function abrirDetalleSinTxDias(
        terminal
    ) {

        // R8F:
        // Este detalle pertenece exclusivamente a "Sin transmisi?n".
        // Si estaba abierto Ver PPU, se cierra antes.

        const modalOperativas =
            $("modalPpuOperativas");

        if (modalOperativas) {

            modalOperativas.classList.add(
                "hidden"
            );

            modalOperativas.setAttribute(
                "aria-hidden",
                "true"
            );
        }

        terminalSinTxDiasActual =
            String(
                terminal
                ||
                ""
            )
            .trim()
            .toUpperCase();


        const filas =
            detalleSinTxDiasActual.filter(
                fila => {

                    if (!terminalSinTxDiasActual) {
                        return true;
                    }

                    return (
                        String(
                            fila.terminal
                            ||
                            ""
                        )
                        .trim()
                        .toUpperCase()
                        ===
                        terminalSinTxDiasActual
                    );
                }
            );


        let terminalNombre =
            "Todas las terminales";


        if (
            terminalSinTxDiasActual
            &&
            filas.length
        ) {

            terminalNombre =
                filas[0].terminal_nombre
                ||
                filas[0].terminal
                ||
                terminalSinTxDiasActual;
        }


        $("modalSinTxDiasSubtitulo")
            .textContent =
            (
                "Terminal: "
                +
                terminalNombre
                +
                " | Fecha: "
                +
                fechaCL(
                    $("fechaDesde").value
                )
                +
                (
                    $("fechaDesde").value
                    !==
                    $("fechaHasta").value
                    ?
                    (
                        " al "
                        +
                        fechaCL(
                            $("fechaHasta").value
                        )
                    )
                    :
                    ""
                )
            );


        $("buscarSinTxDias").value =
            "";


        cargarTiposBusSinTxDias(
            filas
        );


        renderDetalleSinTxDias();


        const modal =
            $("modalSinTxDias");


        modal.classList.remove(
            "hidden"
        );

        modal.setAttribute(
            "aria-hidden",
            "false"
        );
    }


    function filasDetalleSinTxDias() {

        let filas =
            [...detalleSinTxDiasActual];


        if (terminalSinTxDiasActual) {

            filas =
                filas.filter(
                    fila =>
                        String(
                            fila.terminal
                            ||
                            ""
                        )
                        .trim()
                        .toUpperCase()
                        ===
                        terminalSinTxDiasActual
                );
        }


        const buscar =
            String(
                $("buscarSinTxDias")?.value
                ||
                ""
            )
            .trim()
            .toUpperCase();


        const tipo =
            String(
                $("filtroTipoBusSinTxDias")?.value
                ||
                ""
            )
            .trim()
            .toUpperCase();


        if (buscar) {

            filas =
                filas.filter(
                    fila =>
                        String(
                            fila.ppu
                            ||
                            ""
                        )
                        .toUpperCase()
                        .includes(
                            buscar
                        )
                );
        }


        if (tipo) {

            filas =
                filas.filter(
                    fila =>
                        String(
                            fila.tipo_bus
                            ||
                            ""
                        )
                        .trim()
                        .toUpperCase()
                        ===
                        tipo
                );
        }


        return filas;
    }


    function cargarTiposBusSinTxDias(
        filas
    ) {

        const select =
            $("filtroTipoBusSinTxDias");


        const tipos =
            [
                ...new Set(
                    filas
                    .map(
                        fila =>
                            String(
                                fila.tipo_bus
                                ||
                                ""
                            )
                            .trim()
                    )
                    .filter(Boolean)
                )
            ]
            .sort();


        select.innerHTML =
            `
            <option value="">
                Todos los tipos de bus
            </option>
            `;


        tipos.forEach(
            tipo => {

                select.insertAdjacentHTML(
                    "beforeend",
                    `
                    <option value="${escapeHtml(tipo)}">
                        ${escapeHtml(tipo)}
                    </option>
                    `
                );
            }
        );
    }


    function renderDetalleSinTxDias() {

        const tbody =
            $("tbodyModalSinTxDias");


        const filas =
            filasDetalleSinTxDias();


        $("totalModalSinTxDias")
            .textContent =
            numero(
                filas.length
            );


        if (!filas.length) {

            tbody.innerHTML =
                `
                <tr>

                    <td
                        colspan="5"
                        class="empty-cell">

                        Sin PPU para los filtros
                        seleccionados.

                    </td>

                </tr>
                `;

            return;
        }


        tbody.innerHTML =
            filas
            .sort(
                (a, b) => {

                    const terminal =
                        String(
                            a.terminal_nombre
                            ||
                            ""
                        )
                        .localeCompare(
                            String(
                                b.terminal_nombre
                                ||
                                ""
                            ),
                            "es"
                        );

                    if (terminal !== 0) {
                        return terminal;
                    }

                    return (
                        Number(
                            b.dias_sin_transmision
                            ||
                            0
                        )
                        -
                        Number(
                            a.dias_sin_transmision
                            ||
                            0
                        )
                        ||
                        String(
                            a.ppu
                            ||
                            ""
                        )
                        .localeCompare(
                            String(
                                b.ppu
                                ||
                                ""
                            )
                        )
                    );
                }
            )
            .map(
                fila =>
                    `
                    <tr>

                        <td>
                            ${escapeHtml(
                                fila.terminal_nombre
                                ||
                                fila.terminal
                                ||
                                "-"
                            )}
                        </td>

                        <td>
                            <strong>
                                ${escapeHtml(
                                    fila.ppu
                                    ||
                                    "-"
                                )}
                            </strong>
                        </td>

                        <td>
                            ${escapeHtml(
                                fila.tipo_bus
                                ||
                                "-"
                            )}
                        </td>

                        <td class="num">

                            ${
                                fila.plazas !== null
                                &&
                                fila.plazas !== undefined
                                ?
                                numero(
                                    fila.plazas
                                )
                                :
                                "\u2014"
                            }

                        </td>

                        <td class="num">

                            <strong class="dias-sin-tx-badge">

                                ${numero(
                                    fila.dias_sin_transmision
                                )}

                            </strong>

                        </td>

                    </tr>
                    `
            )
            .join("");
    }


    function cerrarDetalleSinTxDias() {

        const modal =
            $("modalSinTxDias");

        if (!modal) {
            return;
        }

        modal.classList.add(
            "hidden"
        );

        modal.setAttribute(
            "aria-hidden",
            "true"
        );
    }





    // ================================================================
    // MODAL SIN TRANSMISION
    // ================================================================

    function abrirSinTransmision(
        terminalCodigo,
        terminalNombre
    ) {

        if (!datosActuales) {
            return;
        }


        let filas =
            datosActuales.sin_transmision_detalle
            ||
            [];


        if (terminalCodigo) {

            filas =
                filas.filter(
                    fila =>
                        String(
                            fila.terminal
                            ||
                            ""
                        )
                        .toUpperCase()
                        ===
                        String(
                            terminalCodigo
                        )
                        .toUpperCase()
                );
        }


        filas =
            [...filas]
            .sort(
                (a, b) =>
                    String(
                        a.ppu
                    )
                    .localeCompare(
                        String(
                            b.ppu
                        ),
                        "es"
                    )
            );


        $("modalTitulo").textContent =
            terminalNombre
            ? (
                "PPU sin transmisión — "
                +
                terminalNombre
            )
            : "PPU sin transmisión — Todas las terminales";


        const pi =
            periodoTexto(
                $("periodoInicial").value
            );


        const pf =
            periodoTexto(
                $("periodoFinal").value
            );


        $("modalSubtitulo").textContent =
            (
                fechaCL(
                    $("fechaDesde").value
                )
                +
                (
                    $("fechaDesde").value
                    !==
                    $("fechaHasta").value
                    ? (
                        " al "
                        +
                        fechaCL(
                            $("fechaHasta").value
                        )
                    )
                    : ""
                )
                +
                " · "
                +
                pi
                +
                " a "
                +
                pf
            );


        $("modalTotal").textContent =
            filas.length;


        if (!filas.length) {

            $("tbodySinTx").innerHTML =
                `
                <tr>
                    <td colspan="6" class="empty-cell">
                        No existen PPU sin transmisión para esta consulta.
                    </td>
                </tr>
                `;
        }
        else {

            $("tbodySinTx").innerHTML =
                filas
                .map(
                    fila => `
                    <tr>

                        <td>
                            <strong class="ppu-value">
                                ${escapeHtml(fila.ppu)}
                            </strong>
                        </td>

                        <td>
                            ${escapeHtml(fila.interno || "—")}
                        </td>

                        <td>
                            ${escapeHtml(fila.unidad || "—")}
                        </td>

                        <td>
                            ${escapeHtml(fila.terminal_nombre || fila.terminal || "—")}
                        </td>

                        <td>
                            ${escapeHtml(fila.tipo_bus || "—")}
                        </td>

                        <td>
                            ${escapeHtml(fila.tipo_flota || "—")}
                        </td>

                    </tr>
                    `
                )
                .join("");
        }


        const modal =
            $("modalSinTx");


        modal.classList.remove(
            "hidden"
        );


        modal.setAttribute(
            "aria-hidden",
            "false"
        );


        document.body.classList.add(
            "modal-open"
        );
    }


    function cerrarModal() {

        const modal =
            $("modalSinTx");


        modal.classList.add(
            "hidden"
        );


        modal.setAttribute(
            "aria-hidden",
            "true"
        );


        document.body.classList.remove(
            "modal-open"
        );
    }


    // ================================================================
    // EXPORTAR
    // ================================================================

    function exportar() {

        window.location.href =
            (
                "/api/flota-operativa/exportar-excel?"
                +
                queryParams().toString()
            );
    }


    // ================================================================
    // EVENTOS
    // ================================================================

    document.addEventListener(
        "click",
        event => {

            const botonSinTx =
                event.target.closest(
                    "[data-sintx-terminal]"
                );


            if (botonSinTx) {

                abrirSinTransmision(
                    botonSinTx.dataset.sintxTerminal,
                    botonSinTx.dataset.sintxNombre
                );

                return;
            }


            const botonTodos =
                event.target.closest(
                    "[data-sintx-todos]"
                );


            if (botonTodos) {

                abrirSinTransmision(
                    "",
                    ""
                );

                return;
            }
        }
    );


    $("btnConsultar")
        .addEventListener(
            "click",
            consultar
        );


    $("btnExportar")
        .addEventListener(
            "click",
            exportar
        );



    // ================================================================
    // EVENTOS SIN TX DIAS 20260910
    // ================================================================

    const btnCerrarSinTxDias =
        $("btnCerrarSinTxDias");

    if (btnCerrarSinTxDias) {

        btnCerrarSinTxDias.addEventListener(
            "click",
            cerrarDetalleSinTxDias
        );
    }


    const buscarSinTxDias =
        $("buscarSinTxDias");

    if (buscarSinTxDias) {

        buscarSinTxDias.addEventListener(
            "input",
            renderDetalleSinTxDias
        );
    }


    const filtroTipoBusSinTxDias =
        $("filtroTipoBusSinTxDias");

    if (filtroTipoBusSinTxDias) {

        filtroTipoBusSinTxDias.addEventListener(
            "change",
            renderDetalleSinTxDias
        );
    }


    const modalSinTxDias =
        $("modalSinTxDias");

    if (modalSinTxDias) {

        modalSinTxDias.addEventListener(
            "click",
            evento => {

                if (
                    evento.target
                    ===
                    modalSinTxDias
                ) {
                    cerrarDetalleSinTxDias();
                }
            }
        );
    }


    $("btnCerrarModal")
        .addEventListener(
            "click",
            cerrarModal
        );


    $("btnCerrarModalFooter")
        .addEventListener(
            "click",
            cerrarModal
        );


    $("modalSinTx")
        .addEventListener(
            "click",
            event => {

                if (
                    event.target
                    ===
                    $("modalSinTx")
                ) {

                    cerrarModal();
                }
            }
        );


    document.addEventListener(
        "keydown",
        event => {

            if (
                event.key
                ===
                "Escape"
            ) {

                cerrarModal();
            }
        }
    );


    // ================================================================
    // INICIO
    // ================================================================

    cargarFiltros()
        .then(
            consultar
        )
        .catch(
            error => {

                console.error(
                    error
                );

                alert(
                    error.message
                );
            }
        );


    // ================================================================
    // ACTUALIZACION AUTOMATICA
    // ================================================================

    const INTERVALO_ACTUALIZACION_MS =
        60 * 1000;


    setInterval(
        async () => {

            // No ejecutar si ya existe una consulta en proceso.

            if (
                document.body.classList.contains(
                    "is-loading"
                )
            ) {
                return;
            }


            try {

                const respuesta =
                    await fetch(
                        (
                            "/api/flota-operativa/consulta?"
                            +
                            queryParams().toString()
                            +
                            "&_ts="
                            +
                            Date.now()
                        ),
                        {
                            cache: "no-store"
                        }
                    );


                if (!respuesta.ok) {
                    return;
                }


                const datos =
                    await respuesta.json();


                datosActuales =
                    datos;


                render(
                    datos
                );

            }
            catch (error) {

                console.warn(
                    "Actualización automática Flota Operativa:",
                    error
                );
            }

        },
        INTERVALO_ACTUALIZACION_MS
    );



})();
