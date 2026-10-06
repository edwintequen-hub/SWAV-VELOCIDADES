"""
Scheduler aislado R2.2 para FLOTA.

Reglas:
- Independiente del scheduler R1.6.
- Descarga U8 y U9.
- Intervalo inicial: 5 minutos.
- No modifica BD de flota.
- No interpreta taller ni velocidades.
- Mantiene estado en memoria para monitoreo.
"""

from datetime import datetime, timedelta
from threading import Lock

from app.database import SessionLocal
from app.models import CredencialSinoptico
from app.services.sinoptico_r22_service import (
    SinopticoR22Service,
)


INTERVALO_R22_MINUTOS = 5

_lock_r22 = Lock()

_estado_r22 = {
    "activo": True,
    "ejecutando": False,
    "intervalo_minutos": INTERVALO_R22_MINUTOS,
    "ultima_ejecucion": None,
    "proxima_ejecucion": None,
    "resultados": {},
    "ultimo_error": None,
}


def obtener_estado_r22():
    return {
        "activo": _estado_r22["activo"],
        "ejecutando": _estado_r22["ejecutando"],
        "intervalo_minutos":
            _estado_r22["intervalo_minutos"],
        "ultima_ejecucion":
            _estado_r22["ultima_ejecucion"],
        "proxima_ejecucion":
            _estado_r22["proxima_ejecucion"],
        "resultados":
            dict(_estado_r22["resultados"]),
        "ultimo_error":
            _estado_r22["ultimo_error"],
    }


def _obtener_credencial_activa(db):
    credencial = (
        db.query(CredencialSinoptico)
        .filter(
            CredencialSinoptico.activo.is_(True)
        )
        .order_by(
            CredencialSinoptico.id.desc()
        )
        .first()
    )

    if credencial is None:
        raise RuntimeError(
            "No existe credencial Sinoptico activa."
        )

    return credencial


def ejecutar_r22_ahora():
    if not _lock_r22.acquire(blocking=False):
        return {
            "ok": False,
            "estado": "EN_EJECUCION",
            "mensaje":
                "Ya existe una descarga R2.2 en curso.",
        }

    _estado_r22["ejecutando"] = True

    inicio = datetime.now()
    db = SessionLocal()

    try:
        credencial = _obtener_credencial_activa(db)

        usuario = getattr(
            credencial,
            "usuario",
            None,
        )

        password = (
            getattr(
                credencial,
                "password",
                None,
            )
            or
            getattr(
                credencial,
                "clave",
                None,
            )
        )

        if not usuario:
            raise RuntimeError(
                "Credencial activa sin usuario."
            )

        if not password:
            raise RuntimeError(
                "Credencial activa sin password/clave."
            )

        fecha = inicio.strftime("%d/%m/%Y")

        servicio = SinopticoR22Service()

        resultados = {}

        for unidad in ("U8", "U9"):
            try:
                resultado = servicio.descargar(
                    usuario=usuario,
                    password=password,
                    unidad=unidad,
                    fecha=fecha,
                )

                resultados[unidad] = {
                    "ok": True,
                    "estado": "COMPLETADO",
                    "ruta_archivo":
                        resultado.get("ruta_archivo"),
                    "bytes":
                        resultado.get("bytes"),
                    "fecha":
                        resultado.get("fecha"),
                }

            except Exception as exc:
                resultados[unidad] = {
                    "ok": False,
                    "estado": "ERROR",
                    "mensaje": str(exc),
                }

        fin = datetime.now()

        _estado_r22["ultima_ejecucion"] = (
            fin.isoformat(sep=" ", timespec="seconds")
        )

        _estado_r22["proxima_ejecucion"] = (
            fin
            + timedelta(
                minutes=INTERVALO_R22_MINUTOS
            )
        ).isoformat(
            sep=" ",
            timespec="seconds",
        )

        _estado_r22["resultados"] = resultados

        errores = [
            unidad
            for unidad, resultado
            in resultados.items()
            if not resultado.get("ok")
        ]

        if errores:
            _estado_r22["ultimo_error"] = (
                "Error R2.2 en: "
                + ", ".join(errores)
            )
        else:
            _estado_r22["ultimo_error"] = None

        return {
            "ok": not bool(errores),
            "estado":
                "COMPLETADO"
                if not errores
                else "PARCIAL",
            "inicio":
                inicio.isoformat(
                    sep=" ",
                    timespec="seconds",
                ),
            "fin":
                fin.isoformat(
                    sep=" ",
                    timespec="seconds",
                ),
            "resultados":
                resultados,
            "proxima_ejecucion":
                _estado_r22[
                    "proxima_ejecucion"
                ],
        }

    except Exception as exc:
        fin = datetime.now()

        _estado_r22["ultima_ejecucion"] = (
            fin.isoformat(
                sep=" ",
                timespec="seconds",
            )
        )

        _estado_r22["proxima_ejecucion"] = (
            fin
            + timedelta(
                minutes=INTERVALO_R22_MINUTOS
            )
        ).isoformat(
            sep=" ",
            timespec="seconds",
        )

        _estado_r22["ultimo_error"] = str(exc)

        return {
            "ok": False,
            "estado": "ERROR",
            "mensaje": str(exc),
        }

    finally:
        db.close()

        _estado_r22["ejecutando"] = False

        _lock_r22.release()


def scheduler_r22_tick():
    if not _estado_r22["activo"]:
        return {
            "ok": True,
            "estado": "INACTIVO",
        }

    ahora = datetime.now()

    proxima_texto = (
        _estado_r22.get(
            "proxima_ejecucion"
        )
    )

    if proxima_texto:
        try:
            proxima = datetime.fromisoformat(
                proxima_texto
            )
        except ValueError:
            proxima = None
    else:
        proxima = None

    if (
        proxima is not None
        and
        ahora < proxima
    ):
        return {
            "ok": True,
            "estado": "ESPERANDO",
            "proxima_ejecucion":
                proxima_texto,
        }

    return ejecutar_r22_ahora()
