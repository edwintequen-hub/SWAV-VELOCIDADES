"""
=========================================================
SWAV - API IMPORTACIONES
=========================================================
"""

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    UploadFile,
)

from sqlalchemy.orm import Session

from app.database import get_db
from app.services.procesador import ProcesadorSWAV


router = APIRouter(
    prefix="/importar",
    tags=["Importaciones"],
)


# ==========================================================
# IMPORTAR R1.6
# ==========================================================

@router.post("/r16")
def importar_r16(

    unidad: str = Form(...),

    archivo: UploadFile = File(...),

    db: Session = Depends(get_db),

):

    # ---------------------------------------------
    # VALIDAR ARCHIVO
    # ---------------------------------------------

    if not archivo.filename:

        return {

            "estado": "ERROR",

            "mensaje": "Debe seleccionar un archivo."

        }

    if not archivo.filename.lower().endswith(".csv"):

        return {

            "estado": "ERROR",

            "mensaje": "Debe seleccionar un archivo CSV."

        }

    # ---------------------------------------------
    # PROCESADOR PRINCIPAL
    # ---------------------------------------------

    procesador = ProcesadorSWAV(db)

    resultado = procesador.procesar(

        archivo=archivo,

        unidad=unidad,

    )

    return resultado