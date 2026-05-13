"""
Configuración global de pytest: variables de entorno mínimas para importar la app
sin depender de un .env local (CI y desarrollo).
"""

from __future__ import annotations

import os


def pytest_configure(config) -> None:
    os.environ.setdefault("POSTGRES_USER", "test")
    os.environ.setdefault("POSTGRES_PASSWORD", "test")
    os.environ.setdefault("POSTGRES_DB", "test")
    os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
    os.environ.setdefault("POSTGRES_PORT", "5432")
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+psycopg2://test:test@127.0.0.1:5432/test",
    )
    os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-32b-minimo!!")
    os.environ.setdefault("ALGORITHM", "HS256")
    os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
