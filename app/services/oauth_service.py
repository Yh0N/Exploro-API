"""
Servicio OAuth2 de EXPLORO.

Gestiona el flujo completo de autenticación con Google:
1. Construye la URL de autorización del proveedor.
2. Intercambia el código de autorización por tokens del proveedor (via httpx síncrono).
3. Obtiene la información del usuario (email, nombre, foto, sub/id).
4. Busca o crea el Usuario en PostgreSQL.
5. Detecta conflictos de proveedor (mismo correo, diferente proveedor).
6. Emite access_token y refresh_token propios de EXPLORO (python-jose).
7. Almacena el refresh_token hasheado en la BD para invalidación por servidor.

Requisitos del proyecto:
- RF1: Registro y autenticación de usuarios
- RNF4: Seguridad - autenticación obligatoria, HTTPS, datos sensibles resguardados
- Sin Firebase, Auth0, Clerk ni Supabase
"""

import httpx
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.models.user import Usuario
from app.models.profile import Perfil


# ================================================================
# CONSTANTES DE LOS PROVEEDORES OAUTH
# ================================================================

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"



# ================================================================
# CONSTRUCCIÓN DE URLS DE AUTORIZACIÓN
# ================================================================

def build_google_auth_url(redirect_uri: Optional[str] = None) -> str:
    """
    Construye la URL de autorización de Google OAuth2 con los scopes necesarios.

    El frontend debe redirigir al usuario a esta URL para que autorice el acceso.
    Google devolverá un código de autorización al redirect_uri especificado.

    Args:
        redirect_uri: URI de redirección. Si no se especifica, se usa el valor de .env.

    Returns:
        URL completa de autorización de Google como string.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth no está configurado en el servidor"
        )

    uri = redirect_uri or settings.GOOGLE_REDIRECT_URI
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": uri,
        "response_type": "code",
        # openid: identidad básica | email: correo | profile: nombre y foto
        "scope": "openid email profile",
        "access_type": "offline",   # Necesario para obtener refresh_token de Google
        "prompt": "select_account", # Fuerza selección de cuenta siempre
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{query}"




# ================================================================
# AUTENTICACIÓN GOOGLE
# ================================================================

def authenticate_google(code: str, redirect_uri: str, db: Session) -> dict:
    """
    Ejecuta el flujo completo de autenticación OAuth2 con Google.

    Pasos:
    a) Intercambia el código de autorización por tokens de Google (httpx síncrono).
    b) Obtiene la información del usuario: email, nombre, foto, sub (ID único de Google).
    c) Busca el usuario en PostgreSQL por correo electrónico.
    d) Si no existe: crea Usuario(proveedor_auth='google', email_verificado=True, rol=1).
    e) Si existe con diferente proveedor: lanza HTTPException 409 (conflicto de identidad).
    f) Actualiza foto_perfil si cambió desde la última sesión.
    g) Genera access_token + refresh_token propios de EXPLORO.
    h) Almacena el refresh_token en la BD y retorna {access_token, refresh_token, user}.

    Args:
        code: Código de autorización de un solo uso devuelto por Google.
        redirect_uri: Debe coincidir exactamente con el registrado en Google Console.
        db: Sesión síncrona de SQLAlchemy.

    Returns:
        Diccionario con access_token, refresh_token, token_type y datos del usuario.

    Raises:
        HTTPException 409: Si el correo ya está registrado con otro proveedor.
        HTTPException 400: Si Google rechaza el código de autorización.
        HTTPException 500: Si ocurre un error al contactar los servidores de Google.
    """
    # ── a) Intercambiar código por tokens de Google ───────────────────────────
    token_data = _exchange_google_code(code, redirect_uri)

    # ── b) Obtener información del usuario de Google ──────────────────────────
    userinfo = _get_google_userinfo(token_data["access_token"])

    email: str = userinfo.get("email", "")
    nombre: str = userinfo.get("name", email.split("@")[0])
    foto: Optional[str] = userinfo.get("picture")
    sub: str = userinfo.get("sub", "")           # ID único de Google
    email_verificado: bool = userinfo.get("email_verified", False)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google no proporcionó un correo electrónico válido"
        )

    # ── c/d/e/f) Buscar o crear usuario en PostgreSQL ─────────────────────────
    usuario = _buscar_o_crear_usuario(
        db=db,
        correo=email,
        nombre=nombre,
        foto=foto,
        sub=sub,
        proveedor="google",
        email_verificado=email_verificado
    )

    # ── g/h) Emitir tokens EXPLORO y persistir refresh token ──────────────────
    return _emitir_tokens_exploro(db, usuario)


def _exchange_google_code(code: str, redirect_uri: str) -> dict:
    """
    Intercambia el código de autorización de Google por un access_token del proveedor.

    Realiza una petición POST a la API de Google con las credenciales del servidor.

    Args:
        code: Código de un solo uso devuelto por Google al callback.
        redirect_uri: URI de redirección exacta registrada en Google Console.

    Returns:
        Diccionario con access_token (y opcionalmente id_token, refresh_token de Google).

    Raises:
        HTTPException 400: Si Google responde con error (código inválido, expirado, etc.).
        HTTPException 500: Si ocurre un error de red al contactar Google.
    """
    try:
        response = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=10.0
        )
        token_data = response.json()

        if "error" in token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error de Google OAuth: {token_data.get('error_description', token_data['error'])}"
            )

        return token_data

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error de red al contactar Google: {str(e)}"
        )


def _get_google_userinfo(access_token: str) -> dict:
    """
    Obtiene la información del usuario usando el access_token de Google.

    Consulta el endpoint userinfo de Google para obtener email, nombre,
    foto de perfil y el ID único del usuario (sub).

    Args:
        access_token: Token de acceso de Google (no el de EXPLORO).

    Returns:
        Diccionario con los campos del perfil de Google: email, name, picture, sub.

    Raises:
        HTTPException 500: Si Google rechaza el access_token o hay error de red.
    """
    try:
        response = httpx.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10.0
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo obtener información del usuario de Google"
            )
        return response.json()

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener userinfo de Google: {str(e)}"
        )




# ================================================================
# LÓGICA COMPARTIDA (HELPER FUNCTIONS)
# ================================================================

def _buscar_o_crear_usuario(
    db: Session,
    correo: str,
    nombre: str,
    foto: Optional[str],
    sub: str,
    proveedor: str,
    email_verificado: bool
) -> Usuario:
    """
    Busca un usuario por correo en PostgreSQL o lo crea si no existe.

    Reglas de negocio:
    - Si el correo no existe: crea Usuario con proveedor_auth=proveedor, rol=1.
    - Si el correo existe con el mismo proveedor: actualiza foto_perfil y updated_at.
    - Si el correo existe con diferente proveedor: lanza HTTPException 409 con
      mensaje indicando el proveedor original para guiar al usuario.

    Args:
        db: Sesión de SQLAlchemy.
        correo: Correo electrónico del usuario del proveedor OAuth.
        nombre: Nombre del usuario del proveedor OAuth.
        foto: URL de la foto de perfil del proveedor (puede ser None).
        sub: ID único del usuario en el proveedor (sub de Google, id de Facebook).
        proveedor: Nombre del proveedor: 'google'.
        email_verificado: True si el proveedor verificó el correo.

    Returns:
        Objeto SQLAlchemy Usuario (existente o recién creado).

    Raises:
        HTTPException 409: Si el correo ya está registrado con otro proveedor.
    """
    usuario = db.query(Usuario).filter(Usuario.correo == correo).first()

    if usuario is None:
        # ── CASO: Usuario nuevo ───────────────────────────────────────────────
        usuario = Usuario(
            nombre=nombre,
            correo=correo,
            # La columna 'contraseña' tiene NOT NULL; para usuarios OAuth
            # se guarda una cadena vacía ya que nunca la usarán directamente.
            contraseña="",
            proveedor_auth=proveedor,
            proveedor_id=sub,
            email_verificado=email_verificado,
            foto_perfil=foto,
            rol=1,          # turista por defecto (RF1)
            activo=True,
            updated_at=datetime.utcnow()
        )
        db.add(usuario)
        db.flush()  # Obtener id_usuario sin hacer commit

        # Crear perfil vacío automáticamente (consistente con registrar_usuario)
        perfil = Perfil(id_usuario=usuario.id_usuario)
        db.add(perfil)
        db.commit()
        db.refresh(usuario)

    elif usuario.proveedor_auth != proveedor and usuario.proveedor_auth != "local":
        # ── CASO: Conflicto de proveedor ──────────────────────────────────────
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"El correo '{correo}' ya está registrado con el proveedor "
                f"'{usuario.proveedor_auth}'. "
                f"Por favor, inicia sesión con {usuario.proveedor_auth}."
            )
        )

    else:
        # ── CASO: Usuario existente con el mismo proveedor ────────────────────
        # Actualizar foto de perfil si cambió y registrar la hora de actualización
        if foto and usuario.foto_perfil != foto:
            usuario.foto_perfil = foto
        usuario.updated_at = datetime.utcnow()

        # Si el usuario fue creado localmente y ahora usa OAuth, vincular el proveedor
        if usuario.proveedor_auth == "local":
            usuario.proveedor_auth = proveedor
            usuario.proveedor_id = sub
            usuario.email_verificado = email_verificado

        db.commit()
        db.refresh(usuario)

    return usuario


def _emitir_tokens_exploro(db: Session, usuario: Usuario) -> dict:
    """
    Genera el par access_token / refresh_token de EXPLORO para el usuario.

    Los claims del JWT incluyen: sub (correo), id_usuario, rol, proveedor_auth y scopes.
    El refresh_token se persiste en la columna 'refresh_token' de la tabla usuarios
    para permitir invalidación por el servidor (logout, cambio de contraseña, etc.).

    Args:
        db: Sesión de SQLAlchemy.
        usuario: Objeto Usuario de SQLAlchemy.

    Returns:
        Diccionario con access_token, refresh_token, token_type y datos del usuario.
    """
    claims = {
        "sub": usuario.correo,
        "id_usuario": usuario.id_usuario,
        "rol": usuario.rol,
        "proveedor_auth": usuario.proveedor_auth,
        "scopes": ["read", "write"],
    }

    access_token = create_access_token(data=claims)
    refresh_token = create_refresh_token(data={"sub": usuario.correo, "id_usuario": usuario.id_usuario})

    # Persistir refresh token en BD para control de invalidación por servidor
    usuario.refresh_token = refresh_token
    usuario.updated_at = datetime.utcnow()
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": usuario,
    }
