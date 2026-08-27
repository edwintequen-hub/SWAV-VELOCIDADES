"""
=========================================================
SWAV
Motor ComparaciÃ³n
VersiÃ³n 1.0
=========================================================
"""

from sqlalchemy.orm import Session

from app.models import Expedicion
from app.models import Registro
from app.models import Velocidad
from app.models import HistorialImportacion
from app.models import HistoricoRegistro
from app.models import HistoricoPPU
from app.models import HistoricoExpedicion


class MotorComparacion:

    def __init__(self, db: Session):
        self.db = db

    # =====================================================
    # PROCESAR
    # =====================================================

    def procesar(self, unidad=None):

        print("=" * 80)
        print("MOTOR COMPARACION")
        print("=" * 80)

        # =====================================================
        # EXPEDICIONES VALIDAS DE LA UNIDAD SOLICITADA
        # =====================================================

        consulta = (
            self.db.query(Expedicion)
            .filter(
                Expedicion.procesado == True,
                Expedicion.valido == True,
                Expedicion.periodo != None
            )
        )

        if unidad:

            unidad = (
                str(unidad)
                .strip()
                .upper()
            )

            consulta = consulta.filter(
                Expedicion.unidad == unidad
            )

        expediciones = consulta.all()

        print(
            "Unidad procesada          :",
            unidad if unidad else "TODAS"
        )

        print(
            f"Expediciones encontradas : "
            f"{len(expediciones)}"
        )

        # =====================================================
        # REGISTRO ACTUAL
        # SOLO SE REEMPLAZA LA UNIDAD PROCESADA
        # =====================================================

        consulta_registro = (
            self.db.query(Registro)
        )

        if unidad:

            consulta_registro = (
                consulta_registro.filter(
                    Registro.unidad == unidad
                )
            )

        eliminados = (
            consulta_registro.delete(
                synchronize_session=False
            )
        )

        print(
            "Registros actuales "
            "eliminados       :",
            eliminados
        )

        # IMPORTANTE:
        # no hacemos commit aqui.
        # El commit final del motor confirma
        # Registro + HistoricoExpedicion
        # + HistoricoRegistro + HistoricoPPU.

        grupos = self.agrupar_expediciones(
            expediciones
        )

        print(
            f"Grupos encontrados       : "
            f"{len(grupos)}"
        )

        velocidades = self.cargar_velocidades()

        print(
            f"Velocidades cargadas     : "
            f"{len(velocidades)}"
        )

        carga_hash = self.obtener_hash_carga(
            expediciones,
            unidad=unidad
        )

        print(
            "Carga hash               :",
            carga_hash
            if carga_hash
            else "NO DISPONIBLE"
        )

        # =====================================================
        # HISTORIZAR EXPEDICIONES VALIDAS
        # =====================================================

        self.guardar_historico_expediciones(
            expediciones=expediciones,
            velocidades=velocidades,
            carga_hash=carga_hash,
        )

        return self.guardar_registro(
            grupos,
            velocidades,
            carga_hash
        )


    # =====================================================
    # AGRUPAR EXPEDICIONES
    # =====================================================

    def agrupar_expediciones(self, expediciones):

        grupos = {}

        for exp in expediciones:

            # =================================================
            # SEGURIDAD: VELOCIDAD REAL VALIDA
            # =================================================
            # Una expedicion sin velocidad real positiva
            # no participa del Registro ni del Historico.
            # =================================================

            if (
                exp.velocidad_km_h is None
                or exp.velocidad_km_h <= 0
            ):
                continue


             # =================================================
            # AGRUPACION POR RUTA OFICIAL
            # =================================================
            # La ruta original se conserva en cada Expedicion
            # para auditoria, pero NO forma parte de la llave
            # del consolidado.
            #
            # Ejemplo:
            # T841 00I    -> T841 00I
            # T841 C2 00I -> T841 00I
            # T841 02I    -> T841 00I
            #
            # Todas participan del mismo grupo oficial.
            # =================================================

            ruta_oficial = (
                exp.ruta_normalizada
                or exp.ruta
            )

            key = (
                exp.unidad,
                exp.fecha,
                exp.tipo_dia,
                exp.servicio,
                exp.codigo_ts,
                ruta_oficial,
                exp.sentido,
                exp.periodo,
            )

            if key not in grupos:

                grupos[key] = {
                    "unidad": exp.unidad,
                    "empresa": exp.empresa,
                    "fecha_operacional": exp.fecha,
                    "tipo_dia": exp.tipo_dia,
                    "servicio": exp.servicio,
                    "codigo_ts": exp.codigo_ts,
                    "ruta": ruta_oficial,
		    "ruta_normalizada": ruta_oficial,
                    "sentido": exp.sentido,
                    "periodo": exp.periodo,
                    "expediciones": 0,
                    "patentes": set(),
                    "suma_velocidad": 0.0,
                    "detalle_expediciones": [],
                }

            grupos[key]["expediciones"] += 1

            grupos[key]["detalle_expediciones"].append(
                exp
            )

            grupos[key]["patentes"].add(
                exp.patente
            )

            grupos[key]["suma_velocidad"] += (
                exp.velocidad_km_h or 0
            )

        return grupos

    # =====================================================
    # CARGAR VELOCIDADES TEÃ“RICAS
    # =====================================================

    def cargar_velocidades(self):

        velocidades = {}

        datos = (
            self.db.query(Velocidad)
            .all()
        )

        for vel in datos:

            key = (
                str(vel.tipo_dia).strip().upper(),
                str(vel.codigo_ts).strip().upper(),
                str(vel.sentido).strip().upper(),
                int(vel.periodo),
            )

            velocidades[key] = {
                "velocidad": vel.velocidad,
                "indicador": (
                    str(
                        vel.indicador_tiempo_espera
                    ).strip().upper()
                    if vel.indicador_tiempo_espera is not None
                    else None
                ),
            }

        return velocidades

    # =====================================================
    # HISTORICO DE TODAS LAS EXPEDICIONES VALIDAS
    # =====================================================

    def guardar_historico_expediciones(
        self,
        expediciones,
        velocidades,
        carga_hash,
    ):

        if not carga_hash:

            print(
                "ADVERTENCIA: no existe carga_hash. "
                "No se historizan expediciones."
            )

            return 0

        insertadas = 0
        existentes = 0
        analizables = 0
        no_analizables = 0

        motivos = {}

        for exp in expediciones:

            # -------------------------------------------------
            # Seguridad m?nima
            # -------------------------------------------------

            if not exp.patente:
                continue

            if exp.inicio_servicio is None:
                continue

            # -------------------------------------------------
            # Anti-duplicidad
            # -------------------------------------------------

            existente = (
                self.db.query(
                    HistoricoExpedicion.id
                )
                .filter(
                    HistoricoExpedicion.unidad
                    == exp.unidad,

                    HistoricoExpedicion.fecha_operacional
                    == exp.fecha,

                    HistoricoExpedicion.patente
                    == exp.patente,

                    HistoricoExpedicion.inicio_servicio
                    == exp.inicio_servicio,

                    HistoricoExpedicion.ruta
                    == exp.ruta,
                )
                .first()
            )

            if existente:

                existentes += 1
                continue

            # -------------------------------------------------
            # Normalizar Tipo D?a
            # -------------------------------------------------

            tipo_dia = (
                str(exp.tipo_dia or "")
                .strip()
                .upper()
            )

            if tipo_dia == "DIA NORMAL":
                tipo_dia = "LABORAL"

            elif tipo_dia == "DIA SABADO":
                tipo_dia = "SABADO"

            elif tipo_dia == "DIA DOMINGO":
                tipo_dia = "DOMINGO"

            # -------------------------------------------------
            # Normalizar Sentido
            # -------------------------------------------------

            sentido = (
                str(exp.sentido or "")
                .strip()
                .upper()
            )

            if sentido in (
                "I",
                "IDA"
            ):

                sentido = "IDA"

            elif sentido in (
                "R",
                "REGRESO",
                "RET",
                "RETORNO"
            ):

                sentido = "RET"

            # -------------------------------------------------
            # Misma llave usada por MotorComparacion
            # -------------------------------------------------

            key = (
                tipo_dia,
                str(
                    exp.codigo_ts
                ).strip().upper(),
                sentido,
                int(exp.periodo),
            )

            velocidad_data = (
                velocidades.get(key)
            )

            velocidad_teorica = None
            porcentaje = None
            indicador = None
            clasificacion = None
            analizable = False
            motivo = ""

            # -------------------------------------------------
            # SIN LLAVE ANEXO 3
            # -------------------------------------------------

            if not velocidad_data:

                if (
                    exp.observacion
                    and
                    "Tiempo objetivo no encontrado"
                    in exp.observacion
                ):

                    motivo = (
                        "SIN COBERTURA "
                        "ANEXO 3 / ANEXO 4"
                    )

                else:

                    motivo = (
                        "SIN LLAVE ANEXO 3"
                    )

            else:

                indicador = (
                    velocidad_data[
                        "indicador"
                    ]
                )

                velocidad_teorica = (
                    velocidad_data[
                        "velocidad"
                    ]
                    or 0
                )

                # ---------------------------------------------
                # INDICADOR NO ANALIZABLE
                # ---------------------------------------------

                if indicador not in (
                    "IP",
                    "IE"
                ):

                    motivo = (
                        "INDICADOR -- / NO IP-IE"
                    )

                # ---------------------------------------------
                # VELOCIDAD TEORICA INVALIDA
                # ---------------------------------------------

                elif velocidad_teorica <= 0:

                    motivo = (
                        "VELOCIDAD TEORICA 0"
                    )

                # ---------------------------------------------
                # ANALIZABLE
                # ---------------------------------------------

                else:

                    analizable = True

                    porcentaje = (
                        self.calcular_reduccion(
                            exp.velocidad_km_h
                            or 0,
                            velocidad_teorica
                        )
                    )

                    clasificacion = (
                        self.clasificar(
                            porcentaje,
                            indicador
                        )
                    )

            if analizable:

                analizables += 1

            else:

                no_analizables += 1

                motivos[motivo] = (
                    motivos.get(
                        motivo,
                        0
                    )
                    + 1
                )

            # -------------------------------------------------
            # INSERTAR HISTORICO EXPEDICION
            # -------------------------------------------------

            nuevo = HistoricoExpedicion(

                unidad=exp.unidad,

                empresa=exp.empresa,

                fecha_operacional=(
                    exp.fecha
                ),

                tipo_dia=exp.tipo_dia,

                servicio=exp.servicio,

                codigo_bus=exp.codigo_bus,

                patente=exp.patente,

                codigo_ts=exp.codigo_ts,

                ruta=exp.ruta,

                ruta_normalizada=(
                    exp.ruta_normalizada
                ),

                sentido=exp.sentido,

                periodo=exp.periodo,

                inicio_servicio=(
                    exp.inicio_servicio
                ),

                fin_servicio=(
                    exp.fin_servicio
                ),

                franja_horaria=(
                    exp.franja_horaria
                ),

                velocidad_real=(
                    exp.velocidad_km_h
                ),

                velocidad_teorica=(
                    velocidad_teorica
                ),

                porcentaje_reduccion=(
                    porcentaje
                ),

                indicador_tiempo_espera=(
                    indicador
                ),

                analizable=analizable,

                motivo_no_analizable=(
                    motivo
                ),

                clasificacion=(
                    clasificacion
                ),

                archivo_origen=(
                    exp.archivo_origen
                ),

                carga_hash=carga_hash,
            )

            self.db.add(
                nuevo
            )

            insertadas += 1

        print("=" * 80)
        print("HISTORICO EXPEDICIONES")
        print("=" * 80)

        print(
            "Insertadas       :",
            insertadas
        )

        print(
            "Ya existentes    :",
            existentes
        )

        print(
            "Analizables      :",
            analizables
        )

        print(
            "No analizables   :",
            no_analizables
        )

        for motivo, cantidad in sorted(
            motivos.items()
        ):

            print(
                motivo,
                ":",
                cantidad
            )

        print("=" * 80)

        # IMPORTANTE:
        # No hacemos commit aqu?.
        # El commit general del motor confirma
        # HistoricoExpedicion + HistoricoRegistro
        # + HistoricoPPU en la misma operaci?n.

        return insertadas


    # =====================================================
    # GUARDAR REGISTRO
    # =====================================================

    def guardar_registro(
        self,
        grupos,
        velocidades,
        carga_hash,
    ):

        registros = 0

        for grupo in grupos.values():

            if grupo["expediciones"] == 0:
                continue

            # -------------------------------------------------
            # VELOCIDAD REAL
            # -------------------------------------------------

            velocidad_real = round(
                grupo["suma_velocidad"]
                /
                grupo["expediciones"],
                2,
            )

            # -------------------------------------------------
            # NORMALIZAR TIPO DE DÃA
            # -------------------------------------------------

            tipo_dia = (
                str(grupo["tipo_dia"])
                .strip()
                .upper()
            )

            if tipo_dia == "DIA NORMAL":
                tipo_dia = "LABORAL"

            elif tipo_dia == "DIA SABADO":
                tipo_dia = "SABADO"

            elif tipo_dia == "DIA DOMINGO":
                tipo_dia = "DOMINGO"

            # -------------------------------------------------
            # NORMALIZAR SENTIDO
            # -------------------------------------------------

            sentido = (
                str(grupo["sentido"])
                .strip()
                .upper()
            )

            if sentido in ("I", "IDA"):
                sentido = "IDA"

            elif sentido in (
                "R",
                "REGRESO",
                "RET",
                "RETORNO"
            ):
                sentido = "RET"

            # -------------------------------------------------
            # BUSCAR VELOCIDAD TEÃ“RICA
            # -------------------------------------------------

            key = (
                tipo_dia,
                str(
                    grupo["codigo_ts"]
                ).strip().upper(),
                sentido,
                int(grupo["periodo"]),
            )

            velocidad_data = velocidades.get(key)

            if not velocidad_data:
                continue

            # -------------------------------------------------
            # INDICADOR
            # -------------------------------------------------

            indicador = velocidad_data["indicador"]

            # -------------------------------------------------
            # SOLO IP E IE
            # -------------------------------------------------

            if indicador not in ("IP", "IE"):
                continue

            velocidad_teorica = (
                velocidad_data["velocidad"] or 0
            )

            # -------------------------------------------------
            # REDUCCIÃ“N
            # -------------------------------------------------

            porcentaje = self.calcular_reduccion(
                velocidad_real,
                velocidad_teorica,
            )

            # -------------------------------------------------
            # CLASIFICACIÃ“N IP / IE
            # -------------------------------------------------

            if velocidad_teorica <= 0:

                clasificacion = "SIN VELOCIDAD"

            else:

                clasificacion = self.clasificar(
                    porcentaje,
                    indicador
                )

            # -------------------------------------------------
            # SALIDA DE CONTROL
            # -------------------------------------------------

            print("=" * 80)
            print("REGISTRO")
            print("=" * 80)
            print(
                f"Servicio           : "
                f"{grupo['servicio']}"
            )
            print(
                f"CÃ³digo TS          : "
                f"{grupo['codigo_ts']}"
            )
            print(
                f"Ruta               : "
                f"{grupo['ruta_normalizada']}"
            )
            print(
                f"Sentido            : "
                f"{grupo['sentido']}"
            )
            print(
                f"Tipo DÃ­a           : "
                f"{grupo['tipo_dia']}"
            )
            print(
                f"Periodo            : "
                f"{grupo['periodo']}"
            )
            print(
                f"Expediciones       : "
                f"{grupo['expediciones']}"
            )
            print(
                f"Buses              : "
                f"{len(grupo['patentes'])}"
            )
            print(
                f"Velocidad Real     : "
                f"{velocidad_real}"
            )
            print(
                f"Velocidad TeÃ³rica  : "
                f"{velocidad_teorica}"
            )
            print(
                f"Indicador          : "
                f"{indicador}"
            )
            print(
                f"ReducciÃ³n (%)      : "
                f"{porcentaje}"
            )
            print(
                f"ClasificaciÃ³n      : "
                f"{clasificacion}"
            )
            print("=" * 80)

            # -------------------------------------------------
            # CREAR REGISTRO
            # -------------------------------------------------

            nuevo = Registro(

                unidad=grupo["unidad"],

                empresa=grupo["empresa"],

                tipo_dia=grupo["tipo_dia"],

                servicio=grupo["servicio"],

                codigo_ts=grupo["codigo_ts"],

                ruta=grupo["ruta"],

                ruta_normalizada=grupo[
                    "ruta_normalizada"
                ],

                sentido=grupo["sentido"],

                periodo=grupo["periodo"],

                expediciones=grupo[
                    "expediciones"
                ],

                buses=len(
                    grupo["patentes"]
                ),

                velocidad_real=velocidad_real,

                velocidad_teorica=(
                    velocidad_teorica
                ),

                porcentaje_reduccion=(
                    porcentaje
                ),

                indicador_tiempo_espera=(
                    indicador
                ),

                clasificacion=(
                    clasificacion
                ),

                estado="PENDIENTE",

                informar=(
                    clasificacion
                    in (
                        "SIMPLE",
                        "COMPLEJO"
                    )
                ),

                observacion=(
                    "Velocidad teÃ³rica no encontrada"
                    if clasificacion
                    == "SIN VELOCIDAD"
                    else ""
                ),
            )

            self.db.add(nuevo)

            if carga_hash:
                self.guardar_historico(
                    grupo=grupo,
                    velocidad_real=velocidad_real,
                    velocidad_teorica=velocidad_teorica,
                    porcentaje=porcentaje,
                    indicador=indicador,
                    clasificacion=clasificacion,
                    carga_hash=carga_hash,
                )

            registros += 1

        self.db.flush()

        print("=" * 80)
        print("REGISTROS GENERADOS")
        print("=" * 80)
        print(
            f"Total registros : "
            f"{registros}"
        )
        print("=" * 80)

        return registros

    # =====================================================
    # IDENTIDAD DE CARGA R1.6
    # =====================================================

    def obtener_hash_carga(
        self,
        expediciones,
        unidad=None
    ):
        if unidad:
            unidad = str(unidad).strip().upper()

        elif expediciones:
            unidad = expediciones[0].unidad

        else:
            return None

        historial = (
            self.db.query(HistorialImportacion)
            .filter(
                HistorialImportacion.tipo_archivo == "R1.6",
                HistorialImportacion.unidad == unidad,
            )
            .order_by(HistorialImportacion.id.desc())
            .first()
        )

        return (
            historial.carga_hash
            if historial
            else None
        )

    # =====================================================
    # HISTÃ“RICO SIN DUPLICIDAD
    # =====================================================
    # =====================================================
    # HISTORICO SIN DUPLICIDAD
    # UPSERT POR IDENTIDAD OPERACIONAL
    # =====================================================

    def guardar_historico(
        self,
        grupo,
        velocidad_real,
        velocidad_teorica,
        porcentaje,
        indicador,
        clasificacion,
        carga_hash
    ):

        fecha = grupo["fecha_operacional"]

        # =====================================================
        # IDENTIDAD OPERACIONAL DEL CONSOLIDADO
        #
        # carga_hash NO forma parte de la identidad.
        # El hash queda solamente para auditoria.
        # =====================================================

        historico_registro = (
            self.db.query(
                HistoricoRegistro
            )
            .filter(
                HistoricoRegistro.unidad
                == grupo["unidad"],

                HistoricoRegistro.fecha_operacional
                == fecha,

                HistoricoRegistro.tipo_dia
                == grupo["tipo_dia"],

                HistoricoRegistro.servicio
                == grupo["servicio"],

                HistoricoRegistro.codigo_ts
                == grupo["codigo_ts"],

                HistoricoRegistro.ruta
                == grupo["ruta"],

                HistoricoRegistro.ruta_normalizada
                == grupo["ruta_normalizada"],

                HistoricoRegistro.sentido
                == grupo["sentido"],

                HistoricoRegistro.periodo
                == grupo["periodo"],

                HistoricoRegistro.indicador_tiempo_espera
                == indicador,
            )
            .first()
        )

        # =====================================================
        # IDENTIDAD / AUDITORIA DE LA CARGA
        # =====================================================

        historial = (
            self.db.query(
                HistorialImportacion
            )
            .filter(
                HistorialImportacion.tipo_archivo
                == "R1.6",

                HistorialImportacion.unidad
                == grupo["unidad"],

                HistorialImportacion.carga_hash
                == carga_hash,
            )
            .order_by(
                HistorialImportacion.id.desc()
            )
            .first()
        )

        archivo_origen = (
            historial.archivo
            if historial
            else ""
        )

        # =====================================================
        # INSERTAR O ACTUALIZAR CONSOLIDADO
        # =====================================================

        if historico_registro is None:

            historico_registro = HistoricoRegistro(

                unidad=grupo["unidad"],

                empresa=grupo["empresa"],

                fecha_operacional=fecha,

                tipo_dia=grupo["tipo_dia"],

                servicio=grupo["servicio"],

                codigo_ts=grupo["codigo_ts"],

                ruta=grupo["ruta"],

                ruta_normalizada=(
                    grupo["ruta_normalizada"]
                ),

                sentido=grupo["sentido"],

                periodo=grupo["periodo"],

                expediciones=grupo["expediciones"],

                buses=len(
                    grupo["patentes"]
                ),

                velocidad_real=velocidad_real,

                velocidad_teorica=(
                    velocidad_teorica
                ),

                porcentaje_reduccion=(
                    porcentaje
                ),

                indicador_tiempo_espera=(
                    indicador
                ),

                clasificacion=(
                    clasificacion
                ),

                estado="PENDIENTE",

                informar=(
                    clasificacion
                    in (
                        "SIMPLE",
                        "COMPLEJO"
                    )
                ),

                observacion=(
                    ""
                    if clasificacion
                    != "SIN VELOCIDAD"
                    else
                    "Velocidad teorica no encontrada"
                ),

                archivo_origen=(
                    archivo_origen
                ),

                carga_hash=carga_hash,
            )

            self.db.add(
                historico_registro
            )

            self.db.flush()

        else:

            # -------------------------------------------------
            # ACTUALIZAR CONSOLIDADO DEL DIA
            # CON LA CARGA ACUMULATIVA MAS RECIENTE
            # -------------------------------------------------

            historico_registro.empresa = (
                grupo["empresa"]
            )

            historico_registro.expediciones = (
                grupo["expediciones"]
            )

            historico_registro.buses = len(
                grupo["patentes"]
            )

            historico_registro.velocidad_real = (
                velocidad_real
            )

            historico_registro.velocidad_teorica = (
                velocidad_teorica
            )

            historico_registro.porcentaje_reduccion = (
                porcentaje
            )

            historico_registro.clasificacion = (
                clasificacion
            )

            historico_registro.estado = (
                "PENDIENTE"
            )

            historico_registro.informar = (
                clasificacion
                in (
                    "SIMPLE",
                    "COMPLEJO"
                )
            )

            historico_registro.observacion = (
                ""
                if clasificacion
                != "SIN VELOCIDAD"
                else
                "Velocidad teorica no encontrada"
            )

            historico_registro.archivo_origen = (
                archivo_origen
            )

            historico_registro.carga_hash = (
                carga_hash
            )

            self.db.flush()

        # =====================================================
        # PPU DEL GRUPO
        # =====================================================

        detalle = grupo.get(
            "detalle_expediciones",
            []
        )

        ppu_insertadas = 0
        ppu_existentes = 0

        for exp in detalle:

            if not exp.patente:
                continue

            if exp.inicio_servicio is None:
                continue

            if (
                exp.velocidad_km_h is None
                or exp.velocidad_km_h <= 0
            ):
                continue

            # -------------------------------------------------
            # ANTI-DUPLICIDAD PPU
            # -------------------------------------------------

            ppu_existente = (
                self.db.query(
                    HistoricoPPU.id
                )
                .filter(
                    HistoricoPPU.historico_id
                    == historico_registro.id,

                    HistoricoPPU.patente
                    == exp.patente,

                    HistoricoPPU.inicio_servicio
                    == exp.inicio_servicio,

                    HistoricoPPU.ruta
                    == exp.ruta,
                )
                .first()
            )

            if ppu_existente:

                ppu_existentes += 1
                continue

            velocidad_ppu = (
                exp.velocidad_km_h
            )

            # -------------------------------------------------
            # REDUCCION Y CLASIFICACION INDIVIDUAL
            # MISMO MOTOR OFICIAL
            # -------------------------------------------------

            if (
                velocidad_teorica
                is not None
                and velocidad_teorica > 0
            ):

                reduccion_ppu = (
                    self.calcular_reduccion(
                        velocidad_ppu,
                        velocidad_teorica
                    )
                )

                clasificacion_ppu = (
                    self.clasificar(
                        reduccion_ppu,
                        indicador
                    )
                )

            else:

                reduccion_ppu = 0

                clasificacion_ppu = (
                    "SIN VELOCIDAD"
                )

            # -------------------------------------------------
            # CREAR PPU NUEVA
            # -------------------------------------------------

            historico_ppu = HistoricoPPU(

                historico_id=(
                    historico_registro.id
                ),

                unidad=grupo["unidad"],

                fecha_operacional=fecha,

                tipo_dia=grupo["tipo_dia"],

                servicio=exp.servicio,

                codigo_ts=exp.codigo_ts,

                ruta=exp.ruta,

                ruta_normalizada=(
                    exp.ruta_normalizada
                ),

                sentido=exp.sentido,

                periodo=exp.periodo,

                patente=exp.patente,

                velocidad_real=(
                    velocidad_ppu
                ),

                velocidad_teorica=(
                    velocidad_teorica
                ),

                porcentaje_reduccion=(
                    reduccion_ppu
                ),

                indicador_tiempo_espera=(
                    indicador
                ),

                clasificacion=(
                    clasificacion_ppu
                ),

                estado="PENDIENTE",

                inicio_servicio=(
                    exp.inicio_servicio
                ),

                fin_servicio=(
                    exp.fin_servicio
                ),

                franja_horaria=(
                    exp.franja_horaria
                ),

                archivo_origen=(
                    exp.archivo_origen
                    if exp.archivo_origen
                    else archivo_origen
                ),

                carga_hash=carga_hash,
            )

            self.db.add(
                historico_ppu
            )

            ppu_insertadas += 1

        print(
            "HISTORICO UPSERT | "
            f"ID: {historico_registro.id} | "
            f"PPU NUEVAS: {ppu_insertadas} | "
            f"PPU EXISTENTES: {ppu_existentes}"
        )

        return True



    def calcular_reduccion(
        self,
        velocidad_real,
        velocidad_teorica,
    ):

        if velocidad_teorica <= 0:
            return 0

        return round(
            (
                (
                    velocidad_teorica
                    -
                    velocidad_real
                )
                /
                velocidad_teorica
            )
            * 100,
            2,
        )

    # =====================================================
    # CLASIFICAR IP / IE
    # =====================================================

    def clasificar(
        self,
        porcentaje,
        indicador,
    ):

        if indicador not in (
            "IP",
            "IE"
        ):
            raise ValueError(
                "Solo se pueden clasificar "
                "indicadores IP o IE"
            )

        # -----------------------------------------------
        # HASTA 10% = OK
        # -----------------------------------------------

        if porcentaje <= 10:
            return "OK"

        # -----------------------------------------------
        # IP
        # >10% y <=20% = SIMPLE
        # >20% = COMPLEJO
        # -----------------------------------------------

        if indicador == "IP":

            if porcentaje < 20:
                return "SIMPLE"

            return "COMPLEJO"

        # -----------------------------------------------
        # IE
        # >10% y <=30% = SIMPLE
        # >30% = COMPLEJO
        # -----------------------------------------------

        if indicador == "IE":

            if porcentaje < 30:
                return "SIMPLE"

            return "COMPLEJO"

