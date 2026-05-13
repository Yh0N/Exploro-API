from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.schemas.user_schema import UserCreate, UserLogin
from app.services.auth_service import login_usuario, logout_usuario, registrar_usuario


def test_registrar_usuario_correo_duplicado():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = object()
    datos = UserCreate(
        nombre="Ana",
        correo="ana@example.com",
        contraseña="Secret123!",
        preferencias=[],
        rol="usuario_regular",
    )
    with pytest.raises(HTTPException) as exc:
        registrar_usuario(db, datos)
    assert exc.value.status_code == 400


def test_login_usuario_usuario_inexistente():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        login_usuario(db, UserLogin(correo="x@y.com", contraseña="x"))
    assert exc.value.status_code == 401


def test_login_usuario_password_incorrecta(monkeypatch):
    db = MagicMock()
    usuario = MagicMock()
    usuario.contraseña = "hash"
    db.query.return_value.filter.return_value.first.return_value = usuario

    monkeypatch.setattr("app.services.auth_service.verify_password", lambda p, h: False)

    with pytest.raises(HTTPException) as exc:
        login_usuario(db, UserLogin(correo="x@y.com", contraseña="mala"))
    assert exc.value.status_code == 401


def test_logout_usuario_persiste_revocacion(monkeypatch):
    db = MagicMock()
    usuario = MagicMock()
    usuario.id_usuario = 1
    token = "t" * 20

    monkeypatch.setattr(
        "app.services.auth_service.verify_token",
        lambda t: {"sub": "x@y.com", "exp": 9999999999},
    )

    out = logout_usuario(db, token, usuario)
    assert "message" in out
    db.add.assert_called_once()
    db.commit.assert_called_once()
