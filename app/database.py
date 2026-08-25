"""
=========================================================
SWAV - Sistema Web de Análisis de Velocidades
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

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,          # Cambiar a True para depuración SQL
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