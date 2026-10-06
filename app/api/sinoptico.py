"""
=========================================================
SWAV - SINOPTICO
API de integracion con Sinoptico
=========================================================
"""

from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import os
import json
import subprocess
import time


from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.services.procesador import ProcesadorSWAV
from app.services.historico_flota_operativa_r16_service import (
    procesar_archivo_r16,
)
from app.services.historico_flota_operativa_servicio_r16_service import (
    procesar_r16_servicios,
)
from app.services.flota_ppu_detector_service import (
    detectar_ppu_desde_historico,
)
from app.services.reporte_comercial_r16_service import (
    sincronizar_historico_reporte_comercial_r16,
)
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

    ahora = datetime.now(ZoneInfo("America/Santiago"))

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

        _trace_t0 = time.monotonic()
        print(
            f"[R16 TRACE] {unidad} DESCARGA INICIO",
            flush=True,
        )

        datos_bridge = servicio_r16.descargar(
            usuario=usuario_sinoptico,
            unidad=unidad,
            fecha=fecha,
            hora_desde=hora_inicio,
            hora_hasta=hora_fin,
        )

        print(
            f"[R16 TRACE] {unidad} DESCARGA FIN "
            f"{time.monotonic() - _trace_t0:.2f}s",
            flush=True,
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
    # 3. FLOTA OPERATIVA - R1.6 ORIGINAL COMPLETO
    # =====================================================
    #
    # REGLA:
    # - usa directamente el R1.6 descargado;
    # - NO depende de Expedicion;
    # - NO depende de MotorComparacion;
    # - NO aplica filtros de Velocidades;
    # - conserva filas con velocidad 0;
    # - conserva FIN SERVICIO 1900;
    # - PPU repetida mismo periodo se consolida;
    # - historial principal:
    #       fecha + periodo + PPU
    # - historial servicio:
    #       fecha + periodo + PPU + servicio
    #
    # Se utiliza una sesion independiente para que
    # Flota Operativa no comparta transaccion con
    # el procesamiento de Velocidades.
    # =====================================================

    flota_db = SessionLocal()

    try:

        _trace_t0 = time.monotonic()
        print(
            f"[R16 TRACE] {unidad} FLOTA GENERAL INICIO",
            flush=True,
        )

        resultado_flota_operativa = (
            procesar_archivo_r16(
                db=flota_db,
                archivo=str(archivo),
                unidad=unidad,
            )
        )

        print(
            f"[R16 TRACE] {unidad} FLOTA GENERAL FIN "
            f"{time.monotonic() - _trace_t0:.2f}s",
            flush=True,
        )

        _trace_t0 = time.monotonic()
        print(
            f"[R16 TRACE] {unidad} FLOTA SERVICIOS INICIO",
            flush=True,
        )

        resultado_flota_servicios = (
            procesar_r16_servicios(
                db=flota_db,
                archivo=str(archivo),
                unidad=unidad,
            )
        )

        print(
            f"[R16 TRACE] {unidad} FLOTA SERVICIOS FIN "
            f"{time.monotonic() - _trace_t0:.2f}s",
            flush=True,
        )

        # =================================================
        # DETECTOR PERSISTENTE DE PPU NO RECONOCIDAS
        # =================================================
        #
        # Solo se procesan fechas reconocidas por AMBOS
        # historicos R1.6:
        #
        #   - Flota Operativa general
        #   - Flota Operativa por TS
        #
        # Cada fecha se procesa individualmente para evitar
        # incluir dias intermedios no presentes en el archivo.
        # =================================================

        fechas_flota_general = set(
            (
                resultado_flota_operativa.get(
                    "resultado_por_fecha",
                    {},
                )
                or {}
            ).keys()
        )

        fechas_flota_servicios = set(
            (
                resultado_flota_servicios.get(
                    "resultado_por_fecha",
                    {},
                )
                or {}
            ).keys()
        )

        fechas_detector = sorted(
            fechas_flota_general
            & fechas_flota_servicios
        )

        fechas_solo_general = sorted(
            fechas_flota_general
            - fechas_flota_servicios
        )

        fechas_solo_servicios = sorted(
            fechas_flota_servicios
            - fechas_flota_general
        )

        resultado_detector_ppu = {
            "estado": "OK",
            "fechas_procesadas": [],
            "fechas_solo_general":
                fechas_solo_general,
            "fechas_solo_servicios":
                fechas_solo_servicios,
            "eventos_analizados": 0,
            "eventos_candidatos": 0,
            "detecciones_creadas": 0,
            "detecciones_existentes": 0,
            "evidencias_creadas": 0,
            "evidencias_existentes": 0,
            "maestros_creados": 0,
            "maestros_actualizados": 0,
            "detalle_por_fecha": {},
        }

        for fecha_detector in fechas_detector:

            _trace_t0 = time.monotonic()
            print(
                f"[R16 TRACE] {unidad} DETECTOR INICIO "
                f"fecha={fecha_detector}",
                flush=True,
            )

            resultado_fecha_detector = (
                detectar_ppu_desde_historico(
                    db=flota_db,
                    fecha_desde=fecha_detector,
                    fecha_hasta=fecha_detector,
                    dry_run=False,
                )
            )

            print(
                f"[R16 TRACE] {unidad} DETECTOR FIN "
                f"fecha={fecha_detector} "
                f"{time.monotonic() - _trace_t0:.2f}s",
                flush=True,
            )

            persistencia_fecha = (
                resultado_fecha_detector.get(
                    "persistencia"
                )
                or {}
            )

            resultado_detector_ppu[
                "fechas_procesadas"
            ].append(
                fecha_detector
            )

            resultado_detector_ppu[
                "eventos_analizados"
            ] += (
                resultado_fecha_detector.get(
                    "eventos_analizados",
                    0,
                )
                or 0
            )

            resultado_detector_ppu[
                "eventos_candidatos"
            ] += (
                resultado_fecha_detector.get(
                    "eventos_candidatos",
                    0,
                )
                or 0
            )

            for clave in (
                "detecciones_creadas",
                "detecciones_existentes",
                "evidencias_creadas",
                "evidencias_existentes",
                "maestros_creados",
                "maestros_actualizados",
            ):

                resultado_detector_ppu[
                    clave
                ] += (
                    persistencia_fecha.get(
                        clave,
                        0,
                    )
                    or 0
                )

            resultado_detector_ppu[
                "detalle_por_fecha"
            ][fecha_detector] = {
                "eventos_analizados":
                    resultado_fecha_detector.get(
                        "eventos_analizados",
                        0,
                    ),

                "eventos_candidatos":
                    resultado_fecha_detector.get(
                        "eventos_candidatos",
                        0,
                    ),

                "persistencia":
                    persistencia_fecha,
            }

        # =================================================
        # HISTORICO REPORTE COMERCIAL R1.6
        # =================================================
        #
        # Usa exclusivamente fechas reconocidas por ambos
        # historicos de Flota Operativa. La funcion es
        # idempotente y participa en esta misma transaccion.
        # =================================================

        resultado_reporte_comercial_r16 = {
            "estado": "OK",
            "fechas_procesadas": [],
            "insertados": 0,
            "actualizados": 0,
            "detalle_por_fecha": {},
        }

        for fecha_comercial in fechas_detector:

            _trace_t0 = time.monotonic()
            print(
                f"[R16 TRACE] {unidad} COMERCIAL INICIO "
                f"fecha={fecha_comercial}",
                flush=True,
            )

            resultado_fecha_comercial = (
                sincronizar_historico_reporte_comercial_r16(
                    db=flota_db,
                    fecha=fecha_comercial,
                    unidad=unidad,
                    commit=False,
                )
            )

            print(
                f"[R16 TRACE] {unidad} COMERCIAL FIN "
                f"fecha={fecha_comercial} "
                f"{time.monotonic() - _trace_t0:.2f}s",
                flush=True,
            )

            resultado_reporte_comercial_r16[
                "fechas_procesadas"
            ].append(
                fecha_comercial
            )

            resultado_reporte_comercial_r16[
                "insertados"
            ] += (
                resultado_fecha_comercial.get(
                    "insertados",
                    0,
                )
                or 0
            )

            resultado_reporte_comercial_r16[
                "actualizados"
            ] += (
                resultado_fecha_comercial.get(
                    "actualizados",
                    0,
                )
                or 0
            )

            resultado_reporte_comercial_r16[
                "detalle_por_fecha"
            ][fecha_comercial] = (
                resultado_fecha_comercial
            )

        _trace_t0 = time.monotonic()
        print(
            f"[R16 TRACE] {unidad} COMMIT FLOTA INICIO",
            flush=True,
        )

        flota_db.commit()

        print(
            f"[R16 TRACE] {unidad} COMMIT FLOTA FIN "
            f"{time.monotonic() - _trace_t0:.2f}s",
            flush=True,
        )

    except Exception as exc:

        flota_db.rollback()

        raise HTTPException(
            status_code=500,
            detail={
                "mensaje":
                    "R1.6 descargado, pero fallo "
                    "la persistencia independiente "
                    "de Flota Operativa",
                "error":
                    str(exc),
                "unidad":
                    unidad,
                "archivo":
                    str(archivo),
            }
        )

    finally:

        flota_db.close()


    # =====================================================
    # 4. PROCESAMIENTO COMPLETO SWAV / VELOCIDADES
    # =====================================================

    try:

        procesador = ProcesadorSWAV(
            db
        )

        _trace_t0 = time.monotonic()
        print(
            f"[R16 TRACE] {unidad} SWAV INICIO",
            flush=True,
        )

        resultado = procesador.procesar(
            archivo=str(archivo),
            unidad=unidad,
        )

        print(
            f"[R16 TRACE] {unidad} SWAV FIN "
            f"{time.monotonic() - _trace_t0:.2f}s",
            flush=True,
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
    # 5. MISMO ARCHIVO YA PROCESADO
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
    # 6. RESPUESTA FINAL
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
        "flota_operativa":
            resultado_flota_operativa,

        "flota_operativa_servicios":
            resultado_flota_servicios,

        "detector_ppu":
            resultado_detector_ppu,

        "reporte_comercial_r16":
            resultado_reporte_comercial_r16,

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
