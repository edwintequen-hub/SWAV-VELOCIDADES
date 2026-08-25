"""
==========================================================
SWAV - Sistema Web Análisis de Velocidades
Módulo: Explorador de archivos R1.6
Versión: 2.0
==========================================================
"""

from pathlib import Path
import pandas as pd


class ExploradorCSV:

    def __init__(self, ruta_archivo):

        self.ruta = Path(ruta_archivo)

        self.df = None

        self.fila_encabezado = None

        self.codificacion = None

        self.separador = None

    # ======================================================
    # Detectar codificación
    # ======================================================

    def detectar_codificacion(self):

        codificaciones = [
            "utf-8",
            "latin1",
            "cp1252",
        ]

        for cod in codificaciones:

            try:

                pd.read_csv(
                    self.ruta,
                    encoding=cod,
                    nrows=5,
                    header=None,
                )

                self.codificacion = cod

                return cod

            except Exception:
                pass

        raise Exception("No fue posible detectar la codificación.")

    # ======================================================
    # Detectar separador
    # ======================================================

    def detectar_separador(self):

        separadores = [
            ";",
            ",",
            "\t",
            "|",
        ]

        mejor = None

        mayor_columnas = 0

        for sep in separadores:

            try:

                df = pd.read_csv(
                    self.ruta,
                    encoding=self.codificacion,
                    sep=sep,
                    header=None,
                    nrows=20,
                )

                if len(df.columns) > mayor_columnas:

                    mayor_columnas = len(df.columns)

                    mejor = sep

            except Exception:
                pass

        if mejor is None:

            raise Exception("No fue posible detectar el separador.")

        self.separador = mejor

        return mejor

    # ======================================================
    # Leer archivo completo SIN encabezado
    # ======================================================

    def leer_archivo(self):

        self.df = pd.read_csv(

            self.ruta,

            encoding=self.codificacion,

            sep=self.separador,

            header=None,

            dtype=str,

        )

    # ======================================================
    # Buscar automáticamente el encabezado
    # ======================================================

    def buscar_encabezado(self):

        palabras = [

            "Servicio",

            "Ruta",

            "Patente",

            "Hora",

            "Bus",

            "Velocidad",

        ]

        for i, fila in self.df.iterrows():

            texto = " ".join(fila.fillna("").astype(str))

            coincidencias = 0

            for palabra in palabras:

                if palabra.lower() in texto.lower():

                    coincidencias += 1

            if coincidencias >= 2:

                self.fila_encabezado = i

                return i

        raise Exception("No fue posible encontrar el encabezado del archivo.")

    # ======================================================
    # Leer nuevamente usando el encabezado encontrado
    # ======================================================

    def cargar_datos(self):

        self.df = pd.read_csv(

            self.ruta,

            encoding=self.codificacion,

            sep=self.separador,

            header=self.fila_encabezado,

            dtype=str,

        )

    # ======================================================
    # Mostrar resumen
    # ======================================================

    def mostrar_resumen(self):

        print("=" * 60)

        print("SWAV - EXPLORADOR R1.6")

        print("=" * 60)

        print(f"Archivo       : {self.ruta.name}")

        print(f"Codificación  : {self.codificacion}")

        print(f"Separador     : {repr(self.separador)}")

        print(f"Encabezado    : Fila {self.fila_encabezado}")

        print(f"Filas         : {len(self.df):,}")

        print(f"Columnas      : {len(self.df.columns)}")

        print()

        print("COLUMNAS")

        print("-" * 60)

        for i, columna in enumerate(self.df.columns, start=1):

            print(f"{i:02d}. {columna}")

        print()

        print("TIPOS DE DATOS")

        print("-" * 60)

        print(self.df.dtypes)

        print()

        print("PRIMERAS 5 FILAS")

        print("-" * 60)

        print(self.df.head())

    # ======================================================
    # Ejecutar todo
    # ======================================================

    def ejecutar(self):

        self.detectar_codificacion()

        self.detectar_separador()

        self.leer_archivo()

        self.buscar_encabezado()

        self.cargar_datos()

        self.mostrar_resumen()

        return self.df