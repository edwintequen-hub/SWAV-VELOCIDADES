"""
=========================================================
SWAV - Sistema Web de AnÃ¡lisis de Velocidades
Modelos de Base de Datos
=========================================================
"""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from sqlalchemy.sql import func

from app.database import Base


# =========================================================
# UNIDADES
# =========================================================

class Unidad(Base):

    __tablename__ = "unidades"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    codigo = Column(
        String(10),
        unique=True,
        nullable=False
    )

    nombre = Column(
        String(50),
        nullable=False
    )

    activo = Column(
        Boolean,
        default=True
    )

    fecha_creacion = Column(
        DateTime,
        server_default=func.now()
    )


# =========================================================
# CONFIGURACION
# =========================================================

class Configuracion(Base):

    __tablename__ = "configuracion"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    unidad_id = Column(
        Integer,
        ForeignKey("unidades.id")
    )

    duracion_minima = Column(
        Integer,
        default=20
    )

    porcentaje_cumplimiento = Column(
        Float,
        default=70
    )

    fecha_actualizacion = Column(
        DateTime,
        server_default=func.now()
    )


# =========================================================
# RUTAS NORMALIZADAS
# =========================================================

class RutaNormalizada(Base):

    __tablename__ = "rutas_normalizadas"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    ruta_original = Column(
        String(30),
        unique=True,
        nullable=False
    )

    ruta_oficial = Column(
        String(30),
        nullable=False
    )

    activo = Column(
        Boolean,
        default=True
    )

    fecha_creacion = Column(
        DateTime,
        server_default=func.now()
    )


# =========================================================
# SERVICIOS (INFO.xlsx)
# =========================================================

class Servicio(Base):

    __tablename__ = "servicios"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    unidad = Column(
        String(10),
        nullable=False,
        index=True
    )

    empresa = Column(
        String(20),
        nullable=False
    )

    servicio = Column(
        String(30),
        nullable=False,
        index=True
    )

    terminal = Column(
        String(60),
        nullable=False
    )

    tipo_dia = Column(
        String(20),
        nullable=False,
        index=True
    )

    codigo_ts = Column(
        String(20),
        nullable=False,
        index=True
    )

    ruta_ida = Column(
        String(30)
    )

    ruta_regreso = Column(
        String(30)
    )

    activo = Column(
        Boolean,
        default=True
    )

    version = Column(
        String(20),
        default="1.0"
    )

    fecha_importacion = Column(
        DateTime,
        server_default=func.now()
    )


# =========================================================
# PERIODOS
# CatÃ¡logo importado desde Anexo 4
# =========================================================

class Periodo(Base):

    __tablename__ = "periodos"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    unidad = Column(
        String(10),
        nullable=False,
        index=True
    )

    empresa = Column(
        String(20),
        nullable=False,
        index=True
    )

    escenario = Column(
        String(30)
    )

    codigo_ts = Column(
        String(20),
        nullable=False,
        index=True
    )

    sentido = Column(
        String(10),
        nullable=False,
        index=True
    )

    tipo_dia = Column(
        String(20),
        nullable=False,
        index=True
    )

    tipo_evento = Column(
        String(30)
    )

    hora_inicio = Column(
        String(10)
    )

    periodo_inicio = Column(
        String(10),
        index=True
    )

    hora_fin = Column(
        String(10)
    )

    periodo_fin = Column(
        String(10)
    )

    duracion = Column(
        Float
    )

    fecha_creacion = Column(
        DateTime,
        server_default=func.now()
    )


# =========================================================
# ANEXO 3 - VELOCIDADES TEORICAS
# =========================================================

class Velocidad(Base):

    __tablename__ = "velocidades"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    unidad = Column(
        String(10),
        nullable=False,
        index=True
    )

    empresa = Column(
        String(20),
        nullable=False,
        index=True
    )

    codigo_ts = Column(
        String(20),
        nullable=False,
        index=True
    )

    sentido = Column(
        String(10),
        nullable=False,
        index=True
    )

    tipo_dia = Column(
        String(20),
        nullable=False,
        index=True
    )

    periodo = Column(
        Integer,
        nullable=False,
        index=True
    )

    velocidad = Column(
        Float,
        nullable=False
    )

    # ---------------------------------------------------------
    # NUEVO:
    # Indicador proveniente de la columna N del Anexo 3
    #
    # Valores esperados:
    # IP
    # IE
    # --
    # ---------------------------------------------------------

    indicador_tiempo_espera = Column(
        String(10),
        nullable=True,
        index=True
    )

    version = Column(
        String(20),
        default="1.0"
    )

    activo = Column(
        Boolean,
        default=True
    )

    fecha_importacion = Column(
        DateTime,
        server_default=func.now()
    )


# =========================================================
# EXPEDICIONES (R1.6)
# =========================================================

class Expedicion(Base):

    __tablename__ = "expediciones"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # -----------------------------------------------------
    # AuditorÃ­a
    # -----------------------------------------------------

    archivo_origen = Column(
        String(250)
    )

    fecha_importacion = Column(
        DateTime,
        server_default=func.now()
    )

    # -----------------------------------------------------
    # InformaciÃ³n de la Unidad
    # -----------------------------------------------------

    unidad = Column(
        String(10),
        nullable=False,
        index=True
    )

    empresa = Column(
        String(20)
    )

    # -----------------------------------------------------
    # Datos originales R1.6
    # -----------------------------------------------------

    servicio = Column(
        String(30),
        index=True
    )

    codigo_bus = Column(
        String(20)
    )

    patente = Column(
        String(20),
        index=True
    )

    ruta = Column(
        String(30),
        index=True
    )

    tipo_dia = Column(
        String(20)
    )

    franja_horaria = Column(
        String(30)
    )

    inicio_servicio = Column(
        DateTime
    )

    fin_servicio = Column(
        DateTime
    )

    fecha = Column(
        Date
    )

    hora = Column(
        Integer
    )

    zona_horaria = Column(
        String(30)
    )

    tiempo_viaje_real = Column(
        String(30)
    )

    rango_esperado = Column(
        String(80)
    )

    cumplimiento = Column(
        String(20)
    )

    plazas = Column(
        Integer
    )

    km_inicio = Column(
        Float
    )

    km_fin = Column(
        Float
    )

    # -----------------------------------------------------
    # Datos calculados
    # -----------------------------------------------------

    codigo_ts = Column(
        String(20),
        index=True
    )

    ruta_normalizada = Column(
        String(30),
        index=True
    )

    sentido = Column(
        String(10)
    )

    velocidad_km_min = Column(
        Float
    )

    velocidad_km_h = Column(
        Float
    )

    duracion_min = Column(
        Float
    )

    periodo = Column(
        Integer,
        index=True
    )

    velocidad_teorica = Column(
        Float
    )

    porcentaje_reduccion = Column(
        Float
    )

    # -----------------------------------------------------
    # Indicador Anexo 3
    # -----------------------------------------------------

    indicador_tiempo_espera = Column(
        String(10),
        index=True
    )

    # -----------------------------------------------------
    # Estado
    # -----------------------------------------------------

    valido = Column(
        Boolean,
        default=True
    )

    procesado = Column(
        Boolean,
        default=False
    )

    observacion = Column(
        Text
    )

    fecha_procesamiento = Column(
        DateTime
    )


# =========================================================
# REGISTRO
# Equivalente a la Hoja Registro de la Macro
# =========================================================

class Registro(Base):

    __tablename__ = "registro"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    unidad = Column(
        String(10),
        index=True
    )

    empresa = Column(
        String(20)
    )

    tipo_dia = Column(
        String(20)
    )

    servicio = Column(
        String(30),
        index=True
    )

    codigo_ts = Column(
        String(20),
        index=True
    )

    ruta = Column(
        String(30),
        index=True
    )

    ruta_normalizada = Column(
        String(30),
        index=True
    )

    sentido = Column(
        String(10)
    )

    periodo = Column(
        Integer,
        index=True
    )

    expediciones = Column(
        Integer,
        default=0
    )

    buses = Column(
        Integer,
        default=0
    )

    velocidad_real = Column(
        Float
    )

    velocidad_teorica = Column(
        Float
    )

    porcentaje_reduccion = Column(
        Float
    )

    # ---------------------------------------------------------
    # NUEVO:
    # IP / IE utilizado para determinar la clasificaciÃ³n
    # ---------------------------------------------------------

    indicador_tiempo_espera = Column(
        String(10),
        index=True
    )

    clasificacion = Column(
        String(20)
    )

    estado = Column(
        String(20)
    )

    informar = Column(
        Boolean,
        default=False
    )

    observacion = Column(
        Text
    )

    fecha_proceso = Column(
        DateTime,
        server_default=func.now()
    )



# =========================================================
# HISTORICO REGISTROS
# Registros histÃ³ricos consolidados
# =========================================================

class HistoricoRegistro(Base):

    __tablename__ = "historico_registros"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    unidad = Column(
        String(10),
        index=True
    )

    empresa = Column(
        String(20)
    )

    fecha_operacional = Column(
        Date
    )

    tipo_dia = Column(
        String(30)
    )

    servicio = Column(
        String(30),
        index=True
    )

    codigo_ts = Column(
        String(30),
        index=True
    )

    ruta = Column(
        String(100),
        index=True
    )

    ruta_normalizada = Column(
        String(100),
        index=True
    )

    sentido = Column(
        String(20)
    )

    periodo = Column(
        Integer,
        index=True
    )

    expediciones = Column(
        Integer,
        default=0
    )

    buses = Column(
        Integer,
        default=0
    )

    velocidad_real = Column(
        Float
    )

    velocidad_teorica = Column(
        Float
    )

    porcentaje_reduccion = Column(
        Float
    )

    indicador_tiempo_espera = Column(
        String(10),
        index=True
    )

    clasificacion = Column(
        String(20)
    )

    estado = Column(
        String(20)
    )

    informar = Column(
        Boolean,
        default=False
    )

    observacion = Column(
        Text
    )

    archivo_origen = Column(
        String(250)
    )

    carga_hash = Column(
        String(64)
    )

    fecha_proceso = Column(
        DateTime,
        server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "unidad",
            "fecha_operacional",
            "carga_hash",
            "tipo_dia",
            "servicio",
            "codigo_ts",
            "ruta",
            "ruta_normalizada",
            "sentido",
            "periodo",
            "indicador_tiempo_espera",
            name="uq_historico_resultado"
        ),
    )

# =========================================================
# HISTORICO EXPEDICIONES
# Todas las expediciones validas procesadas por SWAV
# =========================================================

class HistoricoExpedicion(Base):

    __tablename__ = "historico_expediciones"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    unidad = Column(
        String(10),
        nullable=False,
        index=True
    )

    empresa = Column(
        String(20)
    )

    fecha_operacional = Column(
        Date,
        nullable=False,
        index=True
    )

    tipo_dia = Column(
        String(30),
        nullable=False,
        index=True
    )

    servicio = Column(
        String(30),
        nullable=False,
        index=True
    )

    codigo_bus = Column(
        String(20)
    )

    patente = Column(
        String(20),
        nullable=False,
        index=True
    )

    codigo_ts = Column(
        String(30),
        nullable=False,
        index=True
    )

    ruta = Column(
        String(100)
    )

    ruta_normalizada = Column(
        String(100),
        nullable=False,
        index=True
    )

    sentido = Column(
        String(20),
        nullable=False,
        index=True
    )

    periodo = Column(
        Integer,
        nullable=False,
        index=True
    )

    inicio_servicio = Column(
        DateTime,
        nullable=False,
        index=True
    )

    fin_servicio = Column(
        DateTime
    )

    franja_horaria = Column(
        String(30)
    )

    velocidad_real = Column(
        Float
    )

    velocidad_teorica = Column(
        Float
    )

    porcentaje_reduccion = Column(
        Float
    )

    indicador_tiempo_espera = Column(
        String(10),
        index=True
    )

    analizable = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True
    )

    motivo_no_analizable = Column(
        String(250)
    )

    clasificacion = Column(
        String(20),
        index=True
    )

    archivo_origen = Column(
        String(250)
    )

    carga_hash = Column(
        String(64),
        nullable=False,
        index=True
    )

    fecha_proceso = Column(
        DateTime,
        server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "carga_hash",
            "patente",
            "inicio_servicio",
            "ruta",
            name="uq_historico_expedicion"
        ),
    )


# =========================================================
# HISTORICO PPU
# Resultado individual de cada PPU que formo un periodo
# =========================================================

class HistoricoPPU(Base):

    __tablename__ = "historico_ppu"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    historico_id = Column(
        Integer,
        nullable=False,
        index=True
    )

    unidad = Column(
        String(10),
        nullable=False,
        index=True
    )

    fecha_operacional = Column(
        Date,
        nullable=False,
        index=True
    )

    tipo_dia = Column(
        String(30),
        nullable=False
    )

    servicio = Column(
        String(30),
        nullable=False
    )

    codigo_ts = Column(
        String(30),
        nullable=False
    )

    ruta = Column(
        String(100)
    )

    ruta_normalizada = Column(
        String(100),
        nullable=False
    )

    sentido = Column(
        String(20),
        nullable=False
    )

    periodo = Column(
        Integer,
        nullable=False
    )

    patente = Column(
        String(20),
        nullable=False,
        index=True
    )

    velocidad_real = Column(
        Float
    )

    velocidad_teorica = Column(
        Float
    )

    porcentaje_reduccion = Column(
        Float
    )

    indicador_tiempo_espera = Column(
        String(10)
    )

    clasificacion = Column(
        String(20)
    )

    estado = Column(
        String(20)
    )

    inicio_servicio = Column(
        DateTime
    )

    fin_servicio = Column(
        DateTime
    )

    franja_horaria = Column(
        String(30)
    )

    archivo_origen = Column(
        String(250)
    )

    carga_hash = Column(
        String(64),
        nullable=False
    )

    fecha_proceso = Column(
        DateTime,
        server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "historico_id",
            "patente",
            "inicio_servicio",
            "ruta",
            name="uq_historico_ppu"
        ),
    )


# =========================================================
# HISTORIAL IMPORTACIONES
# =========================================================

class HistorialImportacion(Base):

    __tablename__ = "historial_importaciones"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    unidad = Column(
        String(10)
    )

    empresa = Column(
        String(20)
    )

    archivo = Column(
        String(250)
    )

    tipo_archivo = Column(
        String(30)
    )

    version = Column(
        String(20)
    )

    registros = Column(
        Integer,
        default=0
    )

    registros_validos = Column(
        Integer,
        default=0
    )

    registros_descartados = Column(
        Integer,
        default=0
    )

    observaciones = Column(
        Text
    )

    fecha = Column(
        DateTime,
        server_default=func.now()
    )

    carga_hash = Column(
        String(64)
    )


