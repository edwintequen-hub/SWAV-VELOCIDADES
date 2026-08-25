"""
=========================================================
SWAV
Importador Anexo 3
Versión 1.2
=========================================================
"""

from pathlib import Path
from datetime import time, datetime

import pandas as pd

from sqlalchemy.orm import Session

from app.models import HistorialImportacion
from app.models import Velocidad

from app.utils.unidades import obtener_unidad_empresa


class ImportadorAnexo3:

    def __init__(self, db: Session):

        self.db = db

    # =====================================================
    # IMPORTAR
    # =====================================================

    def importar(self, archivo):

        print("=" * 80)
        print("IMPORTANDO ANEXO 3")
        print("=" * 80)

        archivo = Path(archivo)

        if not archivo.exists():

            raise FileNotFoundError(
                f"No existe el archivo:\n{archivo}"
            )

        print(f"Archivo : {archivo.name}")

        # =================================================
        # LEER EXCEL
        # =================================================

        df = pd.read_excel(
            archivo,
            sheet_name=0,
            header=6
        )

        print(
            f"Registros encontrados : {len(df)}"
        )

        # =================================================
        # NORMALIZAR COLUMNAS
        # =================================================

        df.columns = [
            str(col).strip().upper()
            for col in df.columns
        ]

        # =================================================
        # VALIDAR
        # =================================================

        self.validar_columnas(df)

        # =================================================
        # IDENTIFICAR UNIDADES DEL ARCHIVO
        # =================================================

        unidades_archivo = set()

        for valor in df[
            "UNIDAD DE SERVICIO"
        ].dropna():

            unidad, empresa = (
                obtener_unidad_empresa(valor)
            )

            if unidad not in {"U8", "U9"}:

                raise Exception(
                    f"Unidad no soportada en Anexo 3: {valor}"
                )

            unidades_archivo.add(unidad)

        if not unidades_archivo:

            raise Exception(
                "El Anexo 3 no contiene ninguna unidad válida."
            )

        print(
            "Unidades del archivo:",
            sorted(unidades_archivo)
        )

        # =================================================
        # ESTADÍSTICAS POR UNIDAD
        # =================================================

        totales_por_unidad = {
            unidad: 0
            for unidad in unidades_archivo
        }

        validos_por_unidad = {
            unidad: 0
            for unidad in unidades_archivo
        }

        # =================================================
        # ESTADÍSTICAS IP / IE / --
        # =================================================

        indicadores = {
            "IP": 0,
            "IE": 0,
            "--": 0,
            "VACIO": 0,
        }

        # =================================================
        # PROCESAMIENTO
        # =================================================

        try:

            # =================================================
            # IMPORTANTE:
            # SOLO ELIMINAR LAS UNIDADES PRESENTES
            # EN ESTE ARCHIVO
            # =================================================

            self.db.query(Velocidad).filter(
                Velocidad.unidad.in_(
                    unidades_archivo
                )
            ).delete(
                synchronize_session=False
            )

            self.db.flush()

            registros = 0

            duplicados = set()

            # =================================================
            # RECORRER EXCEL
            # =================================================

            for indice, fila in df.iterrows():

                try:

                    # -----------------------------------------
                    # UNIDAD
                    # -----------------------------------------

                    unidad, empresa = (
                        obtener_unidad_empresa(
                            fila[
                                "UNIDAD DE SERVICIO"
                            ]
                        )
                    )

                    if unidad not in unidades_archivo:

                        continue

                    totales_por_unidad[
                        unidad
                    ] += 1

                    # -----------------------------------------
                    # DATOS
                    # -----------------------------------------

                    codigo_ts = (
                        self.limpiar_texto(
                            fila[
                                "CODIGO TS SERVICIO"
                            ]
                        )
                    )

                    sentido = (
                        self.limpiar_texto(
                            fila["SENTIDO"]
                        )
                    )

                    tipo_dia = (
                        self.limpiar_texto(
                            fila["TIPO DIA"]
                        )
                    )

                    # -----------------------------------------
                    # PERIODO
                    # -----------------------------------------

                    periodo = (
                        self.convertir_periodo(
                            fila["MH"]
                        )
                    )

                    print(
                        "MH =",
                        fila["MH"],
                        " -> PERIODO =",
                        periodo
                    )

                    # -----------------------------------------
                    # VELOCIDAD
                    # -----------------------------------------

                    velocidad = (
                        self.convertir_float(
                            fila[
                                "VELOCIDAD (KM/HRA)"
                            ]
                        )
                    )

                    # -----------------------------------------
                    # INDICADOR IP / IE
                    #
                    # Columna N del Anexo 3:
                    # INDICADOR TIEMPO DE ESPERA
                    # -----------------------------------------

                    indicador = (
                        self.normalizar_indicador(
                            fila[
                                "INDICADOR TIEMPO DE ESPERA"
                            ]
                        )
                    )

                    indicadores[
                        indicador
                    ] += 1

                    # -----------------------------------------
                    # CLAVE DUPLICADO
                    # -----------------------------------------

                    clave = (
                        unidad,
                        codigo_ts,
                        sentido,
                        tipo_dia,
                        periodo,
                    )

                    if clave in duplicados:

                        continue

                    duplicados.add(clave)

                    # -----------------------------------------
                    # CREAR REGISTRO
                    # -----------------------------------------

                    nuevo = Velocidad(

                        unidad=unidad,

                        empresa=empresa,

                        codigo_ts=codigo_ts,

                        sentido=sentido,

                        tipo_dia=tipo_dia,

                        periodo=periodo,

                        velocidad=velocidad,

                        indicador_tiempo_espera=indicador,

                    )

                    self.db.add(nuevo)

                    validos_por_unidad[
                        unidad
                    ] += 1

                    registros += 1

                except Exception as e:

                    print(
                        f"Fila {indice + 8}: {e}"
                    )

            # =================================================
            # ASEGURAR INSERTS
            # =================================================

            self.db.flush()

            # =================================================
            # HISTORIAL POR UNIDAD
            # =================================================

            for unidad in sorted(
                unidades_archivo
            ):

                empresa = (
                    "ALFA"
                    if unidad == "U8"
                    else "OMEGA"
                )

                total = (
                    totales_por_unidad[
                        unidad
                    ]
                )

                validos = (
                    validos_por_unidad[
                        unidad
                    ]
                )

                descartados = (
                    total - validos
                )

                historial = HistorialImportacion(

                    unidad=unidad,

                    empresa=empresa,

                    archivo=archivo.name,

                    tipo_archivo="ANEXO 3",

                    version="1.2",

                    registros=total,

                    registros_validos=validos,

                    registros_descartados=descartados,

                    observaciones=(
                        "Importación correcta"
                    )

                )

                self.db.add(historial)

            # =================================================
            # COMMIT FINAL
            # =================================================

            self.db.commit()

        except Exception:

            self.db.rollback()

            raise

        # =================================================
        # RESULTADO
        # =================================================

        print("=" * 80)
        print("ANEXO 3 IMPORTADO")
        print("=" * 80)

        print(
            f"Archivo               : {archivo.name}"
        )

        print(
            f"Registros Excel       : {len(df)}"
        )

        print(
            f"Velocidades Importadas: {registros}"
        )

        print(
            "Unidades procesadas   :",
            ", ".join(
                sorted(unidades_archivo)
            )
        )

        print("-" * 80)
        print("INDICADOR TIEMPO DE ESPERA")
        print("-" * 80)

        print(
            f"IP                    : {indicadores['IP']}"
        )

        print(
            f"IE                    : {indicadores['IE']}"
        )

        print(
            f"--                    : {indicadores['--']}"
        )

        print(
            f"VACIO                 : {indicadores['VACIO']}"
        )

        print("=" * 80)

        return registros

    # =====================================================
    # VALIDAR COLUMNAS
    # =====================================================

    def validar_columnas(self, df):

        columnas_requeridas = {

            "UNIDAD DE SERVICIO",

            "CODIGO TS SERVICIO",

            "SENTIDO",

            "TIPO DIA",

            "MH",

            "VELOCIDAD (KM/HRA)",

            "INDICADOR TIEMPO DE ESPERA",

        }

        faltantes = (
            columnas_requeridas
            - set(df.columns)
        )

        if faltantes:

            raise Exception(

                "Faltan columnas:\n\n"

                + "\n".join(
                    sorted(faltantes)
                )

            )

        print(
            "Columnas validadas correctamente."
        )

    # =====================================================
    # LIMPIAR TEXTO
    # =====================================================

    def limpiar_texto(self, valor):

        if pd.isna(valor):

            return ""

        return str(
            valor
        ).strip().upper()

    # =====================================================
    # NORMALIZAR INDICADOR
    # =====================================================

    def normalizar_indicador(self, valor):

        if pd.isna(valor):

            return "VACIO"

        indicador = (
            str(valor)
            .strip()
            .upper()
        )

        if indicador == "IP":

            return "IP"

        if indicador == "IE":

            return "IE"

        if indicador == "--":

            return "--"

        if indicador == "":

            return "VACIO"

        # No convertir silenciosamente
        # valores desconocidos a IP o IE.

        print(
            f"Indicador no reconocido: {indicador}"
        )

        return indicador

    # =====================================================
    # CONVERTIR PERIODO
    # =====================================================

    def convertir_periodo(self, valor):

        if pd.isna(valor):

            return 0

        # Excel devuelve datetime

        if isinstance(
            valor,
            datetime
        ):

            return valor.hour + 1

        # Excel devuelve time

        if isinstance(
            valor,
            time
        ):

            return valor.hour + 1

        texto = str(
            valor
        ).strip()

        if ":" in texto:

            h = int(
                texto.split(":")[0]
            )

            return h + 1

        try:

            return int(
                float(texto)
            )

        except Exception:

            return 0

    # =====================================================
    # CONVERTIR FLOAT
    # =====================================================

    def convertir_float(self, valor):

        if pd.isna(valor):

            return 0.0

        try:

            return float(valor)

        except Exception:

            return 0.0