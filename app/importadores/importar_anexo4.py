"""
=========================================================
SWAV
Importador Anexo 4
Versión 1.2
=========================================================
"""

from pathlib import Path
from datetime import time, datetime

import pandas as pd

from sqlalchemy.orm import Session

from app.models import HistorialImportacion
from app.models import Periodo

from app.utils.unidades import obtener_unidad_empresa


class ImportadorAnexo4:

    def __init__(self, db: Session):

        self.db = db

    # =====================================================
    # IMPORTAR
    # =====================================================

    def importar(
        self,
        archivo,
        unidad_objetivo=None
    ):

        print("=" * 80)
        print("IMPORTANDO ANEXO 4")
        print("=" * 80)

        archivo = Path(archivo)

        if not archivo.exists():

            raise FileNotFoundError(
                f"No existe el archivo:\n{archivo}"
            )

        print(
            f"Archivo : {archivo.name}"
        )

        # =================================================
        # LEER EXCEL
        # =================================================

        df = pd.read_excel(

            archivo,

            sheet_name="Tabla Horaria",

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
        # IDENTIFICAR UNIDADES
        # =================================================

        unidades_archivo = set()

        for valor in df[
            "UNIDAD DE SERVICIO"
        ].dropna():

            unidad, empresa = (
                obtener_unidad_empresa(
                    valor
                )
            )

            if unidad not in {
                "U8",
                "U9"
            }:

                raise Exception(
                    f"Unidad no soportada en Anexo 4: {valor}"
                )

            unidades_archivo.add(
                unidad
            )

        if not unidades_archivo:

            raise Exception(
                "El Anexo 4 no contiene ninguna unidad válida."
            )

        if unidad_objetivo is not None:

            unidad_objetivo = (
                str(unidad_objetivo)
                .strip()
                .upper()
            )

            if unidad_objetivo not in {
                "U8",
                "U9"
            }:

                raise Exception(
                    "Unidad objetivo no valida para "
                    "Anexo 4: "
                    + unidad_objetivo
                )

            if (
                unidad_objetivo
                not in unidades_archivo
            ):

                raise Exception(
                    "El archivo Anexo 4 no contiene "
                    "la unidad "
                    + unidad_objetivo
                    + "."
                )

            # IMPORTANTE:
            # Desde este punto el importador solamente
            # puede borrar, procesar y registrar
            # la unidad elegida por el usuario.
            unidades_archivo = {
                unidad_objetivo
            }

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
        # PROCESAMIENTO
        # =================================================

        try:

            # =================================================
            # IMPORTANTE:
            # SOLO ELIMINAR LAS UNIDADES DEL ARCHIVO
            # =================================================

            self.db.query(
                Periodo
            ).filter(

                Periodo.unidad.in_(
                    unidades_archivo
                )

            ).delete(

                synchronize_session=False

            )

            self.db.flush()

            registros = 0

            duplicados = set()

            # =================================================
            # CONSOLIDACION ANEXO 4
            # Una fila por clave, conservando MAYOR DURACION
            # =================================================

            seleccionados = {}

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

                    escenario = (
                        self.limpiar_texto(
                            fila[
                                "ESCENARIO"
                            ]
                        )
                    )

                    codigo_ts = (
                        self.limpiar_texto(
                            fila[
                                "CODIGO TS SERVICIO"
                            ]
                        )
                    )

                    sentido = (
                        self.limpiar_texto(
                            fila[
                                "SENTIDO"
                            ]
                        )
                    )

                    tipo_dia = (
                        self.limpiar_texto(
                            fila[
                                "TIPO_DIA"
                            ]
                        )
                    )

                    tipo_evento = (
                        self.limpiar_texto(
                            fila[
                                "TIPO_EVENTO"
                            ]
                        )
                    )

                    # -----------------------------------------
                    # HORAS
                    # -----------------------------------------

                    hora_inicio = (
                        self.convertir_hora(
                            fila[
                                "HORA_INICIO"
                            ]
                        )
                    )

                    periodo_inicio = (
                        self.convertir_hora(
                            fila[
                                "PERIODO_INICIO"
                            ]
                        )
                    )

                    hora_fin = (
                        self.convertir_hora(
                            fila[
                                "HORA_FIN"
                            ]
                        )
                    )

                    periodo_fin = (
                        self.convertir_hora(
                            fila[
                                "PERIODO_FIN"
                            ]
                        )
                    )

                    # -----------------------------------------
                    # DURACIÓN
                    # -----------------------------------------

                    duracion = (
                        self.convertir_duracion(
                            fila[
                                "DURACION"
                            ]
                        )
                    )

                    # -----------------------------------------
                    # CLAVE DUPLICADO
                    # -----------------------------------------

                    clave = (

                        unidad,

                        codigo_ts,

                        sentido,

                        tipo_dia,

                        periodo_inicio,

                    )

                    # -----------------------------------------
                    # CONSOLIDAR DUPLICADOS
                    # REGLA OFICIAL:
                    # conservar MAYOR DURACION por clave
                    # -----------------------------------------

                    actual = seleccionados.get(
                        clave
                    )

                    if (
                        actual is None
                        or
                        duracion > actual["duracion"]
                    ):

                        seleccionados[
                            clave
                        ] = {

                            "unidad": unidad,

                            "empresa": empresa,

                            "escenario": escenario,

                            "codigo_ts": codigo_ts,

                            "sentido": sentido,

                            "tipo_dia": tipo_dia,

                            "tipo_evento": tipo_evento,

                            "hora_inicio": hora_inicio,

                            "periodo_inicio": periodo_inicio,

                            "hora_fin": hora_fin,

                            "periodo_fin": periodo_fin,

                            "duracion": duracion,

                        }

                    continue

                except Exception as e:

                    print(
                        f"Fila {indice + 8}: {e}"
                    )

            # =================================================
            # INSERTAR PERIODOS CONSOLIDADOS
            # =================================================

            for dato in seleccionados.values():

                nuevo = Periodo(

                    unidad=dato["unidad"],

                    empresa=dato["empresa"],

                    escenario=dato["escenario"],

                    codigo_ts=dato["codigo_ts"],

                    sentido=dato["sentido"],

                    tipo_dia=dato["tipo_dia"],

                    tipo_evento=dato["tipo_evento"],

                    hora_inicio=dato["hora_inicio"],

                    periodo_inicio=dato[
                        "periodo_inicio"
                    ],

                    hora_fin=dato["hora_fin"],

                    periodo_fin=dato[
                        "periodo_fin"
                    ],

                    duracion=dato["duracion"],

                )

                self.db.add(
                    nuevo
                )

                validos_por_unidad[
                    dato["unidad"]
                ] += 1

                registros += 1

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

                    tipo_archivo="ANEXO 4",

                    version="1.2",

                    registros=total,

                    registros_validos=validos,

                    registros_descartados=descartados,

                    observaciones=(
                        "Importación correcta"
                    )

                )

                self.db.add(
                    historial
                )

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
        print("ANEXO 4 IMPORTADO")
        print("=" * 80)

        print(
            f"Archivo              : {archivo.name}"
        )

        print(
            f"Registros Excel      : {len(df)}"
        )

        print(
            f"Períodos Importados  : {registros}"
        )

        print(
            "Unidades procesadas  :",
            ", ".join(
                sorted(
                    unidades_archivo
                )
            )
        )

        print("=" * 80)

        return registros

    # =====================================================
    # VALIDAR COLUMNAS
    # =====================================================

    def validar_columnas(self, df):

        columnas_requeridas = {

            "UNIDAD DE SERVICIO",

            "ESCENARIO",

            "CODIGO TS SERVICIO",

            "SENTIDO",

            "TIPO_DIA",

            "TIPO_EVENTO",

            "HORA_INICIO",

            "PERIODO_INICIO",

            "HORA_FIN",

            "PERIODO_FIN",

            "DURACION",

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
    # CONVERTIR HORA
    # =====================================================

    def convertir_hora(self, valor):

        if pd.isna(valor):

            return ""

        if isinstance(
            valor,
            datetime
        ):

            return valor.strftime(
                "%H:%M:%S"
            )

        if isinstance(
            valor,
            time
        ):

            return valor.strftime(
                "%H:%M:%S"
            )

        texto = str(
            valor
        ).strip()

        if texto == "NaT":

            return ""

        return texto

    # =====================================================
    # CONVERTIR DURACIÓN
    # =====================================================

    def convertir_duracion(self, valor):

        if pd.isna(valor):

            return 0.0

        if isinstance(
            valor,
            datetime
        ):

            return float(

                valor.hour * 60

                + valor.minute

                + valor.second / 60

            )

        if isinstance(
            valor,
            time
        ):

            return float(

                valor.hour * 60

                + valor.minute

                + valor.second / 60

            )

        if isinstance(
            valor,
            (int, float)
        ):

            return float(
                valor
            )

        texto = str(
            valor
        ).strip()

        if ":" in texto:

            partes = texto.split(":")

            if len(partes) >= 2:

                horas = int(
                    partes[0]
                )

                minutos = int(
                    partes[1]
                )

                return float(
                    horas * 60
                    + minutos
                )

        try:

            return float(
                texto
            )

        except Exception:

            return 0.0