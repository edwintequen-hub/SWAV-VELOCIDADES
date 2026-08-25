
/*
=========================================================
SWAV
REPORTES HISTORICOS
=========================================================
*/

document.addEventListener(
    "DOMContentLoaded",
    () => {


        const btnConsultar =
            document.getElementById(
                "btnConsultar"
            );


        const btnLimpiar =
            document.getElementById(
                "btnLimpiar"
            );


        const btnExcel =
            document.getElementById(
                "btnExcel"
            );


        const totalRegistros =
            document.getElementById(
                "totalRegistros"
            );


        const totalOk =
            document.getElementById(
                "totalOk"
            );


        const totalSimples =
            document.getElementById(
                "totalSimples"
            );


        const totalComplejos =
            document.getElementById(
                "totalComplejos"
            );


        const tablaResumen =
            document.getElementById(
                "tablaResumen"
            );


        const tablaPPU =
            document.getElementById(
                "tablaPPU"
            );


        const tablaExpediciones =
            document.getElementById(
                "tablaExpediciones"
            );



        async function consultarReportes(){


            try {


                const params =
                    new URLSearchParams();



                const fechaDesde =
                    document.getElementById(
                        "fechaDesde"
                    ).value;


                const fechaHasta =
                    document.getElementById(
                        "fechaHasta"
                    ).value;


                const unidad =
                    document.getElementById(
                        "unidad"
                    ).value;


                const tipoDia =
                    document.getElementById(
                        "tipoDia"
                    ).value;


                const servicioUsuario =
                    document.getElementById(
                        "servicioUsuario"
                    ).value;


                const servicioEmpresa =
                    document.getElementById(
                        "servicioEmpresa"
                    ).value;


                const indicador =
                    document.getElementById(
                        "indicador"
                    ).value;


                const clasificacion =
                    document.getElementById(
                        "clasificacion"
                    ).value;



                if(fechaDesde)
                    params.append(
                        "fecha_desde",
                        fechaDesde
                    );


                if(fechaHasta)
                    params.append(
                        "fecha_hasta",
                        fechaHasta
                    );


                if(unidad)
                    params.append(
                        "unidad",
                        unidad
                    );


                if(tipoDia)
                    params.append(
                        "tipo_dia",
                        tipoDia
                    );


                if(servicioUsuario)
                    params.append(
                        "servicio_usuario",
                        servicioUsuario
                    );


                if(servicioEmpresa)
                    params.append(
                        "servicio_empresa",
                        servicioEmpresa
                    );


                if(indicador)
                    params.append(
                        "indicador",
                        indicador
                    );


                if(clasificacion)
                    params.append(
                        "clasificacion",
                        clasificacion
                    );



                const url =
                    "/reportes/resumen?"
                    +
                    params.toString();



                const respuesta =
                    await fetch(
                        url
                    );



                if(!respuesta.ok){

                    throw new Error(
                        "Error consulta reportes"
                    );

                }



                const datos =
                    await respuesta.json();

                const respuestaPPU =
                    await fetch(
                        "/reportes/ppu?"
                        +
                        params.toString()
                    );


                if(!respuestaPPU.ok){

                    throw new Error(
                        "Error consulta PPU"
                    );

                }


                const datosPPU =
                    await respuestaPPU.json();





                pintarResumen(
                    datos
                );

                pintarPPU(
                    datosPPU
                );




            }
            catch(error){

                console.error(
                    error
                );

                alert(
                    "Error cargando reportes"
                );

            }


        }



        function pintarResumen(
            datos
        ){


            let filas =
                Array.isArray(datos)
                ?
                datos
                :
                datos.registros
                ??
                [];



            totalRegistros.textContent =
                filas.length;



            totalOk.textContent =
                filas.filter(
                    x =>
                    x.clasificacion
                    ===
                    "OK"
                ).length;



            totalSimples.textContent =
                filas.filter(
                    x =>
                    x.clasificacion
                    ===
                    "SIMPLE"
                ).length;



            totalComplejos.textContent =
                filas.filter(
                    x =>
                    x.clasificacion
                    ===
                    "COMPLEJO"
                ).length;



            tablaResumen.innerHTML =
                "";



            if(
                filas.length
                ===
                0
            ){

                tablaResumen.innerHTML = `
                    <tr>
                        <td colspan="12"
                            class="text-center">
                            Sin datos
                        </td>
                    </tr>
                `;

                return;

            }



            filas.forEach(
                r => {


                    const claseClasificacion =
                        r.clasificacion === "COMPLEJO"
                            ? "clasificacion-complejo"
                            : r.clasificacion === "SIMPLE"
                            ? "clasificacion-simple"
                            : "clasificacion-ok";


                    tablaResumen.innerHTML += `

                    <tr>

                        <td>${r.fecha_operacional ?? "-"}</td>

                        <td>${r.unidad ?? "-"}</td>

                        <td>${r.tipo_dia ?? "-"}</td>

                        <td>${r.servicio_usuario ?? "-"}</td>

                        <td>${r.codigo_ts ?? "-"}</td>

                        <td>${r.servicio_empresa ?? "-"}</td>


                        <td>${r.sentido ?? "-"}</td>

                        <td>${r.periodo ?? "-"}</td>

                        <td>${r.expediciones ?? "-"}</td>

                        <td>${r.buses ?? "-"}</td>

                        <td>${r.velocidad_real != null ? Number(r.velocidad_real).toFixed(2) : "-"}</td>

                        <td>${r.velocidad_teorica != null ? Number(r.velocidad_teorica).toFixed(2) : "-"}</td>

                        <td>${r.reduccion != null ? Number(r.reduccion).toFixed(2) + " %" : "-"}</td>

                        <td>${r.indicador ?? "-"}</td>

                        <td><span class="${claseClasificacion}">${r.clasificacion ?? "-"}</span></td>

                        <td>${r.informar ? "SI" : "NO"}</td>

                        <td>${r.estado ?? "-"}</td>

                    </tr>

                    `;


                }
            );



        }




        function pintarPPU(datos){

            const filas =
                Array.isArray(datos)
                ? datos
                : (datos.ppu ?? []);

            if(!tablaPPU){
                return;
            }

            if(filas.length === 0){

                tablaPPU.innerHTML = `
                    <tr>
                        <td colspan="12"
                            class="text-center text-secondary py-4">
                            Sin datos PPU.
                        </td>
                    </tr>
                `;

                return;
            }

            const html = filas.map(

                p => {

                    const claseClasificacion =
                        p.clasificacion === "COMPLEJO"
                            ? "clasificacion-complejo"
                            : p.clasificacion === "SIMPLE"
                            ? "clasificacion-simple"
                            : "clasificacion-ok";

                    return `
                        <tr>

                            <td>${p.fecha_operacional ?? "-"}</td>

                            <td>${p.servicio_usuario ?? "-"}</td>

                            <td>${p.servicio_empresa ?? "-"}</td>

                            <td>${p.periodo ?? "-"}</td>

                            <td><strong>${p.patente ?? "-"}</strong></td>

                            <td>${p.inicio_servicio ?? "-"}</td>

                            <td>${p.fin_servicio ?? "-"}</td>

                            <td>${p.velocidad_real != null ? Number(p.velocidad_real).toFixed(2) : "-"}</td>

                            <td>${p.velocidad_teorica != null ? Number(p.velocidad_teorica).toFixed(2) : "-"}</td>

                            <td>${p.reduccion != null ? Number(p.reduccion).toFixed(2) + " %" : "-"}</td>

                            <td>${p.indicador ?? "-"}</td>

                            <td>
                                <span class="${claseClasificacion}">
                                    ${p.clasificacion ?? "-"}
                                </span>
                            </td>

                        </tr>
                    `;

                }

            ).join("");


            tablaPPU.innerHTML = html;

        }


        btnConsultar?.addEventListener(
            "click",
            consultarReportes
        );



        btnLimpiar?.addEventListener(
            "click",
            () => {


                document
                .querySelectorAll(
                    "input,select"
                )
                .forEach(
                    e =>
                    e.value=""
                );


                tablaResumen.innerHTML =
                `
                <tr>
                    <td colspan="12"
                    class="text-center text-secondary py-4">
                    Sin consulta.
                    </td>
                </tr>
                `;


                totalRegistros.textContent=0;
                totalOk.textContent=0;
                totalSimples.textContent=0;
                totalComplejos.textContent=0;


            }
        );



        btnExcel?.addEventListener(
            "click",
            () => {

                window.location.href =
                    "/reportes/excel";

            }
        );



    }
);








