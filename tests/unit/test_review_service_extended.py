from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.services.review_service import eliminar_reseña, listar_reseñas


def test_listar_reseñas_ok():
    db = MagicMock()
    lugar = MagicMock()
    reseña = MagicMock()
    reseña.id_resena = 1
    reseña.id_usuario = 2
    reseña.id_lugar = 3
    reseña.comentarios = "ok"
    reseña.puntuacion = 5
    reseña.fecha = None

    def query_side_effect(*args, **kwargs):
        if len(args) == 1:
            m = MagicMock()
            m.filter.return_value.first.return_value = lugar
            return m
        m = MagicMock()
        m.join.return_value.filter.return_value.order_by.return_value.all.return_value = [(reseña, "Ana")]
        return m

    db.query.side_effect = query_side_effect

    out = listar_reseñas(db, 3)
    assert len(out) == 1
    assert out[0]["nombre_usuario"] == "Ana"


def test_listar_reseñas_lugar_inexistente():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        listar_reseñas(db, 9)
    assert exc.value.status_code == 404


def test_eliminar_reseña_autor():
    db = MagicMock()
    reseña = MagicMock()
    reseña.id_usuario = 5
    usuario = MagicMock()
    usuario.id_usuario = 5
    usuario.rol = "usuario_regular"

    db.query.return_value.filter.return_value.first.return_value = reseña

    out = eliminar_reseña(db, 10, usuario)
    assert "message" in out
    db.delete.assert_called_once_with(reseña)
    db.commit.assert_called_once()


def test_eliminar_reseña_admin():
    db = MagicMock()
    reseña = MagicMock()
    reseña.id_usuario = 5
    admin = MagicMock()
    admin.id_usuario = 1
    admin.rol = "administrador"

    db.query.return_value.filter.return_value.first.return_value = reseña

    eliminar_reseña(db, 10, admin)
    db.delete.assert_called_once()


def test_eliminar_reseña_sin_permiso():
    db = MagicMock()
    reseña = MagicMock()
    reseña.id_usuario = 5
    otro = MagicMock()
    otro.id_usuario = 9
    otro.rol = "usuario_regular"

    db.query.return_value.filter.return_value.first.return_value = reseña

    with pytest.raises(HTTPException) as exc:
        eliminar_reseña(db, 10, otro)
    assert exc.value.status_code == 403


def test_eliminar_reseña_no_existe():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        eliminar_reseña(db, 99, MagicMock())
    assert exc.value.status_code == 404
