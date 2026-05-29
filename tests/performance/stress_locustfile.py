"""
Prueba de Estrés (Stress Test) - ISO 25010: Eficiencia de Rendimiento (PE-2.3 Capacidad)

Objetivo: encontrar el punto de quiebre del sistema incrementando la carga
hasta que el error rate supere el 5% o la latencia p95 supere 3000 ms.

Perfil de carga (escalonado):
  00:00-01:00   50 usuarios  (ramp)
  01:00-02:00   100 usuarios (ramp)
  02:00-03:00   200 usuarios (ramp)
  03:00-04:00   300 usuarios (ramp)
  04:00-05:00   400 usuarios (ramp)
  05:00-06:00   500 usuarios (carga máxima)
  06:00-07:00   cool-down -> 0

Umbrales:
  Punto de quiebre = cuando error rate > 5% o p95 > 3000 ms
  Sistema aprueba = soporta ≥ 200 usuarios sin superar umbrales

Ejecución:
  locust -f tests/performance/stress_locustfile.py StressUser \\
         --host http://localhost:8000 --headless \\
         --csv resultados_stress
"""
from __future__ import annotations

import random
import time

import requests as _requests
from locust import HttpUser, LoadTestShape, TaskSet, between, events, task


PASTO_LAT = 1.2136
PASTO_LON = -77.2811
CATEGORIAS = ["restaurante", "parque", "museo", "iglesia", "mirador"]

SEED_USERS = [
    {"correo": "turista1@exploro.test", "contraseña": "Test1234!"},
    {"correo": "turista2@exploro.test", "contraseña": "Test1234!"},
    {"correo": "pyme1@exploro.test",    "contraseña": "Test1234!"},
    {"correo": "admin@exploro.test",    "contraseña": "Test1234!"},
]

_TOKEN_POOL: list[str] = []


@events.test_start.add_listener
def _precargar_tokens(environment, **_kw):
    base_url = (environment.host or "http://localhost:8000").rstrip("/")
    print("\n[stress] Precargando tokens JWT...")
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
        except Exception:
            pass
        time.sleep(0.3)
    print(f"[stress] Pool listo: {len(_TOKEN_POOL)} tokens\n")


class StressTasks(TaskSet):
    """Mezcla de operaciones para simular carga real bajo estrés."""

    @task(5)
    def listar_lugares(self):
        cat = random.choice(CATEGORIAS)
        self.client.get(f"/places?categoria={cat}", name="GET /places?categoria=[cat]")

    @task(4)
    def lugares_cercanos_postgis(self):
        lat = PASTO_LAT + random.uniform(-0.08, 0.08)
        lon = PASTO_LON + random.uniform(-0.08, 0.08)
        radio = random.choice([1, 2, 5, 10])
        self.client.get(
            f"/places/nearby?latitud={lat:.4f}&longitud={lon:.4f}&radio_km={radio}",
            headers={"Authorization": f"Bearer {random.choice(_TOKEN_POOL)}"} if _TOKEN_POOL else {},
            name="GET /places/nearby",
        )

    @task(3)
    def recomendaciones_populares(self):
        self.client.get("/recommendations/popular", name="GET /recommendations/popular")

    @task(3)
    def recomendaciones_cercanas(self):
        lat = PASTO_LAT + random.uniform(-0.05, 0.05)
        lon = PASTO_LON + random.uniform(-0.05, 0.05)
        self.client.get(
            f"/recommendations/nearby?latitud={lat:.4f}&longitud={lon:.4f}&radio_km=10",
            name="GET /recommendations/nearby",
        )

    @task(2)
    def recomendaciones_auth(self):
        if not _TOKEN_POOL:
            return
        lat = PASTO_LAT + random.uniform(-0.05, 0.05)
        lon = PASTO_LON + random.uniform(-0.05, 0.05)
        self.client.get(
            f"/recommendations?latitud={lat:.4f}&longitud={lon:.4f}&radio_km=10&limite=10",
            headers={"Authorization": f"Bearer {random.choice(_TOKEN_POOL)}"},
            name="GET /recommendations (auth)",
        )

    @task(1)
    def health(self):
        self.client.get("/", name="GET /health")


class StressUser(HttpUser):
    """
    ISO 25010 - Eficiencia de Rendimiento: Capacidad (PE-2.3).
    Usuario para prueba de estrés escalonada.
    """
    tasks = [StressTasks]
    wait_time = between(0.5, 2)


class StressShape(LoadTestShape):
    """
    Perfil de carga escalonado para encontrar el punto de quiebre:
      Escala de 50 a 500 usuarios en 6 minutos, luego cool-down.

    Para ejecutar:
      locust -f tests/performance/stress_locustfile.py StressUser \\
             --host http://localhost:8000 --headless \\
             --csv resultados_stress
    """

    _stages = [
        {"hasta": 60,  "usuarios": 50,  "spawn_rate": 5.0},
        {"hasta": 120, "usuarios": 100, "spawn_rate": 5.0},
        {"hasta": 180, "usuarios": 200, "spawn_rate": 5.0},
        {"hasta": 240, "usuarios": 300, "spawn_rate": 5.0},
        {"hasta": 300, "usuarios": 400, "spawn_rate": 5.0},
        {"hasta": 360, "usuarios": 500, "spawn_rate": 5.0},
        {"hasta": 420, "usuarios": 0,   "spawn_rate": 20.0},
    ]

    def tick(self):
        t = self.get_run_time()
        for stage in self._stages:
            if t < stage["hasta"]:
                return stage["usuarios"], stage["spawn_rate"]
        return None


@events.quitting.add_listener
def _validar_stress(environment, **_kw):
    """Resume los resultados del stress test y reporta el punto de quiebre."""
    stats = environment.runner.stats.total
    if not stats.num_requests:
        return

    p95 = stats.get_response_time_percentile(0.95) or 0
    p99 = stats.get_response_time_percentile(0.99) or 0
    error_pct = stats.num_failures / stats.num_requests * 100

    print("\n" + "=" * 62)
    print("  RESUMEN STRESS TEST — ISO 25010 PE: Capacidad")
    print("=" * 62)
    print(f"  Requests totales  : {stats.num_requests}")
    print(f"  Fallos            : {stats.num_failures}")
    print(f"  Error rate        : {error_pct:.2f}%   [límite 5%]")
    print(f"  Latencia p95      : {p95:.0f} ms   [límite 3000 ms]")
    print(f"  Latencia p99      : {p99:.0f} ms")
    print(f"  RPS promedio      : {stats.total_rps:.1f}")
    print("-" * 62)

    if error_pct > 5 or p95 > 3000:
        print("  [PUNTO DE QUIEBRE DETECTADO]")
        if error_pct > 5:
            print(f"    ✗ Error rate {error_pct:.1f}% > 5%")
        if p95 > 3000:
            print(f"    ✗ p95 {p95:.0f} ms > 3000 ms")
        print("    → Documentar usuarios activos en ese momento como límite de capacidad")
        environment.process_exit_code = 1
    else:
        print("  [OK] Sistema soportó carga máxima dentro de umbrales")
    print("=" * 62 + "\n")
