"""
=========================================================
SWAV
Sistema Web de Análisis de Velocidades
=========================================================

Registro Operacional

Versión 2.0
Alineado con la Macro Excel

=========================================================
"""

from sqlalchemy.orm import Session

from app.models import Expedicion
from app.models import Registro


# =========================================================
# CABECERA
# =========================================================

def obtener_cabecera_registro(
    db: Session,
    servicio: str,
    periodo: int,
):

    return (

        db.query(Registro)

        .filter(

            Registro.servicio == servicio,

            Registro.periodo == periodo,

        )

        .first()

    )


# =========================================================
# DETALLE
# =========================================================

def obtener_detalle_registro(
    db: Session,
    servicio: str,
    periodo: int,
):

    expediciones = (

        db.query(Expedicion)

        .filter(

            Expedicion.servicio == servicio,

            Expedicion.periodo == periodo,

        )

        .order_by(

            Expedicion.inicio_servicio.asc()

        )

        .all()

    )

    resultado = []

    for e in expediciones:

        resultado.append(

            {

                "patente": e.patente,

                "codigo_bus": e.codigo_bus,

                "ruta": e.ruta,

                "ruta_normalizada": e.ruta_normalizada,

                "inicio": e.inicio_servicio,

                "fin": e.fin_servicio,

                "duracion": e.duracion_min,

                "velocidad_real": e.velocidad_km_h,

                "velocidad_teorica": e.velocidad_teorica,

                "reduccion": e.porcentaje_reduccion,

                "plazas": e.plazas,

                "sentido": e.sentido,

                "codigo_ts": e.codigo_ts,

            }

        )

    return resultado


# =========================================================
# REGISTRO COMPLETO
# =========================================================

def obtener_registro(
    db: Session,
    servicio: str,
    periodo: int,
):

    cabecera = obtener_cabecera_registro(
        db,
        servicio,
        periodo,
    )

    detalle = obtener_detalle_registro(
        db,
        servicio,
        periodo,
    )

    if cabecera is None:

        return {

            "cabecera": None,

            "detalle": detalle,

        }

    return {

        "cabecera": {

            "servicio": cabecera.servicio,

            "ruta": cabecera.ruta,

            "ruta_normalizada": cabecera.ruta_normalizada,

            "sentido": cabecera.sentido,

            "periodo": cabecera.periodo,

            "expediciones": cabecera.expediciones,

            "buses": cabecera.buses,

            "velocidad_real": cabecera.velocidad_real,

            "velocidad_teorica": cabecera.velocidad_teorica,

            "reduccion": cabecera.porcentaje_reduccion,

            "clasificacion": cabecera.clasificacion,

            "estado": cabecera.estado,

        },

        "detalle": detalle,

    }