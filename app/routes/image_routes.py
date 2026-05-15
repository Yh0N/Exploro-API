from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database.connection import get_db
from app.core.security import get_current_user
from app.models.user import Usuario
from app.models.image import Imagen
from app.models.place import Lugar
from app.models.pyme import Pyme
from app.schemas.image_schema import ImagenResponse
from app.services.image_service import process_and_save_image, delete_image_file

router = APIRouter(prefix="/imagenes", tags=["Imágenes (RF12)"])

# Límites configurados
LIMIT_PYME = 10
LIMIT_LUGAR_PER_USER = 5

@router.post("/pymes/{pyme_id}", response_model=ImagenResponse)
async def subir_imagen_pyme(
    pyme_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Sube una imagen para una PYME. 
    Solo el dueño puede subir (o admin). Límite: 10 fotos por PYME.
    """
    pyme = db.query(Pyme).filter(Pyme.id_pyme == pyme_id).first()
    if not pyme:
        raise HTTPException(status_code=404, detail="PYME no encontrada")
    
    # Autorización: Dueño o Admin (rol 3)
    if pyme.id_usuario != current_user.id_usuario and current_user.rol != 3:
        raise HTTPException(status_code=403, detail="Solo el dueño de la PYME puede subir imágenes")

    # Validar límite total de la PYME
    total_fotos = db.query(Imagen).filter(
        Imagen.entidad_tipo == 'pyme', 
        Imagen.entidad_id == pyme_id
    ).count()
    
    if total_fotos >= LIMIT_PYME:
        raise HTTPException(status_code=400, detail="Límite de imágenes alcanzado para esta PYME")

    # Procesar y guardar
    relative_url = process_and_save_image(file, "pyme", pyme_id)
    
    # Persistir en DB
    nueva_imagen = Imagen(
        url=relative_url,
        entidad_tipo='pyme',
        entidad_id=pyme_id,
        id_usuario=current_user.id_usuario
    )
    db.add(nueva_imagen)

    # ACTUALIZAR COLUMNA 'fotos' EN PYME (Sincronización)
    fotos_actuales = pyme.fotos.split(",") if pyme.fotos else []
    fotos_actuales.append(relative_url)
    pyme.fotos = ",".join(fotos_actuales)
    
    # Establecer foto_principal si no tiene
    if not pyme.foto_principal:
        pyme.foto_principal = relative_url

    db.commit()
    db.refresh(nueva_imagen)
    return nueva_imagen

@router.post("/lugares/{lugar_id}", response_model=ImagenResponse)
async def subir_imagen_lugar(
    lugar_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Sube una imagen para un lugar turístico.
    Cualquier usuario autenticado puede subir. Límite: 5 fotos por usuario en este lugar.
    """
    lugar = db.query(Lugar).filter(Lugar.id_lugar == lugar_id).first()
    if not lugar:
        raise HTTPException(status_code=404, detail="Lugar no encontrado")

    # Validar límite por usuario en este lugar
    user_fotos_count = db.query(Imagen).filter(
        Imagen.entidad_tipo == 'lugar',
        Imagen.entidad_id == lugar_id,
        Imagen.id_usuario == current_user.id_usuario
    ).count()
    
    if user_fotos_count >= LIMIT_LUGAR_PER_USER:
        raise HTTPException(status_code=400, detail="Has alcanzado el límite de 5 fotos para este lugar")

    # Procesar y guardar
    relative_url = process_and_save_image(file, "lugar", lugar_id)
    
    # Persistir en DB
    nueva_imagen = Imagen(
        url=relative_url,
        entidad_tipo='lugar',
        entidad_id=lugar_id,
        id_usuario=current_user.id_usuario
    )
    db.add(nueva_imagen)

    # ACTUALIZAR COLUMNA 'fotos' EN LUGAR (Sincronización)
    fotos_actuales = lugar.fotos.split(",") if lugar.fotos else []
    fotos_actuales.append(relative_url)
    lugar.fotos = ",".join(fotos_actuales)

    # Establecer foto_principal si no tiene
    if not lugar.foto_principal:
        lugar.foto_principal = relative_url

    db.commit()
    db.refresh(nueva_imagen)
    return nueva_imagen

@router.get("/pymes/{pyme_id}", response_model=List[ImagenResponse])
async def listar_imagenes_pyme(pyme_id: int, db: Session = Depends(get_db)):
    return db.query(Imagen).filter(Imagen.entidad_tipo == 'pyme', Imagen.entidad_id == pyme_id).all()

@router.get("/lugares/{lugar_id}", response_model=List[ImagenResponse])
async def listar_imagenes_lugar(lugar_id: int, db: Session = Depends(get_db)):
    return db.query(Imagen).filter(Imagen.entidad_tipo == 'lugar', Imagen.entidad_id == lugar_id).all()

@router.delete("/legacy", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_imagen_legacy(
    entity_type: str,
    entity_id: int,
    url_to_delete: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Elimina una imagen que no está en la tabla 'imagenes' pero sí en la columna 'fotos' (Legacy).
    """
    if entity_type == 'lugar':
        entidad = db.query(Lugar).filter(Lugar.id_lugar == entity_id).first()
    else:
        entidad = db.query(Pyme).filter(Pyme.id_pyme == entity_id).first()

    if not entidad:
        raise HTTPException(status_code=404, detail="Entidad no encontrada")

    # Autorización: Solo dueño de la entidad o Admin
    if entidad.id_usuario != current_user.id_usuario and current_user.rol != 3:
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar esta imagen")

    # Limpiar URL (quitar dominio si viene completo)
    # Ejemplo: http://localhost:8000/uploads/file.png -> /uploads/file.png
    relative_url = url_to_delete
    if "uploads/" in url_to_delete:
        relative_url = "/uploads/" + url_to_delete.split("uploads/")[-1]

    # Eliminar de la columna fotos
    if entidad.fotos:
        fotos_list = entidad.fotos.split(",")
        if relative_url in fotos_list:
            fotos_list.remove(relative_url)
            entidad.fotos = ",".join(fotos_list)
            
            # Actualizar foto principal si es necesario
            if entidad.foto_principal == relative_url:
                entidad.foto_principal = fotos_list[0] if fotos_list else None
            
            # Eliminar archivo físico
            delete_image_file(relative_url)
            
            db.commit()
            return None
    
    raise HTTPException(status_code=404, detail="La imagen no se encontró en los registros de la entidad")

@router.delete("/{imagen_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_imagen(
    imagen_id: int, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    imagen = db.query(Imagen).filter(Imagen.id_imagen == imagen_id).first()
    if not imagen:
        raise HTTPException(status_code=404, detail="Imagen no encontrada")

    # Autorización: Dueño de la foto, Dueño del Lugar/Pyme o Admin
    permiso = False
    if current_user.rol == 3: # Admin
        permiso = True
    elif imagen.id_usuario == current_user.id_usuario: # Autor de la foto
        permiso = True
    else:
        # Verificar si es dueño de la entidad (Lugar o Pyme)
        if imagen.entidad_tipo == 'lugar':
            entidad = db.query(Lugar).filter(Lugar.id_lugar == imagen.entidad_id).first()
        else:
            entidad = db.query(Pyme).filter(Pyme.id_pyme == imagen.entidad_id).first()
            
        if entidad and entidad.id_usuario == current_user.id_usuario:
            permiso = True

    if not permiso:
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar esta imagen")

    # Eliminar archivo físico
    delete_image_file(imagen.url)
    
    # ELIMINAR DE COLUMNA 'fotos' (Sincronización)
    if imagen.entidad_tipo == 'lugar':
        entidad = db.query(Lugar).filter(Lugar.id_lugar == imagen.entidad_id).first()
    else:
        entidad = db.query(Pyme).filter(Pyme.id_pyme == imagen.entidad_id).first()
    
    if entidad and entidad.fotos:
        fotos_actuales = entidad.fotos.split(",")
        if imagen.url in fotos_actuales:
            fotos_actuales.remove(imagen.url)
            entidad.fotos = ",".join(fotos_actuales)
            
            # Si era la foto principal, actualizarla
            if entidad.foto_principal == imagen.url:
                entidad.foto_principal = fotos_actuales[0] if fotos_actuales else None

    # Eliminar de DB
    db.delete(imagen)
    db.commit()
    return None
