"""
Servicio de reseñas de EXPLORO.
Contiene la lógica de negocio para:
- Publicar reseñas sobre lugares turísticos
- Listar reseñas de un lugar específico
- Eliminar reseñas (autor o admin)

La calificación promedio del lugar se calcula dinámicamente
con AVG() al consultar, sin almacenar un valor estático.
"""

from typing import List
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.review import Reseña
from app.models.place import Lugar
from app.models.user import Usuario
from app.schemas.review_schema import ReviewCreate


def crear_reseña(db: Session, id_lugar: int, datos: ReviewCreate, usuario: Usuario) -> dict:
    """
    Publica una nueva reseña sobre un lugar turístico.
    
    Verifica que el lugar exista y que el usuario no haya
    reseñado el mismo lugar previamente.
    
    Args:
        db: Sesión de base de datos
        id_lugar: ID del lugar a reseñar
        datos: Datos de la reseña (comentarios, puntuación)
        usuario: Usuario autenticado
    
    Returns:
        Diccionario con los datos de la reseña creada
    
    Raises:
        HTTPException 404 si el lugar no existe
        HTTPException 400 si el usuario ya reseñó este lugar
    """
    # Verificar que el lugar existe
    lugar = db.query(Lugar).filter(Lugar.id_lugar == id_lugar).first()
    if not lugar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lugar no encontrado"
        )

    # Verificar que el usuario no haya reseñado este lugar
    reseña_existente = db.query(Reseña).filter(
        Reseña.id_usuario == usuario.id_usuario,
        Reseña.id_lugar == id_lugar
    ).first()
    if reseña_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya has publicado una reseña para este lugar"
        )

    # Crear la reseña
    nueva_reseña = Reseña(
        id_usuario=usuario.id_usuario,
        id_lugar=id_lugar,
        comentarios=datos.comentarios,
        puntuacion=datos.puntuacion
    )
    db.add(nueva_reseña)
    db.commit()
    db.refresh(nueva_reseña)

    return {
        "id_resena": nueva_reseña.id_resena,
        "id_usuario": nueva_reseña.id_usuario,
        "id_lugar": nueva_reseña.id_lugar,
        "comentarios": nueva_reseña.comentarios,
        "puntuacion": nueva_reseña.puntuacion,
        "fecha": nueva_reseña.fecha,
        "nombre_usuario": usuario.nombre
    }


def listar_reseñas(db: Session, id_lugar: int) -> List[dict]:
    """
    Lista todas las reseñas de un lugar específico.
    Incluye el nombre del autor de cada reseña.
    
    Args:
        db: Sesión de base de datos
        id_lugar: ID del lugar
    
    Returns:
        Lista de diccionarios con las reseñas y nombre del autor
    
    Raises:
        HTTPException 404 si el lugar no existe
    """
    # Verificar que el lugar existe
    lugar = db.query(Lugar).filter(Lugar.id_lugar == id_lugar).first()
    if not lugar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lugar no encontrado"
        )

    # Obtener reseñas con join para incluir el nombre del usuario
    resenas = db.query(Reseña, Usuario.nombre).join(
        Usuario, Reseña.id_usuario == Usuario.id_usuario
    ).filter(
        Reseña.id_lugar == id_lugar
    ).order_by(Reseña.fecha.desc()).all()

    return [
        {
            "id_resena": reseña.id_resena,
            "id_usuario": reseña.id_usuario,
            "id_lugar": reseña.id_lugar,
            "comentarios": reseña.comentarios,
            "puntuacion": reseña.puntuacion,
            "fecha": reseña.fecha,
            "nombre_usuario": nombre
        }
        for reseña, nombre in reseñas
    ]


def eliminar_reseña(db: Session, id_resena: int, usuario: Usuario) -> dict:
    """
    Elimina una reseña existente.
    Solo el autor de la reseña o un administrador pueden eliminarla.
    
    Args:
        db: Sesión de base de datos
        id_resena: ID de la reseña a eliminar
        usuario: Usuario autenticado
    
    Returns:
        Diccionario con mensaje de confirmación
    
    Raises:
        HTTPException 404 si la reseña no existe
        HTTPException 403 si el usuario no tiene permiso para eliminarla
    """
    reseña = db.query(Reseña).filter(Reseña.id_resena == id_resena).first()
    if not reseña:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reseña no encontrada"
        )

    # Verificar permisos: solo el autor o un admin pueden eliminar
    if reseña.id_usuario != usuario.id_usuario and usuario.rol != "administrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar esta reseña"
        )

    db.delete(reseña)
    db.commit()
    return {"message": "Reseña eliminada exitosamente"}
