from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
import shutil
import os
import uuid
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

    # Generar nombre único para evitar colisiones
    extension = file.filename.split(".")[-1].lower()
    if extension not in ["jpg", "jpeg", "png", "webp"]:
        raise HTTPException(status_code=400, detail="Formato de imagen no permitido")
        
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
