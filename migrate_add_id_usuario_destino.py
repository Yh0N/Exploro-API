import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Configuración de base de datos usando variables de entorno o defaults
DB_HOST = "localhost"
DB_PORT = os.getenv("POSTGRES_PORT", "5433")
DB_NAME = os.getenv("POSTGRES_DB", "exploro_db")
DB_USER = os.getenv("POSTGRES_USER", "exploro_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "exploro_password")

def main():
    try:
        print(f"Conectando a postgresql://{DB_USER}:***@{DB_HOST}:{DB_PORT}/{DB_NAME}")
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.autocommit = True
        cur = conn.cursor()

        # Añadir id_usuario_destino si no existe
        print("Añadiendo columna 'id_usuario_destino' a 'resenas'...")
        cur.execute("""
            ALTER TABLE resenas 
            ADD COLUMN IF NOT EXISTS id_usuario_destino INTEGER REFERENCES usuarios(id_usuario) ON DELETE CASCADE;
        """)
        print("Columna añadida correctamente.")

        cur.close()
        conn.close()
        print("Migración completada exitosamente.")

    except Exception as e:
        print(f"Error en la migración: {e}")

if __name__ == "__main__":
    main()
