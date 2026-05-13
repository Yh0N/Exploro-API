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
    summary="Publicar reseña en lugar",
    description="Publica una reseña y calificación sobre un lugar turístico"
)
def create_place_review(
    id_lugar: int,
    datos: ReviewCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crear_reseña(db, datos, current_user, id_lugar=id_lugar)


@router.get(
    "/places/{id_lugar}/reviews",
    summary="Listar reseñas de lugar",
    description="Lista todas las reseñas de un lugar turístico"
)
def list_place_reviews(id_lugar: int, db: Session = Depends(get_db)):
    return listar_reseñas(db, id_lugar=id_lugar)


@router.post(
    "/pymes/{id_pyme}/reviews",
    status_code=status.HTTP_201_CREATED,
    summary="Publicar reseña en pyme",
    description="Publica una reseña y calificación sobre una pyme"
)
def create_pyme_review(
    id_pyme: int,
    datos: ReviewCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crear_reseña(db, datos, current_user, id_pyme=id_pyme)


@router.get(
    "/pymes/{id_pyme}/reviews",
    summary="Listar reseñas de pyme",
    description="Lista todas las reseñas de una pyme"
)
def list_pyme_reviews(id_pyme: int, db: Session = Depends(get_db)):
    return listar_reseñas(db, id_pyme=id_pyme)


@router.post(
    "/users/{id_usuario_destino}/reviews",
    status_code=status.HTTP_201_CREATED,
    summary="Publicar reseña a usuario",
    description="Publica una reseña y calificación sobre un usuario (ej. un guía o anfitrión)"
)
def create_user_review(
    id_usuario_destino: int,
    datos: ReviewCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crear_reseña(db, datos, current_user, id_usuario_destino=id_usuario_destino)


@router.get(
    "/users/{id_usuario_destino}/reviews",
    summary="Listar reseñas de usuario",
    description="Lista todas las reseñas recibidas por un usuario"
)
def list_user_reviews(id_usuario_destino: int, db: Session = Depends(get_db)):
    return listar_reseñas(db, id_usuario_destino=id_usuario_destino)


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


@router.put(
    "/reviews/{id_resena}",
    summary="Actualizar reseña",
    description="Actualiza la calificación y el comentario de una reseña existente (solo el autor)"
)
def update_review(
    id_resena: int,
    datos: ReviewCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.services.review_service import actualizar_reseña
    return actualizar_reseña(db, id_resena, datos, current_user)
