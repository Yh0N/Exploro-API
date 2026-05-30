"""
Seed data para pruebas de carga locales (Locust).

Crea los usuarios y lugares que necesita locustfile.py para funcionar.
Usar SOLO en ambiente local/desarrollo — nunca en producción.

Uso:
  # Crear seed data:
  python scripts/seed_load_test.py

  # Eliminar seed data después:
  python scripts/seed_load_test.py --cleanup

  # URL personalizada:
  python scripts/seed_load_test.py --base-url http://localhost:8000
"""
from __future__ import annotations

import argparse
import sys
import time
import requests

DEFAULT_BASE = "http://localhost:8000"

SEED_USERS = [
    {"nombre": "Turista 1",   "correo": "turista1@exploro.test", "contraseña": "Test1234!", "rol": 1, "preferencias": ["museo", "parque"]},
    {"nombre": "Turista 2",   "correo": "turista2@exploro.test", "contraseña": "Test1234!", "rol": 1, "preferencias": ["restaurante"]},
    {"nombre": "Pyme 1",      "correo": "pyme1@exploro.test",    "contraseña": "Test1234!", "rol": 2, "preferencias": []},
    {"nombre": "Pyme 2",      "correo": "pyme2@exploro.test",    "contraseña": "Test1234!", "rol": 2, "preferencias": []},
    {"nombre": "Admin Test",  "correo": "admin@exploro.test",    "contraseña": "Test1234!", "rol": 3, "preferencias": []},
]

SEED_LUGARES = [
    {"nombre": "Parque Nariño",       "descripcion": "Parque central de Pasto", "latitud": 1.2136,  "longitud": -77.2811, "categoria": "parque"},
    {"nombre": "Laguna La Cocha",     "descripcion": "Laguna natural del sur",  "latitud": 1.0987,  "longitud": -77.1423, "categoria": "naturaleza"},
    {"nombre": "Iglesia San Juan",    "descripcion": "Iglesia histórica",       "latitud": 1.2145,  "longitud": -77.2790, "categoria": "religioso"},
    {"nombre": "Museo del Carnaval",  "descripcion": "Museo del Carnaval",      "latitud": 1.2156,  "longitud": -77.2834, "categoria": "museo"},
    {"nombre": "Mirador Morasurco",   "descripcion": "Vista panorámica",        "latitud": 1.1890,  "longitud": -77.2450, "categoria": "mirador"},
    {"nombre": "Restaurante El Patio","descripcion": "Comida típica nariñense", "latitud": 1.2130,  "longitud": -77.2800, "categoria": "restaurante"},
    {"nombre": "Hotel Cuellar's",     "descripcion": "Hotel céntrico",          "latitud": 1.2140,  "longitud": -77.2815, "categoria": "hotel"},
    {"nombre": "Volcán Galeras",      "descripcion": "Volcán activo cercano",   "latitud": 1.2207,  "longitud": -77.3597, "categoria": "naturaleza"},
    {"nombre": "Catedral de Pasto",   "descripcion": "Catedral principal",      "latitud": 1.2139,  "longitud": -77.2808, "categoria": "religioso"},
    {"nombre": "Plaza del Carnaval",  "descripcion": "Plaza principal",         "latitud": 1.2134,  "longitud": -77.2809, "categoria": "parque"},
    {"nombre": "Café El Volcán",      "descripcion": "Café artesanal",          "latitud": 1.2125,  "longitud": -77.2795, "categoria": "restaurante"},
    {"nombre": "Centro Artesanal",    "descripcion": "Artesanías nariñenses",   "latitud": 1.2148,  "longitud": -77.2820, "categoria": "cultura"},
    {"nombre": "Bosque Municipal",    "descripcion": "Área verde urbana",       "latitud": 1.2200,  "longitud": -77.2700, "categoria": "parque"},
    {"nombre": "Mirador Campanero",   "descripcion": "Vista al volcán",         "latitud": 1.2100,  "longitud": -77.3100, "categoria": "mirador"},
    {"nombre": "Laguna Verde",        "descripcion": "Laguna volcánica",        "latitud": 1.2250,  "longitud": -77.3620, "categoria": "naturaleza"},
    {"nombre": "Museo Taminango",     "descripcion": "Arte popular",            "latitud": 1.2160,  "longitud": -77.2850, "categoria": "museo"},
    {"nombre": "Plaza de Nariño",     "descripcion": "Plaza fundacional",       "latitud": 1.2138,  "longitud": -77.2812, "categoria": "cultura"},
    {"nombre": "Agencia Exploro",     "descripcion": "Tours locales",           "latitud": 1.2135,  "longitud": -77.2805, "categoria": "agencia"},
    {"nombre": "Termas de Tajumbina", "descripcion": "Aguas termales",          "latitud": 1.4100,  "longitud": -77.0200, "categoria": "naturaleza"},
    {"nombre": "Santuario Las Lajas", "descripcion": "Santuario famoso",        "latitud": 0.8100,  "longitud": -77.5900, "categoria": "religioso"},
]


def _login(base: str, correo: str, contraseña: str) -> str | None:
    r = requests.post(f"{base}/auth/login", json={"correo": correo, "contraseña": contraseña}, timeout=10)
    if r.status_code == 200:
        return r.json().get("access_token")
    return None


def crear_seed(base: str) -> None:
    print(f"\n{'='*55}")
    print("  CREANDO SEED DATA PARA LOAD TEST")
    print(f"{'='*55}")

    # 1. Crear usuarios
    print("\n[1/3] Creando usuarios seed...")
    for user in SEED_USERS:
        r = requests.post(f"{base}/auth/register", json=user, timeout=10)
        if r.status_code == 201:
            print(f"  [OK] {user['correo']}")
        elif r.status_code == 409:
            print(f"  [YA EXISTE] {user['correo']}")
        else:
            print(f"  [ERROR {r.status_code}] {user['correo']}: {r.text[:60]}")
        time.sleep(0.4)  # evitar rate limit

    # 2. Login de la pyme para crear lugares
    print("\n[2/3] Autenticando pyme para crear lugares...")
    token_pyme = _login(base, "pyme1@exploro.test", "Test1234!")

    if not token_pyme:
        print("  [ERROR] No se pudo autenticar pyme1. Los lugares no se crearán.")
        return

    # Crear pyme si no existe
    r_pyme = requests.post(
        f"{base}/pymes",
        json={"nombre": "Pyme Test Locust", "tipo": "agencia", "ubicacion_textual": "Pasto, Nariño"},
        headers={"Authorization": f"Bearer {token_pyme}"},
        timeout=10,
    )
    if r_pyme.status_code in (200, 201):
        print(f"  [OK] Pyme creada: id={r_pyme.json().get('id_pyme')}")
    else:
        print(f"  [INFO] Pyme: {r_pyme.status_code} — {r_pyme.text[:60]}")

    # 3. Crear lugares
    print("\n[3/3] Creando lugares turísticos...")
    lugares_creados = 0
    for lugar in SEED_LUGARES:
        r = requests.post(
            f"{base}/places",
            json=lugar,
            headers={"Authorization": f"Bearer {token_pyme}"},
            timeout=10,
        )
        if r.status_code == 201:
            lugares_creados += 1
            print(f"  [OK] {lugar['nombre']}")
        else:
            print(f"  [ERROR {r.status_code}] {lugar['nombre']}: {r.text[:60]}")
        time.sleep(0.1)

    print(f"\n{'='*55}")
    print(f"  Seed completado: {len(SEED_USERS)} usuarios, {lugares_creados} lugares")
    print(f"  Ahora puedes correr:")
    print(f"  locust -f tests/performance/locustfile.py PlacesNearbyUser \\")
    print(f"         --host {base} --headless --run-time 4m --csv resultados_pico")
    print(f"{'='*55}\n")


def eliminar_seed(base: str) -> None:
    print(f"\n{'='*55}")
    print("  ELIMINANDO SEED DATA DE LOAD TEST")
    print(f"{'='*55}")

    token_admin = _login(base, "admin@exploro.test", "Test1234!")
    if not token_admin:
        print("  [ERROR] No se pudo autenticar admin. Limpieza cancelada.")
        return

    headers = {"Authorization": f"Bearer {token_admin}"}

    # Obtener todos los usuarios y eliminar los seed + VUs temporales
    r = requests.get(f"{base}/admin/users", headers=headers, timeout=10)
    if r.status_code != 200:
        print(f"  [ERROR] No se pudo obtener usuarios: {r.status_code}")
        return

    seed_correos = {u["correo"] for u in SEED_USERS}
    usuarios = r.json()
    eliminados_seed = 0
    eliminados_vu = 0

    for u in usuarios:
        correo = u.get("correo", "")
        es_seed = correo in seed_correos
        # Usuarios temporales creados por el fallback de Locust cuando no hay seeds
        es_vu_temporal = correo.endswith("@load.test") and correo.startswith("vu_")

        if es_seed or es_vu_temporal:
            r_del = requests.delete(f"{base}/admin/users/{u['id_usuario']}", headers=headers, timeout=10)
            if r_del.status_code == 200:
                if es_seed:
                    print(f"  [OK] Seed eliminado:  {correo}")
                    eliminados_seed += 1
                else:
                    print(f"  [OK] VU eliminado:    {correo}")
                    eliminados_vu += 1
            else:
                print(f"  [ERROR] {correo}: {r_del.status_code}")

    print(f"\n  {eliminados_seed} usuarios seed eliminados (lugares en cascada).")
    print(f"  {eliminados_vu} usuarios VU temporales (vu_*@load.test) eliminados.")
    print(f"{'='*55}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed data para load test de Exploro API")
    parser.add_argument("--cleanup", action="store_true", help="Eliminar el seed data")
    parser.add_argument("--base-url", default=DEFAULT_BASE, help=f"URL base de la API (default: {DEFAULT_BASE})")
    args = parser.parse_args()

    try:
        requests.get(f"{args.base_url}/", timeout=5)
    except Exception:
        print(f"\n[ERROR] La API no responde en {args.base_url}")
        print("  Verifica que Docker esté corriendo.")
        sys.exit(1)

    if args.cleanup:
        eliminar_seed(args.base_url)
    else:
        crear_seed(args.base_url)


if __name__ == "__main__":
    main()
