from pathlib import Path
import csv
from datetime import datetime


def _hora_a_minutos(valor):
    if valor is None:
        return None

    texto = str(valor).strip()

    for formato in ("%H:%M:%S", "%H:%M"):
        try:
            fecha = datetime.strptime(texto, formato)
            return fecha.hour * 60 + fecha.minute
        except Exception:
            pass

    return None


def _datetime_a_minutos(valor):
    if valor is None:
        return None

    texto = str(valor).strip()

    formatos = (
        "%d/%m/%Y %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d-%m-%Y %H:%M",
    )

    for formato in formatos:
        try:
            fecha = datetime.strptime(texto, formato)
            return fecha.hour * 60 + fecha.minute
        except Exception:
            pass

    return None


def _diferencia_circular_minutos(inicio, objetivo):
    if inicio is None or objetivo is None:
        return None

    diferencia = objetivo - inicio

    if diferencia < -720:
        diferencia += 1440
    elif diferencia > 720:
        diferencia -= 1440

    return abs(diferencia)


def _buscar_r1_6(archivo_origen=None):
    """
    Busca el R1.6 correspondiente al registro histórico.

    PRIORIDAD:
    1. archivo_origen guardado en historico_registros.
    2. Si no existe, utiliza el archivo más reciente como
       mecanismo de respaldo.

    Nunca se debe cambiar el archivo histórico por otro
    cuando existe archivo_origen.
    """

    carpeta = Path("./uploads")

    if not carpeta.exists():
        return None

    # ---------------------------------------------------------
    # 1. ARCHIVO DE ORIGEN DEL HISTÓRICO
    # ---------------------------------------------------------

    if archivo_origen:

        nombre = Path(
            str(archivo_origen).strip()
        ).name

        if nombre:

            archivo = carpeta / nombre

            if archivo.exists():
                return archivo

    # ---------------------------------------------------------
    # 2. RESPALDO: ARCHIVO MÁS RECIENTE
    # ---------------------------------------------------------

    archivos = list(
        carpeta.glob("RptBusEnServicio10xCsv*.csv")
    )

    if not archivos:
        return None

    archivos.sort(
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    return archivos[0]


def _leer_r1_6(archivo_origen=None):
    """
    Lee el R1.6 correspondiente al archivo de origen
    del registro histórico.

    Columnas comprobadas:

        0 = SERVICIO
        2 = PATENTE BUS
        3 = RUTA
        4 = TIPO DIA
        5 = FRANJA HORARIA
        6 = INICIO SERVICIO
        7 = FIN SERVICIO
        15 = VELOCIDAD (Km/Min)
    """

    archivo = _buscar_r1_6(
        archivo_origen
    )

    if archivo is None:
        return []

    filas = []

    try:

        with open(
            archivo,
            "r",
            encoding="utf-8-sig",
            errors="replace",
            newline=""
        ) as f:

            lector = csv.reader(
                f,
                delimiter=";"
            )

            for fila in lector:

                if len(fila) < 8:
                    continue

                filas.append(fila)

    except Exception:
        return []

    return filas



def _parse_datetime_r16(valor):
    if valor is None:
        return None

    texto = str(valor).strip()

    if not texto:
        return None

    for formato in (
        "%d/%m/%Y %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(
                texto,
                formato
            )
        except Exception:
            pass

    return None



def _obtener_ppu_periodo(db, reg):
    """
    Reconstruye las expediciones históricas directamente
    desde el R1.6.

    Una expedición cuenta cuando termina correctamente.

    Los registros consecutivos de una misma PPU se agrupan
    cuando la separación entre el fin anterior y el inicio
    siguiente es <= 120 segundos.
    """

    if reg.periodo is None:
        return []

    # =========================================================
    # 1. IDENTIFICAR PERÍODO HORARIO
    # =========================================================
    #
    # Regla SWAV / Macro VBA:
    # PERIODO = Hour(HoraInicio) + 1
    #
    # Periodo 1  = 00:00 - 00:59
    # Periodo 14 = 13:00 - 13:59
    # Periodo 15 = 14:00 - 14:59
    # Periodo 24 = 23:00 - 23:59
    # =========================================================

    try:

        indice = int(
            reg.periodo
        )

    except Exception:

        return []

    if (
        indice < 1
        or indice > 24
    ):

        return []

    hora_inicio_periodo = (
        (indice - 1) * 60
    )

    hora_fin_periodo = (
        hora_inicio_periodo + 20
    )

    # =========================================================
    # 3. LEER R1.6 DEL HISTÓRICO
    # =========================================================

    archivo_origen = getattr(
        reg,
        "archivo_origen",
        None
    )

    filas = _leer_r1_6(
        archivo_origen
    )

    if not filas:
        return []

    ruta_buscada = (
        str(reg.ruta).strip()
        if reg.ruta
        else ""
    )

    tipo_dia_buscado = (
        str(reg.tipo_dia).strip().upper()
        if reg.tipo_dia
        else ""
    )

    # =========================================================
    # 4. OBTENER REGISTROS R1.6
    # =========================================================

    registros = []

    for numero_fila, fila in enumerate(
        filas,
        start=1
    ):

        if len(fila) < 8:
            continue

        patente = str(
            fila[2]
        ).strip()

        ruta = str(
            fila[3]
        ).strip()

        tipo_dia = str(
            fila[4]
        ).strip().upper()

        inicio_texto = str(
            fila[6]
        ).strip()

        fin_texto = str(
            fila[7]
        ).strip()

        if not patente:
            continue

        if ruta != ruta_buscada:
            continue

        if tipo_dia != tipo_dia_buscado:
            continue

        inicio_dt = _parse_datetime_r16(
            inicio_texto
        )

        fin_dt = _parse_datetime_r16(
            fin_texto
        )

        if inicio_dt is None:
            continue

        # FIN 1900 = expedición no terminada

        if (
            fin_dt is None
            or fin_dt.year == 1900
        ):
            continue

        inicio = (
            inicio_dt.hour * 60
            + inicio_dt.minute
        )

        if (
            inicio < hora_inicio_periodo
            or inicio > hora_fin_periodo
        ):
            continue

        # =====================================================
        # VELOCIDAD
        # =====================================================

        velocidad = None

        if len(fila) > 15:

            texto_velocidad = (
                str(fila[15])
                .strip()
                .replace(",", ".")
            )

            try:

                velocidad = (
                    float(texto_velocidad)
                    * 60
                )

            except Exception:

                velocidad = None

        registros.append(
            {
                "fila_r1_6": numero_fila,
                "patente": patente,
                "inicio_dt": inicio_dt,
                "fin_dt": fin_dt,
                "inicio": inicio_texto,
                "fin": fin_texto,
                "velocidad_real": velocidad,
            }
        )

    if not registros:
        return []

    # =========================================================
    # 5. ORDENAR
    # =========================================================

    registros.sort(
        key=lambda x: (
            x["inicio_dt"],
            x["patente"],
        )
    )

    # =========================================================
    # 6. RECONSTRUIR EXPEDICIONES
    # =========================================================

    MARGEN_CONTINUIDAD_SEGUNDOS = 120

    expediciones = []

    actual = None

    for registro in registros:

        if actual is None:

            actual = {
                "patente": registro["patente"],
                "inicio_dt": registro["inicio_dt"],
                "fin_dt": registro["fin_dt"],
                "inicio": registro["inicio"],
                "fin": registro["fin"],
                "velocidad_real": registro[
                    "velocidad_real"
                ],
                "fila_r1_6": registro[
                    "fila_r1_6"
                ],
                "registros": 1,
            }

            continue

        mismo_ppu = (
            registro["patente"]
            == actual["patente"]
        )

        separacion = (
            registro["inicio_dt"]
            - actual["fin_dt"]
        ).total_seconds()

        consecutiva = (
            separacion >= 0
            and separacion
            <= MARGEN_CONTINUIDAD_SEGUNDOS
        )

        if (
            mismo_ppu
            and consecutiva
        ):

            actual["fin_dt"] = (
                registro["fin_dt"]
            )

            actual["fin"] = (
                registro["fin"]
            )

            actual["registros"] += 1

            if (
                actual["velocidad_real"]
                is None
            ):

                actual["velocidad_real"] = (
                    registro["velocidad_real"]
                )

        else:

            expediciones.append(
                actual
            )

            actual = {
                "patente": registro["patente"],
                "inicio_dt": registro["inicio_dt"],
                "fin_dt": registro["fin_dt"],
                "inicio": registro["inicio"],
                "fin": registro["fin"],
                "velocidad_real": registro[
                    "velocidad_real"
                ],
                "fila_r1_6": registro[
                    "fila_r1_6"
                ],
                "registros": 1,
            }

    if actual is not None:

        expediciones.append(
            actual
        )

    # =========================================================
    # 7. CONSTRUIR RESULTADO
    # =========================================================

    resultado = []

    velocidad_teorica = (
        reg.velocidad_teorica
    )

    for expedicion in expediciones:

        velocidad_real = (
            expedicion["velocidad_real"]
        )

        reduccion = None

        if (
            velocidad_real is not None
            and velocidad_teorica is not None
            and velocidad_teorica != 0
        ):

            reduccion = round(
                (
                    (
                        velocidad_teorica
                        - velocidad_real
                    )
                    / velocidad_teorica
                ) * 100,
                2
            )

        # =====================================================
        # CLASIFICACIÓN INDIVIDUAL DE LA PPU
        # =====================================================

        indicador = str(
            getattr(
                reg,
                "indicador_tiempo_espera",
                ""
            )
            or ""
        ).strip().upper()

        estado_ppu = "OK"

        if reduccion is not None:

            if indicador == "IP":

                if reduccion >= 20:
                    estado_ppu = "COMPLEJO"

                elif reduccion >= 10:
                    estado_ppu = "SIMPLE"

            elif indicador == "IE":

                if reduccion >= 30:
                    estado_ppu = "COMPLEJO"

                elif reduccion >= 10:
                    estado_ppu = "SIMPLE"

        resultado.append(
            {
                "patente": expedicion[
                    "patente"
                ],

                "servicio_empresa": reg.ruta,

                "inicio": expedicion[
                    "inicio"
                ],

                "fin": expedicion[
                    "fin"
                ],

                "velocidad_real": (
                    round(
                        velocidad_real,
                        2
                    )
                    if velocidad_real is not None
                    else None
                ),

                "velocidad_teorica": (
                    round(
                        velocidad_teorica,
                        2
                    )
                    if velocidad_teorica is not None
                    else None
                ),

                "reduccion": reduccion,

                "estado": estado_ppu,

                "origen": "R1.6",

                "fila_r1_6": expedicion[
                    "fila_r1_6"
                ],

                "registros_r1_6": expedicion[
                    "registros"
                ],
            }
        )

    return resultado



