"""
Fixtures para las pruebas de seguridad de Exploro API.

Los tests marcados con @pytest.mark.integration necesitan una base de datos
PostgreSQL + PostGIS real.  En local se levanta automaticamente con
Testcontainers (USE_TESTCONTAINERS=1, por defecto).

Los tests de JWT/tokens funcionan sin base de datos (mocks).
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text


def _normalize_url(url: str) -> str:
    if url.startswith("postgresql://") and "+psycopg2" not in url:
        return "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


# ---------------------------------------------------------------------------
# Base de datos para tests de seguridad que necesitan DB real
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def security_db_url():
    """URL de la BD de seguridad (Testcontainers o variable de entorno)."""
    use_tc = os.environ.get("USE_TESTCONTAINERS", "1").strip().lower() not in ("0", "false", "no")
    if not use_tc:
        raw = os.environ.get("DATABASE_URL") or os.environ.get("TEST_DATABASE_URL")
        if not raw:
            pytest.skip("USE_TESTCONTAINERS=0 requiere DATABASE_URL")
        yield _normalize_url(raw)
        return

    pytest.importorskip("testcontainers", reason="pip install testcontainers[postgres]")
    try:
        from testcontainers.postgres import PostgresContainer
    except Exception as exc:
        pytest.skip(f"Testcontainers no disponible: {exc}")
        return

    try:
        with PostgresContainer("postgis/postgis:15-3.3") as pg:
            yield _normalize_url(pg.get_connection_url())
    except Exception as exc:
        pytest.skip(f"No se pudo iniciar PostGIS: {exc}")


@pytest.fixture(scope="session")
def security_app(security_db_url):
    """Instancia de la app FastAPI apuntando a la BD de seguridad."""
    os.environ["DATABASE_URL"] = security_db_url

    from app.database.connection import Base, engine
    from app.main import app

    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    return app


@pytest.fixture(scope="session")
def security_engine(security_app):
    from app.database.connection import engine
    return engine


@pytest.fixture
def sec_client(security_app):
    """TestClient HTTP para los tests de seguridad con DB."""
    from fastapi.testclient import TestClient
    with TestClient(security_app) as c:
        yield c


@pytest.fixture(autouse=True)
def _limpiar_tablas(request):
    """Trunca tablas tras cada test de integración. Tests sin @integration no tocan la BD."""
    if not request.node.get_closest_marker("integration"):
        yield
        return

    engine = request.getfixturevalue("security_engine")
    yield
    from app.database.connection import Base
    names = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
    if names:
        with engine.connect() as conn:
            conn.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))
            conn.commit()


# ---------------------------------------------------------------------------
# Helpers reutilizables
# ---------------------------------------------------------------------------

def registrar_usuario(client, suffix: str, rol: str = "usuario_regular") -> dict:
    """Registra un usuario y retorna {correo, contraseña, token}."""
    correo = f"sec_{suffix}@exploro.test"
    contraseña = "SecTest1234!"
    r = client.post(
        "/auth/register",
        json={
            "nombre": f"Sec {suffix}",
            "correo": correo,
            "contraseña": contraseña,
            "preferencias": [],
            "rol": rol,
        },
    )
    assert r.status_code == 201, r.text
    token_r = client.post(
        "/auth/login",
        data={"username": correo, "password": contraseña},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert token_r.status_code == 200, token_r.text
    return {
        "correo": correo,
        "contraseña": contraseña,
        "token": token_r.json()["access_token"],
    }
