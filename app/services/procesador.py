"""
=========================================================
SWAV
Procesador Principal
=========================================================
"""

from sqlalchemy.orm import Session

from app.services.importador import ImportadorR16
from app.services.preparacion import PreparadorR16
from app.services.motor_comparacion import MotorComparacion


class ProcesadorSWAV:

    def __init__(self, db: Session):

        self.db = db

    # =====================================================
    # PROCESO COMPLETO
    # =====================================================

    def procesar(self, archivo, unidad):

        try:

            # ---------------------------------------------
            # 1. IMPORTAR
            # ---------------------------------------------

            importador = ImportadorR16(
                self.db
            )

            resultado_importacion = (
                importador.importar(
                    archivo=archivo,
                    unidad=unidad,
                )
            )

            if (
                resultado_importacion.get(
                    "estado"
                )
                != "OK"
            ):

                # DUPLICADO u otra respuesta
                # que no requiere modificar la BD.

                self.db.rollback()

                return resultado_importacion

            # ---------------------------------------------
            # 2. PREPARAR
            # ---------------------------------------------

            preparador = PreparadorR16(
                self.db
            )

            resultado_preparacion = (
                preparador.procesar(
                    unidad=unidad
                )
            )

            # ---------------------------------------------
            # 3. COMPARACION Y REGISTRO
            # ---------------------------------------------

            motor = MotorComparacion(
                self.db
            )

            resultado_registro = (
                motor.procesar(
                    unidad=unidad
                )
            )

            # ---------------------------------------------
            # 4. CONFIRMACION UNICA
            # ---------------------------------------------

            self.db.commit()

            return {

                "estado": "OK",

                "importacion":
                    resultado_importacion,

                "preparacion":
                    resultado_preparacion,

                "registro":
                    resultado_registro,
            }

        except Exception:

            self.db.rollback()

            raise

