"""
Servicio de autenticación de EXPLORO.
Contiene la lógica de negocio para:
- Registro de nuevos usuarios (con creación automática de perfil)
- Inicio de sesión (verificación de credenciales y generación de JWT)
- Cierre de sesión (revocación del token en la lista negra)
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import Usuario
from app.models.profile import Perfil
from app.models.auth_token import TokenRevocado
from app.core.security import hash_password, verify_password, create_access_token, verify_token
from app.schemas.user_schema import UserCreate, UserLogin, UserSocialLogin
import secrets
import string


def registrar_usuario(db: Session, datos: UserCreate) -> Usuario:
    """
    Registra un nuevo usuario en el sistema.
    
    1. Verifica que el correo no esté ya registrado
    2. Cifra la contraseña con bcrypt
    3. Crea el registro de usuario
    4. Crea automáticamente un perfil vacío asociado
    
    Args:
        db: Sesión de base de datos
        datos: Datos del nuevo usuario (nombre, correo, contraseña, preferencias, rol)
    
    Returns:
        Objeto Usuario creado
    
    Raises:
        HTTPException 400 si el correo ya está registrado
    """
    # Verificar si el correo ya existe
    usuario_existente = db.query(Usuario).filter(Usuario.correo == datos.correo).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado"
        )

    # Crear el usuario con la contraseña cifrada
    nuevo_usuario = Usuario(
        nombre=datos.nombre,
        correo=datos.correo,
        contraseña=hash_password(datos.contraseña),
        preferencias=datos.preferencias if datos.preferencias else [],
        rol=datos.rol if datos.rol else 1
    )
    db.add(nuevo_usuario)
    db.flush()  # Obtener el id_usuario sin hacer commit

    # Crear perfil vacío automáticamente
    perfil = Perfil(
        id_usuario=nuevo_usuario.id_usuario
    )
    db.add(perfil)
    db.commit()
    db.refresh(nuevo_usuario)

    return nuevo_usuario


def login_usuario(db: Session, datos: UserLogin) -> dict:
    """
    Inicia sesión de un usuario.
    
    1. Busca al usuario por correo
    2. Verifica la contraseña con bcrypt
    3. Genera un token JWT con el correo como subject
    
    Args:
        db: Sesión de base de datos
        datos: Credenciales del usuario (correo, contraseña)
    
    Returns:
        Diccionario con access_token y token_type
    
    Raises:
        HTTPException 401 si las credenciales son incorrectas
    """
    # Buscar usuario por correo
    usuario = db.query(Usuario).filter(Usuario.correo == datos.correo).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )

    # Verificar la contraseña
    if not verify_password(datos.contraseña, usuario.contraseña):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )
    # Generar token JWT
    access_token = create_access_token(data={"sub": usuario.correo})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


def login_social_usuario(db: Session, datos: UserSocialLogin) -> dict:
    """
    Inicia sesión de un usuario mediante proveedor social (Google/Facebook).
    
    1. Si el usuario existe por correo, lo loguea.
    2. Si no existe, lo crea automáticamente.
    """
    # En un sistema real, aquí validaríamos el id_token con Google/Facebook
    # Para fines de demostración, usaremos el correo enviado
    correo = datos.correo or f"{datos.provider}_{secrets.token_hex(4)}@exploro.com"
    nombre = datos.nombre or f"Usuario {datos.provider.capitalize()}"
    
    usuario = db.query(Usuario).filter(Usuario.correo == correo).first()
    
    if not usuario:
        # Crear usuario nuevo
        # Generar contraseña aleatoria segura que el usuario nunca usará directamente
        alphabet = string.ascii_letters + string.digits
        random_password = ''.join(secrets.choice(alphabet) for i in range(20))
        
        usuario = Usuario(
            nombre=nombre,
            correo=correo,
            contraseña=hash_password(random_password),
            rol=1 # Turista por defecto
        )
        db.add(usuario)
        db.flush()
        
        perfil = Perfil(id_usuario=usuario.id_usuario)
        db.add(perfil)
        db.commit()
        db.refresh(usuario)
    
    # Generar token JWT
    access_token = create_access_token(data={"sub": usuario.correo})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


def logout_usuario(db: Session, token: str, usuario: Usuario) -> dict:
    """
    Cierra la sesión del usuario revocando su token JWT.
    
    Agrega el token a la tabla de tokens revocados (blacklist).
    Las futuras peticiones con este token serán rechazadas por
    get_current_user() en security.py.
    
    Args:
        db: Sesión de base de datos
        token: Token JWT a revocar
        usuario: Usuario autenticado actual
    
    Returns:
        Diccionario con mensaje de confirmación
    """
    # Decodificar el token para obtener la fecha de expiración
    payload = verify_token(token)
    exp_timestamp = payload.get("exp")
    fecha_expiracion = None
    if exp_timestamp:
        fecha_expiracion = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)

    # Guardar el token en la blacklist
    token_revocado = TokenRevocado(
        id_usuario=usuario.id_usuario,
        token=token,
        fecha_expiracion=fecha_expiracion
    )
    db.add(token_revocado)
    db.commit()

    return {"message": "Sesión cerrada exitosamente"}
