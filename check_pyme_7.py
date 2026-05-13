
import os
import re
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.connection import Base
from app.core.config import settings

# Import all models
from app.models.user import Usuario
from app.models.profile import Perfil
from app.models.place import Lugar
from app.models.review import Reseña
from app.models.recommendation import Recomendacion
from app.models.pyme import Pyme
from app.models.auth_token import TokenRevocado

db_url = settings.DATABASE_URL
db_url = re.sub(r'@db:', '@localhost:', db_url)
db_url = db_url.replace(':5432/', ':5433/')

engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    pyme = db.query(Pyme).filter(Pyme.id_pyme == 7).first()
    if pyme:
        print(f"Pyme ID: {pyme.id_pyme}")
        print(f"Nombre: {pyme.nombre}")
        print(f"Aprobado: {pyme.aprobado}")
        print(f"Latitud: {pyme.latitud}")
        print(f"Longitud: {pyme.longitud}")
        print(f"Ubicacion Textual: {pyme.ubicacion_textual}")
    else:
        print("Pyme with ID 7 not found")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
