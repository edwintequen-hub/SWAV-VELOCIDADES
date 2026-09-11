"""
=============================================================================
SWAV
HISTORICO FLOTA OPERATIVA DESDE R1.6 ORIGINAL
=============================================================================

MODULO TOTALMENTE INDEPENDIENTE DE VELOCIDADES.

FUENTE:
    archivo R1.6 original completo.

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

REGLA:
    FECHA + PERIODO + PPU = 1 presencia operativa.

Las filas con velocidad 0 o FIN SERVICIO 1900
NO se eliminan por esas condiciones.

=============================================================================
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, date
import time as _fo_time

from sqlalchemy import func, text
from sqlalchemy.exc import OperationalError

from app.models import (
    HistoricoFlotaOperativa,
    FlotaAsignacionTerminal,
)

from app.services.flota_operativa_r16_service import (
    leer_r16_completo,
    normalizar_ppu,
)


# =============================================================================
# DATETIME R1.6
# =============================================================================

_FORMATOS_FECHA_HORA = (
    "%d/%m/%Y %H:%M:%S",
    "%d-%m-%Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
)


def convertir_fecha_hora(valor):

    texto_valor = str(
        valor or ""
    ).strip()

    if not texto_valor:
        return None

    for formato in _FORMATOS_FECHA_HORA:

        try:

            return datetime.strptime(
                texto_valor,
                formato
            )

        except ValueError:
            pass

    return None


def obtener_fecha_operacional(fila):

    inicio = convertir_fecha_hora(
        fila.get(
            "INICIO SERVICIO"
        )
    )

    if inicio is None:
        return None

    return inicio.date()


def obtener_periodo(fila):

    inicio = convertir_fecha_hora(
        fila.get(
            "INICIO SERVICIO"
        )
    )

    if inicio is None:
        return None

    return int(
        inicio.hour
    ) + 1


# =============================================================================
# PLAZAS
# =============================================================================

def obtener_plazas(registros):

    valores = []

    for fila in registros:

        valor = str(
            fila.get(
                "PLAZAS",
                ""
            )
            or ""
        ).strip()

        if not valor:
            continue

        try:

            valores.append(
                int(
                    float(
                        valor.replace(
                            ",",
                            "."
                        )
                    )
                )
            )

        except Exception:
            pass

    if not valores:
        return None

    return valores[-1]


# =============================================================================
# CATALOGO
# =============================================================================

def obtener_catalogo(db):

    filas = (
        db.query(
            FlotaAsignacionTerminal
        )
        .order_by(
            FlotaAsignacionTerminal.id
        )
        .all()
    )

    resultado = {}

    for fila in filas:

        ppu = normalizar_ppu(
            getattr(
                fila,
                "ppu",
                None
            )
        )

        if ppu:
            resultado[ppu] = fila

    return resultado


# =============================================================================
# PROCESAMIENTO UNA VEZ
# =============================================================================

def _procesar_archivo_una_vez(
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

        grupos[
            (
                fecha_operacional,
                periodo,
                ppu,
            )
        ].append(
            fila
        )


    catalogo = obtener_catalogo(
        db
    )

    fechas = sorted(
        {
            clave[0]
            for clave in grupos
        }
    )

    existentes = {}

    if fechas:

        filas_existentes = (
            db.query(
                HistoricoFlotaOperativa
            )
            .filter(
                HistoricoFlotaOperativa.fecha.in_(
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
                )
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


    for clave, registros in grupos.items():

        fecha_operacional, periodo, ppu = clave

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

        plazas = obtener_plazas(
            registros
        )

        asignacion = catalogo.get(
            ppu
        )


        fila_existente = existentes.get(
            clave
        )


        if fila_existente is not None:

            if primera is not None:

                if (
                    fila_existente.primera_transmision
                    is None
                    or primera
                    <
                    fila_existente.primera_transmision
                ):

                    fila_existente.primera_transmision = (
                        primera
                    )

            if ultima is not None:

                if (
                    fila_existente.ultima_transmision
                    is None
                    or ultima
                    >
                    fila_existente.ultima_transmision
                ):

                    fila_existente.ultima_transmision = (
                        ultima
                    )


            cantidad_actual = (
                fila_existente
                .cantidad_registros_fuente
                or 0
            )

            cantidad_nueva = len(
                registros
            )

            #
            # El R1.6 automatico es una fotografia acumulativa
            # del dia. No sumamos cada descarga porque
            # duplicaria artificialmente los registros.
            #
            fila_existente.cantidad_registros_fuente = max(
                cantidad_actual,
                cantidad_nueva,
            )


            if plazas is not None:

                fila_existente.plazas = (
                    plazas
                )


            archivos_previos = {
                parte.strip()
                for parte in str(
                    fila_existente.archivo_origen
                    or ""
                ).split("|")
                if parte.strip()
            }

            archivos_previos.add(
                archivo_origen
            )

            fila_existente.archivo_origen = (
                " | ".join(
                    sorted(
                        archivos_previos
                    )
                )
            )

            actualizados += 1
            continue


        terminal = None
        interno = None
        tipo_bus = None
        tipo_flota = None

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
                None
            )

            interno = getattr(
                asignacion,
                "interno",
                None
            )

            tipo_bus = getattr(
                asignacion,
                "tipo_bus",
                None
            )

            tipo_flota = getattr(
                asignacion,
                "tipo_flota",
                None
            )

            unidad_catalogo = getattr(
                asignacion,
                "unidad",
                None
            )

            if unidad_catalogo:

                unidad_registro = (
                    unidad_catalogo
                )

        else:

            sin_terminal_nuevos += 1


        nuevo = HistoricoFlotaOperativa(
            fecha=fecha_operacional,
            periodo=periodo,
            ppu=ppu,
            unidad=unidad_registro,
            terminal=terminal,
            interno=interno,
            tipo_bus=tipo_bus,
            tipo_flota=tipo_flota,
            plazas=plazas,
            primera_transmision=primera,
            ultima_transmision=ultima,
            cantidad_registros_fuente=len(
                registros
            ),
            archivo_origen=archivo_origen,
        )

        db.add(
            nuevo
        )

        existentes[
            clave
        ] = nuevo

        insertados += 1


    db.commit()


    resultados_fecha = {}

    for fecha_operacional in fechas:

        total = (
            db.query(
                func.count(
                    HistoricoFlotaOperativa.id
                )
            )
            .filter(
                HistoricoFlotaOperativa.fecha
                ==
                fecha_operacional
            )
            .scalar()
        ) or 0


        ppu_unicas = (
            db.query(
                func.count(
                    func.distinct(
                        HistoricoFlotaOperativa.ppu
                    )
                )
            )
            .filter(
                HistoricoFlotaOperativa.fecha
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
            "presencias_historicas":
                int(total),

            "ppu_unicas":
                int(ppu_unicas),
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

        "presencias_calculadas":
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

        "resultado_por_fecha":
            resultados_fecha,
    }


# =============================================================================
# CONTROL SQLITE
# =============================================================================

def procesar_archivo_r16(
    db,
    archivo,
    unidad=None,
    max_intentos=8,
    espera_segundos=5,
):

    ultimo_error = None

    for intento in range(
        1,
        max_intentos + 1
    ):

        try:

            db.execute(
                text(
                    "PRAGMA busy_timeout = 60000"
                )
            )

            resultado = (
                _procesar_archivo_una_vez(
                    db=db,
                    archivo=archivo,
                    unidad=unidad,
                )
            )

            resultado[
                "intento_sqlite"
            ] = intento

            resultado[
                "reintentos_sqlite"
            ] = intento - 1

            return resultado


        except OperationalError as error:

            db.rollback()

            ultimo_error = error

            mensaje = str(
                error
            ).lower()

            bloqueo = (
                "database is locked"
                in mensaje
                or
                "database table is locked"
                in mensaje
            )

            if not bloqueo:
                raise

            if intento >= max_intentos:
                break

            print(
                "[FLOTA OPERATIVA R1.6] "
                f"SQLite ocupado. "
                f"Intento {intento}/"
                f"{max_intentos}."
            )

            _fo_time.sleep(
                espera_segundos
            )


        except Exception:

            db.rollback()
            raise


    raise RuntimeError(
        "FLOTA OPERATIVA R1.6: "
        "SQLite permanecio bloqueado "
        f"despues de {max_intentos} intentos. "
        "No se guardo una carga parcial."
    ) from ultimo_error
