"""
Configuración central de la aplicación EXPLORO.
Usa pydantic-settings para cargar variables de entorno desde el archivo .env.
"""

from typing import Optional
from pydantic import field_validator
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
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Configuración OAuth2 Google ──────────────────────────────────
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    # URL de callback que Google devolverá el código de autorización
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"

    # URL base del frontend para construir redirects OAuth
    FRONTEND_URL: str = "http://localhost:3000"

    # ─────────────────────────────────────────────────────────────────
    # TAREA 2: Validación de SECRET_KEY (mínimo 32 caracteres)
    # ─────────────────────────────────────────────────────────────────

    @field_validator("SECRET_KEY")
    @classmethod
    def validar_secret_key(cls, v: str) -> str:
        """
        Verifica que la SECRET_KEY tenga al menos 32 caracteres.
        Una clave corta hace que los JWT sean vulnerables a fuerza bruta.
        Genera una segura con: openssl rand -hex 32
        """
        if len(v) < 32:
            raise ValueError(
                "SECRET_KEY debe tener mínimo 32 caracteres. "
                "Genera una con: openssl rand -hex 32"
            )
        return v

    class Config:
        """Configuración de pydantic-settings para leer el archivo .env"""
        env_file = ".env"
        extra = "allow"

    # ─────────────────────────────────────────────────────────────────
    # TAREA 7: Validación de variables de entorno críticas al arrancar
    # ─────────────────────────────────────────────────────────────────

    @classmethod
    def validate_env(cls, instance: "Settings") -> None:
        """
        Verifica que todas las variables de entorno críticas estén definidas.
        Se llama tras instanciar Settings. Si falta alguna, lanza RuntimeError
        con la lista de variables ausentes para facilitar el diagnóstico.
        """
        variables_criticas = {
            "SECRET_KEY": instance.SECRET_KEY,
            "DATABASE_URL": instance.DATABASE_URL,
            "GOOGLE_CLIENT_ID": instance.GOOGLE_CLIENT_ID,
            "GOOGLE_CLIENT_SECRET": instance.GOOGLE_CLIENT_SECRET,
        }

        faltantes = [
            nombre
            for nombre, valor in variables_criticas.items()
            if not valor or str(valor).strip() == ""
        ]

        if faltantes:
            raise RuntimeError(
                f"Faltan variables de entorno críticas: {', '.join(faltantes)}. "
                "Revisa tu archivo .env o las variables de entorno del servidor."
            )


# ─────────────────────────────────────────────────────────────────
# Instancia global de configuración, accesible desde cualquier módulo
# ─────────────────────────────────────────────────────────────────

settings = Settings()

# Validar variables críticas al arrancar la aplicación (TAREA 7)
Settings.validate_env(settings)
