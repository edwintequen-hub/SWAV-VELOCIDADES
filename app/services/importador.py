"""
=========================================================
SWAV - Sistema Web de AnÃ¡lisis de Velocidades
Importador Oficial R1.6
=========================================================
"""

from datetime import datetime
from pathlib import Path
import hashlib
import re

import pandas as pd
from sqlalchemy.orm import Session

from app.utils.parser_rutas import ParserRutas
from app.services.catalogo import Catalogo

from app.config import (
    CSV_ENCODING,
    CSV_HEADER_ROW,
    CSV_SEPARATOR,
)

from app.models import (
    Expedicion,
    HistorialImportacion,
)


class ImportadorR16:

    COLUMNAS_OBLIGATORIAS = [

        "SERVICIO",
        "CODIGO BUS",
        "PATENTE BUS",
        "RUTA",
        "TIPO DIA",
        "FRANJA HORARIA",
        "INICIO SERVICIO",
        "FIN SERVICIO",
        "ZONA HORARIA",
        "TIEMPO DE VIAJE REAL",
        "RANGO ESPERADO DE VIAJE POR FRANJA HORARIA",
        "CUMPLIMIENTO",
        "PLAZAS",
        "INICIO SERVICIO (Km)",
        "FIN SERVICIO (Km)",
        "VELOCIDAD (Km/Min)",

    ]

    def __init__(self, db: Session):

        self.db = db

        self.df = None

        self.archivo = ""

        self.carga_hash = ""

        self.unidad = ""

        self.registros_validos = 0

        self.registros_descartados = 0

        # =================================================
        # VENTANA TEMPORAL DEL PROPIO R1.6
        # =================================================

        self.ventana_desde = None

        self.ventana_hasta = None

        self.registros_fuera_rango = 0

    # =====================================================
    # LEER VENTANA TEMPORAL DEL R1.6
    # =====================================================

    def leer_ventana_reporte(self, archivo):

        """
        Lee la ventana temporal declarada dentro del R1.6.

        El formato real del archivo puede contener muchas
        columnas vacÃ­as entre la fecha y la hora, por ejemplo:

            10-08-2026;;;;;;;;;;;;;;; 0:00;;;;;;;;;;;;;;;

        Por eso se extraen fecha y hora mediante patrones,
        sin modificar el resto del procesamiento.
        """

        valores = {}

        debe_cerrar = False

        # =====================================================
        # OBTENER LÃNEAS DEL ARCHIVO
        # =====================================================

        if hasattr(archivo, "read"):

            archivo.seek(0)

            archivo_lineas = archivo

        else:

            archivo_lineas = open(
                archivo,
                "r",
                encoding=CSV_ENCODING,
                errors="replace"
            )

            debe_cerrar = True

        try:

            for linea in archivo_lineas:

                if isinstance(linea, bytes):

                    linea = linea.decode(
                        CSV_ENCODING,
                        errors="replace"
                    )

                texto = str(linea).strip()

                # -------------------------------------------------
                # FORMATO JASPER / DESCARGA AUTOMATICA
                # -------------------------------------------------

                texto_upper = texto.upper()

                if texto_upper.startswith("IN_FECHAINICIAL="):
                    valores["FECHA DESDE"] = texto.split("=", 1)[1].strip()

                elif texto_upper.startswith("IN_FECHAFINAL="):
                    valores["FECHA HASTA"] = texto.split("=", 1)[1].strip()

                elif texto_upper.startswith("IN_HORAINICIAL="):
                    valores["HORA DESDE"] = texto.split("=", 1)[1].strip()

                elif texto_upper.startswith("IN_HORAFINAL="):
                    valores["HORA HASTA"] = texto.split("=", 1)[1].strip()


                # -------------------------------------------------
                # Detectar encabezado de datos
                # -------------------------------------------------

                if (
                    texto_upper.startswith("SERVICIO")
                    and "CODIGO BUS" in texto_upper
                    and "PATENTE BUS" in texto_upper
                ):

                    break

                # -------------------------------------------------
                # Normalizar solamente para detectar la etiqueta
                # -------------------------------------------------

                # -------------------------------------------------
                # Detectar ventana temporal
                #
                # Soporta:
                # Fecha Desde;23-08-2026
                # Fecha Desde : 23/08/2026
                # -------------------------------------------------

                if texto_upper.startswith("FECHA DESDE"):

                    coincidencia = re.search(
                        r"\b\d{2}[/-]\d{2}[/-]\d{4}\b",
                        texto
                    )

                    if coincidencia:

                        valores["FECHA DESDE"] = (
                            coincidencia.group(0)
                            .replace("/", "-")
                        )

                elif texto_upper.startswith("FECHA HASTA"):

                    coincidencia = re.search(
                        r"\b\d{2}[/-]\d{2}[/-]\d{4}\b",
                        texto
                    )

                    if coincidencia:

                        valores["FECHA HASTA"] = (
                            coincidencia.group(0)
                            .replace("/", "-")
                        )

                elif texto_upper.startswith("HORA DESDE"):

                    coincidencia = re.search(
                        r"\b\d{1,2}:\d{2}(?::\d{2})?\b",
                        texto
                    )

                    if coincidencia:

                        valores["HORA DESDE"] = (
                            coincidencia.group(0)
                        )

                elif texto_upper.startswith("HORA HASTA"):

                    coincidencia = re.search(
                        r"\b\d{1,2}:\d{2}(?::\d{2})?\b",
                        texto
                    )

                    if coincidencia:

                        valores["HORA HASTA"] = (
                            coincidencia.group(0)
                        )

        finally:

            if debe_cerrar:

                archivo_lineas.close()

        # =====================================================
        # OBTENER VALORES
        # =====================================================

        fecha_desde = valores.get(
            "FECHA DESDE"
        )

        fecha_hasta = valores.get(
            "FECHA HASTA"
        )

        hora_desde = valores.get(
            "HORA DESDE"
        )

        hora_hasta = valores.get(
            "HORA HASTA"
        )

        print("=" * 80)

        print("DATOS DE VENTANA R1.6")

        print(
            "Fecha Desde:",
            fecha_desde
        )

        print(
            "Hora Desde:",
            hora_desde
        )

        print(
            "Fecha Hasta:",
            fecha_hasta
        )

        print(
            "Hora Hasta:",
            hora_hasta
        )

        print("=" * 80)

        # =====================================================
        # VALIDAR
        # =====================================================

        if not all(
            (
                fecha_desde,
                fecha_hasta,
                hora_desde,
                hora_hasta,
            )
        ):

            raise ValueError(
                "El R1.6 no contiene una ventana "
                "temporal completa "
                "(Fecha Desde, Fecha Hasta, "
                "Hora Desde, Hora Hasta)."
            )

        # =====================================================
        # CONVERTIR FECHAS
        # =====================================================

        try:

            fecha_desde = fecha_desde.replace("/", "-")
            fecha_hasta = fecha_hasta.replace("/", "-")

            f_desde = datetime.strptime(
                fecha_desde,
                "%d-%m-%Y"
            ).date()

            f_hasta = datetime.strptime(
                fecha_hasta,
                "%d-%m-%Y"
            ).date()

            h_desde = datetime.strptime(
                hora_desde,
                "%H:%M"
            ).time()

            h_hasta = datetime.strptime(
                hora_hasta,
                "%H:%M"
            ).time()

        except ValueError as e:

            raise ValueError(
                "No se pudo interpretar la ventana "
                "temporal del R1.6: "
                f"{fecha_desde} {hora_desde} -> "
                f"{fecha_hasta} {hora_hasta}"
            ) from e

        # =====================================================
        # CREAR VENTANA DEFINITIVA
        # =====================================================

        self.ventana_desde = datetime.combine(
            f_desde,
            h_desde
        )

        self.ventana_hasta = datetime.combine(
            f_hasta,
            h_hasta
        )

        # =====================================================
        # VALIDAR ORDEN
        # =====================================================

        if self.ventana_hasta < self.ventana_desde:

            raise ValueError(
                "La ventana temporal del R1.6 "
                "es invÃ¡lida: "
                "Fecha/Hora Hasta es anterior "
                "a Fecha/Hora Desde."
            )

        print("VENTANA R1.6:")

        print(
            "  DESDE:",
            self.ventana_desde
        )

        print(
            "  HASTA:",
            self.ventana_hasta
        )

    # =====================================================
    # LEER CSV
    # =====================================================

    def leer_csv(
        self,
        archivo,
        unidad
    ):

        debe_cerrar = False

        # -------------------------------------------------
        # Normalizar entrada
        # -------------------------------------------------

        if hasattr(archivo, "read"):

            archivo_abierto = archivo

        else:

            archivo_abierto = open(
                archivo,
                "rb"
            )

            debe_cerrar = True

        self.archivo = Path(
            archivo_abierto.name
        ).name

        # -------------------------------------------------
        # Identidad por contenido
        # -------------------------------------------------

        archivo_abierto.seek(0)

        contenido = archivo_abierto.read()

        if isinstance(contenido, str):

            contenido = contenido.encode(
                CSV_ENCODING,
                errors="replace"
            )

        self.carga_hash = hashlib.sha256(
            contenido
        ).hexdigest()

        archivo_abierto.seek(0)

        self.unidad = unidad

        # -------------------------------------------------
        # Leer primero la ventana declarada por el R1.6
        # -------------------------------------------------

        self.leer_ventana_reporte(
            archivo_abierto
        )

        # -------------------------------------------------
        # Detectar encabezado y separador real del R1.6
        # -------------------------------------------------

        archivo_abierto.seek(0)

        contenido_csv = archivo_abierto.read()

        if isinstance(contenido_csv, bytes):

            contenido_texto = contenido_csv.decode(
                CSV_ENCODING,
                errors="replace"
            )

        else:

            contenido_texto = contenido_csv

        lineas_csv = contenido_texto.splitlines()

        separador_detectado = CSV_SEPARATOR
        fila_encabezado = CSV_HEADER_ROW

        for indice, linea in enumerate(lineas_csv):

            texto_linea = str(linea).strip()
            texto_upper = texto_linea.upper()

            if (
                texto_upper.startswith("SERVICIO")
                and "CODIGO BUS" in texto_upper
                and "PATENTE BUS" in texto_upper
            ):

                fila_encabezado = indice

                if "\t" in linea:

                    separador_detectado = "\t"

                elif ";" in linea:

                    separador_detectado = ";"

                elif "," in linea:

                    separador_detectado = ","

                break

        print("=" * 80)
        print("DETECCION FORMATO R1.6")
        print("=" * 80)
        print(
            "FILA ENCABEZADO:",
            fila_encabezado + 1
        )
        print(
            "SEPARADOR:",
            repr(separador_detectado)
        )
        print("=" * 80)

        # -------------------------------------------------
        # Volver al inicio para pandas
        # -------------------------------------------------

        archivo_abierto.seek(0)

        self.df = pd.read_csv(

            archivo_abierto,

            sep=separador_detectado,

            encoding=CSV_ENCODING,

            header=fila_encabezado,

            dtype=str,

        )

        self.df.columns = [

            str(col).strip()

            for col in self.df.columns

        ]

        print("=" * 80)

        print("COLUMNAS DEL CSV")

        print("=" * 80)

        for columna in self.df.columns:

            print(
                repr(columna)
            )

        print("=" * 80)

        print("PRIMERA FILA")

        print("=" * 80)

        print(
            self.df.iloc[0].to_dict()
        )

        print("=" * 80)

        if debe_cerrar:
            archivo_abierto.close()

        return self.df

    # =====================================================
    # VALIDAR COLUMNAS
    # =====================================================

    def validar_columnas(self):

        faltantes = [

            columna

            for columna
            in self.COLUMNAS_OBLIGATORIAS

            if columna not in self.df.columns

        ]

        if faltantes:

            raise Exception(

                "Faltan columnas:\n"

                + "\n".join(faltantes)

            )

    # =====================================================
    # LIMPIAR
    # =====================================================

    def limpiar_datos(self):

        self.df = self.df.fillna("")

        self.df = self.df.apply(

            lambda c:
                c.astype(str).str.strip()

        )

        return self.df

    # =====================================================
    # CONVERSIONES
    # =====================================================

    @staticmethod
    def texto(valor):

        if valor is None:

            return ""

        return str(valor).strip()

    @staticmethod
    def entero(valor):

        try:

            if valor == "":

                return None

            return int(
                float(valor)
            )

        except Exception:

            return None

    @staticmethod
    def decimal(valor):

        try:

            if valor == "":

                return None

            return float(

                str(valor)
                .replace(",", ".")

            )

        except Exception:

            return None

    @staticmethod
    def fecha_hora(valor):

        if valor in (
            "",
            None
        ):

            return None

        formatos = [

            "%d/%m/%Y %H:%M:%S",

            "%d/%m/%Y %H:%M",

            "%d-%m-%Y %H:%M:%S",

            "%d-%m-%Y %H:%M",

            "%Y-%m-%d %H:%M:%S",

            "%Y-%m-%d %H:%M",

        ]

        for formato in formatos:

            try:

                return datetime.strptime(

                    str(valor),

                    formato,

                )

            except Exception:

                pass

        return None

    # =====================================================
    # CONVERTIR FILA
    # =====================================================

    def convertir_fila(
        self,
        fila
    ):

        print("-" * 80)

        print(
            "INICIO RAW:",
            repr(
                fila.get(
                    "INICIO SERVICIO"
                )
            )
        )

        print(
            "FIN RAW   :",
            repr(
                fila.get(
                    "FIN SERVICIO"
                )
            )
        )

        print(
            "TIEMPO RAW:",
            repr(
                fila.get(
                    "TIEMPO DE VIAJE REAL"
                )
            )
        )

        print("-" * 80)

        inicio = self.fecha_hora(

            fila[
                "INICIO SERVICIO"
            ]

        )

        fin = self.fecha_hora(

            fila[
                "FIN SERVICIO"
            ]

        )

        print(
            "INICIO OK :",
            inicio
        )

        print(
            "FIN OK    :",
            fin
        )

        velocidad_min = self.decimal(

            fila[
                "VELOCIDAD (Km/Min)"
            ]

        )

        velocidad_hora = None

        if velocidad_min is not None:

            velocidad_hora = (
                velocidad_min * 60
            )

        fecha = None

        hora = None

        if inicio:

            fecha = inicio.date()

            hora = inicio.hour

        ruta = self.texto(

            fila[
                "RUTA"
            ]

        )

        interpretacion = (
            ParserRutas.interpretar(
                ruta
            )
        )

        codigo_ts = None

        sentido = None

        if interpretacion:

            codigo_ts = (
                interpretacion.get(
                    "codigo_ts"
                )
            )

            sentido = (
                interpretacion.get(
                    "sentido"
                )
            )

        servicio_cliente = None

        if codigo_ts and sentido:

            catalogo = Catalogo(
                self.db
            )

            resolucion = (
                catalogo.resolver(
                    codigo_ts,
                    sentido
                )
            )

            if resolucion:

                servicio_cliente = (
                    resolucion["servicio"]
                )

        return Expedicion(

            unidad=self.unidad,

            archivo_origen=self.archivo,

            servicio=(
                servicio_cliente
                if servicio_cliente
                else self.texto(
                    fila["SERVICIO"]
                )
            ),

            codigo_bus=self.texto(

                fila[
                    "CODIGO BUS"
                ]

            ),

            patente=self.texto(

                fila[
                    "PATENTE BUS"
                ]

            ),

            ruta=ruta,

            codigo_ts=codigo_ts,

            sentido=sentido,

            tipo_dia=self.texto(

                fila[
                    "TIPO DIA"
                ]

            ),

            franja_horaria=self.texto(

                fila[
                    "FRANJA HORARIA"
                ]

            ),

            inicio_servicio=inicio,

            fin_servicio=fin,

            fecha=fecha,

            hora=hora,

            zona_horaria=self.texto(

                fila[
                    "ZONA HORARIA"
                ]

            ),

            tiempo_viaje_real=self.texto(

                fila[
                    "TIEMPO DE VIAJE REAL"
                ]

            ),

            rango_esperado=self.texto(

                fila[
                    "RANGO ESPERADO DE VIAJE POR FRANJA HORARIA"
                ]

            ),

            cumplimiento=self.texto(

                fila[
                    "CUMPLIMIENTO"
                ]

            ),

            plazas=self.entero(

                fila[
                    "PLAZAS"
                ]

            ),

            km_inicio=self.decimal(

                fila[
                    "INICIO SERVICIO (Km)"
                ]

            ),

            km_fin=self.decimal(

                fila[
                    "FIN SERVICIO (Km)"
                ]

            ),

            velocidad_km_min=velocidad_min,

            velocidad_km_h=velocidad_hora,

            duracion_min=None,

            ruta_normalizada=self.texto(

                fila[
                    "RUTA"
                ]

            ),

            valido=True,

            observacion="",

            procesado=False,

        )

    # =====================================================
    # GUARDAR EN BASE DE DATOS
    # =====================================================

    def guardar_bd(self):

        expediciones = []

        self.registros_validos = 0

        self.registros_descartados = 0

        self.registros_fuera_rango = 0

        for _, fila in self.df.iterrows():

            try:

                # =================================================
                # FILTRO TEMPORAL DEL R1.6
                # =================================================
                #
                # IMPORTANTE:
                #
                # Se utiliza INICIO SERVICIO.
                #
                # Una expediciÃ³n que comenzÃ³ el dÃ­a anterior
                # pero terminÃ³ el dÃ­a del reporte NO entra.
                #
                # Ejemplo:
                #
                # 09-08 22:30 -> 10-08 00:05  âŒ
                #
                # 10-08 08:22 -> 10-08 09:03  âœ…
                #
                # =================================================

                inicio = self.fecha_hora(

                    fila[
                        "INICIO SERVICIO"
                    ]

                )

                if inicio is None:

                    raise ValueError(
                        "INICIO SERVICIO "
                        "no es una fecha/hora vÃ¡lida"
                    )

                if not (

                    self.ventana_desde
                    <= inicio
                    <= self.ventana_hasta

                ):

                    self.registros_descartados += 1

                    self.registros_fuera_rango += 1

                    continue

                # =================================================
                # CONVERSIÃ“N NORMAL
                # =================================================

                # =================================================
                # DESCARTAR EXPEDICIONES NO FINALIZADAS
                # FIN SERVICIO = A?O 1900
                # =================================================

                fin = self.fecha_hora(
                    fila[
                        "FIN SERVICIO"
                    ]
                )

                if (
                    fin is None
                    or fin.year == 1900
                ):
                    self.registros_descartados += 1
                    continue

                # =================================================
                # DESCARTAR VELOCIDAD CERO O INVALIDA
                # =================================================

                velocidad_min = self.decimal(
                    fila[
                        "VELOCIDAD (Km/Min)"
                    ]
                )

                if (
                    velocidad_min is None
                    or velocidad_min <= 0
                ):
                    self.registros_descartados += 1
                    continue

                expedicion = (
                    self.convertir_fila(
                        fila
                    )
                )

                expediciones.append(
                    expedicion
                )

                self.registros_validos += 1

            except Exception as e:

                self.registros_descartados += 1

                print("=" * 80)

                print(
                    "ERROR IMPORTANDO FILA"
                )

                print(
                    repr(e)
                )

                print(
                    fila.to_dict()
                )

                print("=" * 80)

        if expediciones:

            self.db.bulk_save_objects(
                expediciones
            )

        self.db.flush()

        print(
            f"EXPEDICIONES IMPORTADAS: "
            f"{self.registros_validos}"
        )

        print(
            f"DESCARTADAS: "
            f"{self.registros_descartados}"
        )

        print(
            f"FUERA DE RANGO: "
            f"{self.registros_fuera_rango}"
        )

    # =====================================================
    # HISTORIAL
    # =====================================================

    def registrar_historial(self):

        print(
            ">>> REGISTRANDO HISTORIAL R1.6 NUEVO <<<"
        )

        historial = HistorialImportacion(

            unidad=self.unidad,

            empresa="ALFA / OMEGA",

            archivo=self.archivo,

            tipo_archivo="R1.6",

            version="1.0",

            registros=len(self.df),

            registros_validos=self.registros_validos,

            registros_descartados=self.registros_descartados,

            carga_hash=self.carga_hash,

            observaciones=(

                "ImportaciÃ³n R1.6 | "

                f"Ventana: "
                f"{self.ventana_desde} -> "
                f"{self.ventana_hasta} | "

                f"Fuera de rango: "
                f"{self.registros_fuera_rango}"

            )

        )

        self.db.add(
            historial
        )

        self.db.flush()

    # =====================================================
    # IMPORTACIÃ“N COMPLETA
    # =====================================================

    def importar(
        self,
        archivo,
        unidad
    ):

        try:

            # -------------------------------------------------
            # Reiniciar contadores
            # -------------------------------------------------

            self.registros_validos = 0

            self.registros_descartados = 0

            self.registros_fuera_rango = 0

            # -------------------------------------------------
            # Leer CSV
            # -------------------------------------------------

            self.leer_csv(

                archivo,

                unidad

            )

            # -------------------------------------------------
            # Validar estructura
            # -------------------------------------------------

            # -------------------------------------------------
            # EVITAR REPROCESAR EL MISMO R1.6
            # -------------------------------------------------

            existente = (
                self.db.query(
                    HistorialImportacion
                )
                .filter(
                    HistorialImportacion.tipo_archivo == "R1.6",
                    HistorialImportacion.unidad == self.unidad,
                    HistorialImportacion.carga_hash == self.carga_hash,
                )
                .first()
            )

            if existente is not None:

                return {
                    "estado": "DUPLICADO",
                    "unidad": self.unidad,
                    "archivo": self.archivo,
                    "carga_hash": self.carga_hash,
                    "mensaje": (
                        "Este archivo R1.6 ya fue procesado. "
                        "No se insertaron datos nuevamente."
                    ),
                }

            self.validar_columnas()

            # -------------------------------------------------
            # Limpiar datos
            # -------------------------------------------------

            self.limpiar_datos()

            print("=" * 80)

            print(
                "TOTAL DE FILAS:",
                len(self.df)
            )

            print(
                self.df.head()
            )

            print("=" * 80)

            # -------------------------------------------------
            # Eliminar expediciones anteriores
            # -------------------------------------------------

            self.db.query(
                Expedicion
            ).filter(
                Expedicion.unidad == self.unidad
            ).delete(
                synchronize_session=False
            )

            # IMPORTANTE:
            # No hacer commit aqui.
            # El borrado y la carga nueva deben quedar
            # dentro de la misma transaccion.

            # -------------------------------------------------
            # Guardar nuevas expediciones
            # -------------------------------------------------

            self.guardar_bd()

            # -------------------------------------------------
            # Registrar historial
            # -------------------------------------------------

            self.registrar_historial()

            return {

                "estado": "OK",

                "unidad": self.unidad,

                "archivo": self.archivo,

                "registros": len(
                    self.df
                ),

                "registros_importados":
                    self.registros_validos,

                "registros_descartados":
                    self.registros_descartados,

                "registros_fuera_rango":
                    self.registros_fuera_rango,

                "ventana_desde": (

                    self.ventana_desde.isoformat()

                    if self.ventana_desde

                    else None

                ),

                "ventana_hasta": (

                    self.ventana_hasta.isoformat()

                    if self.ventana_hasta

                    else None

                ),

            }

        except Exception as e:

            import traceback

            traceback.print_exc()

            self.db.rollback()

            raise
