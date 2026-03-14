"""
Rutas de recomendaciones de EXPLORO.
Endpoints para obtener recomendaciones personalizadas,
lugares populares y recomendaciones por ubicación.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.recommendation_service import (
    obtener_recomendaciones_personalizadas,
    obtener_lugares_populares,
    obtener_recomendaciones_cercanas
)
from app.core.security import get_current_user
from app.models.user import Usuario

router = APIRouter(prefix="/recommendations", tags=["Recomendaciones"])


@router.get(
    "",
    summary="Recomendaciones personalizadas",
    description="Genera recomendaciones basadas en las preferencias del usuario"
)
def get_recommendations(
    latitud: Optional[float] = Query(None, ge=-90, le=90, description="Latitud del usuario"),
    longitud: Optional[float] = Query(None, ge=-180, le=180, description="Longitud del usuario"),
    radio_km: float = Query(5.0, gt=0, le=50, description="Radio de búsqueda en km"),
    limite: int = Query(10, ge=1, le=50, description="Número máximo de resultados"),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Genera recomendaciones personalizadas para el usuario autenticado.
    
    Algoritmo Fase 1:
    1. Filtra por las categorías de preferencia del usuario
    2. Excluye lugares que ya reseñó
    3. Si se proporcionan coordenadas, filtra por distancia
    4. Ordena por calificación promedio
    """
    return obtener_recomendaciones_personalizadas(
        db, current_user, latitud, longitud, radio_km, limite
    )


@router.get(
    "/popular",
    summary="Lugares populares",
    description="Obtiene los lugares con mejor calificación promedio"
)
def get_popular(
    limite: int = Query(10, ge=1, le=50, description="Número máximo de resultados"),
    db: Session = Depends(get_db)
):
    """
    Retorna los lugares más populares del sistema.
    Solo incluye lugares aprobados con al menos una reseña.
    Ordenados por calificación promedio descendente.
    """
    return obtener_lugares_populares(db, limite)


@router.get(
    "/nearby",
    summary="Recomendaciones cercanas",
    description="Recomienda lugares cercanos a una ubicación con calificación"
)
def get_nearby_recommendations(
    latitud: float = Query(..., ge=-90, le=90, description="Latitud del punto de referencia"),
    longitud: float = Query(..., ge=-180, le=180, description="Longitud del punto de referencia"),
    radio_km: float = Query(2.0, gt=0, le=50, description="Radio de búsqueda en km"),
    limite: int = Query(10, ge=1, le=50, description="Número máximo de resultados"),
    db: Session = Depends(get_db)
):
    """
    Recomienda lugares cercanos a las coordenadas proporcionadas.
    Incluye calificación promedio y distancia en metros.
    Ordenados por cercanía.
    """
    return obtener_recomendaciones_cercanas(db, latitud, longitud, radio_km, limite)
