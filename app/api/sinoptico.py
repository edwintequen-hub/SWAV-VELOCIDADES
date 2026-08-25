"""
=========================================================
SWAV - SINOPTICO
API de integracion con Sinoptico
=========================================================
"""

from datetime import datetime
from pathlib import Path
import json
import subprocess


from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from sqlalchemy.orm import Session

from app.database import get_db
from app.services.procesador import ProcesadorSWAV

from pydantic import BaseModel


from app.services.sinoptico_service import (
    SinopticoService,
    SinopticoServiceError,
)


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/api/sinoptico",
    tags=["Sinoptico"],
)


# =========================================================
# MODELOS
# =========================================================

class SinopticoLoginRequest(BaseModel):

    usuario: str
    clave: str



# =========================================================
# DESCARGA AUTOMATICA R1.6
# =========================================================
# =========================================================
# DESCARGA + PROCESAMIENTO AUTOMATICO R1.6
# =========================================================

@router.post(
    "/r16download/{unidad}"
)
def descargar_r16(
    unidad: str,
    db: Session = Depends(get_db),
):

    unidad = (
        str(unidad)
        .upper()
        .strip()
    )

    if unidad not in (
        "U8",
        "U9",
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Unidad invalida. "
                "Use U8 o U9."
            )
        )

    ahora = datetime.now()

    fecha = ahora.strftime(
        "%d/%m/%Y"
    )

    hora_inicio = "00:00"

    hora_fin = ahora.strftime(
        "%H:%M"
    )

    bridge = (
        Path(__file__)
        .resolve()
        .parents[2]
        /
        "backend"
        /
        "sinoptico_bridge"
        /
        "SinopticoBridge.exe"
    )

    if not bridge.exists():

        raise HTTPException(
            status_code=500,
            detail=(
                "No existe "
                "SinopticoBridge.exe: "
                + str(bridge)
            )
        )

    # =====================================================
    # 1. DESCARGAR R1.6 Y ESPERAR TERMINO REAL
    # =====================================================

    try:

        proceso = subprocess.run(

            [
                str(bridge),

                "r16download",

                "edwin.tequen",

                unidad,

                fecha,

                hora_inicio,

                hora_fin,
            ],

            cwd=str(
                bridge.parent
            ),

            capture_output=True,

            text=True,

            errors="replace",

            timeout=300,

            check=False,
        )

    except subprocess.TimeoutExpired:

        raise HTTPException(
            status_code=504,
            detail=(
                "La descarga R1.6 excedio "
                "el tiempo maximo de espera."
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Error ejecutando "
                "SinopticoBridge: "
                + str(exc)
            )
        )

    salida = (
        proceso.stdout
        or ""
    ).strip()

    error_bridge = (
        proceso.stderr
        or ""
    ).strip()

    if proceso.returncode != 0:

        raise HTTPException(
            status_code=500,
            detail={
                "mensaje":
                    "SinopticoBridge termino con error",

                "codigo":
                    proceso.returncode,

                "stdout":
                    salida,

                "stderr":
                    error_bridge,
            }
        )

    # =====================================================
    # 2. LEER RESPUESTA JSON DEL BRIDGE
    # =====================================================

    inicio_json = salida.find("{")

    fin_json = salida.rfind("}")

    if (
        inicio_json < 0
        or fin_json < inicio_json
    ):

        raise HTTPException(
            status_code=500,
            detail={
                "mensaje":
                    "SinopticoBridge no devolvio JSON valido",

                "stdout":
                    salida,

                "stderr":
                    error_bridge,
            }
        )

    try:

        datos_bridge = json.loads(
            salida[
                inicio_json:
                fin_json + 1
            ]
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail={
                "mensaje":
                    "No fue posible interpretar "
                    "la respuesta del Bridge",

                "error":
                    str(exc),

                "stdout":
                    salida,
            }
        )

    if not datos_bridge.get(
        "descargado",
        False
    ):

        raise HTTPException(
            status_code=500,
            detail={
                "mensaje":
                    "El Bridge no confirmo "
                    "la descarga R1.6",

                "bridge":
                    datos_bridge,
            }
        )

    archivo = Path(
        str(
            datos_bridge.get(
                "archivo",
                ""
            )
        )
    )

    if not archivo.exists():

        raise HTTPException(
            status_code=500,
            detail=(
                "El Bridge informo la descarga, "
                "pero el archivo no existe: "
                + str(archivo)
            )
        )

    if archivo.stat().st_size <= 0:

        raise HTTPException(
            status_code=500,
            detail=(
                "El archivo R1.6 descargado "
                "esta vacio: "
                + str(archivo)
            )
        )

    # =====================================================
    # 3. PROCESAMIENTO COMPLETO SWAV
    # =====================================================

    try:

        procesador = ProcesadorSWAV(
            db
        )

        resultado = procesador.procesar(
            archivo=str(archivo),
            unidad=unidad,
        )

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "R1.6 descargado, pero fallo "
                "el procesamiento SWAV: "
                + str(exc)
            )
        )

    estado_proceso = (
        str(
            resultado.get(
                "estado",
                ""
            )
        )
        .strip()
        .upper()
    )

    # =====================================================
    # 4. MISMO ARCHIVO YA PROCESADO
    # =====================================================

    if estado_proceso == "DUPLICADO":

        return {

            "ok": True,

            "estado":
                "YA_PROCESADO",

            "unidad":
                unidad,

            "fecha":
                fecha,

            "desde":
                hora_inicio,

            "hasta":
                hora_fin,

            "archivo":
                str(archivo),

            "descargado":
                True,

            "procesado":
                False,

            "duplicado":
                True,

            "resultado":
                resultado,

            "mensaje":
                (
                    "El archivo R1.6 ya habia "
                    "sido procesado. "
                    "No se duplicaron datos."
                ),
        }

    if estado_proceso != "OK":

        raise HTTPException(
            status_code=500,
            detail={
                "mensaje":
                    "El procesamiento SWAV "
                    "no termino correctamente",

                "resultado":
                    resultado,
            }
        )

    # =====================================================
    # 5. RESPUESTA FINAL
    # =====================================================

    return {

        "ok": True,

        "estado":
            "COMPLETADO",

        "unidad":
            unidad,

        "fecha":
            fecha,

        "desde":
            hora_inicio,

        "hasta":
            hora_fin,

        "archivo":
            str(archivo),

        "descargado":
            True,

        "procesado":
            True,

        "base_datos_actualizada":
            True,

        "resultado":
            resultado,

        "mensaje":
            (
                "R1.6 descargado, procesado "
                "y guardado correctamente."
            ),
    }


# =========================================================
# DIAGNOSTICO SINOPTICO
# =========================================================

@router.get(
    "/diagnostico"
)
def diagnostico_sinoptico():

    try:

        servicio = SinopticoService()


        resultado = servicio.diagnostico()


        return resultado


    except SinopticoServiceError as exc:


        raise HTTPException(

            status_code=503,

            detail=str(exc)

        )


    except Exception as exc:


        raise HTTPException(

            status_code=500,

            detail=(

                "Error interno al ejecutar "
                "diagnostico Sinoptico: "
                +
                str(exc)

            )

        )



# =========================================================
# LOGIN SINOPTICO
# =========================================================

@router.post(
    "/login"
)
def login_sinoptico(

    datos: SinopticoLoginRequest,

):


    usuario = str(
        datos.usuario or ""
    ).strip()


    clave = str(
        datos.clave or ""
    )



    if not usuario:


        raise HTTPException(

            status_code=400,

            detail="Usuario Sinoptico requerido."

        )


    if not clave:


        raise HTTPException(

            status_code=400,

            detail="Clave Sinoptico requerida."

        )



    try:


        servicio = SinopticoService()



        resultado = servicio.login(

            usuario=usuario,

            clave=clave,

        )



        autenticado = (

            resultado.get("ok") is True

            and

            resultado.get(
                "autenticado"
            ) is True

            and

            resultado.get(
                "estado"
            ) == 1

        )



        if not autenticado:


            return {


                "ok":
                    False,


                "autenticado":
                    False,


                "estado":
                    resultado.get(
                        "estado"
                    ),


                "mensaje":

                    resultado.get(
                        "mensaje"
                    )

                    or

                    "Autenticacion Sinoptico rechazada."

            }



        return {


            "ok":
                True,


            "autenticado":
                True,


            "estado":
                resultado.get(
                    "estado"
                ),


            "mensaje":
                resultado.get(
                    "mensaje"
                ),

        }



    except SinopticoServiceError as exc:


        raise HTTPException(

            status_code=503,

            detail=str(exc)

        )


    except Exception as exc:


        raise HTTPException(

            status_code=500,

            detail=(

                "Error interno durante "
                "autenticacion Sinoptico: "
                +
                str(exc)

            )

        )


    finally:


        clave = None

