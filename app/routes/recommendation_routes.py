"""
Rutas de recomendaciones de EXPLORO.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.connection import get_db
from app.models.user import Usuario
from app.schemas.recommendation_schema import (
    NearbyRecommendationResponse,
    PopularPlaceResponse,
    RecommendationResponse,
)
from app.services.recommendation_service import (
    obtener_lugares_populares,
    obtener_recomendaciones_cercanas,
    obtener_recomendaciones_personalizadas,
)

router = APIRouter(prefix="/recommendations", tags=["Recomendaciones"])


@router.get(
    "",
    response_model=List[RecommendationResponse],
    summary="Recomendaciones personalizadas",
    description=(
        "Genera recomendaciones personalizadas mezclando preferencias del usuario, "
        "historial de reseñas, popularidad del lugar y cercanía geográfica."
    ),
)
def get_recommendations(
    latitud: Optional[float] = Query(None, ge=-90, le=90, description="Latitud del usuario"),
    longitud: Optional[float] = Query(None, ge=-180, le=180, description="Longitud del usuario"),
    radio_km: float = Query(5.0, gt=0, le=50, description="Radio de búsqueda en km"),
    limite: int = Query(10, ge=1, le=50, description="Número máximo de resultados"),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return obtener_recomendaciones_personalizadas(
        db=db,
        usuario=current_user,
        latitud=latitud,
        longitud=longitud,
        radio_km=radio_km,
        limite=limite,
    )


@router.get(
    "/popular",
    response_model=List[PopularPlaceResponse],
    summary="Lugares populares",
    description="Obtiene los lugares con mejor mezcla entre valoración promedio y volumen de reseñas",
)
def get_popular(
    limite: int = Query(10, ge=1, le=50, description="Número máximo de resultados"),
    db: Session = Depends(get_db),
):
    return obtener_lugares_populares(db, limite)


@router.get(
    "/nearby",
    response_model=List[NearbyRecommendationResponse],
    summary="Recomendaciones cercanas",
    description="Recomienda lugares cercanos mezclando distancia y calidad percibida",
)
def get_nearby_recommendations(
    latitud: float = Query(..., ge=-90, le=90, description="Latitud del punto de referencia"),
    longitud: float = Query(..., ge=-180, le=180, description="Longitud del punto de referencia"),
    radio_km: float = Query(2.0, gt=0, le=50, description="Radio de búsqueda en km"),
    limite: int = Query(10, ge=1, le=50, description="Número máximo de resultados"),
    db: Session = Depends(get_db),
):
    return obtener_recomendaciones_cercanas(db, latitud, longitud, radio_km, limite)
