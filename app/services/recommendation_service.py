"""
Servicio de recomendaciones de EXPLORO.

La estrategia actual usa un enfoque hibrido y explicable que mezcla:
1. Preferencias declaradas del usuario
2. Interacciones historicas del usuario a partir de sus resenas
3. Popularidad del lugar (rating promedio + volumen de resenas)
4. Cercania geografica cuando el cliente envia coordenadas
5. Novedad, evitando priorizar lugares ya recomendados repetidamente

No depende de modelos avanzados de ML, por lo que sigue alineado con el
alcance de la primera version descrita en el documento del proyecto.
"""

from __future__ import annotations

from math import sqrt
from typing import Dict, List, Optional, Sequence

from geoalchemy2 import Geography
from sqlalchemy import cast, func
from sqlalchemy.orm import Session

from app.models.place import Lugar
from app.models.recommendation import Recomendacion
from app.models.review import Reseña
from app.models.user import Usuario


POPULARIDAD_BASE = 3.5


def _normalizar(valor: float, minimo: float, maximo: float) -> float:
    """Normaliza un valor al rango 0..1 evitando divisiones por cero."""
    if maximo <= minimo:
        return 0.0
    return max(0.0, min(1.0, (valor - minimo) / (maximo - minimo)))


def _score_distancia(distancia_metros: Optional[float], radio_metros: Optional[float]) -> float:
    """Da mayor puntaje a los lugares mas cercanos dentro del radio."""
    if distancia_metros is None or not radio_metros or radio_metros <= 0:
        return 0.0
    return max(0.0, 1 - (distancia_metros / radio_metros))


def _score_preferencia(categoria: str, preferencias: Sequence[str]) -> float:
    """Premia coincidencias con intereses declarados."""
    return 1.0 if categoria in preferencias else 0.0


def _score_afinidad_categoria(categoria: str, afinidad_por_categoria: Dict[str, float]) -> float:
    """Usa el historial de resenas del usuario para reforzar categorias afines."""
    return max(0.0, min(1.0, afinidad_por_categoria.get(categoria, 0.0)))


def _score_popularidad(
    calificacion_promedio: Optional[float],
    total_resenas: int,
    max_resenas: int,
) -> float:
    """
    Combina rating y volumen con una aproximacion bayesiana sencilla.

    Esto evita que un lugar con una sola resena de 5.0 opaque a otro
    con muchas resenas y calificacion estable.
    """
    rating = calificacion_promedio if calificacion_promedio is not None else POPULARIDAD_BASE
    peso_resenas = total_resenas / (total_resenas + 5)
    rating_ajustado = (peso_resenas * rating) + ((1 - peso_resenas) * POPULARIDAD_BASE)
    score_rating = max(0.0, min(1.0, rating_ajustado / 5))
    score_volumen = _normalizar(float(total_resenas), 0.0, float(max_resenas or 1))
    return round((score_rating * 0.75) + (score_volumen * 0.25), 4)


def _score_novedad(veces_recomendado: int) -> float:
    """Da prioridad a lugares menos repetidos en el historial de sugerencias."""
    return max(0.0, 1 - min(veces_recomendado, 5) / 5)


def _construir_razones(
    categoria: str,
    preferencias: Sequence[str],
    afinidad_categoria: float,
    distancia_metros: Optional[float],
    total_resenas: int,
    calificacion_promedio: Optional[float],
) -> List[str]:
    """Genera razones cortas para explicar la recomendacion al cliente."""
    razones: List[str] = []

    if categoria in preferencias:
        razones.append(f"Coincide con tu preferencia por {categoria}")

    if afinidad_categoria >= 0.75:
        razones.append(f"Sueles calificar bien la categoria {categoria}")

    if distancia_metros is not None:
        razones.append(f"Esta cerca de tu ubicacion ({round(distancia_metros)} m)")

    if calificacion_promedio is not None and calificacion_promedio >= 4.0:
        razones.append(f"Tiene buena valoracion ({round(calificacion_promedio, 2)}/5)")

    if total_resenas >= 3:
        razones.append(f"Cuenta con {total_resenas} resenas")

    if not razones:
        razones.append("Es una opcion relevante dentro de la oferta disponible")

    return razones


def _persistir_recomendaciones(
    db: Session,
    usuario: Usuario,
    recomendaciones: Sequence[dict],
) -> None:
    """Guarda un rastro simple de las recomendaciones generadas."""
    ids_lugares = [item["id_lugar"] for item in recomendaciones]
    if not ids_lugares:
        return

    existentes = {
        fila[0]
        for fila in db.query(Recomendacion.id_lugar).filter(
            Recomendacion.id_usuario == usuario.id_usuario,
            Recomendacion.id_lugar.in_(ids_lugares),
        ).all()
    }

    nuevas = [
        Recomendacion(id_usuario=usuario.id_usuario, id_lugar=item["id_lugar"])
        for item in recomendaciones
        if item["id_lugar"] not in existentes
    ]

    if nuevas:
        db.add_all(nuevas)
        db.commit()


def _obtener_afinidad_por_categoria(db: Session, usuario: Usuario) -> Dict[str, float]:
    """
    Calcula afinidad por categoria a partir de las resenas del usuario.

    Una puntuacion alta sobre una categoria incrementa la probabilidad
    de recomendar lugares similares.
    """
    filas = db.query(
        Lugar.categoria,
        func.avg(Reseña.puntuacion).label("promedio_categoria"),
    ).join(
        Lugar, Lugar.id_lugar == Reseña.id_lugar
    ).filter(
        Reseña.id_usuario == usuario.id_usuario
    ).group_by(
        Lugar.categoria
    ).all()

    afinidad: Dict[str, float] = {}
    for categoria, promedio in filas:
        promedio_normalizado = max(0.0, min(1.0, (float(promedio) - 1) / 4))
        afinidad[categoria] = round(promedio_normalizado, 4)
    return afinidad


def obtener_recomendaciones_personalizadas(
    db: Session,
    usuario: Usuario,
    latitud: Optional[float] = None,
    longitud: Optional[float] = None,
    radio_km: float = 5.0,
    limite: int = 10,
) -> List[dict]:
    """
    Genera recomendaciones personalizadas para el usuario autenticado.

    La salida incluye:
    - score_recomendacion: valor compuesto 0..1
    - razones: explicacion legible del por que fue recomendado
    - factores: desglose de los componentes del score
    """
    preferencias = usuario.preferencias if usuario.preferencias else []
    afinidad_por_categoria = _obtener_afinidad_por_categoria(db, usuario)
    radio_metros = radio_km * 1000 if latitud is not None and longitud is not None else None

    subquery_reseñados = db.query(Reseña.id_lugar).filter(
        Reseña.id_usuario == usuario.id_usuario
    ).subquery()

    subquery_historial = db.query(
        Recomendacion.id_lugar,
        func.count(Recomendacion.id_recomendacion).label("veces_recomendado"),
    ).filter(
        Recomendacion.id_usuario == usuario.id_usuario
    ).group_by(
        Recomendacion.id_lugar
    ).subquery()

    distancia_expr = None
    if latitud is not None and longitud is not None:
        distancia_expr = func.ST_Distance(
            cast(Lugar.ubicacion, Geography),
            cast(func.ST_SetSRID(func.ST_MakePoint(longitud, latitud), 4326), Geography),
        )

    query = db.query(
        Lugar.id_lugar,
        Lugar.nombre,
        Lugar.descripcion,
        Lugar.latitud,
        Lugar.longitud,
        Lugar.categoria,
        func.avg(Reseña.puntuacion).label("calificacion_promedio"),
        func.count(Reseña.id_resena).label("total_resenas"),
        func.coalesce(subquery_historial.c.veces_recomendado, 0).label("veces_recomendado"),
    ).outerjoin(
        Reseña, Lugar.id_lugar == Reseña.id_lugar
    ).outerjoin(
        subquery_historial, Lugar.id_lugar == subquery_historial.c.id_lugar
    ).filter(
        Lugar.aprobado == True,
        ~Lugar.id_lugar.in_(subquery_reseñados),
    )

    if latitud is not None and longitud is not None and radio_metros is not None:
        query = query.filter(
            func.ST_DWithin(
                cast(Lugar.ubicacion, Geography),
                cast(func.ST_SetSRID(func.ST_MakePoint(longitud, latitud), 4326), Geography),
                radio_metros,
            )
        ).add_columns(distancia_expr.label("distancia_metros"))

    query = query.group_by(
        Lugar.id_lugar,
        subquery_historial.c.veces_recomendado,
    )

    filas = query.all()
    if not filas:
        return []

    max_resenas = max(int(fila.total_resenas or 0) for fila in filas)
    resultados: List[dict] = []

    for fila in filas:
        distancia_metros = float(getattr(fila, "distancia_metros", 0) or 0) if latitud is not None and longitud is not None else None
        calificacion_promedio = float(fila.calificacion_promedio) if fila.calificacion_promedio is not None else None
        total_resenas = int(fila.total_resenas or 0)
        veces_recomendado = int(fila.veces_recomendado or 0)

        score_preferencia = _score_preferencia(fila.categoria, preferencias)
        score_afinidad = _score_afinidad_categoria(fila.categoria, afinidad_por_categoria)
        score_popularidad = _score_popularidad(calificacion_promedio, total_resenas, max_resenas)
        score_distancia = _score_distancia(distancia_metros, radio_metros)
        score_novedad = _score_novedad(veces_recomendado)

        pesos = {
            "preferencia": 0.30 if preferencias else 0.0,
            "afinidad_historial": 0.25 if afinidad_por_categoria else 0.0,
            "popularidad": 0.30,
            "distancia": 0.10 if distancia_metros is not None else 0.0,
            "novedad": 0.05,
        }
        peso_total = sum(pesos.values()) or 1.0

        score_total = (
            (score_preferencia * pesos["preferencia"])
            + (score_afinidad * pesos["afinidad_historial"])
            + (score_popularidad * pesos["popularidad"])
            + (score_distancia * pesos["distancia"])
            + (score_novedad * pesos["novedad"])
        ) / peso_total

        resultados.append(
            {
                "id_lugar": fila.id_lugar,
                "nombre": fila.nombre,
                "descripcion": fila.descripcion,
                "latitud": fila.latitud,
                "longitud": fila.longitud,
                "categoria": fila.categoria,
                "calificacion_promedio": round(calificacion_promedio, 2) if calificacion_promedio is not None else None,
                "total_resenas": total_resenas,
                "distancia_metros": round(distancia_metros, 2) if distancia_metros is not None else None,
                "score_recomendacion": round(score_total, 4),
                "razones": _construir_razones(
                    fila.categoria,
                    preferencias,
                    score_afinidad,
                    distancia_metros,
                    total_resenas,
                    calificacion_promedio,
                ),
                "factores": {
                    "preferencia": round(score_preferencia, 4),
                    "afinidad_historial": round(score_afinidad, 4),
                    "popularidad": round(score_popularidad, 4),
                    "distancia": round(score_distancia, 4),
                    "novedad": round(score_novedad, 4),
                },
            }
        )

    resultados.sort(
        key=lambda item: (
            item["score_recomendacion"],
            item["calificacion_promedio"] or 0,
            -item["distancia_metros"] if item["distancia_metros"] is not None else 0,
        ),
        reverse=True,
    )

    recomendaciones = resultados[:limite]
    _persistir_recomendaciones(db, usuario, recomendaciones)
    return recomendaciones


def obtener_lugares_populares(db: Session, limite: int = 10) -> List[dict]:
    """
    Obtiene lugares populares con una mezcla de rating promedio y volumen.
    """
    resultados = db.query(
        Lugar,
        func.avg(Reseña.puntuacion).label("calificacion_promedio"),
        func.count(Reseña.id_resena).label("total_resenas"),
    ).outerjoin(
        Reseña, Lugar.id_lugar == Reseña.id_lugar
    ).filter(
        Lugar.aprobado == True
    ).group_by(
        Lugar.id_lugar
    ).all()

    if not resultados:
        return []

    max_resenas = max(int(total or 0) for _, _, total in resultados)
    lugares = []
    for lugar, avg, total in resultados:
        score_popularidad = _score_popularidad(float(avg), int(total or 0), max_resenas)
        lugares.append(
            {
                "id_lugar": lugar.id_lugar,
                "nombre": lugar.nombre,
                "descripcion": lugar.descripcion,
                "latitud": lugar.latitud,
                "longitud": lugar.longitud,
                "categoria": lugar.categoria,
                "calificacion_promedio": round(float(avg), 2) if avg is not None else None,
                "total_resenas": int(total or 0),
                "score_popularidad": round(score_popularidad, 4),
            }
        )

    lugares.sort(
        key=lambda item: (
            item["score_popularidad"],
            item["calificacion_promedio"] or 0,
            sqrt(item["total_resenas"]),
        ),
        reverse=True,
    )
    return lugares[:limite]


def obtener_recomendaciones_cercanas(
    db: Session,
    latitud: float,
    longitud: float,
    radio_km: float = 2.0,
    limite: int = 10,
) -> List[dict]:
    """
    Recomienda lugares cercanos ponderando cercania y calidad.
    """
    radio_metros = radio_km * 1000

    filas = db.query(
        Lugar,
        func.avg(Reseña.puntuacion).label("calificacion_promedio"),
        func.count(Reseña.id_resena).label("total_resenas"),
        func.ST_Distance(
            cast(Lugar.ubicacion, Geography),
            cast(func.ST_SetSRID(func.ST_MakePoint(longitud, latitud), 4326), Geography),
        ).label("distancia_metros"),
    ).outerjoin(
        Reseña, Lugar.id_lugar == Reseña.id_lugar
    ).filter(
        Lugar.aprobado == True,
        func.ST_DWithin(
            cast(Lugar.ubicacion, Geography),
            cast(func.ST_SetSRID(func.ST_MakePoint(longitud, latitud), 4326), Geography),
            radio_metros,
        ),
    ).group_by(
        Lugar.id_lugar
    ).all()

    if not filas:
        return []

    max_resenas = max(int(fila.total_resenas or 0) for fila in filas)
    resultados = []
    for fila in filas:
        lugar = fila[0]
        score_popularidad = _score_popularidad(
            float(fila.calificacion_promedio) if fila.calificacion_promedio is not None else None,
            int(fila.total_resenas or 0),
            max_resenas,
        )
        score_distancia = _score_distancia(float(fila.distancia_metros), radio_metros)
        score_total = round((score_distancia * 0.6) + (score_popularidad * 0.4), 4)

        resultados.append(
            {
                "id_lugar": lugar.id_lugar,
                "nombre": lugar.nombre,
                "descripcion": lugar.descripcion,
                "latitud": lugar.latitud,
                "longitud": lugar.longitud,
                "categoria": lugar.categoria,
                "calificacion_promedio": round(float(fila.calificacion_promedio), 2) if fila.calificacion_promedio is not None else None,
                "total_resenas": int(fila.total_resenas or 0),
                "distancia_metros": round(float(fila.distancia_metros), 2),
                "score_recomendacion": score_total,
            }
        )

    resultados.sort(
        key=lambda item: (
            item["score_recomendacion"],
            item["calificacion_promedio"] or 0,
            -item["distancia_metros"],
        ),
        reverse=True,
    )
    return resultados[:limite]
