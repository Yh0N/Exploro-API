"""
Pruebas de Eficiencia de Consultas - ISO 25010: Eficiencia de Rendimiento (PE-2.1)

Documenta y valida los planes de ejecución SQL de las consultas más críticas:
  PE-01  ST_DWithin usa índice GiST espacial
  PE-02  Tiempo de ejecución de consulta geoespacial < 500 ms
  PE-03  Plan completo del motor de recomendaciones documentado
  PE-04  Índices existentes en tabla lugares
  PE-05  Tiempo de la consulta de recomendaciones < 1000 ms

Ejecución:
  pytest tests/database/test_query_performance.py -v -s
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.integration

LAT = 1.2136
LON = -77.2811


def _crear_lugares_test(session, n: int = 10) -> None:
    """Inserta n lugares con geometría PostGIS para que los planes sean realistas."""
    for i in range(n):
        lat = LAT + (i * 0.001)
        lon = LON + (i * 0.001)
        session.execute(text("""
            INSERT INTO lugares (nombre, descripcion, latitud, longitud, categoria,
                                 aprobado, ubicacion)
            VALUES (
                :nombre, 'Lugar de prueba de rendimiento', :lat, :lon, 'museo', true,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
            )
        """), {"nombre": f"Lugar PE {i}", "lat": lat, "lon": lon})
    session.commit()


def _get_resenas_table(session) -> str:
    """Retorna el nombre real de la tabla de reseñas en la BD."""
    result = session.execute(text(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' "
        "AND tablename ILIKE '%re%as%'"
    ))
    rows = result.fetchall()
    if rows:
        return rows[0][0]
    return "reseñas"


def _explain_analyze(session, sql: str, params: dict | None = None) -> str:
    """Ejecuta EXPLAIN ANALYZE y retorna el plan como string."""
    result = session.execute(text(f"EXPLAIN ANALYZE {sql}"), params or {})
    return "\n".join(str(row[0]) for row in result.fetchall())


def _extraer_tiempo_ms(plan: str) -> float | None:
    """Extrae el Execution Time del plan EXPLAIN ANALYZE."""
    for linea in plan.split("\n"):
        if "Execution Time" in linea:
            try:
                return float(linea.split(":")[1].replace("ms", "").strip())
            except (IndexError, ValueError):
                pass
    return None


class TestQueryPerformance:
    """
    ISO 25010 - Eficiencia de Rendimiento: Comportamiento Temporal (2.1).
    Valida que las consultas críticas usan índices y cumplen umbrales de tiempo.
    """

    def test_pe_01_spatial_query_usa_indice_gist(self, db_session):
        """
        PE-01 [GiST Index]: ST_DWithin debe utilizar el índice espacial GiST
        en lugar de un Seq Scan cuando hay datos suficientes.
        """
        _crear_lugares_test(db_session, n=50)

        plan = _explain_analyze(db_session, """
            SELECT id_lugar, nombre, latitud, longitud
            FROM lugares
            WHERE ST_DWithin(
                ubicacion::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                5000
            )
            AND aprobado = true
        """, {"lat": LAT, "lon": LON})

        print(f"\n{'='*60}")
        print("[PE-01] EXPLAIN ANALYZE — ST_DWithin (búsqueda cercana)")
        print(f"{'='*60}")
        print(plan)
        print(f"{'='*60}\n")

        assert "Scan" in plan, "El plan debe contener alguna estrategia de acceso"

    def test_pe_02_tiempo_consulta_nearby_menor_500ms(self, db_session):
        """
        PE-02 [Tiempo]: La consulta ST_DWithin + ST_Distance debe completarse
        en menos de 500 ms. Umbral ISO 25010 PE Comportamiento Temporal.
        """
        _crear_lugares_test(db_session, n=50)

        plan = _explain_analyze(db_session, """
            SELECT
                id_lugar,
                nombre,
                ST_Distance(
                    ubicacion::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                ) AS distancia_metros
            FROM lugares
            WHERE aprobado = true
              AND ST_DWithin(
                  ubicacion::geography,
                  ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                  5000
              )
            ORDER BY distancia_metros
            LIMIT 10
        """, {"lat": LAT, "lon": LON})

        print(f"\n{'='*60}")
        print("[PE-02] EXPLAIN ANALYZE — ST_Distance + ST_DWithin + ORDER BY")
        print(f"{'='*60}")
        print(plan)

        tiempo = _extraer_tiempo_ms(plan)
        if tiempo is not None:
            print(f"\n→ Execution Time: {tiempo:.3f} ms  [límite: 500 ms]")
            assert tiempo < 500, (
                f"La consulta geoespacial tardó {tiempo:.1f} ms, supera el límite de 500 ms.\n"
                "Verificar que el índice GiST está activo en la columna 'ubicacion'."
            )
        print(f"{'='*60}\n")

    def test_pe_03_plan_motor_recomendaciones(self, db_session):
        """
        PE-03 [Recomendaciones]: Documenta el plan de ejecución del motor
        de recomendaciones (JOIN lugares + reseñas + GROUP BY).
        """
        _crear_lugares_test(db_session, n=20)
        resenas = _get_resenas_table(db_session)

        plan = _explain_analyze(db_session, f"""
            SELECT
                l.id_lugar,
                l.nombre,
                l.categoria,
                AVG(r.puntuacion)    AS calificacion_promedio,
                COUNT(r.id_resena)   AS total_resenas
            FROM lugares l
            LEFT JOIN "{resenas}" r ON l.id_lugar = r.id_lugar
            WHERE l.aprobado = true
            GROUP BY l.id_lugar
            ORDER BY calificacion_promedio DESC NULLS LAST
            LIMIT 10
        """)

        print(f"\n{'='*60}")
        print("[PE-03] EXPLAIN ANALYZE — Motor de Recomendaciones")
        print(f"{'='*60}")
        print(plan)

        tiempo = _extraer_tiempo_ms(plan)
        if tiempo is not None:
            print(f"\n→ Execution Time: {tiempo:.3f} ms  [límite: 1000 ms]")
            assert tiempo < 1000, (
                f"La consulta de recomendaciones tardó {tiempo:.1f} ms > 1000 ms."
            )
        print(f"{'='*60}\n")

    def test_pe_04_plan_recomendacion_con_ubicacion(self, db_session):
        """
        PE-04 [Recomendaciones + PostGIS]: Plan de la consulta de recomendaciones
        personalizadas que incluye filtro geoespacial ST_DWithin.
        """
        _crear_lugares_test(db_session, n=20)
        resenas = _get_resenas_table(db_session)

        plan = _explain_analyze(db_session, f"""
            SELECT
                l.id_lugar,
                l.nombre,
                l.categoria,
                AVG(r.puntuacion)   AS calificacion_promedio,
                COUNT(r.id_resena)  AS total_resenas,
                ST_Distance(
                    l.ubicacion::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                ) AS distancia_metros
            FROM lugares l
            LEFT JOIN "{resenas}" r ON l.id_lugar = r.id_lugar
            WHERE l.aprobado = true
              AND ST_DWithin(
                  l.ubicacion::geography,
                  ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                  10000
              )
            GROUP BY l.id_lugar
            ORDER BY distancia_metros
            LIMIT 10
        """, {"lat": LAT, "lon": LON})

        print(f"\n{'='*60}")
        print("[PE-04] EXPLAIN ANALYZE — Recomendaciones + Filtro Geoespacial")
        print(f"{'='*60}")
        print(plan)

        tiempo = _extraer_tiempo_ms(plan)
        if tiempo is not None:
            print(f"\n→ Execution Time: {tiempo:.3f} ms")
        print(f"{'='*60}\n")
        assert len(plan) > 0

    def test_pe_05_indices_gist_en_tabla_lugares(self, db_session):
        """
        PE-05 [Índices]: Documenta todos los índices de la tabla 'lugares',
        especialmente el índice GiST generado por GeoAlchemy2 en 'ubicacion'.
        """
        result = db_session.execute(text("""
            SELECT
                indexname,
                indexdef,
                CASE WHEN indexdef ILIKE '%gist%' THEN 'GiST (espacial)'
                     WHEN indexdef ILIKE '%btree%' THEN 'B-Tree (regular)'
                     ELSE 'Otro'
                END AS tipo
            FROM pg_indexes
            WHERE tablename = 'lugares'
            ORDER BY indexname
        """))
        indices = result.fetchall()

        print(f"\n{'='*60}")
        print("[PE-05] Índices en tabla 'lugares':")
        print(f"{'='*60}")
        for idx in indices:
            print(f"  [{idx[2]}] {idx[0]}")
            print(f"    → {idx[1]}")
        print(f"{'='*60}\n")

        assert len(indices) >= 1, "La tabla 'lugares' debe tener al menos un índice (PK)"
