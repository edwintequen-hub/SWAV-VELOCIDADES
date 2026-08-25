"""
=========================================================
SWAV
Motor de Registro
Versión 1.0
=========================================================
"""

from sqlalchemy.orm import Session

from app.models import (
    Expedicion,
    Servicio,
    RutaNormalizada,
    Velocidad,
)

from collections import defaultdict

from app.models import Registro

class MotorRegistro:

    def __init__(self, db: Session):

        self.db = db

    # =====================================================
    # PROCESAR EXPEDICIONES
    # =====================================================

    def procesar(self):

        print("=" * 80)
        print("MOTOR DE REGISTRO")
        print("=" * 80)

        expediciones = (

            self.db.query(Expedicion)

            .all()
            
        )

        print(f"Expediciones encontradas : {len(expediciones)}")

        procesadas = 0

        for exp in expediciones:

            try:

                self.procesar_expedicion(exp)

                procesadas += 1

            except Exception as e:

                exp.observacion = str(e)

                exp.valido = False

        self.db.commit()

        self.actualizar_registro()

        print("=" * 80)
        print(f"Expediciones procesadas : {procesadas}")
        print("=" * 80)

        return procesadas

    def actualizar_registro(self):

        print("=" * 80)
        print("GENERANDO REGISTRO")
        print("=" * 80)

        # Limpiar registro anterior
        self.db.query(Registro).delete()

        grupos = defaultdict(list)

        expediciones = (
            self.db.query(Expedicion)
            .filter(Expedicion.procesado == True)
            .all()
        )

        for exp in expediciones:

            clave = (
                exp.unidad,
                exp.tipo_dia,
                exp.codigo_ts,
                exp.ruta_normalizada,
                exp.sentido,
                exp.periodo
            )

            grupos[clave].append(exp)

        print(f"Grupos encontrados: {len(grupos)}")

        for clave, lista in grupos.items():

            unidad, tipo_dia, codigo_ts, ruta, sentido, periodo = clave

            empresa = lista[0].empresa
            servicio = lista[0].servicio
            velocidad_teorica = lista[0].velocidad_teorica

            cantidad_expediciones = len(lista)

            buses = len(
                {
                    e.patente
                    for e in lista
                    if e.patente
                }
            )

            velocidad_real = round(
                sum(
                    e.velocidad_km_h
                    for e in lista
                ) / cantidad_expediciones,
                2
            )

            if velocidad_teorica > 0:

                porcentaje = round(
                    (
                        (velocidad_teorica - velocidad_real)
                        /
                        velocidad_teorica
                    ) * 100,
                    2
                )

                clasificacion = self.clasificar(
                    porcentaje,
                    velocidad_teorica
                )

            else:

                porcentaje = 0

                clasificacion = "SIN VELOCIDAD"

            registro = Registro(

                unidad=unidad,

                empresa=empresa,

                tipo_dia=tipo_dia,

                servicio=servicio,

                codigo_ts=codigo_ts,

                ruta=ruta,

                ruta_normalizada=ruta,

                sentido=sentido,

                periodo=periodo,

                expediciones=cantidad_expediciones,

                buses=buses,

                velocidad_real=velocidad_real,

                velocidad_teorica=velocidad_teorica,

                porcentaje_reduccion=porcentaje,

                clasificacion=clasificacion,

                estado="PENDIENTE",

                informar=clasificacion in (
                    "SIMPLE",
                    "COMPLEJO"
                ),

                observacion=""
            )

            self.db.add(registro)

        self.db.commit()

        print("=" * 80)
        print("REGISTRO GENERADO")
        print("=" * 80)

        print(
            f"Total registros : {len(grupos)}"
        )


    # =====================================================
    # PROCESAR UNA EXPEDICIÓN
    # =====================================================

    def procesar_expedicion(self, exp):

        codigo_ts = exp.servicio

        if codigo_ts.startswith("T"):

            codigo_ts = codigo_ts[1:]

        servicio = (

            self.db.query(Servicio)

            .filter(

                Servicio.codigo_ts == codigo_ts

            )

            .first()

        )

        if servicio:

            # Datos provenientes de INFO.xlsx
            exp.servicio = servicio.servicio      # B01
            exp.codigo_ts = servicio.codigo_ts    # 801
            exp.unidad = servicio.unidad
            exp.empresa = servicio.empresa

        else:

            exp.codigo_ts = ""
            exp.observacion = "Código TS no encontrado"

        ruta = (

            self.db.query(RutaNormalizada)

            .filter(

                RutaNormalizada.ruta_original == exp.ruta

            )

            .first()

        )

        if ruta:

            exp.ruta_normalizada = ruta.ruta_oficial

        else:

            exp.ruta_normalizada = exp.ruta

        exp.sentido = self.calcular_sentido(

            exp.ruta_normalizada

        )

        exp.velocidad_km_h = self.calcular_velocidad(

            exp

        )

        # Validar velocidad real

        if exp.velocidad_km_h <= 0:

            exp.procesado = False
            exp.observacion = "Velocidad igual a 0"
            
        exp.duracion_min = self.calcular_duracion(

            exp

        )

        # Validar duración mínima

        if exp.duracion_min <= 0:

            exp.procesado = False
            exp.observacion = "Duración inválida"

            return

        exp.periodo = self.calcular_periodo(

            exp

        )

        # -----------------------------------------------------
        # Velocidad teórica
        # -----------------------------------------------------
        print("=" * 80)
        print("EXPEDICION")
        print("Servicio           :", exp.servicio)
        print("Codigo TS          :", exp.codigo_ts)
        print("Ruta               :", exp.ruta)
        print("Ruta Normalizada   :", exp.ruta_normalizada)
        print("Sentido            :", exp.sentido)
        print("Tipo Dia           :", exp.tipo_dia)
        print("Hora Inicio        :", exp.inicio_servicio)
        print("Periodo            :", exp.periodo)
        print("=" * 80)


        exp.velocidad_teorica = self.buscar_velocidad_teorica(exp)

        # -----------------------------------------------------
        # Porcentaje de reducción
        # -----------------------------------------------------

        exp.porcentaje_reduccion = self.calcular_reduccion(

            exp.velocidad_km_h,

            exp.velocidad_teorica,

        )

        print(f"Velocidad Real      : {exp.velocidad_km_h}")
        print(f"Velocidad Teórica   : {exp.velocidad_teorica}")
        print(f"Reducción (%)       : {exp.porcentaje_reduccion}")
        print(f"CLASIFICACION       : {self.clasificar(exp.porcentaje_reduccion)}")
        # -----------------------------------------------------
        # Clasificación
        # -----------------------------------------------------

        clasificacion = self.clasificar(
            exp.porcentaje_reduccion,
            exp.velocidad_teorica
        )

        print(f"CLASIFICACION : {clasificacion}")

   
        # -----------------------------------------------------
        # Observación
        # -----------------------------------------------------

        if exp.velocidad_teorica <= 0:

            exp.observacion = "Velocidad teórica no encontrada"

        else:

            exp.observacion = ""

        # -----------------------------------------------------
# Procesada
# -----------------------------------------------------

        errores = []

        if not exp.codigo_ts:
            errores.append("Código TS")

        if not exp.ruta_normalizada:
            errores.append("Ruta")

        if exp.velocidad_teorica <= 0:
            errores.append("Velocidad Teórica")

        exp.procesado = len(errores) == 0

        if errores:
            exp.observacion = "Falta: " + ", ".join(errores)
        else:
            exp.observacion = ""


    # =====================================================
    # CALCULAR SENTIDO
    # =====================================================

    def calcular_sentido(self, ruta):

        if not ruta:
            return ""

        ruta = ruta.upper().strip()

        if ruta.endswith("I"):
            return "IDA"

        if ruta.endswith("R"):
            return "RET"

        if ruta.endswith("V"):
            return "VUELTA"

        return ""

    # =====================================================
    # CALCULAR VELOCIDAD KM/H
    # =====================================================

    def calcular_velocidad(self, exp):

        if exp.velocidad_km_min is None:

            return 0

        return round(

            exp.velocidad_km_min * 60,

            2

        )

    # =====================================================
    # CALCULAR DURACIÓN
    # =====================================================
    
    def calcular_duracion(self, exp):

        if (
            exp.inicio_servicio is None
            or
            exp.fin_servicio is None
        ):
            return 0

        segundos = (
            exp.fin_servicio
            -
            exp.inicio_servicio
        ).total_seconds()

        # Si cruza medianoche
        if segundos < 0:
           segundos += 86400

        return round(segundos / 60, 2)

    # =====================================================
    # CALCULAR PERIODO
    # =====================================================

    def calcular_periodo(self, exp):

        if exp.inicio_servicio is None:

            return 0

    # Igual que la macro VBA:
    # PERIODO = Hour(HoraInicio) + 1

        return exp.inicio_servicio.hour + 1

    # =====================================================
    # BUSCAR VELOCIDAD TEÓRICA
    # =====================================================

    def buscar_velocidad_teorica(self, exp):

        tipo_dia = (exp.tipo_dia or "").strip().upper()

        equivalencias = {
            "DIA NORMAL": "LABORAL",
            "LABORAL": "LABORAL",
            "SABADO": "SÁBADO",
            "SÁBADO": "SÁBADO",
            "DOMINGO": "DOMINGO",
        }

        tipo_dia = equivalencias.get(tipo_dia, tipo_dia)

        if not tipo_dia:
            return 0

        # ----------------------------------------
        # DEBUG
        # ----------------------------------------
        print("=" * 80)
        print("BUSQUEDA VELOCIDAD")
        print(f"TS       : [{repr(exp.codigo_ts)}]")
        print(f"SENTIDO  : [{repr(exp.sentido)}]")
        print(f"TIPO DIA : [{repr(tipo_dia)}]")
        print(f"PERIODO  : [{repr(exp.periodo)}]")

        velocidad = (
            self.db.query(Velocidad)
            .filter(
                Velocidad.codigo_ts == exp.codigo_ts,
                Velocidad.tipo_dia == tipo_dia,
                Velocidad.sentido == exp.sentido,
                Velocidad.periodo == exp.periodo,
            )
            .first()
        )

        if velocidad:
            print(f"VELOCIDAD ENCONTRADA: {velocidad.velocidad}")
            return velocidad.velocidad

        print("NO ENCONTRADA")
        return 0

    # =====================================================
    # CALCULAR PORCENTAJE REDUCCIÓN
    # =====================================================

    def calcular_reduccion(

        self,

        velocidad_real,

        velocidad_teorica,

    ):

        if velocidad_teorica <= 0:

            return 0

        return round(

            (

                (velocidad_teorica - velocidad_real)

                / velocidad_teorica

            ) * 100,

            2,

        )

    
    # =====================================================
    # CLASIFICAR
    # =====================================================

    def clasificar(
        self,
        porcentaje,
        velocidad_teorica=0
    ):

        if velocidad_teorica <= 0:
            return "SIN VELOCIDAD"

        if porcentaje <= 10:
            return "OK"

        elif porcentaje <= 29:
            return "SIMPLE"

        else:
            return "COMPLEJO"

    # =====================================================
    # RESUMEN
    # =====================================================

    def resumen(self):

        total = self.db.query(Expedicion).count()

        procesadas = (

            self.db.query(Expedicion)

            .filter(

                Expedicion.procesado == True

            )

            .count()

        )

        pendientes = total - procesadas

        print("=" * 80)
        print("RESUMEN MOTOR")
        print("=" * 80)
        print(f"Total expediciones : {total}")
        print(f"Procesadas         : {procesadas}")
        print(f"Pendientes         : {pendientes}")
        print("=" * 80)

        return {

            "total": total,

            "procesadas": procesadas,

            "pendientes": pendientes,

        }