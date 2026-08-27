"""
=========================================================
METROPOL
Dashboard API
=========================================================
"""

from fastapi import APIRouter
from sqlalchemy import func, case
from datetime import timezone
from zoneinfo import ZoneInfo

from app.database import SessionLocal
from app.models import HistoricoRegistro, HistorialImportacion

router = APIRouter(
    prefix="/api",
    tags=["Dashboard"],
)


@router.get("/dashboard")
def dashboard():

    db = SessionLocal()

    try:

        # =====================================================
        # INFORMACIÃ“N DEL SISTEMA
        # =====================================================

        # =====================================================
        # FECHA OPERACIONAL ACTUAL DEL DASHBOARD
        # =====================================================

        ultima_fecha_operacional = (
            db.query(
                func.max(
                    HistoricoRegistro.fecha_operacional
                )
            )
            .scalar()
        )

        # =====================================================
        # UNIDAD DE LA ULTIMA IMPORTACION R1.6
        # =====================================================

        ultima_importacion_registro = (
            db.query(HistorialImportacion)
            .filter(
                HistorialImportacion.tipo_archivo == "R1.6"
            )
            .order_by(
                HistorialImportacion.fecha.desc(),
                HistorialImportacion.id.desc(),
            )
            .first()
        )

        unidad_actual = (
            str(
                ultima_importacion_registro.unidad
                or ""
            ).strip()
            if ultima_importacion_registro
            else ""
        )

        ultima_importacion = (
            ultima_importacion_registro.fecha
            if ultima_importacion_registro
            else None
        )

        # =====================================================
        # FILTRO OPERACIONAL DEL DASHBOARD
        #
        # Todo el Dashboard debe pertenecer a:
        #   - ultima fecha operacional
        #   - ultima unidad procesada
        # =====================================================

        if unidad_actual:

            filtro_fecha = (
                (
                    HistoricoRegistro.fecha_operacional
                    == ultima_fecha_operacional
                )
                &
                (
                    HistoricoRegistro.unidad
                    == unidad_actual
                )
            )

        else:

            unidad_actual = "--"

            filtro_fecha = (
                HistoricoRegistro.fecha_operacional
                == ultima_fecha_operacional
            )

        # SQLite CURRENT_TIMESTAMP se guarda en UTC.
        # Convertimos a hora oficial de Santiago para la UI.
        if ultima_importacion is not None:

            ultima_importacion = (
                ultima_importacion
                .replace(tzinfo=timezone.utc)
                .astimezone(
                    ZoneInfo("America/Santiago")
                )
            )

        # =====================================================
        # 1. INDICADORES GENERALES
        # =====================================================


        total_registros = (
            db.query(HistoricoRegistro)
            .filter(filtro_fecha)
            .count()
        )

        total_expediciones = (
            db.query(
                func.sum(
                    HistoricoRegistro.expediciones
                )
            )
            .filter(filtro_fecha)
            .scalar() or 0
        )

        total_buses = (
            db.query(
                func.sum(
                    HistoricoRegistro.buses
                )
            )
            .filter(filtro_fecha)
            .scalar() or 0
        )

        velocidad_real = (
            db.query(
                func.avg(
                    HistoricoRegistro.velocidad_real
                )
            )
            .filter(filtro_fecha)
            .scalar() or 0
        )

        velocidad_teorica = (
            db.query(
                func.avg(
                    HistoricoRegistro.velocidad_teorica
                )
            )
            .filter(filtro_fecha)
            .scalar() or 0
        )

        reduccion = (
            db.query(
                func.avg(
                    HistoricoRegistro.porcentaje_reduccion
                )
            )
            .filter(filtro_fecha)
            .scalar() or 0
        )

        # =====================================================
        # 2. CLASIFICACIÃ“N OPERACIONAL
        # =====================================================

        total_ok = (
            db.query(HistoricoRegistro)
            .filter(
                filtro_fecha,
                HistoricoRegistro.clasificacion == "OK"
            )
            .count()
        )

        total_simple = (
            db.query(HistoricoRegistro)
            .filter(
                filtro_fecha,
                HistoricoRegistro.clasificacion == "SIMPLE"
            )
            .count()
        )

        total_complejo = (
            db.query(HistoricoRegistro)
            .filter(
                filtro_fecha,
                HistoricoRegistro.clasificacion == "COMPLEJO"
            )
            .count()
        )

        total_sin_velocidad = (
            db.query(HistoricoRegistro)
            .filter(
                filtro_fecha,
                HistoricoRegistro.clasificacion == "SIN VELOCIDAD"
            )
            .count()
        )

        # =====================================================
        # 2B. INDICADORES IP / IE
        # =====================================================

        ip_expediciones = (
            db.query(
                func.sum(HistoricoRegistro.expediciones)
            )
            .filter(
                filtro_fecha,
                HistoricoRegistro.indicador_tiempo_espera == "IP"
            )
            .scalar() or 0
        )

        ip_ok = (
            db.query(HistoricoRegistro)
            .filter(
                filtro_fecha,
                HistoricoRegistro.indicador_tiempo_espera == "IP",
                HistoricoRegistro.clasificacion == "OK"
            )
            .count()
        )

        ip_simple = (
            db.query(HistoricoRegistro)
            .filter(
                filtro_fecha,
                HistoricoRegistro.indicador_tiempo_espera == "IP",
                HistoricoRegistro.clasificacion == "SIMPLE"
            )
            .count()
        )

        ip_complejo = (
            db.query(HistoricoRegistro)
            .filter(
                filtro_fecha,
                HistoricoRegistro.indicador_tiempo_espera == "IP",
                HistoricoRegistro.clasificacion == "COMPLEJO"
            )
            .count()
        )

        ie_expediciones = (
            db.query(
                func.sum(HistoricoRegistro.expediciones)
            )
            .filter(
                filtro_fecha,
                HistoricoRegistro.indicador_tiempo_espera == "IE"
            )
            .scalar() or 0
        )

        ie_ok = (
            db.query(HistoricoRegistro)
            .filter(
                filtro_fecha,
                HistoricoRegistro.indicador_tiempo_espera == "IE",
                HistoricoRegistro.clasificacion == "OK"
            )
            .count()
        )

        ie_simple = (
            db.query(HistoricoRegistro)
            .filter(
                filtro_fecha,
                HistoricoRegistro.indicador_tiempo_espera == "IE",
                HistoricoRegistro.clasificacion == "SIMPLE"
            )
            .count()
        )

        ie_complejo = (
            db.query(HistoricoRegistro)
            .filter(
                filtro_fecha,
                HistoricoRegistro.indicador_tiempo_espera == "IE",
                HistoricoRegistro.clasificacion == "COMPLEJO"
            )
            .count()
        )

        ip_eventos = ip_simple + ip_complejo
        ie_eventos = ie_simple + ie_complejo

        # 3. ESTADO OPERACIONAL
        # =====================================================

        total_pendientes = (

            db.query(HistoricoRegistro)

            .filter(
                filtro_fecha,
                HistoricoRegistro.estado == "PENDIENTE"
            )

            .count()

        )

        total_informados = (

            db.query(HistoricoRegistro)

            .filter(
                filtro_fecha,
                HistoricoRegistro.estado == "INFORMADO DTPM"
            )

            .count()

        )

         # =====================================================
        # 4. CENTRO DE ALERTAS
        # =====================================================

        evento_critico = (

            db.query(HistoricoRegistro)

            .filter(
                filtro_fecha,
                HistoricoRegistro.clasificacion == "COMPLEJO"
            )

            .order_by(
                HistoricoRegistro.porcentaje_reduccion.desc()
            )

            .first()

        )

        # =====================================================
        # 4B. EVENTOS PRIORITARIOS A INFORMAR
        # =====================================================
        #
        # Regla:
        # 1. COMPLEJOS primero.
        # 2. Luego SIMPLES si no existen suficientes complejos.
        # 3. Máximo 3 eventos por indicador.
        # 4. Mayor reducción primero dentro de cada clasificación.
        # =====================================================

        prioridad_clasificacion = case(
            (
                HistoricoRegistro.clasificacion == "COMPLEJO",
                1
            ),
            (
                HistoricoRegistro.clasificacion == "SIMPLE",
                2
            ),
            else_=3
        )

        # =====================================================
        # EVENTOS PRIORITARIOS COMBINADOS IP + IE
        # =====================================================
        #
        # Reglas:
        # 1. COMPLEJOS primero.
        # 2. SIMPLES después.
        # 3. Dentro de cada clasificación:
        #    mayor reducción -> menor reducción.
        # 4. IP e IE se mezclan.
        # 5. Máximo 6 eventos.
        # =====================================================

        prioritarios = (
            db.query(HistoricoRegistro)
            .filter(
                filtro_fecha,
                HistoricoRegistro.indicador_tiempo_espera.in_(
                    ["IP", "IE"]
                ),
                HistoricoRegistro.clasificacion.in_(
                    ["COMPLEJO", "SIMPLE"]
                )
            )
            .order_by(
                prioridad_clasificacion.asc(),
                HistoricoRegistro.porcentaje_reduccion.desc()
            )
            .limit(6)
            .all()
        )

        def serializar_prioritario(evento):

            return {

                "id": evento.id,

                "indicador":
                    evento.indicador_tiempo_espera,

                "clasificacion":
                    evento.clasificacion,

                "servicio":
                    evento.servicio,

                "ruta":
                    evento.ruta,

                "sentido":
                    evento.sentido,

                "periodo":
                    evento.periodo,

                "velocidad_real":
                    round(
                        evento.velocidad_real or 0,
                        2
                    ),

                "velocidad_teorica":
                    round(
                        evento.velocidad_teorica or 0,
                        2
                    ),

                "reduccion":
                    round(
                        evento.porcentaje_reduccion or 0,
                        2
                    ),

                "fecha_operacional":
                    evento.fecha_operacional.isoformat()
                    if evento.fecha_operacional
                    else None,

                "estado":
                    evento.estado,

                "informar":
                    bool(evento.informar),

                "observacion":
                    evento.observacion

            }

        # =====================================================
        # 5. TOP 10 SERVICIOS CON MAYOR REDUCCIÃ“N
        # =====================================================

        top_servicios = (

            db.query(

                HistoricoRegistro.servicio,

                func.max(
                    HistoricoRegistro.porcentaje_reduccion
                ).label("reduccion"),

                func.avg(
                    HistoricoRegistro.velocidad_real
                ).label("velocidad_real"),

                func.avg(
                    HistoricoRegistro.velocidad_teorica
                ).label("velocidad_teorica"),

                func.count(
                    HistoricoRegistro.id
                ).label("eventos")

            )

            .filter(
                filtro_fecha,
                HistoricoRegistro.clasificacion != "OK"
            )

            .group_by(
                HistoricoRegistro.servicio
            )

            .order_by(
                func.max(
                    HistoricoRegistro.porcentaje_reduccion
                ).desc()
            )

            .limit(10)

            .all()

        )

        # =====================================================
        # 6. REDUCCIÃ“N PROMEDIO POR PERÃODO
        # =====================================================

        reduccion_periodos = (

            db.query(

                HistoricoRegistro.periodo,

                func.max(
                    HistoricoRegistro.porcentaje_reduccion
                ).label("reduccion"),

                func.count(
                    HistoricoRegistro.id
                ).label("eventos")

            )

            .filter(
                filtro_fecha,
                HistoricoRegistro.clasificacion != "OK"
            )

            .group_by(
                HistoricoRegistro.periodo
            )

            .order_by(
                HistoricoRegistro.periodo
            )

            .all()

        )

        # =====================================================
        # 7. COMPARACIÃ“N VELOCIDAD REAL VS TEÃ“RICA
        # =====================================================

        comparacion_velocidades = (

            db.query(

                HistoricoRegistro.servicio,

                func.avg(
                    HistoricoRegistro.velocidad_real
                ).label("velocidad_real"),

                func.avg(
                    HistoricoRegistro.velocidad_teorica
                ).label("velocidad_teorica"),

                func.max(
                    HistoricoRegistro.porcentaje_reduccion
                ).label("reduccion"),

            )

            .filter(filtro_fecha)
            .group_by(
                HistoricoRegistro.servicio
            )

            .order_by(
                func.max(
                    HistoricoRegistro.porcentaje_reduccion
                ).desc()
            )

            .limit(10)

            .all()

        )
        

         # =====================================================
        # JSON
        # =====================================================

        return {

            # =====================================================
            # INFORMACIÃ“N DEL SISTEMA
            # =====================================================

            "unidad": unidad_actual,

            "fecha": (
                ultima_fecha_operacional.strftime("%d/%m/%Y")
                if ultima_fecha_operacional
                else "--"
            ),

            "ultima_importacion": (
                ultima_importacion.strftime("%d/%m/%Y %H:%M")
                if ultima_importacion
                else "--"
            ),

            "general": {

                "expediciones": total_expediciones,

                "registros": total_registros,

                "buses": total_buses,

                "velocidad_real": round(
                    velocidad_real,
                    2
                ),

                "velocidad_teorica": round(
                    velocidad_teorica,
                    2
                ),

                "reduccion": round(
                    reduccion,
                    2
                )

            },

            "clasificacion": {

                "ok": total_ok,

                "simple": total_simple,

                "complejo": total_complejo,

                "sin_velocidad": total_sin_velocidad

            },

            "estado": {

                "pendientes": total_pendientes,

                "informados": total_informados

            },

            "ip": {

                "expediciones": ip_expediciones,

                "ok": ip_ok,

                "simples": ip_simple,

                "complejos": ip_complejo,

                "eventos": ip_eventos

            },

            "ie": {

                "expediciones": ie_expediciones,

                "ok": ie_ok,

                "simples": ie_simple,

                "complejos": ie_complejo,

                "eventos": ie_eventos

            },

            # =====================================================
            # EVENTOS PRIORITARIOS A INFORMAR
            # =====================================================

            "prioritarios": [
                serializar_prioritario(evento)
                for evento in prioritarios
            ],

            # =====================================================
            # CENTRO DE ALERTAS
            # =====================================================

            "alertas": {

                "servicio_critico":
                    evento_critico.servicio
                    if evento_critico else "--",

                "ruta_critica":
                    evento_critico.ruta
                    if evento_critico else "--",

                "sentido":
                    evento_critico.sentido
                    if evento_critico else "--",

                "periodo_critico":
                    evento_critico.periodo
                    if evento_critico else "--",

                "velocidad_real":
                    round(
                        evento_critico.velocidad_real or 0,
                        2
                    ) if evento_critico else 0,

                "velocidad_teorica":
                    round(
                        evento_critico.velocidad_teorica or 0,
                        2
                    ) if evento_critico else 0,

                "mayor_reduccion":
                    round(
                        evento_critico.porcentaje_reduccion or 0,
                        2
                    ) if evento_critico else 0

            },

            # =====================================================
            # TOP SERVICIOS
            # =====================================================

            "top_servicios": [

                {

                    "servicio": t.servicio,

                    "reduccion": round(
                        t.reduccion or 0,
                        2
                    ),

                    "velocidad_real": round(
                        t.velocidad_real or 0,
                        2
                    ),

                    "velocidad_teorica": round(
                        t.velocidad_teorica or 0,
                        2
                    ),

                    "eventos": t.eventos

                }

                for t in top_servicios

            ],

            # =====================================================
            # REDUCCIÃ“N POR PERÃODO
            # =====================================================

            "periodos": [

                {

                    "periodo": p.periodo,

                    "reduccion": round(
                        p.reduccion or 0,
                        2
                    ),

                    "eventos": p.eventos

                }

                for p in reduccion_periodos

            ],

            # =====================================================
            # COMPARACIÃ“N DE VELOCIDADES
            # =====================================================

            "comparacion_velocidades": [

                {

                    "servicio": v.servicio,

                    "velocidad_real": round(
                        v.velocidad_real or 0,
                        2
                    ),

                    "velocidad_teorica": round(
                        v.velocidad_teorica or 0,
                        2
                    ),

                    "reduccion": round(
                        v.reduccion or 0,
                        2
                    )

                }

                for v in comparacion_velocidades

            ],

            # =====================================================
            # REGISTRO OPERACIONAL
            # =====================================================

            "registros": [

                {

                    "id": r.id,

                    "servicio": r.servicio,

                    "codigo_ts": r.codigo_ts,

                    "ruta": r.ruta,

                    "sentido": r.sentido,

                    "periodo": r.periodo,

                    "expediciones": r.expediciones,

                    "buses": r.buses,

                    "velocidad_real": round(
                        r.velocidad_real or 0,
                        2
                    ),

                    "velocidad_teorica": round(
                        r.velocidad_teorica or 0,
                        2
                    ),

                    "reduccion": round(
                        r.porcentaje_reduccion or 0,
                        2
                    ),

                    "clasificacion": r.clasificacion,

                    "estado": r.estado,

                    "informar": r.informar,

                    "observacion": r.observacion

                }

                for r in (

                    db.query(HistoricoRegistro)

                    .filter(
                        filtro_fecha,
                        HistoricoRegistro.clasificacion != "OK"
                    )

                    .order_by(
                        HistoricoRegistro.porcentaje_reduccion.desc()
                    )

                    .limit(100)

                    .all()

                )

            ]

        }

    finally:

        db.close()
        




