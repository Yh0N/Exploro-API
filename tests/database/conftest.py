"""
Fixtures para pruebas de base de datos de Exploro API.
Reutiliza el mismo patrón de Testcontainers que tests/integration.
"""
from __future__ import annotations

import os
import pytest
from sqlalchemy import text


def _normalize_url(url: str) -> str:
    if url.startswith("postgresql://") and "+psycopg2" not in url:
        return "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


@pytest.fixture(scope="session")
def db_database_url():
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
def db_app(db_database_url):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import app.database.connection as db_module

    os.environ["DATABASE_URL"] = db_database_url

    new_engine = create_engine(db_database_url, pool_pre_ping=True)
    db_module.engine = new_engine
    db_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=new_engine)

    from app.main import app

    with new_engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.commit()
    db_module.Base.metadata.create_all(bind=new_engine)
    return app


@pytest.fixture(scope="session")
def db_engine(db_app):
    import app.database.connection as db_module
    return db_module.engine


@pytest.fixture
def db_session(db_engine):
    from app.database.connection import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_app):
    from fastapi.testclient import TestClient
    with TestClient(db_app) as c:
        yield c


@pytest.fixture(autouse=True)
def _limpiar_tablas(request, db_engine):
    if not request.node.get_closest_marker("integration"):
        yield
        return
    yield
    from app.database.connection import Base
    names = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
    if names:
        with db_engine.connect() as conn:
            conn.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))
            conn.commit()
