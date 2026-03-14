"""
Rutas de administración de EXPLORO.
Endpoints exclusivos para usuarios con rol 'administrador'.
Permite gestionar usuarios y aprobar lugares turísticos.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.connection import get_db
from app.schemas.user_schema import UserResponse
from app.schemas.place_schema import PlaceResponse
from app.core.security import require_role
from app.models.user import Usuario
from app.models.place import Lugar
from app.services.place_service import agregar_calificacion

router = APIRouter(prefix="/admin", tags=["Administración"])


@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="Listar todos los usuarios",
    description="Obtiene la lista de todos los usuarios registrados (solo admin)"
)
def list_all_users(
    current_user: Usuario = Depends(require_role(["administrador"])),
    db: Session = Depends(get_db)
):
    """
    Lista todos los usuarios del sistema.
    Solo accesible por administradores.
    """
    usuarios = db.query(Usuario).all()
    return usuarios


@router.delete(
    "/users/{id_usuario}",
    summary="Eliminar usuario",
    description="Elimina un usuario del sistema (solo admin)"
)
def delete_user(
    id_usuario: int,
    current_user: Usuario = Depends(require_role(["administrador"])),
    db: Session = Depends(get_db)
):
    """
    Elimina un usuario del sistema.
    No se puede eliminar a sí mismo.
    La eliminación es en cascada (perfil, reseñas, pyme, etc.).
    """
    if id_usuario == current_user.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminarte a ti mismo"
        )

    usuario = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    db.delete(usuario)
    db.commit()
    return {"message": f"Usuario '{usuario.nombre}' eliminado exitosamente"}


@router.get(
    "/places",
    summary="Lugares pendientes de aprobación",
    description="Lista los lugares que aún no han sido aprobados (solo admin)"
)
def list_pending_places(
    current_user: Usuario = Depends(require_role(["administrador"])),
    db: Session = Depends(get_db)
):
    """
    Lista todos los lugares que están pendientes de aprobación.
    Los lugares se crean con aprobado=False y requieren aprobación
    de un administrador para aparecer en las búsquedas públicas.
    """
    lugares = db.query(Lugar).filter(Lugar.aprobado == False).all()
    resultados = []
    for lugar in lugares:
        lugar_dict = {
            "id_lugar": lugar.id_lugar,
            "nombre": lugar.nombre,
            "descripcion": lugar.descripcion,
            "latitud": lugar.latitud,
            "longitud": lugar.longitud,
            "categoria": lugar.categoria,
            "aprobado": lugar.aprobado,
        }
        agregar_calificacion(lugar_dict, db)
        resultados.append(lugar_dict)
    return resultados


@router.put(
    "/places/{id_lugar}/approve",
    summary="Aprobar lugar",
    description="Aprueba un lugar registrado para que aparezca públicamente (solo admin)"
)
def approve_place(
    id_lugar: int,
    current_user: Usuario = Depends(require_role(["administrador"])),
    db: Session = Depends(get_db)
):
    """
    Aprueba un lugar turístico para que sea visible públicamente.
    Solo administradores pueden aprobar lugares.
    """
    lugar = db.query(Lugar).filter(Lugar.id_lugar == id_lugar).first()
    if not lugar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lugar no encontrado"
        )

    if lugar.aprobado:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este lugar ya está aprobado"
        )

    lugar.aprobado = True
    db.commit()
    db.refresh(lugar)

    resultado = {
        "id_lugar": lugar.id_lugar,
        "nombre": lugar.nombre,
        "descripcion": lugar.descripcion,
        "latitud": lugar.latitud,
        "longitud": lugar.longitud,
        "categoria": lugar.categoria,
        "aprobado": lugar.aprobado,
    }
    agregar_calificacion(resultado, db)
    return resultado
