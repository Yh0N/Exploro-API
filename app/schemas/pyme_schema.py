"""
Esquemas Pydantic para la entidad Pyme.
Define los modelos de validación para la creación, actualización
y respuesta de información de pymes.
"""

from pydantic import BaseModel, Field
from typing import Optional


class PymeCreate(BaseModel):
    """Esquema para registrar una nueva pyme."""
    nombre: str = Field(..., min_length=2, max_length=200, description="Nombre de la pyme")
    tipo: str = Field(..., max_length=100, description="Tipo de pyme: restaurante, hotel, agencia, etc.")
    ubicacion: Optional[str] = Field(None, max_length=300, description="Dirección de la pyme")


class PymeUpdate(BaseModel):
    """Esquema para actualizar datos de una pyme existente."""
    nombre: Optional[str] = Field(None, min_length=2, max_length=200)
    tipo: Optional[str] = Field(None, max_length=100)
    ubicacion: Optional[str] = Field(None, max_length=300)


class PymeResponse(BaseModel):
    """Esquema de respuesta con la información de la pyme."""
    id_pyme: int
    nombre: str
    tipo: str
    ubicacion: Optional[str] = None
    id_usuario: int

    class Config:
        from_attributes = True
