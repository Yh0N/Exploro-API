"""
Conexión a la base de datos PostgreSQL con SQLAlchemy y GeoAlchemy2.
Define el engine, la sesión local y la Base declarativa para los modelos.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings


# Motor de conexión a PostgreSQL
# pool_pre_ping verifica la conexión antes de usarla para evitar conexiones muertas
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True
)

# Fábrica de sesiones para interactuar con la base de datos
# autocommit=False: las transacciones se manejan manualmente
# autoflush=False: los cambios no se envían automáticamente a la BD
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Clase base para todos los modelos SQLAlchemy del proyecto
Base = declarative_base()


def get_db():
    """
    Dependency de FastAPI que proporciona una sesión de base de datos.
    Se usa con Depends(get_db) en los endpoints.
    La sesión se cierra automáticamente al finalizar la petición.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
