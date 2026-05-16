"""
Punto de entrada principal de la API EXPLORO.
Configura FastAPI, registra todos los routers y crea las tablas
de la base de datos al iniciar.

Documentación Swagger disponible en: http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import os

# Importaciones para rate limiting
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter

from app.database.connection import engine, Base

# Importar TODOS los modelos para que SQLAlchemy los registre en el metadata
from app.models.user import Usuario
from app.models.profile import Perfil
from app.models.place import Lugar
from app.models.review import Reseña
from app.models.recommendation import Recomendacion
from app.models.pyme import Pyme
from app.models.auth_token import TokenRevocado
from app.models.image import Imagen

# Importar routers
from app.routes.auth_routes import router as auth_router
from app.routes.user_routes import router as user_router
from app.routes.place_routes import router as place_router
from app.routes.review_routes import router as review_router
from app.routes.recommendation_routes import router as recommendation_router
from app.routes.pyme_routes import router as pyme_router
from app.routes.admin_routes import router as admin_router
from app.routes.upload_routes import router as upload_router
from app.routes.image_routes import router as image_router
from app.api.v1.endpoints.auth import router as oauth_router


# ─────────────────────────────────────────────────────────────────
# MIDDLEWARE: Límite de tamaño de solicitudes (TAREA 4)
# Rechaza cualquier POST que supere 5 MB antes de procesarlo
# ─────────────────────────────────────────────────────────────────

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB en bytes


class LimitUploadSize(BaseHTTPMiddleware):
    """
    Middleware que rechaza solicitudes POST cuyo Content-Length supere
    el límite configurado (5 MB). Previene ataques de subida masiva.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST":
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > MAX_UPLOAD_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "El archivo supera el tamaño máximo permitido de 5 MB"}
                )
        return await call_next(request)


# ─────────────────────────────────────────────────────────────────
# INSTANCIA DE LA APLICACIÓN
# ─────────────────────────────────────────────────────────────────

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

# ─────────────────────────────────────────────────────────────────
# RATE LIMITING (TAREA 1)
# Registrar el limiter en el estado de la app y su manejador de error
# ─────────────────────────────────────────────────────────────────

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─────────────────────────────────────────────────────────────────
# CORS RESTRICTIVO (TAREA 6)
# Solo se permiten orígenes conocidos; sin wildcards en producción
# ─────────────────────────────────────────────────────────────────

# Orígenes permitidos (CORS)
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
origins = [
    frontend_url,
    "https://airbnb-clone-exploro.vercel.app",  # Vercel forzado
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Aplicar middleware de límite de tamaño primero
app.add_middleware(LimitUploadSize)

# CORS debe ser lo ÚLTIMO en agregarse (para que sea lo PRIMERO en ejecutarse)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────
# ARCHIVOS ESTÁTICOS
# ─────────────────────────────────────────────────────────────────

# Servir archivos estáticos (fotos subidas)
if not os.path.exists("uploads"):
    os.makedirs("uploads")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# ─────────────────────────────────────────────────────────────────
# EVENTOS DE CICLO DE VIDA
# ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
def on_startup():
    """
    Se ejecuta al iniciar la aplicación.
    Crea todas las tablas definidas en los modelos si no existen.
    NOTA: Para producción se recomienda usar Alembic para migraciones.
    """
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
    Base.metadata.create_all(bind=engine)


# ─────────────────────────────────────────────────────────────────
# ROUTERS
# ─────────────────────────────────────────────────────────────────

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(place_router)
app.include_router(review_router)
app.include_router(recommendation_router)
app.include_router(pyme_router)
app.include_router(admin_router)
app.include_router(upload_router)

# Router OAuth2 con Google (prefijo /api/v1/auth/...)
app.include_router(oauth_router, prefix="/api/v1")
# Router de imágenes RF12 (prefijo /api/v1/imagenes/...)
app.include_router(image_router, prefix="/api/v1")


# ─────────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def home():
    """Verifica que la API está funcionando correctamente."""
    return {
        "message": "EXPLORO API funcionando",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Endpoint dedicado para health checks de Render/Docker."""
    return {"status": "healthy", "version": "1.0.0"}
