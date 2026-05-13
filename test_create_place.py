"""
Prueba end-to-end del endpoint POST /places con dirección textual.
Ejecutar con: docker exec exploro_api python test_create_place.py
"""
import httpx

BASE = "http://localhost:8000"

# 1. Login para obtener token
print("1. Haciendo login...")
login_resp = httpx.post(f"{BASE}/auth/login", json={
    "correo": "admin@gmail.com",
    "contraseña": "secret"
})
if login_resp.status_code != 200:
    print(f"  ❌ Login fallido: {login_resp.status_code} - {login_resp.text}")
    exit(1)

token = login_resp.json().get("access_token")
print(f"  ✅ Token obtenido: {token[:30]}...")

headers = {"Authorization": f"Bearer {token}"}

# 2. Crear lugar con dirección textual
print("\n2. Creando lugar con dirección textual...")
create_resp = httpx.post(f"{BASE}/places", json={
    "nombre": "Lugar de Prueba con Dirección",
    "descripcion": "Prueba de geocoding",
    "categoria": "parque",
    "ubicacion_textual": "Calle 18, Centro, Pasto"
}, headers=headers)

print(f"  Status: {create_resp.status_code}")
if create_resp.status_code == 201:
    data = create_resp.json()
    print(f"  ✅ Lugar creado exitosamente!")
    print(f"     ID: {data.get('id_lugar')}")
    print(f"     Nombre: {data.get('nombre')}")
    print(f"     Latitud: {data.get('latitud')}")
    print(f"     Longitud: {data.get('longitud')}")
    print(f"     Dirección: {data.get('direccion')}")
else:
    print(f"  ❌ Error: {create_resp.text}")

# 3. Crear lugar con coordenadas directas
print("\n3. Creando lugar con coordenadas directas...")
create_resp2 = httpx.post(f"{BASE}/places", json={
    "nombre": "Lugar de Prueba con Coordenadas",
    "descripcion": "Prueba con lat/lng",
    "categoria": "naturaleza",
    "latitud": 1.2136,
    "longitud": -77.2811
}, headers=headers)

print(f"  Status: {create_resp2.status_code}")
if create_resp2.status_code == 201:
    data2 = create_resp2.json()
    print(f"  ✅ Lugar creado exitosamente!")
    print(f"     ID: {data2.get('id_lugar')}")
    print(f"     Latitud: {data2.get('latitud')}")
    print(f"     Longitud: {data2.get('longitud')}")
else:
    print(f"  ❌ Error: {create_resp2.text}")
