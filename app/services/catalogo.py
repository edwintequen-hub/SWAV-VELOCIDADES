"""
SWAV

Catálogo Maestro
"""

from sqlalchemy.orm import Session

from app.models import Servicio


class Catalogo:

    def __init__(self, db: Session):

        self.db = db

    # =====================================================
    # BUSCAR POR CÓDIGO TS
    # =====================================================

    def buscar_por_codigo_ts(self, codigo_ts):

        codigo_ts = str(codigo_ts).strip().upper()

        return (
            self.db.query(Servicio)
            .filter(
                Servicio.codigo_ts == codigo_ts
            )
            .first()
        )

    # =====================================================
    # OBTENER SERVICIO CLIENTE
    # =====================================================

    def obtener_servicio_cliente(self, codigo_ts):

        servicio = self.buscar_por_codigo_ts(codigo_ts)

        if servicio is None:
            return None

        return servicio.servicio

    # =====================================================
    # OBTENER RUTA OFICIAL
    # =====================================================

    def obtener_ruta_oficial(self, codigo_ts, sentido):

        servicio = self.buscar_por_codigo_ts(codigo_ts)

        if servicio is None:
            return None

        sentido = str(sentido).strip().upper()

        if sentido == "I":
            return servicio.ruta_ida

        if sentido == "R":
            return servicio.ruta_regreso

        return None

    # =====================================================
    # BUSCAR POR RUTA
    # =====================================================

    def buscar_por_ruta(self, ruta_normalizada):
        """
        Busca un servicio por la ruta oficial
        (Ida o Regreso).
        """

        if not ruta_normalizada:
            return None

        ruta_normalizada = (
            str(ruta_normalizada)
            .strip()
            .upper()
        )

        return (
            self.db.query(Servicio)
            .filter(
                (Servicio.ruta_ida == ruta_normalizada)
                |
                (Servicio.ruta_regreso == ruta_normalizada)
            )
            .first()
        )

    # =====================================================
    # RESOLVER SERVICIO COMPLETO
    # HM-007
    # =====================================================

    def resolver(self, codigo_ts, sentido):
        """
        Resuelve un Código TS + sentido utilizando
        el Catálogo Maestro.

        codigo_ts:
            Servicio empresarial / DTPM.

        servicio:
            Servicio cliente.
        """

        codigo_ts = (
            str(codigo_ts)
            .strip()
            .upper()
        )

        sentido = (
            str(sentido)
            .strip()
            .upper()
        )

        servicio = self.buscar_por_codigo_ts(
            codigo_ts
        )

        if servicio is None:
            return None

        if sentido == "I":

            ruta_oficial = servicio.ruta_ida

        elif sentido == "R":

            ruta_oficial = servicio.ruta_regreso

        else:

            ruta_oficial = None

        return {

            # Servicio empresarial / DTPM
            "codigo_ts": servicio.codigo_ts,

            # Servicio cliente
            "servicio": servicio.servicio,

            # Unidad / empresa
            "unidad": servicio.unidad,
            "empresa": servicio.empresa,

            # Datos operacionales
            "terminal": servicio.terminal,
            "tipo_dia": servicio.tipo_dia,

            # Ruta oficial
            "ruta_oficial": ruta_oficial,

            # Sentido
            "sentido": sentido,

        }