"""
Script de migración: corrige longitud de fotos y agrega campo is_public.
Ejecutar con:
    python migrate_fix_profile_photos.py
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
-- Cambiar tipos de columna a TEXT para soportar Base64
ALTER TABLE perfiles ALTER COLUMN foto TYPE TEXT;
ALTER TABLE usuarios ALTER COLUMN foto_perfil TYPE TEXT;

-- Agregar columna is_public si no existe
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT TRUE;
"""

try:
    with engine.connect() as conn:
        conn.execute(text(SQL))
        conn.commit()
        print("Migracion completada: fotos ampliadas e is_public agregado.")
except Exception as e:
    print(f"Error al ejecutar la migracion: {e}")
