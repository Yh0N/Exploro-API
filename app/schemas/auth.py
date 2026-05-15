"""
Esquemas Pydantic para el flujo OAuth2 de EXPLORO.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# ================================================================
# TOKENS
# ================================================================

class Token(BaseModel):
    """Respuesta estándar de autenticación OAuth2."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Payload del JWT."""
    sub: str        # user_id o correo
    email: Optional[str] = None
    tipo: Optional[int] = None # rol
    exp: Optional[datetime] = None


class RefreshRequest(BaseModel):
    """Cuerpo de la petición para renovar el access token."""
    refresh_token: str


# ================================================================
# RESPUESTAS DE USUARIO
# ================================================================

class UserResponse(BaseModel):
    """Datos del usuario devueltos en la autenticación."""
    id: int = Field(..., alias="id_usuario")
    email: str = Field(..., alias="correo")
    nombre: str
    foto_perfil: Optional[str] = None
    tipo: int = Field(..., alias="rol")
    proveedor_auth: str

    class Config:
        from_attributes = True
        populate_by_name = True


class TokenWithUser(BaseModel):
    """Tokens + Datos del usuario."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


# ================================================================
# PETICIONES DE CALLBACK
# ================================================================

class GoogleCallbackRequest(BaseModel):
    """Callback de Google."""
    code: str
    redirect_uri: str




# ================================================================
# ACTUALIZACIÓN DE PERFIL
# ================================================================

class UserMeUpdate(BaseModel):
    """Actualización de perfil propio."""
    nombre: Optional[str] = None
    preferencias: Optional[List[str]] = None
