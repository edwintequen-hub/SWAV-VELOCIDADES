"""
=========================================================
SWAV - Schemas Pydantic
=========================================================
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


# ==========================================================
# UNIDADES
# ==========================================================

class UnidadBase(BaseModel):

    codigo: str

    nombre: str


class UnidadCreate(UnidadBase):

    pass


class UnidadResponse(UnidadBase):

    id: int

    class Config:

        from_attributes = True


# ==========================================================
# EXPEDICIONES
# ==========================================================

class ExpedicionResponse(BaseModel):

    id: int

    unidad: str

    archivo_origen: Optional[str]

    servicio: Optional[str]

    codigo_bus: Optional[str]

    patente: Optional[str]

    ruta: Optional[str]

    ruta_normalizada: Optional[str]

    tipo_dia: Optional[str]

    franja_horaria: Optional[str]

    inicio_servicio: Optional[datetime]

    fin_servicio: Optional[datetime]

    fecha: Optional[date]

    hora: Optional[int]

    zona_horaria: Optional[str]

    tiempo_viaje_real: Optional[str]

    rango_esperado: Optional[str]

    cumplimiento: Optional[str]

    plazas: Optional[int]

    km_inicio: Optional[float]

    km_fin: Optional[float]

    velocidad_km_min: Optional[float]

    velocidad_km_h: Optional[float]

    duracion_min: Optional[float]

    valido: Optional[bool]

    observacion: Optional[str]

    fecha_importacion: Optional[datetime]

    class Config:

        from_attributes = True


# ==========================================================
# HISTORIAL IMPORTACIONES
# ==========================================================

class HistorialResponse(BaseModel):

    id: int

    unidad: str

    archivo: str

    registros: int

    registros_validos: int

    registros_descartados: int

    observaciones: Optional[str]

    fecha: datetime

    class Config:

        from_attributes = True