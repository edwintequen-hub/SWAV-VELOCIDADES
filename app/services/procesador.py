"""
=========================================================
SWAV
Procesador Principal
=========================================================
"""

from sqlalchemy.orm import Session
import time as time_module
from sqlalchemy import event

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
            _sql_preparador = {
                "total": 0,
                "configuracion": 0,
                "unidades": 0,
                "servicios": 0,
                "periodos": 0,
                "expediciones": 0,
                "otros": 0,
            }

            def _contar_sql_preparador(
                conn,
                cursor,
                statement,
                parameters,
                context,
                executemany,
            ):
                _sql_preparador["total"] += 1

                sql = " ".join(
                    str(statement).lower().split()
                )

                if "configuracion" in sql:
                    clave = "configuracion"
                elif "unidades" in sql:
                    clave = "unidades"
                elif "servicios" in sql:
                    clave = "servicios"
                elif "periodos" in sql:
                    clave = "periodos"
                elif "expediciones" in sql:
                    clave = "expediciones"
                else:
                    clave = "otros"

                _sql_preparador[clave] += 1

            _engine_preparador = self.db.get_bind()

            event.listen(
                _engine_preparador,
                "before_cursor_execute",
                _contar_sql_preparador,
            )

            print(
                f"[SWAV TRACE] {unidad} PREPARADOR INICIO",
                flush=True,
            )

            try:
                resultado_preparacion = (
                    preparador.procesar(
                        unidad=unidad
                    )
                )
            finally:
                event.remove(
                    _engine_preparador,
                    "before_cursor_execute",
                    _contar_sql_preparador,
                )

            print(
                f"[SWAV TRACE] {unidad} PREPARADOR FIN "
                f"{time_module.monotonic() - _t_preparador:.2f}s "
                f"SQL={_sql_preparador['total']} "
                f"CONFIG={_sql_preparador['configuracion']} "
                f"UNIDAD={_sql_preparador['unidades']} "
                f"SERVICIO={_sql_preparador['servicios']} "
                f"PERIODO={_sql_preparador['periodos']} "
                f"EXPEDICION={_sql_preparador['expediciones']} "
                f"OTROS={_sql_preparador['otros']}",
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

