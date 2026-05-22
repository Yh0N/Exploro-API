"""
Pruebas de carga y rendimiento para Exploro API.
Herramienta: Locust 2.x (https://locust.io)

Escenarios implementados:
  E1  50 VU x 5 min  -> GET /places?categoria=restaurante  (lectura publica)
  E2  100 VU x 3 min -> POST /auth/login + GET /recommendations (flujo autenticado)
  E3  Pico 0->200 VU -> GET /places/nearby (PostGIS geoespacial)

Umbrales RNF2:
  p95 < 2000 ms | p99 < 3000 ms | error rate < 1%

Instrucciones de ejecucion:
  # Instalar dependencias
  pip install locust

  # Pre-requisito: datos semilla cargados
  python seed_data.py

  # E1 - Listado de lugares (50 VU, 5 minutos)
  locust -f tests/performance/locustfile.py ListarLugaresPorCategoria \\
         --host http://localhost:8000 --headless -u 50 -r 5 -t 5m

  # E2 - Login + Recomendaciones (100 VU, 3 minutos)
  locust -f tests/performance/locustfile.py FlujoLoginRecomendaciones \\
         --host http://localhost:8000 --headless -u 100 -r 10 -t 3m

  # E3 - Pico geoespacial (ramp-up 0->200 en 2 min, usar Shape)
  locust -f tests/performance/locustfile.py PlacesNearbyUser \\
         --host http://localhost:8000 --headless --run-time 4m

  # Todos los escenarios con UI web (abrir http://localhost:8089)
  locust -f tests/performance/locustfile.py --host http://localhost:8000
"""

from __future__ import annotations

import random
import uuid

from locust import HttpUser, LoadTestShape, TaskSet, between, events, task


# ---------------------------------------------------------------------------
# Coordenadas del centro de Pasto, Colombia
# ---------------------------------------------------------------------------
PASTO_LAT = 1.2136
PASTO_LON = -77.2811

CATEGORIAS = [
    "restaurante", "parque", "museo", "iglesia",
    "mirador", "hotel", "agencia", "cafe",
]

# Credenciales de usuarios creados por seed_data.py
SEED_USERS = [
    {"correo": "turista1@exploro.test", "contraseña": "Test1234!"},
    {"correo": "turista2@exploro.test", "contraseña": "Test1234!"},
    {"correo": "pyme1@exploro.test",    "contraseña": "Test1234!"},
    {"correo": "pyme2@exploro.test",    "contraseña": "Test1234!"},
    {"correo": "admin@exploro.test",    "contraseña": "Test1234!"},
]


# ---------------------------------------------------------------------------
# Helper: login OAuth2 y devuelve JWT
# ---------------------------------------------------------------------------
def _login(client, correo: str, contraseña: str) -> str | None:
    """Retorna access_token o None si el login falla."""
    with client.post(
        "/auth/login",
        data={"username": correo, "password": contraseña},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        name="POST /auth/login",
        catch_response=True,
    ) as resp:
        if resp.status_code == 200:
            resp.success()
            return resp.json().get("access_token")
        resp.failure(f"Login fallo ({resp.status_code}): {resp.text[:100]}")
        return None


# ===========================================================================
# ESCENARIO 1  Listado de lugares por categoria (carga sostenida)
# Configuracion recomendada: -u 50 -r 5 -t 5m
# ===========================================================================
class ListarLugaresPorCategoria(HttpUser):
    """
    E1: Turistas anonimos navegando el catalogo publico.
    Solo lectura, sin autenticacion JWT.
    Objetivo: p95 < 500 ms, error rate < 1 %.
    """

    wait_time = between(1, 3)

    @task(4)
    def listar_por_categoria(self):
        """GET /places?categoria=X - el endpoint publico mas frecuente."""
        categoria = random.choice(CATEGORIAS)
        self.client.get(
            f"/places?categoria={categoria}",
            name="GET /places?categoria=[cat]",
        )

    @task(2)
    def listar_sin_filtro(self):
        """GET /places - catalogo completo sin filtros."""
        self.client.get("/places", name="GET /places")

    @task(2)
    def listar_con_calificacion(self):
        """GET /places?calificacion_min=4 - filtro de calidad."""
        self.client.get(
            "/places?calificacion_min=4",
            name="GET /places?calificacion_min=4",
        )

    @task(1)
    def health_check(self):
        """GET / - latencia de linea de base."""
        self.client.get("/", name="GET /health")

    @task(1)
    def listar_pymes(self):
        """GET /pymes - catalogo de pymes turisticas."""
        self.client.get("/pymes", name="GET /pymes")


# ===========================================================================
# ESCENARIO 2  Flujo completo: login + recomendaciones personalizadas
# Configuracion recomendada: -u 100 -r 10 -t 3m
# ===========================================================================
class FlujoLoginRecomendaciones(HttpUser):
    """
    E2: Turistas autenticados usando el motor de recomendaciones.
    Objetivo: p95 < 2000 ms, p99 < 3000 ms, error rate < 1 %.
    """

    wait_time = between(2, 5)

    def on_start(self):
        """Obtiene JWT al inicio de cada usuario virtual."""
        self.token: str | None = None
        cred = random.choice(SEED_USERS)
        self.token = _login(self.client, cred["correo"], cred["contraseña"])

        # Fallback: crea un usuario temporal si la semilla no existe
        if self.token is None:
            suffix = uuid.uuid4().hex[:8]
            correo = f"vu_{suffix}@load.test"
            self.client.post(
                "/auth/register",
                json={
                    "nombre": f"VU {suffix}",
                    "correo": correo,
                    "contraseña": "Load1234!",
                    "preferencias": ["museo", "parque"],
                    "rol": "usuario_regular",
                },
                name="POST /auth/register [setup]",
            )
            self.token = _login(self.client, correo, "Load1234!")

    def _headers(self) -> dict:
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    @task(5)
    def recomendaciones_personalizadas(self):
        """GET /recommendations - motor hibrido con geolocalizacion."""
        delta_lat = random.uniform(-0.05, 0.05)
        delta_lon = random.uniform(-0.05, 0.05)
        radio = random.randint(2, 10)
        limite = random.choice([5, 10, 15])
        lat = PASTO_LAT + delta_lat
        lon = PASTO_LON + delta_lon
        self.client.get(
            f"/recommendations?latitud={lat:.4f}&longitud={lon:.4f}"
            f"&radio_km={radio}&limite={limite}",
            headers=self._headers(),
            name="GET /recommendations",
        )

    @task(2)
    def recomendaciones_populares(self):
        """GET /recommendations/popular - sin auth, popularidad global."""
        self.client.get(
            "/recommendations/popular",
            name="GET /recommendations/popular",
        )

    @task(2)
    def ver_mi_perfil(self):
        """GET /users/me - latencia del endpoint de perfil autenticado."""
        self.client.get(
            "/users/me",
            headers=self._headers(),
            name="GET /users/me",
        )

    @task(1)
    def ver_detalle_lugar(self):
        """GET /places/{id} - detalle de un lugar (cache-friendly)."""
        id_lugar = random.randint(1, 20)
        self.client.get(
            f"/places/{id_lugar}",
            name="GET /places/[id]",
        )


# ===========================================================================
# ESCENARIO 3  Pico: busqueda geoespacial PostGIS (ramp-up 0->200 en 2 min)
# Controlado por PicoGeoespacialShape
# ===========================================================================
class BusquedaGeoespacialTasks(TaskSet):
    """Tareas para el escenario de pico de carga geoespacial."""

    @task(6)
    def nearby_pasto_centro(self):
        """GET /places/nearby - radio variable, coordenadas fijas del centro."""
        radio = random.choice([1, 2, 3, 5])
        self.client.get(
            f"/places/nearby?latitud={PASTO_LAT}&longitud={PASTO_LON}&radio_km={radio}",
            name="GET /places/nearby [pasto centro]",
        )

    @task(3)
    def nearby_aleatorio(self):
        """GET /places/nearby - posicion ligeramente aleatoria (variabilidad)."""
        lat = PASTO_LAT + random.uniform(-0.08, 0.08)
        lon = PASTO_LON + random.uniform(-0.08, 0.08)
        radio = round(random.uniform(0.5, 5.0), 1)
        self.client.get(
            f"/places/nearby?latitud={lat:.4f}&longitud={lon:.4f}&radio_km={radio}",
            name="GET /places/nearby [random]",
        )

    @task(1)
    def recomendaciones_cercanas(self):
        """GET /recommendations/nearby - endpoint PostGIS de recomendaciones."""
        radio = random.randint(2, 10)
        self.client.get(
            f"/recommendations/nearby"
            f"?latitud={PASTO_LAT}&longitud={PASTO_LON}&radio_km={radio}",
            name="GET /recommendations/nearby",
        )


class PlacesNearbyUser(HttpUser):
    """
    E3: Clase base para el pico geoespacial.
    La forma (shape) PicoGeoespacialShape controla el volumen de usuarios.
    """

    tasks = [BusquedaGeoespacialTasks]
    wait_time = between(0.5, 2)


# ===========================================================================
# Shape personalizada para E3: ramp-up 0->200 VU en 2 min
# ===========================================================================
class PicoGeoespacialShape(LoadTestShape):
    """
    Perfil de carga tipo 'pico':
      00:00-02:00  ramp-up lineal  0 -> 200 usuarios  (spawn_rate=1.67/s)
      02:00-03:00  meseta           200 usuarios       (carga maxima)
      03:00-04:00  cool-down        200 -> 0 usuarios

    Para usar esta forma ejecutar:
      locust -f locustfile.py PlacesNearbyUser \\
             --host http://localhost:8000 --headless --run-time 4m
    """

    _stages = [
        {"hasta": 120, "usuarios": 200, "spawn_rate": 1.67},   # 2 min ramp-up
        {"hasta": 180, "usuarios": 200, "spawn_rate": 0.0},    # 1 min meseta
        {"hasta": 240, "usuarios": 0,   "spawn_rate": 5.0},    # 1 min cool-down
    ]

    def tick(self):
        t = self.get_run_time()
        for stage in self._stages:
            if t < stage["hasta"]:
                return stage["usuarios"], stage["spawn_rate"]
        return None  # termina la prueba


# ===========================================================================
# Listener: resumen de metricas RNF2 al finalizar
# ===========================================================================
@events.quitting.add_listener
def _validar_umbrales_rnf2(environment, **_kw):
    """
    Imprime resumen y verifica los umbrales de rendimiento definidos en RNF2:
      - Latencia p95 < 2000 ms
      - Latencia p99 < 3000 ms
      - Error rate  < 1 %
    """
    stats = environment.runner.stats.total
    if not stats.num_requests:
        return

    p95 = stats.get_response_time_percentile(0.95) or 0
    p99 = stats.get_response_time_percentile(0.99) or 0
    error_pct = stats.num_failures / stats.num_requests * 100

    print("\n" + "=" * 62)
    print("  RESUMEN METRICAS RNF2 - Exploro API")
    print("=" * 62)
    print(f"  Requests totales : {stats.num_requests}")
    print(f"  Fallos           : {stats.num_failures}")
    print(f"  Error rate       : {error_pct:.2f}%   [limite 1%]")
    print(f"  Latencia p50     : {stats.get_response_time_percentile(0.50):.0f} ms")
    print(f"  Latencia p95     : {p95:.0f} ms  [limite 2000 ms]")
    print(f"  Latencia p99     : {p99:.0f} ms  [limite 3000 ms]")
    print(f"  RPS promedio     : {stats.total_rps:.1f}")
    print("-" * 62)

    fallos = []
    if p95 > 2_000:
        fallos.append(f"p95 {p95:.0f} ms > 2000 ms")
    if p99 > 3_000:
        fallos.append(f"p99 {p99:.0f} ms > 3000 ms")
    if error_pct > 1:
        fallos.append(f"Error rate {error_pct:.2f}% > 1%")

    if fallos:
        print("  [FALLO RNF2]")
        for f in fallos:
            print(f"    x {f}")
        environment.process_exit_code = 1
    else:
        print("  [OK] Todos los umbrales RNF2 cumplidos")
    print("=" * 62 + "\n")
