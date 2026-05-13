"""
Script de migración: agrega la columna 'direccion' a la tabla 'lugares'.
Ejecutar UNA sola vez con:
    docker exec exploro_api python migrate_add_direccion.py
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
ADD COLUMN IF NOT EXISTS direccion VARCHAR(300);
"""

with engine.connect() as conn:
    conn.execute(text(SQL))
    conn.commit()
    print("✅ Columna 'direccion' agregada (o ya existía) en la tabla 'lugares'.")
