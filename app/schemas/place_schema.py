"""
Esquemas Pydantic para la entidad Lugar.
Define los modelos de validación para la creación, actualización
y respuesta de lugares turísticos.
"""

from pydantic import BaseModel, Field
from typing import Optional


class PlaceCreate(BaseModel):
    """Esquema para registrar un nuevo lugar turístico."""
    nombre: str = Field(..., min_length=2, max_length=200, description="Nombre del lugar")
    descripcion: Optional[str] = Field(None, max_length=1000, description="Descripción del lugar")
    latitud: Optional[float] = Field(None, ge=-90, le=90, description="Latitud del lugar (opcional si se provee dirección)")
    longitud: Optional[float] = Field(None, ge=-180, le=180, description="Longitud del lugar (opcional si se provee dirección)")
    ubicacion_textual: Optional[str] = Field(None, max_length=300, description="Dirección o descripción de la ubicación para geocodificar")
    categoria: str = Field(..., max_length=100, description="Categoría principal")
    subcategoria: Optional[str] = Field(None, max_length=100, description="Subcategoría del lugar")


class PlaceUpdate(BaseModel):
    """Esquema para actualizar un lugar existente."""
    nombre: Optional[str] = Field(None, min_length=2, max_length=200)
    descripcion: Optional[str] = Field(None, max_length=1000)
    latitud: Optional[float] = Field(None, ge=-90, le=90)
    longitud: Optional[float] = Field(None, ge=-180, le=180)
    categoria: Optional[str] = Field(None, max_length=100)
    subcategoria: Optional[str] = Field(None, max_length=100)


class PlaceResponse(BaseModel):
    """Esquema de respuesta con la información completa del lugar."""
    id_lugar: int
    nombre: str
    descripcion: Optional[str] = None
    latitud: float
    longitud: float
    categoria: str
    aprobado: bool
    calificacion_promedio: Optional[float] = None  # Se calcula dinámicamente con AVG()
    numero_reseñas: Optional[int] = 0
    id_usuario: Optional[int] = None
    host_name: Optional[str] = None
    host_since: Optional[str] = None

    class Config:
        from_attributes = True


class PlaceNearbyRequest(BaseModel):
    """Esquema para buscar lugares cercanos por coordenadas y radio."""
    latitud: float = Field(..., ge=-90, le=90, description="Latitud del punto de referencia")
    longitud: float = Field(..., ge=-180, le=180, description="Longitud del punto de referencia")
    radio_km: float = Field(default=2.0, gt=0, le=50, description="Radio de búsqueda en kilómetros")
