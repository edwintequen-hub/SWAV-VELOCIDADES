from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    FlotaAsignacionTerminal,
    FlotaPPUDeteccion,
    FlotaPPUDeteccionServicio,
    FlotaPPUValidacion,
    HistoricoFlotaOperativa,
    HistoricoFlotaOperativaServicio,
    Servicio,
)


CLASIFICACIONES_PROPIAS = {
    "BUS_NUEVO_PROPIO",
    "MOVIMIENTO_INTERNO",
}


def normalizar_ppu(valor: Any) -> str:
    """
    PPU canonica:
    mayusculas, sin guiones ni espacios.
    """

    return (
        str(valor or "")
        .strip()
        .upper()
        .replace("-", "")
        .replace(" ", "")
    )


def normalizar_ts_observado(
    valor: Any,
) -> str:
    """
    Normalizacion certificada para intentar
    resolver el TS observado contra Servicio.

    Ejemplos:
        T963 E0 -> 963E
        T930 C0 -> 930C
        T932    -> 932

    Si el resultado no existe de forma unica
    en el catalogo, NO se inventa equivalencia.
    """

    texto = (
        str(valor or "")
        .strip()
        .upper()
    )

    texto = re.sub(
        r"\s+",
        "",
        texto,
    )

    if texto.startswith("T"):
        texto = texto[1:]

    texto = re.sub(
        r"([A-Z])\d+$",
        r"\1",
        texto,
    )

    return texto


def _version_catalogo_actual(
    db: Session,
):
    return (
        db.query(
            FlotaAsignacionTerminal.version
        )
        .filter(
            FlotaAsignacionTerminal.activo.is_(True)
        )
        .order_by(
            FlotaAsignacionTerminal.fecha_importacion.desc()
        )
        .limit(1)
        .scalar()
    )


def obtener_ppus_propias_reconocidas(
    db: Session,
) -> set[str]:

    version = _version_catalogo_actual(
        db
    )

    catalogadas: set[str] = set()

    if version:

        filas = (
            db.query(
                FlotaAsignacionTerminal
            )
            .filter(
                FlotaAsignacionTerminal.version
                == version,

                FlotaAsignacionTerminal.activo.is_(True),
            )
            .all()
        )

        catalogadas = {
            normalizar_ppu(fila.ppu)
            for fila in filas
            if normalizar_ppu(fila.ppu)
        }

    validadas = (
        db.query(
            FlotaPPUValidacion
        )
        .filter(
            FlotaPPUValidacion.estado
            == "VALIDADO",

            FlotaPPUValidacion.clasificacion_final.in_(
                CLASIFICACIONES_PROPIAS
            ),
        )
        .all()
    )

    propias_validadas = {
        normalizar_ppu(fila.ppu)
        for fila in validadas
        if normalizar_ppu(fila.ppu)
    }

    return (
        catalogadas
        |
        propias_validadas
    )


def construir_catalogo_ts(
    db: Session,
) -> dict[str, list[Servicio]]:

    catalogo: dict[
        str,
        list[Servicio],
    ] = defaultdict(list)

    filas = (
        db.query(
            Servicio
        )
        .all()
    )

    for fila in filas:

        codigo = (
            str(fila.codigo_ts or "")
            .strip()
            .upper()
        )

        if codigo:
            catalogo[codigo].append(
                fila
            )

    return dict(catalogo)


def resolver_servicio_cliente(
    codigo_ts_observado: Any,
    catalogo_ts: dict[
        str,
        list[Servicio],
    ],
) -> dict[str, Any]:

    normalizado = normalizar_ts_observado(
        codigo_ts_observado
    )

    coincidencias = catalogo_ts.get(
        normalizado,
        [],
    )

    if len(coincidencias) != 1:

        return {
            "codigo_ts_catalogo":
                normalizado or None,

            "servicio_cliente":
                None,

            "unidad_catalogo":
                None,

            "terminal_catalogo":
                None,

            "resuelto":
                False,
        }

    fila = coincidencias[0]

    return {
        "codigo_ts_catalogo":
            normalizado,

        "servicio_cliente":
            fila.servicio,

        "unidad_catalogo":
            fila.unidad,

        "terminal_catalogo":
            fila.terminal,

        "resuelto":
            True,
    }


def detectar_ppu_desde_historico(
    db: Session,
    fecha_desde: date | str | None = None,
    fecha_hasta: date | str | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    """
    Detecta eventos de PPU no reconocidas a partir
    del historico R1.6 ya persistido.

    Modos:
        dry_run=True:
            detecta y devuelve candidatas sin escribir.

        dry_run=False:
            persiste idempotentemente detecciones,
            evidencias TS y maestro de validacion.

    Este servicio NO ejecuta commit().
    El llamador controla commit/rollback.
    """

    propias = (
        obtener_ppus_propias_reconocidas(
            db
        )
    )

    catalogo_ts = construir_catalogo_ts(
        db
    )

    # =====================================================
    # NORMALIZAR FECHAS PARA SQLITE / POSTGRESQL
    # =====================================================
    #
    # PostgreSQL no permite comparar una columna DATE
    # directamente contra VARCHAR. La API historica de esta
    # funcion admite date | str, por lo que normalizamos los
    # textos ISO YYYY-MM-DD a datetime.date antes del filtro.
    # =====================================================

    def normalizar_fecha_filtro(valor):

        if valor is None:
            return None

        if isinstance(valor, datetime):
            return valor.date()

        if isinstance(valor, date):
            return valor

        if isinstance(valor, str):

            valor = valor.strip()

            if not valor:
                return None

            try:
                return datetime.strptime(
                    valor,
                    "%Y-%m-%d",
                ).date()

            except ValueError as exc:
                raise ValueError(
                    "Fecha invalida para detector PPU: "
                    + valor
                    + ". Formato esperado: YYYY-MM-DD."
                ) from exc

        raise TypeError(
            "Tipo de fecha no soportado por detector PPU: "
            + type(valor).__name__
        )

    fecha_desde = normalizar_fecha_filtro(
        fecha_desde
    )

    fecha_hasta = normalizar_fecha_filtro(
        fecha_hasta
    )

    consulta = db.query(
        HistoricoFlotaOperativa
    )

    if fecha_desde is not None:
        consulta = consulta.filter(
            HistoricoFlotaOperativa.fecha
            >= fecha_desde
        )

    if fecha_hasta is not None:
        consulta = consulta.filter(
            HistoricoFlotaOperativa.fecha
            <= fecha_hasta
        )

    eventos = (
        consulta
        .order_by(
            HistoricoFlotaOperativa.fecha,
            HistoricoFlotaOperativa.periodo,
            HistoricoFlotaOperativa.ppu,
        )
        .all()
    )

    candidatas = []

    for evento in eventos:

        ppu_normalizada = normalizar_ppu(
            evento.ppu
        )

        if not ppu_normalizada:
            continue

        if ppu_normalizada in propias:
            continue

        evidencias_db = (
            db.query(
                HistoricoFlotaOperativaServicio
            )
            .filter(
                HistoricoFlotaOperativaServicio.fecha
                == evento.fecha,

                HistoricoFlotaOperativaServicio.periodo
                == evento.periodo,

                HistoricoFlotaOperativaServicio.ppu
                == evento.ppu,
            )
            .order_by(
                HistoricoFlotaOperativaServicio
                .primera_transmision,

                HistoricoFlotaOperativaServicio.servicio,
            )
            .all()
        )

        evidencias = []

        for evidencia in evidencias_db:

            resolucion = (
                resolver_servicio_cliente(
                    evidencia.servicio,
                    catalogo_ts,
                )
            )

            evidencias.append({
                "codigo_ts_observado":
                    evidencia.servicio,

                "codigo_ts_catalogo":
                    resolucion[
                        "codigo_ts_catalogo"
                    ],

                "servicio_cliente":
                    resolucion[
                        "servicio_cliente"
                    ],

                "resuelto":
                    resolucion[
                        "resuelto"
                    ],

                "unidad":
                    evidencia.unidad,

                "terminal":
                    evidencia.terminal,

                "primera_transmision":
                    evidencia.primera_transmision,

                "ultima_transmision":
                    evidencia.ultima_transmision,

                "cantidad_registros_fuente":
                    evidencia.cantidad_registros_fuente,

                "archivo_origen":
                    evidencia.archivo_origen,
            })

        candidatas.append({
            "ppu":
                evento.ppu,

            "ppu_normalizada":
                ppu_normalizada,

            "fecha":
                evento.fecha,

            "periodo":
                evento.periodo,

            "unidad":
                evento.unidad,

            "terminal":
                evento.terminal,

            "primera_transmision":
                evento.primera_transmision,

            "ultima_transmision":
                evento.ultima_transmision,

            "cantidad_registros_fuente":
                evento.cantidad_registros_fuente,

            "archivo_origen":
                evento.archivo_origen,

            "estado_deteccion":
                "POR_VALIDAR",

            "evidencias_ts":
                evidencias,
        })

    persistencia = {
        "detecciones_creadas": 0,
        "detecciones_existentes": 0,
        "evidencias_creadas": 0,
        "evidencias_existentes": 0,
        "maestros_creados": 0,
        "maestros_actualizados": 0,
    }

    if not dry_run:

        for candidata in candidatas:

            deteccion_creada = False

            deteccion = (
                db.query(
                    FlotaPPUDeteccion
                )
                .filter(
                    FlotaPPUDeteccion.fecha
                    == candidata["fecha"],

                    FlotaPPUDeteccion.periodo
                    == candidata["periodo"],

                    FlotaPPUDeteccion.ppu_normalizada
                    == candidata["ppu_normalizada"],
                )
                .one_or_none()
            )

            if deteccion is None:

                deteccion = FlotaPPUDeteccion(
                    ppu=candidata["ppu"],
                    ppu_normalizada=candidata[
                        "ppu_normalizada"
                    ],
                    fecha=candidata["fecha"],
                    periodo=candidata["periodo"],
                    unidad=candidata["unidad"],
                    terminal=candidata["terminal"],
                    servicio=None,
                    codigo_ts=None,
                    primera_transmision=candidata[
                        "primera_transmision"
                    ],
                    ultima_transmision=candidata[
                        "ultima_transmision"
                    ],
                    cantidad_registros_fuente=(
                        candidata[
                            "cantidad_registros_fuente"
                        ]
                        or 0
                    ),
                    archivo_origen=candidata[
                        "archivo_origen"
                    ],
                    carga_hash=None,
                    estado_deteccion="POR_VALIDAR",
                )

                db.add(
                    deteccion
                )
                db.flush()

                persistencia[
                    "detecciones_creadas"
                ] += 1

                deteccion_creada = True

            else:

                persistencia[
                    "detecciones_existentes"
                ] += 1

            for evidencia in candidata[
                "evidencias_ts"
            ]:

                codigo_observado = (
                    str(
                        evidencia[
                            "codigo_ts_observado"
                        ]
                        or ""
                    )
                    .strip()
                )

                if not codigo_observado:
                    continue

                evidencia_existente = (
                    db.query(
                        FlotaPPUDeteccionServicio
                    )
                    .filter(
                        FlotaPPUDeteccionServicio.deteccion_id
                        == deteccion.id,

                        FlotaPPUDeteccionServicio.codigo_ts_observado
                        == codigo_observado,
                    )
                    .one_or_none()
                )

                if evidencia_existente is not None:

                    persistencia[
                        "evidencias_existentes"
                    ] += 1

                    continue

                fila_evidencia = (
                    FlotaPPUDeteccionServicio(
                        deteccion_id=deteccion.id,
                        codigo_ts_observado=(
                            codigo_observado
                        ),
                        servicio_cliente=evidencia[
                            "servicio_cliente"
                        ],
                        unidad=evidencia[
                            "unidad"
                        ],
                        terminal=evidencia[
                            "terminal"
                        ],
                        primera_transmision=evidencia[
                            "primera_transmision"
                        ],
                        ultima_transmision=evidencia[
                            "ultima_transmision"
                        ],
                        cantidad_registros_fuente=(
                            evidencia[
                                "cantidad_registros_fuente"
                            ]
                            or 0
                        ),
                        archivo_origen=evidencia[
                            "archivo_origen"
                        ],
                    )
                )

                db.add(
                    fila_evidencia
                )

                persistencia[
                    "evidencias_creadas"
                ] += 1

            maestro = (
                db.query(
                    FlotaPPUValidacion
                )
                .filter(
                    FlotaPPUValidacion.ppu
                    == candidata[
                        "ppu_normalizada"
                    ]
                )
                .one_or_none()
            )

            if maestro is None:

                primera_evidencia = (
                    candidata[
                        "evidencias_ts"
                    ][0]
                    if candidata[
                        "evidencias_ts"
                    ]
                    else None
                )

                maestro = FlotaPPUValidacion(
                    ppu=candidata[
                        "ppu_normalizada"
                    ],
                    estado="POR_VALIDAR",
                    unidad_primera=candidata[
                        "unidad"
                    ],
                    terminal_primera=candidata[
                        "terminal"
                    ],
                    servicio_primero=(
                        primera_evidencia[
                            "servicio_cliente"
                        ]
                        if primera_evidencia
                        else None
                    ),
                    codigo_ts_primero=(
                        primera_evidencia[
                            "codigo_ts_observado"
                        ]
                        if primera_evidencia
                        else None
                    ),
                    unidad_ultima=candidata[
                        "unidad"
                    ],
                    terminal_ultima=candidata[
                        "terminal"
                    ],
                    servicio_ultimo=(
                        primera_evidencia[
                            "servicio_cliente"
                        ]
                        if primera_evidencia
                        else None
                    ),
                    codigo_ts_ultimo=(
                        primera_evidencia[
                            "codigo_ts_observado"
                        ]
                        if primera_evidencia
                        else None
                    ),
                    primera_deteccion=(
                        candidata[
                            "primera_transmision"
                        ]
                        or candidata["fecha"]
                    ),
                    ultima_deteccion=(
                        candidata[
                            "ultima_transmision"
                        ]
                        or candidata["fecha"]
                    ),
                    cantidad_detecciones=1,
                    clasificacion_final=None,
                    observacion=None,
                    fuente_deteccion="R1.6",
                    fecha_validacion=None,
                )

                db.add(
                    maestro
                )

                persistencia[
                    "maestros_creados"
                ] += 1

            else:

                # La decision humana NO se modifica.
                #
                # Solo actualizamos evidencia operacional
                # cuando este evento es realmente nuevo.
                if deteccion_creada:

                    ultima_evidencia = (
                        candidata[
                            "evidencias_ts"
                        ][-1]
                        if candidata[
                            "evidencias_ts"
                        ]
                        else None
                    )

                    maestro.unidad_ultima = (
                        candidata["unidad"]
                    )

                    maestro.terminal_ultima = (
                        candidata["terminal"]
                    )

                    maestro.servicio_ultimo = (
                        ultima_evidencia[
                            "servicio_cliente"
                        ]
                        if ultima_evidencia
                        else None
                    )

                    maestro.codigo_ts_ultimo = (
                        ultima_evidencia[
                            "codigo_ts_observado"
                        ]
                        if ultima_evidencia
                        else None
                    )

                    maestro.ultima_deteccion = (
                        candidata[
                            "ultima_transmision"
                        ]
                        or candidata["fecha"]
                    )

                    maestro.cantidad_detecciones = (
                        maestro.cantidad_detecciones
                        or 0
                    ) + 1

                    persistencia[
                        "maestros_actualizados"
                    ] += 1

        db.flush()

    return {
        "dry_run":
            dry_run,

        "eventos_analizados":
            len(eventos),

        "ppus_propias_reconocidas":
            len(propias),

        "eventos_candidatos":
            len(candidatas),

        "persistencia":
            persistencia,

        "candidatas":
            candidatas,
    }
