"""
Modelo SQLAlchemy para la entidad Lugar.
Representa los lugares turísticos de Pasto, Colombia.
Usa GeoAlchemy2 para la columna 'ubicacion' con tipo Geometry(Point, 4326)
que permite realizar consultas geoespaciales con PostGIS.

NOTA: calificacion_promedio NO se almacena como columna.
Se calcula dinámicamente con AVG() sobre las reseñas para evitar
desincronización y condiciones de carrera.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from app.database.connection import Base


class Lugar(Base):
    """
    Tabla 'lugares' - Lugares turísticos registrados en el sistema.
    
    La columna 'ubicacion' es de tipo Geometry(Point) con SRID 4326 (WGS84).
    Se usa para consultas de proximidad con ST_Distance de PostGIS.
    
    Las columnas 'latitud' y 'longitud' se mantienen como referencia
    rápida, pero la columna 'ubicacion' es la que se usa para cálculos
    geoespaciales.
    """
    __tablename__ = "lugares"

    id_lugar = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(String(1000), nullable=True)
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)
    ubicacion = Column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    direccion = Column(String(300), nullable=True)  # Dirección textual (opcional)
    categoria = Column(String(100), nullable=False)  # restaurante, hotel, museo, parque, tour, etc.
    subcategoria = Column(String(100), nullable=True)  # Subcategoría específica
    aprobado = Column(Boolean, default=True)  # Se crea aprobado por defecto
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True)
    foto_principal = Column(String(500), nullable=True)
    fotos = Column(String(2000), nullable=True)  # Lista separada por comas de URLs de fotos

    # Relaciones
    usuario = relationship("Usuario", back_populates="lugares")
    resenas = relationship("Reseña", back_populates="lugar", cascade="all, delete-orphan")
    recomendaciones = relationship("Recomendacion", back_populates="lugar", cascade="all, delete-orphan")
