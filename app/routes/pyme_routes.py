"""
Rutas de pymes de EXPLORO.
Endpoints para registrar, consultar y actualizar pymes turísticas.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.connection import get_db
from app.schemas.pyme_schema import PymeCreate, PymeUpdate, PymeResponse
from app.core.security import get_current_user, require_role
from app.models.user import Usuario
from app.models.pyme import Pyme
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import func
from app.models.review import Reseña
from app.services.geocoding_service import geocode_address

router = APIRouter(prefix="/pymes", tags=["Pymes"])

@router.get(
    "",
    response_model=List[PymeResponse],
    summary="Listar todas las pymes",
    description="Obtiene la lista de todas las pymes registradas con su calificación promedio"
)
def list_pymes(db: Session = Depends(get_db)):
    """
    Retorna la lista de todas las pymes con su calificación calculada.
    """
    # Consulta avanzada para traer pymes con su promedio de reseñas
    pymes_con_rating = db.query(
        Pyme,
        func.avg(Reseña.puntuacion).label("rating"),
        func.count(Reseña.id_resena).label("reviews_count")
    ).outerjoin(Reseña, Pyme.id_pyme == Reseña.id_pyme).group_by(Pyme.id_pyme).all()

    return [{
        "id_pyme": p.Pyme.id_pyme,
        "nombre": p.Pyme.nombre,
        "tipo": p.Pyme.tipo,
        "ubicacion_textual": p.Pyme.ubicacion_textual,
        "latitud": p.Pyme.latitud,
        "longitud": p.Pyme.longitud,
        "id_usuario": p.Pyme.id_usuario,
        "aprobado": p.Pyme.aprobado,
        "subcategoria": p.Pyme.subcategoria,
        "calificacion_promedio": round(float(p.rating), 2) if p.rating else 0.0,
        "numero_reseñas": p.reviews_count
    } for p in pymes_con_rating]


@router.post(
    "",
    response_model=PymeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar pyme",
    description="Registra una nueva pyme asociada al usuario autenticado"
)
async def create_pyme(
    datos: PymeCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Registra una nueva pyme en el sistema.
    Permite que usuarios regulares (rol 1) se conviertan en anfitriones (rol 2).
    Cada usuario solo puede tener una pyme asociada.
    """
    # Si el usuario es regular, actualizar su rol a Pyme (2)
    if current_user.rol == 1:
        current_user.rol = 2

    # Intentar geocodificar si no hay coordenadas pero sí dirección
    lat = datos.latitud
    lng = datos.longitud
    
    if (lat is None or lng is None) and datos.ubicacion_textual:
        print(f"[Geocoding] Intentando obtener coordenadas para: {datos.ubicacion_textual}")
        coords = await geocode_address(datos.ubicacion_textual)
        if coords:
            lat, lng = coords
            print(f"[Geocoding] Éxito: {lat}, {lng}")

    # Construir punto geoespacial
    punto = None
    if lat is not None and lng is not None:
        punto = from_shape(Point(lng, lat), srid=4326)

    nueva_pyme = Pyme(
        nombre=datos.nombre,
        tipo=datos.tipo,
        subcategoria=datos.subcategoria,
        ubicacion_textual=datos.ubicacion_textual,
        latitud=lat,
        longitud=lng,
        ubicacion=punto,
        id_usuario=current_user.id_usuario
    )
    db.add(nueva_pyme)
    db.commit()
    db.refresh(nueva_pyme)
    return nueva_pyme


@router.get(
    "/{id_pyme}",
    response_model=PymeResponse,
    summary="Ver pyme",
    description="Obtiene la información de una pyme por su ID"
)
def get_pyme(id_pyme: int, db: Session = Depends(get_db)):
    """
    Retorna los datos de una pyme registrada.
    Endpoint público (no requiere autenticación).
    """
    pyme = db.query(Pyme).filter(Pyme.id_pyme == id_pyme).first()
    if not pyme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pyme no encontrada"
        )
    return pyme


@router.put(
    "/{id_pyme}",
    response_model=PymeResponse,
    summary="Actualizar pyme",
    description="Actualiza los datos de una pyme (dueño o admin)"
)
def update_pyme(
    id_pyme: int,
    datos: PymeUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Actualiza los datos de una pyme existente.
    Solo el dueño de la pyme o un administrador pueden actualizarla.
    """
    pyme = db.query(Pyme).filter(Pyme.id_pyme == id_pyme).first()
    if not pyme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pyme no encontrada"
        )

    # Verificar permisos
    if pyme.id_usuario != current_user.id_usuario and current_user.rol != 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para actualizar esta pyme"
        )

    # Actualizar solo los campos proporcionados
    if datos.nombre is not None:
        pyme.nombre = datos.nombre
    if datos.tipo is not None:
        pyme.tipo = datos.tipo
    if datos.subcategoria is not None:
        pyme.subcategoria = datos.subcategoria
    if datos.ubicacion_textual is not None:
        pyme.ubicacion_textual = datos.ubicacion_textual
    
    # Actualizar coordenadas y geometría
    if datos.latitud is not None or datos.longitud is not None:
        nueva_lat = datos.latitud if datos.latitud is not None else pyme.latitud
        nueva_lng = datos.longitud if datos.longitud is not None else pyme.longitud
        pyme.latitud = nueva_lat
        pyme.longitud = nueva_lng
        pyme.ubicacion = from_shape(Point(nueva_lng, nueva_lat), srid=4326)

    db.commit()
    db.refresh(pyme)
    return pyme
@router.delete(
    "/{id_pyme}",
    summary="Eliminar pyme",
    description="Elimina una pyme del sistema (dueño o admin)"
)
def delete_pyme(
    id_pyme: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Elimina una pyme existente.
    Solo el dueño de la pyme o un administrador pueden eliminarla.
    """
    pyme = db.query(Pyme).filter(Pyme.id_pyme == id_pyme).first()
    if not pyme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pyme no encontrada"
        )

    # Verificar permisos
    if pyme.id_usuario != current_user.id_usuario and current_user.rol != 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar esta pyme"
        )

    db.delete(pyme)
    db.commit()
    return {"message": "Pyme eliminada exitosamente"}
