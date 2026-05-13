"""
Script de migración: agrega columnas de fotos a las tablas 'lugares' y 'pymes'.
Ejecutar UNA sola vez con:
    docker exec exploro_api python migrate_add_photos.py
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está definida en .env")

# Ajuste para ejecución local (fuera de docker)
if "@db:" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("@db:5432", "@localhost:5433")

engine = create_engine(DATABASE_URL)

SQL = """
ALTER TABLE lugares ADD COLUMN IF NOT EXISTS foto_principal VARCHAR(500);
ALTER TABLE lugares ADD COLUMN IF NOT EXISTS fotos VARCHAR(2000);

ALTER TABLE pymes ADD COLUMN IF NOT EXISTS foto_principal VARCHAR(500);
ALTER TABLE pymes ADD COLUMN IF NOT EXISTS fotos VARCHAR(2000);
"""

try:
    with engine.connect() as conn:
        conn.execute(text(SQL))
        conn.commit()
        print("✅ Columnas de fotos agregadas exitosamente.")
except Exception as e:
    print(f"❌ Error al ejecutar la migración: {e}")
