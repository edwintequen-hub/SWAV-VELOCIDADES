"""
=========================================================
SWAV
API REPORTES HISTORICOS
=========================================================

Todos los reportes consultan exclusivamente la BD historica.

Fuentes:
- HistoricoRegistro
- HistoricoPPU
- HistoricoExpedicion
=========================================================
"""

from io import BytesIO

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)

from fastapi.responses import (
    StreamingResponse,
)

from sqlalchemy.orm import Session

from app.database import get_db

from app.services.reportes import (
    consultar_resumen_historico,
    consultar_ppu_historico,
    consultar_expediciones_historicas,
    obtener_filtros_reportes,
    generar_excel_historico,
)


router = APIRouter(
    prefix="/reportes",
    tags=["Reportes"],
)


# =========================================================
# UTILIDADES SERIALIZACION
# =========================================================

def _fecha(valor):

    if valor is None:
        return None

    return valor.isoformat()


def _fecha_hora(valor):

    if valor is None:
        return None

    return valor.strftime(
        "%d/%m/%Y %H:%M:%S"
    )


def _numero(valor):

    if valor is None:
        return None

    return round(
        float(valor),
        2
    )


# =========================================================
# FILTROS DISPONIBLES
# =========================================================

@router.get(
    "/filtros"
)
def filtros_reportes(
    db: Session = Depends(get_db)
):

    return obtener_filtros_reportes(
        db
    )


# =========================================================
# RESUMEN HISTORICO
# =========================================================

@router.get(
    "/resumen"
)
def reporte_resumen(
    fecha_desde: str | None = Query(
        default=None
    ),
    fecha_hasta: str | None = Query(
        default=None
    ),
    unidad: str | None = Query(
        default=None
    ),
    tipo_dia: str | None = Query(
        default=None
    ),
    servicio_usuario: str | None = Query(
        default=None
    ),
    servicio_empresa: str | None = Query(
        default=None
    ),
    indicador: str | None = Query(
        default=None
    ),
    clasificacion: str | None = Query(
        default=None
    ),
    db: Session = Depends(get_db),
):

    try:

        registros = consultar_resumen_historico(
            db=db,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            unidad=unidad,
            tipo_dia=tipo_dia,
            servicio_usuario=servicio_usuario,
            servicio_empresa=servicio_empresa,
            indicador=indicador,
            clasificacion=clasificacion,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    return {
        "total": len(registros),

        "registros": [
            {
                "id": r.id,
                "fecha_operacional": _fecha(
                    r.fecha_operacional
                ),
                "unidad": r.unidad,
                "empresa": r.empresa,
                "tipo_dia": r.tipo_dia,
                "servicio_usuario": r.servicio,
                "codigo_ts": r.codigo_ts,
                "servicio_empresa": r.ruta,
                "ruta_normalizada": (
                    r.ruta_normalizada
                ),
                "sentido": r.sentido,
                "periodo": r.periodo,
                "expediciones": r.expediciones,
                "buses": r.buses,
                "velocidad_real": _numero(
                    r.velocidad_real
                ),
                "velocidad_teorica": _numero(
                    r.velocidad_teorica
                ),
                "reduccion": _numero(
                    r.porcentaje_reduccion
                ),
                "indicador": (
                    r.indicador_tiempo_espera
                ),
                "clasificacion": (
                    r.clasificacion
                ),
                "estado": r.estado,
                "informar": r.informar,
                "observacion": r.observacion,
                "archivo_origen": (
                    r.archivo_origen
                ),
            }

            for r in registros
        ],
    }


# =========================================================
# DETALLE PPU
# =========================================================

@router.get(
    "/ppu"
)
def reporte_ppu(
    fecha_desde: str | None = Query(
        default=None
    ),
    fecha_hasta: str | None = Query(
        default=None
    ),
    unidad: str | None = Query(
        default=None
    ),
    tipo_dia: str | None = Query(
        default=None
    ),
    servicio_usuario: str | None = Query(
        default=None
    ),
    servicio_empresa: str | None = Query(
        default=None
    ),
    indicador: str | None = Query(
        default=None
    ),
    clasificacion: str | None = Query(
        default=None
    ),
    db: Session = Depends(get_db),
):

    try:

        ppus = consultar_ppu_historico(
            db=db,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            unidad=unidad,
            tipo_dia=tipo_dia,
            servicio_usuario=servicio_usuario,
            servicio_empresa=servicio_empresa,
            indicador=indicador,
            clasificacion=clasificacion,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    return {
        "total": len(ppus),

        "ppu": [
            {
                "id": p.id,
                "historico_id": p.historico_id,
                "fecha_operacional": _fecha(
                    p.fecha_operacional
                ),
                "unidad": p.unidad,
                "tipo_dia": p.tipo_dia,
                "servicio_usuario": p.servicio,
                "codigo_ts": p.codigo_ts,
                "servicio_empresa": p.ruta,
                "ruta_normalizada": (
                    p.ruta_normalizada
                ),
                "sentido": p.sentido,
                "periodo": p.periodo,
                "patente": p.patente,
                "inicio_servicio": _fecha_hora(
                    p.inicio_servicio
                ),
                "fin_servicio": _fecha_hora(
                    p.fin_servicio
                ),
                "franja_horaria": (
                    p.franja_horaria
                ),
                "velocidad_real": _numero(
                    p.velocidad_real
                ),
                "velocidad_teorica": _numero(
                    p.velocidad_teorica
                ),
                "reduccion": _numero(
                    p.porcentaje_reduccion
                ),
                "indicador": (
                    p.indicador_tiempo_espera
                ),
                "clasificacion": (
                    p.clasificacion
                ),
                "estado": p.estado,
                "archivo_origen": (
                    p.archivo_origen
                ),
            }

            for p in ppus
        ],
    }


# =========================================================
# EXPEDICIONES HISTORICAS
# =========================================================

@router.get(
    "/expediciones-historicas"
)
def reporte_expediciones_historicas(
    fecha_desde: str | None = Query(
        default=None
    ),
    fecha_hasta: str | None = Query(
        default=None
    ),
    unidad: str | None = Query(
        default=None
    ),
    tipo_dia: str | None = Query(
        default=None
    ),
    servicio_usuario: str | None = Query(
        default=None
    ),
    servicio_empresa: str | None = Query(
        default=None
    ),
    indicador: str | None = Query(
        default=None
    ),
    clasificacion: str | None = Query(
        default=None
    ),
    db: Session = Depends(get_db),
):

    try:

        expediciones = (
            consultar_expediciones_historicas(
                db=db,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                unidad=unidad,
                tipo_dia=tipo_dia,
                servicio_usuario=servicio_usuario,
                servicio_empresa=servicio_empresa,
                indicador=indicador,
                clasificacion=clasificacion,
            )
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    return {
        "total": len(expediciones),

        "expediciones": [
            {
                "id": e.id,
                "fecha_operacional": _fecha(
                    e.fecha_operacional
                ),
                "unidad": e.unidad,
                "empresa": e.empresa,
                "tipo_dia": e.tipo_dia,
                "servicio_usuario": e.servicio,
                "codigo_bus": e.codigo_bus,
                "patente": e.patente,
                "codigo_ts": e.codigo_ts,
                "servicio_empresa": e.ruta,
                "ruta_normalizada": (
                    e.ruta_normalizada
                ),
                "sentido": e.sentido,
                "periodo": e.periodo,
                "inicio_servicio": _fecha_hora(
                    e.inicio_servicio
                ),
                "fin_servicio": _fecha_hora(
                    e.fin_servicio
                ),
                "franja_horaria": (
                    e.franja_horaria
                ),
                "velocidad_real": _numero(
                    e.velocidad_real
                ),
                "velocidad_teorica": _numero(
                    e.velocidad_teorica
                ),
                "reduccion": _numero(
                    e.porcentaje_reduccion
                ),
                "indicador": (
                    e.indicador_tiempo_espera
                ),
                "analizable": e.analizable,
                "motivo_no_analizable": (
                    e.motivo_no_analizable
                ),
                "clasificacion": (
                    e.clasificacion
                ),
                "archivo_origen": (
                    e.archivo_origen
                ),
            }

            for e in expediciones
        ],
    }


# =========================================================
# EXPORTAR EXCEL
# =========================================================

@router.get(
    "/excel"
)
def exportar_excel_historico(
    fecha_desde: str | None = Query(
        default=None
    ),
    fecha_hasta: str | None = Query(
        default=None
    ),
    unidad: str | None = Query(
        default=None
    ),
    tipo_dia: str | None = Query(
        default=None
    ),
    servicio_usuario: str | None = Query(
        default=None
    ),
    servicio_empresa: str | None = Query(
        default=None
    ),
    indicador: str | None = Query(
        default=None
    ),
    clasificacion: str | None = Query(
        default=None
    ),
    db: Session = Depends(get_db),
):

    try:

        resultado = generar_excel_historico(
            db=db,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            unidad=unidad,
            tipo_dia=tipo_dia,
            servicio_usuario=servicio_usuario,
            servicio_empresa=servicio_empresa,
            indicador=indicador,
            clasificacion=clasificacion,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    archivo = resultado[
        "archivo"
    ]

    nombre = (
        "SWAV_REPORTE_HISTORICO.xlsx"
    )

    return StreamingResponse(
        archivo,
        media_type=(
            "application/"
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="{nombre}"'
            ),
            "X-SWAV-Registros": str(
                resultado["registros"]
            ),
            "X-SWAV-PPU": str(
                resultado["ppu"]
            ),
        },
    )
