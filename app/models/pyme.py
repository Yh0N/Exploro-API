"""
Modelo SQLAlchemy para la entidad Pyme.
Representa a las pequeñas y medianas empresas turísticas
vinculadas a usuarios con rol 'pyme'.
"""

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

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
    ubicacion = Column(String(300), nullable=True)  # Dirección textual
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), unique=True, nullable=False)

    # Relación con Usuario
    usuario = relationship("Usuario", back_populates="pyme")
