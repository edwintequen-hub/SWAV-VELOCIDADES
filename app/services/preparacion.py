"""
=========================================================
SWAV
HM-003
PREPARACIÃ“N DEL R1.6
=========================================================

Reglas homologadas:

HM-003.1  Calcular duraciÃ³n
HM-003.2  Corregir/normalizar ruta
HM-003.3  Calcular C / NC usando Anexo 4
HM-003.4  Calcular perÃ­odo
HM-003.5  Excluir NC
HM-003.6  Excluir velocidad 0

C / NC:
    duraciÃ³n mÃ¡xima Anexo 4
        -> mÃ¡ximo - (mÃ¡ximo * porcentaje)
        -> tiempo objetivo
        -> duraciÃ³n R1.6 < objetivo => NC
        -> duraciÃ³n R1.6 >= objetivo => C

El porcentaje es configurable por unidad.
Por defecto: 70 %.

La duraciÃ³n mÃ­nima es independiente.
Por defecto: 20 minutos.
=========================================================
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Configuracion
from app.models import Expedicion
from app.models import Periodo
from app.models import Servicio
from app.models import Unidad
from app.catalogos.rutas import RUTAS_CORREGIDAS


class PreparadorR16:

    def __init__(self, db: Session):
        self.db = db

        (
            self.duracion_minima,
            self.porcentaje_cumplimiento,
        ) = self.obtener_configuracion()

    # =====================================================
    # UTILIDADES
    # =====================================================

    @staticmethod
    def normalizar_texto(valor):
        if valor is None:
            return ""
        return str(valor).strip().upper()

    @classmethod
    def normalizar_unidad(cls, unidad):
        return cls.normalizar_texto(unidad)

    @classmethod
    def normalizar_sentido(cls, sentido):
        sentido = cls.normalizar_texto(sentido)

        if sentido in ("I", "IDA"):
            return "IDA"

        if sentido in (
            "R",
            "RET",
            "REGRESO",
            "RETORNO",
        ):
            return "RET"

        return sentido

    @classmethod
    def normalizar_codigo_ts(cls, codigo):
        return cls.normalizar_texto(codigo)

    # =====================================================
    # CONFIGURACIÃ“N
    # =====================================================

    def obtener_configuracion(self):

        configuraciones = (
            self.db.query(Configuracion, Unidad)
            .join(
                Unidad,
                Configuracion.unidad_id == Unidad.id,
            )
            .all()
        )

        if len(configuraciones) == 1:
            config, _unidad = configuraciones[0]

            return (
                config.duracion_minima or 20,
                getattr(
                    config,
                    "porcentaje_cumplimiento",
                    70,
                ) or 70,
            )

        return 20, 70

    def obtener_configuracion_unidad(self, unidad_codigo):

        unidad_codigo = self.normalizar_unidad(
            unidad_codigo
        )

        unidad = (
            self.db.query(Unidad)
            .filter(
                Unidad.codigo == unidad_codigo
            )
            .first()
        )

        if unidad is None:
            return 20, 70

        config = (
            self.db.query(Configuracion)
            .filter(
                Configuracion.unidad_id == unidad.id
            )
            .first()
        )

        if config is None:
            return 20, 70

        duracion_minima = (
            config.duracion_minima
            if config.duracion_minima is not None
            else 20
        )

        porcentaje = getattr(
            config,
            "porcentaje_cumplimiento",
            70,
        )

        if porcentaje is None:
            porcentaje = 70

        return (
            float(duracion_minima),
            float(porcentaje),
        )

    # =====================================================
    # DURACIÃ“N
    # =====================================================

    @staticmethod
    def calcular_duracion(expedicion):

        if expedicion.inicio_servicio is None:
            return None

        if expedicion.fin_servicio is None:
            return None

        inicio = expedicion.inicio_servicio
        fin = expedicion.fin_servicio

        diferencia = fin - inicio

        if diferencia.total_seconds() < 0:
            diferencia += timedelta(days=1)

        return round(
            diferencia.total_seconds() / 60,
            2,
        )

    # =====================================================
    # EN CURSO
    # =====================================================

    @staticmethod
    def esta_en_curso(expedicion):

        if expedicion.fin_servicio is None:
            return True

        return expedicion.fin_servicio.year == 1900

    # =====================================================
    # CORREGIR RUTA
    # =====================================================

    @classmethod
    def corregir_ruta(cls, ruta):

        if not ruta:
            return ""

        ruta = cls.normalizar_texto(ruta)

        return RUTAS_CORREGIDAS.get(
            ruta,
            ruta,
        )

    # =====================================================
    # NORMALIZAR RUTA
    # =====================================================

    @classmethod
    def normalizar_ruta(cls, ruta):

        if not ruta:
            return ""

        ruta = cls.normalizar_texto(ruta)

        partes = ruta.split()

        if len(partes) != 2:
            return ruta

        codigo = partes[0]
        sentido = partes[1][-1]

        if sentido == "I":
            return f"{codigo} 00I"

        if sentido == "R":
            return f"{codigo} 00R"

        return ruta

    # =====================================================
    # RESOLVER CÃ“DIGO TS
    # =====================================================

    def resolver_codigo_ts(self, expedicion):

        codigo_actual = self.normalizar_codigo_ts(
            expedicion.codigo_ts
        )

        if codigo_actual:
            return codigo_actual

        ruta = self.normalizar_texto(
            expedicion.ruta_normalizada
        )

        if not ruta:
            return ""

        servicios = (
            self.db.query(Servicio)
            .filter(
                Servicio.unidad
                == self.normalizar_unidad(
                    expedicion.unidad
                )
            )
            .all()
        )

        for servicio in servicios:

            ruta_ida = self.normalizar_texto(
                getattr(
                    servicio,
                    "ruta_ida",
                    "",
                )
            )

            ruta_regreso = self.normalizar_texto(
                getattr(
                    servicio,
                    "ruta_regreso",
                    "",
                )
            )

            if ruta in (
                ruta_ida,
                ruta_regreso,
            ):

                codigo = self.normalizar_codigo_ts(
                    servicio.codigo_ts
                )

                expedicion.codigo_ts = codigo

                return codigo

        return ""

    # =====================================================
    # BUSCAR SERVICIO EN INFO
    # =====================================================

    def buscar_servicio_info(self, expedicion):
        """
        INFO es la fuente maestra.

        Busca primero coincidencia exacta.

        Si la ruta de R1.6 no coincide exactamente,
        se intenta homologar usando:

            unidad
            servicio usuario
            cÃ³digo base
            sentido

        Ejemplo:

            R1.6 : T808 03R
            INFO : T808 00R

        Resultado:

            T808 00R
            CÃ³digo TS 808
            Sentido RET
        """

        unidad = self.normalizar_unidad(
            expedicion.unidad
        )

        servicio_usuario = self.normalizar_texto(
            expedicion.servicio
        )

        ruta_r16 = self.normalizar_texto(
            expedicion.ruta
        )

        if not unidad or not servicio_usuario:
            return None

        servicios = (
            self.db.query(Servicio)
            .filter(
                Servicio.unidad == unidad,
                Servicio.servicio == servicio_usuario,
            )
            .all()
        )

        if not servicios:
            return None

        # -------------------------------------------------
        # 1. COINCIDENCIA EXACTA
        # -------------------------------------------------

        for servicio in servicios:

            ruta_ida = self.normalizar_texto(
                getattr(
                    servicio,
                    "ruta_ida",
                    "",
                )
            )

            ruta_regreso = self.normalizar_texto(
                getattr(
                    servicio,
                    "ruta_regreso",
                    "",
                )
            )

            if ruta_r16 in (
                ruta_ida,
                ruta_regreso,
            ):
                return servicio

        # -------------------------------------------------
        # 2. HOMOLOGACIÃ“N POR CÃ“DIGO + SENTIDO
        #
        # T808 03R -> T808 00R
        # -------------------------------------------------

        partes = ruta_r16.split()

        if len(partes) < 2:
            return None

        codigo_base = partes[0]
        ultimo = partes[-1][-1:]

        if ultimo == "I":
            sentido = "IDA"

        elif ultimo == "R":
            sentido = "RET"

        else:
            # FS no se homologa.
            return None

        candidatos = []

        for servicio in servicios:

            if sentido == "IDA":

                ruta_info = self.normalizar_texto(
                    getattr(
                        servicio,
                        "ruta_ida",
                        "",
                    )
                )

            else:

                ruta_info = self.normalizar_texto(
                    getattr(
                        servicio,
                        "ruta_regreso",
                        "",
                    )
                )

            if not ruta_info:
                continue

            partes_info = ruta_info.split()

            if len(partes_info) < 2:
                continue

            if partes_info[0] == codigo_base:
                candidatos.append(servicio)

        # No inventamos si existen varias alternativas.
        if len(candidatos) == 1:
            return candidatos[0]

        return None

        # =====================================================
    # RESOLVER INFO
    # =====================================================

    def resolver_info(self, expedicion):
        """
        Devuelve:

            servicio_info
            ruta_oficial
            codigo_ts
            sentido

        INFO es la fuente de verdad para la homologaciÃ³n.
        """

        servicio_info = self.buscar_servicio_info(
            expedicion
        )

        if servicio_info is None:
            return None, "", "", ""

        ruta_ida = self.normalizar_texto(
            getattr(
                servicio_info,
                "ruta_ida",
                "",
            )
        )

        ruta_regreso = self.normalizar_texto(
            getattr(
                servicio_info,
                "ruta_regreso",
                "",
            )
        )

        ruta_r16 = self.normalizar_texto(
            expedicion.ruta
        )

        sentido = ""
        ruta_oficial = ""

        # -------------------------------------------------
        # COINCIDENCIA EXACTA
        # -------------------------------------------------

        if ruta_r16 == ruta_ida:

            sentido = "IDA"
            ruta_oficial = ruta_ida

        elif ruta_r16 == ruta_regreso:

            sentido = "RET"
            ruta_oficial = ruta_regreso

        else:

            # -------------------------------------------------
            # HOMOLOGACIÃ“N DE VARIANTE
            #
            # Ejemplo:
            #
            # R1.6 : T808 03R
            # INFO : T808 00R
            #
            # Resultado:
            #
            # T808 00R
            # RET
            # -------------------------------------------------

            partes = ruta_r16.split()

            if len(partes) >= 2:

                ultimo = partes[-1][-1:]

                if ultimo == "I":

                    sentido = "IDA"
                    ruta_oficial = ruta_ida

                elif ultimo == "R":

                    sentido = "RET"
                    ruta_oficial = ruta_regreso

        codigo_ts = self.normalizar_codigo_ts(
            servicio_info.codigo_ts
        )

        if (
            not codigo_ts
            or sentido not in ("IDA", "RET")
            or not ruta_oficial
        ):
            return None, "", "", ""

        return (
            servicio_info,
            ruta_oficial,
            codigo_ts,
            sentido,
        )

    # =====================================================
    # RESOLVER SENTIDO
    # =====================================================

    def resolver_sentido(self, expedicion):

        sentido = self.normalizar_sentido(
            expedicion.sentido
        )

        if sentido in (
            "IDA",
            "RET",
        ):

            expedicion.sentido = sentido

            return sentido

        ruta = self.normalizar_texto(
            expedicion.ruta_normalizada
        )

        if ruta.endswith("I"):

            sentido = "IDA"

        elif ruta.endswith("R"):

            sentido = "RET"

        else:

            # FS u otro sentido no vÃ¡lido.
            sentido = ""

        expedicion.sentido = sentido

        return sentido

    # =====================================================
    # DURACIÃ“N MÃXIMA ANEXO 4
    # =====================================================

    def obtener_duracion_maxima_anexo4(
        self,
        unidad,
        codigo_ts,
        sentido,
    ):

        unidad = self.normalizar_unidad(
            unidad
        )

        codigo_ts = self.normalizar_codigo_ts(
            codigo_ts
        )

        sentido = self.normalizar_sentido(
            sentido
        )

        # -------------------------------------------------
        # SOLO IDA / RET
        #
        # FS nunca participa.
        # -------------------------------------------------

        if (
            not unidad
            or not codigo_ts
            or sentido not in (
                "IDA",
                "RET",
            )
        ):
            return None

        periodos = (
            self.db.query(Periodo)
            .filter(
                Periodo.unidad == unidad,
                Periodo.codigo_ts == codigo_ts,
            )
            .all()
        )

        duraciones = []

        for periodo in periodos:

            sentido_periodo = (
                self.normalizar_sentido(
                    periodo.sentido
                )
            )

            # -------------------------------------------------
            # FS NO PARTICIPA
            # -------------------------------------------------

            if sentido_periodo not in (
                "IDA",
                "RET",
            ):
                continue

            if sentido_periodo != sentido:
                continue

            if periodo.duracion is None:
                continue

            try:

                duracion = float(
                    periodo.duracion
                )

            except (
                TypeError,
                ValueError,
            ):

                continue

            if duracion > 0:

                duraciones.append(
                    duracion
                )

        if not duraciones:
            return None

        return max(
            duraciones
        )

    # =====================================================
    # TIEMPO OBJETIVO C / NC
    # =====================================================

    def calcular_tiempo_objetivo(
        self,
        duracion_maxima,
        porcentaje,
    ):

        if duracion_maxima is None:
            return None

        porcentaje = float(
            porcentaje
        )

        if porcentaje < 0:
            porcentaje = 0

        if porcentaje > 100:
            porcentaje = 100

        # -------------------------------------------------
        # Ejemplo:
        #
        # MÃ¡ximo = 141 minutos
        # Cumplimiento = 70 %
        #
        # 141 - (141 * 70 / 100)
        # = 42.30 minutos
        # = 00:42:18
        # -------------------------------------------------

        tiempo_objetivo = (
            duracion_maxima
            - (
                duracion_maxima
                * porcentaje
                / 100
            )
        )

        return round(
            tiempo_objetivo,
            2,
        )

    # =====================================================
    # CALCULAR C / NC
    # =====================================================

    def calcular_cumplimiento(
        self,
        expedicion,
    ):

        # -------------------------------------------------
        # INFO debe resolver primero el CÃ³digo TS.
        # -------------------------------------------------

        (
            servicio_info,
            ruta_oficial,
            codigo_ts_info,
            sentido_info,
        ) = self.resolver_info(
            expedicion
        )

        if servicio_info is not None:

            expedicion.codigo_ts = (
                codigo_ts_info
            )

            expedicion.sentido = (
                sentido_info
            )

            expedicion.ruta_normalizada = (
                ruta_oficial
            )

        else:

            codigo_ts_info = (
                self.resolver_codigo_ts(
                    expedicion
                )
            )

            sentido_info = (
                self.resolver_sentido(
                    expedicion
                )
            )

        codigo_ts = self.normalizar_codigo_ts(
            expedicion.codigo_ts
            or codigo_ts_info
        )

        sentido = self.normalizar_sentido(
            expedicion.sentido
            or sentido_info
        )

        if (
            not codigo_ts
            or sentido not in (
                "IDA",
                "RET",
            )
        ):

            return {
                "cumplimiento": None,
                "duracion_maxima": None,
                "tiempo_objetivo": None,
                "observacion": (
                    "No fue posible resolver "
                    "CÃ³digo TS/Sentido"
                ),
            }

        # -------------------------------------------------
        # BUSCAR MÃXIMO EN ANEXO 4
        # -------------------------------------------------

        duracion_maxima = (
            self.obtener_duracion_maxima_anexo4(
                expedicion.unidad,
                codigo_ts,
                sentido,
            )
        )

        if duracion_maxima is None:

            return {
                "cumplimiento": None,
                "duracion_maxima": None,
                "tiempo_objetivo": None,
                "observacion": (
                    "Tiempo objetivo no encontrado "
                    "en Anexo 4"
                ),
            }

        # -------------------------------------------------
        # CALCULAR OBJETIVO
        # -------------------------------------------------

        tiempo_objetivo = (
            self.calcular_tiempo_objetivo(
                duracion_maxima,
                self.porcentaje_cumplimiento,
            )
        )

        if expedicion.duracion_min is None:

            return {
                "cumplimiento": None,
                "duracion_maxima": (
                    duracion_maxima
                ),
                "tiempo_objetivo": (
                    tiempo_objetivo
                ),
                "observacion": (
                    "No fue posible calcular duraciÃ³n"
                ),
            }

        # -------------------------------------------------
        # C / NC
        # -------------------------------------------------

        if (
            expedicion.duracion_min
            < tiempo_objetivo
        ):

            cumplimiento = "NC"

        else:

            cumplimiento = "C"

        return {
            "cumplimiento": cumplimiento,
            "duracion_maxima": (
                duracion_maxima
            ),
            "tiempo_objetivo": (
                tiempo_objetivo
            ),
            "observacion": "",
        }

    # =====================================================
    # VALIDAR DURACIÃ“N MÃNIMA
    # =====================================================

    def validar_duracion(
        self,
        expedicion,
    ):

        if expedicion.duracion_min is None:

            expedicion.valido = False

            expedicion.observacion = (
                "No fue posible calcular duraciÃ³n"
            )

            return False

        if (
            expedicion.duracion_min
            < self.duracion_minima
        ):

            expedicion.valido = False

            expedicion.observacion = (
                f"DuraciÃ³n menor a "
                f"{self.duracion_minima} minutos"
            )

            return False

        expedicion.valido = True

        return True

    # =====================================================
    # DEPURACIÃ“N
    # =====================================================

    def aplicar_reglas_depuracion(
        self,
        expedicion,
    ):

        # -------------------------------------------------
        # VELOCIDAD REAL INVALIDA
        # -------------------------------------------------
        # Regla SWAV / Macro:
        # una expedicion sin velocidad real valida
        # no participa del analisis.
        #
        # Se eliminan:
        #   None
        #   0
        #   valores negativos
        # -------------------------------------------------

        if (
            expedicion.velocidad_km_h is None
            or expedicion.velocidad_km_h <= 0
        ):

            self.db.delete(
                expedicion
            )

            return True

        # -------------------------------------------------
        # DURACIÃ“N MENOR AL MÃNIMO
        # -------------------------------------------------

        if (
            expedicion.duracion_min
            is not None
            and expedicion.duracion_min
            < self.duracion_minima
        ):

            self.db.delete(
                expedicion
            )

            return True

        # -------------------------------------------------
        # NC
        # -------------------------------------------------

        if (
            self.normalizar_texto(
                expedicion.cumplimiento
            )
            == "NC"
        ):

            self.db.delete(
                expedicion
            )

            return True

        return False

        # =====================================================
    # PREPARAR EXPEDICIÃ“N
    # =====================================================

    def preparar_expedicion(
        self,
        expedicion,
    ):

        # -------------------------------------------------
        # CONFIGURACIÃ“N SEGÃšN UNIDAD
        # -------------------------------------------------

        (
            self.duracion_minima,
            self.porcentaje_cumplimiento,
        ) = self.obtener_configuracion_unidad(
            expedicion.unidad
        )

        # -------------------------------------------------
        # EN CURSO
        # -------------------------------------------------

        if self.esta_en_curso(
            expedicion
        ):

            expedicion.duracion_min = None

            expedicion.procesado = True
            expedicion.valido = False

            expedicion.observacion = (
                "ExpediciÃ³n en curso "
                "(sin hora de tÃ©rmino)"
            )

            expedicion.fecha_procesamiento = (
                datetime.now()
            )

            return

        # -------------------------------------------------
        # HM-003.1
        # CALCULAR DURACIÃ“N
        # -------------------------------------------------

        expedicion.duracion_min = (
            self.calcular_duracion(
                expedicion
            )
        )

        # -------------------------------------------------
        # HM-003.4
        # CALCULAR PERÃODO
        # -------------------------------------------------

        if (
            expedicion.inicio_servicio
            is not None
        ):

            expedicion.periodo = (
                expedicion
                .inicio_servicio
                .hour
                + 1
            )

        else:

            expedicion.periodo = 0

        # -------------------------------------------------
        # FS NO SE REGISTRA
        #
        # MUY IMPORTANTE:
        #
        # Se revisa ANTES de INFO.
        #
        # Si R1.6 trae FS:
        #
        #     FS -> no se registra
        #
        # No se convierte en IDA ni RET.
        # -------------------------------------------------

        sentido_original = (
            self.normalizar_texto(
                expedicion.sentido
            )
        )

        if sentido_original == "FS":

            expedicion.procesado = True
            expedicion.valido = False

            expedicion.observacion = (
                "FS no se registra"
            )

            expedicion.fecha_procesamiento = (
                datetime.now()
            )

            return

        # -------------------------------------------------
        # HM-003.2
        # HOMOLOGACIÃ“N CONTRA INFO
        # -------------------------------------------------

        (
            servicio_info,
            ruta_oficial,
            codigo_ts_info,
            sentido_info,
        ) = self.resolver_info(
            expedicion
        )

        # -------------------------------------------------
        # INFO ENCONTRÃ“ LA HOMOLOGACIÃ“N
        # -------------------------------------------------

        if servicio_info is not None:

            # INFO ES LA FUENTE MAESTRA.

            expedicion.codigo_ts = (
                codigo_ts_info
            )

            expedicion.sentido = (
                sentido_info
            )

            expedicion.ruta_normalizada = (
                ruta_oficial
            )

        # -------------------------------------------------
        # INFO NO ENCONTRÃ“ HOMOLOGACIÃ“N
        # -------------------------------------------------

        else:

            # No inventamos una ruta.
            #
            # Mantenemos el mecanismo anterior
            # como respaldo.

            expedicion.ruta_normalizada = (
                self.corregir_ruta(
                    expedicion.ruta
                )
            )

            self.resolver_codigo_ts(
                expedicion
            )

            self.resolver_sentido(
                expedicion
            )

        # -------------------------------------------------
        # VALIDAR SENTIDO
        # -------------------------------------------------

        sentido_final = (
            self.normalizar_sentido(
                expedicion.sentido
            )
        )

        if sentido_final not in (
            "IDA",
            "RET",
        ):

            expedicion.procesado = True
            expedicion.valido = False

            expedicion.observacion = (
                "Sentido no vÃ¡lido para "
                "procesamiento"
            )

            expedicion.fecha_procesamiento = (
                datetime.now()
            )

            return

        # -------------------------------------------------
        # HM-003.3
        # VALIDAR DURACIÃ“N MÃNIMA
        # -------------------------------------------------

        if not self.validar_duracion(
            expedicion
        ):

            expedicion.procesado = True

            expedicion.fecha_procesamiento = (
                datetime.now()
            )

            return

        # -------------------------------------------------
        # HM-003.3
        # CALCULAR C / NC
        # -------------------------------------------------

        resultado = (
            self.calcular_cumplimiento(
                expedicion
            )
        )

        # -------------------------------------------------
        # GUARDAR RESULTADO C / NC
        # -------------------------------------------------

        if (
            resultado["cumplimiento"]
            is not None
        ):

            expedicion.cumplimiento = (
                resultado[
                    "cumplimiento"
                ]
            )

            expedicion.observacion = ""

            # -------------------------------------------------
            # TRAZA DE PRUEBA
            # -------------------------------------------------

            print(
                "=" * 80
            )

            print(
                "HM-003.3 C / NC"
            )

            print(
                "=" * 80
            )

            print(
                "Unidad             :",
                expedicion.unidad,
            )

            print(
                "Servicio           :",
                expedicion.servicio,
            )

            print(
                "CÃ³digo TS          :",
                expedicion.codigo_ts,
            )

            print(
                "Sentido            :",
                expedicion.sentido,
            )

            print(
                "Ruta               :",
                expedicion.ruta_normalizada,
            )

            print(
                "DuraciÃ³n R1.6      :",
                expedicion.duracion_min,
            )

            print(
                "MÃ¡ximo Anexo 4     :",
                resultado[
                    "duracion_maxima"
                ],
            )

            print(
                "Porcentaje         :",
                self.porcentaje_cumplimiento,
            )

            print(
                "Tiempo objetivo    :",
                resultado[
                    "tiempo_objetivo"
                ],
            )

            print(
                "Cumplimiento       :",
                resultado[
                    "cumplimiento"
                ],
            )

            print(
                "=" * 80
            )

        else:

            expedicion.observacion = (
                resultado[
                    "observacion"
                ]
            )

        # -------------------------------------------------
        # HM-003.5 / HM-003.6
        # APLICAR DEPURACIÃ“N
        # -------------------------------------------------

        eliminado = (
            self.aplicar_reglas_depuracion(
                expedicion
            )
        )

        if eliminado:
            return

        # -------------------------------------------------
        # MARCAR COMO PROCESADO
        # -------------------------------------------------

        expedicion.valido = True

        expedicion.procesado = True

        expedicion.fecha_procesamiento = (
            datetime.now()
        )

    # =====================================================
    # PROCESAR TODAS
    # =====================================================

    def procesar(self):

        expediciones = (
            self.db.query(
                Expedicion
            )
            .filter(
                Expedicion.procesado
                == False
            )
            .all()
        )

        procesadas = 0
        eliminadas = 0

        for expedicion in expediciones:

            # Guardamos el estado antes
            # de aplicar las reglas.

            antes = (
                expedicion in self.db
            )

            self.preparar_expedicion(
                expedicion
            )

            if (
                antes
                and expedicion
                not in self.db
            ):

                eliminadas += 1

            else:

                procesadas += 1

        self.db.commit()

        return {
            "estado": "OK",
            "procesadas": procesadas,
            "eliminadas": eliminadas,
            "duracion_minima": (
                self.duracion_minima
            ),
            "porcentaje_cumplimiento": (
                self.porcentaje_cumplimiento
            ),
        }
