from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.schemas.place_schema import PlaceCreate, PlaceUpdate
from app.services.place_service import (
    _obtener_estadisticas_resenas,
    agregar_calificacion,
    crear_lugar,
    eliminar_lugar,
    listar_lugares,
    obtener_lugar,
)


def test_obtener_estadisticas_resenas_con_y_sin_datos():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = (4.3333, 3)
    avg, count = _obtener_estadisticas_resenas(db, 1)
    assert avg == 4.33
    assert count == 3

    db.query.return_value.filter.return_value.first.return_value = (None, 0)
    avg, count = _obtener_estadisticas_resenas(db, 1)
    assert avg is None
    assert count == 0


def test_agregar_calificacion():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = (5.0, 1)
    d = {"id_lugar": 2}
    res = agregar_calificacion(d, db)
    assert res["calificacion_promedio"] == 5.0
    assert res["numero_reseñas"] == 1


def test_obtener_lugar_404():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        obtener_lugar(db, 99)
    assert exc.value.status_code == 404


def test_eliminar_lugar_404():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        eliminar_lugar(db, 99)
    assert exc.value.status_code == 404


def test_listar_lugares_sin_filtros():
    db = MagicMock()
    lugar = MagicMock()
    lugar.id_lugar = 1
    lugar.nombre = "N"
    lugar.descripcion = None
    lugar.latitud = 1.0
    lugar.longitud = -77.0
    lugar.categoria = "museo"
    lugar.aprobado = True
    db.query.return_value.outerjoin.return_value.filter.return_value.group_by.return_value.all.return_value = [
        (lugar, 4.5, 10)
    ]
    out = listar_lugares(db)
    assert len(out) == 1
    assert out[0]["calificacion_promedio"] == 4.5


def test_crear_lugar_persiste(monkeypatch):
    db = MagicMock()
    nuevo = MagicMock()
    nuevo.id_lugar = 5
    nuevo.nombre = "Lu"
    nuevo.descripcion = "d"
    nuevo.latitud = 1.2
    nuevo.longitud = -77.2
    nuevo.categoria = "parque"
    nuevo.aprobado = False

    monkeypatch.setattr("app.services.place_service.Lugar", MagicMock(return_value=nuevo))

    datos = PlaceCreate(
        nombre="Lu",
        descripcion="d",
        latitud=1.2,
        longitud=-77.2,
        categoria="parque",
    )
    out = crear_lugar(db, datos)
    assert out["id_lugar"] == 5
    db.add.assert_called_once()
    db.commit.assert_called_once()
