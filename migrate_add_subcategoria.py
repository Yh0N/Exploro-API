"""
Migración: agrega columna 'subcategoria' a la tabla 'lugares' y 'pymes'.
Ejecutar con:
    docker exec exploro_api python migrate_add_subcategoria.py
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está definida en .env")

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    conn.execute(text("""
        ALTER TABLE lugares
        ADD COLUMN IF NOT EXISTS subcategoria VARCHAR(100);
    """))
    # Intentar agregar a pymes si existe la columna tipo
    try:
        conn.execute(text("""
            ALTER TABLE pymes
            ADD COLUMN IF NOT EXISTS subcategoria VARCHAR(100);
        """))
        print("✅ Columna 'subcategoria' agregada a 'pymes'.")
    except Exception as e:
        print(f"⚠️  No se pudo agregar 'subcategoria' a pymes: {e}")
    
    conn.commit()

print("✅ Columna 'subcategoria' agregada (o ya existía) en 'lugares'.")
