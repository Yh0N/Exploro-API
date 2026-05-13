import psycopg2
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

DB_NAME = os.getenv("POSTGRES_DB", "exploro_db")
DB_USER = os.getenv("POSTGRES_USER", "exploro_user")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "exploro_password")
DB_HOST = "localhost" # Desde fuera de docker usamos localhost
DB_PORT = os.getenv("POSTGRES_PORT", "5433")

def migrate():
    conn = None
    cur = None
    try:
        # Conectar a la base de datos
        print(f"Conectando a {DB_NAME} en {DB_HOST}:{DB_PORT} como {DB_USER}...")
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()

        print("--- Iniciando migración: Agregar id_usuario a lugares ---")

        # 1. Agregar columna id_usuario a la tabla lugares
        print("Agregando columna id_usuario a la tabla lugares...")
        cur.execute("""
            ALTER TABLE lugares 
            ADD COLUMN IF NOT EXISTS id_usuario INTEGER REFERENCES usuarios(id_usuario) ON DELETE SET NULL;
        """)

        # Confirmar cambios
        conn.commit()
        print("¡Migración completada exitosamente!")

    except Exception as e:
        print(f"Error durante la migración: {e}")
        if conn:
            conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate()
