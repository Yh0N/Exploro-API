"""
Servicio de lugares turísticos de EXPLORO.
Contiene la lógica de negocio para:
- CRUD de lugares (crear, leer, actualizar, eliminar)
- Búsqueda con filtros (categoría, calificación mínima)
- Búsqueda de lugares cercanos con PostGIS (ST_DWithin, ST_Distance)
- Cálculo dinámico de calificación promedio con AVG()
"""

from typing import Optional, List
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.models.place import Lugar
from app.models.review import Reseña
from app.schemas.place_schema import PlaceCreate, PlaceUpdate


def _obtener_estadisticas_resenas(db: Session, id_lugar: int) -> tuple[Optional[float], int]:
    """
    Calcula dinámicamente el promedio y total de reseñas de un lugar.
    """
    stats = db.query(
        func.avg(Reseña.puntuacion),
        func.count(Reseña.id_resena)
    ).filter(Reseña.id_lugar == id_lugar).first()
    
    avg = round(float(stats[0]), 2) if stats[0] else None
    count = stats[1] if stats[1] else 0
    return avg, count


def agregar_calificacion(lugar_dict: dict, db: Session) -> dict:
    """
    Agrega calificacion_promedio y numero_reseñas calculados dinámicamente.
    """
    avg, count = _obtener_estadisticas_resenas(db, lugar_dict["id_lugar"])
    lugar_dict["calificacion_promedio"] = avg
    lugar_dict["numero_reseñas"] = count
    return lugar_dict


def crear_lugar(db: Session, datos: PlaceCreate, id_usuario: int = None) -> dict:
    """
    Registra un nuevo lugar turístico en el sistema.
    
    Construye el punto geoespacial con from_shape(Point(lng, lat), srid=4326)
    para almacenarlo correctamente en la columna PostGIS.
    
    El lugar se crea con aprobado=False, requiere aprobación de admin.
    
    Args:
        db: Sesión de base de datos
        datos: Datos del lugar (nombre, descripcion, latitud, longitud, categoria)
        id_usuario: ID del usuario que crea el lugar
    
    Returns:
        Diccionario con los datos del lugar creado
    """
    # Construir el punto geoespacial con Shapely + GeoAlchemy2 (solo si hay coordenadas)
    punto = None
    if datos.latitud is not None and datos.longitud is not None:
        punto = from_shape(Point(datos.longitud, datos.latitud), srid=4326)

    nuevo_lugar = Lugar(
        nombre=datos.nombre,
        descripcion=datos.descripcion,
        latitud=datos.latitud,
        longitud=datos.longitud,
        ubicacion=punto,
        direccion=datos.ubicacion_textual,
        categoria=datos.categoria,
        subcategoria=getattr(datos, 'subcategoria', None),
        id_usuario=id_usuario,
        aprobado=True
    )
    db.add(nuevo_lugar)
    db.commit()
    db.refresh(nuevo_lugar)

    resultado = {
        "id_lugar": nuevo_lugar.id_lugar,
        "nombre": nuevo_lugar.nombre,
        "descripcion": nuevo_lugar.descripcion,
        "latitud": nuevo_lugar.latitud,
        "longitud": nuevo_lugar.longitud,
        "direccion": nuevo_lugar.direccion,
        "categoria": nuevo_lugar.categoria,
        "aprobado": nuevo_lugar.aprobado,
        "id_usuario": nuevo_lugar.id_usuario,
        "calificacion_promedio": None,
        "foto_principal": nuevo_lugar.foto_principal,
        "fotos": nuevo_lugar.fotos.split(",") if nuevo_lugar.fotos else []
    }
    return resultado


def obtener_lugar(db: Session, id_lugar: int) -> dict:
    """
    Obtiene la información detallada de un lugar por su ID.
    Incluye la calificación promedio calculada dinámicamente.
    
    Args:
        db: Sesión de base de datos
        id_lugar: ID del lugar a consultar
    
    Returns:
        Diccionario con todos los datos del lugar
    
    Raises:
        HTTPException 404 si el lugar no existe
    """
    lugar = db.query(Lugar).filter(Lugar.id_lugar == id_lugar).first()
    if not lugar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lugar no encontrado"
        )

    resultado = {
        "id_lugar": lugar.id_lugar,
        "nombre": lugar.nombre,
        "descripcion": lugar.descripcion,
        "latitud": lugar.latitud,
        "longitud": lugar.longitud,
        "direccion": lugar.direccion,
        "categoria": lugar.categoria,
        "subcategoria": lugar.subcategoria,
        "aprobado": lugar.aprobado,
        "id_usuario": lugar.id_usuario,
        "foto_principal": lugar.foto_principal,
        "fotos": lugar.fotos.split(",") if lugar.fotos else []
    }

    # Agregar info del anfitrión
    if lugar.usuario:
        if lugar.usuario.pyme:
            resultado["host_name"] = lugar.usuario.pyme.nombre
        else:
            resultado["host_name"] = lugar.usuario.nombre
        resultado["host_since"] = str(lugar.usuario.fecha_registro.year)
    else:
        resultado["host_name"] = "Anfitrión de Exploro"
        resultado["host_since"] = "2024"

    return agregar_calificacion(resultado, db)


def listar_lugares(
    db: Session,
    categoria: Optional[str] = None,
    calificacion_min: Optional[float] = None
) -> List[dict]:
    """
    Lista los lugares turísticos aprobados con filtros opcionales.
    Usa SQL JOIN y GROUP BY para calcular promedios directamente,
    solucionando el problema de consultas N+1 en Python.
    
    Args:
        db: Sesión de base de datos
        categoria: Filtrar por categoría (opcional)
        calificacion_min: Filtrar por calificación mínima (opcional)
    
    Returns:
        Lista de diccionarios con los datos de los lugares
    """
    query = db.query(
        Lugar,
        func.avg(Reseña.puntuacion).label("calificacion_promedio"),
        func.count(Reseña.id_resena).label("numero_reseñas")
    ).outerjoin(Reseña, Lugar.id_lugar == Reseña.id_lugar).filter(Lugar.aprobado == True)

    if categoria:
        query = query.filter(Lugar.categoria == categoria)

    query = query.group_by(Lugar.id_lugar)

    if calificacion_min is not None:
        query = query.having(func.avg(Reseña.puntuacion) >= calificacion_min)

    resultados_db = query.all()

    resultados = []
    for lugar, avg, count in resultados_db:
        resultados.append({
            "id_lugar": lugar.id_lugar,
            "nombre": lugar.nombre,
            "descripcion": lugar.descripcion,
            "latitud": lugar.latitud,
            "longitud": lugar.longitud,
            "direccion": lugar.direccion,
            "categoria": lugar.categoria,
            "subcategoria": lugar.subcategoria,
            "aprobado": lugar.aprobado,
            "id_usuario": lugar.id_usuario,
            "foto_principal": lugar.foto_principal,
            "fotos": lugar.fotos.split(",") if lugar.fotos else [],
            "calificacion_promedio": round(float(avg), 2) if avg else None,
            "numero_reseñas": count if count else 0
        })

    return resultados


def actualizar_lugar(db: Session, id_lugar: int, datos: PlaceUpdate) -> dict:
    """
    Actualiza los datos de un lugar existente.
    Solo actualiza los campos que se proporcionan (no nulos).
    Si se actualizan coordenadas, reconstruye el punto geoespacial.
    
    Args:
        db: Sesión de base de datos
        id_lugar: ID del lugar a actualizar
        datos: Campos a actualizar
    
    Returns:
        Diccionario con los datos actualizados del lugar
    
    Raises:
        HTTPException 404 si el lugar no existe
    """
    lugar = db.query(Lugar).filter(Lugar.id_lugar == id_lugar).first()
    if not lugar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lugar no encontrado"
        )

    # Actualizar solo los campos proporcionados
    if datos.nombre is not None:
        lugar.nombre = datos.nombre
    if datos.descripcion is not None:
        lugar.descripcion = datos.descripcion
    if datos.categoria is not None:
        lugar.categoria = datos.categoria

    # Si se actualizan coordenadas, reconstruir el punto geoespacial
    nueva_lat = datos.latitud if datos.latitud is not None else lugar.latitud
    nueva_lng = datos.longitud if datos.longitud is not None else lugar.longitud
    if datos.latitud is not None or datos.longitud is not None:
        lugar.latitud = nueva_lat
        lugar.longitud = nueva_lng
        lugar.ubicacion = from_shape(Point(nueva_lng, nueva_lat), srid=4326)

    db.commit()
    db.refresh(lugar)

    resultado = {
        "id_lugar": lugar.id_lugar,
        "nombre": lugar.nombre,
        "descripcion": lugar.descripcion,
        "latitud": lugar.latitud,
        "longitud": lugar.longitud,
        "categoria": lugar.categoria,
        "aprobado": lugar.aprobado,
    }
    return agregar_calificacion(resultado, db)


def eliminar_lugar(db: Session, id_lugar: int) -> dict:
    """
    Elimina un lugar turístico del sistema (solo admin).
    
    Args:
        db: Sesión de base de datos
        id_lugar: ID del lugar a eliminar
    
    Returns:
        Diccionario con mensaje de confirmación
    
    Raises:
        HTTPException 404 si el lugar no existe
    """
    lugar = db.query(Lugar).filter(Lugar.id_lugar == id_lugar).first()
    if not lugar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lugar no encontrado"
        )

    db.delete(lugar)
    db.commit()
    return {"message": f"Lugar '{lugar.nombre}' eliminado exitosamente"}


def buscar_lugares_cercanos(
    db: Session,
    latitud: float,
    longitud: float,
    radio_km: float = 2.0,
    aprobados_only: bool = True
) -> List[dict]:
    """
    Busca lugares cercanos usando PostGIS ST_DWithin y ST_Distance.
    
    Usa ST_DWithin para filtrar eficientemente por distancia
    (aprovecha índices espaciales) y ST_Distance para calcular
    la distancia exacta en metros.
    
    El radio se convierte de kilómetros a metros para ST_DWithin.
    Se usa Geography para obtener distancias en metros reales
    (no grados como con Geometry puro).
    
    Args:
        db: Sesión de base de datos
        latitud: Latitud del punto de referencia
        longitud: Longitud del punto de referencia
        radio_km: Radio de búsqueda en kilómetros (default: 2.0)
    
    Returns:
        Lista de lugares con distancia en metros, ordenados por cercanía
    """
    from geoalchemy2 import Geography
    from sqlalchemy import cast

    # Construir el punto de referencia del usuario
    punto_usuario = from_shape(Point(longitud, latitud), srid=4326)
    radio_metros = radio_km * 1000  # Convertir km a metros

    # Consulta con ST_DWithin (filtro eficiente con índice espacial)
    # y ST_Distance (cálculo de distancia exacta en metros)
    query = db.query(
        Lugar,
        func.ST_Distance(
            cast(Lugar.ubicacion, Geography),
            cast(func.ST_SetSRID(func.ST_MakePoint(longitud, latitud), 4326), Geography)
        ).label("distancia_metros")
    )

    if aprobados_only:
        query = query.filter(Lugar.aprobado == True)

    lugares = query.filter(
        func.ST_DWithin(
            cast(Lugar.ubicacion, Geography),
            cast(func.ST_SetSRID(func.ST_MakePoint(longitud, latitud), 4326), Geography),
            radio_metros
        )
    ).order_by("distancia_metros").all()

    resultados = []
    for lugar, distancia in lugares:
        lugar_dict = {
            "id_lugar": lugar.id_lugar,
            "nombre": lugar.nombre,
            "descripcion": lugar.descripcion,
            "latitud": lugar.latitud,
            "longitud": lugar.longitud,
            "direccion": lugar.direccion,
            "categoria": lugar.categoria,
            "aprobado": lugar.aprobado,
            "distancia_metros": round(distancia, 2),
            "foto_principal": lugar.foto_principal,
            "fotos": lugar.fotos.split(",") if lugar.fotos else []
        }
        agregar_calificacion(lugar_dict, db)
        resultados.append(lugar_dict)

    return resultados
