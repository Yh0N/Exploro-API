"""
Migración: hacer latitud y longitud nullable en la tabla lugares.
Necesario para soportar lugares registrados solo con dirección (geocoding pendiente).

Ejecutar con:
    docker exec exploro_api python migrate_nullable_coords.py
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está definida en .env")

engine = create_engine(DATABASE_URL)

SQL = """
ALTER TABLE lugares
    ALTER COLUMN latitud DROP NOT NULL,
    ALTER COLUMN longitud DROP NOT NULL;
"""

with engine.connect() as conn:
    conn.execute(text(SQL))
    conn.commit()
    print("✅ Columnas 'latitud' y 'longitud' ahora son nullable en 'lugares'.")
