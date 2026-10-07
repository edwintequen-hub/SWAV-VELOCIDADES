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


        const btnExportar =
            $("btnExportar");

        if (btnExportar) {
            btnExportar.disabled =
                estado;
        }
    }


    // ================================================================
    // CONSULTA
    // ================================================================


    // ================================================================
    // MATRICES FLOTA U8/U9 PARA VISTA GENERAL
    // ================================================================

    async function completarMatricesFlota(
        datos
    ) {

        const unidadSeleccionada =
            String(
                $("unidad").value
                ||
                ""
            )
                .trim()
                .toUpperCase();

        // Si existe filtro de unidad, la respuesta principal
        // ya contiene la matriz individual certificada.
        if (unidadSeleccionada) {
            return datos;
        }

        const matricesFlota = {};

        await Promise.all(
            ["U8", "U9"].map(
                async unidadMatriz => {

                    const paramsUnidad =
                        queryParams({
                            unidad:
                                unidadMatriz
                        });

                    const respuestaUnidad =
                        await fetch(
                            (
                                "/api/flota-operativa/consulta?"
                                +
                                paramsUnidad.toString()
                                +
                                "&_ts="
                                +
                                Date.now()
                            ),
                            {
                                cache:
                                    "no-store"
                            }
                        );

                    if (!respuestaUnidad.ok) {
                        throw new Error(
                            "No fue posible cargar matriz "
                            +
                            unidadMatriz
                        );
                    }

                    const datosUnidad =
                        await respuestaUnidad.json();

                    const matrizUnidad =
                        datosUnidad.matriz_flota
                        ||
                        null;

                    if (
                        matrizUnidad
                        &&
                        String(
                            matrizUnidad.unidad
                            ||
                            ""
                        )
                            .trim()
                            .toUpperCase()
                        ===
                        unidadMatriz
                    ) {
                        matricesFlota[
                            unidadMatriz
                        ] =
                            matrizUnidad;
                    }
                }
            )
        );

        datos.matrices_flota =
            matricesFlota;

        return datos;
    }

    // ================================================================
    // R22-FRONTEND-ESTADO-AUTOMATICO
    // Estado informativo del scheduler.
    // No ejecuta descargas.
    // ================================================================

    function formatearHoraR22(valor) {

        if (!valor) {
            return "--";
        }

        const texto = String(valor);

        const coincidencia =
            texto.match(
                /(\d{2}):(\d{2}):(\d{2})/
            );

        if (!coincidencia) {
            return texto;
        }

        return (
            coincidencia[1]
            + ":"
            + coincidencia[2]
            + ":"
            + coincidencia[3]
        );
    }


    async function actualizarEstadoR22() {

        try {

            const respuesta =
                await fetch(
                    "/api/flota-operativa/r22/estado",
                    {
                        cache: "no-store"
                    }
                );

            if (!respuesta.ok) {
                throw new Error(
                    `HTTP ${respuesta.status}`
                );
            }

            const estado =
                await respuesta.json();

            const frecuencia =
                $("r22Frecuencia");

            const ultima =
                $("r22UltimaDescarga");

            const proxima =
                $("r22ProximaDescarga");

            const estadoU8 =
                $("r22EstadoU8");

            const estadoU9 =
                $("r22EstadoU9");

            const badge =
                $("r22EstadoBadge");


            if (frecuencia) {
                frecuencia.textContent =
                    estado.intervalo_minutos
                        ? `cada ${estado.intervalo_minutos} min`
                        : "--";
            }


            if (ultima) {
                ultima.textContent =
                    formatearHoraR22(
                        estado.ultima_ejecucion
                    );
            }


            if (proxima) {
                proxima.textContent =
                    formatearHoraR22(
                        estado.proxima_ejecucion
                    );
            }


            const resultados =
                estado.resultados || {};


            if (estadoU8) {
                estadoU8.textContent =
                    resultados.U8?.estado
                    || "--";
            }


            if (estadoU9) {
                estadoU9.textContent =
                    resultados.U9?.estado
                    || "--";
            }


            if (badge) {

                badge.classList.remove(
                    "fuente-estado-ok",
                    "fuente-estado-error",
                    "fuente-estado-espera"
                );

                if (
                    estado.activo
                    &&
                    !estado.ultimo_error
                ) {

                    badge.textContent =
                        estado.ejecutando
                            ? "ACTUALIZANDO"
                            : "AUTOMÁTICO ACTIVO";

                    badge.classList.add(
                        "fuente-estado-ok"
                    );

                }
                else {

                    badge.textContent =
                        "REVISAR";

                    badge.classList.add(
                        "fuente-estado-error"
                    );
                }
            }

        }
        catch (error) {

            console.error(
                "Estado R2.2:",
                error
            );

            const badge =
                $("r22EstadoBadge");

            if (badge) {

                badge.textContent =
                    "SIN CONEXIÓN";

                badge.classList.remove(
                    "fuente-estado-ok",
                    "fuente-estado-espera"
                );

                badge.classList.add(
                    "fuente-estado-error"
                );
            }
        }
    }


    async function consultar() {

        // R2.2 retirado del flujo activo.
        // Su codigo/backend se conserva como respaldo.

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


            await completarMatricesFlota(
                datos
            );


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

        try {

            renderAlertasPpu(
                datos.alertas_ppu
                ||
                {}
            );

        } catch (errorAlertasPpu) {

            console.error(
                "ERROR RENDER ALERTAS PPU:",
                errorAlertasPpu
            );
        }



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


    // ================================================================
    // R15H-G4D - ROTULO LIMPIO PARA TABLA SIN TX
    // FORMATO: U8 ALFA | Condell
    // ================================================================

    function etiquetaSinTxUnidadTerminal(
        terminal
    ) {

        const unidad =
            unidadPorTerminal(
                terminal
            );

        const unidadTexto = String(
            unidad.texto
            || unidad.codigo
            || ""
        )
            .replace(/\?/g, " ")
            .replace(/\s+/g, " ")
            .trim();

        const terminalTexto = String(
            terminal
            || "-"
        ).trim();

        return `
            <strong class="terminal-name-clean">
                ${escapeHtml(
                    unidadTexto
                )}
                |
                ${escapeHtml(
                    terminalTexto
                )}
            </strong>
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

        // Reporte operacional independiente.
        // No modifica la matriz de Flota/R2.2.
        cargarComercialR16Unidad(
            "U8"
        );

        cargarComercialR16Unidad(
            "U9"
        );
    }



    // ================================================================
    // COMERCIAL-R16-HISTORICO-FRONTEND
    // Salidas comerciales desde historico persistido en BD.
    // Independiente de la matriz Flota/R2.2.
    // ================================================================

    const comercialR16Estado = {
        U8: {
            cargando: false,
            clave: "",
            fechas: null,
            ultimaFecha: ""
        },
        U9: {
            cargando: false,
            clave: "",
            fechas: null,
            ultimaFecha: ""
        }
    };


    // SWAV-19C4H-FECHA-COMERCIAL
    function fechaComercialR16Seleccionada(
        unidad
    ) {
        const control =
            $(`comercialR16Fecha${unidad}`);

        const fecha =
            control
                ? control.value
                : "";

        if (!fecha) {
            return {
                fecha: "",
                error:
                    "Seleccione una fecha del histórico R1.6."
            };
        }

        return {
            fecha,
            error: ""
        };
    }


    async function obtenerFechasComercialR16(
        unidad,
        forzar = false
    ) {
        const estadoUnidad =
            comercialR16Estado[
                unidad
            ];

        if (
            !forzar
            &&
            estadoUnidad.fechas
            instanceof Set
        ) {
            return estadoUnidad;
        }

        const params =
            new URLSearchParams({
                unidad:
                    unidad
            });

        const respuesta =
            await fetch(
                `/api/flota-operativa/comercial-r16/fechas?${params.toString()}`
            );

        const datos =
            await respuesta.json();

        if (!respuesta.ok) {
            throw new Error(
                datos.detail
                ||
                "No fue posible consultar las fechas históricas R1.6."
            );
        }

        const fechas =
            Array.isArray(
                datos.fechas
            )
                ? datos.fechas
                    .map(
                        fila =>
                            String(
                                fila.fecha
                                ||
                                ""
                            )
                    )
                    .filter(Boolean)
                : [];

        estadoUnidad.fechas =
            new Set(
                fechas
            );

        estadoUnidad.ultimaFecha =
            fechas.length
                ? fechas[0]
                : "";

        return estadoUnidad;
    }


    function mensajeFechaNoDisponibleComercialR16(
        unidad,
        fecha
    ) {
        const ultima =
            comercialR16Estado[
                unidad
            ].ultimaFecha;

        return (
            `Sin histórico R1.6 disponible para ${fecha}.`
            +
            (
                ultima
                    ? ` Última fecha disponible: ${ultima}.`
                    : ""
            )
        );
    }


    function actualizarBotonExcelComercialR16(
        unidad,
        habilitado
    ) {
        const boton =
            $(
                `btnComercialR16Excel${unidad}`
            );

        if (!boton) {
            return;
        }

        boton.disabled =
            !habilitado;

        boton.title =
            habilitado
                ? "Descargar reporte diario R1.6"
                : "No existe histórico R1.6 para la fecha seleccionada";
    }




    function textoCoberturaComercialR16(
        datos
    ) {
        const estado =
            String(
                datos.estado_cobertura
                ||
                ""
            );

        const corte =
            datos.corte_r16
                ? String(
                    datos.corte_r16
                )
                : "";

        if (
            estado ===
            "PARCIAL_O_POR_CERTIFICAR"
        ) {
            return (
                "Cobertura parcial o por certificar"
                +
                (
                    corte
                        ? ` ? Corte R1.6: ${escapeComercialR16(corte)}`
                        : ""
                )
            );
        }

        if (estado) {
            return (
                escapeComercialR16(
                    estado
                )
                +
                (
                    corte
                        ? ` ? Corte R1.6: ${escapeComercialR16(corte)}`
                        : ""
                )
            );
        }

        return (
            corte
                ? `Corte R1.6: ${escapeComercialR16(corte)}`
                : "Cobertura sin informaci?n."
        );
    }

    function renderResumenComercialR16(
        unidad,
        datos
    ) {
        const contenedor =
            $(
                `comercialR16Resumen${unidad}`
            );

        if (!contenedor) {
            return;
        }

        const resumen =
            Array.isArray(
                datos.resumen_terminal
            )
                ? datos.resumen_terminal
                : [];

        const tarjetasTerminal =
            resumen
            .map(
                fila => {

                    const real =
                        Number(
                            fila.salidas_reales
                            ??
                            fila.real
                            ??
                            fila.total_real
                            ??
                            0
                        );

                    const perfil =
                        Number(
                            fila.perfil_comercial
                            ??
                            fila.perfil
                            ??
                            fila.total_perfil
                            ??
                            0
                        );

                    const diferencia =
                        Number(
                            fila.diferencia
                            ??
                            (
                                real
                                -
                                perfil
                            )
                        );

                    return `
                        <div class="comercial-r16-terminal-card">
                            <span>
                                ${escapeComercialR16(
                                    fila.terminal
                                    ||
                                    "-"
                                )}
                            </span>

                            <strong>
                                ${numeroComercialR16(real)}
                            </strong>

                            <small>
                                Perfil:
                                ${numeroComercialR16(perfil)}
                                ? Dif:
                                ${numeroComercialR16(diferencia)}
                            </small>
                        </div>
                    `;
                }
            )
            .join("");

        contenedor.innerHTML = `
            <div class="comercial-r16-kpis">

                <div class="comercial-r16-kpi">
                    <span>Salidas R1.6</span>
                    <strong>
                        ${numeroComercialR16(
                            datos.total_real
                        )}
                    </strong>
                </div>

                <div class="comercial-r16-kpi">
                    <span>Perfil Comercial</span>
                    <strong>
                        ${numeroComercialR16(
                            datos.total_perfil
                        )}
                    </strong>
                </div>

                <div class="comercial-r16-kpi">
                    <span>Diferencia</span>
                    <strong>
                        ${numeroComercialR16(
                            datos.total_diferencia
                            ??
                            (
                                Number(
                                    datos.total_real
                                    ||
                                    0
                                )
                                -
                                Number(
                                    datos.total_perfil
                                    ||
                                    0
                                )
                            )
                        )}
                    </strong>
                </div>

            </div>

            <div class="comercial-r16-terminales">
                ${tarjetasTerminal}
            </div>
        `;
    }

    function renderMatrizComercialR16(
        unidad,
        datos
    ) {
        const contenedor =
            $(
                `comercialR16Matriz${unidad}`
            );

        if (!contenedor) {
            return;
        }

        const filas =
            Array.isArray(
                datos.matriz_terminal
            )
                ? datos.matriz_terminal
                : [];

        if (!filas.length) {
            contenedor.innerHTML = `
                <div class="empty-cell">
                    Sin datos comerciales R1.6 para esta fecha.
                </div>
            `;
            return;
        }

        const periodos = [
            ...new Set(
                filas
                .map(
                    fila =>
                        String(
                            fila.periodo
                            ??
                            fila.periodo_30
                            ??
                            fila.periodo_1h
                            ??
                            ""
                        )
                )
                .filter(Boolean)
            )
        ]
        .sort();

        const terminales = [
            ...new Set(
                filas
                .map(
                    fila =>
                        String(
                            fila.terminal
                            ||
                            ""
                        )
                )
                .filter(Boolean)
            )
        ]
        .sort();

        const indice =
            new Map();

        filas.forEach(
            fila => {

                const terminal =
                    String(
                        fila.terminal
                        ||
                        ""
                    );

                const periodo =
                    String(
                        fila.periodo
                        ??
                        fila.periodo_30
                        ??
                        fila.periodo_1h
                        ??
                        ""
                    );

                indice.set(
                    `${terminal}|||${periodo}`,
                    fila
                );
            }
        );

        const cabeceraPeriodos =
            periodos
            .map(
                periodo => `
                    <th>
                        ${escapeComercialR16(periodo)}
                    </th>
                `
            )
            .join("");

        const cuerpo =
            terminales
            .map(
                terminal => {

                    let totalReal = 0;
                    let totalPerfil = 0;

                    const celdas =
                        periodos
                        .map(
                            periodo => {

                                const fila =
                                    indice.get(
                                        `${terminal}|||${periodo}`
                                    )
                                    ||
                                    {};

                                const real =
                                    Number(
                                        fila.salidas_reales
                                        ??
                                        fila.real
                                        ??
                                        0
                                    );

                                const perfil =
                                    Number(
                                        fila.perfil_comercial
                                        ??
                                        fila.perfil
                                        ??
                                        0
                                    );

                                totalReal += real;
                                totalPerfil += perfil;

                                return `
                                    <td class="comercial-r16-celda">
                                        <strong>
                                            ${numeroComercialR16(real)}
                                        </strong>
                                        <small>
                                            ${numeroComercialR16(perfil)}
                                        </small>
                                    </td>
                                `;
                            }
                        )
                        .join("");

                    return `
                        <tr>
                            <th class="comercial-r16-terminal">
                                ${escapeComercialR16(terminal)}
                            </th>

                            ${celdas}

                            <td class="comercial-r16-total">
                                <strong>
                                    ${numeroComercialR16(totalReal)}
                                </strong>
                                <small>
                                    ${numeroComercialR16(totalPerfil)}
                                </small>
                            </td>
                        </tr>
                    `;
                }
            )
            .join("");

        contenedor.innerHTML = `
            <div class="comercial-r16-leyenda">
                <strong>Valor superior:</strong>
                Salidas R1.6
                ?
                <strong>Valor inferior:</strong>
                Perfil Comercial
            </div>

            <table class="comercial-r16-tabla">
                <thead>
                    <tr>
                        <th>Terminal</th>
                        ${cabeceraPeriodos}
                        <th>Total</th>
                    </tr>
                </thead>

                <tbody>
                    ${cuerpo}
                </tbody>
            </table>
        `;
    }

    async function cargarComercialR16Unidad(
        unidad,
        forzar = false
    ) {
        const estado =
            $(
                `comercialR16Estado${unidad}`
            );

        const resumen =
            $(
                `comercialR16Resumen${unidad}`
            );

        const matriz =
            $(
                `comercialR16Matriz${unidad}`
            );

        if (
            !estado
            ||
            !resumen
            ||
            !matriz
        ) {
            return;
        }

        const seleccion =
            fechaComercialR16Seleccionada(unidad);

        if (seleccion.error) {

            estado.textContent =
                seleccion.error;

            resumen.innerHTML = "";
            matriz.innerHTML = "";

            comercialR16Estado[
                unidad
            ].clave = "";

            return;
        }

        const selector =
            $(
                `comercialR16Granularidad${unidad}`
            );

        const granularidad =
            selector
                ? selector.value
                : "30MIN";

        const clave =
            `${seleccion.fecha}|${granularidad}`;

        if (
            !forzar
            &&
            comercialR16Estado[
                unidad
            ].clave === clave
        ) {
            return;
        }

        if (
            comercialR16Estado[
                unidad
            ].cargando
        ) {
            return;
        }

        comercialR16Estado[
            unidad
        ].cargando = true;

        estado.textContent =
            "Validando fecha hist?rica R1.6...";

        resumen.innerHTML = "";
        matriz.innerHTML = "";

        actualizarBotonExcelComercialR16(
            unidad,
            false
        );

        try {

            const fechasDisponibles =
                await obtenerFechasComercialR16(
                    unidad
                );

            if (
                !fechasDisponibles.fechas.has(
                    seleccion.fecha
                )
            ) {
                const mensaje =
                    mensajeFechaNoDisponibleComercialR16(
                        unidad,
                        seleccion.fecha
                    );

                estado.textContent =
                    mensaje;

                resumen.innerHTML = "";

                matriz.innerHTML = `
                    <div class="empty-cell">
                        ${escapeHtml(
                            mensaje
                        )}
                    </div>
                `;

                comercialR16Estado[
                    unidad
                ].clave = "";

                return;
            }

            estado.textContent =
                "Cargando histórico comercial R1.6...";

            actualizarBotonExcelComercialR16(
                unidad,
                true
            );

            const params =
                new URLSearchParams({
                    fecha:
                        seleccion.fecha,
                    unidad:
                        unidad,
                    granularidad:
                        granularidad
                });

            const respuesta =
                await fetch(
                    `/api/flota-operativa/comercial-r16/reporte?${params.toString()}`
                );

            const datos =
                await respuesta.json();

            if (!respuesta.ok) {
                throw new Error(
                    datos.detail
                    ||
                    "No fue posible cargar el reporte comercial R1.6."
                );
            }

            comercialR16Estado[
                unidad
            ].clave = clave;

            estado.innerHTML = `
                <strong>
                    ${escapeHtml(
                        unidad
                    )}
                    ?
                    ${escapeHtml(
                        seleccion.fecha
                    )}
                    ?
                    ${escapeHtml(
                        granularidad
                    )}
                </strong>

                <span>
                    ${textoCoberturaComercialR16(
                        datos
                    )}
                </span>
            `;

            renderResumenComercialR16(
                unidad,
                datos
            );

            renderMatrizComercialR16(
                unidad,
                datos
            );

        }
        catch (error) {

            console.error(
                "ERROR COMERCIAL R1.6",
                unidad,
                error
            );

            estado.textContent =
                error.message;

            resumen.innerHTML = "";

            matriz.innerHTML = `
                <div class="empty-cell">
                    No fue posible cargar Salidas Comerciales R1.6.
                </div>
            `;

            comercialR16Estado[
                unidad
            ].clave = "";
        }
        finally {

            comercialR16Estado[
                unidad
            ].cargando = false;
        }
    }


    // SWAV-19C4L-DESCARGA-XLSX
    async function descargarExcelComercialR16(
        unidad
    ) {
        const seleccion =
            fechaComercialR16Seleccionada(unidad);

        if (seleccion.error) {
            alert(seleccion.error);
            return;
        }

        const boton =
            $(`btnComercialR16Excel${unidad}`);

        try {
            const fechasDisponibles =
                await obtenerFechasComercialR16(
                    unidad
                );

            if (
                !fechasDisponibles.fechas.has(
                    seleccion.fecha
                )
            ) {
                alert(
                    mensajeFechaNoDisponibleComercialR16(
                        unidad,
                        seleccion.fecha
                    )
                );

                actualizarBotonExcelComercialR16(
                    unidad,
                    false
                );

                return;
            }

            if (boton) {
                boton.disabled = true;
                boton.dataset.textoOriginal =
                    boton.textContent;

                boton.textContent =
                    "Generando Excel...";
            }

            const params =
                new URLSearchParams({
                    fecha:
                        seleccion.fecha,
                    unidad:
                        unidad
                });

            const url =
                `/api/flota-operativa/comercial-r16/exportar-excel?${params.toString()}`;

            console.log(
                "DESCARGA COMERCIAL R1.6:",
                url
            );

            const respuesta =
                await fetch(
                    url,
                    {
                        method: "GET",
                        cache: "no-store"
                    }
                );

            if (!respuesta.ok) {
                let detalle = "";

                try {
                    detalle =
                        await respuesta.text();
                }
                catch (_) {
                    detalle = "";
                }

                throw new Error(
                    `HTTP ${respuesta.status}`
                    +
                    (
                        detalle
                            ? ` - ${detalle}`
                            : ""
                    )
                );
            }

            const blob =
                await respuesta.blob();

            if (!blob || blob.size === 0) {
                throw new Error(
                    "El servidor devolvi? un archivo vac?o."
                );
            }

            let nombre =
                `REPORTE_COMERCIAL_R16_${unidad}_${seleccion.fecha}.xlsx`;

            const disposition =
                respuesta.headers.get(
                    "Content-Disposition"
                )
                ||
                "";

            const match =
                disposition.match(
                    /filename="?([^";]+)"?/i
                );

            if (
                match
                &&
                match[1]
            ) {
                nombre =
                    match[1].trim();
            }

            const blobUrl =
                URL.createObjectURL(
                    blob
                );

            const enlace =
                document.createElement(
                    "a"
                );

            enlace.href =
                blobUrl;

            enlace.download =
                nombre;

            enlace.style.display =
                "none";

            document.body.appendChild(
                enlace
            );

            enlace.click();

            enlace.remove();

            setTimeout(
                () => {
                    URL.revokeObjectURL(
                        blobUrl
                    );
                },
                1500
            );
        }
        catch (error) {
            console.error(
                "ERROR DESCARGANDO EXCEL COMERCIAL R1.6",
                unidad,
                error
            );

            alert(
                "No fue posible descargar el Excel comercial R1.6.\n\n"
                +
                (
                    error?.message
                    ||
                    String(error)
                )
            );
        }
        finally {
            if (boton) {
                boton.disabled = false;

                boton.textContent =
                    boton.dataset.textoOriginal
                    ||
                    "Descargar Excel";
            }
        }
    }


    async function prepararFechaComercialR16(
        unidad
    ) {
        const control =
            $(`comercialR16Fecha${unidad}`);

        if (!control) {
            return;
        }

        const disponibles =
            await obtenerFechasComercialR16(
                unidad
            );

        const fechas =
            disponibles.fechas;

        // SWAV-22C-FECHA-COMERCIAL-INDEPENDIENTE
        // Este m?dulo usa su propio hist?rico R1.6.
        // No hereda la fecha del filtro global de Flota.
        const fechaElegida =
            disponibles.ultimaFecha
            ||
            "";

        if (fechaElegida) {
            control.value =
                fechaElegida;
        }

        if (
            !control.dataset.comercialR16FechaEvento
        ) {
            control.dataset.comercialR16FechaEvento =
                "1";

            control.addEventListener(
                "change",
                () => {
                    cargarComercialR16Unidad(
                        unidad,
                        true
                    );
                }
            );
        }
    }


    function instalarEventosComercialR16() {

        for (
            const unidad
            of ["U8", "U9"]
        ) {
            const selector =
                $(
                    `comercialR16Granularidad${unidad}`
                );

            if (
                selector
                &&
                !selector.dataset.comercialR16Evento
            ) {
                selector.dataset.comercialR16Evento =
                    "1";

                selector.addEventListener(
                    "change",
                    () => {
                        cargarComercialR16Unidad(
                            unidad,
                            true
                        );
                    }
                );
            }

            const boton =
                $(
                    `btnComercialR16Excel${unidad}`
                );

            if (
                boton
                &&
                !boton.dataset.comercialR16Evento
            ) {
                boton.dataset.comercialR16Evento =
                    "1";

                boton.addEventListener(
                    "click",
                    () => {
                        descargarExcelComercialR16(
                            unidad
                        );
                    }
                );
            }
        }
    }


    instalarEventosComercialR16();

    Promise.all([
        prepararFechaComercialR16("U8"),
        prepararFechaComercialR16("U9")
    ])
    .then(() => {
        cargarComercialR16Unidad(
            "U8",
            true
        );

        cargarComercialR16Unidad(
            "U9",
            true
        );
    })
    .catch(error => {
        console.error(
            "ERROR PREPARANDO FECHAS COMERCIAL R1.6",
            error
        );
    });



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

        const prestamosResumen = (
            datos.prestamos_resumen
            ||
            []
        );

        window.__swavPrestamosDetalle = (
            datos.prestamos_detalle
            ||
            []
        );

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

                            const movimiento =
                                prestamosResumen.find(
                                    item =>
                                        String(
                                            item.terminal
                                            ||
                                            ""
                                        ).toUpperCase()
                                        ===
                                        String(
                                            fila.terminal
                                            ||
                                            ""
                                        ).toUpperCase()
                                )
                                ||
                                {};

                            const prestados =
                                Number(
                                    movimiento.prestados
                                    ||
                                    0
                                );

                            const recibidos =
                                Number(
                                    movimiento.recibidos
                                    ||
                                    0
                                );

                            const operativaAjustada =
                                Number(
                                    movimiento.operativa_ajustada
                                    ??
                                    fila.operativa
                                    ??
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

                                        <div class="prestamos-terminal-resumen">

                                            ${
                                                prestados > 0
                                                ? `
                                                <button
                                                    type="button"
                                                    class="
                                                        prestamo-chip
                                                        prestamo-chip-sale
                                                    "
                                                    data-prestamo-tipo="prestados"
                                                    data-prestamo-terminal="${escapeHtml(
                                                        fila.terminal
                                                    )}"
                                                    data-prestamo-unidad="${escapeHtml(
                                                        unidad
                                                    )}">
                                                    &#8593;
                                                    ${numero(prestados)}
                                                    Prestados
                                                </button>
                                                `
                                                : `
                                                <span
                                                    class="
                                                        prestamo-chip
                                                        prestamo-chip-neutro
                                                    ">
                                                    &#8593; 0 Prestados
                                                </span>
                                                `
                                            }

                                            ${
                                                recibidos > 0
                                                ? `
                                                <button
                                                    type="button"
                                                    class="
                                                        prestamo-chip
                                                        prestamo-chip-recibe
                                                    "
                                                    data-prestamo-tipo="recibidos"
                                                    data-prestamo-terminal="${escapeHtml(
                                                        fila.terminal
                                                    )}"
                                                    data-prestamo-unidad="${escapeHtml(
                                                        unidad
                                                    )}">
                                                    &#8595;
                                                    ${numero(recibidos)}
                                                    Recibidos
                                                </button>
                                                `
                                                : `
                                                <span
                                                    class="
                                                        prestamo-chip
                                                        prestamo-chip-neutro
                                                    ">
                                                    &#8595; 0 Recibidos
                                                </span>
                                                `
                                            }

                                            <span
                                                class="
                                                    prestamo-chip
                                                    prestamo-chip-ajustada
                                                ">
                                                Ajustada:
                                                ${numero(
                                                    operativaAjustada
                                                )}
                                            </span>

                                        </div>

                                    </div>


                                    <div class="unidad-terminal-barra">

                                        <div
                                            class="unidad-terminal-barra-activa ${porcentaje < 50 ? "barra-critico" : (porcentaje <= 80 ? "barra-atencion" : "barra-normal")}"
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

        // ============================================================
        // R13F - CORTE COBERTURA REAL R1.6
        //
        // El acumulado solamente se muestra hasta el periodo
        // alcanzado por el ultimo archivo R1.6 de la unidad.
        //
        // Ejemplo:
        // hasta 15:09 -> P16 visible -> P17-P24 sin cobertura.
        // ============================================================

        // ============================================================
        // R13F-R22 - COBERTURA REAL DE LA MATRIZ DE FLOTA
        //
        // Los valores acumulados de esta matriz provienen de R2.2.
        // Su corte temporal tambien debe provenir de cobertura_r22.
        //
        // La cobertura R1.6 permanece intacta para las otras vistas.
        // ============================================================

        const coberturaUnidad =
            (
                datos.cobertura_r22
                &&
                String(
                    datos.cobertura_r22.unidad
                    ||
                    ""
                )
                    .trim()
                    .toUpperCase()
                ===
                String(
                    unidad
                    ||
                    ""
                )
                    .trim()
                    .toUpperCase()
            )
                ? datos.cobertura_r22
                : null;


        const unidadNormalizada =
            String(
                unidad
                ||
                ""
            )
                .trim()
                .toUpperCase();

        const matrizFlotaIndividual =
            (
                datos.matriz_flota
                &&
                String(
                    datos.matriz_flota.unidad
                    ||
                    ""
                )
                    .trim()
                    .toUpperCase()
                ===
                unidadNormalizada
            )
                ? datos.matriz_flota
                : null;

        const matrizFlotaGeneral =
            (
                datos.matrices_flota
                &&
                datos.matrices_flota[
                    unidadNormalizada
                ]
            )
                ||
                null;

        const matrizFlotaUnidad =
            matrizFlotaIndividual
            ||
            matrizFlotaGeneral;


        let ultimoPeriodoCobertura = 0;

        if (coberturaUnidad) {

            const periodoR22 = Number(
                coberturaUnidad.ultimo_periodo
                ||
                0
            );

            if (
                Number.isInteger(periodoR22)
                &&
                periodoR22 >= 1
                &&
                periodoR22 <= 24
            ) {

                ultimoPeriodoCobertura =
                    periodoR22;
            }
        }

        if (
            ultimoPeriodoCobertura === 0
            &&
            matrizFlotaUnidad
        ) {

            const periodoMatriz = Number(
                matrizFlotaUnidad.ultimo_periodo_r22
                ||
                0
            );

            if (
                Number.isInteger(periodoMatriz)
                &&
                periodoMatriz >= 1
                &&
                periodoMatriz <= 24
            ) {

                ultimoPeriodoCobertura =
                    periodoMatriz;
            }
        }


        const periodoTieneCobertura = (
            periodo
        ) => {

            return (
                Number(periodo)
                <=
                ultimoPeriodoCobertura
            );
        };


        const filasPeriodo = (
            datos.resumen_terminal_acumulado
            ||
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
            ultimoPeriodoCobertura,
            terminales,
            matrizFlotaUnidad
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
        // Cerramos cualquier modal de "sin transmisión" que pudiera
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



    // ================================================================
    // PRUEBA VISUAL - REAL R1.6 VS PERFIL OPERACIONAL
    // Primera etapa: visualizacion por hora / 60 minutos
    // ================================================================

    async function renderMatrizRealVsPerfilUnidad(
        unidad,
        filasGlobal
    ) {

        const sufijo =
            unidad === "U8"
                ? "U8"
                : "U9";

        const contenedor =
            $(`matrizUnidad${sufijo}`);

        if (!contenedor) {
            return;
        }

        const fechaDesde =
            $("fechaDesde")
                ? $("fechaDesde").value
                : "";

        const fechaHasta =
            $("fechaHasta")
                ? $("fechaHasta").value
                : "";

        const fecha =
            fechaDesde
            ||
            fechaHasta;

        if (!fecha) {
            contenedor.innerHTML = `
                <div class="empty-cell">
                    Seleccione una fecha.
                </div>
            `;
            return;
        }

        if (
            fechaDesde
            &&
            fechaHasta
            &&
            fechaDesde !== fechaHasta
        ) {
            contenedor.innerHTML = `
                <div class="empty-cell">
                    Real vs Perfil requiere un solo día.
                    Seleccione la misma fecha Desde y Hasta.
                </div>
            `;
            return;
        }

        contenedor.innerHTML = `
            <div class="empty-cell">
                Cargando Real R1.6 vs Perfil...
            </div>
        `;

        try {

            const params =
                new URLSearchParams({
                    fecha: fecha,
                    unidad: unidad
                });

            const respuesta =
                await fetch(
                    `/api/flota-operativa/real-vs-perfil?${params.toString()}`
                );

            if (!respuesta.ok) {
                throw new Error(
                    `HTTP ${respuesta.status}`
                );
            }

            const datos =
                await respuesta.json();

            // --------------------------------------------------------
            // ESTADO VISUAL 60 / 30
            // --------------------------------------------------------

            const claveModo =
                `flotaRealPerfilModo_${unidad}`;

            let modo =
                sessionStorage.getItem(claveModo)
                ||
                "60";

            if (
                modo !== "60"
                &&
                modo !== "30"
            ) {
                modo = "60";
            }

            // --------------------------------------------------------
            // MODAL DETALLE R1.6
            // --------------------------------------------------------

            const abrirDetalleSalidas = (
                terminal,
                etiqueta,
                salidas
            ) => {

                const lista =
                    Array.isArray(salidas)
                        ? salidas
                        : [];

                const filasDetalle =
                    lista
                        .slice()
                        .sort(
                            (a, b) =>
                                String(
                                    a.inicio_servicio
                                    ||
                                    ""
                                ).localeCompare(
                                    String(
                                        b.inicio_servicio
                                        ||
                                        ""
                                    )
                                )
                        )
                        .map(
                            (x, indice) => {

                                const fechaHora =
                                    String(
                                        x.inicio_servicio
                                        ||
                                        ""
                                    );

                                const hora =
                                    fechaHora.includes(" ")
                                        ? fechaHora.split(" ")[1]
                                        : fechaHora;

                                return `
                                    <tr>
                                        <td class="num">
                                            ${indice + 1}
                                        </td>

                                        <td>
                                            <strong>
                                                ${escapeHtml(
                                                    x.patente
                                                    ||
                                                    "-"
                                                )}
                                            </strong>
                                        </td>

                                        <td>
                                            ${escapeHtml(
                                                x.servicio
                                                ||
                                                "-"
                                            )}
                                        </td>

                                        <td>
                                            ${escapeHtml(
                                                hora
                                                ||
                                                "-"
                                            )}
                                        </td>

                                        <td>
                                            ${escapeHtml(
                                                x.terminal
                                                ||
                                                terminal
                                            )}
                                        </td>
                                    </tr>
                                `;
                            }
                        )
                        .join("");

                const overlay =
                    document.createElement("div");

                overlay.className =
                    "detalle-salidas-r16-overlay";

                overlay.style.cssText = `
                    position:fixed;
                    inset:0;
                    z-index:99999;
                    background:rgba(0,0,0,.48);
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    padding:20px;
                `;

                overlay.innerHTML = `
                    <div style="
                        background:#fff;
                        width:min(900px,96vw);
                        max-height:88vh;
                        border-radius:14px;
                        box-shadow:0 18px 50px rgba(0,0,0,.25);
                        overflow:hidden;
                    ">

                        <div style="
                            display:flex;
                            justify-content:space-between;
                            align-items:center;
                            gap:20px;
                            padding:15px 18px;
                            border-bottom:1px solid #ddd;
                        ">

                            <div>
                                <strong>
                                    Salidas R1.6 ?
                                    ${escapeHtml(terminal)}
                                    ?
                                    ${escapeHtml(etiqueta)}
                                </strong>

                                <div style="
                                    margin-top:5px;
                                    font-size:12px;
                                    color:#555;
                                ">
                                    ${escapeHtml(fecha)}
                                    ?
                                    ${escapeHtml(unidad)}
                                    ?
                                    ${numero(lista.length)}
                                    salidas
                                </div>
                            </div>

                            <button
                                type="button"
                                class="cerrar-salidas-r16"
                                style="
                                    border:0;
                                    background:transparent;
                                    font-size:28px;
                                    cursor:pointer;
                                ">
                                &times;
                            </button>
                        </div>

                        <div style="
                            overflow:auto;
                            max-height:72vh;
                        ">
                            <table class="data-table">
                                <thead>
                                    <tr>
                                        <th class="num">#</th>
                                        <th>PPU</th>
                                        <th>Servicio</th>
                                        <th>Hora salida</th>
                                        <th>Terminal</th>
                                    </tr>
                                </thead>

                                <tbody>
                                    ${
                                        filasDetalle
                                        ||
                                        `
                                        <tr>
                                            <td
                                                colspan="5"
                                                class="empty-cell">
                                                Sin salidas.
                                            </td>
                                        </tr>
                                        `
                                    }
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;

                document.body.appendChild(
                    overlay
                );

                const cerrar = () =>
                    overlay.remove();

                overlay
                    .querySelector(
                        ".cerrar-salidas-r16"
                    )
                    .addEventListener(
                        "click",
                        cerrar
                    );

                overlay.addEventListener(
                    "click",
                    evento => {
                        if (
                            evento.target
                            ===
                            overlay
                        ) {
                            cerrar();
                        }
                    }
                );
            };

            // --------------------------------------------------------
            // RENDER INTERNO
            // --------------------------------------------------------

            const renderModo = () => {

                const es60 =
                    modo === "60";

                const filas =
                    es60
                        ? (
                            Array.isArray(datos.intervalos_60)
                                ? datos.intervalos_60
                                : []
                        )
                        : (
                            Array.isArray(datos.intervalos_30)
                                ? datos.intervalos_30
                                : []
                        );

                const resumen =
                    es60
                        ? (
                            Array.isArray(datos.resumen_terminal_60)
                                ? datos.resumen_terminal_60
                                : []
                        )
                        : (
                            Array.isArray(datos.resumen_terminal_30)
                                ? datos.resumen_terminal_30
                                : []
                        );

                const intervalos = [];

                if (es60) {

                    for (
                        let periodo = 1;
                        periodo <= 24;
                        periodo++
                    ) {
                        intervalos.push({
                            clave: String(periodo),
                            etiqueta:
                                `P${String(periodo).padStart(2, "0")}`
                        });
                    }

                } else {

                    for (
                        let hora = 0;
                        hora <= 23;
                        hora++
                    ) {

                        intervalos.push({
                            clave:
                                `${String(hora).padStart(2, "0")}:00`,
                            etiqueta:
                                `${String(hora).padStart(2, "0")}:00`
                        });

                        intervalos.push({
                            clave:
                                `${String(hora).padStart(2, "0")}:30`,
                            etiqueta:
                                `${String(hora).padStart(2, "0")}:30`
                        });
                    }
                }

                const mapa =
                    new Map();

                for (const fila of filas) {

                    const terminal =
                        normalizarTerminalUnidad(
                            fila.terminal
                        );

                    const clave =
                        es60
                            ? String(
                                Number(
                                    fila.periodo
                                )
                            )
                            : String(
                                fila.intervalo
                                ??
                                fila.media_hora
                                ??
                                fila.etiqueta
                                ??
                                ""
                            ).slice(0, 5);

                    if (
                        !terminal
                        ||
                        !clave
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
                            clave,
                            fila
                        );
                }

                // ----------------------------------------------------
                // TERMINALES = UNION DE DATOS + RESUMEN
                // ----------------------------------------------------

                const terminales =
                    new Map();

                for (const x of resumen) {

                    const codigo =
                        normalizarTerminalUnidad(
                            x.terminal
                        );

                    if (!codigo) {
                        continue;
                    }

                    terminales.set(
                        codigo,
                        {
                            codigo: codigo,
                            nombre:
                                x.terminal_nombre
                                ||
                                x.terminal
                        }
                    );
                }

                for (const codigo of mapa.keys()) {

                    if (!terminales.has(codigo)) {
                        terminales.set(
                            codigo,
                            {
                                codigo: codigo,
                                nombre: codigo
                            }
                        );
                    }
                }

                // ----------------------------------------------------
                // TOTALES GENERALES
                // ----------------------------------------------------

                const totalReal =
                    resumen.reduce(
                        (acc, x) =>
                            acc
                            +
                            Number(
                                x.real
                                ||
                                0
                            ),
                        0
                    );

                const totalPerfil =
                    resumen.reduce(
                        (acc, x) =>
                            acc
                            +
                            Number(
                                x.perfil
                                ||
                                0
                            ),
                        0
                    );

                const pctGeneral =
                    totalPerfil > 0
                        ? (
                            totalReal
                            /
                            totalPerfil
                        ) * 100
                        : null;

                // ----------------------------------------------------
                // CABECERA RESUMEN
                // ----------------------------------------------------

                const panel = `
                    <div style="
                        padding:12px 14px;
                        border-bottom:1px solid #e3e3e3;
                        background:#fff;
                    ">

                        <div style="
                            display:flex;
                            align-items:center;
                            justify-content:space-between;
                            flex-wrap:wrap;
                            gap:12px;
                        ">

                            <div>
                                <div style="
                                    font-size:14px;
                                    font-weight:800;
                                ">
                                    Salidas R1.6 vs Perfil operacional
                                </div>

                                <div style="
                                    margin-top:3px;
                                    font-size:12px;
                                    color:#666;
                                ">
                                    ${escapeHtml(unidad)}
                                    &bull;
                                    ${escapeHtml(datos.tipo_dia || "")}
                                    &bull;
                                    ${escapeHtml(fecha)}
                                </div>
                            </div>

                            <div style="
                                display:flex;
                                gap:8px;
                                flex-wrap:wrap;
                            ">

                                <button
                                    type="button"
                                    class="modo-real-perfil"
                                    data-modo="60"
                                    style="
                                        padding:7px 12px;
                                        border-radius:8px;
                                        border:1px solid #bbb;
                                        cursor:pointer;
                                        font-weight:${
                                            es60
                                                ? "800"
                                                : "500"
                                        };
                                        background:${
                                            es60
                                                ? "#eef3ff"
                                                : "#fff"
                                        };
                                    ">
                                    Por hora (60 min)
                                </button>

                                <button
                                    type="button"
                                    class="modo-real-perfil"
                                    data-modo="30"
                                    style="
                                        padding:7px 12px;
                                        border-radius:8px;
                                        border:1px solid #bbb;
                                        cursor:pointer;
                                        font-weight:${
                                            !es60
                                                ? "800"
                                                : "500"
                                        };
                                        background:${
                                            !es60
                                                ? "#eef3ff"
                                                : "#fff"
                                        };
                                    ">
                                    Por media hora (30 min)
                                </button>
                            </div>
                        </div>

                        <div style="
                            display:flex;
                            flex-wrap:wrap;
                            gap:10px;
                            margin-top:12px;
                        ">

                            <div style="
                                border:1px solid #ddd;
                                border-radius:9px;
                                padding:7px 12px;
                            ">
                                <small>REAL R1.6</small>
                                <div style="
                                    font-size:18px;
                                    font-weight:800;
                                ">
                                    ${numero(totalReal)}
                                </div>
                            </div>

                            <div style="
                                border:1px solid #ddd;
                                border-radius:9px;
                                padding:7px 12px;
                            ">
                                <small>PERFIL</small>
                                <div style="
                                    font-size:18px;
                                    font-weight:800;
                                ">
                                    ${numero(totalPerfil)}
                                </div>
                            </div>

                            <div style="
                                border:1px solid #ddd;
                                border-radius:9px;
                                padding:7px 12px;
                            ">
                                <small>CUMPLIMIENTO</small>
                                <div style="
                                    font-size:18px;
                                    font-weight:800;
                                ">
                                    ${
                                        pctGeneral === null
                                            ? "--"
                                            : porcentaje(pctGeneral)
                                    }
                                </div>
                            </div>
                        </div>

                        <div style="
                            margin-top:9px;
                            font-size:11px;
                            color:#666;
                        ">
                            Real / Perfil &bull;
                            Haz clic en una celda con salidas
                            para ver PPU, servicio y hora.
                        </div>
                    </div>
                `;

                // ----------------------------------------------------
                // CABECERA TABLA
                // ----------------------------------------------------

                let cabecera = `
                    <th class="sticky-terminal">
                        Terminal
                    </th>
                `;

                for (
                    const intervalo
                    of intervalos
                ) {

                    cabecera += `
                        <th
                            class="num periodo-col"
                            style="min-width:82px;">
                            ${escapeHtml(
                                intervalo.etiqueta
                            )}

                            <small style="
                                display:block;
                                font-weight:400;
                                white-space:nowrap;
                            ">
                                Real / Perfil
                            </small>
                        </th>
                    `;
                }

                // ----------------------------------------------------
                // TOTALES POR INTERVALO
                // ----------------------------------------------------

                const totalRealIntervalo =
                    new Map();

                const totalPerfilIntervalo =
                    new Map();

                for (
                    const intervalo
                    of intervalos
                ) {
                    totalRealIntervalo.set(
                        intervalo.clave,
                        0
                    );

                    totalPerfilIntervalo.set(
                        intervalo.clave,
                        0
                    );
                }

                // ----------------------------------------------------
                // FILAS TERMINALES
                // ----------------------------------------------------

                let cuerpo = "";

                for (
                    const terminal
                    of terminales.values()
                ) {

                    const valores =
                        mapa.get(terminal.codigo)
                        ||
                        new Map();

                    let celdas = "";

                    for (
                        const intervalo
                        of intervalos
                    ) {

                        const fila =
                            valores.get(
                                intervalo.clave
                            )
                            ||
                            {
                                real: 0,
                                perfil: 0,
                                porcentaje: null,
                                detalle: []
                            };

                        const real =
                            Number(
                                fila.real
                                ||
                                0
                            );

                        const perfil =
                            Number(
                                fila.perfil
                                ||
                                0
                            );

                        totalRealIntervalo.set(
                            intervalo.clave,
                            Number(
                                totalRealIntervalo.get(
                                    intervalo.clave
                                )
                                ||
                                0
                            )
                            +
                            real
                        );

                        totalPerfilIntervalo.set(
                            intervalo.clave,
                            Number(
                                totalPerfilIntervalo.get(
                                    intervalo.clave
                                )
                                ||
                                0
                            )
                            +
                            perfil
                        );

                        const pct =
                            perfil > 0
                                ? (
                                    real
                                    /
                                    perfil
                                ) * 100
                                : null;

                        const clase =
                            pct === null
                                ? ""
                                : clasePorcentaje(
                                    pct
                                );

                        const detalleTexto =
                            perfil > 0
                                ? porcentaje(pct)
                                : "S/R";

                        const clickeable =
                            real > 0;

                        celdas += `
                            <td
                                class="
                                    num
                                    periodo-col
                                    celda-real-perfil
                                "
                                ${
                                    clickeable
                                        ? `
                                        data-terminal="${escapeHtml(
                                            terminal.codigo
                                        )}"
                                        data-clave="${escapeHtml(
                                            intervalo.clave
                                        )}"
                                        data-etiqueta="${escapeHtml(
                                            intervalo.etiqueta
                                        )}"
                                        `
                                        : ""
                                }
                                style="
                                    min-width:82px;
                                    padding:5px;
                                    ${
                                        clickeable
                                            ? "cursor:pointer;"
                                            : ""
                                    }
                                ">

                                <div
                                    class="${clase}"
                                    style="
                                        border-radius:8px;
                                        padding:5px 4px;
                                        min-height:42px;
                                        display:flex;
                                        flex-direction:column;
                                        justify-content:center;
                                        align-items:center;
                                        gap:3px;
                                    ">

                                    <strong style="
                                        white-space:nowrap;
                                        font-size:12px;
                                    ">
                                        ${numero(real)}
                                        /
                                        ${numero(perfil)}
                                    </strong>

                                    <small style="
                                        white-space:nowrap;
                                        font-size:10px;
                                    ">
                                        ${detalleTexto}
                                    </small>
                                </div>
                            </td>
                        `;
                    }

                    cuerpo += `
                        <tr>
                            <td class="sticky-terminal">
                                <strong>
                                    ${escapeHtml(
                                        terminal.nombre
                                    )}
                                </strong>
                            </td>

                            ${celdas}
                        </tr>
                    `;
                }

                // ----------------------------------------------------
                // FILA TOTAL
                // ----------------------------------------------------

                let totales = "";

                for (
                    const intervalo
                    of intervalos
                ) {

                    const real =
                        Number(
                            totalRealIntervalo.get(
                                intervalo.clave
                            )
                            ||
                            0
                        );

                    const perfil =
                        Number(
                            totalPerfilIntervalo.get(
                                intervalo.clave
                            )
                            ||
                            0
                        );

                    const pct =
                        perfil > 0
                            ? (
                                real
                                /
                                perfil
                            ) * 100
                            : null;

                    totales += `
                        <td
                            class="
                                num
                                periodo-col
                                total-periodo
                            "
                            style="min-width:82px;">

                            <strong style="
                                white-space:nowrap;
                            ">
                                ${numero(real)}
                                /
                                ${numero(perfil)}
                            </strong>

                            <small style="
                                display:block;
                                margin-top:3px;
                                white-space:nowrap;
                            ">
                                ${
                                    pct === null
                                        ? "S/R"
                                        : porcentaje(pct)
                                }
                            </small>
                        </td>
                    `;
                }

                const filaTotal = `
                    <tr class="matriz-unidad-total">

                        <td class="sticky-terminal">
                            <strong>
                                TOTAL ${escapeHtml(unidad)}
                            </strong>

                            <small style="
                                display:block;
                                margin-top:3px;
                            ">
                                ${numero(totalReal)}
                                /
                                ${numero(totalPerfil)}
                            </small>
                        </td>

                        ${totales}

                    </tr>
                `;

                // ----------------------------------------------------
                // PINTAR
                // ----------------------------------------------------

                contenedor.innerHTML = `
                    ${panel}

                    <div style="
                        overflow:auto;
                        width:100%;
                    ">
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
                                ${cuerpo}
                                ${filaTotal}
                            </tbody>
                        </table>
                    </div>
                `;

                // ----------------------------------------------------
                // EVENTO CAMBIO 60 / 30
                // ----------------------------------------------------

                contenedor
                    .querySelectorAll(
                        ".modo-real-perfil"
                    )
                    .forEach(
                        boton => {

                            boton.addEventListener(
                                "click",
                                () => {

                                    const nuevoModo =
                                        boton.dataset.modo;

                                    if (
                                        nuevoModo !== "60"
                                        &&
                                        nuevoModo !== "30"
                                    ) {
                                        return;
                                    }

                                    modo =
                                        nuevoModo;

                                    sessionStorage.setItem(
                                        claveModo,
                                        modo
                                    );

                                    renderModo();
                                }
                            );
                        }
                    );

                // ----------------------------------------------------
                // EVENTO DETALLE PPU
                // ----------------------------------------------------

                contenedor
                    .querySelectorAll(
                        ".celda-real-perfil[data-terminal]"
                    )
                    .forEach(
                        celda => {

                            celda.addEventListener(
                                "click",
                                () => {

                                    const terminal =
                                        celda.dataset.terminal
                                        ||
                                        "";

                                    const clave =
                                        celda.dataset.clave
                                        ||
                                        "";

                                    const etiqueta =
                                        celda.dataset.etiqueta
                                        ||
                                        clave;

                                    const fila =
                                        (
                                            mapa.get(terminal)
                                            ||
                                            new Map()
                                        ).get(clave);

                                    const salidas =
                                        fila
                                        &&
                                        Array.isArray(
                                            fila.detalle
                                        )
                                            ? fila.detalle
                                            : [];

                                    abrirDetalleSalidas(
                                        terminal,
                                        etiqueta,
                                        salidas
                                    );
                                }
                            );
                        }
                    );
            };

            renderModo();

        } catch (error) {

            console.error(
                "Error Real vs Perfil",
                unidad,
                error
            );

            contenedor.innerHTML = `
                <div class="empty-cell">
                    No fue posible cargar Real R1.6 vs Perfil.
                </div>
            `;
        }
    }


    // ================================================================
    // FLOTA-R22-DETALLE-VISUAL
    // Detalle PPU real obtenido desde R2.2.
    // ================================================================

    function renderDetalleR22Terminal(
        terminal,
        series
    ) {

        const filas =
            Array.isArray(series)
                ? series
                : [];

        let html = `
            <div style="
                padding:12px;
                background:#f8fafc;
                border:1px solid #e2e8f0;
                border-radius:8px;
            ">

                <div style="
                    display:flex;
                    justify-content:space-between;
                    align-items:center;
                    gap:12px;
                    margin-bottom:10px;
                    flex-wrap:wrap;
                ">

                    <div>
                        <strong>
                            DETALLE FLOTA R2.2
                        </strong>

                        <span style="
                            margin-left:8px;
                            color:#64748b;
                        ">
                            ${escapeHtml(terminal)}
                        </span>
                    </div>

                    <small style="color:#64748b;">
                        PPU detectadas por periodo y acumuladas
                    </small>

                </div>

                <div style="overflow-x:auto;">

                    <table style="
                        width:100%;
                        border-collapse:collapse;
                        font-size:12px;
                    ">

                        <thead>
                            <tr>
                                <th style="padding:7px;text-align:left;">
                                    Periodo
                                </th>

                                <th style="padding:7px;text-align:center;">
                                    Perfil
                                </th>

                                <th style="padding:7px;text-align:center;">
                                    PPU periodo
                                </th>

                                <th style="padding:7px;text-align:center;">
                                    Operativa acum.
                                </th>

                                <th style="padding:7px;text-align:left;">
                                    PPU detectadas
                                </th>

                                <th style="padding:7px;text-align:left;">
                                    PPU acumuladas
                                </th>
                            </tr>
                        </thead>

                        <tbody>
        `;

        for (const fila of filas) {

            const periodo =
                Number(fila.periodo || 0);

            const conDatos =
                String(
                    fila.estado_r22 || ""
                ).toUpperCase()
                ===
                "CON_DATOS";

            const ppusPeriodo =
                Array.isArray(
                    fila.r22_ppus_periodo
                )
                    ? fila.r22_ppus_periodo
                    : [];

            const ppusAcumuladas =
                Array.isArray(
                    fila.r22_ppus_acumuladas
                )
                    ? fila.r22_ppus_acumuladas
                    : [];

            const pintarPpus = lista => {

                if (!conDatos || !lista.length) {
                    return "-";
                }

                return lista
                    .map(
                        ppu => `
                            <span style="
                                display:inline-block;
                                margin:2px;
                                padding:2px 6px;
                                border:1px solid #cbd5e1;
                                border-radius:5px;
                                background:#fff;
                                font-family:monospace;
                                font-weight:600;
                            ">
                                ${escapeHtml(ppu)}
                            </span>
                        `
                    )
                    .join("");
            };

            html += `
                <tr style="
                    border-top:1px solid #e2e8f0;
                    vertical-align:top;
                ">

                    <td style="
                        padding:7px;
                        font-weight:700;
                    ">
                        P${String(periodo).padStart(2, "0")}
                    </td>

                    <td style="
                        padding:7px;
                        text-align:center;
                        font-weight:700;
                    ">
                        ${numero(
                            fila.perfil_teorico ?? 0
                        )}
                    </td>

                    <td style="
                        padding:7px;
                        text-align:center;
                    ">
                        ${
                            conDatos
                                ? numero(
                                    fila.r22_periodo ?? 0
                                )
                                : "-"
                        }
                    </td>

                    <td style="
                        padding:7px;
                        text-align:center;
                        font-weight:700;
                    ">
                        ${
                            conDatos
                                ? numero(
                                    fila.r22_acumulado ?? 0
                                )
                                : "-"
                        }
                    </td>

                    <td style="padding:7px;">
                        ${pintarPpus(ppusPeriodo)}
                    </td>

                    <td style="padding:7px;">
                        ${pintarPpus(ppusAcumuladas)}
                    </td>

                </tr>
            `;
        }

        html += `
                        </tbody>
                    </table>
                </div>
            </div>
        `;

        return html;
    }


    function renderMatrizUnidad(
        unidad,
        filasPeriodo,
        ultimoPeriodoCobertura,
        filasGlobal,
        matrizFlota
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


        // ============================================================
        // FLOTA - 4 SERIES CERTIFICADAS
        //
        // PERFIL:
        //   buses requeridos por periodo.
        //
        // R1.6:
        //   PPU con presencia historica en el periodo.
        //
        // R2.2 PERIODO:
        //   PPU unicas detectadas dentro del periodo.
        //
        // R2.2 ACUMULADA:
        //   PPU distintas acumuladas hasta el periodo.
        // ============================================================

        const seriesFlota =
            (
                matrizFlota
                &&
                Array.isArray(
                    matrizFlota.series
                )
            )
                ? matrizFlota.series
                : [];

        const serieFlotaPorPeriodo =
            new Map();

        for (
            const filaSerie
            of seriesFlota
        ) {

            const periodoSerie =
                Number(
                    filaSerie.periodo
                );

            if (
                Number.isInteger(
                    periodoSerie
                )
                &&
                periodoSerie >= 1
                &&
                periodoSerie <= 24
            ) {

                serieFlotaPorPeriodo.set(
                    periodoSerie,
                    filaSerie
                );
            }
        }


        // ============================================================
        // FLOTA-BUS-PERFIL-R22
        //
        // BUS:
        //   PPU operativas acumuladas detectadas por R2.2.
        //
        // PERFIL:
        //   buses requeridos en el periodo.
        //
        // Fuente:
        //   matrizFlota.terminales
        // ============================================================

        const terminalesMatrizFlota =
            (
                matrizFlota
                &&
                Array.isArray(
                    matrizFlota.terminales
                )
            )
                ? matrizFlota.terminales
                : [];

        const mapaBusPerfilTerminal =
            new Map();

        for (
            const filaTerminal
            of terminalesMatrizFlota
        ) {

            const terminal =
                normalizarTerminalUnidad(
                    filaTerminal.terminal
                );

            const seriesTerminal =
                Array.isArray(
                    filaTerminal.series
                )
                    ? filaTerminal.series
                    : [];

            if (!terminal) {
                continue;
            }

            if (
                !mapaBusPerfilTerminal.has(
                    terminal
                )
            ) {
                mapaBusPerfilTerminal.set(
                    terminal,
                    new Map()
                );
            }

            const mapaPeriodos =
                mapaBusPerfilTerminal.get(
                    terminal
                );

            for (
                const filaPeriodo
                of seriesTerminal
            ) {

                const periodo =
                    Number(
                        filaPeriodo.periodo
                    );

                if (
                    !Number.isInteger(periodo)
                    ||
                    periodo < 1
                    ||
                    periodo > 24
                ) {
                    continue;
                }

                mapaPeriodos.set(
                    periodo,
                    filaPeriodo
                );
            }
        }


        function valorBusPerfilTerminal(
            terminal,
            periodo
        ) {

            const mapaTerminal =
                mapaBusPerfilTerminal.get(
                    terminal
                );

            const fila =
                mapaTerminal
                    ? mapaTerminal.get(periodo)
                    : null;

            if (!fila) {
                return {
                    visible: "-",
                    bus: null,
                    perfil: null,
                    estado: "SIN_DATOS"
                };
            }

            const estado =
                fila.estado_r22
                ||
                (
                    fila.r22_acumulado === null
                    ||
                    fila.r22_acumulado === undefined
                        ? "SIN_DATOS"
                        : "CON_DATOS"
                );

            if (
                estado === "SIN_DATOS"
                ||
                fila.r22_acumulado === null
                ||
                fila.r22_acumulado === undefined
            ) {
                return {
                    visible: "-",
                    bus: null,
                    perfil:
                        fila.perfil_teorico,
                    estado: "SIN_DATOS"
                };
            }

            const bus =
                Number(
                    fila.r22_acumulado
                );

            const perfil =
                Number(
                    fila.perfil_teorico
                    ??
                    0
                );

            return {
                // FLOTA-PERFIL-NEGRITA
                visible:
                    `${numero(bus)}/<strong class="perfil-negrita">${numero(perfil)}</strong>`,
                bus,
                perfil,
                estado
            };
        }


        const definicionesSeriesFlota = [
            {
                clave: "perfil_teorico",
                etiqueta: "PERFIL TEORICO",
                clase: "matriz-serie-perfil"
            },
            {
                clave: "r16_ppu",
                etiqueta: "PPU CON PRESENCIA R1.6",
                clase: "matriz-serie-r16"
            },
            {
                clave: "r22_periodo",
                etiqueta: "PPU DETECTADAS R2.2",
                clase: "matriz-serie-r22"
            },
            {
                clave: "r22_acumulado",
                etiqueta: "OPERATIVA ACUM. R2.2",
                clase: "matriz-serie-r22-acum"
            }
        ];

        let filasSeriesFlota = "";

        if (seriesFlota.length) {

            for (
                const definicion
                of definicionesSeriesFlota
            ) {

                let celdasSerie = "";

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

                    const filaSerie =
                        serieFlotaPorPeriodo.get(
                            periodo
                        );

                    const valor =
                        filaSerie
                            ? filaSerie[
                                definicion.clave
                            ]
                            : null;

                    const esSerieR22 =
                        (
                            definicion.clave
                            ===
                            "r22_periodo"
                            ||
                            definicion.clave
                            ===
                            "r22_acumulado"
                        );

                    const r22SinDatos =
                        (
                            esSerieR22
                            &&
                            (
                                !filaSerie
                                ||
                                filaSerie.estado_r22
                                ===
                                "SIN_DATOS"
                                ||
                                valor === null
                                ||
                                valor === undefined
                            )
                        );

                    const valorVisible =
                        r22SinDatos
                            ? "-"
                            : (
                                valor === null
                                ||
                                valor === undefined
                                    ? "\u2014"
                                    : numero(valor)
                            );

                    celdasSerie += `
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
                                ${valorVisible}
                            </strong>
                        </td>
                    `;
                }

                filasSeriesFlota += `
                    <tr
                        class="
                            matriz-serie-flota
                            ${definicion.clase}
                        ">

                        <td class="sticky-terminal">
                            <strong>
                                ${escapeHtml(
                                    definicion.etiqueta
                                )}
                            </strong>
                        </td>

                        <td class="num sticky-asignada">
                            &mdash;
                        </td>

                        ${celdasSerie}

                        <td class="num">
                            &mdash;
                        </td>

                        <td class="num">
                            &mdash;
                        </td>

                        <td class="num">
                            &mdash;
                        </td>

                        <td>
                            &mdash;
                        </td>

                    </tr>
                `;
            }
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

                const busPerfil =
                    valorBusPerfilTerminal(
                        terminalCodigo,
                        periodo
                    );

                const valor =
                    busPerfil.bus;

                if (valor !== null) {
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
                }

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
                            ${
                                busPerfil.visible
                            }
                        </strong>
                    </td>
                `;
            }


            const terminalDetalleId =
                (
                    "detalle-terminal-"
                    +
                    unidad
                    +
                    "-"
                    +
                    String(
                        global.terminal
                        ||
                        ""
                    ).replace(
                        /[^a-zA-Z0-9_-]/g,
                        "-"
                    )
                );

            cuerpo += `
                <tr class="matriz-terminal-principal">

                    <td class="sticky-terminal">

                        <button
                            type="button"
                            class="btn-toggle-terminal"
                            data-toggle-terminal="${escapeHtml(
                                terminalDetalleId
                            )}"
                            aria-expanded="false">

                            <span
                                class="toggle-terminal-icon"
                                aria-hidden="true">
                                &#9654;
                            </span>

                            <strong>
                                ${escapeHtml(
                                    global.terminal_nombre
                                    ||
                                    global.terminal
                                )}
                            </strong>

                        </button>

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

                <tr
                    id="${escapeHtml(terminalDetalleId)}"
                    class="matriz-terminal-detalle"
                    hidden>

                    <td
                        colspan="30"
                        class="matriz-terminal-detalle-celda">

                        <div class="matriz-terminal-detalle-contenido">

                            ${renderDetalleR22Terminal(
                                global.terminal,
                                (
                                    matrizFlota
                                    &&
                                    Array.isArray(
                                        matrizFlota.terminales
                                    )
                                        ? (
                                            (
                                                matrizFlota.terminales.find(
                                                    x =>
                                                        normalizarTerminalUnidad(
                                                            x.terminal
                                                        )
                                                        ===
                                                        normalizarTerminalUnidad(
                                                            global.terminal
                                                        )
                                                )
                                                ||
                                                {}
                                            ).series
                                            ||
                                            []
                                        )
                                        : []
                                )
                            )}

                        </div>

                    </td>

                </tr>
            `;
        }


        // ============================================================
        // FILA TOTAL DE LA UNIDAD
        // ============================================================


        function valorBusPerfilTotal(
            periodo
        ) {

            const fila =
                serieFlotaPorPeriodo.get(
                    periodo
                );

            if (!fila) {
                return "-";
            }

            if (
                fila.estado_r22 === "SIN_DATOS"
                ||
                fila.r22_acumulado === null
                ||
                fila.r22_acumulado === undefined
            ) {
                return "-";
            }

            const bus =
                Number(
                    fila.r22_acumulado
                );

            const perfil =
                Number(
                    fila.perfil_teorico
                    ??
                    0
                );

            return (
                `${numero(bus)}/<strong class="perfil-negrita">${numero(perfil)}</strong>`
            );
        }


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
                        ${
                            valorBusPerfilTotal(
                                periodo
                            )
                        }
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


        const idDetalleTotal =
            `detalle-total-${unidad}`;

        const filaTotal = `
            <tr class="matriz-unidad-total">

                <td class="sticky-terminal">

                    <button
                        type="button"
                        class="
                            btn-toggle-terminal
                            btn-toggle-total
                        "
                        data-toggle-terminal="${idDetalleTotal}"
                        aria-expanded="false">

                        <span
                            class="toggle-terminal-icon"
                            aria-hidden="true">
                            &#9654;
                        </span>

                        <strong>
                            TOTAL ${unidad}
                        </strong>

                    </button>

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

            <tr
                id="${idDetalleTotal}"
                class="
                    matriz-terminal-detalle
                    matriz-total-detalle
                "
                hidden>

                <td
                    colspan="30"
                    class="matriz-terminal-detalle-celda">

                    <div class="matriz-total-series">

                        <table
                            class="
                                data-table
                                matriz-unidad-table
                                matriz-periodos-table
                                matriz-series-detalle-table
                            ">

                            <tbody>
                                ${filasSeriesFlota}
                            </tbody>

                        </table>

                    </div>

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
        // DESPLEGAR / CERRAR TERMINAL Y TOTAL
        // ------------------------------------------------------------

        contenedor
            .querySelectorAll(
                ".btn-toggle-terminal[data-toggle-terminal]"
            )
            .forEach(
                boton => {

                    boton.addEventListener(
                        "click",
                        () => {

                            const idDetalle =
                                boton.dataset.toggleTerminal
                                ||
                                "";

                            if (!idDetalle) {
                                return;
                            }

                            const detalle =
                                document.getElementById(
                                    idDetalle
                                );

                            if (!detalle) {
                                return;
                            }

                            const abrir =
                                detalle.hidden;

                            detalle.hidden =
                                !abrir;

                            boton.setAttribute(
                                "aria-expanded",
                                abrir
                                    ? "true"
                                    : "false"
                            );

                            const icono =
                                boton.querySelector(
                                    ".toggle-terminal-icon"
                                );

                            if (icono) {
                                icono.innerHTML =
                                    abrir
                                        ? "&#9660;"
                                        : "&#9654;";
                            }
                        }
                    );
                }
            );


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


    // ============================================================
    // DETECTOR PPU NO RECONOCIDAS
    // ============================================================

    function renderAlertasPpu(alertas) {

        const panel =
            $("alertasPpuPanel");

        const estado =
            $("alertasPpuEstado");

        const contenido =
            $("alertasPpuContenido");

        if (
            !panel
            ||
            !estado
            ||
            !contenido
        ) {
            return;
        }

        const datos = (
            alertas
            &&
            typeof alertas === "object"
        )
            ? alertas
            : {};

        const detalle =
            Array.isArray(
                datos.detalle
            )
                ? datos.detalle
                : [];

        const totalBackend =
            Number(
                datos.total_no_reconocidas
            );

        const total =
            Number.isFinite(
                totalBackend
            )
                ? totalBackend
                : detalle.length;

        panel.classList.remove(
            "con-alertas",
            "sin-alertas"
        );

        if (total <= 0) {

            panel.classList.add(
                "sin-alertas"
            );

            estado.textContent =
                "SIN ALERTAS";

            contenido.innerHTML = `
                <div class="alertas-ppu-vacio">
                    Sin PPU no reconocidas pendientes
                    de validaci?n.
                </div>
            `;

            return;
        }

        panel.classList.add(
            "con-alertas"
        );

        estado.textContent = (
            total === 1
                ? "1 PPU POR VALIDAR"
                : `${total} PPU POR VALIDAR`
        );

        const filas =
            detalle
            .map(
                item => {

                    const ppu =
                        escapeHtml(
                            item.ppu
                            ??
                            "-"
                        );

                    const unidad =
                        escapeHtml(
                            item.unidad
                            ??
                            "-"
                        );

                    const terminal =
                        escapeHtml(
                            item.terminal
                            ??
                            "-"
                        );

                    const serviciosValor =
                        Array.isArray(
                            item.servicios
                        )
                            ? item.servicios.join(", ")
                            : (
                                item.servicio
                                ??
                                "-"
                            );

                    const tsValor =
                        Array.isArray(
                            item.codigos_ts
                        )
                            ? item.codigos_ts.join(", ")
                            : (
                                item.codigo_ts
                                ??
                                "-"
                            );

                    const servicios =
                        escapeHtml(
                            serviciosValor
                        );

                    const codigosTs =
                        escapeHtml(
                            tsValor
                        );

                    const primera =
                        escapeHtml(
                            item.primera_deteccion
                            ??
                            item.primera_fecha
                            ??
                            "-"
                        );

                    const ultima =
                        escapeHtml(
                            item.ultima_deteccion
                            ??
                            item.ultima_fecha
                            ??
                            "-"
                        );

                    const estadoItem =
                        escapeHtml(
                            item.estado
                            ??
                            "POR VALIDAR"
                        );

                    return `
                        <tr>
                            <td>
                                <strong>
                                    ${ppu}
                                </strong>
                            </td>

                            <td>${unidad}</td>
                            <td>${terminal}</td>
                            <td>${servicios}</td>
                            <td>${codigosTs}</td>
                            <td>${primera}</td>
                            <td>${ultima}</td>

                            <td>
                                <span class="alertas-ppu-badge">
                                    ${estadoItem}
                                </span>
                            </td>
                        </tr>
                    `;
                }
            )
            .join("");

        contenido.innerHTML = `
            <div class="alertas-ppu-resumen">
                Se detectaron ${total}
                PPU no reconocidas en operaci?n R1.6.
                Requieren validaci?n antes de
                clasificarlas.
            </div>

            <div class="table-wrap">
                <table class="alertas-ppu-tabla">
                    <thead>
                        <tr>
                            <th>PPU</th>
                            <th>Unidad</th>
                            <th>Terminal</th>
                            <th>Servicio</th>
                            <th>TS observado</th>
                            <th>Primera detecci?n</th>
                            <th>?ltima detecci?n</th>
                            <th>Estado</th>
                        </tr>
                    </thead>

                    <tbody>
                        ${filas}
                    </tbody>
                </table>
            </div>
        `;
    }


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

            if (valor < 50) {

                return {
                    clase: "apoyo-critico",
                    estado: "CR\u00cdTICO"
                };
            }

            if (valor <= 80) {

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


        // ============================================================
        // R17B - MOTOR DE RECOMENDACION DE APOYO OPERACIONAL
        // ============================================================
        //
        // Reglas:
        // - Receptor: terminal bajo 50 %.
        // - Objetivo: llevarlo como minimo a 50 %.
        // - Donantes: solamente terminales de la misma unidad.
        // - Un donante nunca puede quedar bajo 50 %.
        // - Se pueden combinar hasta 3 terminales.
        // - Prioridad: mayor cantidad de buses disponibles.
        //
        // IMPORTANTE:
        // Esta funcion NO modifica los datos reales.
        // Solamente genera una simulacion/recomendacion.
        // ============================================================

        function calcularRecomendacionApoyo(
            terminales,
            receptor
        ) {

            const OBJETIVO = 0.50;

            const asignadaReceptor =
                Number(
                    receptor.asignada
                    ||
                    0
                );

            const operativaReceptor =
                Number(
                    receptor.operativa
                    ||
                    0
                );

            const minimoReceptor =
                Math.ceil(
                    asignadaReceptor
                    *
                    OBJETIVO
                );

            const necesidadInicial =
                Math.max(
                    0,
                    minimoReceptor
                    -
                    operativaReceptor
                );

            if (
                asignadaReceptor <= 0
                ||
                necesidadInicial <= 0
            ) {

                return {
                    aplica: false,
                    necesidad: 0,
                    entregados: 0,
                    deficit: 0,
                    donantes: [],
                    estado: "SIN APOYO REQUERIDO"
                };
            }


            // --------------------------------------------------------
            // CALCULAR CAPACIDAD REAL DE CADA POSIBLE DONANTE
            // --------------------------------------------------------

            const candidatos =
                terminales
                .filter(
                    fila =>
                        fila !== receptor
                )
                .map(
                    fila => {

                        const asignada =
                            Number(
                                fila.asignada
                                ||
                                0
                            );

                        const operativa =
                            Number(
                                fila.operativa
                                ||
                                0
                            );

                        const minimo =
                            Math.ceil(
                                asignada
                                *
                                OBJETIVO
                            );

                        const disponible =
                            Math.max(
                                0,
                                operativa
                                -
                                minimo
                            );

                        return {
                            fila,
                            asignada,
                            operativa,
                            minimo,
                            disponible
                        };
                    }
                )
                .filter(
                    candidato =>
                        candidato.disponible > 0
                )
                .sort(
                    (a, b) => {

                        const porcentajeA =
                            a.asignada
                                ? (
                                    a.operativa
                                    /
                                    a.asignada
                                    *
                                    100
                                )
                                : 0;

                        const porcentajeB =
                            b.asignada
                                ? (
                                    b.operativa
                                    /
                                    b.asignada
                                    *
                                    100
                                )
                                : 0;

                        // R17M-B2:
                        // primero el terminal con mejor
                        // porcentaje operativo.

                        if (
                            porcentajeB
                            !==
                            porcentajeA
                        ) {
                            return (
                                porcentajeB
                                -
                                porcentajeA
                            );
                        }

                        // Si existe empate porcentual,
                        // priorizar mayor capacidad segura.

                        return (
                            b.disponible
                            -
                            a.disponible
                        );
                    }
                )


            // --------------------------------------------------------
            // DISTRIBUIR NECESIDAD
            // --------------------------------------------------------

            let pendiente =
                necesidadInicial;

            const donantes = candidatos.map(
                candidato => ({
                    terminal:
                        candidato.fila.terminal_nombre
                        ||
                        candidato.fila.terminal
                        ||
                        "",
                    cantidad: 0,
                    cantidad_sugerida: 0,
                    asignada:
                        candidato.asignada,
                    operativa_actual:
                        candidato.operativa,
                    operativa_proyectada:
                        candidato.operativa,
                    porcentaje_proyectado:
                        candidato.asignada
                            ? (
                                candidato.operativa
                                /
                                candidato.asignada
                                *
                                100
                            )
                            : 0,
                    capacidad_disponible:
                        candidato.disponible
                })
            );

            // ====================================================
            // R17N - REPARTO EQUILIBRADO
            // ====================================================
            //
            // Cada bus se asigna al donante que conserve el mayor
            // porcentaje operativo DESPUES de realizar el aporte.
            //
            // Esto distribuye el esfuerzo entre terminales y evita
            // cargar toda la necesidad a un solo patio.
            // ====================================================

            while (pendiente > 0) {

                const disponibles =
                    donantes
                    .filter(
                        donante =>
                            donante.cantidad
                            <
                            donante.capacidad_disponible
                    )
                    .map(
                        donante => {

                            const despues =
                                donante.operativa_actual
                                -
                                donante.cantidad
                                -
                                1;

                            const porcentajeDespues =
                                donante.asignada
                                    ? (
                                        despues
                                        /
                                        donante.asignada
                                        *
                                        100
                                    )
                                    : 0;

                            return {
                                donante,
                                despues,
                                porcentajeDespues
                            };
                        }
                    )
                    .sort(
                        (a, b) => {

                            if (
                                b.porcentajeDespues
                                !==
                                a.porcentajeDespues
                            ) {
                                return (
                                    b.porcentajeDespues
                                    -
                                    a.porcentajeDespues
                                );
                            }

                            const margenA =
                                a.donante.capacidad_disponible
                                -
                                a.donante.cantidad;

                            const margenB =
                                b.donante.capacidad_disponible
                                -
                                b.donante.cantidad;

                            return (
                                margenB
                                -
                                margenA
                            );
                        }
                    );

                if (!disponibles.length) {
                    break;
                }

                const elegido =
                    disponibles[0].donante;

                elegido.cantidad += 1;
                elegido.cantidad_sugerida =
                    elegido.cantidad;

                elegido.operativa_proyectada =
                    elegido.operativa_actual
                    -
                    elegido.cantidad;

                elegido.porcentaje_proyectado =
                    elegido.asignada
                        ? (
                            elegido.operativa_proyectada
                            /
                            elegido.asignada
                            *
                            100
                        )
                        : 0;

                pendiente -= 1;
            }

            const aporteTotal =
                donantes.reduce(
                    (
                        total,
                        donante
                    ) =>
                        total
                        +
                        donante.cantidad,
                    0
                );

                        // ====================================================
            // R17N-B - TOTAL REAL ENTREGADO
            // ====================================================

            const entregados =
                aporteTotal;

const operativaReceptorProyectada =
                operativaReceptor
                +
                entregados;

            const porcentajeReceptorProyectado =
                asignadaReceptor
                    ? (
                        operativaReceptorProyectada
                        /
                        asignadaReceptor
                        *
                        100
                    )
                    : 0;


            let estado =
                "SIN CAPACIDAD INTERNA";

            if (
                entregados > 0
                &&
                pendiente === 0
            ) {
                estado =
                    "APOYO COMPLETO";
            }
            else if (
                entregados > 0
                &&
                pendiente > 0
            ) {
                estado =
                    "APOYO PARCIAL";
            }


            return {
                aplica: true,

                terminal_receptor:
                    receptor.terminal_nombre
                    ||
                    receptor.terminal
                    ||
                    "",

                asignada_receptor:
                    asignadaReceptor,

                operativa_receptor:
                    operativaReceptor,

                minimo_objetivo:
                    minimoReceptor,

                necesidad:
                    necesidadInicial,

                entregados,

                deficit:
                    pendiente,

                operativa_proyectada:
                    operativaReceptorProyectada,

                porcentaje_proyectado:
                    porcentajeReceptorProyectado,

                donantes,

                estado
            };
        }



        // ============================================================
        // R17C - PRESENTACION RECOMENDACION APOYO OPERACIONAL
        // ============================================================

        function renderRecomendacionApoyo(
            unidad,
            terminales
        ) {

            const filasValidas =
                terminales.filter(
                    fila =>
                        Number(fila.asignada || 0) > 0
                );

            const receptoresCriticos =
                filasValidas
                .filter(
                    fila => {

                        const asignada =
                            Number(
                                fila.asignada
                                ||
                                0
                            );

                        const operativa =
                            Number(
                                fila.operativa
                                ||
                                0
                            );

                        if (asignada <= 0) {
                            return false;
                        }

                        return (
                            operativa
                            /
                            asignada
                            *
                            100
                        ) < 50;
                    }
                )
                .sort(
                    (a, b) => {

                        const pa =
                            Number(a.asignada || 0)
                                ? (
                                    Number(a.operativa || 0)
                                    /
                                    Number(a.asignada)
                                    *
                                    100
                                )
                                : 0;

                        const pb =
                            Number(b.asignada || 0)
                                ? (
                                    Number(b.operativa || 0)
                                    /
                                    Number(b.asignada)
                                    *
                                    100
                                )
                                : 0;

                        return pa - pb;
                    }
                );

            if (!receptoresCriticos.length) {

                return `
                    <div class="recomendacion-apoyo recomendacion-apoyo-ok">
                        <div class="recomendacion-apoyo-icono">
                            &#10003;
                        </div>

                        <div>
                            <strong>
                                Sin terminales cr\u00edticos
                            </strong>

                            <span>
                                No se requiere redistribuci\u00f3n para alcanzar
                                el umbral m\u00ednimo del 50 %.
                            </span>
                        </div>
                    </div>
                `;
            }


            // Prioridad operacional:
            // terminal con menor porcentaje operativo.
            const receptor =
                receptoresCriticos[0];

            const recomendacion =
                calcularRecomendacionApoyo(
                    filasValidas,
                    receptor
                );

            const terminalReceptor =
                recomendacion.terminal_receptor
                ||
                receptor.terminal_nombre
                ||
                receptor.terminal
                ||
                "Terminal";

            const asignada =
                Number(
                    recomendacion.asignada_receptor
                    ||
                    0
                );

            const operativa =
                Number(
                    recomendacion.operativa_receptor
                    ||
                    0
                );

            const porcentajeActual =
                asignada
                    ? (
                        operativa
                        /
                        asignada
                        *
                        100
                    )
                    : 0;

            const porcentajeProyectado =
                Number(
                    recomendacion.porcentaje_proyectado
                    ||
                    porcentajeActual
                );

            const empresa =
                String(unidad).toUpperCase() === "U8"
                    ? "ALFA"
                    : "OMEGA";

            const estadoClase =
                recomendacion.estado === "APOYO COMPLETO"
                    ? "completo"
                    : (
                        recomendacion.estado === "APOYO PARCIAL"
                            ? "parcial"
                            : "sin-capacidad"
                    );

            const donantesHtml =
                recomendacion.donantes.length
                    ? recomendacion.donantes
                        .map(
                            (donante, indice) => {

                                const porcentajeAntes =
                                    donante.asignada
                                        ? (
                                            donante.operativa_actual
                                            /
                                            donante.asignada
                                            *
                                            100
                                        )
                                        : 0;

                                return `
                                    <div class="recomendacion-donante">

                                        <div class="recomendacion-donante-numero">
                                            ${indice + 1}
                                        </div>

                                        <div class="recomendacion-donante-terminal">
                                            <strong>
                                                ${escapeHtml(
                                                    donante.terminal
                                                )}
                                            </strong>

                                            <span>
                                                ${donante.operativa_actual}
                                                /
                                                ${donante.asignada}
                                                &nbsp;&middot;&nbsp;
                                                ${porcentajeAntes.toFixed(2)} %
                                            </span>
                                        </div>

                                        <div class="recomendacion-donante-sugerido">
                                            <span>
                                                SUGERIDO
                                            </span>
                                            <strong>
                                                ${donante.cantidad}
                                            </strong>
                                            <small>
                                                buses
                                            </small>
                                        </div>

                                        <div class="recomendacion-donante-simulador">

                                            <label>
                                                APORTE SIMULADO
                                            </label>

                                            <div class="simulador-aporte-control">

                                                <button
                                                    type="button"
                                                    class="simulador-menos"
                                                    data-simulador-menos
                                                    aria-label="Disminuir aporte"
                                                >-</button>

                                                <input
                                                    type="number"
                                                    class="simulador-aporte-input"
                                                    data-simulador-aporte
                                                    min="0"
                                                    max="${donante.capacidad_disponible}"
                                                    step="1"
                                                    value="${donante.cantidad}"
                                                    data-sugerido="${donante.cantidad}"
                                                    data-capacidad="${donante.capacidad_disponible}"
                                                    data-operativa="${donante.operativa_actual}"
                                                    data-asignada="${donante.asignada}"
                                                    data-terminal="${escapeHtml(
                                                        donante.terminal
                                                    )}"
                                                >

                                                <button
                                                    type="button"
                                                    class="simulador-mas"
                                                    data-simulador-mas
                                                    aria-label="Aumentar aporte"
                                                >+</button>

                                            </div>

                                            <small>
                                                Disponible seguro:
                                                ${donante.capacidad_disponible}
                                            </small>

                                        </div>

                                        <div class="recomendacion-donante-proyeccion">
                                            <span>
                                                DESPUÉS DEL APOYO
                                            </span>

                                            <strong data-donante-resultado>
                                                ${donante.operativa_proyectada}
                                                /
                                                ${donante.asignada}
                                                &nbsp;&middot;&nbsp;
                                                ${Number(
                                                    donante.porcentaje_proyectado
                                                ).toFixed(2)} %
                                            </strong>
                                        </div>

                                    </div>
                                `;
                            }
                        )
                        .join("")
                    : `
                        <div class="recomendacion-sin-donante">
                            No existe capacidad interna disponible
                            para prestar buses sin dejar otro terminal
                            bajo el 50 %.
                        </div>
                    `;


            return `
                <div
                    class="recomendacion-apoyo"
                    data-simulador-apoyo="1"
                    data-unidad="${escapeHtml(
                        String(unidad).toUpperCase()
                    )}"
                    data-receptor="${escapeHtml(
                        terminalReceptor
                    )}"
                    data-receptor-operativa="${operativa}"
                    data-receptor-asignada="${asignada}"
                    data-necesidad="${recomendacion.necesidad}"
                >

                    <div class="recomendacion-apoyo-header">

                        <div>
                            <span class="recomendacion-apoyo-eyebrow">
                                RECOMENDACION DE APOYO OPERACIONAL
                            </span>

                            <h4>
                                ${escapeHtml(
                                    String(unidad).toUpperCase()
                                )}
                                &middot;
                                ${empresa}
                            </h4>
                        </div>

                        <div class="recomendacion-estado ${estadoClase}">
                            ${escapeHtml(
                                recomendacion.estado
                            )}
                        </div>

                    </div>


                    <div class="recomendacion-apoyo-principal">

                        <div class="recomendacion-prioridad">

                            <span class="recomendacion-label">
                                PRIORIDAD DE APOYO
                            </span>

                            <strong class="recomendacion-terminal-critico">
                                ${escapeHtml(
                                    terminalReceptor
                                )}
                            </strong>

                            <div class="recomendacion-actual">
                                <strong>
                                    ${operativa}/${asignada}
                                </strong>

                                <span>
                                    ${porcentajeActual.toFixed(2)} %
                                    operativa
                                </span>
                            </div>

                        </div>


                        <div class="recomendacion-kpi">
                            <span>
                                OBJETIVO
                            </span>

                            <strong>
                                50 %
                            </strong>

                            <small>
                                m\u00ednimo operacional
                            </small>
                        </div>


                        <div class="recomendacion-kpi">
                            <span>
                                NECESITA
                            </span>

                            <strong>
                                ${recomendacion.necesidad}
                            </strong>

                            <small>
                                buses
                            </small>
                        </div>


                        <div class="recomendacion-kpi">
                            <span>
                                APOYO PROPUESTO
                            </span>

                            <strong>
                                <span data-simulador-total>
                                    ${recomendacion.entregados}
                                </span>
                            </strong>

                            <small>
                                buses
                            </small>
                        </div>


                        <div class="recomendacion-kpi recomendacion-proyectada">
                            <span>
                                PROYECCI\u00d3N
                            </span>

                            <strong>
                                <span data-simulador-receptor-resultado>
                                    ${recomendacion.operativa_proyectada}
                                    /
                                    ${asignada}
                                </span>
                            </strong>

                            <small data-simulador-receptor-porcentaje>
                                ${porcentajeProyectado.toFixed(2)} %
                            </small>
                        </div>

                    </div>


                    <div class="recomendacion-apoyo-subtitulo">
                        <strong>
                            Distribucion sugerida del apoyo
                        </strong>

                        <span>
                            Todos los terminales disponibles de la misma unidad,
                            sin dejar un donante bajo 50 %.
                        </span>
                    </div>


                    <div class="recomendacion-donantes">
                        ${donantesHtml}
                    </div>


                    ${
                        recomendacion.deficit > 0
                            ? `
                                <div class="recomendacion-deficit">
                                    D\u00e9ficit pendiente:
                                    <strong>
                                        ${recomendacion.deficit}
                                        buses
                                    </strong>
                                </div>
                            `
                            : ""
                    }

                    <div class="simulador-resumen">

                        <div>
                            <span>
                                APOYO SIMULADO
                            </span>
                            <strong data-simulador-resumen-total>
                                ${recomendacion.entregados} buses
                            </strong>
                        </div>

                        <div>
                            <span>
                                NECESIDAD
                            </span>
                            <strong>
                                ${recomendacion.necesidad} buses
                            </strong>
                        </div>

                        <div>
                            <span>
                                BALANCE
                            </span>
                            <strong data-simulador-balance>
                                ${
                                    recomendacion.deficit > 0
                                        ? `Faltan ${recomendacion.deficit}`
                                        : "Nivelado"
                                }
                            </strong>
                        </div>

                        <button
                            type="button"
                            class="simulador-restablecer"
                            data-simulador-restablecer
                        >
                            Restablecer sugerido
                        </button>

                    </div>


                    <div class="recomendacion-nota">
                        Simulacion operacional basada en la flota
                        operativa observada. No ejecuta movimientos
                        de buses ni modifica la asignaci\u00f3n real.
                    </div>

                </div>
            `;
        }



        // ============================================================
        // R17I-C - RECALCULO INTERACTIVO DE APOYO
        // ============================================================

        function recalcularSimuladorApoyo(contenedor) {

            if (!contenedor) {
                return;
            }

            const operativaReceptor =
                Number(
                    contenedor.dataset.receptorOperativa
                    ||
                    0
                );

            const asignadaReceptor =
                Number(
                    contenedor.dataset.receptorAsignada
                    ||
                    0
                );

            const necesidad =
                Number(
                    contenedor.dataset.necesidad
                    ||
                    0
                );

            const inputs = Array.from(
                contenedor.querySelectorAll(
                    "[data-simulador-aporte]"
                )
            );

            let total = 0;

            inputs.forEach(
                input => {

                    const capacidad =
                        Math.max(
                            0,
                            Number(
                                input.dataset.capacidad
                                ||
                                0
                            )
                        );

                    let aporte =
                        Number(
                            input.value
                            ||
                            0
                        );

                    if (!Number.isFinite(aporte)) {
                        aporte = 0;
                    }

                    aporte =
                        Math.round(aporte);

                    aporte =
                        Math.max(
                            0,
                            Math.min(
                                capacidad,
                                aporte
                            )
                        );

                    input.value =
                        aporte;

                    total +=
                        aporte;

                    const operativa =
                        Number(
                            input.dataset.operativa
                            ||
                            0
                        );

                    const asignada =
                        Number(
                            input.dataset.asignada
                            ||
                            0
                        );

                    const despues =
                        Math.max(
                            0,
                            operativa
                            -
                            aporte
                        );

                    const porcentaje =
                        asignada > 0
                            ? (
                                despues
                                /
                                asignada
                                *
                                100
                            )
                            : 0;

                    const fila =
                        input.closest(
                            ".recomendacion-donante"
                        );

                    const resultado =
                        fila
                            ? fila.querySelector(
                                "[data-donante-resultado]"
                            )
                            : null;

                    if (resultado) {

                        resultado.textContent =
                            `${despues} / ${asignada} \u00b7 ${porcentaje.toFixed(2)} %`;

                        resultado.classList.toggle(
                            "simulacion-alerta",
                            porcentaje < 50
                        );
                    }
                }
            );


            const receptorDespues =
                operativaReceptor
                +
                total;

            const porcentajeReceptor =
                asignadaReceptor > 0
                    ? (
                        receptorDespues
                        /
                        asignadaReceptor
                        *
                        100
                    )
                    : 0;


            const totalKpi =
                contenedor.querySelector(
                    "[data-simulador-total]"
                );

            if (totalKpi) {
                totalKpi.textContent =
                    total;
            }


            const resultadoReceptor =
                contenedor.querySelector(
                    "[data-simulador-receptor-resultado]"
                );

            if (resultadoReceptor) {
                resultadoReceptor.textContent =
                    `${receptorDespues} / ${asignadaReceptor}`;
            }


            const porcentajeElemento =
                contenedor.querySelector(
                    "[data-simulador-receptor-porcentaje]"
                );

            if (porcentajeElemento) {
                porcentajeElemento.textContent =
                    `${porcentajeReceptor.toFixed(2)} %`;
            }


            const resumenTotal =
                contenedor.querySelector(
                    "[data-simulador-resumen-total]"
                );

            if (resumenTotal) {
                resumenTotal.textContent =
                    `${total} buses`;
            }


            const balance =
                contenedor.querySelector(
                    "[data-simulador-balance]"
                );

            const diferencia =
                total
                -
                necesidad;

            if (balance) {

                balance.classList.remove(
                    "balance-ok",
                    "balance-falta",
                    "balance-superavit"
                );

                if (diferencia === 0) {

                    balance.textContent =
                        "Nivelado";

                    balance.classList.add(
                        "balance-ok"
                    );

                } else if (diferencia < 0) {

                    balance.textContent =
                        `Faltan ${Math.abs(diferencia)} buses`;

                    balance.classList.add(
                        "balance-falta"
                    );

                } else {

                    balance.textContent =
                        `+${diferencia} buses sobre objetivo`;

                    balance.classList.add(
                        "balance-superavit"
                    );
                }
            }
        }


        function activarSimuladoresApoyo() {

            document
                .querySelectorAll(
                    "[data-simulador-apoyo]"
                )
                .forEach(
                    contenedor => {

                        if (
                            contenedor.dataset.simuladorActivo
                            ===
                            "1"
                        ) {
                            return;
                        }

                        contenedor.dataset.simuladorActivo =
                            "1";


                        contenedor.addEventListener(
                            "input",
                            event => {

                                if (
                                    event.target.matches(
                                        "[data-simulador-aporte]"
                                    )
                                ) {
                                    recalcularSimuladorApoyo(
                                        contenedor
                                    );
                                }
                            }
                        );


                        contenedor.addEventListener(
                            "click",
                            event => {

                                const botonMenos =
                                    event.target.closest(
                                        "[data-simulador-menos]"
                                    );

                                const botonMas =
                                    event.target.closest(
                                        "[data-simulador-mas]"
                                    );

                                const botonReset =
                                    event.target.closest(
                                        "[data-simulador-restablecer]"
                                    );


                                if (
                                    botonMenos
                                    ||
                                    botonMas
                                ) {

                                    const fila =
                                        event.target.closest(
                                            ".recomendacion-donante"
                                        );

                                    const input =
                                        fila
                                            ? fila.querySelector(
                                                "[data-simulador-aporte]"
                                            )
                                            : null;

                                    if (!input) {
                                        return;
                                    }

                                    const actual =
                                        Number(
                                            input.value
                                            ||
                                            0
                                        );

                                    input.value =
                                        botonMas
                                            ? actual + 1
                                            : actual - 1;

                                    recalcularSimuladorApoyo(
                                        contenedor
                                    );

                                    return;
                                }


                                if (botonReset) {

                                    contenedor
                                        .querySelectorAll(
                                            "[data-simulador-aporte]"
                                        )
                                        .forEach(
                                            input => {

                                                input.value =
                                                    input.dataset.sugerido
                                                    ||
                                                    "0";
                                            }
                                        );

                                    recalcularSimuladorApoyo(
                                        contenedor
                                    );
                                }
                            }
                        );


                        recalcularSimuladorApoyo(
                            contenedor
                        );
                    }
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

                
                    ${renderRecomendacionApoyo(
                        unidad,
                        datosUnidad
                    )}

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
                    &lt; 50 % de la flota del terminal
                </span>

                <span class="leyenda-atencion">
                    <i></i>
                    <strong>Atenci\u00f3n</strong>
                    50 % a 80 % de la flota del terminal
                </span>

                <span class="leyenda-normal">
                    <i></i>
                    <strong>Normal</strong>
                    &gt; 80 % de la flota del terminal
                </span>

            </div>
        `;

        activarSimuladoresApoyo();

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
                                    ${etiquetaSinTxUnidadTerminal(
                                        fila.terminal_nombre
                                        ||
                                        fila.terminal
                                        ||
                                        "-"
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
        // Este detalle pertenece exclusivamente a "Sin transmisión".
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


    const btnExportar =
        $("btnExportar");

    if (btnExportar) {
        btnExportar.addEventListener(
            "click",
            exportar
        );
    }



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
    // R11B - MONITOR ESTADO AUTOMATICO R1.6
    // ================================================================

    function formatearHoraMonitorR16(valor) {

        if (!valor) {
            return "--";
        }

        const fecha =
            new Date(valor);

        if (Number.isNaN(fecha.getTime())) {
            return "--";
        }

        return fecha.toLocaleTimeString(
            "es-CL",
            {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
                hour12: false
            }
        );
    }


    function estadoUnidadMonitorR16(
        respuesta,
        unidad
    ) {

        const texto =
            String(
                respuesta
                ??
                ""
            );

        const patronOk =
            new RegExp(
                "'" + unidad
                + "'\\s*:\\s*\\{[^}]*'ok'\\s*:\\s*True",
                "i"
            );

        const patronError =
            new RegExp(
                "'" + unidad
                + "'\\s*:\\s*\\{[^}]*'ok'\\s*:\\s*False",
                "i"
            );

        if (patronOk.test(texto)) {
            return "ok";
        }

        if (patronError.test(texto)) {
            return "error";
        }

        return "pendiente";
    }


    async function cargarMonitorR16Flota() {

        const monitor =
            document.getElementById(
                "r16MonitorFlota"
            );

        if (!monitor) {
            return;
        }

        const estado =
            document.getElementById(
                "r16MonitorEstado"
            );

        const unidades =
            document.getElementById(
                "r16MonitorUnidades"
            );

        const ultima =
            document.getElementById(
                "r16MonitorUltima"
            );

        const proxima =
            document.getElementById(
                "r16MonitorProxima"
            );

        const frecuencia =
            document.getElementById(
                "r16MonitorFrecuencia"
            );

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
                    "HTTP "
                    +
                    response.status
                );
            }

            const datos =
                await response.json();

            const u8 =
                estadoUnidadMonitorR16(
                    datos.ultima_respuesta,
                    "U8"
                );

            const u9 =
                estadoUnidadMonitorR16(
                    datos.ultima_respuesta,
                    "U9"
                );

            monitor.classList.remove(
                "r16-live-ok",
                "r16-live-error",
                "r16-live-pending"
            );

            if (!datos.activo) {

                monitor.classList.add(
                    "r16-live-pending"
                );

                if (estado) {
                    estado.textContent =
                        "R1.6 AUTOMATICO DESACTIVADO";
                }

            }
            else if (
                u8 === "ok"
                &&
                u9 === "ok"
            ) {

                monitor.classList.add(
                    "r16-live-ok"
                );

                if (estado) {
                    estado.textContent =
                        "R1.6 ACTUALIZADO";
                }

            }
            else if (
                u8 === "error"
                ||
                u9 === "error"
            ) {

                monitor.classList.add(
                    "r16-live-error"
                );

                if (estado) {
                    estado.textContent =
                        "ERROR ACTUALIZACION R1.6";
                }

            }
            else {

                monitor.classList.add(
                    "r16-live-pending"
                );

                if (estado) {
                    estado.textContent =
                        "R1.6 VERIFICANDO";
                }
            }

            if (unidades) {

                unidades.textContent =
                    "U8 "
                    +
                    (
                        u8 === "ok"
                            ? "\u2713 OK"
                            : (
                                u8 === "error"
                                    ? "\u2715 ERROR"
                                    : "--"
                            )
                    )
                    +
                    " | U9 "
                    +
                    (
                        u9 === "ok"
                            ? "\u2713 OK"
                            : (
                                u9 === "error"
                                    ? "\u2715 ERROR"
                                    : "--"
                            )
                    );
            }

            if (ultima) {

                ultima.textContent =
                    formatearHoraMonitorR16(
                        datos.ultima_ejecucion
                    );
            }

            if (proxima) {

                proxima.textContent =
                    formatearHoraMonitorR16(
                        datos.proxima_ejecucion
                    );
            }

            if (frecuencia) {

                frecuencia.textContent =
                    (
                        datos.intervalo_minutos
                        ??
                        "--"
                    )
                    +
                    " min";
            }

        }
        catch (error) {

            console.error(
                "Monitor R1.6 Flota Operativa:",
                error
            );

            monitor.classList.remove(
                "r16-live-ok",
                "r16-live-pending"
            );

            monitor.classList.add(
                "r16-live-error"
            );

            if (estado) {
                estado.textContent =
                    "SIN CONEXION ESTADO R1.6";
            }
        }
    }


    cargarMonitorR16Flota();

    setInterval(
        cargarMonitorR16Flota,
        60 * 1000
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


                await completarMatricesFlota(
                    datos
                );


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





    // ================================================================
    // R11C4 - MODAL PRESTADOS / RECIBIDOS
    // Independiente del modal certificado Ver PPU.
    // ================================================================

    function abrirModalPrestamos(
        tipo,
        terminal,
        unidad
    ) {

        const detalle = (
            window.__swavPrestamosDetalle
            ||
            []
        );


        const filas = detalle
            .filter(
                item => {

                    const unidadOk =
                        !unidad
                        ||
                        String(
                            item.unidad
                            ||
                            ""
                        ).toUpperCase()
                        ===
                        String(
                            unidad
                        ).toUpperCase();


                    let terminalOk = false;

                    if (
                        tipo
                        ===
                        "prestados"
                    ) {

                        terminalOk =
                            String(
                                item.terminal_base
                                ||
                                ""
                            ).toUpperCase()
                            ===
                            String(
                                terminal
                            ).toUpperCase();

                    } else {

                        terminalOk =
                            String(
                                item.terminal_operativo
                                ||
                                ""
                            ).toUpperCase()
                            ===
                            String(
                                terminal
                            ).toUpperCase();
                    }


                    return (
                        unidadOk
                        &&
                        terminalOk
                    );
                }
            )
            .sort(
                (a, b) => {

                    const fechaA =
                        String(
                            a.fecha
                            ||
                            ""
                        );

                    const fechaB =
                        String(
                            b.fecha
                            ||
                            ""
                        );

                    if (
                        fechaA
                        !==
                        fechaB
                    ) {

                        return fechaA.localeCompare(
                            fechaB
                        );
                    }


                    const periodoA =
                        Number(
                            a.periodo
                            ||
                            0
                        );

                    const periodoB =
                        Number(
                            b.periodo
                            ||
                            0
                        );

                    if (
                        periodoA
                        !==
                        periodoB
                    ) {

                        return (
                            periodoA
                            -
                            periodoB
                        );
                    }


                    return String(
                        a.ppu
                        ||
                        ""
                    ).localeCompare(
                        String(
                            b.ppu
                            ||
                            ""
                        )
                    );
                }
            );


        let modal =
            document.getElementById(
                "modalPrestamosPatio"
            );


        if (!modal) {

            modal =
                document.createElement(
                    "div"
                );

            modal.id =
                "modalPrestamosPatio";

            modal.className =
                "prestamos-modal-overlay hidden";

            modal.innerHTML = `
                <div class="prestamos-modal">

                    <div class="prestamos-modal-header">

                        <div>
                            <span class="modal-kicker">
                                APOYO ENTRE PATIOS
                            </span>

                            <h3 id="prestamosModalTitulo">
                                Buses en pr\u00e9stamo
                            </h3>

                            <p id="prestamosModalSubtitulo">
                            </p>
                        </div>

                        <button
                            type="button"
                            id="cerrarPrestamosModal"
                            class="prestamos-modal-cerrar"
                            aria-label="Cerrar">
                            &times;
                        </button>

                    </div>

                    <div class="prestamos-modal-body">

                        <div class="prestamos-modal-resumen">
                            <strong id="prestamosModalBuses">
                                0
                            </strong>
                            <span id="prestamosModalBusesLabel">
                                buses
                            </span>

                            <span>
                                /
                            </span>

                            <strong id="prestamosModalTotal">
                                0
                            </strong>
                            <span>
                                movimientos
                            </span>
                        </div>

                        <div class="prestamos-tabla-wrap">

                            <table class="data-table prestamos-tabla">

                                <thead>
                                    <tr>
                                        <th>PPU</th>
                                        <th>Patio base</th>
                                        <th>Patio operativo</th>
                                        <th>Servicios</th>
                                        <th>Per\u00edodos</th>
                                        <th>Movimientos</th>
                                    </tr>
                                </thead>

                                <tbody id="prestamosModalBody">
                                </tbody>

                            </table>

                        </div>

                    </div>

                                </div>
            `;


            document.body.appendChild(
                modal
            );


            document
                .getElementById(
                    "cerrarPrestamosModal"
                )
                .addEventListener(
                    "click",
                    () => {
                        modal.classList.add(
                            "hidden"
                        );

                        document.body.classList.remove(
                            "modal-open"
                        );
                    }
                );


            modal.addEventListener(
                "click",
                evento => {

                    if (
                        evento.target
                        ===
                        modal
                    ) {

                        modal.classList.add(
                            "hidden"
                        );

                        document.body.classList.remove(
                            "modal-open"
                        );
                    }
                }
            );
        }


        const titulo =
            document.getElementById(
                "prestamosModalTitulo"
            );

        const subtitulo =
            document.getElementById(
                "prestamosModalSubtitulo"
            );

        const total =
            document.getElementById(
                "prestamosModalTotal"
            );

        const tbody =
            document.getElementById(
                "prestamosModalBody"
            );


        const busesElemento =
            document.getElementById(
                "prestamosModalBuses"
            );

        const busesLabelElemento =
            document.getElementById(
                "prestamosModalBusesLabel"
            );

        const ppuUnicas = new Set(
            filas
                .map(
                    item =>
                        String(
                            item.ppu
                            ||
                            item.patente
                            ||
                            ""
                        )
                            .trim()
                            .toUpperCase()
                )
                .filter(Boolean)
        );

        const totalBusesUnicos =
            ppuUnicas.size;


        titulo.textContent =
            tipo === "prestados"
                ? "Buses prestados"
                : "Buses recibidos";


        subtitulo.textContent =
            (
                terminal
                +
                " \u00b7 "
                +
                unidad
            );


        busesElemento.textContent =
            String(
                totalBusesUnicos
            );

        busesLabelElemento.textContent =
            tipo === "prestados"
                ? (
                    totalBusesUnicos === 1
                        ? "bus prestado"
                        : "buses prestados"
                )
                : (
                    totalBusesUnicos === 1
                        ? "bus recibido"
                        : "buses recibidos"
                );

        total.textContent =
            String(
                filas.length
            );


        const filasAgrupadasMapa =
            new Map();

        for (const item of filas) {

            const ppuClave =
                String(
                    item.ppu
                    ||
                    item.patente
                    ||
                    ""
                )
                    .trim()
                    .toUpperCase();

            if (!ppuClave) {
                continue;
            }

            if (
                !filasAgrupadasMapa.has(
                    ppuClave
                )
            ) {

                filasAgrupadasMapa.set(
                    ppuClave,
                    {
                        ppu:
                            ppuClave,

                        terminal_base:
                            item.terminal_base_nombre
                            ||
                            item.terminal_base
                            ||
                            "",

                        terminal_operativo:
                            item.terminal_operativo_nombre
                            ||
                            item.terminal_operativo
                            ||
                            "",

                        servicios:
                            new Set(),

                        periodos:
                            new Set(),

                        movimientos:
                            0,
                    }
                );
            }

            const agrupado =
                filasAgrupadasMapa.get(
                    ppuClave
                );

            const servicio =
                String(
                    item.servicio_r16
                    ||
                    ""
                ).trim();

            if (servicio) {
                agrupado.servicios.add(
                    servicio
                );
            }

            const periodoNumero =
                Number(
                    item.periodo
                    ||
                    0
                );

            if (
                Number.isInteger(
                    periodoNumero
                )
                &&
                periodoNumero >= 1
                &&
                periodoNumero <= 24
            ) {

                agrupado.periodos.add(
                    periodoNumero
                );
            }

            agrupado.movimientos += 1;
        }


        const filasAgrupadas =
            Array.from(
                filasAgrupadasMapa.values()
            )
            .sort(
                (a, b) =>
                    a.ppu.localeCompare(
                        b.ppu
                    )
            );


        if (!filas.length) {

            tbody.innerHTML = `
                <tr>
                    <td
                        colspan="6"
                        class="empty-cell">
                        Sin movimientos para el rango seleccionado.
                    </td>
                </tr>
            `;

        } else {

            tbody.innerHTML =
                filasAgrupadas
                .map(
                    item => `
                        <tr>

                            <td>
                                <strong class="ppu-value">
                                    ${escapeHtml(
                                        item.ppu
                                        ||
                                        ""
                                    )}
                                </strong>
                            </td>

                            <td>
                                ${escapeHtml(
                                    item.terminal_base
                                    ||
                                    ""
                                )}
                            </td>

                            <td>
                                ${escapeHtml(
                                    item.terminal_operativo
                                    ||
                                    ""
                                )}
                            </td>

                            <td>
                                ${escapeHtml(
                                    Array.from(
                                        item.servicios
                                    )
                                    .sort()
                                    .join(", ")
                                )}
                            </td>

                            <td>
                                ${escapeHtml(
                                    Array.from(
                                        item.periodos
                                    )
                                    .sort(
                                        (a, b) =>
                                            a - b
                                    )
                                    .map(
                                        periodo =>
                                            `P${String(
                                                periodo
                                            ).padStart(
                                                2,
                                                "0"
                                            )}`
                                    )
                                    .join(", ")
                                )}
                            </td>

                            <td class="num">
                                <strong>
                                    ${numero(
                                        item.movimientos
                                    )}
                                </strong>
                            </td>

                        </tr>
                    `
                )
                .join("");
        }


        modal.classList.remove(
            "hidden"
        );

        document.body.classList.add(
            "modal-open"
        );
    }


    document.addEventListener(
        "click",
        evento => {

            const boton =
                evento.target.closest(
                    ".prestamo-chip[data-prestamo-tipo]"
                );

            if (!boton) {
                return;
            }


            evento.preventDefault();


            abrirModalPrestamos(
                boton.dataset.prestamoTipo
                ||
                "",
                boton.dataset.prestamoTerminal
                ||
                "",
                boton.dataset.prestamoUnidad
                ||
                ""
            );
        }
    );




    // ================================================================
    // R11D3 - PINTAR BARRAS APOYO
    // Solo presentación.
    // Lee el porcentaje ya calculado y mostrado por SWAV.
    // ================================================================

    function pintarBarrasApoyo() {

        const tarjetas =
            document.querySelectorAll(
                ".apoyo-terminal-card"
            );

        tarjetas.forEach(
            tarjeta => {

                const porcentajeElemento =
                    tarjeta.querySelector(
                        ".apoyo-metricas > div:last-child strong"
                    );

                if (!porcentajeElemento) {
                    return;
                }

                const texto =
                    String(
                        porcentajeElemento.textContent
                        ||
                        ""
                    )
                    .replace("%", "")
                    .replace(",", ".")
                    .trim();

                let valor =
                    Number.parseFloat(
                        texto
                    );

                if (
                    !Number.isFinite(valor)
                ) {
                    valor = 0;
                }

                valor =
                    Math.max(
                        0,
                        Math.min(
                            100,
                            valor
                        )
                    );

                tarjeta.style.setProperty(
                    "--apoyo-pct",
                    valor + "%"
                );
            }
        );
    }


    document.addEventListener(
        "DOMContentLoaded",
        () => {

            pintarBarrasApoyo();

            const ranking =
                document.getElementById(
                    "rankingApoyo"
                );

            if (!ranking) {
                return;
            }

            const observer =
                new MutationObserver(
                    () => {
                        pintarBarrasApoyo();
                    }
                );

            observer.observe(
                ranking,
                {
                    childList: true,
                    subtree: true
                }
            );
        }
    );

})();


    // ================================================================
    // R15H-E3 - EXCEL HISTORICO SIN TX
    // ================================================================

    const btnExcelHistoricoSinTx =
        document.getElementById(
            "btnExcelHistoricoSinTx"
        );

    if (btnExcelHistoricoSinTx) {

        btnExcelHistoricoSinTx.addEventListener(
            "click",
            () => {

                window.location.href =
                    "/api/flota-operativa/exportar-sin-tx-historico";
            }
        );
    }


