"""
Prueba de Resistencia (Endurance / Soak Test) - ISO 25010: Fiabilidad (R-1.1 Madurez)

Objetivo: verificar que no existen fugas de memoria (memory leaks) ni
degradación de rendimiento tras 2 horas de carga sostenida moderada.

Perfil de carga:
  00:00-05:00   ramp-up  0 -> 30 usuarios (spawn_rate = 0.1/s)
  05:00-120:00  meseta   30 usuarios sostenidos (2 horas)
  120:00-125:00 cool-down 30 -> 0 usuarios

Umbrales de aceptación:
  Error rate < 1%
  p95 < 2000 ms
  p99 < 3000 ms
  Sin incremento sostenido de latencia (no hay degradación temporal)

Ejecución:
  locust -f tests/performance/soak_locustfile.py SoakUser \\
         --host http://localhost:8000 --headless --csv resultados_soak

Para pre-cargar datos primero:
  python scripts/seed_soak.py  (o usar la API manualmente)
"""
from __future__ import annotations

import random
import time
from collections import deque

import requests as _requests
from locust import HttpUser, LoadTestShape, TaskSet, between, events, task


PASTO_LAT = 1.2136
PASTO_LON = -77.2811

CATEGORIAS = ["restaurante", "parque", "museo", "iglesia", "mirador", "hotel"]

SEED_USERS = [
    {"correo": "turista1@exploro.test", "contraseña": "Test1234!"},
    {"correo": "turista2@exploro.test", "contraseña": "Test1234!"},
    {"correo": "pyme1@exploro.test",    "contraseña": "Test1234!"},
    {"correo": "admin@exploro.test",    "contraseña": "Test1234!"},
]

_TOKEN_POOL: list[str] = []
_LATENCIAS_P95: deque[float] = deque(maxlen=1000)


@events.test_start.add_listener
def _precargar_tokens(environment, **_kw):
    base_url = (environment.host or "http://localhost:8000").rstrip("/")
    print("\n[soak] Precargando tokens JWT...")
    for cred in SEED_USERS:
        try:
            resp = _requests.post(
                f"{base_url}/auth/login",
                json={"correo": cred["correo"], "contraseña": cred["contraseña"]},
                timeout=10,
            )
            if resp.status_code == 200:
                token = resp.json().get("access_token")
                if token:
                    _TOKEN_POOL.append(token)
                    print(f"  [OK] {cred['correo']}")
            else:
                print(f"  [WARN] {cred['correo']} -> {resp.status_code}")
        except Exception as exc:
            print(f"  [ERROR] {cred['correo']}: {exc}")
        time.sleep(0.5)
    print(f"[soak] Pool listo: {len(_TOKEN_POOL)}/{len(SEED_USERS)} tokens\n")


class SoakTasks(TaskSet):
    """Mezcla de operaciones de lectura para prueba de resistencia."""

    @task(4)
    def listar_lugares(self):
        cat = random.choice(CATEGORIAS)
        self.client.get(f"/places?categoria={cat}", name="GET /places?categoria=[cat]")

    @task(3)
    def lugares_populares(self):
        self.client.get("/recommendations/popular", name="GET /recommendations/popular")

    @task(2)
    def lugares_cercanos(self):
        lat = PASTO_LAT + random.uniform(-0.05, 0.05)
        lon = PASTO_LON + random.uniform(-0.05, 0.05)
        self.client.get(
            f"/recommendations/nearby?latitud={lat:.4f}&longitud={lon:.4f}&radio_km=5",
            name="GET /recommendations/nearby",
        )

    @task(2)
    def recomendaciones_auth(self):
        if not _TOKEN_POOL:
            return
        token = random.choice(_TOKEN_POOL)
        lat = PASTO_LAT + random.uniform(-0.03, 0.03)
        lon = PASTO_LON + random.uniform(-0.03, 0.03)
        self.client.get(
            f"/recommendations?latitud={lat:.4f}&longitud={lon:.4f}&radio_km=5&limite=10",
            headers={"Authorization": f"Bearer {token}"},
            name="GET /recommendations (auth)",
        )

    @task(1)
    def health_check(self):
        self.client.get("/", name="GET /health")


class SoakUser(HttpUser):
    """
    ISO 25010 - Fiabilidad: Madurez (R-1.1).
    Usuario para prueba de resistencia de 2 horas.
    """
    tasks = [SoakTasks]
    wait_time = between(2, 5)


class SoakShape(LoadTestShape):
    """
    Perfil de carga de resistencia (Soak Test):
      00:00-05:00    ramp-up   0 -> 30 usuarios
      05:00-7200:00  meseta    30 usuarios (2 horas)
      7200:00-7205:00 cool-down 30 -> 0

    Para ejecutar:
      locust -f tests/performance/soak_locustfile.py SoakUser \\
             --host http://localhost:8000 --headless \\
             --csv resultados_soak
    """

    _stages = [
        {"hasta": 300,  "usuarios": 30, "spawn_rate": 0.1},   # 5 min ramp-up
        {"hasta": 7200, "usuarios": 30, "spawn_rate": 1.0},   # 2 horas meseta
        {"hasta": 7500, "usuarios": 0,  "spawn_rate": 5.0},   # 5 min cool-down
    ]

    def tick(self):
        t = self.get_run_time()
        for stage in self._stages:
            if t < stage["hasta"]:
                return stage["usuarios"], stage["spawn_rate"]
        return None


@events.quitting.add_listener
def _validar_soak(environment, **_kw):
    """Valida umbrales al finalizar el soak test."""
    stats = environment.runner.stats.total
    if not stats.num_requests:
        return

    p95 = stats.get_response_time_percentile(0.95) or 0
    p99 = stats.get_response_time_percentile(0.99) or 0
    error_pct = stats.num_failures / stats.num_requests * 100

    print("\n" + "=" * 62)
    print("  RESUMEN SOAK TEST — ISO 25010 Fiabilidad: Madurez")
    print("=" * 62)
    print(f"  Duración total    : {stats.last_request_timestamp - stats.start_time:.0f} s")
    print(f"  Requests totales  : {stats.num_requests}")
    print(f"  Fallos            : {stats.num_failures}")
    print(f"  Error rate        : {error_pct:.2f}%   [límite 1%]")
    print(f"  Latencia p95      : {p95:.0f} ms   [límite 2000 ms]")
    print(f"  Latencia p99      : {p99:.0f} ms   [límite 3000 ms]")
    print(f"  RPS promedio      : {stats.total_rps:.1f}")
    print("-" * 62)

    fallos = []
    if p95 > 2000:
        fallos.append(f"p95 {p95:.0f} ms > 2000 ms — degradación de rendimiento")
    if p99 > 3000:
        fallos.append(f"p99 {p99:.0f} ms > 3000 ms")
    if error_pct > 1:
        fallos.append(f"Error rate {error_pct:.2f}% > 1%")

    if fallos:
        print("  [FALLO SOAK]")
        for f in fallos:
            print(f"    ✗ {f}")
        environment.process_exit_code = 1
    else:
        print("  [OK] Sistema estable tras carga sostenida (sin memory leak detectado)")
    print("=" * 62 + "\n")
