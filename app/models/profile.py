"""
Modelo SQLAlchemy para la entidad Perfil.
Relación 1:1 con Usuario. Almacena información adicional
del usuario como foto de perfil y biografía.
"""

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.database.connection import Base


class Perfil(Base):
    """
    Tabla 'perfiles' - Información extendida del usuario.
    Se crea automáticamente al registrar un nuevo usuario.
    """
    __tablename__ = "perfiles"

    id_perfil = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), unique=True, nullable=False)
    foto = Column(String, nullable=True)  # URL o Base64 de la foto de perfil
    biografia = Column(String(500), nullable=True)  # Descripción breve del usuario

    # Relación inversa con Usuario
    usuario = relationship("Usuario", back_populates="perfil")
