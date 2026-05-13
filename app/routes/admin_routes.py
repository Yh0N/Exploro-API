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
from app.schemas.pyme_schema import PymeResponse
from app.core.security import require_role
from app.models.user import Usuario
from app.models.place import Lugar
from app.models.review import Reseña
from app.models.pyme import Pyme
from app.services.place_service import agregar_calificacion
from app.services.geocoding_service import geocode_address
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

router = APIRouter(prefix="/admin", tags=["Administración"])


@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="Listar todos los usuarios",
    description="Obtiene la lista de todos los usuarios registrados (solo admin)"
)
def list_all_users(
    current_user: Usuario = Depends(require_role([3])),
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
    current_user: Usuario = Depends(require_role([3])),
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

    nombre_usuario = usuario.nombre
    db.delete(usuario)
    db.commit()
    return {"message": f"Usuario '{nombre_usuario}' eliminado exitosamente"}


@router.get(
    "/pymes/pending",
    response_model=List[PymeResponse],
    summary="Pymes pendientes de aprobación",
    description="Lista las pymes que aún no han sido aprobadas (solo admin)"
)
def list_pending_pymes(
    current_user: Usuario = Depends(require_role([3])),
    db: Session = Depends(get_db)
):
    """
    Lista todas las pymes que están pendientes de aprobación.
    """
    pymes = db.query(Pyme).filter(Pyme.aprobado == False).all()
    return pymes


@router.put(
    "/pymes/{id_pyme}/approve",
    response_model=PymeResponse,
    summary="Aprobar pyme",
    description="Aprueba una pyme registrada para que aparezca públicamente (solo admin)"
)
async def approve_pyme(
    id_pyme: int,
    current_user: Usuario = Depends(require_role([3])),
    db: Session = Depends(get_db)
):
    """
    Aprueba una pyme para que sea visible públicamente.
    Solo administradores pueden aprobar pymes.
    Si la pyme no tiene coordenadas, intenta geocodificarlas automáticamente.
    """
    pyme = db.query(Pyme).filter(Pyme.id_pyme == id_pyme).first()
    if not pyme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pyme no encontrada"
        )

    if pyme.aprobado:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta pyme ya está aprobada"
        )

    # Si no tiene coordenadas, intentar geocodificar antes de aprobar
    if (pyme.latitud is None or pyme.longitud is None) and pyme.ubicacion_textual:
        print(f"[Geocoding Admin] Intentando geocodificar: {pyme.ubicacion_textual}")
        coords = await geocode_address(pyme.ubicacion_textual)
        if coords:
            pyme.latitud, pyme.longitud = coords
            pyme.ubicacion = from_shape(Point(pyme.longitud, pyme.latitud), srid=4326)
            print(f"[Geocoding Admin] Éxito: {coords}")

    pyme.aprobado = True
    db.commit()
    db.refresh(pyme)
    
    return pyme


@router.get(
    "/all-places",
    summary="Listar todos los lugares",
    description="Obtiene la lista de todos los lugares, aprobados y no aprobados (acceso para todos los usuarios del ecosistema)"
)
def list_all_places(
    current_user: Usuario = Depends(require_role([1, 2, 3])),
    db: Session = Depends(get_db)
):
    """
    Lista todos los lugares registrados en el sistema.
    Permite al administrador ver tanto lugares aprobados como pendientes.
    """
    lugares = db.query(Lugar).all()
    resultados = []
    for lugar in lugares:
        lugar_dict = {
            "id_lugar": lugar.id_lugar,
            "nombre": lugar.nombre,
            "descripcion": lugar.descripcion,
            "latitud": lugar.latitud,
            "longitud": lugar.longitud,
            "categoria": lugar.categoria,
            "subcategoria": lugar.subcategoria,
            "aprobado": lugar.aprobado,
            "id_usuario": lugar.id_usuario,
        }
        agregar_calificacion(lugar_dict, db)
        resultados.append(lugar_dict)
    return resultados


@router.get(
    "/all-reviews",
    summary="Listar todas las reseñas",
    description="Obtiene la lista de todas las reseñas del sistema (acceso para todos los usuarios del ecosistema)"
)
def list_all_reviews(
    current_user: Usuario = Depends(require_role([1, 2, 3])),
    db: Session = Depends(get_db)
):
    """
    Lista todas las reseñas registradas.
    Permite moderar comentarios.
    """
    reseñas = db.query(Reseña).all()
    return reseñas
