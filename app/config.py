"""
=========================================================
SWAV
Configuración General
=========================================================
"""

from pathlib import Path


# =========================================================
# DIRECTORIOS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

APP_DIR = BASE_DIR / "app"

DATABASE_DIR = BASE_DIR / "database"

UPLOAD_DIR = BASE_DIR / "uploads"

CATALOGOS_DIR = BASE_DIR / "catalogos"

OUTPUT_DIR = BASE_DIR / "output"


# =========================================================
# BASE DE DATOS
# =========================================================

DATABASE_FILE = DATABASE_DIR / "swav.db"

# =========================================================
# SQLALCHEMY
# =========================================================

DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

# =========================================================
# CATÁLOGOS
# =========================================================

INFO_XLSX = CATALOGOS_DIR / "INFO.xlsx"

RUTAS_NORMALIZADAS_XLSX = (
    CATALOGOS_DIR / "Rutas_Normalizadas.xlsx"
)


# =========================================================
# ANEXO 3
# =========================================================

ANEXO3_U8_DIR = (
    CATALOGOS_DIR / "U8" / "Anexo 3"
)

ANEXO3_U9_DIR = (
    CATALOGOS_DIR / "U9" / "Anexo 3"
)


# =========================================================
# ANEXO 4
# =========================================================

ANEXO4_U8_DIR = (
    CATALOGOS_DIR / "U8" / "Anexo 4"
)

ANEXO4_U9_DIR = (
    CATALOGOS_DIR / "U9" / "Anexo 4"
)


# =========================================================
# CSV R1.6
# =========================================================

CSV_SEPARATOR = ";"

CSV_ENCODING = "utf-8-sig"

CSV_HEADER_ROW = 12


# =========================================================
# PARÁMETROS DEL SISTEMA
# =========================================================

DURACION_MINIMA_DEFAULT = 20

PORCENTAJE_CUMPLIMIENTO_DEFAULT = 70


# =========================================================
# CREAR DIRECTORIOS SI NO EXISTEN
# =========================================================

DATABASE_DIR.mkdir(exist_ok=True)

UPLOAD_DIR.mkdir(exist_ok=True)

OUTPUT_DIR.mkdir(exist_ok=True)

# =========================================================
# APLICACIÓN
# =========================================================

APP_NAME = "METROPOL"

APP_VERSION = "2.0"

APP_DESCRIPTION = "Sistema Web de Análisis de Velocidades"