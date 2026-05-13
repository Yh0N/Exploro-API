"""
Modelo SQLAlchemy para la entidad Usuario.
Representa a los usuarios registrados en el sistema EXPLORO.
El campo 'preferencias' usa ARRAY de PostgreSQL para almacenar
categorías de interés de forma eficiente.
El campo 'rol' maneja todos los tipos de usuario (incluido administrador).
"""

from sqlalchemy import Column, Integer, String, Date, ARRAY, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import date

from app.database.connection import Base

# Tabla de asociación para Favoritos (Muchos a Muchos entre Usuario y Lugar)
favoritos = Table(
    "favoritos",
    Base.metadata,
    Column("id_usuario", Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), primary_key=True),
    Column("id_lugar", Integer, ForeignKey("lugares.id_lugar", ondelete="CASCADE"), primary_key=True)
)


class Usuario(Base):
    """
    Tabla 'usuarios' - Almacena la información de todos los usuarios del sistema.
    
    Roles posibles:
    - usuario_regular: usuario estándar que puede dejar reseñas
    - pyme: representante de una pyme que puede registrar lugares
    - administrador: acceso completo al sistema
    """
    __tablename__ = "usuarios"

    id_usuario = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
    correo = Column(String(150), unique=True, nullable=False, index=True)
    contraseña = Column(String(255), nullable=False)  # Hash bcrypt
    preferencias = Column(ARRAY(String), default=[])  # Array de categorías de interés
    fecha_registro = Column(Date, default=date.today)
    rol = Column(Integer, default=1)  # 1: usuario_regular, 2: pyme, 3: administrador

    # Relaciones con otras tablas
    perfil = relationship("Perfil", back_populates="usuario", uselist=False, cascade="all, delete-orphan")
    resenas = relationship("Reseña", foreign_keys="[Reseña.id_usuario]", back_populates="usuario", cascade="all, delete-orphan")
    recomendaciones = relationship("Recomendacion", back_populates="usuario", cascade="all, delete-orphan")
    pyme = relationship("Pyme", back_populates="usuario", uselist=False, cascade="all, delete-orphan")
    lugares = relationship("Lugar", back_populates="usuario")
    tokens_revocados = relationship("TokenRevocado", back_populates="usuario", cascade="all, delete-orphan")
    
    # Favoritos (Muchos a Muchos)
    favorites = relationship("Lugar", secondary=favoritos, backref="usuarios_que_marcaron_favorito")
