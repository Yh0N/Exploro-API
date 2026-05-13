from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
from app.core import security


def test_hash_y_verify_password():
    h = security.hash_password("miClaveSegura")
    assert h != "miClaveSegura"
    assert security.verify_password("miClaveSegura", h) is True
    assert security.verify_password("otra", h) is False


def test_create_access_token_y_verify_token():
    token = security.create_access_token({"sub": "a@b.com"})
    payload = security.verify_token(token)
    assert payload["sub"] == "a@b.com"
    assert "exp" in payload


def test_verify_token_invalido():
    with pytest.raises(HTTPException) as exc:
        security.verify_token("no-es-un-jwt")
    assert exc.value.status_code == 401


def test_require_role_permite_y_deniega():
    app = FastAPI()

    @app.get("/admin")
    def ruta_admin(user=Depends(security.require_role(["administrador"]))):
        return {"rol": user.rol}

    cliente = TestClient(app)
    ok = SimpleNamespace(rol="administrador")
    app.dependency_overrides[security.get_current_user] = lambda: ok
    assert cliente.get("/admin").status_code == 200

    bad = SimpleNamespace(rol="usuario_regular")
    app.dependency_overrides[security.get_current_user] = lambda: bad
    assert cliente.get("/admin").status_code == 403


def test_get_current_user_token_revocado():
    app = FastAPI()

    @app.get("/me")
    def me(user=Depends(security.get_current_user)):
        return {"correo": user.correo}

    token = security.create_access_token({"sub": "x@example.com"})
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = object()

    app.dependency_overrides[security.oauth2_scheme] = lambda: token
    app.dependency_overrides[security.get_db] = lambda: db

    cliente = TestClient(app)
    assert cliente.get("/me").status_code == 401
