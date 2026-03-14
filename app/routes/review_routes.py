"""
Rutas de reseñas de EXPLORO.
Endpoints para publicar, listar y eliminar reseñas de lugares turísticos.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.review_schema import ReviewCreate
from app.services.review_service import crear_reseña, listar_reseñas, eliminar_reseña
from app.core.security import get_current_user
from app.models.user import Usuario

router = APIRouter(tags=["Reseñas"])


@router.post(
    "/places/{id_lugar}/reviews",
    status_code=status.HTTP_201_CREATED,
    summary="Publicar reseña",
    description="Publica una reseña y calificación sobre un lugar turístico"
)
def create_review(
    id_lugar: int,
    datos: ReviewCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Publica una reseña sobre un lugar turístico.
    
    - Requiere autenticación
    - Solo se puede dejar una reseña por lugar por usuario
    - Puntuación del 1 al 5
    """
    return crear_reseña(db, id_lugar, datos, current_user)


@router.get(
    "/places/{id_lugar}/reviews",
    summary="Listar reseñas",
    description="Lista todas las reseñas de un lugar turístico"
)
def list_reviews(id_lugar: int, db: Session = Depends(get_db)):
    """
    Obtiene todas las reseñas de un lugar específico.
    Incluye el nombre del autor de cada reseña.
    Ordenadas por fecha descendente (más recientes primero).
    """
    return listar_reseñas(db, id_lugar)


@router.delete(
    "/reviews/{id_resena}",
    summary="Eliminar reseña",
    description="Elimina una reseña (solo el autor o un admin)"
)
def delete_review(
    id_resena: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Elimina una reseña existente.
    Solo el autor de la reseña o un administrador pueden eliminarla.
    """
    return eliminar_reseña(db, id_resena, current_user)
