"""
Carga HTTP con Locust contra la API EXPLORO.

Uso local (API ya levantada):
  locust -f tests/performance/locustfile.py --host http://127.0.0.1:8000

CI / headless:
  locust -f tests/performance/locustfile.py --host http://127.0.0.1:8000 \\
    --headless -u 100 -r 100 -t 30s --csv /tmp/exploro_locust
"""

from locust import HttpUser, between, task


class ExploroLoadUser(HttpUser):
    wait_time = between(0.01, 0.05)

    @task(4)
    def health(self):
        self.client.get("/", name="GET /")

    @task(6)
    def popular(self):
        self.client.get("/recommendations/popular", name="GET /recommendations/popular")
