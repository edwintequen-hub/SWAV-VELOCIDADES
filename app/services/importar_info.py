"""
=========================================================
SWAV
Importador Catálogo INFO
=========================================================
"""

from pathlib import Path

import pandas as pd

from sqlalchemy.orm import Session

from app.models import HistorialImportacion
from app.models import Servicio
from app.utils.unidades import obtener_unidad_empresa


class ImportadorINFO:

    def __init__(self, db: Session):

        self.db = db

    # =====================================================
    # IMPORTAR
    # =====================================================

    def importar(self, archivo):

        print("=" * 80)
        print("IMPORTANDO CATÁLOGO INFO")
        print("=" * 80)

        
        archivo = Path(archivo)

        if not archivo.exists():

            raise FileNotFoundError(

                f"No existe el archivo: {archivo}"

            )

        print(f"Archivo : {archivo.name}")

        df = pd.read_excel(archivo)

        print(f"Registros encontrados : {len(df)}")

        # Normalizar encabezados
        df.columns = [

            str(c).strip().upper()

            for c in df.columns

        ]

        # Validar columnas
        self.validar_columnas(df)

        # Limpiar catálogo anterior
        self.db.query(Servicio).delete()

        self.db.commit()

        registros = 0

        duplicados = set()

        for indice, fila in df.iterrows():

            try:

                unidad, empresa = obtener_unidad_empresa(
                    fila["UNIDAD"]
                )

            except ValueError as e:

                raise Exception(

                    f"Error en la fila Excel {indice + 2}: {e}"

                )

            servicio = self.limpiar_texto(fila["SERVICIO"])

            terminal = self.limpiar_texto(fila["TERMINAL"])

            tipo_dia = self.limpiar_texto(fila["TIPO DE DIA"])

            codigo_ts = self.limpiar_texto(
                fila["CODIGO TS SERVICIO"]
            )

            ruta_ida = self.limpiar_texto(
                fila["RUTA IDA"]
            )

            ruta_regreso = self.limpiar_texto(
                fila["RUTA REGRESO"]
            )

            clave = (

                unidad,

                servicio,

                terminal,

                tipo_dia,

                codigo_ts,

            )

            if clave in duplicados:

                continue

            duplicados.add(clave)

            nuevo = Servicio(

                unidad=unidad,

                empresa=empresa,

                servicio=servicio,

                terminal=terminal,

                tipo_dia=tipo_dia,

                codigo_ts=codigo_ts,

                ruta_ida=ruta_ida,

                ruta_regreso=ruta_regreso,

            )

            self.db.add(nuevo)

            registros += 1

        self.db.commit()

        historial = HistorialImportacion(

            unidad="TODAS",

            empresa="ALFA / OMEGA",

            archivo=archivo.name,

            tipo_archivo="INFO",

            version="1.0",

            registros=len(df),

            registros_validos=registros,

            registros_descartados=len(df) - registros,

            observaciones="Importación correcta"

        )

        self.db.add(historial)

        self.db.commit()

        print("=" * 80)
        print("CATÁLOGO INFO IMPORTADO")
        print("=" * 80)
        print(f"Archivo              : {archivo.name}")
        print(f"Registros Excel      : {len(df)}")
        print(f"Servicios Importados : {registros}")
        print(f"Duplicados           : {len(df) - registros}")
        print("=" * 80)

        return registros

    # =====================================================
    # VALIDAR COLUMNAS
    # =====================================================

    def validar_columnas(self, df):

        columnas_requeridas = {

            "UNIDAD",

            "SERVICIO",

            "TERMINAL",

            "TIPO DE DIA",

            "CODIGO TS SERVICIO",

            "RUTA IDA",

            "RUTA REGRESO",

        }

        columnas_excel = set(df.columns)

        faltantes = columnas_requeridas - columnas_excel

        if faltantes:

            raise Exception(

                "Faltan columnas obligatorias:\n\n"

                + "\n".join(sorted(faltantes))

            )

        print("Columnas validadas correctamente.")

    # =====================================================
    # NORMALIZAR TEXTO
    # =====================================================

    def limpiar_texto(self, valor):

        if pd.isna(valor):
            return ""

        return str(valor).strip().upper()


    