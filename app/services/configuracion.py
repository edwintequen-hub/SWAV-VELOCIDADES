"""
=========================================================
SWAV

Servicio de Configuración
=========================================================
"""

from app.database import SessionLocal
from app.models import Configuracion


class ConfiguracionService:

    def __init__(self):

        self.db = SessionLocal()

    def obtener(self, unidad_id):

        configuracion = (

            self.db.query(Configuracion)

            .filter(
                Configuracion.unidad_id == unidad_id
            )

            .first()

        )

        if configuracion is None:

            configuracion = Configuracion(

                unidad_id=unidad_id,

                duracion_minima=20,

                porcentaje_cumplimiento=70

            )

            self.db.add(configuracion)

            self.db.commit()

            self.db.refresh(configuracion)

        return configuracion