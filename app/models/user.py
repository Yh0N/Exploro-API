"""
Modelo SQLAlchemy para la entidad Usuario.
Representa a los usuarios registrados en el sistema EXPLORO.
El campo 'preferencias' usa ARRAY de PostgreSQL para almacenar
categorías de interés de forma eficiente.
El campo 'rol' maneja todos los tipos de usuario (incluido administrador).
Campos OAuth2: proveedor_auth, proveedor_id, email_verificado, foto_perfil,
hashed_password (para login local futuro), refresh_token, activo, updated_at.
"""

from sqlalchemy import Column, Integer, String, Date, ARRAY, ForeignKey, Table, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import date, datetime

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
    contraseña = Column(String(255), nullable=False)  # Hash bcrypt (login local)
    preferencias = Column(ARRAY(String), default=[])  # Array de categorías de interés
    fecha_registro = Column(Date, default=date.today)
    rol = Column(Integer, default=1)  # 1: usuario_regular, 2: pyme, 3: administrador

    # ── Campos OAuth2 (RF1 / RNF4) ────────────────────────────────────────────
    # Proveedor de autenticación: 'local', 'google' o 'facebook'
    proveedor_auth = Column(String(20), nullable=False, default="local")
    # ID externo que devuelve el proveedor OAuth (sub de Google, id de Facebook)
    proveedor_id = Column(String(255), nullable=True, index=True)
    # Indica si el correo fue verificado por el proveedor OAuth
    email_verificado = Column(Boolean, nullable=False, default=False)
    # URL de la foto de perfil obtenida del proveedor
    foto_perfil = Column(String(500), nullable=True)
    # Hash de contraseña exclusivo para login local futuro (nullable para OAuth)
    hashed_password = Column(String(255), nullable=True)
    # Refresh token emitido por EXPLORO (nullable, se actualiza en cada sesión)
    refresh_token = Column(String(512), nullable=True)
    # Indica si la cuenta está activa; inactiva bloquea el acceso
    activo = Column(Boolean, nullable=False, default=True)
    # Timestamp de última actualización del registro
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)

    # Relaciones con otras tablas
    perfil = relationship("Perfil", back_populates="usuario", uselist=False, cascade="all, delete-orphan")
    resenas = relationship("Reseña", foreign_keys="[Reseña.id_usuario]", back_populates="usuario", cascade="all, delete-orphan")
    recomendaciones = relationship("Recomendacion", back_populates="usuario", cascade="all, delete-orphan")
    pyme = relationship("Pyme", back_populates="usuario", uselist=False, cascade="all, delete-orphan")
    lugares = relationship("Lugar", back_populates="usuario")
    tokens_revocados = relationship("TokenRevocado", back_populates="usuario", cascade="all, delete-orphan")
    
    # Favoritos (Muchos a Muchos)
    favorites = relationship("Lugar", secondary=favoritos, backref="usuarios_que_marcaron_favorito")
    
    # Imágenes subidas (RF12)
    imagenes = relationship("Imagen", back_populates="usuario", cascade="all, delete-orphan")
