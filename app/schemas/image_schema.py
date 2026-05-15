from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ImagenBase(BaseModel):
    url: str
    entidad_tipo: str
    entidad_id: int

class ImagenCreate(ImagenBase):
    pass

class ImagenResponse(ImagenBase):
    id_imagen: int
    id_usuario: int
    created_at: datetime

    class Config:
        from_attributes = True
