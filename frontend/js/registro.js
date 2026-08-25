/*
=========================================================
SWAV
Sistema Web de Análisis de Velocidades
=========================================================

Registro Operacional

Autor   : Edwin
Empresa : Metropol
Versión : 1.0

=========================================================
*/

let graficoRegistro = null;


// =========================================================
// CARGAR REGISTRO
// =========================================================

async function cargarRegistro(servicio, periodo){

    const response = await fetch(

        `/api/registro?servicio=${encodeURIComponent(servicio)}&periodo=${periodo}`

    );

    if(!response.ok){

    console.error("Error al cargar el registro.");

    return;

}

const datos = await response.json();

if(!datos){

    return;

}

cargarCabecera(datos.cabecera);

cargarDetalle(datos.detalle);

crearGrafico(datos.detalle);

}


// =========================================================
// CABECERA
// =========================================================

function cargarCabecera(c){

    if(!c) return;

    document.getElementById("lblServicio").textContent =
        c.servicio;

    document.getElementById("lblRuta").textContent =
        c.ruta;

    document.getElementById("lblPeriodo").textContent =
        periodoAHora(c.periodo);

    document.getElementById("lblEstado").textContent =
        c.estado;

    document.getElementById("lblExpediciones").textContent =
        c.expediciones;

    document.getElementById("lblBuses").textContent =
        c.buses;

    document.getElementById("lblVelReal").textContent =
        Number(c.velocidad_real).toFixed(1);

    document.getElementById("lblVelTeorica").textContent =
        Number(c.velocidad_teorica).toFixed(1);

}


// =========================================================
// TABLA
// =========================================================

function cargarDetalle(detalle){

    const tbody =

        document.getElementById("tbodyRegistro");

    tbody.innerHTML = "";

    detalle.forEach(fila => {

        const reduccion = Number(fila.reduccion) || 0;

        let estado = "🟢 OK";

        if (reduccion > 29){

            estado = "🔴 COMPLEJO";

        }
        else if (reduccion > 10){

            estado = "🟡 SIMPLE";

        }

    tbody.innerHTML += `

        <tr>

            <td>${fila.patente}</td>

            <td>${fila.inicio}</td>

            <td>${fila.fin}</td>

            <td>${Number(fila.velocidad_real).toFixed(1)}</td>

            <td>${Number(fila.velocidad_teorica).toFixed(1)}</td>

            <td>${reduccion.toFixed(1)}%</td>

            <td class="estado ${estado.includes('OK') ? 'ok' : estado.includes('SIMPLE') ? 'simple' : 'complejo'}">

            ${estado}

            </td>

        </tr>

    `;

});

}


// =========================================================
// GRAFICO
// =========================================================

function crearGrafico(detalle){

    const ctx =

        document.getElementById("graficoRegistro");

    if(graficoRegistro)

        graficoRegistro.destroy();

    graficoRegistro = new Chart(ctx,{

        type:"bar",

        data:{

            labels:

                detalle.map(x=>x.patente),

            datasets:[

                {

                    label:"Velocidad Real",

                    data:

                        detalle.map(

                            x=>x.velocidad_real

                        )

                },

                {

                    label:"Velocidad Teórica",

                    data:

                        detalle.map(

                            x=>x.velocidad_teorica

                        )

                }

            ]

        },

        options:{

            responsive:true,

            maintainAspectRatio:false

        }

    });

}


// =========================================================
// PERIODO
// =========================================================

function periodoAHora(periodo){

    const horas =

        Math.floor(periodo / 60);

    const minutos =

        periodo % 60;

    return (

        String(horas).padStart(2,"0")

        + ":"

        +

        String(minutos).padStart(2,"0")

    );

}