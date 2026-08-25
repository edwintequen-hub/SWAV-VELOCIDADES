"""
=========================================================
SWAV
Preparador R1.6
Versión 1.0
=========================================================
"""

from pathlib import Path
from datetime import datetime

import pandas as pd

from sqlalchemy.orm import Session

from app.models import Expedicion
from app.models import HistorialImportacion
from app.utils.unidades import obtener_unidad_empresa


class Preparador:

    def __init__(self, db: Session):

        self.db = db


    def preparar_expedicion(self, fila, archivo):

        unidad, empresa = obtener_unidad_empresa("U8")

        servicio = self.limpiar_texto(fila["SERVICIO"])
        codigo_bus = self.limpiar_texto(fila["CODIGO BUS"])
        patente = self.limpiar_texto(fila["PATENTE BUS"])
        ruta = self.limpiar_texto(fila["RUTA"])
        tipo_dia = self.limpiar_texto(fila["TIPO DIA"])
        franja = self.limpiar_texto(fila["FRANJA HORARIA"])

        inicio = self.convertir_fecha(fila["INICIO SERVICIO"])
        fin = self.convertir_fecha(fila["FIN SERVICIO"])

        fecha = inicio.date() if inicio else None
        hora = inicio.hour * 60 + inicio.minute if inicio else 0

        zona = self.limpiar_texto(fila["ZONA HORARIA"])
        tiempo = self.limpiar_texto(fila["TIEMPO DE VIAJE REAL"])
        rango = self.limpiar_texto(
            fila["RANGO ESPERADO DE VIAJE POR FRANJA HORARIA"]
        )

        cumplimiento = self.limpiar_texto(fila["CUMPLIMIENTO"])

        plazas = self.convertir_entero(fila["PLAZAS"])

        km_inicio = self.convertir_float(
            fila["INICIO SERVICIO (KM)"]
        )

        km_fin = self.convertir_float(
            fila["FIN SERVICIO (KM)"]
        )

        velocidad = self.convertir_float(
            fila["VELOCIDAD (KM/MIN)"]
        )

        if velocidad <= 0:

            expedicion.valido = False

            expedicion.observacion = "Velocidad igual a 0"

            

        return Expedicion(

            archivo_origen=archivo.name,

            unidad=unidad,
            empresa=empresa,

            servicio=servicio,

            codigo_bus=codigo_bus,

            patente=patente,

            ruta=ruta,

            tipo_dia=tipo_dia,

            franja_horaria=franja,

            inicio_servicio=inicio,

            fin_servicio=fin,

            fecha=fecha,

            hora=hora,

            zona_horaria=zona,

            tiempo_viaje_real=tiempo,

            rango_esperado=rango,

            cumplimiento=cumplimiento,

            plazas=plazas,

            km_inicio=km_inicio,

            km_fin=km_fin,

            velocidad_km_min=velocidad,

            valido=True,

            procesado=False
        )

    # =====================================================
    # IMPORTAR R1.6
    # =====================================================

    def importar(self, archivo):

        print("=" * 80)
        print("IMPORTANDO R1.6")
        print("=" * 80)

        archivo = Path(archivo)

        if not archivo.exists():

            raise FileNotFoundError(
                f"No existe el archivo:\n{archivo}"
            )

        print(f"Archivo : {archivo.name}")

        df = pd.read_csv(

            archivo,

            header=12,

            sep=None,

            engine="python",

            encoding="utf-8"

        )

        print(f"Registros encontrados : {len(df)}")

        df.columns = [

            str(col).strip().upper()

            for col in df.columns

        ]

        self.validar_columnas(df)

        self.db.query(Expedicion).delete()

        self.db.commit()

        registros = 0

        for indice, fila in df.iterrows():

            try:

                nuevo = self.preparar_expedicion(
                    fila,
                    archivo
                )

                if nuevo is None:
                    continue

                self.db.add(nuevo)

                registros += 1

            except Exception as e:

                print(f"Fila {indice+13}: {e}")

            
        self.db.commit()

        historial = HistorialImportacion(

            unidad="TODAS",

            empresa="ALFA / OMEGA",

            archivo=archivo.name,

            tipo_archivo="R1.6",

            version="1.0",

            registros=len(df),

            registros_validos=registros,

            registros_descartados=len(df) - registros,

            observaciones="Importación correcta"

        )

        self.db.add(historial)

        self.db.commit()

        print("=" * 80)
        print("R1.6 IMPORTADO")
        print("=" * 80)
        print(f"Archivo               : {archivo.name}")
        print(f"Registros CSV         : {len(df)}")
        print(f"Expediciones          : {registros}")
        print("=" * 80)

        return registros

    # =====================================================
    # VALIDAR COLUMNAS
    # =====================================================

    def validar_columnas(self, df):

        columnas_requeridas = {

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

            "INICIO SERVICIO (KM)",

            "FIN SERVICIO (KM)",

            "VELOCIDAD (KM/MIN)"

        }

        faltantes = columnas_requeridas - set(df.columns)

        if faltantes:

            raise Exception(

                "Faltan columnas:\n\n"

                + "\n".join(sorted(faltantes))

            )

        print("Columnas validadas correctamente.")

    # =====================================================
    # LIMPIAR TEXTO
    # =====================================================

    def limpiar_texto(self, valor):

        if pd.isna(valor):

            return ""

        return str(valor).strip().upper()

    # =====================================================
    # CONVERTIR FECHA
    # =====================================================

    def convertir_fecha(self, valor):

        if pd.isna(valor):

            return None

        texto = str(valor).strip()

        formatos = (

            "%d/%m/%Y %H:%M:%S",

            "%d-%m-%Y %H:%M:%S",

            "%Y-%m-%d %H:%M:%S",

        )

        for formato in formatos:

            try:

                return datetime.strptime(texto, formato)

            except Exception:

                pass

        return None

    # =====================================================
    # CONVERTIR FLOAT
    # =====================================================

    def convertir_float(self, valor):

        if pd.isna(valor):

            return 0.0

        texto = str(valor).strip()

        texto = texto.replace(".", "")

        texto = texto.replace(",", ".")

        try:

            return float(texto)

        except Exception:

            return 0.0

    # =====================================================
    # CONVERTIR ENTERO
    # =====================================================

    def convertir_entero(self, valor):

        if pd.isna(valor):

            return 0

        try:

            return int(float(valor))

        except Exception:

            return 0