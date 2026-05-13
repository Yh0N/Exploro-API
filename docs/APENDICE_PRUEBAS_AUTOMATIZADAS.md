# Apéndice: pruebas automatizadas (EXPLORO API)

Este documento resume cómo ejecutar y mantener las pruebas **pytest** (unitarias e integración), **cobertura**, **Locust** (carga) y **OWASP ZAP** (seguridad), alineado con FastAPI y PostgreSQL/PostGIS.

## Estructura

| Ruta | Propósito |
|------|-----------|
| `tests/conftest.py` | Variables de entorno mínimas para importar la app sin `.env` local. |
| `tests/unit/` | Pruebas **unitarias** con mocks (sin PostgreSQL). Incluye `conftest.py` que registra modelos SQLAlchemy en orden. |
| `tests/integration/` | Pruebas de **integración** con **TestClient** y base real (PostGIS). |
| `tests/performance/locustfile.py` | Escenarios de carga HTTP. |
| `scripts/check_locust_p95.py` | Comprueba el peor **p95** del CSV de Locust frente a un umbral (p. ej. 200 ms). |
| `.github/workflows/ci.yml` | CI en GitHub Actions (tests, cobertura, Locust, ZAP). |
| `requirements-dev.txt` | Herramientas de prueba: `pytest-cov`, `httpx`, `testcontainers`, `locust`. |

## Unitarias (pytest + mocks)

Instalación:

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit -v
```

Cobertura solo unitarias (sin umbral global en `.coveragerc`; el **80 %** se exige en CI al combinar con integración):

```bash
pytest tests/unit --cov=app --cov-config=.coveragerc --cov-report=term-missing
```

## Integración (FastAPI TestClient + PostgreSQL/PostGIS)

**Importante:** en un mismo proceso Python no mezcles `tests/unit` (que importan `app.database.connection` con una URL por defecto) con integración que debe fijar `DATABASE_URL` **antes** del primer `import app.main`. En CI se ejecutan en **dos procesos** distintos dentro del mismo job.

### Opción A — CI / Postgres local (sin Testcontainers)

Asegura PostGIS y variables (`DATABASE_URL`, `SECRET_KEY`, etc.), luego:

```bash
set USE_TESTCONTAINERS=0
pytest tests/integration -m integration -v
```

(Linux/macOS: `export USE_TESTCONTAINERS=0`.)

### Opción B — Testcontainers (Docker local)

Con Docker en ejecución:

```bash
pytest tests/integration -m integration -v
```

Por defecto `USE_TESTCONTAINERS=1` levanta `postgis/postgis:15-3.3`.

Tras cada prueba se hace `TRUNCATE ... CASCADE` para aislar datos.

## Cobertura combinada ≥ 80 % (como en CI)

Dos invocaciones secuenciales (dos procesos):

```bash
pytest tests/unit --cov=app --cov-config=.coveragerc --cov-report=
set USE_TESTCONTAINERS=0
pytest tests/integration -m integration --cov=app --cov-append --cov-config=.coveragerc --cov-report=term-missing --cov-fail-under=80
```

En `.coveragerc` se excluyen módulos *stub* sin lógica (`linear_regression`, `collaborative_filter`, `sentiment_analysis`).

## Carga / rendimiento (Locust)

Objetivo de referencia: ~**100 usuarios** y rampa **100 usuarios/s**, midiendo latencias (p95 &lt; **200 ms** en entornos rápidos; en runners compartidos puede variar).

1. Levanta la API con PostGIS (por ejemplo `docker compose up`) y variables coherentes con `.env`.
2. Ejecuta:

```bash
locust -f tests/performance/locustfile.py --host http://127.0.0.1:8000
```

Modo headless (como en CI):

```bash
locust -f tests/performance/locustfile.py --host http://127.0.0.1:8000 --headless -u 100 -r 100 -t 30s --csv /tmp/exploro_locust
python scripts/check_locust_p95.py /tmp/exploro_locust_stats.csv --max-p95-ms 200
```

## Seguridad (OWASP ZAP Baseline)

En CI, ZAP ataca `http://host.docker.internal:8000` con la API escuchando en `0.0.0.0:8000`. Localmente puedes usar la [ZAP Desktop](https://www.zaproxy.org/) o el contenedor oficial apuntando a tu host.

El *baseline* ayuda a detectar problemas comunes (cabeceras, configuración, rutas expuestas). Para **SQL injection** y **autenticación**, combina ZAP con pruebas parametrizadas y revisión de consultas parametrizadas (SQLAlchemy) y JWT en `app/core/security.py`.

## GitHub Actions

El workflow `.github/workflows/ci.yml` define:

1. **test** — servicio `postgis/postgis`, `pytest tests/unit` y luego `pytest tests/integration` con `--cov-append` y `--cov-fail-under=80`.
2. **load-test** — API + Locust + `scripts/check_locust_p95.py`.
3. **owasp-zap-baseline** — API + acción `zaproxy/action-baseline`.

## Nota sobre corrección en `review_service`

Las pruebas detectaron un error en el listado de reseñas: se usaba un nombre de variable incorrecto en la list comprehension. Quedó corregido para que `GET /places/{id}/reviews` funcione correctamente.
