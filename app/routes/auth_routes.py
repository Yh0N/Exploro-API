"""
Rutas de autenticación de EXPLORO.
Endpoints para registro, inicio de sesión y cierre de sesión.
"""

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.user_schema import UserCreate, UserResponse, Token, UserLogin
from app.services.auth_service import registrar_usuario, login_usuario, logout_usuario
from app.core.security import get_current_user, oauth2_scheme

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario",
    description="Crea una nueva cuenta de usuario con perfil vacío asociado"
)
def register(datos: UserCreate, db: Session = Depends(get_db)):
    """
    Registra un nuevo usuario en el sistema EXPLORO.
    
    - Valida que el correo no esté ya registrado
    - Cifra la contraseña con bcrypt
    - Crea automáticamente un perfil vacío
    """
    usuario = registrar_usuario(db, datos)
    return usuario


@router.post(
    "/login",
    response_model=Token,
    summary="Iniciar sesión",
    description="Autentica al usuario y retorna un token JWT"
)
def login(datos: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Inicia sesión con correo y contraseña.
    
    Usa el estándar OAuth2PasswordRequestForm para soportar el login nativo
    en Swagger UI (botón Authorize).
    Retorna un token JWT Bearer para usar en endpoints protegidos.
    """
    datos_login = UserLogin(correo=datos.username, contraseña=datos.password)
    return login_usuario(db, datos_login)


@router.post(
    "/logout",
    summary="Cerrar sesión",
    description="Revoca el token JWT actual del usuario"
)
def logout(
    token: str = Depends(oauth2_scheme),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cierra la sesión del usuario revocando su token JWT.
    
    El token se agrega a la lista negra (tabla tokens_revocados).
    Las futuras peticiones con este token serán rechazadas.
    """
    return logout_usuario(db, token, current_user)
