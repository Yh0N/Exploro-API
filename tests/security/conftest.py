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

# Tokens pre-obtenidos para SEC-PERM tests. Se llenan en _preregistrar_perm_users
# (fixture autouse session) ANTES de que TestRateLimiting agote los límites.
_perm_tokens_cache: dict[str, str] = {}

_PERM_USERS = [
    ("turista_perm@exploro.test",  "Perm1234!", 1),
    ("admin_perm@exploro.test",    "Perm1234!", 3),
    ("userA_perm@exploro.test",    "Perm1234!", 1),
    ("pyme_perm@exploro.test",     "Perm1234!", 2),
    ("autor_resena@exploro.test",  "Perm1234!", 1),
    ("otro_usuario@exploro.test",  "Perm1234!", 1),
    ("logout_test@exploro.test",   "Perm1234!", 1),
]


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
    """
    Instancia de la app FastAPI apuntando a la BD de seguridad (testcontainers).

    Crea un engine nuevo directamente desde security_db_url en lugar de reusar
    el engine de módulo, que puede estar cacheado con otra DATABASE_URL si los
    tests unitarios ya importaron app.database.connection.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import app.database.connection as db_module

    os.environ["DATABASE_URL"] = security_db_url

    new_engine = create_engine(security_db_url, pool_pre_ping=True)
    db_module.engine = new_engine
    db_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=new_engine)

    from app.main import app

    with new_engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.commit()
    db_module.Base.metadata.create_all(bind=new_engine)
    return app


@pytest.fixture(scope="session")
def security_engine(security_app):
    import app.database.connection as db_module
    return db_module.engine


@pytest.fixture(scope="session", autouse=True)
def _preregistrar_perm_users(security_app):
    """
    Pre-registra y autentica los usuarios que necesitan los tests SEC-PERM.
    Corre al inicio de la sesión (autouse session), ANTES de que TestRateLimiting
    consuma los límites de /auth/register (10/min) y /auth/login (20/min).
    Los tokens se guardan en _perm_tokens_cache para que _crear_y_loguear los reutilice.
    """
    from fastapi.testclient import TestClient
    with TestClient(security_app) as client:
        for correo, contraseña, rol in _PERM_USERS:
            r_reg = client.post("/auth/register", json={
                "nombre": f"Perm {rol}",
                "correo": correo,
                "contraseña": contraseña,
                "preferencias": [],
                "rol": rol,
            })
            if r_reg.status_code in (201, 409):
                r_login = client.post("/auth/login", json={"correo": correo, "contraseña": contraseña})
                if r_login.status_code == 200:
                    _perm_tokens_cache[correo] = r_login.json()["access_token"]


@pytest.fixture
def sec_client(security_app):
    """TestClient HTTP para los tests de seguridad con DB."""
    from fastapi.testclient import TestClient
    with TestClient(security_app) as c:
        yield c


@pytest.fixture(autouse=True)
def _limpiar_tablas(request):
    """
    Trunca tablas tras cada test de integración. Tests sin @integration no tocan la BD.
    Se excluye 'usuarios' de la truncación para que los tokens pre-cacheados de
    _preregistrar_perm_users sigan siendo válidos entre tests de TestControlDeAccesoPorRol.
    """
    if not request.node.get_closest_marker("integration"):
        yield
        return

    engine = request.getfixturevalue("security_engine")
    yield
    from app.database.connection import Base
    tablas = [t for t in reversed(Base.metadata.sorted_tables) if t.name != "usuarios"]
    names = ", ".join(f'"{t.name}"' for t in tablas)
    if names:
        with engine.connect() as conn:
            conn.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))
            conn.commit()


# ---------------------------------------------------------------------------
# Helpers reutilizables
# ---------------------------------------------------------------------------

def registrar_usuario(client, suffix: str, rol: int = 1) -> dict:
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
        json={"correo": correo, "contraseña": contraseña},
    )
    assert token_r.status_code == 200, token_r.text
    return {
        "correo": correo,
        "contraseña": contraseña,
        "token": token_r.json()["access_token"],
    }
