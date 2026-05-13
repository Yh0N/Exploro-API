"""
Integración HTTP + PostgreSQL/PostGIS.

IMPORTANTE: ejecutar solo ``pytest tests/integration`` en este proceso para que
``DATABASE_URL`` se fije antes del primer ``import app`` (ver flujo en CI).

- Local: USE_TESTCONTAINERS=1 (por defecto) y Testcontainers.
- CI: USE_TESTCONTAINERS=0 y DATABASE_URL al servicio PostGIS.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text


def _normalize_sqlalchemy_url(url: str) -> str:
    if url.startswith("postgresql://") and "+psycopg2" not in url:
        return "postgresql+psycopg2://" + url[len("postgresql://") :]
    return url


@pytest.fixture(scope="session")
def database_url_integration():
    use_tc = os.environ.get("USE_TESTCONTAINERS", "1").strip().lower() not in ("0", "false", "no")
    if not use_tc:
        raw = os.environ.get("DATABASE_URL") or os.environ.get("TEST_DATABASE_URL")
        if not raw:
            pytest.skip("USE_TESTCONTAINERS=0 requiere DATABASE_URL")
        yield _normalize_sqlalchemy_url(raw)
        return

    pytest.importorskip("testcontainers")
    try:
        from testcontainers.postgres import PostgresContainer
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Testcontainers no disponible: {exc}")

    try:
        with PostgresContainer("postgis/postgis:15-3.3") as pg:
            yield _normalize_sqlalchemy_url(pg.get_connection_url())
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"No se pudo iniciar PostGIS con Testcontainers: {exc}")


@pytest.fixture(scope="session")
def integration_app(database_url_integration):
    os.environ["DATABASE_URL"] = database_url_integration

    from app.database.connection import Base, engine
    from app.main import app

    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    return app


@pytest.fixture(scope="session")
def integration_engine(integration_app):
    from app.database.connection import engine

    return engine


@pytest.fixture
def db_session(integration_engine):
    from app.database.connection import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(integration_app):
    from fastapi.testclient import TestClient

    with TestClient(integration_app) as c:
        yield c


@pytest.fixture(autouse=True)
def _truncate_after_test(integration_engine):
    yield
    from app.database.connection import Base

    names = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
    if not names:
        return
    with integration_engine.connect() as conn:
        conn.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))
        conn.commit()
