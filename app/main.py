"""
Punto de entrada principal de la API EXPLORO.
Configura FastAPI, registra todos los routers y crea las tablas
de la base de datos al iniciar.

Documentación Swagger disponible en: http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.database.connection import engine, Base

# Importar TODOS los modelos para que SQLAlchemy los registre en el metadata
from app.models.user import Usuario
from app.models.profile import Perfil
from app.models.place import Lugar
from app.models.review import Reseña
from app.models.recommendation import Recomendacion
from app.models.pyme import Pyme
from app.models.auth_token import TokenRevocado

# Importar routers
from app.routes.auth_routes import router as auth_router
from app.routes.user_routes import router as user_router
from app.routes.place_routes import router as place_router
from app.routes.review_routes import router as review_router
from app.routes.recommendation_routes import router as recommendation_router
from app.routes.pyme_routes import router as pyme_router
from app.routes.admin_routes import router as admin_router
from app.routes.upload_routes import router as upload_router


# Crear la aplicación FastAPI
app = FastAPI(
    title="EXPLORO API",
    description=(
        "API RESTful inteligente de recomendaciones turísticas para la ciudad de Pasto, Colombia. "
        "Conecta la oferta turística de pymes locales con turistas, estudiantes foráneos "
        "y nuevos residentes. Gestiona lugares turísticos, usuarios, reseñas y genera "
        "recomendaciones personalizadas basadas en preferencias, geolocalización "
        "y comportamiento del usuario."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS para permitir solicitudes desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "https://1h4bg5xs-3000.use2.devtunnels.ms",
    ],
    allow_origin_regex=r"https://.*\.devtunnels\.ms",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir archivos estáticos (fotos subidas)
if not os.path.exists("uploads"):
    os.makedirs("uploads")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# Evento de inicio: crear tablas en la base de datos si no existen
@app.on_event("startup")
def on_startup():
    """
    Se ejecuta al iniciar la aplicación.
    Crea todas las tablas definidas en los modelos si no existen.
    NOTA: Para producción se recomienda usar Alembic para migraciones.
    """
    Base.metadata.create_all(bind=engine)


# Registrar todos los routers de la API
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(place_router)
app.include_router(review_router)
app.include_router(recommendation_router)
app.include_router(pyme_router)
app.include_router(admin_router)
app.include_router(upload_router)


# Endpoint raíz (health check)
@app.get("/", tags=["Health"])
def home():
    """Verifica que la API está funcionando correctamente."""
    return {
        "message": "EXPLORO API funcionando",
        "version": "1.0.0",
        "docs": "/docs"
    }
