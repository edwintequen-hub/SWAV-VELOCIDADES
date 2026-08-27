"""
=========================================================
SWAV
Servicio Matriz Operacional
=========================================================
"""

from collections import defaultdict
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models import HistoricoRegistro
from app.models import HistoricoPPU
from app.models import Expedicion


def _hora_a_minutos(valor):
    """
    Convierte HH:MM:SS / HH:MM a minutos desde medianoche.
    """

    if valor is None:
        return None

    texto = str(valor).strip()

    if not texto:
        return None

    try:
        partes = texto.split(":")

        hora = int(partes[0])
        minuto = int(partes[1])

        return hora * 60 + minuto

    except Exception:
        return None


def _datetime_a_minutos(valor):
    """
    Obtiene HH:MM desde un datetime/string.
    """

    if valor is None:
        return None

    texto = str(valor).strip()

    if not texto:
        return None

    formatos = (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
    )

    for formato in formatos:

        try:

            fecha = datetime.strptime(texto, formato)

            return fecha.hour * 60 + fecha.minute

        except Exception:
            pass

    return None


def _diferencia_circular_minutos(inicio, objetivo):
    """
    Diferencia horaria considerando cruce de medianoche.
    """

    if inicio is None or objetivo is None:
        return None

    diferencia = objetivo - inicio

    if diferencia < -720:
        diferencia += 1440

    elif diferencia > 720:
        diferencia -= 1440

    return abs(diferencia)


def _obtener_ppu_periodo(
    db,
    reg
):
    """
    Obtiene exclusivamente desde HistoricoPPU las PPU
    certificadas que formaron el HistoricoRegistro.

    No lee R1.6.
    No reconstruye expediciones.
    No recalcula el resumen del periodo.
    """

    ppus = (
        db.query(HistoricoPPU)
        .filter(
            HistoricoPPU.historico_id == reg.id,
            HistoricoPPU.velocidad_real.isnot(None),
            HistoricoPPU.velocidad_real > 0,
        )
        .order_by(
            HistoricoPPU.inicio_servicio
        )
        .all()
    )

    resultado = []

    for ppu in ppus:

        resultado.append(
            {
                "patente": ppu.patente,
                "servicio_empresa": ppu.ruta,
                "velocidad_real": (
                    round(ppu.velocidad_real, 2)
                    if ppu.velocidad_real is not None
                    else None
                ),
                "velocidad_teorica": (
                    round(ppu.velocidad_teorica, 2)
                    if ppu.velocidad_teorica is not None
                    else None
                ),
                "reduccion": (
                    round(ppu.porcentaje_reduccion, 2)
                    if ppu.porcentaje_reduccion is not None
                    else None
                ),
                "estado": (
                    ppu.clasificacion
                    or "OK"
                ),
                "indicador": (
                    ppu.indicador_tiempo_espera
                ),
                "inicio_servicio": (
                    ppu.inicio_servicio.strftime(
                        "%d/%m/%Y %H:%M:%S"
                    )
                    if ppu.inicio_servicio
                    else None
                ),
                "fin_servicio": (
                    ppu.fin_servicio.strftime(
                        "%d/%m/%Y %H:%M:%S"
                    )
                    if ppu.fin_servicio
                    else None
                ),
                "franja_horaria": (
                    ppu.franja_horaria
                ),
                "origen": "BD",
            }
        )

    return resultado


def obtener_matriz(
    unidad="",
    tipo_dia="",
    estado="Todos",
    servicio_usuario="",
    servicio_empresa="",
    fecha_desde="",
    fecha_hasta=""
):

    db = SessionLocal()

    try:

        consulta = db.query(
            HistoricoRegistro
        )

        # ----------------------------------------
        # MATRIZ = REPORTE DEL ULTIMO DIA
        # ----------------------------------------
        #
        # Si no se solicita explicitamente un
        # rango historico, la matriz muestra
        # solamente la fecha operacional mas
        # reciente disponible en la BD.
        #
        # Los filtros fecha_desde / fecha_hasta
        # se conservan para reportes historicos.
        # ----------------------------------------

        if not fecha_desde and not fecha_hasta:

            ultima_fecha = (
                db.query(
                    HistoricoRegistro.fecha_operacional
                )
                .order_by(
                    HistoricoRegistro.fecha_operacional.desc()
                )
                .first()
            )

            if (
                ultima_fecha
                and ultima_fecha[0]
            ):

                consulta = consulta.filter(
                    HistoricoRegistro.fecha_operacional
                    == ultima_fecha[0]
                )

        # ----------------------------------------
        # Unidad
        # ----------------------------------------

        if unidad:

            consulta = consulta.filter(
                HistoricoRegistro.unidad == unidad
            )

        # ----------------------------------------
        # Tipo Día
        # ----------------------------------------

        if tipo_dia:

            consulta = consulta.filter(
                HistoricoRegistro.tipo_dia == tipo_dia
            )

        # ----------------------------------------
        # Servicio Usuario
        # ----------------------------------------

        if servicio_usuario:

            consulta = consulta.filter(
                HistoricoRegistro.servicio
                == servicio_usuario
            )

        # ----------------------------------------
        # Servicio Empresa
        # ----------------------------------------

        if servicio_empresa:

            consulta = consulta.filter(
                HistoricoRegistro.ruta
                == servicio_empresa
            )

        # ----------------------------------------
        # Fecha operacional
        # ----------------------------------------

        if fecha_desde:

            try:

                fecha_desde_dt = (
                    datetime.strptime(
                        str(fecha_desde).strip(),
                        "%Y-%m-%d"
                    ).date()
                )

                consulta = consulta.filter(
                    HistoricoRegistro.fecha_operacional
                    >= fecha_desde_dt
                )

            except ValueError:

                raise ValueError(
                    "fecha_desde debe usar formato YYYY-MM-DD"
                )

        if fecha_hasta:

            try:

                fecha_hasta_dt = (
                    datetime.strptime(
                        str(fecha_hasta).strip(),
                        "%Y-%m-%d"
                    ).date()
                )

                consulta = consulta.filter(
                    HistoricoRegistro.fecha_operacional
                    <= fecha_hasta_dt
                )

            except ValueError:

                raise ValueError(
                    "fecha_hasta debe usar formato YYYY-MM-DD"
                )

        if (
            fecha_desde
            and fecha_hasta
            and fecha_desde_dt > fecha_hasta_dt
        ):

            raise ValueError(
                "fecha_desde no puede ser mayor que fecha_hasta"
            )

        # ----------------------------------------
        # Nunca mostrar SIN VELOCIDAD
        # ----------------------------------------

        consulta = consulta.filter(
            HistoricoRegistro.clasificacion
            != "SIN VELOCIDAD"
        )

        # ----------------------------------------
        # Estado
        # ----------------------------------------

        if estado == "Normal":

            consulta = consulta.filter(
                HistoricoRegistro.clasificacion
                == "OK"
            )

        elif estado == "Simple":

            consulta = consulta.filter(
                HistoricoRegistro.clasificacion
                == "SIMPLE"
            )

        elif estado == "Complejo":

            consulta = consulta.filter(
                HistoricoRegistro.clasificacion
                == "COMPLEJO"
            )

        print("=" * 80)
        print(
            "ESTADO:",
            repr(estado)
        )
        print(
            "REGISTROS:",
            consulta.count()
        )
        print("=" * 80)

        registros = consulta.all()

        matriz = defaultdict(dict)

        # =====================================================
        # PROCESAR REGISTROS HISTÓRICOS
        # =====================================================

        for reg in registros:

            llave = (
                reg.unidad,
                reg.tipo_dia,
                reg.servicio,
                reg.ruta
            )

            # =================================================
            # PPU CERTIFICADAS DESDE HISTORICO_PPU
            # =================================================

            ppu_periodo = _obtener_ppu_periodo(
                db,
                reg
            )

            # =================================================
            # RESUMEN CERTIFICADO DESDE HISTORICO_REGISTRO
            # =================================================
            #
            # HistoricoRegistro es la fuente oficial del
            # resultado consolidado del periodo.
            #
            # HistoricoPPU se utiliza exclusivamente para
            # mostrar el detalle de las expediciones.
            #
            # NO recalcular aqui:
            #   - expediciones
            #   - velocidad real
            #   - velocidad teorica
            #   - reduccion
            #   - clasificacion
            # =================================================

            expediciones_periodo = reg.expediciones

            velocidad_real_periodo = (
                round(reg.velocidad_real, 2)
                if reg.velocidad_real is not None
                else None
            )

            velocidad_teorica_periodo = (
                round(reg.velocidad_teorica, 2)
                if reg.velocidad_teorica is not None
                else None
            )

            reduccion_periodo = (
                round(reg.porcentaje_reduccion, 2)
                if reg.porcentaje_reduccion is not None
                else None
            )

            # =================================================
            # PRIORIDAD OPERACIONAL DE LA MATRIZ
            # =================================================
            #
            # La celda debe representar el evento mas critico
            # encontrado entre las PPU del periodo:
            #
            # COMPLEJO > SIMPLE > OK
            #
            # Los valores consolidados del HistoricoRegistro
            # se conservan para velocidad, reduccion y expediciones.
            # Solo la clasificacion visual de la matriz se obtiene
            # desde las PPU certificadas del periodo.
            # =================================================

            estados_ppu = {
                str(
                    ppu.get(
                        "estado",
                        "OK"
                    )
                    or "OK"
                )
                .strip()
                .upper()
                for ppu in ppu_periodo
            }

            if "COMPLEJO" in estados_ppu:

                clasificacion_periodo = (
                    "COMPLEJO"
                )

            elif "SIMPLE" in estados_ppu:

                clasificacion_periodo = (
                    "SIMPLE"
                )

            else:

                clasificacion_periodo = (
                    "OK"
                )

            # GUARDAR PERÍODO
            # =================================================

            matriz[llave][reg.periodo] = {

                "reduccion": (
                    reduccion_periodo
                ),

                "clasificacion": (
                    clasificacion_periodo
                ),

                "indicador": (
                    reg.indicador_tiempo_espera
                ),

                "velocidad_real": (
                    velocidad_real_periodo
                ),

                "velocidad_teorica": (
                    reg.velocidad_teorica
                ),

                "expediciones": (
                    expediciones_periodo
                ),

                "ppu": ppu_periodo
            }

        # =====================================================
        # CONSTRUIR SALIDA
        # =====================================================

        salida = []

        for llave, periodos in matriz.items():

            salida.append(
                {

                    "unidad": llave[0],

                    "tipo_dia": llave[1],

                    "servicio_usuario": llave[2],

                    "servicio_empresa": llave[3],

                    "periodos": periodos

                }
            )

        return salida

    finally:

        db.close()



