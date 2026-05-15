"""
Esquemas Pydantic para la entidad Usuario.
Define los modelos de validación para las peticiones y respuestas
relacionadas con usuarios, perfiles y autenticación.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import date
import re


# ============================================================
# ESQUEMAS DE AUTENTICACIÓN
# ============================================================

class UserCreate(BaseModel):
    """Esquema para el registro de un nuevo usuario."""
    nombre: str = Field(..., min_length=2, max_length=100, description="Nombre completo del usuario")
    correo: str = Field(..., max_length=150, description="Correo electrónico único")
    contraseña: str = Field(..., min_length=8, max_length=100, description="Contraseña (mínimo 8 caracteres, mayúscula, número y carácter especial)")
    preferencias: Optional[List[str]] = Field(default=[], description="Lista de categorías de interés")
    rol: Optional[int] = Field(default=1, description="Rol: 1 (regular), 2 (pyme), 3 (admin)")

    @field_validator('contraseña')
    @classmethod
    def validar_contrasena_segura(cls, v: str) -> str:
        """Valida que la contraseña cumpla los requisitos de seguridad."""
        if not re.search(r'[A-Z]', v):
            raise ValueError('La contraseña debe contener al menos una letra mayúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('La contraseña debe contener al menos una letra minúscula')
        if not re.search(r'[0-9]', v):
            raise ValueError('La contraseña debe contener al menos un número')
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"|,.<>\/?]', v):
            raise ValueError('La contraseña debe contener al menos un carácter especial (!@#$%^&*...)')
        return v


class UserLogin(BaseModel):
    """Esquema para el inicio de sesión."""
    correo: str = Field(..., description="Correo electrónico registrado")
    contraseña: str = Field(..., description="Contraseña del usuario")


class UserSocialLogin(BaseModel):
    """Esquema para el inicio de sesión social."""
    provider: str = Field(..., description="Proveedor (google o facebook)")
    id_token: Optional[str] = Field(None, description="Token de identidad del proveedor")
    # Para la simulación, permitiremos enviar datos básicos
    nombre: Optional[str] = None
    correo: Optional[str] = None
    rol: Optional[int] = Field(1, description="Rol: 1 (turista), 2 (pyme)")


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
    rol: int
    calificacion_promedio: Optional[float] = 0.0
    numero_reseñas: Optional[int] = 0
    is_public: bool = True
    perfil: Optional[ProfileResponse] = None
    favorites: List[int] = Field(default=[])

    @field_validator('favorites', mode='before')
    @classmethod
    def extract_ids(cls, v):
        """Convierte lista de objetos Lugar a lista de IDs."""
        if isinstance(v, list) and len(v) > 0 and hasattr(v[0], 'id_lugar'):
            return [item.id_lugar for item in v]
        return v

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Esquema para actualizar datos del usuario y perfil."""
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    correo: Optional[str] = Field(None, max_length=150)
    preferencias: Optional[List[str]] = None
    foto: Optional[str] = Field(None, description="URL o Base64 de la foto de perfil")
    biografia: Optional[str] = Field(None, description="Biografía del usuario")
    is_public: Optional[bool] = Field(None, description="Indica si el perfil es público")


class UserPublicResponse(BaseModel):
    """Esquema de respuesta para perfil público (sin datos sensibles)."""
    id_usuario: int
    nombre: str
    preferencias: Optional[List[str]] = []
    fecha_registro: date
    calificacion_promedio: Optional[float] = 0.0
    numero_reseñas: Optional[int] = 0
    perfil: Optional[ProfileResponse] = None

    class Config:
        from_attributes = True
