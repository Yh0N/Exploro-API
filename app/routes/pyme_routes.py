"""
Rutas de pymes de EXPLORO.
Endpoints para registrar, consultar y actualizar pymes turísticas.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.pyme_schema import PymeCreate, PymeUpdate, PymeResponse
from app.core.security import get_current_user, require_role
from app.models.user import Usuario
from app.models.pyme import Pyme

router = APIRouter(prefix="/pymes", tags=["Pymes"])


@router.post(
    "",
    response_model=PymeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar pyme",
    description="Registra una nueva pyme asociada al usuario autenticado"
)
def create_pyme(
    datos: PymeCreate,
    current_user: Usuario = Depends(require_role(["pyme", "administrador"])),
    db: Session = Depends(get_db)
):
    """
    Registra una nueva pyme en el sistema.
    Solo usuarios con rol 'pyme' o 'administrador' pueden registrar pymes.
    Cada usuario solo puede tener una pyme asociada.
    """
    # Verificar que el usuario no tenga ya una pyme
    pyme_existente = db.query(Pyme).filter(Pyme.id_usuario == current_user.id_usuario).first()
    if pyme_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya tienes una pyme registrada"
        )

    nueva_pyme = Pyme(
        nombre=datos.nombre,
        tipo=datos.tipo,
        ubicacion=datos.ubicacion,
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
    if pyme.id_usuario != current_user.id_usuario and current_user.rol != "administrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para actualizar esta pyme"
        )

    # Actualizar solo los campos proporcionados
    if datos.nombre is not None:
        pyme.nombre = datos.nombre
    if datos.tipo is not None:
        pyme.tipo = datos.tipo
    if datos.ubicacion is not None:
        pyme.ubicacion = datos.ubicacion

    db.commit()
    db.refresh(pyme)
    return pyme
