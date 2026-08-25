"""
=========================================================
SWAV
Generación de Registro
=========================================================
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Expedicion
from app.models import Registro


class GeneradorRegistro:

    def __init__(self, db: Session):

        self.db = db

    # =====================================================
    # LIMPIAR TABLA
    # =====================================================

    def limpiar(self):

        self.db.query(Registro).delete()

        self.db.commit()

    # =====================================================
    # GENERAR REGISTRO
    # =====================================================

    def generar(self):

        print("\n" + "=" * 80)
        print("GENERANDO TABLA REGISTRO")
        print("=" * 80)

        self.limpiar()

        # -------------------------------------------------
        # DIAGNÓSTICO
        # -------------------------------------------------

        total_expediciones = self.db.query(
            Expedicion
        ).count()

        total_procesadas = (

            self.db.query(Expedicion)

            .filter(
                Expedicion.procesado == True
            )

            .count()

        )

        total_validas = (

            self.db.query(Expedicion)

            .filter(
                Expedicion.valido == True
            )

            .count()

        )

        total_procesadas_validas = (

            self.db.query(Expedicion)

            .filter(

                Expedicion.procesado == True,

                Expedicion.valido == True

            )

            .count()

        )

        print(f"TOTAL EXPEDICIONES........: {total_expediciones}")
        print(f"TOTAL PROCESADAS..........: {total_procesadas}")
        print(f"TOTAL VALIDAS.............: {total_validas}")
        print(f"TOTAL PROC + VALIDAS......: {total_procesadas_validas}")

        print("-" * 80)

        # -------------------------------------------------
        # CONSULTA
        # -------------------------------------------------

        consulta = (

            self.db.query(

                Expedicion.unidad,

                Expedicion.tipo_dia,

                Expedicion.servicio,

                Expedicion.ruta_normalizada,

                Expedicion.franja_horaria,

                func.count(
                    Expedicion.id
                ).label("expediciones"),

                func.count(
                    func.distinct(
                        Expedicion.patente
                    )
                ).label("buses"),

                func.avg(
                    Expedicion.velocidad_km_h
                ).label("velocidad_real")

            )

            .filter(

                Expedicion.procesado == True,

                Expedicion.valido == True

            )

            .group_by(

                Expedicion.unidad,

                Expedicion.tipo_dia,

                Expedicion.servicio,

                Expedicion.ruta_normalizada,

                Expedicion.franja_horaria

            )

            .all()

        )

        print(f"TOTAL GRUPOS ENCONTRADOS..: {len(consulta)}")

        print("-" * 80)

        for i, fila in enumerate(consulta[:5], start=1):

            print(f"GRUPO {i}")

            print("Unidad........:", fila.unidad)

            print("Tipo Día......:", fila.tipo_dia)

            print("Servicio......:", fila.servicio)

            print("Ruta..........:", fila.ruta_normalizada)

            print("Franja........:", fila.franja_horaria)

            print("Expediciones..:", fila.expediciones)

            print("Buses.........:", fila.buses)

            print("Velocidad.....:", fila.velocidad_real)

            print("-" * 80)

        total = 0

        for fila in consulta:

            registro = Registro(

                unidad=fila.unidad,

                tipo_dia=fila.tipo_dia,

                servicio=fila.servicio,

                ruta=fila.ruta_normalizada,

                ruta_normalizada=fila.ruta_normalizada,

                periodo=0,

                
                expediciones=fila.expediciones,

                buses=fila.buses,

                velocidad_real=round(
                    fila.velocidad_real or 0,
                    2
                ),

                velocidad_teorica=0,

                porcentaje_reduccion=0,

                clasificacion="",

                estado="",

                informar=False

            )

            self.db.add(registro)

            total += 1

        self.db.commit()

        print("=" * 80)
        print(f"REGISTROS INSERTADOS......: {total}")
        print("=" * 80)

        return {

            "estado": "OK",

            "registros": total

        }