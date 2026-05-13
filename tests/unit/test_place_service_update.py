from unittest.mock import MagicMock

from app.schemas.place_schema import PlaceUpdate
from app.services.place_service import actualizar_lugar


def test_actualizar_lugar_coordenadas_reconstruye_punto(monkeypatch):
    db = MagicMock()
    lugar = MagicMock()
    lugar.id_lugar = 1
    lugar.nombre = "N"
    lugar.descripcion = None
    lugar.latitud = 1.0
    lugar.longitud = -77.0
    lugar.categoria = "museo"
    lugar.aprobado = True
    lugar.ubicacion = None

    db.query.return_value.filter.return_value.first.return_value = lugar

    monkeypatch.setattr(
        "app.services.place_service._calcular_calificacion",
        lambda session, id_lugar: 4.0,
    )

    datos = PlaceUpdate(latitud=1.5, longitud=-77.5)
    out = actualizar_lugar(db, 1, datos)

    assert out["latitud"] == 1.5
    assert lugar.ubicacion is not None
    db.commit.assert_called_once()
