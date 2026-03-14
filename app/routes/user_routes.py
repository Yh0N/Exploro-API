"""
Rutas de usuarios de EXPLORO.
Endpoints para consultar y actualizar perfiles de usuario.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.user_schema import UserResponse, UserUpdate, UserPublicResponse
from app.core.security import get_current_user
from app.models.user import Usuario

router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Mi perfil",
    description="Obtiene el perfil completo del usuario autenticado"
)
def get_my_profile(current_user: Usuario = Depends(get_current_user)):
    """
    Retorna toda la información del usuario autenticado,
    incluyendo su perfil (foto, biografía).
    """
    return current_user


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
    return usuario
