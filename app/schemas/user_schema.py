"""
Esquemas Pydantic para la entidad Usuario.
Define los modelos de validación para las peticiones y respuestas
relacionadas con usuarios, perfiles y autenticación.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date


# ============================================================
# ESQUEMAS DE AUTENTICACIÓN
# ============================================================

class UserCreate(BaseModel):
    """Esquema para el registro de un nuevo usuario."""
    nombre: str = Field(..., min_length=2, max_length=100, description="Nombre completo del usuario")
    correo: str = Field(..., max_length=150, description="Correo electrónico único")
    contraseña: str = Field(..., min_length=6, max_length=100, description="Contraseña (mínimo 6 caracteres)")
    preferencias: Optional[List[str]] = Field(default=[], description="Lista de categorías de interés")
    rol: Optional[str] = Field(default="usuario_regular", description="Rol: usuario_regular, pyme, administrador")


class UserLogin(BaseModel):
    """Esquema para el inicio de sesión."""
    correo: str = Field(..., description="Correo electrónico registrado")
    contraseña: str = Field(..., description="Contraseña del usuario")


class Token(BaseModel):
    """Esquema de respuesta con el token JWT."""
    access_token: str
    token_type: str = "bearer"


# ============================================================
# ESQUEMAS DE USUARIO Y PERFIL
# ============================================================

class ProfileResponse(BaseModel):
    """Esquema de respuesta del perfil del usuario."""
    id_perfil: int
    foto: Optional[str] = None
    biografia: Optional[str] = None

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """Esquema de respuesta con la información del usuario."""
    id_usuario: int
    nombre: str
    correo: str
    preferencias: Optional[List[str]] = []
    fecha_registro: date
    rol: str
    perfil: Optional[ProfileResponse] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Esquema para actualizar datos del usuario y perfil."""
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    correo: Optional[str] = Field(None, max_length=150)
    preferencias: Optional[List[str]] = None
    foto: Optional[str] = Field(None, max_length=500, description="URL de la foto de perfil")
    biografia: Optional[str] = Field(None, max_length=500, description="Biografía del usuario")


class UserPublicResponse(BaseModel):
    """Esquema de respuesta para perfil público (sin datos sensibles)."""
    id_usuario: int
    nombre: str
    preferencias: Optional[List[str]] = []
    fecha_registro: date
    perfil: Optional[ProfileResponse] = None

    class Config:
        from_attributes = True
