"""
Modelo SQLAlchemy para la entidad Recomendacion.
Registra las recomendaciones generadas para cada usuario,
almacenando qué lugar fue recomendado y cuándo.
"""

from sqlalchemy import Column, Integer, Date, ForeignKey
from sqlalchemy.orm import relationship
from datetime import date

from app.database.connection import Base


class Recomendacion(Base):
    """
    Tabla 'recomendaciones' - Registro histórico de recomendaciones generadas.
    Permite rastrear qué lugares se han recomendado a cada usuario.
    """
    __tablename__ = "recomendaciones"

    id_recomendacion = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False)
    id_lugar = Column(Integer, ForeignKey("lugares.id_lugar", ondelete="CASCADE"), nullable=False)
    fecha = Column(Date, default=date.today)

    # Relaciones
    usuario = relationship("Usuario", back_populates="recomendaciones")
    lugar = relationship("Lugar", back_populates="recomendaciones")
