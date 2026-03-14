"""
Modelo SQLAlchemy para la entidad Reseña.
Permite a usuarios autenticados dejar comentarios y puntuación
sobre los lugares turísticos registrados.
"""

from sqlalchemy import Column, Integer, String, Date, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import date

from app.database.connection import Base


class Reseña(Base):
    """
    Tabla 'reseñas' - Opiniones y calificaciones de usuarios sobre lugares.
    
    La puntuación debe estar entre 1 y 5 (validado con CheckConstraint).
    La calificación promedio del lugar se calcula dinámicamente con AVG()
    sobre esta tabla.
    """
    __tablename__ = "resenas"

    id_resena = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False)
    id_lugar = Column(Integer, ForeignKey("lugares.id_lugar", ondelete="CASCADE"), nullable=False)
    comentarios = Column(String(1000), nullable=True)
    puntuacion = Column(Integer, nullable=False)
    fecha = Column(Date, default=date.today)

    # Restricción: puntuación entre 1 y 5
    __table_args__ = (
        CheckConstraint("puntuacion >= 1 AND puntuacion <= 5", name="check_puntuacion_rango"),
    )

    # Relaciones
    usuario = relationship("Usuario", back_populates="resenas")
    lugar = relationship("Lugar", back_populates="resenas")
