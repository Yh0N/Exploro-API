"""
Módulo de seguridad de EXPLORO.
Contiene funciones para:
- Cifrado y verificación de contraseñas con bcrypt
- Generación y verificación de tokens JWT
- Dependencies de FastAPI para autenticación y autorización por roles
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.connection import get_db

# Parche de compatibilidad: bcrypt 4.0.0+ eliminó el atributo __about__ 
# que passlib usa para verificar la versión.
import bcrypt
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type("About", (object,), {"__version__": bcrypt.__version__})


# Esquema de seguridad HTTP Bearer para Swagger UI
security_scheme = HTTPBearer()

def get_token_from_header(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)) -> str:
    """Extrae el token en formato string del objeto HTTPAuthorizationCredentials."""
    return credentials.credentials

# Se conserva el mismo nombre para mantener la compatibilidad con el resto de archivos
oauth2_scheme = get_token_from_header

# Contexto de cifrado con bcrypt para hashear contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Genera un hash bcrypt de la contraseña proporcionada.
    Nunca se almacena la contraseña en texto plano.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con su hash bcrypt.
    Retorna True si coinciden, False en caso contrario.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Genera un token JWT de acceso con los datos proporcionados.

    Args:
        data: Diccionario con los claims del token.
              Se recomienda incluir: sub (correo o user_id), email, rol, scopes.
        expires_delta: Tiempo de vida del token. Si no se proporciona,
                      se usa ACCESS_TOKEN_EXPIRE_MINUTES del .env

    Returns:
        Token JWT de acceso codificado como string.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Genera un token JWT de refresco con expiración larga (7 días por defecto).

    El refresh token permite emitir nuevos access tokens sin que el usuario
    vuelva a autenticarse con Google/Facebook. Se almacena en la tabla
    'usuarios' (campo refresh_token) para permitir invalidación por servidor.

    Args:
        data: Diccionario con los claims del token.
              Se incluye el mismo sub que el access token.

    Returns:
        Token JWT de refresco codificado como string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    Decodifica y verifica un token JWT.
    
    Args:
        token: Token JWT a verificar
    
    Returns:
        Diccionario con los claims del token
    
    Raises:
        HTTPException 401 si el token es inválido o ha expirado
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"}
        )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Dependency de FastAPI que obtiene el usuario autenticado actual.
    
    1. Decodifica el token JWT
    2. Extrae el correo del claim "sub"
    3. Verifica que el token no esté en la lista negra (tabla Autenticacion)
    4. Busca al usuario en la base de datos
    
    Returns:
        Objeto Usuario del usuario autenticado
    
    Raises:
        HTTPException 401 si el token es inválido, revocado o el usuario no existe
    """
    # Importación dentro de la función para evitar importaciones circulares
    from app.models.user import Usuario
    from app.models.auth_token import TokenRevocado

    # Verificar y decodificar el token
    payload = verify_token(token)
    correo: str = payload.get("sub")
    if correo is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudo validar las credenciales",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Verificar que el token no esté revocado (logout)
    token_revocado = db.query(TokenRevocado).filter(
        TokenRevocado.token == token
    ).first()
    if token_revocado:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token revocado. Inicie sesión nuevamente.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Buscar al usuario por correo
    usuario = db.query(Usuario).filter(Usuario.correo == correo).first()
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return usuario


def require_role(roles_permitidos: List[int]):
    """
    Dependency factory de FastAPI que verifica que el usuario tenga
    uno de los roles permitidos.
    
    Uso:
        @router.post("/places", dependencies=[Depends(require_role([2, 3]))])
    
    Args:
        roles_permitidos: Lista de roles que pueden acceder al endpoint
    
    Returns:
        Función dependency que verifica el rol del usuario
    
    Raises:
        HTTPException 403 si el usuario no tiene el rol requerido
    """
    def role_checker(current_user = Depends(get_current_user)):
        if current_user.rol not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Se requiere uno de los roles: {', '.join(map(str, roles_permitidos))}"
            )
        return current_user
    return role_checker
