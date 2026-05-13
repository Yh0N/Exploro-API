from app.schemas.pyme_schema import PymeCreate, PymeResponse
from app.schemas.recommendation_schema import (
    NearbyRecommendationResponse,
    PopularPlaceResponse,
    RecommendationResponse,
)


def test_pyme_schemas():
    p = PymeCreate(nombre="Mi Pyme", tipo="restaurante", ubicacion="Pasto")
    assert p.nombre == "Mi Pyme"
    r = PymeResponse(id_pyme=1, nombre="X", tipo="t", ubicacion=None, id_usuario=1)
    assert r.id_pyme == 1


def test_recommendation_response_schemas():
    RecommendationResponse(
        id_lugar=1,
        nombre="L",
        descripcion=None,
        latitud=1.0,
        longitud=-77.0,
        categoria="museo",
        calificacion_promedio=4.5,
        total_resenas=2,
        distancia_metros=10.0,
        score_recomendacion=0.5,
        razones=["a"],
        factores={"x": 1.0},
    )
    PopularPlaceResponse(
        id_lugar=1,
        nombre="L",
        descripcion=None,
        latitud=1.0,
        longitud=-77.0,
        categoria="museo",
        calificacion_promedio=4.0,
        total_resenas=3,
        score_popularidad=0.7,
    )
    NearbyRecommendationResponse(
        id_lugar=1,
        nombre="L",
        descripcion=None,
        latitud=1.0,
        longitud=-77.0,
        categoria="museo",
        calificacion_promedio=4.0,
        total_resenas=3,
        distancia_metros=100.0,
        score_recomendacion=0.6,
    )
