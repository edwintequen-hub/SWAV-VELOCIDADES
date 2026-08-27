/*
==========================================================
METROPOL
Configuración del Sistema
==========================================================
*/

document.addEventListener("DOMContentLoaded", () => {

    document
        .getElementById("btnInfo")
        ?.addEventListener("click", importarInfo);

    document
        .getElementById("btnAnexo3")
        ?.addEventListener("click", importarAnexo3);

    document
        .getElementById("btnAnexo4")
        ?.addEventListener("click", importarAnexo4);

    document
        .getElementById("btnR16")
        ?.addEventListener(
            "click",
            function (event) {

                event.preventDefault();

                importarR16();

            }
        );

});

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

async function importarAnexo3() {

    const archivo =
        document.getElementById(
            "archivoAnexo3"
        );

    const estado =
        document.getElementById(
            "estadoAnexo3"
        );


    if (
        !archivo ||
        !archivo.files ||
        archivo.files.length === 0
    ) {

        alert(
            "Seleccione el archivo Anexo 3."
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
                "/api/configuracion/anexo3",
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
                "✅ Anexo 3 procesado correctamente — " +
                Number(registros)
                    .toLocaleString("es-CL") +
                " registros";

        }


        alert(
            "Anexo 3 procesado correctamente.\n\n" +
            "Registros: " +
            Number(registros)
                .toLocaleString("es-CL")
        );


        archivo.value = "";


        await cargarEstadoImportaciones();


    }

    catch (error) {

        console.error(error);


        if (estado) {

            estado.innerHTML =
                "❌ Error";

        }


        alert(
            "Error procesando Anexo 3:\n" +
            error.message
        );

    }

}

// ==========================================================
// IMPORTAR ANEXO 4
// ==========================================================

async function importarAnexo4() {

    const archivo =
        document.getElementById(
            "archivoAnexo4"
        );

    const estado =
        document.getElementById(
            "estadoAnexo4"
        );


    if (
        !archivo ||
        !archivo.files ||
        archivo.files.length === 0
    ) {

        alert(
            "Seleccione el archivo Anexo 4."
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
                "/api/configuracion/anexo4",
                {
                    method: "POST",
                    body: formData
                }
            );


        const json =
            await respuesta.json();


        console.log(
            "Anexo 4 respuesta:",
            json
        );


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

                "✅ Anexo 4 procesado correctamente — " +

                Number(
                    registros
                ).toLocaleString(
                    "es-CL"
                ) +

                " registros";

        }


        alert(

            "Anexo 4 procesado correctamente.\n\n" +

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
            "Error importando Anexo 4:",
            error
        );


        if (estado) {

            estado.innerHTML =
                "❌ Error";

        }


        alert(

            "Error procesando Anexo 4:\n" +
            error.message

        );

    }

}


// ==========================================================
// IMPORTAR R1.6
// ==========================================================

async function importarR16() {

    const archivo =
        document.getElementById(
            "archivoR16"
        );

    const unidad =
        document.getElementById(
            "unidadR16"
        )?.value;

    const estado =
        document.getElementById(
            "estadoR16"
        );


    if (
        !archivo ||
        !archivo.files ||
        archivo.files.length === 0
    ) {

        alert(
            "Seleccione el archivo R1.6."
        );

        return;

    }


    if (!unidad) {

        alert(
            "Seleccione la unidad."
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
                "/api/configuracion/r16?unidad=" +
                encodeURIComponent(unidad),
                {
                    method: "POST",
                    body: formData
                }
            );


        const json =
            await respuesta.json();


        console.log(
            "R1.6 respuesta:",
            json
        );


        if (!respuesta.ok) {

            throw new Error(
                json.detail ||
                "Error importando R1.6"
            );

        }


        const registrosImportados =
            typeof json?.registro === "number"

                ? json.registro

                : (

                    json?.importacion
                        ?.registros_importados ??

                    json?.registro
                        ?.registros ??

                    json?.registros_importados ??

                    json?.registros ??

                    0

                );


        const fueraRango =
            json?.importacion
                ?.registros_fuera_rango ??

            0;


        if (estado) {

            estado.innerHTML =

                "✅ R1.6 importado correctamente — " +

                Number(
                    registrosImportados
                ).toLocaleString(
                    "es-CL"
                ) +

                " registros";

        }


        alert(

            "R1.6 procesado correctamente.\n\n" +

            "Unidad: " +
            unidad +

            "\nRegistros importados: " +

            Number(
                registrosImportados
            ).toLocaleString(
                "es-CL"
            ) +

            "\nFuera de rango: " +

            Number(
                fueraRango
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
            "Error importando R1.6:",
            error
        );


        if (estado) {

            estado.innerHTML =
                "❌ Error";

        }


        alert(

            "Error procesando R1.6:\n" +
            error.message

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
            Error cargando configuraci�n
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
            Ingrese contrase�a
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
   INICIALIZACION
   ========================================================== */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        cargarCredencialSinoptico();

        configurarPasswordSinoptico();

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

    }
);

