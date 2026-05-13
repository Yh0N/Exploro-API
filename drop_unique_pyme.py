
import os
import re
from sqlalchemy import create_engine, text
from app.core.config import settings

db_url = settings.DATABASE_URL
db_url = re.sub(r'@db:', '@localhost:', db_url)
db_url = db_url.replace(':5432/', ':5433/')

engine = create_engine(db_url)

with engine.connect() as conn:
    try:
        # Intentar eliminar la restricción única si existe
        # El nombre por defecto suele ser pymes_id_usuario_key
        conn.execute(text("ALTER TABLE pymes DROP CONSTRAINT IF EXISTS pymes_id_usuario_key"))
        conn.commit()
        print("Restricción única eliminada exitosamente (si existía).")
    except Exception as e:
        print(f"Error al eliminar restricción: {e}")
