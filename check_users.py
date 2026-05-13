
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.connection import Base
from app.core.config import settings

# Import all models to avoid mapper errors
from app.models.user import Usuario
from app.models.profile import Perfil
from app.models.place import Lugar
from app.models.review import Reseña
from app.models.recommendation import Recomendacion
from app.models.pyme import Pyme
from app.models.auth_token import TokenRevocado

# Correctly replace only the host
import re
db_url = settings.DATABASE_URL
db_url = re.sub(r'@db:', '@localhost:', db_url)
db_url = db_url.replace(':5432/', ':5433/')

print(f"Connecting to: {db_url}")
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    users = db.query(Usuario).all()
    print(f"Found {len(users)} users:")
    for user in users:
        print(f"ID: {user.id_usuario}, Nombre: {user.nombre}, Correo: {user.correo}, Rol: {user.rol}")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
