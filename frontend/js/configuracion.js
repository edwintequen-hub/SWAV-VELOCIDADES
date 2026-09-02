/*
==========================================================
METROPOL
Configuración del Sistema
==========================================================
*/

document.addEventListener(
    "DOMContentLoaded",
    () => {

        document
            .getElementById("btnInfo")
            ?.addEventListener(
                "click",
                importarInfo
            );


        // ==============================================
        // ANEXO 3
        // ==============================================

        document
            .getElementById("btnAnexo3U8")
            ?.addEventListener(
                "click",
                () => importarAnexo3("U8")
            );

        document
            .getElementById("btnAnexo3U9")
            ?.addEventListener(
                "click",
                () => importarAnexo3("U9")
            );


        // ==============================================
        // ANEXO 4
        // ==============================================

        document
            .getElementById("btnAnexo4U8")
            ?.addEventListener(
                "click",
                () => importarAnexo4("U8")
            );

        document
            .getElementById("btnAnexo4U9")
            ?.addEventListener(
                "click",
                () => importarAnexo4("U9")
            );


        // ==============================================
        // R1.6
        // ==============================================

        document
            .getElementById("btnR16U8")
            ?.addEventListener(
                "click",
                () => importarR16("U8")
            );

        document
            .getElementById("btnR16U9")
            ?.addEventListener(
                "click",
                () => importarR16("U9")
            );

    }
);


// ==========================================================
// FORMATEAR FECHA DE IMPORTACIÓN
// ==========================================================

function formatearFechaLocal(fecha) {

    if (!fecha) {
        return "-";
    }

    try {

        let valor = String(fecha).trim();

        const tieneZonaHoraria =
            /Z$/i.test(valor) ||
            /[+-]\d{2}:\d{2}$/.test(valor);

        if (!tieneZonaHoraria) {
            valor += "Z";
        }

        const fechaObj = new Date(valor);

        if (isNaN(fechaObj.getTime())) {
            return String(fecha);
        }

        return fechaObj.toLocaleString(
            "es-CL",
            {
                dateStyle: "short",
                timeStyle: "medium"
            }
        );

    } catch (error) {

        console.error(
            "Error formateando fecha:",
            error
        );

        return String(fecha);
    }
}


// ==========================================================
// CARGAR ESTADO DE IMPORTACIONES
// ==========================================================

function actualizarResumenTarjetaImportacion(
    tipoArchivo,
    unidad,
    item
) {

    const tipo =
        String(tipoArchivo || "")
        .trim()
        .toUpperCase();

    const unidadNormalizada =
        String(unidad || "")
        .trim()
        .toUpperCase();

    let prefijo = null;

    if (tipo === "ANEXO 3") {

        prefijo =
            unidadNormalizada === "U8"
                ? "estadoAnexo3U8Resumen"
                : unidadNormalizada === "U9"
                    ? "estadoAnexo3U9Resumen"
                    : null;

    }
    else if (tipo === "ANEXO 4") {

        prefijo =
            unidadNormalizada === "U8"
                ? "estadoAnexo4U8Resumen"
                : unidadNormalizada === "U9"
                    ? "estadoAnexo4U9Resumen"
                    : null;

    }
    else if (tipo === "R1.6") {

        prefijo =
            unidadNormalizada === "U8"
                ? "estadoR16U8Resumen"
                : unidadNormalizada === "U9"
                    ? "estadoR16U9Resumen"
                    : null;

    }

    if (!prefijo) {
        return;
    }

    const resumen =
        document.getElementById(
            prefijo
        );

    if (!resumen) {
        return;
    }

    const estadoElemento =
        resumen.querySelector(
            ".config-import-state"
        );

    const cantidadElemento =
        resumen.querySelector(
            ".config-import-count"
        );

    const fechaElemento =
        resumen.querySelector(
            ".config-import-date"
        );

    const estado =
        String(
            item?.estado || "Pendiente"
        )
        .trim();

    const cantidad =
        Number(
            item?.registros ?? 0
        );

    const fecha =
        item?.fecha
            ? formatearFechaLocal(
                item.fecha
            )
            : "Sin actualizaci?n";

    if (estadoElemento) {

        const estadoNormalizado =
            estado
            .toUpperCase();

        const correcto =
            estadoNormalizado === "CORRECTO"
            ||
            estadoNormalizado === "OK";

        estadoElemento.innerHTML =
            correcto
                ? '<i class="bi bi-check-circle-fill"></i> Correcto'
                : '<i class="bi bi-hourglass-split"></i> '
                    + estado;

        estadoElemento.classList.toggle(
            "estado-correcto",
            correcto
        );

        estadoElemento.classList.toggle(
            "estado-pendiente",
            !correcto
        );

    }

    if (cantidadElemento) {

        cantidadElemento.textContent =
            cantidad.toLocaleString(
                "es-CL"
            )
            + " registros";

    }

    if (fechaElemento) {

        fechaElemento.textContent =
            fecha;

    }

}


async function cargarEstadoImportaciones() {

    try {

        const respuesta =
            await fetch("/api/configuracion/estado");

        if (!respuesta.ok) {
            throw new Error(
                "No se pudo obtener el estado de importaciones"
            );
        }

        const datos =
            await respuesta.json();

        // ======================================================
        // BUSCAR TABLA
        // ======================================================

        let tabla =
            document.getElementById(
                "tablaImportaciones"
            );

        if (!tabla) {

            const tablas =
                document.querySelectorAll("table");

            tablas.forEach(elemento => {

                if (
                    elemento.querySelector("tbody") &&
                    elemento.querySelector("thead")
                ) {

                    const texto =
                        elemento.innerText.toLowerCase();

                    if (
                        texto.includes("archivo") &&
                        texto.includes("estado") &&
                        texto.includes("registros")
                    ) {

                        tabla = elemento;

                    }

                }

            });

        }

        if (!tabla) {

            console.error(
                "No se encontró la tabla de Estado de Importaciones."
            );

            return;

        }

        const tbody =
            tabla.querySelector("tbody");

        if (!tbody) {

            console.error(
                "No se encontró el tbody de la tabla."
            );

            return;

        }

        // ======================================================
        // CONSTRUIR REGISTROS DESDE EL ESTADO REAL DEL BACKEND
        // ======================================================

        const registros = [];

        // ------------------------------------------------------
        // INFO
        // ------------------------------------------------------

        if (
            datos?.INFO &&
            typeof datos.INFO === "object"
        ) {

            registros.push({

                tipo_archivo: "INFO",

                estado:
                    datos.INFO.estado ??
                    "Pendiente",

                registros:
                    obtenerCantidadRegistros(
                        datos.INFO
                    ),

                fecha:
                    obtenerFechaRegistro(
                        datos.INFO
                    ),

                unidad:
                    datos.INFO.unidad ??
                    "TODAS"

            });

        }

        // ------------------------------------------------------
        // ANEXO 3
        // ------------------------------------------------------

        const anexo3 =
            datos?.["ANEXO 3"];

        if (
            anexo3 &&
            typeof anexo3 === "object"
        ) {

            if (
                anexo3.unidades &&
                typeof anexo3.unidades === "object"
            ) {

                Object.entries(
                    anexo3.unidades
                ).forEach(
                    ([unidad, registro]) => {

                        if (
                            registro &&
                            typeof registro === "object"
                        ) {

                            registros.push({

                                tipo_archivo:
                                    "ANEXO 3",

                                unidad:
                                    registro.unidad ??
                                    unidad,

                                estado:
                                    registro.estado ??
                                    "Pendiente",

                                registros:
                                    obtenerCantidadRegistros(
                                        registro
                                    ),

                                fecha:
                                    obtenerFechaRegistro(
                                        registro
                                    ) ??
                                    obtenerFechaRegistro(
                                        anexo3
                                    )

                            });

                        }

                    }
                );

            }

        }

        // ------------------------------------------------------
        // ANEXO 4
        // ------------------------------------------------------

        const anexo4 =
            datos?.["ANEXO 4"];

        if (
            anexo4 &&
            typeof anexo4 === "object"
        ) {

            if (
                anexo4.unidades &&
                typeof anexo4.unidades === "object"
            ) {

                Object.entries(
                    anexo4.unidades
                ).forEach(
                    ([unidad, registro]) => {

                        if (
                            registro &&
                            typeof registro === "object"
                        ) {

                            registros.push({

                                tipo_archivo:
                                    "ANEXO 4",

                                unidad:
                                    registro.unidad ??
                                    unidad,

                                estado:
                                    registro.estado ??
                                    "Pendiente",

                                registros:
                                    obtenerCantidadRegistros(
                                        registro
                                    ),

                                fecha:
                                    obtenerFechaRegistro(
                                        registro
                                    ) ??
                                    obtenerFechaRegistro(
                                        anexo4
                                    )

                            });

                        }

                    }
                );

            }

        }

        // ------------------------------------------------------
        // R1.6
        // ------------------------------------------------------

        const r16 =
            datos?.["R1.6"];

        if (
            r16 &&
            typeof r16 === "object"
        ) {

            Object.entries(
                r16
            ).forEach(
                ([unidad, registro]) => {

                    if (
                        registro &&
                        typeof registro === "object"
                    ) {

                        registros.push({

                            tipo_archivo:
                                "R1.6",

                            unidad:
                                registro.unidad ??
                                unidad,

                            estado:
                                registro.estado ??
                                "Pendiente",

                            registros:
                                obtenerCantidadRegistros(
                                    registro
                                ),

                            fecha:
                                obtenerFechaRegistro(
                                    registro
                                )

                        });

                    }

                }
            );

        }

        // ======================================================
        // RESUMENES DE TARJETAS U8 / U9
        // ======================================================

        registros.forEach(
            item => {

                actualizarResumenTarjetaImportacion(
                    item.tipo_archivo,
                    item.unidad,
                    item
                );

            }
        );

        // ======================================================
        // ORDEN
        // ======================================================

        ordenarImportaciones(
            registros
        );

        // ======================================================
        // PINTAR
        // ======================================================

        tbody.innerHTML = "";

        if (
            registros.length === 0
        ) {

            tbody.innerHTML = `

                <tr>

                    <td
                        colspan="4"
                        class="text-center text-muted"
                    >

                        No hay importaciones registradas.

                    </td>

                </tr>

            `;

            return;

        }

        registros.forEach(
            item => {

                tbody.appendChild(
                    generarFilaImportacion(
                        item
                    )
                );

            }
        );

        console.log(
            "Estado de importaciones actualizado:",
            registros
        );

    }

    catch (error) {

        console.error(
            "Error cargando estado de importaciones:",
            error
        );

    }

}


// ==========================================================
// IMPORTAR INFO
// ==========================================================

async function importarInfo() {

    const archivo =
        document.getElementById(
            "archivoInfo"
        );

    const estado =
        document.getElementById(
            "estadoInfo"
        );


    if (
        !archivo ||
        !archivo.files ||
        archivo.files.length === 0
    ) {

        alert(
            "Seleccione el archivo INFO.xlsx."
        );

        return;

    }


    if (estado) {

        estado.innerHTML =
            "Procesando...";

    }


    try {

        const formData =
            new FormData();


        formData.append(
            "archivo",
            archivo.files[0]
        );


        const respuesta =
            await fetch(
                "/api/configuracion/info",
                {
                    method: "POST",
                    body: formData
                }
            );


        const json =
            await respuesta.json();


        console.log(
            "INFO respuesta:",
            json
        );


        if (!respuesta.ok) {

            throw new Error(
                json.detail ||
                "Error importando INFO"
            );

        }


        const registros =
            json.registros ??
            json.total ??
            0;


        if (estado) {

            estado.innerHTML =

                "✅ INFO importado correctamente — " +

                Number(
                    registros
                ).toLocaleString(
                    "es-CL"
                ) +

                " registros";

        }


        alert(

            "INFO procesado correctamente.\n\n" +

            "Registros: " +

            Number(
                registros
            ).toLocaleString(
                "es-CL"
            )

        );


        archivo.value =
            "";


        await cargarEstadoImportaciones();


    }

    catch (error) {

        console.error(
            "Error importando INFO:",
            error
        );


        if (estado) {

            estado.innerHTML =
                "❌ Error";

        }


        alert(

            "Error procesando INFO:\n" +
            error.message

        );

    }

}


// ==========================================================
// IMPORTAR ANEXO 3
// ==========================================================

async function importarAnexo3(unidad) {

    const unidadNormalizada =
        String(unidad || "")
        .trim()
        .toUpperCase();

    if (
        unidadNormalizada !== "U8"
        &&
        unidadNormalizada !== "U9"
    ) {

        alert(
            "Unidad invalida para Anexo 3."
        );

        return;
    }

    const archivo =
        document.getElementById(
            "archivoAnexo3"
            + unidadNormalizada
        );

    const estado =
        document.getElementById(
            "estadoAnexo3"
            + unidadNormalizada
        );

    if (
        !archivo ||
        !archivo.files ||
        archivo.files.length === 0
    ) {

        alert(
            "Seleccione el archivo Anexo 3 "
            + unidadNormalizada
            + "."
        );

        return;
    }

    if (estado) {

        estado.innerHTML =
            "Procesando Anexo 3 "
            + unidadNormalizada
            + "...";

    }

    try {

        const formData =
            new FormData();

        formData.append(
            "archivo",
            archivo.files[0]
        );

        const respuesta =
            await fetch(
                "/api/configuracion/anexo3?unidad="
                + encodeURIComponent(
                    unidadNormalizada
                ),
                {
                    method: "POST",
                    body: formData
                }
            );

        const json =
            await respuesta.json();

        if (!respuesta.ok) {

            throw new Error(
                json.detail ||
                "Error importando Anexo 3"
            );

        }

        const registros =
            json.registros ??
            json.total ??
            0;

        if (estado) {

            estado.innerHTML =
                "? Anexo 3 "
                + unidadNormalizada
                + " procesado correctamente ? "
                + Number(registros)
                    .toLocaleString("es-CL")
                + " registros";

        }

        alert(
            "Anexo 3 "
            + unidadNormalizada
            + " procesado correctamente.\n\n"
            + Number(registros)
                .toLocaleString("es-CL")
            + " registros."
        );

        await cargarEstadoImportaciones();

    }
    catch (error) {

        console.error(
            "Error Anexo 3:",
            error
        );

        if (estado) {

            estado.innerHTML =
                "? "
                + error.message;

        }

        alert(
            "Error importando Anexo 3 "
            + unidadNormalizada
            + ":\n\n"
            + error.message
        );

    }

}

async function importarAnexo4(unidad) {

    const unidadNormalizada =
        String(unidad || "")
        .trim()
        .toUpperCase();

    if (
        unidadNormalizada !== "U8"
        &&
        unidadNormalizada !== "U9"
    ) {

        alert(
            "Unidad invalida para Anexo 4."
        );

        return;
    }

    const archivo =
        document.getElementById(
            "archivoAnexo4"
            + unidadNormalizada
        );

    const estado =
        document.getElementById(
            "estadoAnexo4"
            + unidadNormalizada
        );

    if (
        !archivo ||
        !archivo.files ||
        archivo.files.length === 0
    ) {

        alert(
            "Seleccione el archivo Anexo 4 "
            + unidadNormalizada
            + "."
        );

        return;
    }

    if (estado) {

        estado.innerHTML =
            "Procesando Anexo 4 "
            + unidadNormalizada
            + "...";

    }

    try {

        const formData =
            new FormData();

        formData.append(
            "archivo",
            archivo.files[0]
        );

        const respuesta =
            await fetch(
                "/api/configuracion/anexo4?unidad="
                + encodeURIComponent(
                    unidadNormalizada
                ),
                {
                    method: "POST",
                    body: formData
                }
            );

        const json =
            await respuesta.json();

        if (!respuesta.ok) {

            throw new Error(
                json.detail ||
                "Error importando Anexo 4"
            );

        }

        const registros =
            json.registros ??
            json.total ??
            0;

        if (estado) {

            estado.innerHTML =
                "? Anexo 4 "
                + unidadNormalizada
                + " procesado correctamente ? "
                + Number(registros)
                    .toLocaleString("es-CL")
                + " registros";

        }

        alert(
            "Anexo 4 "
            + unidadNormalizada
            + " procesado correctamente.\n\n"
            + Number(registros)
                .toLocaleString("es-CL")
            + " registros."
        );

        await cargarEstadoImportaciones();

    }
    catch (error) {

        console.error(
            "Error Anexo 4:",
            error
        );

        if (estado) {

            estado.innerHTML =
                "? "
                + error.message;

        }

        alert(
            "Error importando Anexo 4 "
            + unidadNormalizada
            + ":\n\n"
            + error.message
        );

    }

}

async function importarR16(unidad) {

    const unidadNormalizada =
        String(unidad || "")
        .trim()
        .toUpperCase();

    if (
        unidadNormalizada !== "U8"
        &&
        unidadNormalizada !== "U9"
    ) {

        alert(
            "Unidad invalida para R1.6."
        );

        return;
    }

    const archivo =
        document.getElementById(
            "archivoR16"
            + unidadNormalizada
        );

    const estado =
        document.getElementById(
            "estadoR16"
            + unidadNormalizada
        );

    if (
        !archivo ||
        !archivo.files ||
        archivo.files.length === 0
    ) {

        alert(
            "Seleccione el archivo R1.6 "
            + unidadNormalizada
            + "."
        );

        return;
    }

    if (estado) {

        estado.innerHTML =
            "Procesando R1.6 "
            + unidadNormalizada
            + "...";

    }

    try {

        const formData =
            new FormData();

        formData.append(
            "archivo",
            archivo.files[0]
        );

        const respuesta =
            await fetch(
                "/api/configuracion/r16?unidad="
                + encodeURIComponent(
                    unidadNormalizada
                ),
                {
                    method: "POST",
                    body: formData
                }
            );

        const json =
            await respuesta.json();

        if (!respuesta.ok) {

            throw new Error(
                json.detail ||
                "Error importando R1.6"
            );

        }

        const registros =
            json.registros ??
            json.total ??
            json.expediciones ??
            0;

        if (estado) {

            estado.innerHTML =
                "? R1.6 "
                + unidadNormalizada
                + " procesado correctamente";

        }

        alert(
            "R1.6 "
            + unidadNormalizada
            + " procesado correctamente."
        );

        await cargarEstadoImportaciones();

    }
    catch (error) {

        console.error(
            "Error R1.6:",
            error
        );

        if (estado) {

            estado.innerHTML =
                "? "
                + error.message;

        }

        alert(
            "Error importando R1.6 "
            + unidadNormalizada
            + ":\n\n"
            + error.message
        );

    }

}

// ==========================================================
// FUNCIONES AUXILIARES
// ==========================================================

function obtenerCantidadRegistros(item) {

    if (
        !item ||
        typeof item !== "object"
    ) {

        return 0;

    }


    const valores = [

        item.registros_importados,

        item.registros_validos,

        item.registros,

        item.total_registros,

        item.total,

        item.cantidad

    ];


    for (
        const valor of valores
    ) {

        if (
            valor !== null &&
            valor !== undefined &&
            valor !== ""
        ) {

            const numero =
                Number(valor);


            if (
                Number.isFinite(numero)
            ) {

                return numero;

            }

        }

    }


    return 0;

}


// ==========================================================
// OBTENER FECHA DEL REGISTRO
// ==========================================================

function obtenerFechaRegistro(item) {

    if (
        !item ||
        typeof item !== "object"
    ) {

        return null;

    }


    return (

        item.ultima_actualizacion ??

        item.fecha_importacion ??

        item.fecha ??

        item.updated_at ??

        item.created_at ??

        null

    );

}


// ==========================================================
// NORMALIZAR TIPO DE ARCHIVO
// ==========================================================

function normalizarTipoArchivo(tipo) {

    if (!tipo) {

        return "";

    }


    const texto =
        String(tipo)
            .trim()
            .toUpperCase();


    if (
        texto === "INFO" ||
        texto === "INFO.XLSX"
    ) {

        return "INFO";

    }


    if (
        texto === "ANEXO 3" ||
        texto === "ANEXO3"
    ) {

        return "ANEXO 3";

    }


    if (
        texto === "ANEXO 4" ||
        texto === "ANEXO4"
    ) {

        return "ANEXO 4";

    }


    if (
        texto === "R1.6" ||
        texto === "R16"
    ) {

        return "R1.6";

    }


    return texto;

}


// ==========================================================
// ORDENAR IMPORTACIONES
// ==========================================================

function ordenarImportaciones(registros) {

    const orden = {

        "INFO": 1,

        "ANEXO 3": 2,

        "ANEXO 4": 3,

        "R1.6": 4

    };


    registros.sort(
        (a, b) => {

            const tipoA =
                normalizarTipoArchivo(
                    a.tipo_archivo
                );


            const tipoB =
                normalizarTipoArchivo(
                    b.tipo_archivo
                );


            const ordenA =
                orden[tipoA] ?? 99;


            const ordenB =
                orden[tipoB] ?? 99;


            if (
                ordenA !== ordenB
            ) {

                return ordenA - ordenB;

            }


            return String(
                a.unidad ?? ""
            ).localeCompare(
                String(
                    b.unidad ?? ""
                )
            );

        }
    );

}


// ==========================================================
// GENERAR FILA DE IMPORTACIÓN
// ==========================================================

function generarFilaImportacion(item) {

    const fila =
        document.createElement(
            "tr"
        );


    const tipo =
        normalizarTipoArchivo(
            item.tipo_archivo
        );


    let nombreMostrar =
        tipo;


    // ------------------------------------------------------
    // INFO
    // ------------------------------------------------------

    if (
        tipo === "INFO"
    ) {

        nombreMostrar =
            "INFO.xlsx";

    }


    // ------------------------------------------------------
    // ANEXO 3
    // ------------------------------------------------------

    else if (
        tipo === "ANEXO 3"
    ) {

        if (item.unidad) {

            nombreMostrar =
                `Anexo 3 ${item.unidad}`;

        }

        else {

            nombreMostrar =
                "Anexo 3";

        }

    }


    // ------------------------------------------------------
    // ANEXO 4
    // ------------------------------------------------------

    else if (
        tipo === "ANEXO 4"
    ) {

        if (item.unidad) {

            nombreMostrar =
                `Anexo 4 ${item.unidad}`;

        }

        else {

            nombreMostrar =
                "Anexo 4";

        }

    }


    // ------------------------------------------------------
    // R1.6
    // ------------------------------------------------------

    else if (
        tipo === "R1.6"
    ) {

        if (item.unidad) {

            nombreMostrar =
                `R1.6 ${item.unidad}`;

        }

        else {

            nombreMostrar =
                "R1.6";

        }

    }


    // ======================================================
    // DESCRIPCIÓN
    // ======================================================

    let descripcion = "";


    if (
        tipo === "INFO"
    ) {

        descripcion =
            "Catálogo de servicios, unidades y terminales.";

    }

    else if (
        tipo === "ANEXO 3"
    ) {

        descripcion =
            item.unidad
                ? `Velocidades teóricas oficiales DTPM para ${item.unidad}.`
                : "Velocidades teóricas oficiales DTPM.";

    }

    else if (
        tipo === "ANEXO 4"
    ) {

        descripcion =
            item.unidad
                ? `Períodos operacionales DTPM para ${item.unidad}.`
                : "Períodos operacionales DTPM.";

    }

    else if (
        tipo === "R1.6"
    ) {

        descripcion =
            item.unidad
                ? `Archivo de expediciones para consulta de velocidades ${item.unidad}.`
                : "Archivo de expediciones para consulta de velocidades.";

    }


    // ======================================================
    // ESTADO
    // ======================================================

    const estadoTexto =
        String(
            item.estado ??
            "Pendiente"
        )
        .trim()
        .toLowerCase();


    let estadoHTML = `

        <span
            class="text-warning fw-semibold"
        >

            <i class="bi bi-clock-fill"></i>

            Pendiente

        </span>

    `;


    if (
        estadoTexto.includes("correct") ||
        estadoTexto === "ok" ||
        estadoTexto.includes("éxito") ||
        estadoTexto.includes("exito") ||
        estadoTexto.includes("procesado")
    ) {

        estadoHTML = `

            <span
                class="text-success fw-semibold"
            >

                <i
                    class="bi bi-check-circle-fill"
                ></i>

                Correcto

            </span>

        `;

    }

    else if (
        estadoTexto.includes("error") ||
        estadoTexto.includes("fall")
    ) {

        estadoHTML = `

            <span
                class="text-danger fw-semibold"
            >

                <i
                    class="bi bi-x-circle-fill"
                ></i>

                Error

            </span>

        `;

    }


    // ======================================================
    // FECHA
    // ======================================================

    const fecha =
        formatearFechaLocal(
            item.fecha
        );


    // ======================================================
    // CREAR FILA
    // ======================================================

    fila.innerHTML = `

        <td>

            <strong>
                ${nombreMostrar}
            </strong>

            <div
                class="small text-muted"
            >

                ${descripcion}

            </div>

        </td>


        <td>

            ${estadoHTML}

        </td>


        <td>

            ${Number(
                item.registros ?? 0
            ).toLocaleString(
                "es-CL"
            )}

        </td>


        <td>

            ${fecha}

        </td>

    `;


    return fila;

}

// ==========================================================
// INICIALIZAR CONFIGURACIÓN
// ==========================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        cargarEstadoImportaciones();

    }
);
/* ==========================================================
   CREDENCIALES SINOPTICO
   ========================================================== */

async function cargarCredencialSinoptico() {

    const usuario =
        document.getElementById(
            "usuarioSinoptico"
        );

    const password =
        document.getElementById(
            "passwordSinoptico"
        );

    const estado =
        document.getElementById(
            "estadoSinoptico"
        );

    if (
        !usuario ||
        !password ||
        !estado
    ) {
        return;
    }

    try {

        const response =
            await fetch(
                "/api/configuracion/sinoptico"
            );

        if (!response.ok) {

            throw new Error(
                "Error HTTP " +
                response.status
            );

        }

        const datos =
            await response.json();

        if (datos.configurado) {

            usuario.value =
                datos.usuario || "";

            password.value = "";

            estado.innerHTML =
            `
            <span class="badge text-bg-success">
                Configurado
            </span>

            <span class="ms-2 text-muted small">
                Usuario: ${datos.usuario || "-"}
            </span>
            `;

        }
        else {

            usuario.value = "";
            password.value = "";

            estado.innerHTML =
            `
            <span class="badge text-bg-secondary">
                Sin configurar
            </span>
            `;

        }

    }
    catch (error) {

        console.error(
            "Error cargando credencial Sinoptico:",
            error
        );

        estado.innerHTML =
        `
        <span class="badge text-bg-danger">
            Error cargando configuración
        </span>
        `;

    }

}


/* ==========================================================
   GUARDAR CREDENCIAL
   ========================================================== */

async function guardarCredencialSinoptico() {

    const usuario =
        document.getElementById(
            "usuarioSinoptico"
        );

    const password =
        document.getElementById(
            "passwordSinoptico"
        );

    const boton =
        document.getElementById(
            "btnGuardarSinoptico"
        );

    const estado =
        document.getElementById(
            "estadoSinoptico"
        );

    if (
        !usuario ||
        !password ||
        !boton ||
        !estado
    ) {
        return;
    }

    const valorUsuario =
        usuario.value.trim();

    const valorPassword =
        password.value;

    if (!valorUsuario) {

        estado.innerHTML =
        `
        <span class="badge text-bg-warning">
            Ingrese usuario
        </span>
        `;

        usuario.focus();

        return;
    }

    if (!valorPassword) {

        estado.innerHTML =
        `
        <span class="badge text-bg-warning">
            Ingrese contraseña
        </span>
        `;

        password.focus();

        return;
    }

    const textoOriginal =
        boton.innerHTML;

    boton.disabled = true;

    boton.innerHTML =
    `
    <span
        class="spinner-border spinner-border-sm"
        role="status">
    </span>

    Guardando...
    `;

    try {

        const response =
            await fetch(
                "/api/configuracion/sinoptico",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify(
                        {
                            usuario:
                                valorUsuario,

                            password:
                                valorPassword
                        }
                    )
                }
            );

        const datos =
            await response.json();

        if (!response.ok) {

            throw new Error(
                datos.detail ||
                "Error guardando credencial"
            );

        }

        password.value = "";

        estado.innerHTML =
        `
        <span class="badge text-bg-success">
            Credencial guardada
        </span>

        <span class="ms-2 text-muted small">
            Usuario: ${datos.usuario || valorUsuario}
        </span>
        `;

    }
    catch (error) {

        console.error(
            "Error guardando credencial Sinoptico:",
            error
        );

        estado.innerHTML =
        `
        <span class="badge text-bg-danger">
            ${error.message}
        </span>
        `;

    }
    finally {

        boton.disabled = false;

        boton.innerHTML =
            textoOriginal;

    }

}


/* ==========================================================
   MOSTRAR / OCULTAR PASSWORD
   ========================================================== */

function configurarPasswordSinoptico() {

    const password =
        document.getElementById(
            "passwordSinoptico"
        );

    const boton =
        document.getElementById(
            "btnMostrarPasswordSinoptico"
        );

    if (
        !password ||
        !boton
    ) {
        return;
    }

    boton.addEventListener(
        "click",
        () => {

            const visible =
                password.type === "text";

            password.type =
                visible
                    ? "password"
                    : "text";

            boton.innerHTML =
                visible
                    ? '<i class="bi bi-eye-fill"></i>'
                    : '<i class="bi bi-eye-slash-fill"></i>';

        }
    );

}



/* ==========================================================
   CONFIGURACION AUTOMATICA R1.6
   ========================================================== */

let intervaloContadorR16Auto = null;
let proximaEjecucionR16Auto = null;


function formatearFechaR16Auto(valor) {

    if (!valor) {
        return "-";
    }

    const fecha = new Date(valor);

    if (Number.isNaN(fecha.getTime())) {
        return valor;
    }

    return fecha.toLocaleString(
        "es-CL",
        {
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit"
        }
    );
}



function actualizarContadorR16Auto() {

    const contador =
        document.getElementById(
            "r16AutoContador"
        );

    if (!contador) {
        return;
    }

    if (!proximaEjecucionR16Auto) {

        contador.textContent =
            "--:--:--";

        return;
    }

    const ahora =
        Date.now();

    const destino =
        proximaEjecucionR16Auto.getTime();

    let diferencia =
        Math.floor(
            (destino - ahora) / 1000
        );

    if (diferencia <= 0) {

        contador.textContent =
            "00:00:00";

        return;
    }

    const horas =
        Math.floor(
            diferencia / 3600
        );

    diferencia %=
        3600;

    const minutos =
        Math.floor(
            diferencia / 60
        );

    const segundos =
        diferencia % 60;

    contador.textContent =
        String(horas).padStart(2, "0")
        + ":"
        + String(minutos).padStart(2, "0")
        + ":"
        + String(segundos).padStart(2, "0");
}


function iniciarContadorR16Auto(
    proximaEjecucion
) {

    if (intervaloContadorR16Auto) {

        clearInterval(
            intervaloContadorR16Auto
        );

        intervaloContadorR16Auto =
            null;

    }

    if (!proximaEjecucion) {

        proximaEjecucionR16Auto =
            null;

        actualizarContadorR16Auto();

        return;
    }

    const fecha =
        new Date(
            proximaEjecucion
        );

    if (
        Number.isNaN(
            fecha.getTime()
        )
    ) {

        proximaEjecucionR16Auto =
            null;

        actualizarContadorR16Auto();

        return;
    }

    proximaEjecucionR16Auto =
        fecha;

    actualizarContadorR16Auto();

    intervaloContadorR16Auto =
        setInterval(
            actualizarContadorR16Auto,
            1000
        );

}


async function cargarConfiguracionR16Auto() {

    const activo =
        document.getElementById("r16AutoActivo");

    const intervalo =
        document.getElementById("r16AutoIntervalo");

    const u8 =
        document.getElementById("r16AutoU8");

    const u9 =
        document.getElementById("r16AutoU9");

    const ultima =
        document.getElementById("r16AutoUltima");

    const proxima =
        document.getElementById("r16AutoProxima");

    const resultado =
        document.getElementById("r16AutoResultado");

    const estado =
        document.getElementById("estadoR16Auto");

    if (
        !activo ||
        !intervalo ||
        !u8 ||
        !u9 ||
        !ultima ||
        !proxima ||
        !resultado ||
        !estado
    ) {
        return;
    }

    estado.innerHTML = `
        <span class="badge text-bg-secondary">
            Cargando...
        </span>
    `;

    try {

        const response =
            await fetch(
                "/api/configuracion/r16-auto"
            );

        const datos =
            await response.json();

        if (!response.ok) {

            throw new Error(
                datos.detail ||
                "Error cargando configuracion R1.6 automatica"
            );

        }

        activo.checked =
            Boolean(datos.activo);

        intervalo.value =
            datos.intervalo_minutos ?? 30;

        u8.checked =
            Boolean(datos.actualizar_u8);

        u9.checked =
            Boolean(datos.actualizar_u9);

        ultima.textContent =
            formatearFechaR16Auto(
                datos.ultima_ejecucion
            );

        proxima.textContent =
            formatearFechaR16Auto(
                datos.proxima_ejecucion
            );

        iniciarContadorR16Auto(
            datos.proxima_ejecucion
        );

        resultado.textContent =
            datos.ultima_respuesta || "-";

        estado.innerHTML = `
            <span class="badge ${
                datos.activo
                    ? "text-bg-success"
                    : "text-bg-secondary"
            }">
                ${
                    datos.activo
                        ? "Automatizacion activa"
                        : "Automatizacion desactivada"
                }
            </span>
        `;

    }
    catch (error) {

        console.error(
            "Error cargando configuracion R1.6 automatica:",
            error
        );

        estado.innerHTML = `
            <span class="badge text-bg-danger">
                ${error.message}
            </span>
        `;

    }

}


async function guardarConfiguracionR16Auto() {

    const activo =
        document.getElementById("r16AutoActivo");

    const intervalo =
        document.getElementById("r16AutoIntervalo");

    const u8 =
        document.getElementById("r16AutoU8");

    const u9 =
        document.getElementById("r16AutoU9");

    const boton =
        document.getElementById("btnGuardarR16Auto");

    const estado =
        document.getElementById("estadoR16Auto");

    if (
        !activo ||
        !intervalo ||
        !u8 ||
        !u9 ||
        !boton ||
        !estado
    ) {
        return;
    }

    const minutos =
        Number(intervalo.value);

    if (
        !Number.isInteger(minutos) ||
        minutos < 5 ||
        minutos > 1440
    ) {

        estado.innerHTML = `
            <span class="badge text-bg-danger">
                Intervalo invalido: use entre 5 y 1440 minutos
            </span>
        `;

        return;
    }

    if (
        !u8.checked &&
        !u9.checked
    ) {

        estado.innerHTML = `
            <span class="badge text-bg-danger">
                Seleccione al menos U8 o U9
            </span>
        `;

        return;
    }

    const textoOriginal =
        boton.innerHTML;

    boton.disabled = true;

    boton.innerHTML = `
        <span
            class="spinner-border spinner-border-sm me-2"
            role="status">
        </span>
        Guardando...
    `;

    try {

        const response =
            await fetch(
                "/api/configuracion/r16-auto",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify(
                        {
                            activo:
                                activo.checked,

                            intervalo_minutos:
                                minutos,

                            actualizar_u8:
                                u8.checked,

                            actualizar_u9:
                                u9.checked
                        }
                    )
                }
            );

        const datos =
            await response.json();

        if (!response.ok) {

            throw new Error(
                datos.detail ||
                "Error guardando configuracion R1.6 automatica"
            );

        }

        estado.innerHTML = `
            <span class="badge text-bg-success">
                Configuracion guardada
            </span>
        `;

        await cargarConfiguracionR16Auto();

    }
    catch (error) {

        console.error(
            "Error guardando configuracion R1.6 automatica:",
            error
        );

        estado.innerHTML = `
            <span class="badge text-bg-danger">
                ${error.message}
            </span>
        `;

    }
    finally {

        boton.disabled = false;

        boton.innerHTML =
            textoOriginal;

    }

}


/* ==========================================================
   INICIALIZACION
   ========================================================== */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        cargarCredencialSinoptico();

        configurarPasswordSinoptico();

        cargarConfiguracionR16Auto();

        const botonGuardar =
            document.getElementById(
                "btnGuardarSinoptico"
            );

        if (botonGuardar) {

            botonGuardar.addEventListener(
                "click",
                guardarCredencialSinoptico
            );

        }

        const botonGuardarR16Auto =
            document.getElementById(
                "btnGuardarR16Auto"
            );

        if (botonGuardarR16Auto) {

            botonGuardarR16Auto.addEventListener(
                "click",
                guardarConfiguracionR16Auto
            );

        }

    }
);

