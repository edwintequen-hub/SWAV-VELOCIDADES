"""
=========================================================
SWAV
API Configuración
=========================================================
"""

from pathlib import Path
import shutil

from fastapi import APIRouter
from fastapi import File
from fastapi import UploadFile
from fastapi import HTTPException

from app.database import SessionLocal
from app.models import HistorialImportacion

#--------------------------------------------------------
# IMPORTADORES
#--------------------------------------------------------

from app.services.importar_info import ImportadorINFO

from app.importadores.importar_anexo3 import (
    ImportadorAnexo3
)

from app.importadores.importar_anexo4 import (
    ImportadorAnexo4
)

from app.services.procesador import ProcesadorSWAV


router = APIRouter(

    prefix="/api/configuracion",

    tags=["Configuración"]

)

UPLOAD_DIR = Path("uploads")

UPLOAD_DIR.mkdir(exist_ok=True)


#=========================================================
# GUARDAR ARCHIVO
#=========================================================

def guardar_archivo(archivo: UploadFile):

    destino = UPLOAD_DIR / archivo.filename

    with open(destino, "wb") as buffer:

        shutil.copyfileobj(

            archivo.file,

            buffer

        )

    return destino


#=========================================================
# INFO
#=========================================================

@router.post("/info")

async def importar_info(

    archivo: UploadFile = File(...)

):

    db = SessionLocal()

    try:

        ruta = guardar_archivo(archivo)

        registros = ImportadorINFO(db).importar(ruta)

        return {

            "estado": "OK",

            "registros": registros

        }

    except Exception as e:

        raise HTTPException(

            status_code=500,

            detail=str(e)

        )

    finally:

        db.close()


#=========================================================
# ANEXO 3
#=========================================================

@router.post("/anexo3")

async def importar_anexo3(

    archivo: UploadFile = File(...)

):

    db = SessionLocal()

    try:

        ruta = guardar_archivo(archivo)

        registros = ImportadorAnexo3(db).importar(ruta)

        return {

            "estado": "OK",

            "registros": registros

        }

    except Exception as e:

        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:

        db.close()


#=========================================================
# ANEXO 4
#=========================================================

@router.post("/anexo4")

async def importar_anexo4(

    archivo: UploadFile = File(...)

):

    db = SessionLocal()

    try:

        ruta = guardar_archivo(archivo)

        registros = ImportadorAnexo4(db).importar(ruta)

        return {

            "estado": "OK",

            "registros": registros

        }

    except Exception as e:

        raise HTTPException(

            status_code=500,

            detail=str(e)

        )

    finally:

        db.close()

# =========================================================
# ESTADO DE IMPORTACIONES
# =========================================================

@router.get("/estado")
async def estado_importaciones():

    from app.models import Velocidad, Periodo
    from sqlalchemy import func

    db = SessionLocal()

    try:

        resultado = {}

        # =====================================================
        # INFO
        # =====================================================

        historial_info = (
            db.query(HistorialImportacion)
            .filter(
                HistorialImportacion.tipo_archivo == "INFO"
            )
            .order_by(
                HistorialImportacion.id.desc()
            )
            .first()
        )

        if historial_info:

            resultado["INFO"] = {
                "estado": "OK",
                "registros": historial_info.registros_validos,
                "fecha": (
                    historial_info.fecha.isoformat()
                    if historial_info.fecha
                    else None
                ),
                "archivo": historial_info.archivo,
                "unidad": "TODAS"
            }

        else:

            resultado["INFO"] = {
                "estado": "PENDIENTE",
                "registros": 0,
                "fecha": None,
                "archivo": None,
                "unidad": "TODAS"
            }

        # =====================================================
        # ANEXO 3
        # =====================================================

        velocidades = (
            db.query(
                Velocidad.unidad,
                func.count(Velocidad.id)
            )
            .group_by(
                Velocidad.unidad
            )
            .all()
        )

        unidades_anexo3 = {}

        for unidad, cantidad in velocidades:

            if unidad:

                unidades_anexo3[unidad] = {
                    "estado": "OK",
                    "registros": cantidad
                }

        historial_anexo3 = (
            db.query(HistorialImportacion)
            .filter(
                HistorialImportacion.tipo_archivo == "ANEXO 3"
            )
            .order_by(
                HistorialImportacion.id.desc()
            )
            .first()
        )

        resultado["ANEXO 3"] = {
            "estado": "OK" if unidades_anexo3 else "PENDIENTE",
            "registros": sum(
                item["registros"]
                for item in unidades_anexo3.values()
            ),
            "unidades": unidades_anexo3,
            "fecha": (
                historial_anexo3.fecha.isoformat()
                if historial_anexo3 and historial_anexo3.fecha
                else None
            ),
            "archivo": (
                historial_anexo3.archivo
                if historial_anexo3
                else None
            )
        }

        # =====================================================
        # ANEXO 4
        # =====================================================

        periodos = (
            db.query(
                Periodo.unidad,
                func.count(Periodo.id)
            )
            .group_by(
                Periodo.unidad
            )
            .all()
        )

        unidades_anexo4 = {}

        for unidad, cantidad in periodos:

            if unidad:

                unidades_anexo4[unidad] = {
                    "estado": "OK",
                    "registros": cantidad
                }

        historial_anexo4 = (
            db.query(HistorialImportacion)
            .filter(
                HistorialImportacion.tipo_archivo == "ANEXO 4"
            )
            .order_by(
                HistorialImportacion.id.desc()
            )
            .first()
        )

        resultado["ANEXO 4"] = {
            "estado": "OK" if unidades_anexo4 else "PENDIENTE",
            "registros": sum(
                item["registros"]
                for item in unidades_anexo4.values()
            ),
            "unidades": unidades_anexo4,
            "fecha": (
                historial_anexo4.fecha.isoformat()
                if historial_anexo4 and historial_anexo4.fecha
                else None
            ),
            "archivo": (
                historial_anexo4.archivo
                if historial_anexo4
                else None
            )
        }

        # =====================================================
        # R1.6 POR UNIDAD
        # =====================================================

        historiales_r16 = (
            db.query(HistorialImportacion)
            .filter(
                HistorialImportacion.tipo_archivo == "R1.6"
            )
            .order_by(
                HistorialImportacion.id.desc()
            )
            .all()
        )

        r16 = {}

        for historial in historiales_r16:

            unidad = historial.unidad

            if not unidad:
                continue

            # Conservamos solamente el último registro
            # de cada unidad.
            if unidad in r16:
                continue

            r16[unidad] = {
                "estado": "OK",
                "registros": historial.registros_validos,
                "fecha": (
                    historial.fecha.isoformat()
                    if historial.fecha
                    else None
                ),
                "archivo": historial.archivo,
                "unidad": unidad
            }

        resultado["R1.6"] = r16

        return resultado

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:

        db.close()


#=========================================================
# R1.6
#=========================================================

@router.post("/r16")

async def importar_r16(

    unidad: str,

    archivo: UploadFile = File(...)

):

    db = SessionLocal()

    try:

        ruta = guardar_archivo(archivo)

        resultado = ProcesadorSWAV(db).procesar(

            archivo=ruta,

            unidad=unidad

        )

        return resultado

    except Exception as e:

        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:

        db.close()