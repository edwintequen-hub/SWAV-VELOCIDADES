from collections import defaultdict
from datetime import datetime, time
import re
import time as _fo_time

from sqlalchemy import func
from sqlalchemy.exc import OperationalError as _FOOperationalError

from app.models import (
    Expedicion,
    HistoricoFlotaOperativa,
    FlotaAsignacionTerminal,
)


# =============================================================================
# HISTORICO FLOTA OPERATIVA
# =============================================================================
#
# MODULO INDEPENDIENTE DE VELOCIDADES.
#
# Fuente:
#     Expedicion proveniente del R1.6 automatico.
#
# Regla:
#     FECHA + PERIODO + PPU = 1 presencia operativa.
#
# No elimina ni modifica expediciones R1.6.
#
# El procesamiento usa una fotografia por ID maximo de Expedicion.
# Si durante la ejecucion llegan nuevas expediciones, quedan para la
# proxima ejecucion.
# =============================================================================


def normalizar_ppu(valor):
    return re.sub(
        r"[^A-Z0-9]",
        "",
        str(valor or "").strip().upper()
    )


def obtener_periodo(expedicion):

    periodo = getattr(
        expedicion,
        "periodo",
        None
    )

    if periodo is not None:

        try:

            periodo = int(periodo)

            if 1 <= periodo <= 24:
                return periodo

        except Exception:
            pass

    inicio = getattr(
        expedicion,
        "inicio_servicio",
        None
    )

    if inicio is not None:

        try:
            return int(inicio.hour) + 1
        except Exception:
            pass

    return None


def convertir_datetime(fecha, valor):

    if valor is None:
        return None

    if isinstance(valor, datetime):
        return valor

    if isinstance(valor, time):
        return datetime.combine(
            fecha,
            valor
        )

    return None


def _catalogo_asignacion(db):

    filas = (
        db.query(FlotaAsignacionTerminal)
        .order_by(FlotaAsignacionTerminal.id)
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


def _obtener_plazas(registros):

    valores = []

    for registro in registros:

        valor = getattr(
            registro,
            "plazas",
            None
        )

        if valor is None:
            continue

        try:
            valores.append(
                int(valor)
            )
        except Exception:
            pass

    if not valores:
        return None

    return valores[-1]


def _procesar_fecha_una_vez(
    db,
    fecha,
    max_expedicion_id=None
):

    # -------------------------------------------------------------------------
    # 1. FOTOGRAFIA ESTABLE DE EXPEDICION
    # -------------------------------------------------------------------------

    if max_expedicion_id is None:

        max_id = (
            db.query(
                func.max(
                    Expedicion.id
                )
            )
            .scalar()
        )

    else:

        max_id = int(
            max_expedicion_id
        )

    if max_id is None:

        return {
            "fecha": str(fecha),
            "max_expedicion_id": None,
            "expediciones_fuente": 0,
            "presencias_calculadas": 0,
            "insertados": 0,
            "existentes": 0,
            "total_historico_fecha": 0,
            "ppu_unicas_fecha": 0,
            "registros_fuente_representados": 0,
        }

    expediciones = (
        db.query(Expedicion)
        .filter(
            Expedicion.fecha == fecha,
            Expedicion.id <= max_id,
            Expedicion.patente.isnot(None)
        )
        .order_by(
            Expedicion.id
        )
        .all()
    )

    # -------------------------------------------------------------------------
    # 2. AGRUPAR FECHA + PERIODO + PPU
    # -------------------------------------------------------------------------

    grupos = defaultdict(list)

    descartados_sin_ppu = 0
    descartados_sin_periodo = 0

    for expedicion in expediciones:

        ppu = normalizar_ppu(
            expedicion.patente
        )

        if not ppu:
            descartados_sin_ppu += 1
            continue

        periodo = obtener_periodo(
            expedicion
        )

        if periodo is None:
            descartados_sin_periodo += 1
            continue

        grupos[
            (
                fecha,
                periodo,
                ppu
            )
        ].append(
            expedicion
        )

    # -------------------------------------------------------------------------
    # 3. CATALOGO DE FLOTA VIGENTE
    # -------------------------------------------------------------------------

    catalogo = _catalogo_asignacion(
        db
    )

    # -------------------------------------------------------------------------
    # 4. HISTORICO YA EXISTENTE
    # -------------------------------------------------------------------------

    existentes_bd = (
        db.query(
            HistoricoFlotaOperativa
        )
        .filter(
            HistoricoFlotaOperativa.fecha
            == fecha
        )
        .all()
    )

    mapa_existentes = {
        (
            fila.fecha,
            fila.periodo,
            normalizar_ppu(
                fila.ppu
            )
        ): fila
        for fila in existentes_bd
    }

    insertados = 0
    ya_existentes = 0

    con_terminal = 0
    sin_terminal = 0

    # -------------------------------------------------------------------------
    # 5. INSERTAR SOLO PRESENCIAS NUEVAS
    # -------------------------------------------------------------------------

    for clave, registros in grupos.items():

        fecha_grupo, periodo, ppu = clave

        existente = mapa_existentes.get(
            clave
        )

        if existente is not None:

            # El registro ya existe.
            #
            # Actualizamos solamente informacion acumulable de la
            # fotografia actual, sin crear duplicados.

            inicios = [
                convertir_datetime(
                    fecha_grupo,
                    getattr(
                        x,
                        "inicio_servicio",
                        None
                    )
                )
                for x in registros
            ]

            inicios = [
                x
                for x in inicios
                if x is not None
            ]

            if inicios:

                nueva_primera = min(
                    inicios
                )

                nueva_ultima = max(
                    inicios
                )

                if (
                    existente.primera_transmision
                    is None
                    or nueva_primera
                    < existente.primera_transmision
                ):
                    existente.primera_transmision = (
                        nueva_primera
                    )

                if (
                    existente.ultima_transmision
                    is None
                    or nueva_ultima
                    > existente.ultima_transmision
                ):
                    existente.ultima_transmision = (
                        nueva_ultima
                    )

            existente.cantidad_registros_fuente = (
                len(registros)
            )

            archivos = sorted(
                {
                    str(
                        getattr(
                            x,
                            "archivo_origen",
                            ""
                        )
                        or ""
                    ).strip()
                    for x in registros
                    if str(
                        getattr(
                            x,
                            "archivo_origen",
                            ""
                        )
                        or ""
                    ).strip()
                }
            )

            existente.archivo_origen = (
                " | ".join(archivos)
                if archivos
                else existente.archivo_origen
            )

            plazas = _obtener_plazas(
                registros
            )

            if plazas is not None:
                existente.plazas = plazas

            ya_existentes += 1
            continue

        asignacion = catalogo.get(
            ppu
        )

        if asignacion is not None:
            con_terminal += 1
        else:
            sin_terminal += 1

        inicios = [
            convertir_datetime(
                fecha_grupo,
                getattr(
                    x,
                    "inicio_servicio",
                    None
                )
            )
            for x in registros
        ]

        inicios = [
            x
            for x in inicios
            if x is not None
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

        unidad = None

        for registro in registros:

            valor = getattr(
                registro,
                "unidad",
                None
            )

            if valor:
                unidad = valor
                break

        terminal = None
        interno = None
        tipo_bus = None
        tipo_flota = None

        if asignacion is not None:

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
                unidad = unidad_catalogo

        archivos = sorted(
            {
                str(
                    getattr(
                        x,
                        "archivo_origen",
                        ""
                    )
                    or ""
                ).strip()
                for x in registros
                if str(
                    getattr(
                        x,
                        "archivo_origen",
                        ""
                    )
                    or ""
                ).strip()
            }
        )

        archivo_origen = (
            " | ".join(
                archivos
            )
            if archivos
            else None
        )

        nuevo = HistoricoFlotaOperativa(
            fecha=fecha_grupo,
            periodo=periodo,
            ppu=ppu,
            unidad=unidad,
            terminal=terminal,
            interno=interno,
            tipo_bus=tipo_bus,
            tipo_flota=tipo_flota,
            plazas=_obtener_plazas(
                registros
            ),
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

        mapa_existentes[
            clave
        ] = nuevo

        insertados += 1

    db.commit()

    # -------------------------------------------------------------------------
    # 6. CERTIFICACION CONTRA LA MISMA FOTOGRAFIA
    # -------------------------------------------------------------------------

    total_historico = (
        db.query(
            func.count(
                HistoricoFlotaOperativa.id
            )
        )
        .filter(
            HistoricoFlotaOperativa.fecha
            == fecha
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
            == fecha
        )
        .scalar()
    ) or 0

    suma_fuente = (
        db.query(
            func.sum(
                HistoricoFlotaOperativa
                .cantidad_registros_fuente
            )
        )
        .filter(
            HistoricoFlotaOperativa.fecha
            == fecha
        )
        .scalar()
    ) or 0

    return {
        "fecha": str(fecha),
        "max_expedicion_id": int(
            max_id
        ),
        "expediciones_fuente": len(
            expediciones
        ),
        "presencias_calculadas": len(
            grupos
        ),
        "descartados_sin_ppu": (
            descartados_sin_ppu
        ),
        "descartados_sin_periodo": (
            descartados_sin_periodo
        ),
        "insertados": insertados,
        "existentes": ya_existentes,
        "con_terminal_nuevos": (
            con_terminal
        ),
        "sin_terminal_nuevos": (
            sin_terminal
        ),
        "total_historico_fecha": int(
            total_historico
        ),
        "ppu_unicas_fecha": int(
            ppu_unicas
        ),
        "registros_fuente_representados": int(
            suma_fuente
        ),
    }



# =============================================================================
# CONTROL DE CONCURRENCIA SQLITE
# =============================================================================
#
# SQLite permite varios lectores, pero un solo escritor simultaneo.
#
# Si el importador automatico R1.6 esta escribiendo justo cuando Flota
# Operativa intenta guardar su historico:
#
#   1. se hace rollback de ESTA transaccion;
#   2. se espera unos segundos;
#   3. se reconstruye la fotografia;
#   4. se vuelve a intentar;
#   5. UNIQUE(fecha, periodo, ppu) sigue protegiendo contra duplicidad.
#
# No modifica Velocidades.
# =============================================================================


def procesar_fecha_con_reintentos_marker():
    """
    Marcador interno para certificar que esta version
    contiene manejo de concurrencia SQLite.
    """
    return True


def procesar_fecha(
    db,
    fecha,
    max_intentos=8,
    espera_segundos=5,
    max_expedicion_id=None
):

    ultimo_error = None

    for intento in range(
        1,
        max_intentos + 1
    ):

        try:

            # Hace que SQLite espere hasta 60 segundos
            # antes de declarar que la base sigue bloqueada.
            db.execute(
                __import__(
                    "sqlalchemy"
                ).text(
                    "PRAGMA busy_timeout = 60000"
                )
            )

            resultado = _procesar_fecha_una_vez(
                db,
                fecha,
                max_expedicion_id=max_expedicion_id
            )

            resultado[
                "intento_sqlite"
            ] = intento

            resultado[
                "reintentos_sqlite"
            ] = intento - 1

            return resultado

        except _FOOperationalError as error:

            db.rollback()

            ultimo_error = error

            texto_error = str(
                error
            ).lower()

            es_bloqueo = (
                "database is locked"
                in texto_error
                or
                "database table is locked"
                in texto_error
            )

            if not es_bloqueo:
                raise

            print()
            print(
                "[FLOTA OPERATIVA] "
                f"SQLite ocupado. Intento "
                f"{intento}/{max_intentos}."
            )

            if intento >= max_intentos:
                break

            print(
                "[FLOTA OPERATIVA] "
                f"Esperando {espera_segundos} "
                "segundos antes de reintentar..."
            )

            _fo_time.sleep(
                espera_segundos
            )

        except Exception:

            db.rollback()
            raise

    raise RuntimeError(
        "FLOTA OPERATIVA: SQLite permanecio "
        f"bloqueado despues de {max_intentos} intentos. "
        "No se guardo una carga parcial."
    ) from ultimo_error

