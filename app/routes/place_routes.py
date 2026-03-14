"""
Rutas de lugares turísticos de EXPLORO.
Endpoints para CRUD de lugares y búsqueda geoespacial.

IMPORTANTE: /places/nearby se registra ANTES de /places/{id}
para evitar que FastAPI interprete "nearby" como un {id}.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.place_schema import PlaceCreate, PlaceUpdate, PlaceResponse
from app.services.place_service import (
    crear_lugar, obtener_lugar, listar_lugares,
    actualizar_lugar, eliminar_lugar, buscar_lugares_cercanos
)
from app.core.security import get_current_user, require_role
from app.models.user import Usuario
from app.models.pyme import Pyme

router = APIRouter(prefix="/places", tags=["Lugares"])


@router.get(
    "",
    summary="Listar lugares",
    description="Lista los lugares turísticos aprobados con filtros opcionales"
)
def list_places(
    categoria: Optional[str] = Query(None, description="Filtrar por categoría"),
    calificacion_min: Optional[float] = Query(None, ge=1, le=5, description="Calificación mínima"),
    db: Session = Depends(get_db)
):
    """
    Lista todos los lugares turísticos aprobados.
    Permite filtrar por categoría y calificación mínima.
    """
    return listar_lugares(db, categoria, calificacion_min)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar lugar",
    description="Registra un nuevo lugar turístico (solo pyme o admin)"
)
def create_place(
    datos: PlaceCreate,
    current_user: Usuario = Depends(require_role(["pyme", "administrador"])),
    db: Session = Depends(get_db)
):
    """
    Registra un nuevo lugar turístico.
    Solo usuarios con rol 'pyme' o 'administrador' pueden crear lugares.
    Las pymes deben tener un perfil de Pyme registrado.
    El lugar se crea con estado aprobado=False (pendiente de revisión).
    """
    if current_user.rol == "pyme":
        pyme_existente = db.query(Pyme).filter(Pyme.id_usuario == current_user.id_usuario).first()
        if not pyme_existente:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debes registrar tu pyme antes de crear lugares."
            )

    return crear_lugar(db, datos)


# ⚠️ IMPORTANTE: /nearby DEBE ir ANTES de /{id} para evitar conflicto de rutas
@router.get(
    "/nearby",
    summary="Lugares cercanos",
    description="Busca lugares cercanos por coordenadas y radio usando PostGIS"
)
def nearby_places(
    latitud: float = Query(..., ge=-90, le=90, description="Latitud del punto de referencia"),
    longitud: float = Query(..., ge=-180, le=180, description="Longitud del punto de referencia"),
    radio_km: float = Query(2.0, gt=0, le=50, description="Radio de búsqueda en km"),
    db: Session = Depends(get_db)
):
    """
    Busca lugares cercanos a las coordenadas proporcionadas.
    Usa PostGIS ST_DWithin para filtrado eficiente y ST_Distance
    para calcular la distancia exacta en metros.
    """
    return buscar_lugares_cercanos(db, latitud, longitud, radio_km)


@router.get(
    "/{id_lugar}",
    summary="Detalle de un lugar",
    description="Obtiene la información completa de un lugar"
)
def get_place(id_lugar: int, db: Session = Depends(get_db)):
    """
    Obtiene los datos detallados de un lugar turístico,
    incluyendo su calificación promedio calculada dinámicamente.
    """
    return obtener_lugar(db, id_lugar)


@router.put(
    "/{id_lugar}",
    summary="Actualizar lugar",
    description="Actualiza los datos de un lugar (dueño o admin)"
)
def update_place(
    id_lugar: int,
    datos: PlaceUpdate,
    current_user: Usuario = Depends(require_role(["pyme", "administrador"])),
    db: Session = Depends(get_db)
):
    """
    Actualiza los datos de un lugar existente.
    Solo pymes (dueñas) o administradores pueden actualizar.
    Si se cambian coordenadas, se reconstruye el punto PostGIS.
    """
    return actualizar_lugar(db, id_lugar, datos)


@router.delete(
    "/{id_lugar}",
    summary="Eliminar lugar",
    description="Elimina un lugar turístico (solo admin)"
)
def delete_place(
    id_lugar: int,
    current_user: Usuario = Depends(require_role(["administrador"])),
    db: Session = Depends(get_db)
):
    """
    Elimina un lugar turístico del sistema.
    Solo usuarios con rol 'administrador' pueden eliminar lugares.
    """
    return eliminar_lugar(db, id_lugar)
