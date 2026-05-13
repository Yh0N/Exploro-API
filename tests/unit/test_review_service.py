from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.schemas.review_schema import ReviewCreate
from app.services.review_service import crear_reseña


def test_crear_reseña_lugar_inexistente():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    usuario = MagicMock()
    with pytest.raises(HTTPException) as exc:
        crear_reseña(db, 1, ReviewCreate(comentarios="x", puntuacion=5), usuario)
    assert exc.value.status_code == 404


def test_crear_reseña_duplicada():
    db = MagicMock()
    lugar = MagicMock()
    db.query.return_value.filter.return_value.first.side_effect = [lugar, object()]
    usuario = MagicMock()
    usuario.id_usuario = 1
    with pytest.raises(HTTPException) as exc:
        crear_reseña(db, 1, ReviewCreate(comentarios="x", puntuacion=4), usuario)
    assert exc.value.status_code == 400
