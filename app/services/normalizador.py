"""
=========================================================
SWAV
Motor de Normalización R1.6
=========================================================
"""

from datetime import datetime

import re

from sqlalchemy.orm import Session

from app.models import Expedicion


class MotorNormalizacion:

    def __init__(self, db: Session):

        self.db = db

    # =====================================================
    # EXTRAER CODIGO TS
    # =====================================================

    def extraer_codigo_ts(self, ruta: str):

        if not ruta:

            return ""

        ruta = ruta.strip().upper()

        coincidencia = re.search(r"T(\d+)", ruta)

        if coincidencia:

            return coincidencia.group(1)

        return ""

    # =====================================================
    # OBTENER SENTIDO
    # =====================================================

    def obtener_sentido(self, ruta: str):

        if not ruta:

            return ""

        ruta = ruta.strip().upper()

        if ruta.endswith("I"):

            return "IDA"

        if ruta.endswith("R"):

            return "RETORNO"

        return ""

    # =====================================================
    # PROCESO COMPLETO
    # =====================================================

    def procesar(self):

        print("=" * 80)
        print("INICIANDO PREPARACIÓN DE EXPEDICIONES")
        print("=" * 80)

        expediciones = self.db.query(Expedicion).all()

        total = len(expediciones)

        print(f"EXPEDICIONES : {total}")

        for expedicion in expediciones:

            # Calcular duración
            expedicion.duracion_min = self.calcular_duracion(
                expedicion.inicio_servicio,
                expedicion.fin_servicio
            )

            # Normalizar ruta
            expedicion.ruta_normalizada = self.normalizar_ruta(
                expedicion.ruta
            )

            # Código TS
            expedicion.codigo_ts = self.extraer_codigo_ts(
                expedicion.ruta_normalizada
            )

            # Sentido
            expedicion.sentido = self.obtener_sentido(
                expedicion.ruta_normalizada
            )

            # Validar duración
            self.eliminar_expediciones_cortas(
                expedicion,
                20
            )

        self.db.commit()

        print("=" * 80)
        print("PREPARACIÓN FINALIZADA")
        print("=" * 80)

        return {

            "estado": "OK",

            "procesadas": total

        }

    # =====================================================
    # NORMALIZAR RUTA
    # =====================================================

    def normalizar_ruta(self, ruta: str):

        if not ruta:
            return ""

        ruta = ruta.strip().upper()

        # Si ya viene normalizada
        if ruta.endswith("00I") or ruta.endswith("00R"):

            return ruta

        equivalencias = {

            "T841 02I": "T841 00I",
            "T841 02R": "T841 00R",

            "T807 03I": "T807 00I",

            "T816 03I": "T816 00I",
            "T816 03R": "T816 00R",
            "T816 06I": "T816 00I",
            "T816 06R": "T816 00R",

            "T817 06I": "T817 00I",

            "T818 03I": "T818 00I",
            "T818 03R": "T818 00R",

            "T822 03I": "T822 00I",

            "T825 03I": "T825 00I",

            "T826 03I": "T826 00I",

            "T836 03I": "T836 00I",

            "T837 03I": "T837 00I",

        }

        return equivalencias.get(ruta, ruta)

    # =====================================================
    # CALCULAR DURACIÓN
    # =====================================================

    def calcular_duracion(self, inicio, fin):

        if inicio is None or fin is None:

            return None

        try:

            minutos = (

                (fin - inicio).total_seconds()

                / 60

            )

            return round(minutos, 2)

        except Exception:

            return None

    # =====================================================
    # CALCULAR HORA OPERACIONAL
    # =====================================================

    def calcular_hora_operacional(self, inicio):

        if inicio is None:

            return None

        try:

            return inicio.hour

        except Exception:

            return None

    # =====================================================
    # VALIDAR CUMPLIMIENTO
    # =====================================================

    def validar_cumplimiento(self, ruta, duracion):

        pass

    # =====================================================
    # ELIMINAR EXPEDICIONES CORTAS
    # =====================================================

    def eliminar_expediciones_cortas(
        self,
        expedicion,
        duracion_minima
    ):

        if expedicion.duracion_min is None:

            expedicion.valido = False

            expedicion.observacion = "Duración inválida"

            return

        if expedicion.duracion_min < duracion_minima:

            expedicion.valido = False

            expedicion.observacion = (
                f"Duración menor a "
                f"{duracion_minima} minutos"
            )

        else:

            expedicion.valido = True

            expedicion.observacion = ""