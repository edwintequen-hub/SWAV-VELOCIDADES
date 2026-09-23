from datetime import datetime
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
# CREDENCIALES SINOPTICO
# =========================================================
#
# Credencial utilizada para la descarga automatica R1.6.
#
# IMPORTANTE:
# - No pertenece exclusivamente a U8 ni U9.
# - Puede corresponder a cualquier supervisor autorizado.
# - Solo una credencial debe mantenerse activa.
# - La clave puede actualizarse desde Configuracion.
#
# =========================================================

class CredencialSinoptico(Base):

    __tablename__ = "credenciales_sinoptico"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    usuario = Column(
        String(150),
        nullable=False
    )

    password = Column(
        String(500),
        nullable=False
    )

    activo = Column(
        Boolean,
        default=True,
        nullable=False
    )

    fecha_actualizacion = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )


# =========================================================
# CONFIGURACION AUTOMATICA R1.6
# =========================================================

class ConfiguracionR16Automatica(Base):

    __tablename__ = "configuracion_r16_automatica"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    activo = Column(
        Boolean,
        default=True,
        nullable=False
    )

    intervalo_minutos = Column(
        Integer,
        default=30,
        nullable=False
    )

    actualizar_u8 = Column(
        Boolean,
        default=True,
        nullable=False
    )

    actualizar_u9 = Column(
        Boolean,
        default=True,
        nullable=False
    )

    ultima_ejecucion = Column(
        DateTime,
        nullable=True
    )

    proxima_ejecucion = Column(
        DateTime,
        nullable=True
    )

    ultima_respuesta = Column(
        String(1000),
        nullable=True
    )

    fecha_actualizacion = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
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



# =========================================================
# FLOTA OPERATIVA - ASIGNACION TERMINAL
# Catalogo historico de PPU por terminal.
# No reemplaza versiones anteriores.
# =========================================================

class FlotaAsignacionTerminal(Base):

    __tablename__ = "flota_asignacion_terminal"

    id = Column(Integer, primary_key=True, index=True)

    version = Column(String(20), nullable=False, index=True)
    ppu = Column(String(20), nullable=False, index=True)
    terminal = Column(String(60), nullable=False, index=True)
    unidad = Column(String(10), nullable=True, index=True)
    empresa = Column(String(20), nullable=True)
    interno = Column(String(30), nullable=True)
    tipo_bus = Column(String(30), nullable=True)
    tipo_flota = Column(String(30), nullable=True)
    es_soporte = Column(Boolean, default=False, nullable=False)
    es_auxiliar = Column(Boolean, default=False, nullable=False)
    archivo_origen = Column(String(250), nullable=True)
    activo = Column(Boolean, default=True, nullable=False)
    fecha_importacion = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "version",
            "ppu",
            name="uq_flota_asignacion_version_ppu",
        ),
    )


# =============================================================================
# FLOTA OPERATIVA - SNAPSHOT R001 / R003
# =============================================================================
#
# R001:
#   Fotografia agregada de Total Flota por terminal.
#
# R003:
#   Fotografia de PPU declaradas disponibles.
#
# Estas tablas NO reemplazan:
#   - expediciones R1.6
#   - historico_flota_operativa
#   - historico_flota_operativa_servicio
#   - flota_asignacion_terminal
#
# Cada carga conserva su identificador de snapshot para mantener historico.
# =============================================================================


class FlotaSnapshotR001(Base):

    __tablename__ = "flota_snapshot_r001"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    snapshot_id = Column(
        String(50),
        nullable=False,
        index=True,
    )

    fecha_reporte = Column(
        DateTime,
        nullable=True,
        index=True,
    )

    terminal = Column(
        String(60),
        nullable=False,
        index=True,
    )

    total_flota = Column(
        Integer,
        nullable=False,
    )

    buses_disponibles = Column(
        Integer,
        nullable=True,
    )

    buses_no_disponibles = Column(
        Integer,
        nullable=True,
    )

    archivo_origen = Column(
        String(250),
        nullable=True,
    )

    carga_hash = Column(
        String(64),
        nullable=True,
        index=True,
    )

    fecha_importacion = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "terminal",
            name="uq_flota_r001_snapshot_terminal",
        ),
    )


class FlotaSnapshotR003(Base):

    __tablename__ = "flota_snapshot_r003"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    snapshot_id = Column(
        String(50),
        nullable=False,
        index=True,
    )

    fecha_reporte = Column(
        DateTime,
        nullable=True,
        index=True,
    )

    ppu = Column(
        String(20),
        nullable=False,
        index=True,
    )

    terminal = Column(
        String(60),
        nullable=True,
        index=True,
    )

    interno = Column(
        String(30),
        nullable=True,
    )

    tipo_bus = Column(
        String(60),
        nullable=True,
    )

    archivo_origen = Column(
        String(250),
        nullable=True,
    )

    carga_hash = Column(
        String(64),
        nullable=True,
        index=True,
    )

    fecha_importacion = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "ppu",
            name="uq_flota_r003_snapshot_ppu",
        ),
    )



# =============================================================================
# FLOTA OPERATIVA - HISTORICO INDEPENDIENTE
# =============================================================================
# Este modelo NO pertenece al motor de velocidades.
#
# Regla de presencia operacional:
#     FECHA + PERIODO + PPU = 1 BUS OPERATIVO
#
# Las expediciones R1.6 originales NO se eliminan.
# Esta tabla conserva una presencia consolidada para consulta historica.
# =============================================================================

from datetime import datetime as _FODatetime

from sqlalchemy import (
    Column as _FOColumn,
    Integer as _FOInteger,
    String as _FOString,
    Date as _FODate,
    DateTime as _FODateTime,
    UniqueConstraint as _FOUniqueConstraint,
)


class HistoricoFlotaOperativa(Base):

    __tablename__ = "historico_flota_operativa"

    id = _FOColumn(
        _FOInteger,
        primary_key=True,
        autoincrement=True
    )

    fecha = _FOColumn(
        _FODate,
        nullable=False,
        index=True
    )

    periodo = _FOColumn(
        _FOInteger,
        nullable=False,
        index=True
    )

    ppu = _FOColumn(
        _FOString(20),
        nullable=False,
        index=True
    )

    unidad = _FOColumn(
        _FOString(20),
        nullable=True,
        index=True
    )

    terminal = _FOColumn(
        _FOString(120),
        nullable=True,
        index=True
    )

    interno = _FOColumn(
        _FOString(50),
        nullable=True
    )

    tipo_bus = _FOColumn(
        _FOString(50),
        nullable=True
    )

    tipo_flota = _FOColumn(
        _FOString(50),
        nullable=True
    )

    plazas = _FOColumn(
        _FOInteger,
        nullable=True
    )

    primera_transmision = _FOColumn(
        _FODateTime,
        nullable=True
    )

    ultima_transmision = _FOColumn(
        _FODateTime,
        nullable=True
    )

    cantidad_registros_fuente = _FOColumn(
        _FOInteger,
        nullable=False,
        default=1
    )

    archivo_origen = _FOColumn(
        _FOString(500),
        nullable=True
    )

    fecha_creacion = _FOColumn(
        _FODateTime,
        nullable=False,
        default=_FODatetime.now
    )

    __table_args__ = (

        _FOUniqueConstraint(
            "fecha",
            "periodo",
            "ppu",
            name="uq_historico_flota_operativa_fecha_periodo_ppu"
        ),

    )


# =============================================================================
# HISTORICO FLOTA OPERATIVA POR SERVICIO
# =============================================================================

class HistoricoFlotaOperativaServicio(Base):

    __tablename__ = "historico_flota_operativa_servicio"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    fecha = Column(
        Date,
        nullable=False,
        index=True,
    )

    periodo = Column(
        Integer,
        nullable=False,
        index=True,
    )

    ppu = Column(
        String(20),
        nullable=False,
        index=True,
    )

    servicio = Column(
        String(100),
        nullable=False,
        index=True,
    )

    unidad = Column(
        String(20),
        nullable=True,
        index=True,
    )

    terminal = Column(
        String(120),
        nullable=True,
        index=True,
    )

    primera_transmision = Column(
        DateTime,
        nullable=True,
    )

    ultima_transmision = Column(
        DateTime,
        nullable=True,
    )

    cantidad_registros_fuente = Column(
        Integer,
        nullable=False,
        default=1,
    )

    archivo_origen = Column(
        String(500),
        nullable=True,
    )

    fecha_creacion = Column(
        DateTime,
        nullable=False,
        default=datetime.now,
    )

    __table_args__ = (

        UniqueConstraint(
            "fecha",
            "periodo",
            "ppu",
            "servicio",
            name=(
                "uq_hist_flota_serv_fecha_per_ppu_serv"
            ),
        ),

    )


