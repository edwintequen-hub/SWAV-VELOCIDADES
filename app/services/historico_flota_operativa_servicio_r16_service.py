"""
=============================================================================
SWAV
HISTORICO FLOTA OPERATIVA POR SERVICIO DESDE R1.6 ORIGINAL
=============================================================================

MODULO INDEPENDIENTE DE VELOCIDADES.

FUENTE:
    R1.6 ORIGINAL COMPLETO.

REGLA PRINCIPAL:
    FECHA + PERIODO + PPU + SERVICIO = 1 presencia por servicio.

REGLA TERMINAL:
    FECHA + PERIODO + PPU sigue siendo la base para contar
    la flota operativa total del terminal.

IMPORTANTE:
    Una PPU puede aparecer en mas de un servicio dentro del
    mismo periodo. Eso NO debe duplicar el total del terminal.

NO USA:
    Expedicion
    PreparadorR16
    MotorComparacion
    Velocidad
    Registro
    HistoricoRegistro
    HistoricoPPU
    IP
    IE
    reduccion
    clasificacion

No descarta registros por:
    velocidad = 0
    FIN SERVICIO = 1900

=============================================================================
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func

from app.models import (
    HistoricoFlotaOperativaServicio,
)

from app.services.flota_operativa_r16_service import (
    leer_r16_completo,
    normalizar_ppu,
)

from app.services.historico_flota_operativa_r16_service import (
    convertir_fecha_hora,
    obtener_fecha_operacional,
    obtener_periodo,
    obtener_catalogo,
)


def normalizar_servicio(valor):

    return str(
        valor or ""
    ).strip().upper()


def procesar_r16_servicios(
    db,
    archivo,
    unidad=None,
):

    lectura = leer_r16_completo(
        archivo=archivo,
        unidad=unidad,
    )

    filas = lectura[
        "filas"
    ]

    grupos = defaultdict(
        list
    )

    descartados_sin_ppu = 0
    descartados_sin_fecha = 0
    descartados_sin_periodo = 0
    descartados_sin_servicio = 0


    # =====================================================================
    # AGRUPAR R1.6 COMPLETO
    # =====================================================================

    for fila in filas:

        ppu = normalizar_ppu(
            fila.get(
                "PATENTE BUS"
            )
        )

        if not ppu:

            descartados_sin_ppu += 1
            continue


        fecha_operacional = (
            obtener_fecha_operacional(
                fila
            )
        )

        if fecha_operacional is None:

            descartados_sin_fecha += 1
            continue


        periodo = obtener_periodo(
            fila
        )

        if periodo is None:

            descartados_sin_periodo += 1
            continue


        servicio = normalizar_servicio(
            fila.get(
                "SERVICIO"
            )
        )

        if not servicio:

            descartados_sin_servicio += 1
            continue


        clave = (
            fecha_operacional,
            periodo,
            ppu,
            servicio,
        )

        grupos[
            clave
        ].append(
            fila
        )


    # =====================================================================
    # CATALOGO TERMINALES
    # =====================================================================

    catalogo = obtener_catalogo(
        db
    )


    fechas = sorted(
        {
            clave[0]
            for clave in grupos
        }
    )


    # =====================================================================
    # EXISTENTES
    # =====================================================================

    existentes = {}

    if fechas:

        filas_existentes = (
            db.query(
                HistoricoFlotaOperativaServicio
            )
            .filter(
                HistoricoFlotaOperativaServicio.fecha.in_(
                    fechas
                )
            )
            .all()
        )

        existentes = {
            (
                fila.fecha,
                fila.periodo,
                normalizar_ppu(
                    fila.ppu
                ),
                normalizar_servicio(
                    fila.servicio
                ),
            ):
            fila
            for fila in filas_existentes
        }


    insertados = 0
    actualizados = 0

    con_terminal_nuevos = 0
    sin_terminal_nuevos = 0


    archivo_origen = str(
        lectura[
            "archivo"
        ]
    )


    # =====================================================================
    # UPSERT
    # =====================================================================

    for clave, registros in grupos.items():

        (
            fecha_operacional,
            periodo,
            ppu,
            servicio,
        ) = clave


        inicios = [

            convertir_fecha_hora(
                fila.get(
                    "INICIO SERVICIO"
                )
            )

            for fila in registros
        ]


        inicios = [
            valor
            for valor in inicios
            if valor is not None
        ]


        primera = (
            min(inicios)
            if inicios
            else None
        )

        ultima = (
            max(inicios)
            if inicios
            else None
        )


        existente = existentes.get(
            clave
        )


        # =================================================================
        # ACTUALIZAR
        # =================================================================

        if existente is not None:

            if primera is not None:

                if (
                    existente.primera_transmision
                    is None
                    or
                    primera
                    <
                    existente.primera_transmision
                ):

                    existente.primera_transmision = (
                        primera
                    )


            if ultima is not None:

                if (
                    existente.ultima_transmision
                    is None
                    or
                    ultima
                    >
                    existente.ultima_transmision
                ):

                    existente.ultima_transmision = (
                        ultima
                    )


            cantidad_actual = (
                existente
                .cantidad_registros_fuente
                or 0
            )

            cantidad_nueva = len(
                registros
            )

            # R1.6 es fotografia acumulativa.
            # No sumar descargas sucesivas.
            existente.cantidad_registros_fuente = max(
                cantidad_actual,
                cantidad_nueva,
            )


            archivos_previos = {
                parte.strip()

                for parte in str(
                    existente.archivo_origen
                    or ""
                ).split("|")

                if parte.strip()
            }

            archivos_previos.add(
                archivo_origen
            )

            existente.archivo_origen = (
                " | ".join(
                    sorted(
                        archivos_previos
                    )
                )
            )

            actualizados += 1

            continue


        # =================================================================
        # NUEVO
        # =================================================================

        asignacion = catalogo.get(
            ppu
        )


        terminal = None

        unidad_registro = (
            str(
                unidad or ""
            )
            .strip()
            .upper()
            or None
        )


        if asignacion is not None:

            con_terminal_nuevos += 1

            terminal = getattr(
                asignacion,
                "terminal",
                None,
            )

            unidad_catalogo = getattr(
                asignacion,
                "unidad",
                None,
            )

            if unidad_catalogo:

                unidad_registro = (
                    unidad_catalogo
                )

        else:

            sin_terminal_nuevos += 1


        nuevo = (
            HistoricoFlotaOperativaServicio(
                fecha=fecha_operacional,
                periodo=periodo,
                ppu=ppu,
                servicio=servicio,
                unidad=unidad_registro,
                terminal=terminal,
                primera_transmision=primera,
                ultima_transmision=ultima,
                cantidad_registros_fuente=len(
                    registros
                ),
                archivo_origen=archivo_origen,
            )
        )


        db.add(
            nuevo
        )

        existentes[
            clave
        ] = nuevo

        insertados += 1


    db.commit()


    # =====================================================================
    # RESULTADOS POR FECHA
    # =====================================================================

    resultados_fecha = {}

    for fecha_operacional in fechas:

        total = (
            db.query(
                func.count(
                    HistoricoFlotaOperativaServicio.id
                )
            )
            .filter(
                HistoricoFlotaOperativaServicio.fecha
                ==
                fecha_operacional
            )
            .scalar()
        ) or 0


        ppu_unicas = (
            db.query(
                func.count(
                    func.distinct(
                        HistoricoFlotaOperativaServicio.ppu
                    )
                )
            )
            .filter(
                HistoricoFlotaOperativaServicio.fecha
                ==
                fecha_operacional
            )
            .scalar()
        ) or 0


        servicios = (
            db.query(
                func.count(
                    func.distinct(
                        HistoricoFlotaOperativaServicio.servicio
                    )
                )
            )
            .filter(
                HistoricoFlotaOperativaServicio.fecha
                ==
                fecha_operacional
            )
            .scalar()
        ) or 0


        resultados_fecha[
            str(
                fecha_operacional
            )
        ] = {
            "presencias_servicio":
                int(total),

            "ppu_unicas":
                int(ppu_unicas),

            "servicios_unicos":
                int(servicios),
        }


    return {
        "estado":
            "OK",

        "fuente":
            "R1.6_COMPLETO",

        "archivo":
            archivo_origen,

        "unidad":
            (
                str(unidad)
                .strip()
                .upper()
                if unidad
                else None
            ),

        "filas_r16":
            len(filas),

        "ppu_unicas_r16":
            lectura[
                "ppu_unicas"
            ],

        "presencias_servicio_calculadas":
            len(grupos),

        "insertados":
            insertados,

        "actualizados":
            actualizados,

        "con_terminal_nuevos":
            con_terminal_nuevos,

        "sin_terminal_nuevos":
            sin_terminal_nuevos,

        "descartados_sin_ppu":
            descartados_sin_ppu,

        "descartados_sin_fecha":
            descartados_sin_fecha,

        "descartados_sin_periodo":
            descartados_sin_periodo,

        "descartados_sin_servicio":
            descartados_sin_servicio,

        "resultado_por_fecha":
            resultados_fecha,
    }
