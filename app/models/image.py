from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base

class Imagen(Base):
    __tablename__ = "imagenes"

    id_imagen = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False)
    entidad_tipo = Column(String(10), nullable=False) # 'pyme' o 'lugar'
    entidad_id = Column(Integer, nullable=False)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relaciones
    usuario = relationship("Usuario", back_populates="imagenes")

    # Nota: No usamos relación directa con Pyme o Lugar aquí para mantenerlo genérico 
    # y evitar dependencias circulares complejas, pero se puede filtrar por entidad_id.
