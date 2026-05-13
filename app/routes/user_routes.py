"""
Rutas de usuarios de EXPLORO.
Endpoints para consultar y actualizar perfiles de usuario.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.connection import get_db
from app.schemas.user_schema import UserResponse, UserUpdate, UserPublicResponse
from app.core.security import get_current_user
from app.models.user import Usuario
from app.models.review import Reseña
from app.models.place import Lugar

router = APIRouter(prefix="/users", tags=["Usuarios"])

def _agregar_stats_usuario(usuario: Usuario, db: Session):
    """Calcula y agrega calificación promedio y número de reseñas al objeto usuario."""
    stats = db.query(
        func.avg(Reseña.puntuacion),
        func.count(Reseña.id_resena)
    ).filter(Reseña.id_usuario_destino == usuario.id_usuario).first()
    
    usuario.calificacion_promedio = round(float(stats[0]), 2) if stats[0] else 0.0
    usuario.numero_reseñas = stats[1] if stats[1] else 0
    return usuario


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Mi perfil",
    description="Obtiene el perfil completo del usuario autenticado"
)
def get_my_profile(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Retorna toda la información del usuario autenticado,
    incluyendo su perfil (foto, biografía).
    """
    return _agregar_stats_usuario(current_user, db)


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Actualizar mi perfil",
    description="Actualiza los datos del usuario y perfil autenticado"
)
def update_my_profile(
    datos: UserUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Actualiza los datos del usuario autenticado.
    
    Campos actualizables del usuario: nombre, correo, preferencias.
    Campos actualizables del perfil: foto, biografía.
    Solo se actualizan los campos proporcionados (no nulos).
    """
    # Actualizar campos del usuario
    if datos.nombre is not None:
        current_user.nombre = datos.nombre
    if datos.correo is not None:
        # Verificar que el nuevo correo no esté en uso
        existente = db.query(Usuario).filter(
            Usuario.correo == datos.correo,
            Usuario.id_usuario != current_user.id_usuario
        ).first()
        if existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya está en uso por otro usuario"
            )
        current_user.correo = datos.correo
    if datos.preferencias is not None:
        current_user.preferencias = datos.preferencias

    # Actualizar campos del perfil (si existe)
    if current_user.perfil:
        if datos.foto is not None:
            current_user.perfil.foto = datos.foto
        if datos.biografia is not None:
            current_user.perfil.biografia = datos.biografia

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post(
    "/me/favorites/{id_lugar}",
    summary="Alternar favorito",
    description="Agrega o elimina un lugar de la lista de favoritos del usuario"
)
def toggle_favorite(
    id_lugar: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Si el lugar ya es favorito, lo elimina.
    Si no lo es, lo agrega.
    """
    lugar = db.query(Lugar).filter(Lugar.id_lugar == id_lugar).first()
    if not lugar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lugar no encontrado"
        )
    
    if lugar in current_user.favorites:
        current_user.favorites.remove(lugar)
        message = "Eliminado de favoritos"
    else:
        current_user.favorites.append(lugar)
        message = "Agregado a favoritos"
    
    db.commit()
    return {
        "message": message, 
        "favorites": [f.id_lugar for f in current_user.favorites]
    }


@router.get(
    "/{id_usuario}",
    response_model=UserPublicResponse,
    summary="Perfil público",
    description="Obtiene el perfil público de un usuario por su ID"
)
def get_public_profile(id_usuario: int, db: Session = Depends(get_db)):
    """
    Retorna el perfil público de un usuario (sin datos sensibles).
    No incluye correo ni contraseña.
    """
    usuario = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    return _agregar_stats_usuario(usuario, db)
