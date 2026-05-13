import sys
import os

# Añadir el directorio raíz al path para poder importar la app
sys.path.append(os.getcwd())

from app.database.connection import engine, Base
from app.models.user import Usuario
from app.models.place import Lugar
# Importar la tabla de asociación favoritos que está en el modelo user
from app.models.user import favoritos

def run_migrations():
    print("Iniciando creación de tablas (migración)...")
    try:
        # Esto creará la tabla 'favoritos' si no existe
        Base.metadata.create_all(bind=engine)
        print("Tablas actualizadas exitosamente.")
    except Exception as e:
        print(f"Error durante la migración: {e}")

if __name__ == "__main__":
    run_migrations()
