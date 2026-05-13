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
    subcategoria: Optional[str] = Field(None, max_length=100, description="Subcategoría específica")
    ubicacion_textual: Optional[str] = Field(None, max_length=300, description="Dirección textual")
    latitud: Optional[float] = Field(None, ge=-90, le=90, description="Latitud")
    longitud: Optional[float] = Field(None, ge=-180, le=180, description="Longitud")


class PymeUpdate(BaseModel):
    """Esquema para actualizar datos de una pyme existente."""
    nombre: Optional[str] = Field(None, min_length=2, max_length=200)
    tipo: Optional[str] = Field(None, max_length=100)
    subcategoria: Optional[str] = Field(None, max_length=100)
    ubicacion_textual: Optional[str] = Field(None, max_length=300)
    latitud: Optional[float] = Field(None, ge=-90, le=90)
    longitud: Optional[float] = Field(None, ge=-180, le=180)


class PymeResponse(BaseModel):
    """Esquema de respuesta con la información de la pyme."""
    id_pyme: int
    nombre: str
    tipo: str
    subcategoria: Optional[str] = None
    ubicacion_textual: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    id_usuario: int
    aprobado: bool = False
    calificacion_promedio: Optional[float] = 0.0
    numero_reseñas: Optional[int] = 0

    class Config:
        from_attributes = True
