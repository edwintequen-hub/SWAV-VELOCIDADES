"""
=========================================================
SWAV
Flota Operativa - Lector independiente R1.6 completo
=========================================================

REGLA:
- Lee directamente el archivo original R1.6.
- NO aplica filtros de Velocidades.
- NO elimina velocidad 0.
- NO elimina FIN SERVICIO 1900.
- NO usa MotorComparacion.
- NO calcula velocidad real/teorica.
- NO calcula IP/IE.
- NO clasifica SIMPLE/COMPLEJO.
=========================================================
"""

from __future__ import annotations

import csv
import re

from pathlib import Path
from typing import Any


# =========================================================
# NORMALIZACION
# =========================================================

def normalizar_texto(
    valor: Any,
) -> str:

    if valor is None:
        return ""

    return str(
        valor
    ).strip()


def normalizar_ppu(
    valor: Any,
) -> str:

    texto = normalizar_texto(
        valor
    ).upper()

    return re.sub(
        r"[^A-Z0-9]",
        "",
        texto,
    )


# =========================================================
# LECTURA DEL ARCHIVO
# =========================================================

def _leer_lineas(
    archivo: Path,
) -> list[str]:

    codificaciones = (
        "utf-8-sig",
        "utf-8",
        "cp1252",
        "latin-1",
    )

    ultimo_error = None

    for encoding in codificaciones:

        try:

            return archivo.read_text(
                encoding=encoding,
            ).splitlines()

        except UnicodeDecodeError as exc:

            ultimo_error = exc

    raise RuntimeError(
        "No fue posible decodificar "
        f"el R1.6: {ultimo_error}"
    )


def _detectar_header(
    lineas: list[str],
) -> int:

    for indice, linea in enumerate(
        lineas
    ):

        mayus = linea.upper()

        if (
            "SERVICIO" in mayus
            and
            "CODIGO BUS" in mayus
            and
            "PATENTE BUS" in mayus
            and
            "INICIO SERVICIO" in mayus
        ):

            return indice

    raise ValueError(
        "No se encontro el encabezado "
        "del reporte R1.6."
    )


def _obtener_metadata(
    lineas: list[str],
    indice_header: int,
) -> dict[str, str]:

    metadata = {}

    buscados = {
        "Unidad de Negocio": "unidad_reporte",
        "Fecha Desde": "fecha_desde",
        "Fecha Hasta": "fecha_hasta",
        "Hora Desde": "hora_desde",
        "Hora Hasta": "hora_hasta",
        "Tolerancia": "tolerancia",
    }

    for linea in lineas[
        :indice_header
    ]:

        columnas = linea.split(
            "\t"
        )

        if not columnas:
            continue

        etiqueta = (
            columnas[0]
            .replace(":", "")
            .strip()
        )

        for buscado, clave in (
            buscados.items()
        ):

            if (
                etiqueta.lower()
                ==
                buscado.lower()
            ):

                valor = ""

                if len(columnas) > 1:

                    valor = (
                        columnas[1]
                        .strip()
                    )

                metadata[
                    clave
                ] = valor

    return metadata


# =========================================================
# FUNCION PRINCIPAL
# =========================================================

def leer_r16_completo(
    archivo: str | Path,
    unidad: str | None = None,
) -> dict:

    ruta = Path(
        archivo
    ).resolve()

    if not ruta.exists():

        raise FileNotFoundError(
            f"No existe R1.6: {ruta}"
        )

    if not ruta.is_file():

        raise ValueError(
            f"No es archivo: {ruta}"
        )

    lineas = _leer_lineas(
        ruta
    )

    indice_header = (
        _detectar_header(
            lineas
        )
    )

    metadata = (
        _obtener_metadata(
            lineas,
            indice_header,
        )
    )

    lector = csv.DictReader(
        lineas[
            indice_header:
        ],
        delimiter="\t",
    )

    filas = []

    for numero_fila, fila in enumerate(
        lector,
        start=indice_header + 2,
    ):

        # -------------------------------------------------
        # IMPORTANTE:
        # NO FILTRAMOS FILAS DEL R1.6
        # -------------------------------------------------

        fila_limpia = {}

        for clave, valor in (
            fila.items()
        ):

            if clave is None:
                continue

            clave_limpia = (
                str(clave)
                .strip()
            )

            fila_limpia[
                clave_limpia
            ] = normalizar_texto(
                valor
            )

        # Evitar solamente lineas fisicamente vacias
        # posteriores al contenido real del archivo.
        if not any(
            fila_limpia.values()
        ):
            continue

        fila_limpia[
            "_numero_fila"
        ] = numero_fila

        fila_limpia[
            "_ppu_normalizada"
        ] = normalizar_ppu(
            fila_limpia.get(
                "PATENTE BUS"
            )
        )

        filas.append(
            fila_limpia
        )


    ppu_unicas = {
        fila[
            "_ppu_normalizada"
        ]
        for fila in filas
        if fila[
            "_ppu_normalizada"
        ]
    }


    return {
        "estado":
            "OK",

        "fuente":
            "R1.6_COMPLETO",

        "archivo":
            str(ruta),

        "unidad":
            (
                str(unidad)
                .strip()
                .upper()
                if unidad
                else None
            ),

        "metadata":
            metadata,

        "fila_encabezado":
            indice_header + 1,

        "total_filas":
            len(filas),

        "ppu_unicas":
            len(ppu_unicas),

        "filas":
            filas,
    }
