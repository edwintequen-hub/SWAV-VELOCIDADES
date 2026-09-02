"""
=========================================================
SWAV
SCHEDULER AUTOMATICO R1.6
=========================================================
"""

import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.database import SessionLocal
from app.models import ConfiguracionR16Automatica
from app.api.sinoptico import descargar_r16

from app.services.coordinador_operaciones import (
    coordinador_swav
)


ZONA_CHILE = ZoneInfo("America/Santiago")

_lock = threading.Lock()


def _ahora_chile():
    return datetime.now(ZONA_CHILE).replace(tzinfo=None)


def _obtener_configuracion(db):

    return (
        db.query(ConfiguracionR16Automatica)
        .order_by(ConfiguracionR16Automatica.id.asc())
        .first()
    )


def ejecutar_r16_automatico():

    if not _lock.acquire(
        blocking=False
    ):

        return {
            "estado": "OMITIDO",
            "mensaje":
                "Ya existe una ejecucion R1.6 en curso."
        }

    try:

        with coordinador_swav.operacion(
            "R1.6 AUTOMATICO",
            esperar=False
        ):

            db = SessionLocal()

            try:

                configuracion = (
                    _obtener_configuracion(
                        db
                    )
                )

                if configuracion is None:

                    return {
                        "estado":
                            "SIN_CONFIGURACION"
                    }

                if not configuracion.activo:

                    return {
                        "estado":
                            "DESACTIVADO"
                    }

                ahora = _ahora_chile()

                resultados = {}

                unidades = []

                if configuracion.actualizar_u8:
                    unidades.append("U8")

                if configuracion.actualizar_u9:
                    unidades.append("U9")

                for unidad in unidades:

                    try:

                        resultado = (
                            descargar_r16(
                                unidad=unidad,
                                db=db
                            )
                        )

                        resultados[unidad] = {
                            "ok": True,
                            "estado":
                                resultado.get(
                                    "estado"
                                ),
                            "mensaje":
                                resultado.get(
                                    "mensaje"
                                )
                        }

                    except Exception as exc:

                        db.rollback()

                        detalle = getattr(
                            exc,
                            "detail",
                            str(exc)
                        )

                        resultados[unidad] = {
                            "ok": False,
                            "error":
                                str(detalle)
                        }

                # Volvemos a consultar por seguridad
                # despues del procesamiento.

                configuracion = (
                    _obtener_configuracion(
                        db
                    )
                )

                intervalo = max(
                    5,
                    int(
                        configuracion
                        .intervalo_minutos
                        or 30
                    )
                )

                configuracion.ultima_ejecucion = (
                    ahora
                )

                configuracion.proxima_ejecucion = (
                    ahora
                    + timedelta(
                        minutes=intervalo
                    )
                )

                configuracion.ultima_respuesta = (
                    str(resultados)[:1000]
                )

                db.commit()

                return {
                    "estado": "OK",
                    "ultima_ejecucion":
                        configuracion
                        .ultima_ejecucion,
                    "proxima_ejecucion":
                        configuracion
                        .proxima_ejecucion,
                    "resultados":
                        resultados
                }

            except Exception:

                db.rollback()
                raise

            finally:

                db.close()

    finally:

        _lock.release()


def scheduler_r16_tick():

    db = SessionLocal()

    try:

        configuracion = _obtener_configuracion(db)

        if configuracion is None:
            return

        if not configuracion.activo:
            return

        ahora = _ahora_chile()

        if configuracion.proxima_ejecucion is None:

            intervalo = max(
                5,
                int(configuracion.intervalo_minutos or 30)
            )

            configuracion.proxima_ejecucion = (
                ahora
                + timedelta(minutes=intervalo)
            )

            db.commit()

            print(
                "[R16 AUTO] Primera ejecucion programada:",
                configuracion.proxima_ejecucion
            )

            return

        if ahora < configuracion.proxima_ejecucion:
            return

    finally:

        db.close()

    print(
        "[R16 AUTO] Iniciando ejecucion automatica:",
        _ahora_chile()
    )

    resultado = ejecutar_r16_automatico()

    print(
        "[R16 AUTO] Resultado:",
        resultado
    )
