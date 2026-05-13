
from sqlalchemy import text
from app.database.connection import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    # Ajustar URL para conexión desde el host (fuera de Docker)
    db_url = engine.url.render_as_string(hide_password=False)
    if "@db:5432" in db_url:
        db_url = db_url.replace("@db:5432", "@localhost:5433")
    
    from sqlalchemy import create_engine
    local_engine = create_engine(db_url)
    
    with local_engine.connect() as conn:
        logger.info("Iniciando migración de roles...")
        
        # 1. Convertir valores existentes
        logger.info("Convirtiendo valores de texto a números (1:regular, 2:pyme, 3:admin)...")
        conn.execute(text("UPDATE usuarios SET rol = '1' WHERE rol = 'usuario_regular' OR rol IS NULL"))
        conn.execute(text("UPDATE usuarios SET rol = '2' WHERE rol = 'pyme'"))
        conn.execute(text("UPDATE usuarios SET rol = '3' WHERE rol = 'administrador'"))
        
        # 2. Alterar tipo de columna
        logger.info("Alterando tipo de columna a INTEGER...")
        conn.execute(text("ALTER TABLE usuarios ALTER COLUMN rol TYPE INTEGER USING (rol::integer)"))
        
        # 3. Establecer valor por defecto
        logger.info("Estableciendo valor por defecto a 1...")
        conn.execute(text("ALTER TABLE usuarios ALTER COLUMN rol SET DEFAULT 1"))
        
        conn.commit()
        logger.info("Migración completada exitosamente.")

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        logger.error(f"Error durante la migración: {e}")
