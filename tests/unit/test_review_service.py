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
        crear_reseña(db, ReviewCreate(comentarios="x", puntuacion=5), usuario, id_lugar=1)
    assert exc.value.status_code == 404


def test_crear_reseña_duplicada():
    db = MagicMock()
    lugar = MagicMock()
    # Primera llamada: lugar existe; segunda llamada: reseña duplicada existe
    db.query.return_value.filter.return_value.first.side_effect = [lugar, object()]
    db.query.return_value.filter_by.return_value.first.return_value = object()
    usuario = MagicMock()
    usuario.id_usuario = 1
    with pytest.raises(HTTPException) as exc:
        crear_reseña(db, ReviewCreate(comentarios="x", puntuacion=4), usuario, id_lugar=1)
    assert exc.value.status_code == 400
