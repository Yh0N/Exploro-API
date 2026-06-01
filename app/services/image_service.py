import os
import io
from PIL import Image
from fastapi import UploadFile, HTTPException
from pathlib import Path
import cloudinary
import cloudinary.uploader

# Configuración de Cloudinary (variables de entorno en Render)
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

MAX_SIZE_MB = 5
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_DIMENSIONS = (2048, 2048)


def process_and_save_image(file: UploadFile, entity_type: str, entity_id: int) -> str:
    """
    Valida, redimensiona y sube una imagen a Cloudinary.
    Retorna la URL segura permanente (https://res.cloudinary.com/...).
    """
    file_ext = Path(file.filename or "image.jpg").suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Formato no permitido. Use JPG, PNG o WEBP")

    content = file.file.read()
    if len(content) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Tamaño máximo 5 MB")

    try:
        img = Image.open(io.BytesIO(content))

        if img.mode in ("RGBA", "P") and file_ext in (".jpg", ".jpeg"):
            img = img.convert("RGB")

        if img.width > MAX_DIMENSIONS[0] or img.height > MAX_DIMENSIONS[1]:
            img.thumbnail(MAX_DIMENSIONS, Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        save_format = "JPEG" if file_ext in (".jpg", ".jpeg") else img.format or "PNG"
        img.save(buffer, format=save_format, optimize=True, quality=85)
        buffer.seek(0)

        folder = f"exploro/{entity_type}/{entity_id}"
        result = cloudinary.uploader.upload(
            buffer,
            folder=folder,
            resource_type="image"
        )
        return result["secure_url"]

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error procesando imagen: {e}")
        raise HTTPException(status_code=500, detail="Error interno al procesar la imagen")
    finally:
        file.file.close()


def delete_image_file(url: str):
    """Elimina una imagen de Cloudinary usando su URL."""
    if not url:
        return

    # Si es una URL de Cloudinary, extraer el public_id y eliminar
    if "cloudinary.com" in url:
        try:
            # Formato: https://res.cloudinary.com/{cloud}/image/upload/v{ver}/{public_id}.{ext}
            parts = url.split("/upload/")
            if len(parts) == 2:
                after_upload = parts[1]
                # Quitar versión si existe (v1234567890/)
                if after_upload.startswith("v") and "/" in after_upload:
                    after_upload = after_upload.split("/", 1)[1]
                # Quitar extensión para obtener public_id
                public_id = after_upload.rsplit(".", 1)[0]
                cloudinary.uploader.destroy(public_id)
        except Exception as e:
            print(f"Error eliminando imagen de Cloudinary: {e}")
        return

    # Fallback: intentar eliminar del filesystem local (imágenes antiguas)
    clean_path = url.lstrip("/")
    full_path = Path(clean_path)
    if full_path.exists():
        full_path.unlink()
