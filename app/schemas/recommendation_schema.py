"""
Esquemas Pydantic para respuestas del motor de recomendaciones.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RecommendationResponse(BaseModel):
    id_lugar: int
    nombre: str
    descripcion: Optional[str] = None
    latitud: float
    longitud: float
    categoria: str
    calificacion_promedio: Optional[float] = None
    total_resenas: int = 0
    distancia_metros: Optional[float] = None
    score_recomendacion: float
    razones: List[str] = Field(default_factory=list)
    factores: Dict[str, float] = Field(default_factory=dict)


class PopularPlaceResponse(BaseModel):
    id_lugar: int
    nombre: str
    descripcion: Optional[str] = None
    latitud: float
    longitud: float
    categoria: str
    calificacion_promedio: Optional[float] = None
    total_resenas: int = 0
    score_popularidad: float


class NearbyRecommendationResponse(BaseModel):
    id_lugar: int
    nombre: str
    descripcion: Optional[str] = None
    latitud: float
    longitud: float
    categoria: str
    calificacion_promedio: Optional[float] = None
    total_resenas: int = 0
    distancia_metros: float
    score_recomendacion: float
