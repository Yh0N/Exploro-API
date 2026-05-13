"""
Modelo SQLAlchemy para la entidad Pyme.
Representa a las pequeñas y medianas empresas turísticas
vinculadas a usuarios con rol 'pyme'.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from app.database.connection import Base


class Pyme(Base):
    """
    Tabla 'pymes' - Información de las pymes turísticas.
    Cada pyme está asociada a un usuario con rol 'pyme'.
    """
    __tablename__ = "pymes"

    id_pyme = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(200), nullable=False)
    tipo = Column(String(100), nullable=False)  # restaurante, hotel, agencia, etc.
    subcategoria = Column(String(100), nullable=True)  # Subcategoría específica
    ubicacion_textual = Column(String(300), nullable=True)  # Dirección textual (renombrado)
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)
    ubicacion = Column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    aprobado = Column(Boolean, default=False)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False)
    foto_principal = Column(String(500), nullable=True)
    fotos = Column(String(2000), nullable=True)  # Lista separada por comas de URLs de fotos

    # Relación con Usuario
    usuario = relationship("Usuario", back_populates="pyme")
