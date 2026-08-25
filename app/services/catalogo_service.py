"""
=========================================================
SWAV
Servicio de Catálogos
=========================================================
"""

from sqlalchemy.orm import Session

from app.models import Servicio


class CatalogoService:

    def __init__(self, db: Session):

        self.db = db

    # =====================================================
    # UNIDADES
    # =====================================================

    def obtener_unidades(self):

        datos = (

            self.db.query(Servicio.unidad)

            .distinct()

            .order_by(Servicio.unidad)

            .all()

        )

        return [fila[0] for fila in datos]

    # =====================================================
    # SERVICIOS
    # =====================================================

    def obtener_servicios(self, unidad):

        datos = (

            self.db.query(Servicio.servicio)

            .filter(

                Servicio.unidad == unidad

            )

            .distinct()

            .order_by(Servicio.servicio)

            .all()

        )

        return [fila[0] for fila in datos]

    # =====================================================
    # TERMINALES
    # =====================================================

    def obtener_terminales(self, unidad, servicio):

        datos = (

            self.db.query(Servicio.terminal)

            .filter(

                Servicio.unidad == unidad,

                Servicio.servicio == servicio

            )

            .distinct()

            .order_by(Servicio.terminal)

            .all()

        )

        return [fila[0] for fila in datos]

    # =====================================================
    # TIPOS DE DIA
    # =====================================================

    def obtener_tipos_dia(self, unidad, servicio):

        datos = (

            self.db.query(Servicio.tipo_dia)

            .filter(

                Servicio.unidad == unidad,

                Servicio.servicio == servicio

            )

            .distinct()

            .order_by(Servicio.tipo_dia)

            .all()

        )

        return [fila[0] for fila in datos]

    # =====================================================
    # CODIGO TS
    # =====================================================

    def obtener_codigo_ts(self, unidad, servicio):

        dato = (

            self.db.query(Servicio)

            .filter(

                Servicio.unidad == unidad,

                Servicio.servicio == servicio

            )

            .first()

        )

        if dato:

            return dato.codigo_ts

        return None

    # =====================================================
    # EMPRESA
    # =====================================================

    def obtener_empresa(self, unidad):

        dato = (

            self.db.query(Servicio)

            .filter(

                Servicio.unidad == unidad

            )

            .first()

        )

        if dato:

            return dato.empresa

        return None

    # =====================================================
    # EXISTE SERVICIO
    # =====================================================

    def existe_servicio(self, unidad, servicio):

        return (

            self.db.query(Servicio)

            .filter(

                Servicio.unidad == unidad,

                Servicio.servicio == servicio

            )

            .count()

        ) > 0