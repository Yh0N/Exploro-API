"""
Pruebas de Concurrencia en BD (Pool de Conexiones) - ISO 25010

  ISO 25010 - Eficiencia de Rendimiento: Capacidad (PE-2.3)
  ISO 25010 - Fiabilidad: Disponibilidad (R-1.2)

Verifica que el pool de conexiones SQLAlchemy soporta carga concurrente
sin agotar las conexiones ni generar errores 503/500.

  POOL-01  20 peticiones concurrentes sin error de pool
  POOL-02  30 peticiones mixtas sin errores 503
  POOL-03  50 peticiones secuenciales sin fuga de conexiones
  POOL-04  Configuración max_connections de PostgreSQL documentada
  POOL-05  Pool bajo carga sostenida (100 peticiones en ráfaga)

Ejecución:
  pytest tests/database/test_connection_pool.py -v -s
"""
from __future__ import annotations

import concurrent.futures
import threading

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.integration


class TestConnectionPool:
    """
    ISO 25010 - Eficiencia de Rendimiento (Capacidad) + Fiabilidad (Disponibilidad).
    Verifica que el pool de conexiones de SQLAlchemy gestiona correctamente
    la concurrencia sin agotar recursos de base de datos.
    """

    def test_pool_01_20_concurrentes_sin_error(self, client):
        """
        POOL-01 [Concurrencia básica]: 20 peticiones concurrentes a GET /places
        deben retornar 200 sin errores de conexión (Too many connections, 503, 500).
        """
        resultados: list[int] = []
        lock = threading.Lock()

        def hacer_peticion(_):
            r = client.get("/places")
            with lock:
                resultados.append(r.status_code)

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            list(executor.map(hacer_peticion, range(20)))

        errores = [c for c in resultados if c not in (200, 429)]
        print(f"\n[POOL-01] 20 concurrentes — códigos: {sorted(set(resultados))}")
        print(f"  Exitosas (200): {resultados.count(200)} / 20")

        assert len(errores) == 0, (
            f"Se obtuvieron {len(errores)} respuestas inesperadas: {errores}\n"
            "Posible agotamiento del connection pool de SQLAlchemy."
        )

    def test_pool_02_30_concurrentes_endpoints_mixtos(self, client):
        """
        POOL-02 [Endpoints mixtos]: 30 peticiones concurrentes a distintos endpoints
        públicos no deben generar errores 503 Service Unavailable.
        """
        endpoints = [
            "/places",
            "/places?categoria=museo",
            "/recommendations/popular",
            "/pymes",
            "/",
        ]
        resultados: list[tuple[str, int]] = []
        lock = threading.Lock()

        def hacer_peticion(i: int):
            endpoint = endpoints[i % len(endpoints)]
            r = client.get(endpoint)
            with lock:
                resultados.append((endpoint, r.status_code))

        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            list(executor.map(hacer_peticion, range(30)))

        errores_503 = [(ep, c) for ep, c in resultados if c == 503]
        codigos = sorted({c for _, c in resultados})
        print(f"\n[POOL-02] 30 mixtas — códigos únicos: {codigos}")
        print(f"  Errores 503: {len(errores_503)}")

        assert len(errores_503) == 0, (
            f"Se obtuvieron {len(errores_503)} errores 503.\n"
            "El pool de conexiones está agotado o el servidor rechaza peticiones."
        )

    def test_pool_03_50_secuenciales_sin_leak(self, client):
        """
        POOL-03 [Sin fuga]: 50 peticiones secuenciales verifican que las conexiones
        se devuelven al pool tras cada petición (sin connection leak).
        """
        fallos = 0
        for i in range(50):
            r = client.get("/recommendations/popular")
            if r.status_code not in (200, 429):
                fallos += 1

        print(f"\n[POOL-03] 50 secuenciales — fallos: {fallos}/50")
        assert fallos == 0, (
            f"{fallos}/50 peticiones fallaron.\n"
            "Posible fuga de conexiones: las conexiones no se devuelven al pool."
        )

    def test_pool_04_configuracion_postgresql_documentada(self, db_session):
        """
        POOL-04 [Config]: Documenta la configuración de conexiones de PostgreSQL.
        Verifica que max_connections sea suficiente para carga concurrente.
        """
        result = db_session.execute(text("""
            SELECT name, setting, unit, short_desc
            FROM pg_settings
            WHERE name IN (
                'max_connections',
                'superuser_reserved_connections',
                'work_mem',
                'shared_buffers'
            )
            ORDER BY name
        """))
        config = result.fetchall()

        print(f"\n{'='*60}")
        print("[POOL-04] Configuración PostgreSQL Connection Pool:")
        print(f"{'='*60}")
        for row in config:
            print(f"  {row[0]:40s} = {row[1]} {row[2] or ''}")
            print(f"    → {row[3]}")
        print(f"{'='*60}\n")

        max_conn = next((int(r[1]) for r in config if r[0] == "max_connections"), 0)
        assert max_conn >= 10, (
            f"max_connections={max_conn} es muy bajo. "
            "Se necesitan al menos 10 para carga básica concurrente."
        )

    def test_pool_05_100_rafaga_sin_degradacion(self, client):
        """
        POOL-05 [Ráfaga]: 100 peticiones concurrentes en ráfaga (max_workers=50)
        no deben producir más de 5% de errores no esperados.
        ISO 25010 — Eficiencia de Rendimiento: Capacidad.
        """
        resultados: list[int] = []
        lock = threading.Lock()

        def hacer_peticion(i: int):
            endpoint = "/places" if i % 2 == 0 else "/recommendations/popular"
            r = client.get(endpoint)
            with lock:
                resultados.append(r.status_code)

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            list(executor.map(hacer_peticion, range(100)))

        errores = [c for c in resultados if c not in (200, 429)]
        tasa_error = len(errores) / len(resultados) * 100

        print(f"\n[POOL-05] 100 en ráfaga (50 workers):")
        print(f"  Códigos únicos: {sorted(set(resultados))}")
        print(f"  Tasa de error: {tasa_error:.1f}%  [límite: 5%]")

        assert tasa_error <= 5, (
            f"Tasa de error {tasa_error:.1f}% > 5% bajo ráfaga de 100 peticiones.\n"
            "El sistema no cumple ISO 25010 Capacidad bajo carga alta."
        )
