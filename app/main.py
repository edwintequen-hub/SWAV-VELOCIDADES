"""
=========================================================
SWAV - Sistema Web de AnÃ¡lisis de Velocidades
AplicaciÃ³n Principal
=========================================================
"""

from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from sqlalchemy import text

from app.config import APP_NAME
from app.config import APP_VERSION

from app.database import Base
from app.database import engine
from app.database import SessionLocal
from sqlalchemy.orm import Session

# Modelos
import app.models
from app.models import Expedicion

# Routers
from app.api.importaciones import router as importaciones_router
from app.api.reportes import router as reportes_router
from app.api.registro import router as registro_router

# Si ya existe este archivo, descomenta la siguiente lÃ­nea
# from app.api.dashboard import router as dashboard_router

from sqlalchemy import func

from app.database import SessionLocal
from app.models import Registro

from app.api.matriz import router as matriz_router
from app.api.dashboard import router as dashboard_router
from app.api.configuracion import router as configuracion_router
from app.api.sinoptico import router as sinoptico_router
from app.api.matriz import router as matriz_router


# ==========================================================
# RUTAS
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

FRONTEND_DIR = PROJECT_ROOT / "frontend"

CSS_DIR = FRONTEND_DIR / "css"

JS_DIR = FRONTEND_DIR / "js"

IMG_DIR = FRONTEND_DIR / "img"

print("=" * 80)

print("PROJECT_ROOT  :", PROJECT_ROOT)

print("FRONTEND_DIR  :", FRONTEND_DIR)

print("CSS_DIR       :", CSS_DIR)

print("JS_DIR        :", JS_DIR)

print("IMG_DIR       :", IMG_DIR)

print("-" * 80)

print("FRONTEND      :", FRONTEND_DIR.exists())

print("CSS           :", CSS_DIR.exists())

print("JS            :", JS_DIR.exists())

print("IMG           :", IMG_DIR.exists())

print("-" * 80)

print("dashboard.css :", (CSS_DIR / "dashboard.css").exists())

print("dashboard.js  :", (JS_DIR / "dashboard.js").exists())

print("logo          :", (IMG_DIR / "logo_metropol.png").exists())

print("=" * 80)

# ==========================================================
# CREAR BASE
# ==========================================================

Base.metadata.create_all(bind=engine)


# ==========================================================
# FASTAPI
# ==========================================================

app = FastAPI(

        

    title=APP_NAME,

    version=APP_VERSION,

)

print("Montando CSS...")
print(CSS_DIR)

print("Montando JS...")
print(JS_DIR)

print("Montando IMG...")
print(IMG_DIR)


# ==========================================================
# ARCHIVOS ESTÃTICOS
# ==========================================================

if FRONTEND_DIR.exists():

    if CSS_DIR.exists():

        app.mount(
            "/css",
            StaticFiles(directory=CSS_DIR),
            name="css",
        )

    if JS_DIR.exists():

        app.mount(
            "/js",
            StaticFiles(directory=JS_DIR),
            name="js",
        )

    if IMG_DIR.exists():

        app.mount(
            "/img",
            StaticFiles(directory=IMG_DIR),
            name="img",
        )    

    app.mount(

        "/frontend",

        StaticFiles(directory=FRONTEND_DIR),

        name="frontend",

    )


# ==========================================================
# ROUTERS
# ==========================================================

app.include_router(importaciones_router)

app.include_router(reportes_router)

app.include_router(matriz_router)

app.include_router(registro_router)

app.include_router(dashboard_router)

app.include_router(configuracion_router)

app.include_router(sinoptico_router)

app.include_router(matriz_router)

# Si ya existe el router dashboard
# app.include_router(dashboard_router)


# ==========================================================
# INICIO
# ==========================================================

@app.get("/")
def inicio():

    return {

        "sistema": APP_NAME,

        "version": APP_VERSION,

        "estado": "OK",

        "dashboard": "/dashboard",

        "api_dashboard": "/api/dashboard",

        "debug": "/debug",

        "conteo": "/conteo",

    }


# ==========================================================
# DASHBOARD HTML
# ==========================================================

@app.get("/dashboard")
def dashboard():

    archivo = FRONTEND_DIR / "dashboard.html"

    if archivo.exists():

        return FileResponse(archivo)

    return {

        "mensaje": "dashboard.html no encontrado"

    }

# ==========================================================
# MATRIZ OPERACIONAL
# ==========================================================

@app.get("/matriz")
def matriz():

    archivo = FRONTEND_DIR / "matriz.html"

    if archivo.exists():

        return FileResponse(archivo)

    return {

        "mensaje": "matriz.html no encontrado"

    }

# ==========================================================
# CONFIGURACIÃ“N
# ==========================================================

@app.get("/configuracion")
def configuracion():

    archivo = FRONTEND_DIR / "configuracion.html"

    if archivo.exists():

        return FileResponse(archivo)

    return {

        "mensaje": "configuracion.html no encontrado"

    }

# ==========================================================
# REPORTES HISTORICOS
# ==========================================================

@app.get("/reportes")
def reportes():

    archivo = FRONTEND_DIR / "reportes.html"

    if archivo.exists():

        return FileResponse(archivo)

    return {

        "mensaje": "reportes.html no encontrado"

    }

# ==========================================================
# HEALTH
# ==========================================================

@app.get("/health")
def health():

    return {

        "status": "running"

    }


# ==========================================================
# DEBUG BASE DE DATOS
# Compatible SQLite / PostgreSQL
# ==========================================================

@app.get("/debug")
def debug():

    db = SessionLocal()

    try:

        from sqlalchemy import inspect

        inspector = inspect(
            db.bind
        )

        tablas = inspector.get_table_names()

        total = db.execute(
            text(
                "SELECT COUNT(*) FROM expediciones"
            )
        ).scalar()

        return {
            "database": str(db.bind.url),
            "tablas": tablas,
            "expediciones": total,
        }

    finally:

        db.close()




# ==========================================================
# CONTEO EXPEDICIONES
# ==========================================================

@app.get("/conteo")
def conteo():

    db = SessionLocal()

    try:

        total = db.query(Expedicion).count()

        return {

            "total": total

        }

    finally:

        db.close()


