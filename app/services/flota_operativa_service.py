"""
SWAV - Flota Operativa

Reglas de negocio:
- Fuente operacional: expediciones R1.6/R1.16 ya persistidas en BD.
- La BD historica NO se elimina ni reemplaza.
- Una PPU puede tener multiples registros/transmisiones, pero cuenta una sola
  vez dentro del mismo periodo para la flota operativa.
- Periodo 1 = 00:00:00 a 00:59:59, ... Periodo 24 = 23:00:00 a 23:59:59.
- Una expedicion valida aporta presencia a cada periodo horario que intersecta
  su intervalo INICIO SERVICIO - FIN SERVICIO.
- FIN SERVICIO 1900 / invalido se descarta.
- La asignacion de terminal proviene del catalogo actualizado de PPU.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Iterable

from sqlalchemy import func
from sqlalchemy.orm import Session
from app.services.flota_r002_service import cargar_r002
from app.services.flota_operativa_r22_service import construir_resumen_terminal_r22
from app.services.sinoptico_r22_service import SinopticoR22Service

from app.config import CATALOGOS_DIR
from app.models import (
    Expedicion,    FlotaAsignacionTerminal,
    HistoricoFlotaOperativa,
    HistoricoFlotaOperativaServicio,
    FlotaPPUValidacion,
    Servicio,
)


CATALOGO_VERSION = "2026-08-26"
CATALOGO_CSV = CATALOGOS_DIR / "distribucion_terminales_20260826.csv"
CATALOGO_ORIGEN = "Distribucion por Terminales 26Ago2026.xlsx"


TERMINAL_LABELS = {
    "EL RETIRO": "El Retiro",
    "SANTA MARGARITA": "Santa Margarita",
    "CONDELL": "Condell",
    "SANTA MARTA": "Santa Marta",
    "AGUIRRE LUCO": "Aguirre Luco",
    "PIE ANDINO": "Pie Andino",
    "JUANITA": "Juanita",
    "SIN ASIGNAR": "Sin asignar",
}


from app.models import FlotaSnapshotR001

def _texto(valor) -> str:
    return str(valor or "").strip()


def _norm(valor) -> str:
    return _texto(valor).upper()


def _normalizar_ppu(valor) -> str:
    """
    Clave normalizada exclusivamente para cruces de PPU.

    Ejemplos:
        SJPC-45 -> SJPC45
        SJPC45  -> SJPC45
        SJPC 45 -> SJPC45

    No modifica el valor original almacenado en la BD.
    """
    texto = _norm(valor)

    return re.sub(
        r"[^A-Z0-9]",
        "",
        texto,
    )



# =====================================================================
# R11C - PRESTAMOS ENTRE PATIOS
# =====================================================================
#
# REGLA:
#   - terminal_base: catalogo vigente de PPU
#   - terminal_operativo: servicio real R1.6 -> tabla Servicio / INFO.xlsx
#
# IMPORTANTE:
#   Este bloque NO modifica HistoricoFlotaOperativaServicio.
#   Solo resuelve informacion operacional durante la consulta.
# =====================================================================


def _normalizar_ts(valor) -> str:

    return re.sub(
        r"[^A-Z0-9]",
        "",
        _norm(valor),
    )


def _construir_mapa_patios_operativos(
    db: Session,
) -> dict:

    filas = (
        db.query(
            Servicio
        )
        .all()
    )

    por_unidad = defaultdict(list)

    for fila in filas:

        unidad = _norm(
            fila.unidad
        )

        terminal = _norm(
            fila.terminal
        )

        codigo_ts = _normalizar_ts(
            fila.codigo_ts
        )

        if (
            not unidad
            or
            not terminal
            or
            not codigo_ts
        ):
            continue

        clave_ts = (
            "T"
            +
            codigo_ts
        )

        por_unidad[
            unidad
        ].append({
            "servicio_cliente":
                _texto(
                    fila.servicio
                ),
            "codigo_ts":
                codigo_ts,
            "clave_ts":
                clave_ts,
            "terminal":
                terminal,
            "ruta_ida":
                _normalizar_ts(
                    getattr(
                        fila,
                        "ruta_ida",
                        None,
                    )
                ),
            "ruta_regreso":
                _normalizar_ts(
                    getattr(
                        fila,
                        "ruta_regreso",
                        None,
                    )
                ),
        })

    return por_unidad


def _resolver_patio_operativo(
    mapa_servicios: dict,
    unidad,
    servicio_r16,
) -> dict:

    unidad_norm = _norm(
        unidad
    )

    r16 = _normalizar_ts(
        servicio_r16
    )

    if (
        not unidad_norm
        or
        not r16
    ):

        return {
            "resuelto": False,
            "terminal_operativo": None,
            "servicio_cliente": None,
            "codigo_ts": None,
            "resolucion": "SIN DATOS",
        }


    candidatos_unidad = (
        mapa_servicios.get(
            unidad_norm,
            [],
        )
    )


    # ================================================================
    # 1. COINCIDENCIA EXACTA
    # ================================================================

    exactos = [
        item
        for item in candidatos_unidad
        if item["clave_ts"] == r16
    ]

    if len(exactos) == 1:

        item = exactos[0]

        return {
            "resuelto": True,
            "terminal_operativo":
                item["terminal"],
            "servicio_cliente":
                item["servicio_cliente"],
            "codigo_ts":
                item["codigo_ts"],
            "resolucion":
                "CODIGO_TS_EXACTO",
        }


    # ================================================================
    # 2. COINCIDENCIA POR RUTA
    #    Ejemplo:
    #       R1.6 T818 E0
    #       ruta T818 E0 00I
    # ================================================================

    candidatos_ruta = []

    for item in candidatos_unidad:

        ruta_ida = (
            item["ruta_ida"]
            or ""
        )

        ruta_regreso = (
            item["ruta_regreso"]
            or ""
        )

        if (
            (
                ruta_ida
                and
                ruta_ida.startswith(
                    r16
                )
            )
            or
            (
                ruta_regreso
                and
                ruta_regreso.startswith(
                    r16
                )
            )
        ):

            candidatos_ruta.append(
                item
            )


    if candidatos_ruta:

        terminales = {
            item["terminal"]
            for item in candidatos_ruta
        }

        if len(terminales) == 1:

            servicios_cliente = sorted({
                item["servicio_cliente"]
                for item in candidatos_ruta
                if item["servicio_cliente"]
            })

            codigos_ts = sorted({
                item["codigo_ts"]
                for item in candidatos_ruta
                if item["codigo_ts"]
            })

            return {
                "resuelto": True,
                "terminal_operativo":
                    next(
                        iter(
                            terminales
                        )
                    ),
                "servicio_cliente":
                    " / ".join(
                        servicios_cliente
                    ),
                "codigo_ts":
                    " / ".join(
                        codigos_ts
                    ),
                "resolucion":
                    "RUTA",
            }


    # ================================================================
    # 3. MISMO NUMERO TS
    #
    # Solo se acepta cuando TODOS los candidatos pertenecen
    # al MISMO terminal.
    #
    # Ejemplos certificados:
    #   T807C2
    #   T830 E3
    #   T841C2
    #   T902 E3
    #   T950 E3
    # ================================================================

    numero_r16 = re.search(
        r"T(\d{3})",
        r16,
    )

    candidatos_numero = []

    if numero_r16:

        numero = (
            numero_r16.group(1)
        )

        for item in candidatos_unidad:

            numero_codigo = re.search(
                r"(\d{3})",
                item["codigo_ts"],
            )

            if (
                numero_codigo
                and
                numero_codigo.group(1)
                ==
                numero
            ):

                candidatos_numero.append(
                    item
                )


    if candidatos_numero:

        terminales = {
            item["terminal"]
            for item in candidatos_numero
        }

        if len(terminales) == 1:

            servicios_cliente = sorted({
                item["servicio_cliente"]
                for item in candidatos_numero
                if item["servicio_cliente"]
            })

            codigos_ts = sorted({
                item["codigo_ts"]
                for item in candidatos_numero
                if item["codigo_ts"]
            })

            return {
                "resuelto": True,
                "terminal_operativo":
                    next(
                        iter(
                            terminales
                        )
                    ),
                "servicio_cliente":
                    " / ".join(
                        servicios_cliente
                    ),
                "codigo_ts":
                    " / ".join(
                        codigos_ts
                    ),
                "resolucion":
                    (
                        "MISMO_NUMERO_"
                        "TERMINAL_UNICO"
                    ),
            }


        # ============================================================
        # Nunca decidir entre patios distintos.
        # ============================================================

        return {
            "resuelto": False,
            "terminal_operativo": None,
            "servicio_cliente": None,
            "codigo_ts": None,
            "resolucion":
                "MIXTO_REVISAR",
        }


    return {
        "resuelto": False,
        "terminal_operativo": None,
        "servicio_cliente": None,
        "codigo_ts": None,
        "resolucion":
            "SIN_MAPA",
    }



def _bool_csv(valor) -> bool:
    return _norm(valor) in {"1", "SI", "SÃ", "TRUE", "VERDADERO"}


def asegurar_catalogo_terminales(db: Session) -> dict:
    """Carga la version del catalogo solo si aun no existe en la BD."""

    existentes = (
        db.query(FlotaAsignacionTerminal)
        .filter(FlotaAsignacionTerminal.version == CATALOGO_VERSION)
        .count()
    )

    if existentes:
        return {
            "version": CATALOGO_VERSION,
            "registros": existentes,
            "cargado": False,
        }

    if not CATALOGO_CSV.exists():
        return {
            "version": CATALOGO_VERSION,
            "registros": 0,
            "cargado": False,
            "advertencia": f"Catalogo no encontrado: {CATALOGO_CSV}",
        }

    nuevos = []
    with CATALOGO_CSV.open("r", encoding="utf-8-sig", newline="") as fh:
        lector = csv.DictReader(fh, delimiter=";")
        for fila in lector:
            ppu = _normalizar_ppu(fila.get("ppu"))
            terminal = _norm(fila.get("terminal"))
            if not ppu or not terminal:
                continue
            nuevos.append(
                FlotaAsignacionTerminal(
                    version=CATALOGO_VERSION,
                    ppu=ppu,
                    terminal=terminal,
                    unidad=_norm(fila.get("unidad")) or None,
                    empresa=_norm(fila.get("empresa")) or None,
                    interno=_texto(fila.get("interno")) or None,
                    tipo_bus=_norm(fila.get("tipo_bus")) or None,
                    tipo_flota=_norm(fila.get("tipo_flota")) or None,
                    es_soporte=_bool_csv(fila.get("es_soporte")),
                    es_auxiliar=_bool_csv(fila.get("es_auxiliar")),
                    archivo_origen=CATALOGO_ORIGEN,
                    activo=True,
                )
            )

    if nuevos:
        db.add_all(nuevos)
        db.commit()

    return {
        "version": CATALOGO_VERSION,
        "registros": len(nuevos),
        "cargado": bool(nuevos),
    }


def _version_catalogo_actual(db: Session) -> str | None:
    asegurar_catalogo_terminales(db)
    return db.query(func.max(FlotaAsignacionTerminal.version)).scalar()


# =====================================================================
# SALIDAS REALES R1.6
# =====================================================================


# =====================================================================
# PERFIL OPERACIONAL 30 / 60 MINUTOS
# =====================================================================

def construir_perfil_operacional(
    fecha: str | date | datetime,
    unidad: str | None = None,
) -> dict:
    """
    Construye el requerimiento operacional desde:

        catalogos/perfil_operacional.xlsx
        catalogos/INFO.xlsx

    Reglas certificadas:

    60 minutos:
        perfil = suma de MAXIMO_HORA por servicio,
        contado una sola vez por servicio/periodo.

    30 minutos:
        perfil = suma de DATO de la media hora exacta.

    Tipo de dia:
        lunes-viernes -> LABORAL
        sabado        -> SABADO
        domingo       -> DOMINGO

    INFO.xlsx se utiliza exclusivamente para resolver:
        unidad + servicio -> terminal

    Esta funcion NO modifica BD ni archivos.
    """

    import pandas as pd
    import unicodedata

    def normalizar(valor) -> str:
        if pd.isna(valor):
            return ""

        s = unicodedata.normalize(
            "NFKD",
            str(valor).strip(),
        )

        return "".join(
            c for c in s
            if not unicodedata.combining(c)
        ).upper()

    def resolver_fecha(valor) -> date:
        if isinstance(valor, datetime):
            return valor.date()

        if isinstance(valor, date):
            return valor

        if isinstance(valor, str):
            texto_fecha = valor.strip()

            for formato in (
                "%Y-%m-%d",
                "%d-%m-%Y",
                "%d/%m/%Y",
            ):
                try:
                    return datetime.strptime(
                        texto_fecha,
                        formato,
                    ).date()
                except ValueError:
                    pass

        raise ValueError(
            f"Fecha invalida para perfil operacional: {valor!r}"
        )

    fecha_obj = resolver_fecha(fecha)

    dia_semana = fecha_obj.weekday()

    if dia_semana <= 4:
        tipo_dia = "LABORAL"
    elif dia_semana == 5:
        tipo_dia = "SABADO"
    else:
        tipo_dia = "DOMINGO"

    archivo_perfil = (
        CATALOGOS_DIR
        / "perfil_operacional.xlsx"
    )

    archivo_info = (
        CATALOGOS_DIR
        / "INFO.xlsx"
    )

    if not archivo_perfil.exists():
        raise FileNotFoundError(
            f"Perfil operacional no encontrado: {archivo_perfil}"
        )

    if not archivo_info.exists():
        raise FileNotFoundError(
            f"INFO.xlsx no encontrado: {archivo_info}"
        )

    perfil = pd.read_excel(
        archivo_perfil,
        sheet_name="Perfil_tabla",
    )

    if len(perfil.columns) != 8:
        raise RuntimeError(
            "perfil_operacional.xlsx no tiene las 8 columnas "
            "certificadas."
        )

    # Renombrado interno para evitar dependencia de tildes/codificacion.
    perfil.columns = [
        "UNIDAD",
        "TIPO_DIA",
        "SERVICIO",
        "MEDIA_HORA",
        "DATO",
        "HORA",
        "MAXIMO_HORA",
        "PERIODO",
    ]

    info = pd.read_excel(
        archivo_info,
        sheet_name="Info",
    )

    mapa_info = {
        normalizar(c): c
        for c in info.columns
    }

    requeridas_info = {
        "UNIDAD",
        "SERVICIO",
        "TERMINAL",
    }

    faltantes_info = sorted(
        requeridas_info
        - set(mapa_info)
    )

    if faltantes_info:
        raise RuntimeError(
            "INFO.xlsx sin columnas requeridas: "
            + ", ".join(faltantes_info)
        )

    # -------------------------------------------------------------
    # Normalizacion perfil
    # -------------------------------------------------------------

    perfil["UNIDAD_N"] = (
        perfil["UNIDAD"]
        .map(normalizar)
    )

    perfil["TIPO_N"] = (
        perfil["TIPO_DIA"]
        .map(normalizar)
    )

    perfil["SERVICIO_N"] = (
        perfil["SERVICIO"]
        .map(normalizar)
    )

    # -------------------------------------------------------------
    # Normalizacion INFO
    # -------------------------------------------------------------

    info["UNIDAD_N"] = (
        info[mapa_info["UNIDAD"]]
        .map(normalizar)
        .replace(
            {
                "ALFAU8": "U8",
                "OMEGAU9": "U9",
            }
        )
    )

    info["SERVICIO_N"] = (
        info[mapa_info["SERVICIO"]]
        .map(normalizar)
    )

    info["TERMINAL_N"] = (
        info[mapa_info["TERMINAL"]]
        .map(normalizar)
    )

    catalogo = (
        info[
            [
                "UNIDAD_N",
                "SERVICIO_N",
                "TERMINAL_N",
            ]
        ]
        .drop_duplicates()
    )

    control_terminal = (
        catalogo
        .groupby(
            [
                "UNIDAD_N",
                "SERVICIO_N",
            ]
        )["TERMINAL_N"]
        .nunique()
    )

    multiterrminal = control_terminal[
        control_terminal > 1
    ]

    if len(multiterrminal):
        raise RuntimeError(
            "INFO.xlsx contiene servicios asociados "
            "a mas de una terminal."
        )

    # -------------------------------------------------------------
    # Filtro fecha / tipo de dia / unidad
    # -------------------------------------------------------------

    seleccionado = perfil[
        perfil["TIPO_N"].eq(tipo_dia)
    ].copy()

    unidad_n = normalizar(unidad)

    if unidad_n:
        seleccionado = seleccionado[
            seleccionado["UNIDAD_N"].eq(
                unidad_n
            )
        ].copy()

    # -------------------------------------------------------------
    # Cruce servicio -> terminal
    # -------------------------------------------------------------

    seleccionado = seleccionado.merge(
        catalogo,
        how="left",
        on=[
            "UNIDAD_N",
            "SERVICIO_N",
        ],
        validate="many_to_one",
    )

    sin_terminal_df = seleccionado[
        seleccionado["TERMINAL_N"].isna()
        |
        seleccionado["TERMINAL_N"].eq("")
    ]

    sin_terminal = (
        sin_terminal_df[
            [
                "UNIDAD_N",
                "SERVICIO_N",
            ]
        ]
        .drop_duplicates()
        .to_dict("records")
    )

    if sin_terminal:
        raise RuntimeError(
            "Perfil operacional con servicios sin terminal: "
            + ", ".join(
                f'{x["UNIDAD_N"]}/{x["SERVICIO_N"]}'
                for x in sin_terminal
            )
        )

    # -------------------------------------------------------------
    # Validaciones numericas
    # -------------------------------------------------------------

    for columna in (
        "DATO",
        "MAXIMO_HORA",
        "PERIODO",
    ):
        seleccionado[columna] = pd.to_numeric(
            seleccionado[columna],
            errors="raise",
        )

    # -------------------------------------------------------------
    # 60 MINUTOS
    #
    # MAXIMO_HORA aparece en las dos medias horas.
    # Debe contarse UNA sola vez por servicio/periodo.
    # -------------------------------------------------------------

    servicio_60 = (
        seleccionado[
            [
                "UNIDAD_N",
                "TERMINAL_N",
                "SERVICIO_N",
                "PERIODO",
                "MAXIMO_HORA",
            ]
        ]
        .drop_duplicates(
            subset=[
                "UNIDAD_N",
                "TERMINAL_N",
                "SERVICIO_N",
                "PERIODO",
            ]
        )
    )

    perfil_60_df = (
        servicio_60
        .groupby(
            [
                "UNIDAD_N",
                "TERMINAL_N",
                "PERIODO",
            ],
            as_index=False,
        )["MAXIMO_HORA"]
        .sum()
    )

    intervalos_60 = []

    for fila in perfil_60_df.itertuples(
        index=False
    ):
        periodo = int(fila.PERIODO)

        intervalos_60.append(
            {
                "fecha": fecha_obj.isoformat(),
                "unidad": fila.UNIDAD_N,
                "terminal": fila.TERMINAL_N,
                "periodo": periodo,
                "etiqueta": f"P{periodo:02d}",
                "perfil": int(fila.MAXIMO_HORA),
            }
        )

    # -------------------------------------------------------------
    # 30 MINUTOS
    #
    # Se usa DATO exacto de cada MEDIA_HORA.
    # -------------------------------------------------------------

    perfil_30_df = (
        seleccionado
        .groupby(
            [
                "UNIDAD_N",
                "TERMINAL_N",
                "MEDIA_HORA",
            ],
            as_index=False,
        )["DATO"]
        .sum()
    )

    intervalos_30 = []

    for fila in perfil_30_df.itertuples(
        index=False
    ):
        media = fila.MEDIA_HORA

        if hasattr(media, "strftime"):
            etiqueta = media.strftime("%H:%M")
        else:
            texto_media = str(media)
            etiqueta = texto_media[:5]

        intervalos_30.append(
            {
                "fecha": fecha_obj.isoformat(),
                "unidad": fila.UNIDAD_N,
                "terminal": fila.TERMINAL_N,
                "media_hora": etiqueta,
                "perfil": int(fila.DATO),
            }
        )

    return {
        "fecha": fecha_obj.isoformat(),
        "tipo_dia": tipo_dia,
        "unidad": unidad_n or None,
        "archivo_perfil": str(
            archivo_perfil
        ),
        "archivo_info": str(
            archivo_info
        ),
        "filas_perfil_filtradas": int(
            len(seleccionado)
        ),
        "total_sin_terminal": 0,
        "sin_terminal": [],
        "intervalos_60": intervalos_60,
        "intervalos_30": intervalos_30,
    }


def construir_salidas_r16(
    db: Session,
    fecha_desde: str | date | None = None,
    fecha_hasta: str | date | None = None,
    unidad: str | None = None,
) -> dict:
    """
    Construye salidas reales desde Expedicion (R1.6).

    Salida unica:
        unidad + servicio + patente + inicio_servicio

    La terminal se obtiene desde el catalogo vigente de
    FlotaAsignacionTerminal mediante PPU normalizada.

    Devuelve:
        - intervalos_60: fecha + unidad + terminal + periodo
        - intervalos_30: fecha + unidad + terminal + media hora

    No modifica el historico.
    """

    f_desde = _parse_fecha(
        fecha_desde,
        "fecha_desde",
    )

    f_hasta = _parse_fecha(
        fecha_hasta,
        "fecha_hasta",
    )

    if f_desde and f_hasta and f_desde > f_hasta:
        raise ValueError(
            "fecha_desde no puede ser mayor que fecha_hasta"
        )

    q = (
        db.query(
            Expedicion.unidad,
            Expedicion.servicio,
            Expedicion.patente,
            Expedicion.inicio_servicio,
        )
        .filter(
            Expedicion.inicio_servicio.isnot(None)
        )
    )

    if f_desde:
        q = q.filter(
            Expedicion.inicio_servicio
            >= datetime.combine(
                f_desde,
                time.min,
            )
        )

    if f_hasta:
        q = q.filter(
            Expedicion.inicio_servicio
            < datetime.combine(
                f_hasta + timedelta(days=1),
                time.min,
            )
        )

    if unidad:
        q = q.filter(
            func.upper(Expedicion.unidad)
            == _norm(unidad)
        )

    # Deduplicacion certificada para este indicador.
    filas = q.distinct().all()

    # Catalogo vigente PPU -> terminal.
    asignaciones = obtener_asignaciones(db)

    salidas_60 = defaultdict(int)
    salidas_30 = defaultdict(int)

    detalle_60 = defaultdict(list)
    detalle_30 = defaultdict(list)

    sin_terminal = []

    for fila in filas:

        inicio = fila.inicio_servicio

        if inicio is None:
            continue

        unidad_fila = _norm(fila.unidad)

        servicio_fila = (
            _texto(fila.servicio)
            or "SIN SERVICIO"
        )

        patente_fila = (
            _texto(fila.patente)
            or "SIN PATENTE"
        )

        ppu_normalizada = _normalizar_ppu(
            patente_fila
        )

        asignacion = asignaciones.get(
            ppu_normalizada
        )

        if asignacion is None:
            terminal = "SIN ASIGNAR"

            sin_terminal.append({
                "fecha": inicio.date().isoformat(),
                "unidad": unidad_fila,
                "servicio": servicio_fila,
                "patente": patente_fila,
                "inicio_servicio": inicio.isoformat(
                    sep=" "
                ),
            })

        else:
            terminal = (
                _norm(asignacion.terminal)
                or "SIN ASIGNAR"
            )

        fecha_fila = inicio.date()

        # P01 = 00:00-00:59
        # ...
        # P24 = 23:00-23:59
        periodo = inicio.hour + 1

        minuto_base = (
            0
            if inicio.minute < 30
            else 30
        )

        intervalo_30 = (
            f"{inicio.hour:02d}:"
            f"{minuto_base:02d}"
        )

        clave_60 = (
            fecha_fila,
            unidad_fila,
            terminal,
            periodo,
        )

        clave_30 = (
            fecha_fila,
            unidad_fila,
            terminal,
            intervalo_30,
        )

        salidas_60[clave_60] += 1
        salidas_30[clave_30] += 1

        detalle = {
            "fecha": fecha_fila.isoformat(),
            "unidad": unidad_fila,
            "terminal": terminal,
            "servicio": servicio_fila,
            "patente": patente_fila,
            "inicio_servicio": inicio.isoformat(
                sep=" "
            ),
        }

        detalle_60[clave_60].append(
            detalle
        )

        detalle_30[clave_30].append(
            detalle
        )

    intervalos_60 = []

    for clave in sorted(salidas_60.keys()):

        (
            fecha_fila,
            unidad_fila,
            terminal,
            periodo,
        ) = clave

        intervalos_60.append({
            "fecha": fecha_fila.isoformat(),
            "unidad": unidad_fila,
            "terminal": terminal,
            "periodo": periodo,
            "hora_inicio":
                f"{periodo - 1:02d}:00",
            "hora_fin":
                f"{periodo - 1:02d}:59",
            "salidas": salidas_60[clave],
            "detalle": detalle_60[clave],
        })

    intervalos_30 = []

    for clave in sorted(salidas_30.keys()):

        (
            fecha_fila,
            unidad_fila,
            terminal,
            intervalo,
        ) = clave

        hora_txt, minuto_txt = (
            intervalo.split(":")
        )

        hora_num = int(hora_txt)
        minuto_num = int(minuto_txt)

        hora_fin = (
            f"{hora_num:02d}:29"
            if minuto_num == 0
            else f"{hora_num:02d}:59"
        )

        intervalos_30.append({
            "fecha": fecha_fila.isoformat(),
            "unidad": unidad_fila,
            "terminal": terminal,
            "intervalo": intervalo,
            "hora_inicio": intervalo,
            "hora_fin": hora_fin,
            "salidas": salidas_30[clave],
            "detalle": detalle_30[clave],
        })

    return {
        "total_salidas_unicas": len(filas),
        "total_sin_terminal": len(sin_terminal),
        "sin_terminal": sin_terminal,
        "intervalos_60": intervalos_60,
        "intervalos_30": intervalos_30,
    }


# =====================================================================
# REAL R1.6 VS PERFIL OPERACIONAL
# =====================================================================

def construir_real_vs_perfil(
    db: Session,
    fecha: str | date | datetime,
    unidad: str | None = None,
) -> dict:
    """
    Compara salidas reales R1.6 contra perfil operacional.

    REAL:
        Expedicion R1.6 certificada mediante construir_salidas_r16().

    PERFIL 60:
        Maximo Hora por servicio/periodo.

    PERFIL 30:
        Dato exacto por media hora.

    Reglas:
        - No es acumulativo.
        - No usa buses en calle como salidas.
        - Conserva valores superiores a 100%.
        - Perfil 0 no genera division por cero.
        - Real > 0 y Perfil = 0 se marca SIN_REQUERIMIENTO.
        - El universo es la union REAL + PERFIL.
    """

    from collections import defaultdict

    def resolver_fecha(valor) -> date:
        if isinstance(valor, datetime):
            return valor.date()

        if isinstance(valor, date):
            return valor

        if isinstance(valor, str):
            valor = valor.strip()

            for formato in (
                "%Y-%m-%d",
                "%d-%m-%Y",
                "%d/%m/%Y",
            ):
                try:
                    return datetime.strptime(
                        valor,
                        formato,
                    ).date()
                except ValueError:
                    pass

        raise ValueError(
            f"Fecha invalida para Real vs Perfil: {valor!r}"
        )

    fecha_obj = resolver_fecha(fecha)
    fecha_iso = fecha_obj.isoformat()

    unidad_n = _norm(unidad) or None

    real = construir_salidas_r16(
        db,
        fecha_desde=fecha_obj,
        fecha_hasta=fecha_obj,
        unidad=unidad_n,
    )

    perfil = construir_perfil_operacional(
        fecha_obj,
        unidad=unidad_n,
    )

    # ================================================================
    # REAL 60
    # ================================================================

    real60 = defaultdict(int)

    for fila in real["intervalos_60"]:
        clave = (
            _norm(fila.get("unidad")),
            _norm(fila.get("terminal")),
            int(fila.get("periodo")),
        )

        real60[clave] += int(
            fila.get(
                "salidas",
                fila.get("total", 0),
            )
            or 0
        )

    # ================================================================
    # PERFIL 60
    # ================================================================

    perfil60 = defaultdict(int)

    for fila in perfil["intervalos_60"]:
        clave = (
            _norm(fila.get("unidad")),
            _norm(fila.get("terminal")),
            int(fila.get("periodo")),
        )

        perfil60[clave] += int(
            fila.get("perfil", 0)
            or 0
        )

    # ================================================================
    # REAL 30
    # ================================================================

    real30 = defaultdict(int)

    for fila in real["intervalos_30"]:

        intervalo = (
            fila.get("media_hora")
            or fila.get("intervalo")
            or fila.get("etiqueta")
            or ""
        )

        intervalo = str(intervalo)[:5]

        clave = (
            _norm(fila.get("unidad")),
            _norm(fila.get("terminal")),
            intervalo,
        )

        real30[clave] += int(
            fila.get(
                "salidas",
                fila.get("total", 0),
            )
            or 0
        )

    # ================================================================
    # PERFIL 30
    # ================================================================

    perfil30 = defaultdict(int)

    for fila in perfil["intervalos_30"]:

        intervalo = str(
            fila.get("media_hora")
            or fila.get("intervalo")
            or fila.get("etiqueta")
            or ""
        )[:5]

        clave = (
            _norm(fila.get("unidad")),
            _norm(fila.get("terminal")),
            intervalo,
        )

        perfil30[clave] += int(
            fila.get("perfil", 0)
            or 0
        )

    # ================================================================
    # UNIVERSO DE UNIDADES / TERMINALES
    # ================================================================

    unidades = sorted(
        {
            clave[0]
            for clave in real60
            if clave[0]
        }
        |
        {
            clave[0]
            for clave in perfil60
            if clave[0]
        }
    )

    terminales_por_unidad = defaultdict(set)

    for u, terminal, _ in real60:
        terminales_por_unidad[u].add(terminal)

    for u, terminal, _ in perfil60:
        terminales_por_unidad[u].add(terminal)

    # ================================================================
    # CONSTRUCTOR DE CELDA
    # ================================================================

    def construir_celda(real_valor, perfil_valor):
        real_valor = int(real_valor or 0)
        perfil_valor = int(perfil_valor or 0)

        if perfil_valor > 0:
            porcentaje = round(
                (
                    real_valor
                    / perfil_valor
                )
                * 100,
                2,
            )

            estado = "CON_PERFIL"

        else:
            porcentaje = None

            if real_valor > 0:
                estado = "SIN_REQUERIMIENTO"
            else:
                estado = "SIN_PERFIL"

        return {
            "real": real_valor,
            "perfil": perfil_valor,
            "porcentaje": porcentaje,
            "estado": estado,
        }

    # ================================================================
    # MATRIZ 60 MIN
    # ================================================================

    intervalos_60 = []

    for u in unidades:

        for terminal in sorted(
            terminales_por_unidad[u]
        ):

            for periodo in range(1, 25):

                clave = (
                    u,
                    terminal,
                    periodo,
                )

                celda = construir_celda(
                    real60.get(clave, 0),
                    perfil60.get(clave, 0),
                )

                intervalos_60.append(
                    {
                        "fecha": fecha_iso,
                        "unidad": u,
                        "terminal": terminal,
                        "periodo": periodo,
                        "etiqueta": f"P{periodo:02d}",
                        **celda,
                    }
                )

    # ================================================================
    # MATRIZ 30 MIN
    # ================================================================

    etiquetas_30 = []

    for hora in range(24):
        etiquetas_30.append(
            f"{hora:02d}:00"
        )
        etiquetas_30.append(
            f"{hora:02d}:30"
        )

    intervalos_30 = []

    for u in unidades:

        for terminal in sorted(
            terminales_por_unidad[u]
        ):

            for intervalo in etiquetas_30:

                clave = (
                    u,
                    terminal,
                    intervalo,
                )

                celda = construir_celda(
                    real30.get(clave, 0),
                    perfil30.get(clave, 0),
                )

                intervalos_30.append(
                    {
                        "fecha": fecha_iso,
                        "unidad": u,
                        "terminal": terminal,
                        "media_hora": intervalo,
                        "etiqueta": intervalo,
                        **celda,
                    }
                )

    # ================================================================
    # RESUMEN POR TERMINAL
    #
    # El porcentaje total se calcula:
    #
    #     SUM(real) / SUM(perfil)
    #
    # Nunca se suman ni promedian porcentajes de celdas.
    # ================================================================

    resumen_terminal_60 = []

    for u in unidades:

        for terminal in sorted(
            terminales_por_unidad[u]
        ):

            filas = [
                x
                for x in intervalos_60
                if (
                    x["unidad"] == u
                    and
                    x["terminal"] == terminal
                )
            ]

            total_real = sum(
                x["real"]
                for x in filas
            )

            total_perfil = sum(
                x["perfil"]
                for x in filas
            )

            if total_perfil > 0:
                porcentaje = round(
                    (
                        total_real
                        / total_perfil
                    )
                    * 100,
                    2,
                )
                estado = "CON_PERFIL"

            else:
                porcentaje = None

                if total_real > 0:
                    estado = "SIN_REQUERIMIENTO"
                else:
                    estado = "SIN_PERFIL"

            resumen_terminal_60.append(
                {
                    "fecha": fecha_iso,
                    "unidad": u,
                    "terminal": terminal,
                    "real": total_real,
                    "perfil": total_perfil,
                    "porcentaje": porcentaje,
                    "estado": estado,
                }
            )

    # ================================================================
    # RESUMEN POR UNIDAD
    # ================================================================

    resumen_unidad_60 = []

    for u in unidades:

        filas = [
            x
            for x in resumen_terminal_60
            if x["unidad"] == u
        ]

        total_real = sum(
            x["real"]
            for x in filas
        )

        total_perfil = sum(
            x["perfil"]
            for x in filas
        )

        porcentaje = (
            round(
                (
                    total_real
                    / total_perfil
                )
                * 100,
                2,
            )
            if total_perfil > 0
            else None
        )

        resumen_unidad_60.append(
            {
                "fecha": fecha_iso,
                "unidad": u,
                "real": total_real,
                "perfil": total_perfil,
                "porcentaje": porcentaje,
            }
        )

    # ================================================================
    # CONTROLES DE CONSERVACION
    # ================================================================

    total_real_60 = sum(
        x["real"]
        for x in intervalos_60
    )

    total_real_30 = sum(
        x["real"]
        for x in intervalos_30
    )

    total_salidas = int(
        real.get(
            "total_salidas_unicas",
            0,
        )
        or 0
    )

    controles = {
        "total_salidas_r16": total_salidas,
        "total_real_60": total_real_60,
        "total_real_30": total_real_30,
        "conservacion_60": (
            total_real_60
            == total_salidas
        ),
        "conservacion_30": (
            total_real_30
            == total_salidas
        ),
        "total_sin_terminal_r16": int(
            real.get(
                "total_sin_terminal",
                0,
            )
            or 0
        ),
        "total_sin_terminal_perfil": int(
            perfil.get(
                "total_sin_terminal",
                0,
            )
            or 0
        ),
    }

    controles["ok"] = (
        controles["conservacion_60"]
        and
        controles["conservacion_30"]
    )

    return {
        "fecha": fecha_iso,
        "tipo_dia": perfil["tipo_dia"],
        "unidad": unidad_n,
        "modo_default": "60",
        "intervalos_60": intervalos_60,
        "intervalos_30": intervalos_30,
        "resumen_terminal_60": resumen_terminal_60,
        "resumen_unidad_60": resumen_unidad_60,
        "controles": controles,
    }


def obtener_asignaciones(db: Session) -> dict[str, FlotaAsignacionTerminal]:
    version = _version_catalogo_actual(db)
    if not version:
        return {}
    filas = (
        db.query(FlotaAsignacionTerminal)
        .filter(
            FlotaAsignacionTerminal.version == version,
            FlotaAsignacionTerminal.activo.is_(True),
        )
        .all()
    )
    return {_normalizar_ppu(f.ppu): f for f in filas}



def obtener_filtros(db: Session) -> dict:
    """
    Filtros de Flota Operativa.

    Fuente operacional:
    - fechas/unidades: HistoricoFlotaOperativa
    - servicios: HistoricoFlotaOperativaServicio
    - terminales/asignada: catalogo de flota activo

    NO usa Expedicion.
    """

    asignaciones = obtener_asignaciones(
        db
    )

    terminales = sorted(
        {
            x.terminal
            for x in asignaciones.values()
            if x.terminal
        }
    )

    unidades_catalogo = sorted(
        {
            x.unidad
            for x in asignaciones.values()
            if x.unidad
        }
    )

    fechas = (
        db.query(
            func.min(
                HistoricoFlotaOperativa.fecha
            ),
            func.max(
                HistoricoFlotaOperativa.fecha
            ),
        )
        .one()
    )

    servicios = [
        x[0]
        for x in (
            db.query(
                HistoricoFlotaOperativaServicio.servicio
            )
            .filter(
                HistoricoFlotaOperativaServicio.servicio.isnot(
                    None
                )
            )
            .distinct()
            .order_by(
                HistoricoFlotaOperativaServicio.servicio
            )
            .all()
        )
        if x[0]
    ]

    unidades_historico = [
        x[0]
        for x in (
            db.query(
                HistoricoFlotaOperativa.unidad
            )
            .filter(
                HistoricoFlotaOperativa.unidad.isnot(
                    None
                )
            )
            .distinct()
            .order_by(
                HistoricoFlotaOperativa.unidad
            )
            .all()
        )
        if x[0]
    ]

    conteos_asignados = defaultdict(
        int
    )

    for item in asignaciones.values():

        conteos_asignados[
            item.terminal
        ] += 1

    return {
        "fecha_desde":
            (
                fechas[0].isoformat()
                if fechas[0]
                else None
            ),

        "fecha_hasta":
            (
                fechas[1].isoformat()
                if fechas[1]
                else None
            ),

        "unidades":
            sorted(
                set(
                    unidades_catalogo
                    +
                    unidades_historico
                )
            ),

        "terminales": [
            {
                "codigo": t,
                "nombre":
                    TERMINAL_LABELS.get(
                        t,
                        t.title()
                    ),
                "asignada":
                    conteos_asignados[t],
            }
            for t in terminales
        ],

        "servicios":
            servicios,

        "periodos": [
            {
                "periodo": p,
                "inicio":
                    f"{p - 1:02d}:00:00",
                "fin":
                    f"{p - 1:02d}:59:59",
            }
            for p in range(
                1,
                25
            )
        ],

        "catalogo_version":
            _version_catalogo_actual(
                db
            ),
    }



def _parse_fecha(valor: str | date | None, nombre: str) -> date | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, date):
        return valor
    try:
        return datetime.strptime(str(valor), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"{nombre} debe tener formato YYYY-MM-DD") from exc


def _validar_periodos(inicial: int, final: int) -> tuple[int, int]:
    try:
        inicial = int(inicial)
        final = int(final)
    except Exception as exc:
        raise ValueError("Los periodos deben ser numeros entre 1 y 24") from exc
    if inicial < 1 or inicial > 24 or final < 1 or final > 24:
        raise ValueError("Los periodos deben estar entre 1 y 24")
    if inicial > final:
        raise ValueError("Periodo inicial no puede ser mayor que periodo final")
    return inicial, final


def _periodos_intersectados(inicio: datetime, fin: datetime) -> Iterable[tuple[date, int, datetime, datetime]]:
    """Devuelve periodos horarios que intersectan el intervalo real."""
    if not inicio or not fin:
        return []
    if fin.year <= 1900 or fin < inicio:
        return []
    # Blindaje ante datos corruptos: ninguna expedicion valida debe durar dias.
    if fin - inicio > timedelta(hours=24):
        return []

    actual = inicio.replace(minute=0, second=0, microsecond=0)
    resultado = []
    while actual <= fin:
        siguiente = actual + timedelta(hours=1)
        solape_inicio = max(inicio, actual)
        solape_fin = min(fin, siguiente - timedelta(microseconds=1))
        if solape_inicio <= solape_fin:
            resultado.append((actual.date(), actual.hour + 1, solape_inicio, solape_fin))
        actual = siguiente
    return resultado



def construir_presencias(
    db: Session,
    fecha_desde: str | date | None = None,
    fecha_hasta: str | date | None = None,
    unidad: str | None = None,
    terminal: str | None = None,
    servicio: str | None = None,
    periodo_inicial: int = 1,
    periodo_final: int = 24,
) -> list[dict]:
    """
    Construye las presencias de Flota Operativa desde
    HistoricoFlotaOperativaServicio.

    Regla certificada:
        FECHA + PERIODO + PPU + SERVICIO

    Los totales de terminal contin?an deduplicando PPU,
    por lo que una PPU multiservicio no infla la flota.

    NO usa Expedicion.
    """

    periodo_inicial, periodo_final = (
        _validar_periodos(
            periodo_inicial,
            periodo_final,
        )
    )

    f_desde = _parse_fecha(
        fecha_desde,
        "fecha_desde"
    )

    f_hasta = _parse_fecha(
        fecha_hasta,
        "fecha_hasta"
    )

    if (
        f_desde
        and
        f_hasta
        and
        f_desde > f_hasta
    ):

        raise ValueError(
            "fecha_desde no puede ser mayor que fecha_hasta"
        )


    q = db.query(
        HistoricoFlotaOperativaServicio
    )


    if f_desde:

        q = q.filter(
            HistoricoFlotaOperativaServicio.fecha
            >=
            f_desde
        )


    if f_hasta:

        q = q.filter(
            HistoricoFlotaOperativaServicio.fecha
            <=
            f_hasta
        )


    q = q.filter(
        HistoricoFlotaOperativaServicio.periodo
        >=
        periodo_inicial,

        HistoricoFlotaOperativaServicio.periodo
        <=
        periodo_final,
    )


    if unidad:

        q = q.filter(
            func.upper(
                HistoricoFlotaOperativaServicio.unidad
            )
            ==
            _norm(
                unidad
            )
        )


    if terminal:

        q = q.filter(
            func.upper(
                HistoricoFlotaOperativaServicio.terminal
            )
            ==
            _norm(
                terminal
            )
        )


    if servicio:

        q = q.filter(
            func.upper(
                HistoricoFlotaOperativaServicio.servicio
            )
            ==
            _norm(
                servicio
            )
        )


    salida = []


    for fila in q.yield_per(
        2000
    ):

        ppu = _normalizar_ppu(
            fila.ppu
        )

        if not ppu:
            continue


        terminal_ppu = (
            _norm(
                fila.terminal
            )
            if fila.terminal
            else "SIN ASIGNAR"
        )


        servicio_ppu = (
            _texto(
                fila.servicio
            )
            or
            "SIN SERVICIO"
        )


        salida.append({
            "fecha":
                fila.fecha,

            "periodo":
                int(
                    fila.periodo
                ),

            "terminal":
                terminal_ppu,

            "servicio":
                servicio_ppu,

            "ppu":
                ppu,

            "unidad":
                _norm(
                    fila.unidad
                ),

            "primera_transmision":
                fila.primera_transmision,

            "ultima_transmision":
                fila.ultima_transmision,
        })


    return salida





# =====================================================================
# FLOTA OPERATIVA - HISTORICO DE DIAS SIN TRANSMISION
# =====================================================================

def _terminal_nombre(valor):
    """
    Convierte el nombre interno del terminal
    a formato legible para pantalla.
    """
    texto = str(valor or "").strip()

    if not texto:
        return "Sin terminal"

    return texto.title()



def obtener_plazas_catalogo():
    """
    Lee plazas por PPU desde la hoja Consolidado
    del catalogo de distribucion de terminales.
    """

    import pandas as pd
    from pathlib import Path

    carpeta = Path("catalogos")

    archivo = carpeta / "Distribucion_Terminales_26Ago2026.xlsx"

    if not archivo.exists():

        candidatos = list(
            carpeta.glob(
                "*Terminales*26Ago2026*.xlsx"
            )
        )

        if not candidatos:
            return {}

        archivo = candidatos[0]


    try:

        df = pd.read_excel(
            archivo,
            sheet_name="Consolidado"
        )

    except Exception:

        return {}


    if (
        "PLACA" not in df.columns
        or
        "plazas" not in df.columns
    ):
        return {}


    resultado = {}

    for _, fila in df.iterrows():

        ppu = _normalizar_ppu(
            fila.get("PLACA")
        )

        if not ppu:
            continue

        valor = fila.get(
            "plazas"
        )

        if valor is None:
            continue

        try:

            if pd.isna(valor):
                continue

        except Exception:
            pass


        try:

            numero = int(
                float(valor)
            )

        except Exception:
            continue


        resultado[ppu] = numero


    return resultado



def construir_sin_transmision_por_dias(
    db: Session,
    fecha_desde,
    fecha_hasta,
    unidad=None,
    terminal=None,
):
    """
    Construye PPU sin transmision por dia.

    Fuente:
        HistoricoFlotaOperativa

    Regla:
    - universo = catalogo activo;
    - solo son evaluables los dias con hist?rico R1.6;
    - un dia sin datos NO penaliza a la flota;
    - no se interpreta automaticamente como Taller.

    NO usa Expedicion.
    """

    if isinstance(
        fecha_desde,
        datetime
    ):

        desde = fecha_desde.date()

    elif isinstance(
        fecha_desde,
        date
    ):

        desde = fecha_desde

    elif fecha_desde:

        desde = datetime.strptime(
            str(
                fecha_desde
            )[:10],
            "%Y-%m-%d"
        ).date()

    else:

        desde = date.today()


    if isinstance(
        fecha_hasta,
        datetime
    ):

        hasta = fecha_hasta.date()

    elif isinstance(
        fecha_hasta,
        date
    ):

        hasta = fecha_hasta

    elif fecha_hasta:

        hasta = datetime.strptime(
            str(
                fecha_hasta
            )[:10],
            "%Y-%m-%d"
        ).date()

    else:

        hasta = desde


    if hasta < desde:

        desde, hasta = (
            hasta,
            desde
        )


    # ================================================================
    # CATALOGO ACTIVO
    # ================================================================

    asignaciones = obtener_asignaciones(
        db
    )

    catalogo = {}

    for ppu_clave, asignacion in asignaciones.items():

        ppu = _normalizar_ppu(
            ppu_clave
        )

        if not ppu:
            continue

        if (
            unidad
            and
            _norm(
                asignacion.unidad
            )
            !=
            _norm(
                unidad
            )
        ):
            continue

        if (
            terminal
            and
            _norm(
                asignacion.terminal
            )
            !=
            _norm(
                terminal
            )
        ):
            continue

        catalogo[
            ppu
        ] = asignacion


    # ================================================================
    # PLAZAS
    # Fuente primaria:
    # catalogo Consolidado.
    #
    # Fuente secundaria:
    # ultimo valor disponible del historico R1.6 completo.
    # ================================================================

    plazas_por_ppu = (
        obtener_plazas_catalogo()
    )


    # Optimizacion: ultima plaza por PPU en PostgreSQL.
    # Mantener el catalogo Consolidado como fuente primaria.
    if db.get_bind().dialect.name == "postgresql":
        from sqlalchemy import text as sql_text

        filas_plazas = db.execute(
            sql_text("""
                SELECT DISTINCT ON (ppu)
                    ppu,
                    plazas
                FROM historico_flota_operativa
                WHERE ppu IS NOT NULL
                  AND plazas IS NOT NULL
                ORDER BY
                    ppu,
                    fecha DESC,
                    periodo DESC,
                    id DESC
            """)
        ).fetchall()
    else:
        filas_plazas = (
            db.query(
                HistoricoFlotaOperativa.ppu,
                HistoricoFlotaOperativa.plazas,
            )
            .filter(
                HistoricoFlotaOperativa.ppu.isnot(None),
                HistoricoFlotaOperativa.plazas.isnot(None),
            )
            .order_by(
                HistoricoFlotaOperativa.fecha.desc(),
                HistoricoFlotaOperativa.periodo.desc(),
                HistoricoFlotaOperativa.id.desc(),
            )
            .yield_per(1000)
        )

    for fila in filas_plazas:

        ppu = _normalizar_ppu(
            fila.ppu
        )

        if (
            ppu
            and
            ppu in catalogo
            and
            ppu not in plazas_por_ppu
        ):

            plazas_por_ppu[
                ppu
            ] = fila.plazas


    # ================================================================
    # COBERTURA POR DIA
    # ================================================================

    fechas_evaluables = []
    fechas_sin_datos = []

    dias_con_tx = defaultdict(
        set
    )


    fecha_actual = desde


    while fecha_actual <= hasta:

        q_dia = (
            db.query(
                HistoricoFlotaOperativa
            )
            .filter(
                HistoricoFlotaOperativa.fecha
                ==
                fecha_actual
            )
        )


        if unidad:

            q_dia = q_dia.filter(
                func.upper(
                    HistoricoFlotaOperativa.unidad
                )
                ==
                _norm(
                    unidad
                )
            )


        registros_dia = (
            q_dia.count()
        )


        if registros_dia <= 0:

            fechas_sin_datos.append(
                fecha_actual
            )

            fecha_actual += timedelta(
                days=1
            )

            continue


        fechas_evaluables.append(
            fecha_actual
        )


        q_presencias = (
            db.query(
                HistoricoFlotaOperativa.ppu
            )
            .filter(
                HistoricoFlotaOperativa.fecha
                ==
                fecha_actual
            )
        )


        if unidad:

            q_presencias = q_presencias.filter(
                func.upper(
                    HistoricoFlotaOperativa.unidad
                )
                ==
                _norm(
                    unidad
                )
            )


        if terminal:

            q_presencias = q_presencias.filter(
                func.upper(
                    HistoricoFlotaOperativa.terminal
                )
                ==
                _norm(
                    terminal
                )
            )


        for presencia in q_presencias.yield_per(1000):

            ppu = _normalizar_ppu(
                presencia.ppu
            )

            if ppu in catalogo:

                dias_con_tx[
                    ppu
                ].add(
                    fecha_actual
                )


        fecha_actual += timedelta(
            days=1
        )


    # ================================================================
    # DETALLE
    # ================================================================

    total_dias_rango = (
        (hasta - desde).days
        + 1
    )

    total_dias_evaluables = len(
        fechas_evaluables
    )

    total_dias_sin_datos = len(
        fechas_sin_datos
    )


    detalle = []


    for ppu, asignacion in catalogo.items():

        fechas_tx = dias_con_tx.get(
            ppu,
            set()
        )

        dias_con_transmision = len(
            fechas_tx
        )

        dias_sin_transmision = (
            total_dias_evaluables
            -
            dias_con_transmision
        )

        if dias_sin_transmision <= 0:
            continue


        detalle.append({
            "terminal":
                _norm(
                    asignacion.terminal
                ),

            "terminal_nombre":
                _terminal_nombre(
                    asignacion.terminal
                ),

            "ppu":
                ppu,

            "tipo_bus":
                (
                    asignacion.tipo_bus
                    or
                    "-"
                ),

            "tipo_flota":
                (
                    asignacion.tipo_flota
                    or
                    "-"
                ),

            "unidad":
                (
                    asignacion.unidad
                    or
                    "-"
                ),

            "interno":
                (
                    asignacion.interno
                    or
                    "-"
                ),

            "plazas":
                plazas_por_ppu.get(
                    ppu
                ),

            "dias_sin_transmision":
                dias_sin_transmision,

            "dias_con_transmision":
                dias_con_transmision,

            "dias_evaluables":
                total_dias_evaluables,

            "dias_sin_datos":
                total_dias_sin_datos,

            "dias_rango":
                total_dias_rango,
        })


    detalle.sort(
        key=lambda x: (
            x[
                "terminal_nombre"
            ],
            -x[
                "dias_sin_transmision"
            ],
            x[
                "ppu"
            ],
        )
    )


    # ================================================================
    # RESUMEN TERMINAL
    # ================================================================

    resumen = {}


    for ppu, asignacion in catalogo.items():

        codigo_terminal = _norm(
            asignacion.terminal
        )


        if codigo_terminal not in resumen:

            resumen[
                codigo_terminal
            ] = {
                "terminal":
                    codigo_terminal,

                "terminal_nombre":
                    _terminal_nombre(
                        asignacion.terminal
                    ),

                "total_ppu":
                    0,

                "tipos_bus":
                    defaultdict(
                        int
                    ),
            }


        fila = resumen[
            codigo_terminal
        ]

        fila[
            "total_ppu"
        ] += 1


        tipo_bus = (
            str(
                asignacion.tipo_bus
                or
                "SIN TIPO"
            )
            .strip()
            .upper()
        )


        fila[
            "tipos_bus"
        ][
            tipo_bus
        ] += 1


    ppus_sin_tx_por_terminal = defaultdict(
        set
    )


    for fila in detalle:

        ppus_sin_tx_por_terminal[
            fila[
                "terminal"
            ]
        ].add(
            fila[
                "ppu"
            ]
        )


    resumen_final = []


    for codigo_terminal, fila in resumen.items():

        total_ppu = fila[
            "total_ppu"
        ]

        total_sin_tx = len(
            ppus_sin_tx_por_terminal.get(
                codigo_terminal,
                set()
            )
        )


        porcentaje = (
            (
                total_sin_tx
                /
                total_ppu
            )
            *
            100
            if total_ppu
            else 0.0
        )


        tipos_bus = [
            {
                "tipo_bus":
                    tipo,

                "cantidad":
                    cantidad,
            }
            for tipo, cantidad
            in sorted(
                fila[
                    "tipos_bus"
                ].items()
            )
        ]


        resumen_final.append({
            "terminal":
                codigo_terminal,

            "terminal_nombre":
                fila[
                    "terminal_nombre"
                ],

            "total_ppu":
                total_ppu,

            "tipos_bus":
                tipos_bus,

            "sin_transmision":
                total_sin_tx,

            "porcentaje_sin_transmision":
                round(
                    porcentaje,
                    2
                ),
        })


    resumen_final.sort(
        key=lambda x: (
            -x[
                "porcentaje_sin_transmision"
            ],
            x[
                "terminal_nombre"
            ],
        )
    )


    return {
        "fecha_desde":
            desde.isoformat(),

        "fecha_hasta":
            hasta.isoformat(),

        "dias_rango":
            total_dias_rango,

        "dias_evaluables":
            total_dias_evaluables,

        "dias_sin_datos":
            total_dias_sin_datos,

        "fechas_evaluables": [
            x.isoformat()
            for x in fechas_evaluables
        ],

        "fechas_sin_datos": [
            x.isoformat()
            for x in fechas_sin_datos
        ],

        "resumen":
            resumen_final,

        "detalle":
            detalle,
    }




def _obtener_totales_r001_actuales(db: Session):
    """
    Total Flota por terminal desde el ultimo snapshot R001.

    R001 es el denominador agregado del dashboard.
    Si no existe R001 se conserva el catalogo historico
    como fallback.
    """
    ultimo = (
        db.query(FlotaSnapshotR001)
        .order_by(
            FlotaSnapshotR001.fecha_importacion.desc(),
            FlotaSnapshotR001.id.desc(),
        )
        .first()
    )

    if ultimo is None:
        return None

    filas = (
        db.query(FlotaSnapshotR001)
        .filter(
            FlotaSnapshotR001.snapshot_id
            == ultimo.snapshot_id
        )
        .all()
    )

    if not filas:
        return None

    totales = {
        _norm(x.terminal): int(x.total_flota or 0)
        for x in filas
        if _norm(x.terminal)
    }

    if not totales:
        return None

    return {
        "snapshot_id": ultimo.snapshot_id,
        "fecha_reporte": (
            ultimo.fecha_reporte.isoformat()
            if ultimo.fecha_reporte
            else None
        ),
        "totales": totales,
    }


def consultar_flota(
    db: Session,
    fecha_desde=None,
    fecha_hasta=None,
    unidad=None,
    terminal=None,
    servicio=None,
    periodo_inicial=1,
    periodo_final=24,
) -> dict:
    presencias = construir_presencias(
        db=db,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        unidad=unidad,
        terminal=terminal,
        servicio=servicio,
        periodo_inicial=periodo_inicial,
        periodo_final=periodo_final,
    )

    asignaciones = obtener_asignaciones(db)

    # Total Flota:
    #   R001 = denominador agregado oficial de la carga.
    #   Catalogo = fallback y detalle PPU.
    # Flota Operativa sigue proviniendo de R1.6.
    r001_actual = _obtener_totales_r001_actuales(db)

    asignada_terminal = defaultdict(int)

    # Terminales pertenecientes a la unidad consultada.
    # La relacion Unidad -> Terminal proviene del catalogo PPU.
    terminales_unidad = set()

    if unidad:
        terminales_unidad = {
            _norm(a.terminal)
            for a in asignaciones.values()
            if _norm(a.unidad) == _norm(unidad)
            and _norm(a.terminal)
        }

    if r001_actual:
        for term, cantidad in r001_actual["totales"].items():

            term_norm = _norm(term)

            if (
                unidad
                and
                terminales_unidad
                and
                term_norm not in terminales_unidad
            ):
                continue

            asignada_terminal[
                term_norm
            ] = int(cantidad)

    else:
        for a in asignaciones.values():
            if unidad and _norm(a.unidad) != _norm(unidad):
                continue

            asignada_terminal[
                _norm(a.terminal)
            ] += 1

    # Resumen terminal: PPU DISTINCT por fecha+periodo+terminal, independiente del servicio.
    terminal_ppus = defaultdict(set)
    for p in presencias:
        terminal_ppus[(p["fecha"], p["periodo"], p["terminal"])].add(p["ppu"])

    resumen_terminal = []

    # La grilla debe mostrar tambien los periodos con 0 PPU transmitiendo.
    # Si el usuario entrego un rango de fechas, se construye toda la malla
    # Fecha x Terminal x Periodo.
    f_desde_grid = _parse_fecha(fecha_desde, "fecha_desde")
    f_hasta_grid = _parse_fecha(fecha_hasta, "fecha_hasta")
    if f_desde_grid is None or f_hasta_grid is None:
        fechas_presencia = sorted({p["fecha"] for p in presencias})
        if fechas_presencia:
            f_desde_grid = f_desde_grid or fechas_presencia[0]
            f_hasta_grid = f_hasta_grid or fechas_presencia[-1]

    terminales_grid = sorted(asignada_terminal.keys())
    if terminal:
        terminales_grid = [t for t in terminales_grid if t == _norm(terminal)]
    # Mantener visibles PPU que transmitieron y aun no estan catalogadas.
    if any(p["terminal"] == "SIN ASIGNAR" for p in presencias):
        if not terminal or _norm(terminal) == "SIN ASIGNAR":
            terminales_grid.append("SIN ASIGNAR")

    fechas_grid = []
    if f_desde_grid and f_hasta_grid:
        cursor = f_desde_grid
        while cursor <= f_hasta_grid:
            fechas_grid.append(cursor)
            cursor += timedelta(days=1)
    else:
        fechas_grid = sorted({p["fecha"] for p in presencias})

    for fecha in fechas_grid:
        for periodo in range(int(periodo_inicial), int(periodo_final) + 1):
            for term in terminales_grid:
                ppus = terminal_ppus.get((fecha, periodo, term), set())
                asignada = asignada_terminal.get(term, 0)
                operativa = len(ppus)
                sin_transmision = max(asignada - operativa, 0) if asignada else 0
                porcentaje = round((operativa / asignada * 100), 2) if asignada else None
                resumen_terminal.append({
                    "fecha": fecha.isoformat(),
                    "terminal": term,
                    "terminal_nombre": TERMINAL_LABELS.get(term, term.title()),
                    "periodo": periodo,
                    "hora_inicio": f"{periodo - 1:02d}:00:00",
                    "hora_fin": f"{periodo - 1:02d}:59:59",
                    "asignada": asignada,
                    "operativa": operativa,
                    "sin_transmision": sin_transmision,
                    "porcentaje_operativa": porcentaje,
                })

    # ================================================================
    # R11C - PRESTAMOS / RECIBIDOS
    # ================================================================
    #
    # NO modifica:
    #   resumen_terminal
    #   resumen_terminal_global
    #   total_global
    #
    # Produce informacion paralela para certificacion.
    # ================================================================

    mapa_patios_operativos = (
        _construir_mapa_patios_operativos(
            db
        )
    )

    prestamos_detalle = []

    # Deduplicacion:
    # una PPU prestada se cuenta una vez por
    # fecha + periodo + patio base + patio operativo.
    claves_prestamo = set()

    # PPU distintas por terminal dentro del rango consultado.
    prestados_ppus_terminal = defaultdict(set)
    recibidos_ppus_terminal = defaultdict(set)

    for presencia in presencias:

        ppu = presencia[
            "ppu"
        ]

        asignacion = (
            asignaciones.get(
                ppu
            )
        )

        if asignacion is None:

            # obtener_asignaciones usa PPU normalizada,
            # pero se mantiene fallback defensivo.
            asignacion = (
                asignaciones.get(
                    _normalizar_ppu(
                        ppu
                    )
                )
            )

        terminal_base = (
            _norm(
                asignacion.terminal
            )
            if asignacion is not None
            else _norm(
                presencia.get(
                    "terminal"
                )
            )
        )

        resolucion = (
            _resolver_patio_operativo(
                mapa_patios_operativos,
                presencia.get(
                    "unidad"
                ),
                presencia.get(
                    "servicio"
                ),
            )
        )

        terminal_operativo = (
            _norm(
                resolucion.get(
                    "terminal_operativo"
                )
            )
            if resolucion.get(
                "terminal_operativo"
            )
            else None
        )

        estado_movimiento = (
            "SIN MAPA"
        )

        if (
            resolucion.get(
                "resuelto"
            )
            and
            terminal_operativo
        ):

            if (
                terminal_base
                ==
                terminal_operativo
            ):

                estado_movimiento = (
                    "BASE"
                )

            else:

                estado_movimiento = (
                    "PRESTADO"
                )


        if (
            estado_movimiento
            !=
            "PRESTADO"
        ):

            continue


        clave = (
            presencia.get(
                "fecha"
            ),
            int(
                presencia.get(
                    "periodo"
                )
                or 0
            ),
            ppu,
            terminal_base,
            terminal_operativo,
        )

        if clave in claves_prestamo:
            continue

        claves_prestamo.add(
            clave
        )

        prestados_ppus_terminal[
            terminal_base
        ].add(
            ppu
        )

        recibidos_ppus_terminal[
            terminal_operativo
        ].add(
            ppu
        )


        prestamos_detalle.append({
            "fecha":
                presencia.get(
                    "fecha"
                ),
            "periodo":
                presencia.get(
                    "periodo"
                ),
            "ppu":
                ppu,
            "unidad":
                presencia.get(
                    "unidad"
                ),
            "servicio_r16":
                presencia.get(
                    "servicio"
                ),
            "servicio_cliente":
                resolucion.get(
                    "servicio_cliente"
                ),
            "codigo_ts":
                resolucion.get(
                    "codigo_ts"
                ),
            "terminal_base":
                terminal_base,
            "terminal_base_nombre":
                TERMINAL_LABELS.get(
                    terminal_base,
                    terminal_base.title(),
                ),
            "terminal_operativo":
                terminal_operativo,
            "terminal_operativo_nombre":
                TERMINAL_LABELS.get(
                    terminal_operativo,
                    terminal_operativo.title(),
                ),
            "estado":
                "PRESTADO",
            "resolucion":
                resolucion.get(
                    "resolucion"
                ),
            "primera_transmision":
                presencia.get(
                    "primera_transmision"
                ),
            "ultima_transmision":
                presencia.get(
                    "ultima_transmision"
                ),
        })


    # ================================================================
    # CASOS SIN RESOLVER / MIXTOS
    # Se informan por separado.
    # ================================================================

    prestamos_revision = []

    claves_revision = set()

    for presencia in presencias:

        resolucion = (
            _resolver_patio_operativo(
                mapa_patios_operativos,
                presencia.get(
                    "unidad"
                ),
                presencia.get(
                    "servicio"
                ),
            )
        )

        if resolucion.get(
            "resuelto"
        ):
            continue

        clave = (
            presencia.get(
                "unidad"
            ),
            presencia.get(
                "servicio"
            ),
        )

        if clave in claves_revision:
            continue

        claves_revision.add(
            clave
        )

        prestamos_revision.append({
            "unidad":
                presencia.get(
                    "unidad"
                ),
            "servicio_r16":
                presencia.get(
                    "servicio"
                ),
            "resolucion":
                resolucion.get(
                    "resolucion"
                ),
        })


    # ================================================================
    # RESUMEN POR TERMINAL
    # ================================================================

    terminales_movimiento = set(
        asignada_terminal.keys()
    )

    terminales_movimiento.update(
        prestados_ppus_terminal.keys()
    )

    terminales_movimiento.update(
        recibidos_ppus_terminal.keys()
    )

    prestamos_resumen = []

    # Operativa actual GLOBAL por base.
    operativa_actual_por_terminal = defaultdict(
        set
    )

    for presencia in presencias:

        operativa_actual_por_terminal[
            presencia.get(
                "terminal"
            )
        ].add(
            presencia.get(
                "ppu"
            )
        )


    # Operativa ajustada:
    # PPU se asigna al patio donde realmente opera.
    operativa_ajustada_ppus = defaultdict(
        set
    )

    for presencia in presencias:

        ppu = presencia.get(
            "ppu"
        )

        asignacion = (
            asignaciones.get(
                ppu
            )
            or
            asignaciones.get(
                _normalizar_ppu(
                    ppu
                )
            )
        )

        terminal_base = (
            _norm(
                asignacion.terminal
            )
            if asignacion is not None
            else _norm(
                presencia.get(
                    "terminal"
                )
            )
        )

        resolucion = (
            _resolver_patio_operativo(
                mapa_patios_operativos,
                presencia.get(
                    "unidad"
                ),
                presencia.get(
                    "servicio"
                ),
            )
        )

        terminal_destino = (
            _norm(
                resolucion.get(
                    "terminal_operativo"
                )
            )
            if (
                resolucion.get(
                    "resuelto"
                )
                and
                resolucion.get(
                    "terminal_operativo"
                )
            )
            else terminal_base
        )

        if terminal_destino:

            operativa_ajustada_ppus[
                terminal_destino
            ].add(
                ppu
            )


    for term in sorted(
        terminales_movimiento
    ):

        prestados = len(
            prestados_ppus_terminal.get(
                term,
                set(),
            )
        )

        recibidos = len(
            recibidos_ppus_terminal.get(
                term,
                set(),
            )
        )

        operativa_actual = len(
            operativa_actual_por_terminal.get(
                term,
                set(),
            )
        )

        operativa_ajustada = len(
            operativa_ajustada_ppus.get(
                term,
                set(),
            )
        )

        flota_base = (
            int(
                asignada_terminal.get(
                    term,
                    0,
                )
            )
        )

        prestamos_resumen.append({
            "terminal":
                term,
            "terminal_nombre":
                TERMINAL_LABELS.get(
                    term,
                    term.title(),
                ),
            "flota_base":
                flota_base,
            "operativa_actual":
                operativa_actual,
            "prestados":
                prestados,
            "recibidos":
                recibidos,
            "operativa_ajustada":
                operativa_ajustada,
            "saldo_prestamos":
                recibidos
                -
                prestados,
        })




    # ================================================================
    # R13C-R22 - FUENTE R2.2 PARA MATRIZ DE FLOTA
    #
    # PRIMERA INTEGRACION CONTROLADA:
    # - Solo se usa si la consulta corresponde a UN solo dia.
    # - Solo se usa si existe previamente el CSV R2.2.
    # - NO descarga automaticamente.
    # - NO reemplaza `presencias` R1.6.
    # - NO modifica prestamos, patio ni otros calculos.
    # ================================================================

    resumen_r22_matriz = None
    cobertura_r22 = None
    fuente_matriz_acumulada = "R1.6"

    fecha_r22_matriz = (
        _parse_fecha(
            fecha_desde,
            "fecha_desde",
        )
    )

    fecha_r22_hasta = (
        _parse_fecha(
            fecha_hasta,
            "fecha_hasta",
        )
    )

    if (
        unidad
        and
        fecha_r22_matriz is not None
        and
        fecha_r22_hasta is not None
        and
        fecha_r22_matriz == fecha_r22_hasta
    ):
        servicio_r22_matriz = (
            SinopticoR22Service()
        )

        ruta_r22_matriz = (
            servicio_r22_matriz
            .ruta_archivo_esperado(
                unidad=unidad,
                fecha=fecha_r22_matriz.strftime(
                    "%d/%m/%Y"
                ),
            )
        )

        if ruta_r22_matriz.exists():

            resumen_r22_matriz = (
                construir_resumen_terminal_r22(
                    ruta_archivo=ruta_r22_matriz,
                    asignaciones=list(
                        asignaciones.values()
                    ),
                    fecha=fecha_r22_matriz,
                    unidad=unidad,
                )
            )

            fuente_matriz_acumulada = "R2.2"

            cobertura_r22_base = (
                resumen_r22_matriz.get(
                    "cobertura",
                    {}
                )
                or {}
            )

            primera_r22 = (
                cobertura_r22_base.get(
                    "primera_transmision"
                )
            )

            ultima_r22 = (
                cobertura_r22_base.get(
                    "ultima_transmision"
                )
            )

            ultimo_periodo_r22 = (
                cobertura_r22_base.get(
                    "ultimo_periodo"
                )
            )

            cobertura_r22 = {
                "unidad":
                    _norm(unidad),

                "fecha":
                    fecha_r22_matriz.isoformat(),

                "primera_transmision":
                    (
                        primera_r22.isoformat(
                            sep=" "
                        )
                        if primera_r22 is not None
                        else None
                    ),

                "ultima_transmision":
                    (
                        ultima_r22.isoformat(
                            sep=" "
                        )
                        if ultima_r22 is not None
                        else None
                    ),

                "ultimo_periodo":
                    ultimo_periodo_r22,

                "fuente":
                    "R2.2",
            }

    # ================================================================
    # R13C - ACUMULADO PROGRESIVO PPU DISTINCT
    # Exclusivo para matriz Comportamiento por periodo.
    #
    # P01 = PPU unicas observadas hasta P01
    # P02 = PPU unicas observadas hasta P02
    # ...
    # P24 = PPU unicas observadas durante todo el rango consultado
    #
    # Una misma PPU nunca suma dos veces.
    # ================================================================

    ppus_exactas_terminal_periodo = defaultdict(
        lambda: defaultdict(set)
    )

    if resumen_r22_matriz is not None:

        for fila_r22 in (
            resumen_r22_matriz.get(
                "resumen_terminal",
                []
            )
        ):

            term_acum = _norm(
                fila_r22.get(
                    "terminal"
                )
            )

            try:
                periodo_acum = int(
                    fila_r22.get(
                        "periodo"
                    )
                    or 0
                )
            except (TypeError, ValueError):
                periodo_acum = 0

            if (
                not term_acum
                or
                periodo_acum < 1
                or
                periodo_acum > 24
            ):
                continue

            for ppu_acum in (
                fila_r22.get(
                    "ppus_periodo",
                    []
                )
                or []
            ):
                if ppu_acum:
                    ppus_exactas_terminal_periodo[
                        term_acum
                    ][
                        periodo_acum
                    ].add(
                        ppu_acum
                    )

    else:

        # Fallback historico:
        # si no existe R2.2 controlado,
        # conservar exactamente R1.6.
        for presencia in presencias:

            term_acum = presencia.get(
                "terminal"
            )

            ppu_acum = presencia.get(
                "ppu"
            )

            try:
                periodo_acum = int(
                    presencia.get(
                        "periodo"
                    )
                    or 0
                )
            except (TypeError, ValueError):
                periodo_acum = 0

            if (
                not term_acum
                or
                not ppu_acum
                or
                periodo_acum < 1
                or
                periodo_acum > 24
            ):
                continue

            ppus_exactas_terminal_periodo[
                term_acum
            ][
                periodo_acum
            ].add(
                ppu_acum
            )


    resumen_terminal_acumulado = []

    terminales_acumulado = set(
        asignada_terminal.keys()
    )

    terminales_acumulado.update(
        ppus_exactas_terminal_periodo.keys()
    )


    for term_acum in sorted(
        terminales_acumulado
    ):

        acumuladas = set()

        asignada_acum = int(
            asignada_terminal.get(
                term_acum,
                0
            )
            or 0
        )

        for periodo_acum in range(
            1,
            25
        ):

            acumuladas.update(
                ppus_exactas_terminal_periodo.get(
                    term_acum,
                    {}
                ).get(
                    periodo_acum,
                    set()
                )
            )

            operativa_acum = len(
                acumuladas
            )

            sin_tx_acum = max(
                asignada_acum
                -
                operativa_acum,
                0
            )

            porcentaje_acum = (
                round(
                    (
                        operativa_acum
                        /
                        asignada_acum
                    )
                    *
                    100,
                    2
                )
                if asignada_acum > 0
                else None
            )

            resumen_terminal_acumulado.append({
                "terminal":
                    term_acum,

                "terminal_nombre":
                    TERMINAL_LABELS.get(
                        term_acum,
                        term_acum.title(),
                    ),

                "periodo":
                    periodo_acum,

                "hora_inicio":
                    f"{periodo_acum - 1:02d}:00:00",

                "hora_fin":
                    f"{periodo_acum - 1:02d}:59:59",

                "asignada":
                    asignada_acum,

                "operativa":
                    operativa_acum,

                "sin_transmision":
                    sin_tx_acum,

                "porcentaje_operativa":
                    porcentaje_acum,
            })



    # =====================================================
    # GLOBAL POR TERMINAL
    # PPU DISTINCT en todo el rango de fechas/periodos elegido.
    # Una misma PPU que aparezca en varios periodos cuenta 1 vez.
    # =====================================================

    terminal_global_ppus = defaultdict(set)

    for p in presencias:
        terminal_global_ppus[p["terminal"]].add(p["ppu"])

    resumen_terminal_global = []

    terminales_global = sorted(asignada_terminal.keys())

    if terminal:
        terminales_global = [
            t for t in terminales_global
            if t == _norm(terminal)
        ]

    if any(p["terminal"] == "SIN ASIGNAR" for p in presencias):
        if not terminal or _norm(terminal) == "SIN ASIGNAR":
            if "SIN ASIGNAR" not in terminales_global:
                terminales_global.append("SIN ASIGNAR")

    for term in terminales_global:

        asignada = (
            asignada_terminal.get(term, 0)
            if term != "SIN ASIGNAR"
            else 0
        )

        operativa = len(
            terminal_global_ppus.get(term, set())
        )

        sin_transmision = max(
            asignada - operativa,
            0,
        )

        porcentaje = (
            round(
                (operativa / asignada) * 100,
                2,
            )
            if asignada > 0
            else None
        )

        resumen_terminal_global.append({
            "terminal": term,
            "terminal_nombre": TERMINAL_LABELS.get(
                term,
                term.title(),
            ),
            "asignada": asignada,
            "operativa": operativa,
            "sin_transmision": sin_transmision,
            "porcentaje_operativa": porcentaje,
        })

    total_asignada = sum(
        r["asignada"]
        for r in resumen_terminal_global
    )

    # -----------------------------------------------------
    # TOTAL GLOBAL CERTIFICADO CONTRA FLOTA ACTUALIZADA
    # -----------------------------------------------------
    # Solo se consideran operativas las PPU que:
    #   1. pertenecen al cat?logo actualizado; y
    #   2. tuvieron al menos una transmisi?n en el rango.
    #
    # Esto garantiza:
    #
    #   ASIGNADA = OPERATIVA + SIN TRANSMISION
    #
    # sin sumar una misma PPU varias veces por per?odo.
    # -----------------------------------------------------

    # -----------------------------------------------------
    # TOTAL GLOBAL R001 + R1.6
    # -----------------------------------------------------
    # Total Flota:
    #   proviene del R001 vigente.
    #
    # Flota Operativa:
    #   PPU DISTINCT que realmente aparece en las presencias
    #   construidas desde R1.6 para el rango consultado.
    #
    # IMPORTANTE:
    #   Ya NO se restringe la operativa al catalogo historico
    #   de 737 PPU, porque R001 declara el universo agregado
    #   vigente y R1.6 es la fuente operacional.
    # -----------------------------------------------------

    ppus_transmitiendo_global = {
        _normalizar_ppu(p["ppu"])
        for p in presencias
        if _normalizar_ppu(p.get("ppu"))
        and (
            not terminal
            or _norm(p.get("terminal")) == _norm(terminal)
        )
    }

    # =====================================================
    # PASO 24L.1 - DETECTOR INFORMATIVO DE PPU NO RECONOCIDA
    # =====================================================
    #
    # R1.6 es la fuente operacional.
    # Una PPU observada en R1.6 que no existe en el catalogo
    # de flota propia se informa para validacion.
    #
    # IMPORTANTE:
    #   En este paso NO se modifica ningun KPI.
    #   No se altera Total Flota, Operativa ni Sin transmision.
    # =====================================================

    ppus_catalogadas = {
        _normalizar_ppu(ppu)
        for ppu in asignaciones.keys()
        if _normalizar_ppu(ppu)
    }

    # PPU propias validadas persistentemente.
    #
    # Una PPU fuera del catalogo solo se reconoce como propia
    # cuando existe una validacion humana terminada y su
    # clasificacion corresponde a una categoria propia.
    #
    # POR_VALIDAR y APOYO_EXTERNO quedan fuera del universo
    # propio y, por lo tanto, no aumentan Flota Operativa.
    clasificaciones_propias = {
        "BUS_NUEVO_PROPIO",
        "MOVIMIENTO_INTERNO",
    }

    filas_propias_validadas = (
        db.query(FlotaPPUValidacion)
        .filter(
            FlotaPPUValidacion.estado == "VALIDADO",
            FlotaPPUValidacion.clasificacion_final.in_(
                clasificaciones_propias
            ),
        )
        .all()
    )

    ppus_propias_validadas = {
        _normalizar_ppu(fila.ppu)
        for fila in filas_propias_validadas
        if _normalizar_ppu(fila.ppu)
    }

    ppus_propias_reconocidas = (
        ppus_catalogadas
        | ppus_propias_validadas
    )

    ppus_no_reconocidas_set = (
        ppus_transmitiendo_global
        - ppus_propias_reconocidas
    )

    detalle_ppu_no_reconocidas = []

    for ppu_alerta in sorted(ppus_no_reconocidas_set):

        presencias_ppu = [
            p
            for p in presencias
            if _normalizar_ppu(p.get("ppu")) == ppu_alerta
            and (
                not terminal
                or _norm(p.get("terminal")) == _norm(terminal)
            )
        ]

        unidades_ppu = sorted({
            str(p.get("unidad") or "").strip()
            for p in presencias_ppu
            if str(p.get("unidad") or "").strip()
        })

        terminales_ppu = sorted({
            str(p.get("terminal") or "").strip()
            for p in presencias_ppu
            if str(p.get("terminal") or "").strip()
        })

        servicios_ppu = sorted({
            str(p.get("servicio") or "").strip()
            for p in presencias_ppu
            if str(p.get("servicio") or "").strip()
        })

        codigos_ts_ppu = sorted({
            str(p.get("codigo_ts") or "").strip()
            for p in presencias_ppu
            if str(p.get("codigo_ts") or "").strip()
        })

        fechas_ppu = sorted({
            str(p.get("fecha") or "").strip()
            for p in presencias_ppu
            if str(p.get("fecha") or "").strip()
        })

        detalle_ppu_no_reconocidas.append({
            "ppu": ppu_alerta,
            "estado": "POR VALIDAR",
            "tipo_alerta": "PPU_NO_RECONOCIDA_R16",
            "unidades": unidades_ppu,
            "terminales_operacionales": terminales_ppu,
            "servicios": servicios_ppu,
            "codigos_ts": codigos_ts_ppu,
            "primera_fecha": (
                fechas_ppu[0]
                if fechas_ppu
                else None
            ),
            "ultima_fecha": (
                fechas_ppu[-1]
                if fechas_ppu
                else None
            ),
            "presencias": len(presencias_ppu),
        })

    alertas_ppu = {
        "total_no_reconocidas":
            len(detalle_ppu_no_reconocidas),

        "ppu_no_reconocidas":
            detalle_ppu_no_reconocidas,

        "regla":
            "PPU observada en R1.6 y no reconocida como flota propia.",

        "afecta_kpi":
            False,
    }

    # =====================================================
    # PASO 24M.2 - OPERATIVA PROPIA
    # =====================================================
    #
    # Solo una PPU reconocida como propia puede formar parte
    # del KPI oficial de Flota Operativa.
    #
    # Una PPU observada en R1.6 pero no reconocida:
    #   - sigue visible en alertas_ppu
    #   - NO aumenta Flota Operativa propia
    #   - NO modifica Total Flota R001
    #   - queda POR VALIDAR
    # =====================================================

    ppus_operativas_propias = (
        ppus_transmitiendo_global
        &
        ppus_propias_reconocidas
    )

    total_operativa = len(
        ppus_operativas_propias
    )

    total_sin_transmision = max(
        total_asignada - total_operativa,
        0,
    )

    porcentaje_global = (
        round(
            (total_operativa / total_asignada) * 100,
            2,
        )
        if total_asignada > 0
        else None
    )

    total_global = {
        "asignada": total_asignada,
        "operativa": total_operativa,
        "sin_transmision": total_sin_transmision,
        "porcentaje_operativa": porcentaje_global,
    }


    # =====================================================
    # PPU SIN TRANSMISION EN TODO EL RANGO CONSULTADO
    # =====================================================
    #
    # Fuente:
    #   cat?logo actualizado de flota asignada
    #
    # Regla:
    #   PPU asignada - PPU que transmiti? al menos una vez
    #
    # IMPORTANTE:
    #   Esto NO significa autom?ticamente "Taller".
    #   Significa "Sin transmisi?n en todo el rango".
    # =====================================================

    ppus_con_transmision = {
        p["ppu"]
        for p in presencias
    }

    sin_transmision_detalle = []
    sin_transmision_por_terminal = defaultdict(list)

    for clave_ppu, asignacion in asignaciones.items():

        if unidad and _norm(asignacion.unidad) != _norm(unidad):
            continue

        terminal_asignada = _norm(asignacion.terminal)

        if terminal and terminal_asignada != _norm(terminal):
            continue

        ppu_clave = _normalizar_ppu(
            asignacion.ppu
        )

        if not ppu_clave:
            continue

        if ppu_clave in ppus_con_transmision:
            continue

        item = {
            "ppu": ppu_clave,
            "terminal": terminal_asignada,
            "terminal_nombre": TERMINAL_LABELS.get(
                terminal_asignada,
                terminal_asignada.title(),
            ),
            "unidad": _norm(
                asignacion.unidad
            ),
            "empresa": _texto(
                asignacion.empresa
            ),
            "interno": _texto(
                asignacion.interno
            ),
            "tipo_bus": _texto(
                asignacion.tipo_bus
            ),
            "tipo_flota": _texto(
                asignacion.tipo_flota
            ),
            "estado": "SIN TRANSMISION",
        }

        sin_transmision_detalle.append(
            item
        )

        sin_transmision_por_terminal[
            terminal_asignada
        ].append(
            item
        )

    sin_transmision_detalle.sort(
        key=lambda x: (
            x["terminal_nombre"],
            x["ppu"],
        )
    )

    resumen_sin_transmision = []

    for term in sorted(
        sin_transmision_por_terminal.keys()
    ):

        items = (
            sin_transmision_por_terminal[
                term
            ]
        )

        resumen_sin_transmision.append({
            "terminal": term,
            "terminal_nombre":
                TERMINAL_LABELS.get(
                    term,
                    term.title(),
                ),
            "total": len(items),
            "ppus": [
                x["ppu"]
                for x in items
            ],
        })


    servicio_ppus = defaultdict(set)
    for p in presencias:
        servicio_ppus[(p["fecha"], p["periodo"], p["terminal"], p["servicio"])].add(p["ppu"])

    resumen_servicio = []
    for (fecha, periodo, term, serv), ppus in sorted(servicio_ppus.items()):
        resumen_servicio.append({
            "fecha": fecha.isoformat(),
            "terminal": term,
            "terminal_nombre": TERMINAL_LABELS.get(term, term.title()),
            "servicio": serv,
            "periodo": periodo,
            "hora_inicio": f"{periodo - 1:02d}:00:00",
            "hora_fin": f"{periodo - 1:02d}:59:59",
            "operativa": len(ppus),
        })

    # KPIs: PPU unicas del conjunto, max/min/promedio de filas terminal-periodo.
    ppu_unicas = {p["ppu"] for p in presencias}
    valores = [r["operativa"] for r in resumen_terminal]
    kpis = {
        "ppu_unicas_rango": len(ppu_unicas),
        "flota_maxima": max(valores) if valores else 0,
        "flota_minima": min(valores) if valores else 0,
        "promedio": round(sum(valores) / len(valores), 2) if valores else 0,
        "terminales_con_datos": len({r["terminal"] for r in resumen_terminal}),
    }


    # ================================================================
    # RESUMEN POR UNIDAD
    # ================================================================
    #
    # La flota asignada proviene del catalogo.
    # La flota operativa proviene de PPU DISTINCT con presencia
    # historica dentro del rango seleccionado.
    #
    # Una misma PPU cuenta una sola vez por unidad en el resumen global.
    # ================================================================

    catalogo_unidad_ppus = defaultdict(set)

    for asignacion in asignaciones.values():

        unidad_asignacion = _norm(
            asignacion.unidad
        )

        terminal_asignacion = _norm(
            asignacion.terminal
        )

        if (
            unidad
            and
            unidad_asignacion != _norm(unidad)
        ):
            continue

        if (
            terminal
            and
            terminal_asignacion != _norm(terminal)
        ):
            continue

        ppu_asignacion = _normalizar_ppu(
            asignacion.ppu
        )

        if not ppu_asignacion:
            continue

        catalogo_unidad_ppus[
            unidad_asignacion
        ].add(
            ppu_asignacion
        )


    transmitiendo_unidad = defaultdict(set)

    for presencia in presencias:

        unidad_presencia = _norm(
            presencia.get(
                "unidad"
            )
        )

        ppu_presencia = _normalizar_ppu(
            presencia.get(
                "ppu"
            )
        )

        if (
            not unidad_presencia
            or
            not ppu_presencia
        ):
            continue

        if (
            ppu_presencia
            in
            catalogo_unidad_ppus.get(
                unidad_presencia,
                set()
            )
        ):

            transmitiendo_unidad[
                unidad_presencia
            ].add(
                ppu_presencia
            )


    resumen_unidades = []

    for codigo_unidad in sorted(
        catalogo_unidad_ppus.keys()
    ):

        asignada_u = len(
            catalogo_unidad_ppus[
                codigo_unidad
            ]
        )

        operativa_u = len(
            transmitiendo_unidad.get(
                codigo_unidad,
                set()
            )
        )

        sin_tx_u = max(
            asignada_u
            -
            operativa_u,
            0
        )

        porcentaje_u = (
            round(
                (
                    operativa_u
                    /
                    asignada_u
                )
                *
                100,
                2
            )
            if asignada_u
            else 0.0
        )

        resumen_unidades.append({
            "unidad":
                codigo_unidad,

            "asignada":
                asignada_u,

            "operativa":
                operativa_u,

            "sin_transmision":
                sin_tx_u,

            "porcentaje_operativa":
                porcentaje_u,
        })


    resumen_unidades.append({
        "unidad":
            "TOTAL",

        "asignada":
            total_global[
                "asignada"
            ],

        "operativa":
            total_global[
                "operativa"
            ],

        "sin_transmision":
            total_global[
                "sin_transmision"
            ],

        "porcentaje_operativa":
            total_global[
                "porcentaje_operativa"
            ],
    })


    # ================================================================
    # COBERTURA FUENTE R1.6
    # ================================================================
    #
    # Se obtiene desde archivo_origen guardado en el historico.
    #
    # Ejemplo:
    # R16_U8_10092026_0000_2223.csv
    #                       ^^^^
    #                       ultimo minuto disponible
    # ================================================================

    cobertura_fuente = []

    f_cobertura_desde = _parse_fecha(
        fecha_desde,
        "fecha_desde"
    )

    f_cobertura_hasta = _parse_fecha(
        fecha_hasta,
        "fecha_hasta"
    )


    q_cobertura = db.query(
        HistoricoFlotaOperativa.unidad,
        HistoricoFlotaOperativa.fecha,
        HistoricoFlotaOperativa.archivo_origen,
    )


    if f_cobertura_desde:

        q_cobertura = q_cobertura.filter(
            HistoricoFlotaOperativa.fecha
            >=
            f_cobertura_desde
        )


    if f_cobertura_hasta:

        q_cobertura = q_cobertura.filter(
            HistoricoFlotaOperativa.fecha
            <=
            f_cobertura_hasta
        )


    if unidad:

        q_cobertura = q_cobertura.filter(
            func.upper(
                HistoricoFlotaOperativa.unidad
            )
            ==
            _norm(
                unidad
            )
        )


    cobertura_por_unidad = {}


    patron_archivo = re.compile(
        r"R16_(U8|U9)_"
        r"(\d{8})_"
        r"(\d{4})_"
        r"(\d{4})"
        r"\.csv",
        re.IGNORECASE,
    )


    for (
        unidad_hist,
        fecha_hist,
        archivos_hist,
    ) in q_cobertura.all():

        codigo_unidad = _norm(
            unidad_hist
        )

        if not codigo_unidad:
            continue


        for parte in str(
            archivos_hist
            or ""
        ).split("|"):

            nombre = Path(
                parte.strip()
            ).name

            match = patron_archivo.search(
                nombre
            )

            if not match:
                continue


            hora_fin = match.group(
                4
            )

            if len(hora_fin) != 4:
                continue


            hh = int(
                hora_fin[:2]
            )

            mm = int(
                hora_fin[2:]
            )


            if (
                hh > 23
                or
                mm > 59
            ):
                continue


            minutos = (
                hh * 60
                +
                mm
            )


            clave_actual = (
                fecha_hist,
                minutos,
            )


            anterior = cobertura_por_unidad.get(
                codigo_unidad
            )


            if (
                anterior is None
                or
                clave_actual
                >
                anterior[
                    "_clave"
                ]
            ):

                cobertura_por_unidad[
                    codigo_unidad
                ] = {
                    "_clave":
                        clave_actual,

                    "unidad":
                        codigo_unidad,

                    "fecha":
                        (
                            fecha_hist.isoformat()
                            if fecha_hist
                            else None
                        ),

                    "hasta":
                        f"{hh:02d}:{mm:02d}",

                    "archivo":
                        nombre,

                    "dia_completo":
                        minutos >= 1439,
                }


    # ================================================================
    # R16I - FALLBACK COBERTURA DESDE HISTORICO REAL
    # ================================================================
    #
    # Si archivo_origen no permite determinar la cobertura (por ejemplo
    # en PostgreSQL/Render), usamos el ultimo PERIODO REAL persistido
    # en HistoricoFlotaOperativa para la fecha consultada y cada unidad.
    #
    # IMPORTANTE:
    # - NO crea periodos.
    # - NO usa resumen_terminal_acumulado.
    # - NO modifica historico.
    # - NO afecta Velocidades.
    # ================================================================

    if not cobertura_por_unidad:

        q_periodo_real = db.query(
            HistoricoFlotaOperativa.unidad,
            HistoricoFlotaOperativa.fecha,
            func.max(
                HistoricoFlotaOperativa.periodo
            ).label("ultimo_periodo"),
        )

        if f_cobertura_desde:
            q_periodo_real = q_periodo_real.filter(
                HistoricoFlotaOperativa.fecha
                >=
                f_cobertura_desde
            )

        if f_cobertura_hasta:
            q_periodo_real = q_periodo_real.filter(
                HistoricoFlotaOperativa.fecha
                <=
                f_cobertura_hasta
            )

        if unidad:
            q_periodo_real = q_periodo_real.filter(
                func.upper(
                    HistoricoFlotaOperativa.unidad
                )
                ==
                _norm(unidad)
            )

        filas_periodo_real = (
            q_periodo_real
            .group_by(
                HistoricoFlotaOperativa.unidad,
                HistoricoFlotaOperativa.fecha,
            )
            .all()
        )

        for (
            unidad_real,
            fecha_real,
            ultimo_periodo_real,
        ) in filas_periodo_real:

            codigo_unidad = _norm(
                unidad_real
            )

            if codigo_unidad not in (
                "U8",
                "U9",
            ):
                continue

            try:
                periodo_real = int(
                    ultimo_periodo_real
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            if not (
                1 <= periodo_real <= 24
            ):
                continue

            # Periodo 1 = 00:00-00:59
            # Periodo 18 = 17:00-17:59
            hora_fin = periodo_real - 1

            hasta_real = (
                f"{hora_fin:02d}:59"
            )

            minutos_real = (
                hora_fin * 60
                +
                59
            )

            clave_real = (
                fecha_real,
                periodo_real,
            )

            actual = cobertura_por_unidad.get(
                codigo_unidad
            )

            if (
                actual is None
                or
                clave_real
                >
                actual.get(
                    "_clave",
                    (
                        date.min,
                        0,
                    )
                )
            ):
                cobertura_por_unidad[
                    codigo_unidad
                ] = {
                    "_clave": clave_real,
                    "unidad": codigo_unidad,
                    "fecha": (
                        fecha_real.isoformat()
                        if fecha_real
                        else None
                    ),
                    "desde": "00:00",
                    "hasta": hasta_real,
                    "minutos": minutos_real,
                    "dia_completo":
                        periodo_real >= 24,
                    "ultimo_periodo":
                        periodo_real,
                    "fuente":
                        "historico_flota_operativa",
                }


    for codigo_unidad in sorted(
        cobertura_por_unidad.keys()
    ):

        item = dict(
            cobertura_por_unidad[
                codigo_unidad
            ]
        )

        item.pop(
            "_clave",
            None
        )

        cobertura_fuente.append(
            item
        )




    # ================================================================
    # PPU SIN TRANSMISION POR DIA
    # Dias sin carga R1.6 no penalizan a la flota.
    # ================================================================

    sin_tx_dias = construir_sin_transmision_por_dias(
        db,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        unidad=unidad,
        terminal=terminal,
    )


    # ================================================================
    # R002 - ESTADO ACTUAL POWER BI
    # ================================================================
    #
    # Capa exclusivamente informativa.
    #
    # NO modifica:
    # - flota asignada
    # - operativa R1.6
    # - sin transmision
    # - porcentajes
    # - prestamos
    # - historicos
    #
    # R002 puede tener una fecha distinta al rango R1.6 consultado.
    # Por eso se presenta como "Estado actual Power BI" y NO como
    # causa historica de una ausencia de transmision.
    # ================================================================

    r002 = cargar_r002()

    mapa_r002 = (
        r002.get("ppus", {})
        if r002.get("disponible")
        else {}
    )

    for item in sin_transmision_detalle:

        ppu_r002 = _normalizar_ppu(
            item.get("ppu")
        )

        dato_r002 = mapa_r002.get(
            ppu_r002
        )

        if dato_r002:

            item["r002_encontrado"] = True
            item["estado_r002"] = (
                dato_r002.get("estado_r002")
            )
            item["terminal_r002"] = (
                dato_r002.get("terminal_r002")
            )
            item["interno_r002"] = (
                dato_r002.get("interno_r002")
            )

            terminal_base_r002 = _norm(
                item.get("terminal")
                or item.get("terminal_nombre")
            )

            terminal_powerbi = _norm(
                dato_r002.get("terminal_r002")
            )

            item["terminal_r002_difiere"] = bool(
                terminal_powerbi
                and terminal_base_r002
                and terminal_powerbi != terminal_base_r002
            )

        else:

            item["r002_encontrado"] = False
            item["estado_r002"] = None
            item["terminal_r002"] = None
            item["interno_r002"] = None
            item["terminal_r002_difiere"] = False

    estado_r002_resumen = {
        "disponible":
            bool(r002.get("disponible")),

        "archivo":
            r002.get("archivo"),

        "fecha_generacion":
            r002.get("fecha_generacion"),

        "total_ppu":
            int(r002.get("total_ppu") or 0),

        "total_cargas_sin_ppu":
            int(
                r002.get(
                    "total_cargas_sin_ppu"
                )
                or 0
            ),

        "cargas_sin_ppu":
            r002.get(
                "cargas_sin_ppu",
                {}
            ),

        "error":
            r002.get("error"),
    }


    # ================================================================
    # MATRIZ FLOTA - 4 SERIES CERTIFICADAS
    # ================================================================
    #
    # PERFIL TEORICO:
    #   buses requeridos por periodo segun perfil_operacional.xlsx.
    #
    # R1.6 PPU:
    #   PPU DISTINCT con presencia historica R1.6 por periodo.
    #
    # R2.2 PERIODO:
    #   PPU DISTINCT detectadas exactamente en el periodo.
    #
    # R2.2 ACUMULADO:
    #   PPU DISTINCT detectadas desde P01 hasta el periodo.
    #
    # IMPORTANTE:
    # - R1.6 NO se interpreta como intervalo inicio-fin de expedicion.
    # - R2.2 posterior a su cobertura real se devuelve como None.
    # - No modifica ninguna tabla.
    # ================================================================

    matriz_flota = None

    if (
        unidad
        and
        fecha_r22_matriz is not None
        and
        fecha_r22_hasta is not None
        and
        fecha_r22_matriz == fecha_r22_hasta
    ):

        # ------------------------------------------------------------
        # PERFIL TEORICO
        # ------------------------------------------------------------

        perfil_matriz = construir_perfil_operacional(
            fecha_r22_matriz,
            unidad,
        )

        perfil_por_periodo = defaultdict(int)

        for fila_perfil in (
            perfil_matriz.get(
                "intervalos_60",
                []
            )
        ):

            try:
                periodo_perfil = int(
                    fila_perfil.get(
                        "periodo"
                    )
                    or 0
                )
            except (TypeError, ValueError):
                continue

            if not 1 <= periodo_perfil <= 24:
                continue

            perfil_por_periodo[
                periodo_perfil
            ] += int(
                fila_perfil.get(
                    "perfil"
                )
                or 0
            )

        # ------------------------------------------------------------
        # MATRIZ POR TERMINAL - PERFIL
        # ------------------------------------------------------------

        perfil_terminal_periodo = defaultdict(int)

        for fila_perfil in (
            perfil_matriz.get(
                "intervalos_60",
                []
            )
        ):
            terminal_perfil = _norm(
                fila_perfil.get(
                    "terminal"
                )
            )

            try:
                periodo_perfil_terminal = int(
                    fila_perfil.get(
                        "periodo"
                    )
                    or 0
                )
            except (TypeError, ValueError):
                continue

            if (
                terminal_perfil
                and
                1 <= periodo_perfil_terminal <= 24
            ):
                perfil_terminal_periodo[
                    (
                        terminal_perfil,
                        periodo_perfil_terminal
                    )
                ] += int(
                    fila_perfil.get(
                        "perfil"
                    )
                    or 0
                )

        # ------------------------------------------------------------
        # R1.6 - PPU DISTINCT CON PRESENCIA POR PERIODO
        # ------------------------------------------------------------

        r16_ppus_periodo = defaultdict(set)
        r16_ppus_terminal_periodo = defaultdict(set)

        for presencia_matriz in presencias:

            fecha_presencia = (
                presencia_matriz.get(
                    "fecha"
                )
            )

            if (
                fecha_presencia
                !=
                fecha_r22_matriz
            ):
                continue

            try:
                periodo_r16 = int(
                    presencia_matriz.get(
                        "periodo"
                    )
                    or 0
                )
            except (TypeError, ValueError):
                continue

            if not 1 <= periodo_r16 <= 24:
                continue

            ppu_r16 = _normalizar_ppu(
                presencia_matriz.get(
                    "ppu"
                )
            )

            if ppu_r16:
                r16_ppus_periodo[
                    periodo_r16
                ].add(
                    ppu_r16
                )

                terminal_r16 = _norm(
                    presencia_matriz.get(
                        "terminal"
                    )
                )

                if terminal_r16:
                    r16_ppus_terminal_periodo[
                        (
                            terminal_r16,
                            periodo_r16
                        )
                    ].add(
                        ppu_r16
                    )

        # ------------------------------------------------------------
        # R2.2 - EXACTO Y ACUMULADO
        # ------------------------------------------------------------

        r22_ppus_periodo = defaultdict(set)
        r22_ppus_terminal_periodo = defaultdict(set)

        if resumen_r22_matriz is not None:

            for fila_r22_matriz in (
                resumen_r22_matriz.get(
                    "resumen_terminal",
                    []
                )
            ):

                try:
                    periodo_r22 = int(
                        fila_r22_matriz.get(
                            "periodo"
                        )
                        or 0
                    )
                except (TypeError, ValueError):
                    continue

                if not 1 <= periodo_r22 <= 24:
                    continue

                for ppu_r22 in (
                    fila_r22_matriz.get(
                        "ppus_periodo",
                        []
                    )
                    or []
                ):

                    ppu_r22_norm = (
                        _normalizar_ppu(
                            ppu_r22
                        )
                    )

                    if ppu_r22_norm:
                        r22_ppus_periodo[
                            periodo_r22
                        ].add(
                            ppu_r22_norm
                        )

                        terminal_r22 = _norm(
                            fila_r22_matriz.get(
                                "terminal"
                            )
                        )

                        if terminal_r22:
                            r22_ppus_terminal_periodo[
                                (
                                    terminal_r22,
                                    periodo_r22
                                )
                            ].add(
                                ppu_r22_norm
                            )

        ultimo_periodo_r22_matriz = None

        if cobertura_r22:

            try:
                ultimo_periodo_r22_matriz = int(
                    cobertura_r22.get(
                        "ultimo_periodo"
                    )
                    or 0
                )
            except (TypeError, ValueError):
                ultimo_periodo_r22_matriz = None

            if (
                ultimo_periodo_r22_matriz is not None
                and
                not (
                    1
                    <=
                    ultimo_periodo_r22_matriz
                    <=
                    24
                )
            ):
                ultimo_periodo_r22_matriz = None

        acumuladas_r22 = set()

        series_matriz_flota = []

        for periodo_matriz in range(1, 25):

            # Solo acumulamos PPU realmente observadas
            # en ese periodo.
            acumuladas_r22.update(
                r22_ppus_periodo.get(
                    periodo_matriz,
                    set()
                )
            )

            periodo_con_cobertura_r22 = (
                resumen_r22_matriz is not None
                and
                ultimo_periodo_r22_matriz is not None
                and
                periodo_matriz
                <=
                ultimo_periodo_r22_matriz
            )

            series_matriz_flota.append({
                "periodo":
                    periodo_matriz,

                "etiqueta":
                    f"P{periodo_matriz:02d}",

                "perfil_teorico":
                    int(
                        perfil_por_periodo.get(
                            periodo_matriz,
                            0
                        )
                    ),

                "r16_ppu":
                    len(
                        r16_ppus_periodo.get(
                            periodo_matriz,
                            set()
                        )
                    ),

                "r22_periodo":
                    (
                        len(
                            r22_ppus_periodo.get(
                                periodo_matriz,
                                set()
                            )
                        )
                        if periodo_con_cobertura_r22
                        else None
                    ),

                "r22_acumulado":
                    (
                        len(
                            acumuladas_r22
                        )
                        if periodo_con_cobertura_r22
                        else None
                    ),

                "estado_r22":
                    (
                        "CON_DATOS"
                        if periodo_con_cobertura_r22
                        else "SIN_DATOS"
                    ),
            })

        # ------------------------------------------------------------
        # SERIES REALES POR TERMINAL
        # ------------------------------------------------------------

        terminales_matriz = sorted(
            {
                terminal
                for terminal, _periodo
                in perfil_terminal_periodo.keys()
            }
            |
            {
                terminal
                for terminal, _periodo
                in r22_ppus_terminal_periodo.keys()
            }
            |
            {
                terminal
                for terminal, _periodo
                in r16_ppus_terminal_periodo.keys()
            }
        )

        series_terminales_matriz = []

        for terminal_matriz in terminales_matriz:

            acumuladas_terminal_r22 = set()
            series_terminal = []

            for periodo_matriz in range(1, 25):

                exactas_terminal_r22 = (
                    r22_ppus_terminal_periodo.get(
                        (
                            terminal_matriz,
                            periodo_matriz
                        ),
                        set()
                    )
                )

                acumuladas_terminal_r22.update(
                    exactas_terminal_r22
                )

                periodo_con_cobertura_terminal = (
                    resumen_r22_matriz is not None
                    and
                    ultimo_periodo_r22_matriz is not None
                    and
                    periodo_matriz
                    <=
                    ultimo_periodo_r22_matriz
                )

                series_terminal.append({
                    "periodo":
                        periodo_matriz,

                    "etiqueta":
                        f"P{periodo_matriz:02d}",

                    "perfil_teorico":
                        int(
                            perfil_terminal_periodo.get(
                                (
                                    terminal_matriz,
                                    periodo_matriz
                                ),
                                0
                            )
                        ),

                    "r16_ppu":
                        len(
                            r16_ppus_terminal_periodo.get(
                                (
                                    terminal_matriz,
                                    periodo_matriz
                                ),
                                set()
                            )
                        ),

                    "r22_periodo":
                        (
                            len(
                                exactas_terminal_r22
                            )
                            if periodo_con_cobertura_terminal
                            else None
                        ),

                    # FLOTA-R22-DETALLE-PPU
                    # PPU DISTINCT detectadas exactamente
                    # dentro del periodo.
                    "r22_ppus_periodo":
                        (
                            sorted(
                                exactas_terminal_r22
                            )
                            if periodo_con_cobertura_terminal
                            else []
                        ),

                    "r22_acumulado":
                        (
                            len(
                                acumuladas_terminal_r22
                            )
                            if periodo_con_cobertura_terminal
                            else None
                        ),

                    # PPU DISTINCT observadas desde P01
                    # hasta este periodo.
                    "r22_ppus_acumuladas":
                        (
                            sorted(
                                acumuladas_terminal_r22
                            )
                            if periodo_con_cobertura_terminal
                            else []
                        ),

                    "estado_r22":
                        (
                            "CON_DATOS"
                            if periodo_con_cobertura_terminal
                            else "SIN_DATOS"
                        ),
                })

            series_terminales_matriz.append({
                "terminal":
                    terminal_matriz,

                "series":
                    series_terminal,
            })

        matriz_flota = {
            "fecha":
                fecha_r22_matriz.isoformat(),

            "unidad":
                _norm(unidad),

            "ultimo_periodo_r22":
                ultimo_periodo_r22_matriz,

            "fuente_perfil":
                "perfil_operacional.xlsx",

            "fuente_r16":
                "HistoricoFlotaOperativaServicio",

            "fuente_r22":
                (
                    "R2.2"
                    if resumen_r22_matriz is not None
                    else None
                ),

            "series":
                series_matriz_flota,

            "terminales":
                series_terminales_matriz,
        }

    return {
        "matriz_flota": matriz_flota,
        "estado_actual_r002": estado_r002_resumen,
        "resumen_sin_transmision_dias": sin_tx_dias["resumen"],
        "sin_transmision_detalle_dias": sin_tx_dias["detalle"],
        "dias_rango_sin_transmision": sin_tx_dias["dias_rango"],
        "dias_evaluables_sin_transmision": sin_tx_dias["dias_evaluables"],
        "dias_sin_datos_sin_transmision": sin_tx_dias["dias_sin_datos"],
        "fechas_evaluables_sin_transmision": sin_tx_dias["fechas_evaluables"],
        "fechas_sin_datos_sin_transmision": sin_tx_dias["fechas_sin_datos"],
        "kpis": kpis,
        "resumen_unidades": resumen_unidades,
        "cobertura_fuente": cobertura_fuente,
        "cobertura_r22": cobertura_r22,
        "resumen_terminal": resumen_terminal,
        "resumen_terminal_acumulado": resumen_terminal_acumulado,
        "resumen_terminal_global": resumen_terminal_global,
        "prestamos_resumen": prestamos_resumen,
        "prestamos_detalle": prestamos_detalle,
        "prestamos_revision": prestamos_revision,
        "total_global": total_global,
        "alertas_ppu": alertas_ppu,
        "sin_transmision_detalle": sin_transmision_detalle,
        "resumen_sin_transmision": resumen_sin_transmision,
        "resumen_servicio": resumen_servicio,
        "total_presencias_servicio_ppu": len(presencias),
    }


def consultar_detalle(
    db: Session,
    fecha: str,
    periodo: int,
    terminal: str,
    servicio: str | None = None,
    unidad: str | None = None,
) -> list[dict]:
    presencias = construir_presencias(
        db=db,
        fecha_desde=fecha,
        fecha_hasta=fecha,
        unidad=unidad,
        terminal=terminal,
        servicio=servicio,
        periodo_inicial=periodo,
        periodo_final=periodo,
    )

    # Si no se filtra servicio: una fila por PPU, consolidando servicios.
    agrupado = {}
    for p in presencias:
        clave = p["ppu"] if not servicio else (p["ppu"], p["servicio"])
        item = agrupado.get(clave)
        if item is None:
            agrupado[clave] = {
                "ppu": p["ppu"],
                "servicios": {p["servicio"]},
                "terminal": p["terminal"],
                "primera_transmision": p["primera_transmision"],
                "ultima_transmision": p["ultima_transmision"],
            }
        else:
            item["servicios"].add(p["servicio"])
            item["primera_transmision"] = min(item["primera_transmision"], p["primera_transmision"])
            item["ultima_transmision"] = max(item["ultima_transmision"], p["ultima_transmision"])

    salida = []
    for item in agrupado.values():
        salida.append({
            "ppu": item["ppu"],
            "servicio": ", ".join(sorted(item["servicios"])),
            "terminal": TERMINAL_LABELS.get(item["terminal"], item["terminal"].title()),
            "primera_transmision": item["primera_transmision"].strftime("%H:%M:%S"),
            "ultima_transmision": item["ultima_transmision"].strftime("%H:%M:%S"),
        })
    salida.sort(key=lambda x: (x["servicio"], x["ppu"]))
    return salida





