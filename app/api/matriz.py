"""
=========================================================
SWAV
API MATRIZ OPERACIONAL
=========================================================
"""

from fastapi import APIRouter

from app.services.matriz_service import obtener_matriz


router = APIRouter(

    prefix="/api/matriz",

    tags=["Matriz"]

)


@router.get("")
def matriz(

    unidad: str = "",

    tipo_dia: str = "",

    estado: str = "Todos",

    servicio_usuario: str = "",

    servicio_empresa: str = "",

    fecha_desde: str = "",

    fecha_hasta: str = ""

):

    return obtener_matriz(

        unidad=unidad,

        tipo_dia=tipo_dia,

        estado=estado,

        servicio_usuario=servicio_usuario,

        servicio_empresa=servicio_empresa,

        fecha_desde=fecha_desde,

        fecha_hasta=fecha_hasta

    )
