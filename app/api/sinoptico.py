"""
=========================================================
SWAV - SINOPTICO
API de integracion con Sinoptico
=========================================================
"""

from datetime import datetime
from pathlib import Path
import os
import json
import subprocess


from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from sqlalchemy.orm import Session

from app.database import get_db
from app.services.procesador import ProcesadorSWAV
from app.services.sinoptico_r16_service import SinopticoR16Service
from app.models import CredencialSinoptico

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

    # =====================================================
    # CREDENCIAL SINOPTICO ACTIVA
    # =====================================================

    # =====================================================
    # CREDENCIAL SINOPTICO
    #
    # PRIORIDAD:
    # 1. Variables de entorno (Render / produccion)
    # 2. Base de datos (local / configuracion)
    # =====================================================

    usuario_env = str(
        os.getenv(
            "SWAV_SINOPTICO_USER",
            ""
        )
    ).strip()

    password_env = str(
        os.getenv(
            "SWAV_SINOPTICO_PASSWORD",
            ""
        )
    )

    if usuario_env and password_env:

        usuario_sinoptico = usuario_env
        password_sinoptico = password_env

    else:

        credencial = (
            db.query(CredencialSinoptico)
            .filter(
                CredencialSinoptico.activo == True
            )
            .order_by(
                CredencialSinoptico.id.desc()
            )
            .first()
        )

        if not credencial:

            raise HTTPException(
                status_code=400,
                detail=(
                    "No existe una credencial "
                    "Sinoptico activa y tampoco "
                    "estan configuradas "
                    "SWAV_SINOPTICO_USER / "
                    "SWAV_SINOPTICO_PASSWORD."
                )
            )

        usuario_sinoptico = (
            str(
                credencial.usuario or ""
            )
            .strip()
        )

        password_sinoptico = (
            str(
                credencial.password or ""
            )
        )

    if (
        not usuario_sinoptico
        or not password_sinoptico
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "La credencial Sinoptico "
                "esta incompleta."
            )
        )

    # =====================================================
    # 1. DESCARGAR R1.6 MEDIANTE SERVICE CERTIFICADO
    # =====================================================

    try:

        servicio_r16 = SinopticoR16Service(
            max_intentos=3,
            espera_reintento=3,
        )

        datos_bridge = servicio_r16.descargar(
            usuario=usuario_sinoptico,
            unidad=unidad,
            fecha=fecha,
            hora_desde=hora_inicio,
            hora_hasta=hora_fin,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "No fue posible descargar "
                "el R1.6 desde Sinoptico: "
                + str(exc)
            )
        )

    # =====================================================
    # 2. VALIDAR RESULTADO DEL SERVICE
    # =====================================================

    if not datos_bridge.get(
        "ok",
        False
    ):
        raise HTTPException(
            status_code=500,
            detail={
                "mensaje":
                    "El servicio Sinoptico "
                    "no confirmo la descarga R1.6",
                "bridge":
                    datos_bridge,
            }
        )

    if not datos_bridge.get(
        "validado",
        False
    ):
        raise HTTPException(
            status_code=500,
            detail={
                "mensaje":
                    "El R1.6 descargado "
                    "no fue validado",
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
                "El servicio informo la descarga, "
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
    # DIAGNOSTICO ARCHIVO REAL RECIBIDO DEL BRIDGE
    # =====================================================

    print()
    print("=" * 100)
    print("DIAGNOSTICO R1.6 - ARCHIVO RECIBIDO DEL BRIDGE")
    print("=" * 100)
    print("RUTA :", archivo)
    print("EXISTE :", archivo.exists())

    if archivo.exists():

        print(
            "TAMANO :",
            archivo.stat().st_size
        )

        try:

            contenido_debug = archivo.read_text(
                encoding="utf-8-sig",
                errors="replace"
            )

            lineas_debug = (
                contenido_debug.splitlines()
            )

            print("LINEAS :", len(lineas_debug))

            print("-" * 100)

            for numero, linea in enumerate(
                lineas_debug[:15],
                start=1
            ):

                print(
                    f"{numero:03d}:",
                    repr(linea)
                )

            print("-" * 100)

            encabezados = [
                (
                    i + 1,
                    linea
                )
                for i, linea
                in enumerate(lineas_debug)
                if (
                    "SERVICIO" in linea.upper()
                    and
                    "CODIGO BUS" in linea.upper()
                    and
                    "PATENTE BUS" in linea.upper()
                )
            ]

            print(
                "ENCABEZADOS DETECTADOS:",
                len(encabezados)
            )

            for numero, linea in encabezados[:3]:

                print(
                    "HEADER LINEA:",
                    numero
                )

                print(
                    "HEADER REPR:",
                    repr(linea)
                )

                print(
                    "TABS:",
                    linea.count("\t"),
                    "| ;:",
                    linea.count(";"),
                    "| ,:",
                    linea.count(",")
                )

        except Exception as exc_debug:

            print(
                "ERROR LEYENDO ARCHIVO DEBUG:",
                repr(exc_debug)
            )

    print("=" * 100)
    print()


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





# =========================================================
# DIAGNOSTICO SECRETO SINOPTICO
# NO EXPONE EL VALOR DEL SECRETO
# =========================================================

@router.get("/secret-debug")
def secret_debug():

    import os

    valor_crudo = os.getenv(
        "SWAV_SINOPTICO_REPORT_SECRET",
        ""
    )

    valor_trim = str(
        valor_crudo or ""
    ).strip()

    servicio = SinopticoR16Service(
        max_intentos=1,
        espera_reintento=1,
    )

    return {
        "variable_presente": bool(
            valor_crudo
        ),
        "largo_crudo": len(
            valor_crudo
        ),
        "largo_trim": len(
            valor_trim
        ),
        "tiene_espacio_inicio": (
            len(valor_crudo)
            !=
            len(valor_crudo.lstrip())
        ),
        "tiene_espacio_fin": (
            len(valor_crudo)
            !=
            len(valor_crudo.rstrip())
        ),
        "modo_directo": servicio.modo_directo,
        "largo_service_secret": len(
            servicio.sinoptico_report_secret
        ),
    }
