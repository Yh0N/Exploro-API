from unittest.mock import MagicMock

import pytest

from app.services.recommendation_service import (
    _construir_razones,
    _normalizar,
    _obtener_afinidad_por_categoria,
    _persistir_recomendaciones,
    _score_afinidad_categoria,
    _score_distancia,
    _score_novedad,
    _score_popularidad,
    _score_preferencia,
)


def test_normalizar_rango_y_bordes():
    assert _normalizar(5, 0, 10) == 0.5
    assert _normalizar(0, 0, 10) == 0.0
    assert _normalizar(10, 0, 10) == 1.0
    assert _normalizar(15, 0, 10) == 1.0
    assert _normalizar(-1, 0, 10) == 0.0
    assert _normalizar(3, 5, 5) == 0.0


def test_score_preferencia_prioriza_categoria_coincidente():
    assert _score_preferencia("museo", ["museo", "parque"]) == 1.0
    assert _score_preferencia("hotel", ["museo", "parque"]) == 0.0


def test_score_afinidad_categoria_limita_rango():
    assert _score_afinidad_categoria("museo", {"museo": 0.8}) == 0.8
    assert _score_afinidad_categoria("x", {}) == 0.0
    assert _score_afinidad_categoria("x", {"x": 2.0}) == 1.0


def test_score_distancia_premia_lugares_cercanos():
    cercano = _score_distancia(200, 2000)
    lejano = _score_distancia(1800, 2000)
    assert cercano > lejano


def test_score_distancia_sin_radio_o_coordenadas():
    assert _score_distancia(100, None) == 0.0
    assert _score_distancia(None, 1000) == 0.0
    assert _score_distancia(100, 0) == 0.0


def test_score_popularidad_equilibra_rating_y_volumen():
    con_pocas_resenas = _score_popularidad(5.0, 1, 50)
    con_muchas_resenas = _score_popularidad(4.6, 40, 50)
    assert con_muchas_resenas > con_pocas_resenas


def test_score_novedad_disminuye_si_ya_se_recomendo_muchas_veces():
    assert _score_novedad(0) > _score_novedad(4)


def test_construir_razones_incluye_mensaje_por_defecto():
    razones = _construir_razones(
        categoria="hotel",
        preferencias=["museo"],
        afinidad_categoria=0.1,
        distancia_metros=None,
        total_resenas=0,
        calificacion_promedio=3.0,
    )
    assert any("relevante" in r.lower() for r in razones)


def test_construir_razones_pref_afinidad_distancia_valoracion():
    r1 = _construir_razones("museo", ["museo"], 0.0, None, 1, None)
    assert any("preferencia" in x.lower() for x in r1)

    r2 = _construir_razones("parque", [], 0.8, 120.0, 1, 3.0)
    assert any("categoria" in x.lower() for x in r2)
    assert any("ubicacion" in x.lower() or "cerca" in x.lower() for x in r2)

    r3 = _construir_razones("tour", [], 0.0, None, 4, 4.5)
    assert any("valoracion" in x.lower() or "valoración" in x.lower() for x in r3)
    assert any("resenas" in x.lower() or "reseñas" in x.lower() for x in r3)


def test_obtener_afinidad_por_categoria_agrupa_resenas():
    db = MagicMock()
    filas = [("museo", 5.0), ("parque", 3.0)]
    db.query.return_value.join.return_value.filter.return_value.group_by.return_value.all.return_value = filas
    usuario = MagicMock()
    usuario.id_usuario = 1

    out = _obtener_afinidad_por_categoria(db, usuario)
    assert "museo" in out and "parque" in out
    assert out["museo"] >= out["parque"]


def test_persistir_recomendaciones_inserta_solo_nuevos():
    db = MagicMock()
    usuario = MagicMock()
    usuario.id_usuario = 7

    db.query.return_value.filter.return_value.all.return_value = [(3,)]

    from app.models.recommendation import Recomendacion

    _persistir_recomendaciones(
        db,
        usuario,
        [
            {"id_lugar": 3},
            {"id_lugar": 4},
        ],
    )

    db.add_all.assert_called_once()
    agregados = db.add_all.call_args[0][0]
    assert len(agregados) == 1
    assert isinstance(agregados[0], Recomendacion)
    assert agregados[0].id_lugar == 4
    db.commit.assert_called_once()


def test_persistir_recomendaciones_no_op_si_vacio():
    db = MagicMock()
    usuario = MagicMock()
    _persistir_recomendaciones(db, usuario, [])
    db.add_all.assert_not_called()
    db.commit.assert_not_called()
