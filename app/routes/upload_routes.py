"""
Rutas de subida de imágenes de EXPLORO.
Incluye validación real de tipo MIME, tamaño y extensión (TAREA 3).
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
import shutil
import os
import uuid

import magic  # python-magic: validación real de tipo MIME

from app.core.security import get_current_user
from app.models.user import Usuario
from app.database.connection import get_db
from sqlalchemy.orm import Session
from app.models.place import Lugar
from app.models.pyme import Pyme

router = APIRouter(prefix="/upload", tags=["Uploads"])

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# ─────────────────────────────────────────────────────────────────
# TAREA 3: Constantes de validación de archivos
# ─────────────────────────────────────────────────────────────────

# Tipos MIME reales permitidos (verificados con python-magic, no solo extensión)
ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "image/webp"]

# Extensiones permitidas en el nombre del archivo
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

# Tamaño máximo: 5 MB
MAX_FILE_SIZE = 5 * 1024 * 1024


async def validate_image(file: UploadFile) -> UploadFile:
    """
    Valida que el archivo subido sea una imagen legítima.

    Verificaciones realizadas:
    1. Extensión del nombre de archivo (whitelist).
    2. Tipo MIME real usando los bytes del archivo (no confiar en el header del cliente).
    3. Tamaño total no supera MAX_FILE_SIZE (5 MB).

    Retorna el archivo con el puntero reiniciado al inicio, listo para guardar.
    Lanza HTTPException 400 si alguna validación falla.
    """
    # 1. Verificar extensión del nombre de archivo
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo no tiene nombre"
        )

    extension = file.filename.rsplit(".", 1)[-1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Extensión '{extension}' no permitida. Usa: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # 2. Verificar el tipo MIME real leyendo los primeros bytes del archivo
    # Esto previene ataques donde se cambia la extensión de un archivo malicioso
    cabecera = await file.read(1024)
    tipo_mime_real = magic.from_buffer(cabecera, mime=True)

    if tipo_mime_real not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El contenido real del archivo es '{tipo_mime_real}', no una imagen válida. "
                   f"Tipos permitidos: {', '.join(ALLOWED_MIME_TYPES)}"
        )

    # Reiniciar puntero al inicio para poder leer el archivo completo después
    await file.seek(0)

    # 3. Verificar tamaño total del archivo leyendo por chunks
    tamanio_total = 0
    while True:
        chunk = await file.read(8192)  # Leer en bloques de 8 KB
        if not chunk:
            break
        tamanio_total += len(chunk)
        if tamanio_total > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El archivo supera el tamaño máximo permitido de {MAX_FILE_SIZE // (1024 * 1024)} MB"
            )

    # Reiniciar puntero nuevamente para que el guardado funcione correctamente
    await file.seek(0)

    return file


@router.post("/{entity_type}/{entity_id}")
async def upload_image(
    entity_type: str,
    entity_id: int,
    file: UploadFile = File(...),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if entity_type not in ["place", "pyme"]:
        raise HTTPException(status_code=400, detail="Tipo de entidad no válido")

    # Verificar existencia y propiedad
    if entity_type == "place":
        entity = db.query(Lugar).filter(Lugar.id_lugar == entity_id).first()
        if not entity:
            raise HTTPException(status_code=404, detail="Lugar no encontrado")
        # Solo el dueño o admin
        if entity.id_usuario != current_user.id_usuario and current_user.rol != 3:
            raise HTTPException(status_code=403, detail="No tienes permiso para subir fotos a este lugar")
    else:
        entity = db.query(Pyme).filter(Pyme.id_pyme == entity_id).first()
        if not entity:
            raise HTTPException(status_code=404, detail="Pyme no encontrada")
        # Solo el dueño o admin
        if entity.id_usuario != current_user.id_usuario and current_user.rol != 3:
            raise HTTPException(status_code=403, detail="No tienes permiso para subir fotos a esta pyme")

    # Validar imagen: extensión, MIME real y tamaño (TAREA 3)
    file = await validate_image(file)

    # Generar nombre único para evitar colisiones
    extension = file.filename.rsplit(".", 1)[-1].lower()
    filename = f"{uuid.uuid4()}.{extension}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    # Guardar el archivo físicamente
    try:
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar el archivo: {str(e)}")

    # La URL que el frontend usará para acceder a la imagen
    # IMPORTANTE: El backend debe servir la carpeta 'uploads' como estática
    url = f"/uploads/{filename}"

    # Actualizar la base de datos
    if not entity.foto_principal:
        entity.foto_principal = url

    # Manejar lista de fotos (almacenada como string separado por comas)
    current_fotos = entity.fotos.split(",") if entity.fotos else []
    current_fotos.append(url)
    entity.fotos = ",".join(current_fotos)

    db.commit()
    db.refresh(entity)

    return {
        "message": "Imagen subida exitosamente",
        "url": url,
        "foto_principal": entity.foto_principal,
        "fotos": entity.fotos.split(",")
    }
