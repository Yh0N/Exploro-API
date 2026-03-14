"""
Esquemas Pydantic para la entidad Reseña.
Define los modelos de validación para la creación y respuesta de reseñas.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class ReviewCreate(BaseModel):
    """Esquema para publicar una nueva reseña sobre un lugar."""
    comentarios: Optional[str] = Field(None, max_length=1000, description="Comentario sobre el lugar")
    puntuacion: int = Field(..., ge=1, le=5, description="Puntuación del 1 al 5")


class ReviewResponse(BaseModel):
    """Esquema de respuesta con la información de la reseña."""
    id_resena: int
    id_usuario: int
    id_lugar: int
    comentarios: Optional[str] = None
    puntuacion: int
    fecha: date
    nombre_usuario: Optional[str] = None  # Se agrega en el servicio

    class Config:
        from_attributes = True
