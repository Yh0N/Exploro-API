"""
Modelo SQLAlchemy para la tabla de tokens revocados (blacklist).
Se usa para implementar el logout real con JWT.
Cuando un usuario hace logout, su token se guarda en esta tabla.
Al autenticarse, se verifica que el token no esté en esta tabla.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.database.connection import Base


class TokenRevocado(Base):
    """
    Tabla 'tokens_revocados' - Lista negra de tokens JWT invalidados.
    
    Cada vez que un usuario hace logout, su token se agrega aquí.
    La función get_current_user() verifica esta tabla antes de
    aceptar un token como válido.
    """
    __tablename__ = "tokens_revocados"

    id_auth = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False)
    token = Column(String(500), nullable=False, unique=True, index=True)
    fecha_emision = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    fecha_expiracion = Column(DateTime(timezone=True), nullable=True)

    # Relación con Usuario
    usuario = relationship("Usuario", back_populates="tokens_revocados")
