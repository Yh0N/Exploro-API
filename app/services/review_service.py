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
from app.models.pyme import Pyme
from app.models.user import Usuario
from app.schemas.review_schema import ReviewCreate


def crear_reseña(
    db: Session, 
    datos: ReviewCreate, 
    usuario: Usuario,
    id_lugar: int = None, 
    id_pyme: int = None,
    id_usuario_destino: int = None
) -> dict:
    """
    Publica una nueva reseña sobre un lugar o una pyme.
    """
    filtro = {}
    if id_lugar:
        # Verificar que el lugar existe
        lugar = db.query(Lugar).filter(Lugar.id_lugar == id_lugar).first()
        if not lugar:
            raise HTTPException(status_code=404, detail="Lugar no encontrado")
        filtro = {"id_lugar": id_lugar}
    elif id_pyme:
        # Verificar que la pyme existe
        pyme = db.query(Pyme).filter(Pyme.id_pyme == id_pyme).first()
        if not pyme:
            raise HTTPException(status_code=404, detail="Pyme no encontrada")
        filtro = {"id_pyme": id_pyme}
    elif id_usuario_destino:
        # Verificar que el usuario destino existe
        usuario_dest = db.query(Usuario).filter(Usuario.id_usuario == id_usuario_destino).first()
        if not usuario_dest:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        filtro = {"id_usuario_destino": id_usuario_destino}
    else:
        raise HTTPException(status_code=400, detail="Debe especificar un Lugar, una Pyme o un Usuario destino")

    # Verificar que el usuario no haya reseñado este destino
    reseña_existente = db.query(Reseña).filter_by(
        id_usuario=usuario.id_usuario,
        **filtro
    ).first()
    
    if reseña_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya has publicado una reseña para este destino"
        )

    # Crear la reseña
    nueva_reseña = Reseña(
        id_usuario=usuario.id_usuario,
        id_lugar=id_lugar,
        id_pyme=id_pyme,
        id_usuario_destino=id_usuario_destino,
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
        "id_pyme": nueva_reseña.id_pyme,
        "id_usuario_destino": nueva_reseña.id_usuario_destino,
        "comentarios": nueva_reseña.comentarios,
        "puntuacion": nueva_reseña.puntuacion,
        "fecha": nueva_reseña.fecha,
        "nombre_usuario": usuario.nombre
    }


def listar_reseñas(db: Session, id_lugar: int = None, id_pyme: int = None, id_usuario_destino: int = None) -> List[dict]:
    """
    Lista todas las reseñas de un lugar o pyme específico.
    """
    query = db.query(Reseña, Usuario.nombre).join(
        Usuario, Reseña.id_usuario == Usuario.id_usuario
    )

    if id_lugar:
        query = query.filter(Reseña.id_lugar == id_lugar)
    elif id_pyme:
        query = query.filter(Reseña.id_pyme == id_pyme)
    elif id_usuario_destino:
        query = query.filter(Reseña.id_usuario_destino == id_usuario_destino)

    resenas = query.order_by(Reseña.fecha.desc()).all()

    return [
        {
            "id_resena": resena.id_resena,
            "id_usuario": resena.id_usuario,
            "id_lugar": resena.id_lugar,
            "id_pyme": resena.id_pyme,
            "id_usuario_destino": resena.id_usuario_destino,
            "comentarios": resena.comentarios,
            "puntuacion": resena.puntuacion,
            "fecha": resena.fecha,
            "nombre_usuario": nombre
        }
        for resena, nombre in resenas
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
    if reseña.id_usuario != usuario.id_usuario and usuario.rol != 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar esta reseña"
        )

    db.delete(reseña)
    db.commit()
    return {"message": "Reseña eliminada exitosamente"}


def actualizar_reseña(db: Session, id_resena: int, datos: ReviewCreate, usuario: Usuario) -> dict:
    """
    Actualiza una reseña existente.
    Solo el autor de la reseña puede modificarla.
    """
    reseña = db.query(Reseña).filter(Reseña.id_resena == id_resena).first()
    if not reseña:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reseña no encontrada"
        )

    # Verificar permisos: solo el autor puede editar (o admin si es necesario, pero usualmente solo autor)
    if reseña.id_usuario != usuario.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para editar esta reseña"
        )

    # Actualizar campos
    reseña.comentarios = datos.comentarios
    reseña.puntuacion = datos.puntuacion
    
    db.commit()
    db.refresh(reseña)

    return {
        "id_resena": reseña.id_resena,
        "id_usuario": reseña.id_usuario,
        "comentarios": reseña.comentarios,
        "puntuacion": reseña.puntuacion,
        "fecha": reseña.fecha,
        "message": "Reseña actualizada exitosamente"
    }
