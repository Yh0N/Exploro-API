
from sqlalchemy import text
from app.database.connection import engine
import re

def swap():
    # Adjust URL for host connection
    db_url = engine.url.render_as_string(hide_password=False)
    if "@db:5432" in db_url:
        db_url = db_url.replace("@db:5432", "@localhost:5433")
    
    from sqlalchemy import create_engine
    local_engine = create_engine(db_url)
    
    with local_engine.connect() as conn:
        print("Intercambiando IDs de roles: 2 <-> 3...")
        # Usar un valor temporal (99) para evitar colisiones
        conn.execute(text("UPDATE usuarios SET rol = 99 WHERE rol = 2"))
        conn.execute(text("UPDATE usuarios SET rol = 2 WHERE rol = 3"))
        conn.execute(text("UPDATE usuarios SET rol = 3 WHERE rol = 99"))
        conn.commit()
        print("Intercambio completado.")

if __name__ == "__main__":
    swap()
