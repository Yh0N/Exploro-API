"""
Servicio de recomendaciones de EXPLORO - Fase 1.
Genera recomendaciones personalizadas de lugares turísticos basadas en:
1. Preferencias del usuario (categorías de interés almacenadas como ARRAY)
2. Calificación promedio (calculada dinámicamente con AVG())
3. Proximidad geoespacial (usando PostGIS ST_DWithin y ST_Distance)
4. Exclusión de lugares ya reseñados por el usuario

Los servicios de Fase 2 (collaborative_filter, linear_regression,
sentiment_analysis) están preparados como archivos separados.
"""

from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from geoalchemy2 import Geography
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import cast

from app.models.place import Lugar
from app.models.review import Reseña
from app.models.user import Usuario


def obtener_recomendaciones_personalizadas(
    db: Session,
    usuario: Usuario,
    latitud: Optional[float] = None,
    longitud: Optional[float] = None,
    radio_km: float = 5.0,
    limite: int = 10
) -> List[dict]:
    """
    Genera recomendaciones personalizadas para el usuario autenticado.
    
    Algoritmo Fase 1:
    1. Obtiene las preferencias del usuario (ARRAY de categorías)
    2. Busca lugares cuya categoría coincida con alguna preferencia
    3. Excluye lugares que el usuario ya reseñó
    4. Si se proporcionan coordenadas, filtra por distancia con PostGIS
    5. Ordena por calificación promedio descendente
    
    Args:
        db: Sesión de base de datos
        usuario: Usuario autenticado
        latitud: Latitud del usuario (opcional, para filtro geoespacial)
        longitud: Longitud del usuario (opcional)
        radio_km: Radio de búsqueda en km (default: 5.0)
        limite: Número máximo de recomendaciones (default: 10)
    
    Returns:
        Lista de lugares recomendados con calificación y distancia
    """
    # Paso 1: Obtener preferencias del usuario
    preferencias = usuario.preferencias if usuario.preferencias else []

    # Paso 2: Query base - lugares aprobados
    query = db.query(Lugar).filter(Lugar.aprobado == True)

    # Filtrar por preferencias si el usuario tiene alguna
    if preferencias:
        query = query.filter(Lugar.categoria.in_(preferencias))

    # Paso 3: Excluir lugares que el usuario ya reseñó
    subquery_reseñados = db.query(Reseña.id_lugar).filter(
        Reseña.id_usuario == usuario.id_usuario
    ).subquery()
    query = query.filter(~Lugar.id_lugar.in_(subquery_reseñados))

    # Paso 4: Filtrar por distancia si se proporcionan coordenadas
    if latitud is not None and longitud is not None:
        radio_metros = radio_km * 1000
        query = query.filter(
            func.ST_DWithin(
                cast(Lugar.ubicacion, Geography),
                cast(func.ST_SetSRID(func.ST_MakePoint(longitud, latitud), 4326), Geography),
                radio_metros
            )
        )

    lugares = query.all()

    # Paso 5: Calcular calificación promedio y distancia para cada lugar
    resultados = []
    for lugar in lugares:
        # Calcular calificación promedio dinámicamente
        avg = db.query(func.avg(Reseña.puntuacion)).filter(
            Reseña.id_lugar == lugar.id_lugar
        ).scalar()
        calificacion = round(float(avg), 2) if avg else 0.0

        lugar_dict = {
            "id_lugar": lugar.id_lugar,
            "nombre": lugar.nombre,
            "descripcion": lugar.descripcion,
            "latitud": lugar.latitud,
            "longitud": lugar.longitud,
            "categoria": lugar.categoria,
            "calificacion_promedio": calificacion
        }

        # Agregar distancia si se proporcionaron coordenadas
        if latitud is not None and longitud is not None:
            distancia = db.query(
                func.ST_Distance(
                    cast(Lugar.ubicacion, Geography),
                    cast(func.ST_SetSRID(func.ST_MakePoint(longitud, latitud), 4326), Geography)
                )
            ).filter(Lugar.id_lugar == lugar.id_lugar).scalar()
            lugar_dict["distancia_metros"] = round(float(distancia), 2) if distancia else None

        resultados.append(lugar_dict)

    # Ordenar por calificación promedio descendente
    resultados.sort(key=lambda x: x["calificacion_promedio"], reverse=True)

    return resultados[:limite]


def obtener_lugares_populares(db: Session, limite: int = 10) -> List[dict]:
    """
    Obtiene los lugares más populares basados en su calificación promedio.
    Solo incluye lugares aprobados que tengan al menos una reseña.
    
    Args:
        db: Sesión de base de datos
        limite: Número máximo de resultados (default: 10)
    
    Returns:
        Lista de lugares ordenados por calificación promedio descendente
    """
    # Subconsulta para obtener la calificación promedio de cada lugar
    resultados = db.query(
        Lugar,
        func.avg(Reseña.puntuacion).label("calificacion_promedio"),
        func.count(Reseña.id_resena).label("total_resenas")
    ).join(
        Reseña, Lugar.id_lugar == Reseña.id_lugar
    ).filter(
        Lugar.aprobado == True
    ).group_by(
        Lugar.id_lugar
    ).order_by(
        func.avg(Reseña.puntuacion).desc()
    ).limit(limite).all()

    return [
        {
            "id_lugar": lugar.id_lugar,
            "nombre": lugar.nombre,
            "descripcion": lugar.descripcion,
            "latitud": lugar.latitud,
            "longitud": lugar.longitud,
            "categoria": lugar.categoria,
            "calificacion_promedio": round(float(avg), 2) if avg else None,
            "total_resenas": total
        }
        for lugar, avg, total in resultados
    ]


def obtener_recomendaciones_cercanas(
    db: Session,
    latitud: float,
    longitud: float,
    radio_km: float = 2.0,
    limite: int = 10
) -> List[dict]:
    """
    Recomienda lugares cercanos a una ubicación dada.
    Usa PostGIS para cálculos de distancia eficientes.
    
    A diferencia de buscar_lugares_cercanos en place_service,
    este endpoint ordena por calificación promedio además de distancia.
    
    Args:
        db: Sesión de base de datos
        latitud: Latitud del punto de referencia
        longitud: Longitud del punto de referencia
        radio_km: Radio de búsqueda en km (default: 2.0)
        limite: Número máximo de resultados (default: 10)
    
    Returns:
        Lista de lugares cercanos con distancia y calificación
    """
    radio_metros = radio_km * 1000

    # Buscar lugares dentro del radio con calificación promedio
    lugares = db.query(
        Lugar,
        func.ST_Distance(
            cast(Lugar.ubicacion, Geography),
            cast(func.ST_SetSRID(func.ST_MakePoint(longitud, latitud), 4326), Geography)
        ).label("distancia_metros")
    ).filter(
        Lugar.aprobado == True,
        func.ST_DWithin(
            cast(Lugar.ubicacion, Geography),
            cast(func.ST_SetSRID(func.ST_MakePoint(longitud, latitud), 4326), Geography),
            radio_metros
        )
    ).order_by("distancia_metros").limit(limite).all()

    resultados = []
    for lugar, distancia in lugares:
        avg = db.query(func.avg(Reseña.puntuacion)).filter(
            Reseña.id_lugar == lugar.id_lugar
        ).scalar()

        resultados.append({
            "id_lugar": lugar.id_lugar,
            "nombre": lugar.nombre,
            "descripcion": lugar.descripcion,
            "latitud": lugar.latitud,
            "longitud": lugar.longitud,
            "categoria": lugar.categoria,
            "calificacion_promedio": round(float(avg), 2) if avg else None,
            "distancia_metros": round(float(distancia), 2) if distancia else None
        })

    return resultados
