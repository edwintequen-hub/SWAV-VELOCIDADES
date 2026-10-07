"""
=========================================================
SWAV
Procesador Principal
=========================================================
"""

from sqlalchemy.orm import Session
import time as time_module

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

            _t_importador = time_module.monotonic()
            print(
                f"[SWAV TRACE] {unidad} IMPORTADOR INICIO",
                flush=True,
            )

            resultado_importacion = (
                importador.importar(
                    archivo=archivo,
                    unidad=unidad,
                )
            )

            print(
                f"[SWAV TRACE] {unidad} IMPORTADOR FIN "
                f"{time_module.monotonic() - _t_importador:.2f}s",
                flush=True,
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

            _t_preparador = time_module.monotonic()
            print(
                f"[SWAV TRACE] {unidad} PREPARADOR INICIO",
                flush=True,
            )

            resultado_preparacion = (
                preparador.procesar(
                    unidad=unidad
                )
            )

            print(
                f"[SWAV TRACE] {unidad} PREPARADOR FIN "
                f"{time_module.monotonic() - _t_preparador:.2f}s",
                flush=True,
            )

            # ---------------------------------------------
            # 3. COMPARACION Y REGISTRO
            # ---------------------------------------------

            motor = MotorComparacion(
                self.db
            )

            _t_motor = time_module.monotonic()
            print(
                f"[SWAV TRACE] {unidad} MOTOR INICIO",
                flush=True,
            )

            resultado_registro = (
                motor.procesar(
                    unidad=unidad
                )
            )

            print(
                f"[SWAV TRACE] {unidad} MOTOR FIN "
                f"{time_module.monotonic() - _t_motor:.2f}s",
                flush=True,
            )

            # ---------------------------------------------
            # 4. CONFIRMACION UNICA
            # ---------------------------------------------

            _t_commit = time_module.monotonic()
            print(
                f"[SWAV TRACE] {unidad} COMMIT INICIO",
                flush=True,
            )

            self.db.commit()

            print(
                f"[SWAV TRACE] {unidad} COMMIT FIN "
                f"{time_module.monotonic() - _t_commit:.2f}s",
                flush=True,
            )

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

