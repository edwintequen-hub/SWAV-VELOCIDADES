from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def normalizar_ppu(valor) -> str:
    return re.sub(
        r"[^A-Z0-9]",
        "",
        str(valor or "").upper(),
    )


def parsear_fecha_r22(valor):
    texto = str(valor or "").strip()

    for formato in (
        "%d/%m/%Y %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d-%m-%Y %H:%M",
    ):
        try:
            return datetime.strptime(
                texto,
                formato,
            )
        except ValueError:
            pass

    return None


def leer_r22(
    ruta_archivo,
    fecha=None,
):
    """
    Lee el CSV R2.2 V9.

    Mapeo certificado:
      C01 = fecha/hora del registro
      C06 = PPU
      C09 = ruta observada
      C10 = servicio base
      C13 = inicio de expedicion observado
      C16 = ruta/variante/sentido

    Esta funcion NO calcula velocidades.
    Esta funcion NO infiere taller.
    Esta funcion NO modifica BD.
    """

    ruta = Path(ruta_archivo)

    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe R2.2: {ruta}"
        )

    fecha_objetivo = None

    if fecha is not None:
        if isinstance(fecha, datetime):
            fecha_objetivo = fecha.date()
        elif hasattr(fecha, "year"):
            fecha_objetivo = fecha
        else:
            fecha_objetivo = datetime.strptime(
                str(fecha),
                "%Y-%m-%d",
            ).date()

    registros = []

    with ruta.open(
        "r",
        encoding="latin-1",
        errors="replace",
        newline="",
    ) as archivo:

        lector = csv.reader(
            archivo,
            delimiter=";",
        )

        for fila in lector:

            # Exportacion V9 certificada: 16 columnas.
            if len(fila) != 16:
                continue

            fecha_hora = parsear_fecha_r22(
                fila[0]
            )

            if fecha_hora is None:
                continue

            if (
                fecha_objetivo is not None
                and
                fecha_hora.date()
                != fecha_objetivo
            ):
                continue

            ppu = normalizar_ppu(
                fila[5]
            )

            if not ppu:
                continue

            registros.append({
                "fecha_hora": fecha_hora,
                "fecha": fecha_hora.date(),
                "periodo": fecha_hora.hour + 1,
                "ppu": ppu,
                "ruta_c09": str(
                    fila[8] or ""
                ).strip(),
                "servicio_c10": str(
                    fila[9] or ""
                ).strip(),
                "inicio_expedicion_c13": (
                    parsear_fecha_r22(
                        fila[12]
                    )
                ),
                "ruta_c16": str(
                    fila[15] or ""
                ).strip(),
            })

    return registros


def construir_resumen_r22(
    ruta_archivo,
    fecha=None,
):
    """
    Construye dos universos diferentes:

    - PPU periodo:
      PPU DISTINCT con al menos un registro R2.2
      dentro de ese periodo.

    - PPU acumulada:
      PPU DISTINCT observada desde P01 hasta
      el periodo evaluado.

    Una PPU nunca suma dos veces en el acumulado.
    """

    registros = leer_r22(
        ruta_archivo=ruta_archivo,
        fecha=fecha,
    )

    ppus_periodo = defaultdict(set)

    for registro in registros:
        ppus_periodo[
            registro["periodo"]
        ].add(
            registro["ppu"]
        )

    acumuladas = set()
    periodos = []

    for periodo in range(1, 25):

        actuales = set(
            ppus_periodo.get(
                periodo,
                set(),
            )
        )

        nuevas = actuales - acumuladas
        ya_vistas = actuales & acumuladas

        acumuladas.update(
            actuales
        )

        periodos.append({
            "periodo": periodo,
            "ppu_periodo": len(
                actuales
            ),
            "nuevas": len(
                nuevas
            ),
            "ya_vistas": len(
                ya_vistas
            ),
            "ppu_acumuladas": len(
                acumuladas
            ),
            "ppus_periodo": sorted(
                actuales
            ),
            "ppus_nuevas": sorted(
                nuevas
            ),
            "ppus_acumuladas": sorted(
                acumuladas
            ),
        })

    return {
        "total_registros": len(
            registros
        ),
        "ppu_distintas": len(
            {
                r["ppu"]
                for r in registros
            }
        ),
        "periodos": periodos,
    }



def construir_resumen_terminal_r22(
    ruta_archivo,
    asignaciones,
    fecha=None,
    unidad=None,
):
    """
    Cruza R2.2 con el catalogo individual PPU -> terminal.

    Devuelve por terminal y periodo:

    - ppu_periodo:
      PPU DISTINCT detectadas en ese periodo.

    - nuevas:
      PPU detectadas por primera vez hasta ese periodo.

    - operativa_acumulada:
      PPU DISTINCT observadas desde P01 hasta el periodo.

    La acumulacion se realiza independientemente por terminal.

    No usa R001 como universo PPU.
    No calcula taller.
    No modifica BD.
    """

    registros = leer_r22(
        ruta_archivo=ruta_archivo,
        fecha=fecha,
    )

    mapa_asignacion = {}

    for asignacion in asignaciones:

        if unidad:
            unidad_asignacion = str(
                getattr(
                    asignacion,
                    "unidad",
                    "",
                )
                or ""
            ).strip().upper()

            if (
                unidad_asignacion
                !=
                str(unidad).strip().upper()
            ):
                continue

        ppu = normalizar_ppu(
            getattr(
                asignacion,
                "ppu",
                "",
            )
        )

        terminal = str(
            getattr(
                asignacion,
                "terminal",
                "",
            )
            or ""
        ).strip().upper()

        if ppu and terminal:
            mapa_asignacion[ppu] = terminal

    exactas = defaultdict(
        lambda: defaultdict(set)
    )

    sin_asignar = set()

    for registro in registros:

        ppu = registro["ppu"]

        terminal = mapa_asignacion.get(
            ppu
        )

        if not terminal:
            sin_asignar.add(ppu)
            continue

        exactas[
            terminal
        ][
            registro["periodo"]
        ].add(
            ppu
        )

    terminales = sorted(
        set(mapa_asignacion.values())
    )

    resumen = []

    for terminal in terminales:

        acumuladas = set()

        for periodo in range(1, 25):

            actuales = set(
                exactas.get(
                    terminal,
                    {},
                ).get(
                    periodo,
                    set(),
                )
            )

            nuevas = (
                actuales
                -
                acumuladas
            )

            acumuladas.update(
                actuales
            )

            resumen.append({
                "terminal": terminal,
                "periodo": periodo,
                "ppu_periodo": len(
                    actuales
                ),
                "nuevas": len(
                    nuevas
                ),
                "operativa_acumulada": len(
                    acumuladas
                ),
                "ppus_periodo": sorted(
                    actuales
                ),
                "ppus_nuevas": sorted(
                    nuevas
                ),
                "ppus_acumuladas": sorted(
                    acumuladas
                ),
            })

    fechas_hora = sorted(
        r["fecha_hora"]
        for r in registros
        if r.get("fecha_hora") is not None
    )

    primera_transmision = (
        fechas_hora[0]
        if fechas_hora
        else None
    )

    ultima_transmision = (
        fechas_hora[-1]
        if fechas_hora
        else None
    )

    ultimo_periodo = (
        ultima_transmision.hour + 1
        if ultima_transmision is not None
        else None
    )

    return {
        "resumen_terminal": resumen,
        "ppu_sin_asignar": sorted(
            sin_asignar
        ),
        "total_sin_asignar": len(
            sin_asignar
        ),
        "cobertura": {
            "primera_transmision":
                primera_transmision,
            "ultima_transmision":
                ultima_transmision,
            "ultimo_periodo":
                ultimo_periodo,
        },
    }
