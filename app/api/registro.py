"""
=========================================================
SWAV
Sistema Web de Análisis de Velocidades
=========================================================

Registro Operacional - API

Autor   : Edwin
Empresa : Metropol
Versión : 1.0

=========================================================
"""

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal

from app.services.registro_service import obtener_registro


# ==========================================================
# ROUTER
# ==========================================================

router = APIRouter(

    prefix="/api",

    tags=["Registro"],

)


# ==========================================================
# DATABASE
# ==========================================================

def get_db():

    db = SessionLocal()

    try:

        yield db

    finally:

        db.close()


# ==========================================================
# REGISTRO OPERACIONAL
# ==========================================================

@router.get("/registro")
def registro_operacional(

    servicio: str,

    periodo: int,

    db: Session = Depends(get_db),

):

    return obtener_registro(

        db,

        servicio,

        periodo,

    )