"""
Configuración central de la aplicación EXPLORO.
Usa pydantic-settings para cargar variables de entorno desde el archivo .env.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Clase de configuración que carga automáticamente las variables
    de entorno definidas en el archivo .env del proyecto.
    """

    # Configuración de la base de datos PostgreSQL
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: str = "5432"

    # URL de conexión a la base de datos (generada o directa desde .env)
    DATABASE_URL: str

    # Configuración de autenticación JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    class Config:
        """Configuración de pydantic-settings para leer el archivo .env"""
        env_file = ".env"
        extra = "allow"


# Instancia global de configuración, accesible desde cualquier módulo
settings = Settings()
