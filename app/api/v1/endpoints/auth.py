"""
Rutas OAuth2 de EXPLORO.

Endpoints para el flujo completo de autenticación con Google:
- Login: genera URL de autorización del proveedor para redirigir al usuario
- Callback: recibe el código de autorización, emite tokens JWT propios
- Refresh: renueva el access_token usando un refresh_token válido
- Me: retorna y actualiza datos del usuario autenticado
- Logout OAuth: invalida el refresh_token del usuario en la BD

Todos los endpoints están bajo el prefijo /auth (montado en /api/v1 en main.py).
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.api.deps import get_current_user
from app.core.security import verify_token
from app.models.user import Usuario
from app.schemas.auth import (
    TokenWithUser,
    UserResponse,
    UserMeUpdate,
    RefreshRequest,
)
from app.services.oauth_service import (
    authenticate_google,
    build_google_auth_url,
)

router = APIRouter(prefix="/auth", tags=["OAuth2 - Autenticación Social"])


# ================================================================
# GOOGLE OAUTH2
# ================================================================

@router.get(
    "/google/login",
    summary="Obtener URL de autorización de Google",
    description=(
        "Devuelve la URL de Google a la que el frontend debe redirigir al usuario "
        "para iniciar el flujo OAuth2. El parámetro `redirect_uri` debe coincidir "
        "exactamente con el configurado en Google Cloud Console."
    )
)
def google_login(
    redirect_uri: Optional[str] = Query(
        None,
        description="URI de redirección registrada en Google Console (opcional, usa valor del .env por defecto)"
    )
):
    """
    Genera y retorna la URL de autorización de Google OAuth2.

    El frontend debe redirigir al navegador del usuario a esta URL.
    Google pedirá consentimiento y luego redirigirá al redirect_uri
    con un parámetro `code` que debe enviarse a /auth/google/callback.
    """
    auth_url = build_google_auth_url(redirect_uri)
    return {"auth_url": auth_url, "provider": "google"}


@router.get(
    "/google/callback",
    response_model=TokenWithUser,
    summary="Callback de Google OAuth2",
    description=(
        "Recibe el código de autorización devuelto por Google, lo intercambia "
        "por información del usuario, crea o recupera el registro en PostgreSQL, "
        "y emite los tokens JWT propios de EXPLORO."
    )
)
def google_callback(
    code: str = Query(..., description="Código de autorización de un solo uso devuelto por Google"),
    redirect_uri: Optional[str] = Query(
        None,
        description="URI de redirección usada en el paso de login (debe ser idéntica)"
    ),
    db: Session = Depends(get_db)
):
    """
    Procesa el callback del flujo OAuth2 de Google.

    - Intercambia el código por tokens de Google (httpx).
    - Obtiene email, nombre, foto y sub del usuario.
    - Crea el usuario en PostgreSQL si no existe.
    - Retorna access_token + refresh_token propios de EXPLORO.
    - Lanza 409 si el correo ya está registrado con login local o Google.
    """
    from app.core.config import settings
    uri = redirect_uri or settings.GOOGLE_REDIRECT_URI
    result = authenticate_google(code=code, redirect_uri=uri, db=db)
    
    # Redirigir al frontend con los tokens en la URL para que los capture
    from fastapi.responses import RedirectResponse
    from app.core.config import settings
    
    frontend_url = settings.FRONTEND_URL or "http://localhost:3000"
    target_url = f"{frontend_url}/auth/callback?token={result['access_token']}&refresh_token={result['refresh_token']}"
    
    return RedirectResponse(url=target_url)


@router.post(
    "/google/callback",
    response_model=TokenWithUser,
    summary="Callback de Google OAuth2 (POST)",
    description=(
        "Versión POST del callback. El frontend envía el código en el cuerpo. "
        "Útil cuando se prefiere no exponer el código en la URL."
    )
)
def google_callback_post(
    code: str = Query(..., description="Código de autorización de Google"),
    redirect_uri: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Procesa el callback de Google recibido por POST."""
    from app.core.config import settings
    uri = redirect_uri or settings.GOOGLE_REDIRECT_URI
    return authenticate_google(code=code, redirect_uri=uri, db=db)




# ================================================================
# REFRESH TOKEN
# ================================================================

@router.post(
    "/refresh",
    summary="Renovar access token",
    description=(
        "Valida el refresh_token enviado en el cuerpo y emite un nuevo access_token. "
        "El refresh_token debe ser el emitido por EXPLORO en el último login OAuth2 "
        "o login local. Si el token está revocado o no coincide con el almacenado "
        "en la BD, se retorna 401."
    )
)
def refresh_access_token(body: RefreshRequest, db: Session = Depends(get_db)):
    """
    Renueva el access_token usando un refresh_token válido.

    Verifica:
    1. Que el refresh_token sea un JWT válido firmado por EXPLORO.
    2. Que el claim 'type' sea 'refresh' (no un access token reutilizado).
    3. Que el correo (sub) exista en la BD y el usuario esté activo.
    4. Que el refresh_token almacenado en la BD coincida (invalida sesiones anteriores).
    """
    from app.core.security import create_access_token

    # Verificar firma y expiración del JWT
    payload = verify_token(body.refresh_token)

    # Verificar que sea un refresh token, no un access token
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token proporcionado no es un refresh token válido",
            headers={"WWW-Authenticate": "Bearer"}
        )

    correo: str = payload.get("sub")
    if not correo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido: claim 'sub' ausente",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Verificar existencia y estado del usuario
    usuario = db.query(Usuario).filter(Usuario.correo == correo).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"}
        )
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La cuenta está desactivada. Contacta con soporte.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Verificar que el refresh token almacenado coincida (seguridad de rotación)
    if usuario.refresh_token != body.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revocado. Inicia sesión nuevamente.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Emitir nuevo access_token
    claims = {
        "sub": usuario.correo,
        "id_usuario": usuario.id_usuario,
        "rol": usuario.rol,
        "proveedor_auth": usuario.proveedor_auth,
        "scopes": ["read", "write"],
    }
    nuevo_access_token = create_access_token(data=claims)

    return {
        "access_token": nuevo_access_token,
        "token_type": "bearer"
    }


# ================================================================
# PERFIL DEL USUARIO AUTENTICADO
# ================================================================

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Obtener perfil del usuario autenticado",
    description=(
        "Retorna los datos del usuario que porta el JWT en el header Authorization. "
        "Requiere un access_token válido emitido por EXPLORO (Google o Facebook OAuth). "
        "Compatible también con usuarios registrados por el flujo local."
    )
)
def get_me(current_user: Usuario = Depends(get_current_user)):
    """
    Devuelve el perfil del usuario actualmente autenticado.

    Extrae el usuario del JWT vía la dependency get_current_user
    de app/core/security.py. No realiza consultas adicionales a la BD.
    """
    return current_user


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Actualizar perfil del usuario autenticado",
    description=(
        "Permite al usuario autenticado actualizar su nombre y/o preferencias de categorías. "
        "No se permite modificar el correo ni el proveedor de autenticación. "
        "Los cambios se persisten en PostgreSQL inmediatamente."
    )
)
def update_me(
    datos: UserMeUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Actualiza nombre y/o preferencias del usuario autenticado.

    Solo se actualiza lo que el cliente envíe (campos opcionales en UserMeUpdate).
    El correo y el proveedor de autenticación son inmutables por seguridad.
    """
    if datos.nombre is not None:
        current_user.nombre = datos.nombre
    if datos.preferencias is not None:
        current_user.preferencias = datos.preferencias

    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    return current_user


# ================================================================
# LOGOUT OAUTH
# ================================================================

@router.post(
    "/logout",
    summary="Cerrar sesión OAuth",
    description=(
        "Invalida el refresh_token del usuario en la base de datos. "
        "El access_token actual seguirá siendo válido hasta su expiración natural "
        "(máximo ACCESS_TOKEN_EXPIRE_MINUTES). Para invalidación inmediata del "
        "access_token, combinar con la blacklist de tokens_revocados."
    )
)
def logout_oauth(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cierra la sesión OAuth invalidando el refresh_token en la BD.

    Al eliminar el refresh_token almacenado, cualquier intento de renovar
    el access_token fallará con 401. El cliente debe eliminar los tokens
    de su almacenamiento local (localStorage, cookies, etc.).
    """
    current_user.refresh_token = None
    current_user.updated_at = datetime.utcnow()
    db.commit()
    return {
        "message": "Sesión cerrada exitosamente. Los tokens han sido invalidados.",
        "provider": current_user.proveedor_auth
    }
