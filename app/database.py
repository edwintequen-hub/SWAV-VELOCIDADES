"""
=========================================================
SWAV - Sistema Web de AnÃ¡lisis de Velocidades
Base de Datos
=========================================================
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import DATABASE_URL


# ==========================================================
# ENGINE
# ==========================================================

# ==========================================================
# ENGINE
# Compatible SQLite / PostgreSQL
# ==========================================================

connect_args = {}

if DATABASE_URL.startswith(
    "sqlite"
):
    connect_args = {
        "check_same_thread": False
    }

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    future=True,
)

# ==========================================================
# SESSION
# ==========================================================

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ==========================================================
# BASE
# ==========================================================

Base = declarative_base()


# ==========================================================
# DEPENDENCIA FASTAPI
# ==========================================================

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()
