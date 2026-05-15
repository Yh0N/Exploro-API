import os
import uuid
from PIL import Image
from fastapi import UploadFile, HTTPException
from pathlib import Path
import io

# Configuración básica
UPLOAD_DIR = "uploads"
MAX_SIZE_MB = 5
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_DIMENSIONS = (2048, 2048)

def process_and_save_image(file: UploadFile, entity_type: str, entity_id: int) -> str:
    """
    Valida, redimensiona y guarda una imagen en el sistema de archivos local.
    Retorna la URL relativa del archivo guardado.
    """
    # 1. Validar extensión
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Formato no permitido. Use JPG, PNG o WEBP")

    # 2. Validar tamaño (lectura inicial para check rápido si es posible)
    # Nota: para archivos muy grandes es mejor leer en chunks, pero para 5MB está bien así
    content = file.file.read()
    if len(content) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Tamaño máximo 5 MB")

    # 3. Procesamiento con Pillow
    try:
        img = Image.open(io.BytesIO(content))
        
        # Validar modo de color (convertir RGBA a RGB si es necesario para JPEG)
        if img.mode in ("RGBA", "P") and file_ext in (".jpg", ".jpeg"):
            img = img.convert("RGB")

        # Redimensionar si excede dimensiones máximas
        if img.width > MAX_DIMENSIONS[0] or img.height > MAX_DIMENSIONS[1]:
            img.thumbnail(MAX_DIMENSIONS, Image.Resampling.LANCZOS)

        # 4. Generar ruta y nombre único
        target_dir = Path(UPLOAD_DIR) / entity_type / str(entity_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{uuid.uuid4()}{file_ext}"
        file_path = target_dir / filename
        
        # 5. Guardar optimizado
        # Si es muy grande, forzamos optimización o conversión a WEBP si se desea
        # Por ahora guardamos en su formato original pero con calidad controlada
        img.save(file_path, optimize=True, quality=85)
        
        # Retornar URL relativa para la DB
        return f"/uploads/{entity_type}/{entity_id}/{filename}"
        
    except Exception as e:
        print(f"Error procesando imagen: {e}")
        raise HTTPException(status_code=500, detail="Error interno al procesar la imagen")
    finally:
        file.file.close()

def delete_image_file(relative_url: str):
    """Elimina el archivo físico del disco"""
    if not relative_url:
        return
    
    # Quitar el prefijo /uploads/ si existe para construir la ruta real
    clean_path = relative_url.lstrip('/')
    full_path = Path(clean_path)
    
    if full_path.exists():
        full_path.unlink()
