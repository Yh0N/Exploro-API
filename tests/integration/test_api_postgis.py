"""
Integración HTTP + PostgreSQL/PostGIS (Testcontainers o DATABASE_URL en CI).
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def _register(client: TestClient, suffix: str, rol: str = "usuario_regular", preferencias=None):
    correo = f"u{suffix}@example.com"
    body = {
        "nombre": f"Usuario {suffix}",
        "correo": correo,
        "contraseña": "Secret123!",
        "preferencias": preferencias or [],
        "rol": rol,
    }
    r = client.post("/auth/register", json=body)
    assert r.status_code == 201, r.text
    return correo, body["contraseña"]


def _login(client: TestClient, correo: str, password: str) -> str:
    r = client.post(
        "/auth/login",
        data={"username": correo, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_health(client: TestClient):
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data.get("message")
    assert "version" in data


def test_recommendations_popular_sin_datos(client: TestClient):
    r = client.get("/recommendations/popular")
    assert r.status_code == 200
    assert r.json() == []


def test_flujo_admin_pyme_lugar_resena_recomendaciones(client: TestClient):
    suf = uuid.uuid4().hex[:8]

    correo_adm, pwd_adm = _register(client, f"adm{suf}", rol="administrador")
    token_admin = _login(client, correo_adm, pwd_adm)

    correo_pyme, pwd_pyme = _register(client, f"pyme{suf}", rol="pyme")
    token_pyme = _login(client, correo_pyme, pwd_pyme)

    r_pyme = client.post(
        "/pymes",
        json={"nombre": "Pyme Test", "tipo": "restaurante", "ubicacion": "Pasto"},
        headers=_auth_headers(token_pyme),
    )
    assert r_pyme.status_code == 201, r_pyme.text
    id_pyme = r_pyme.json()["id_pyme"]

    r_pub = client.get(f"/pymes/{id_pyme}")
    assert r_pub.status_code == 200

    lat, lon = 1.2084, -77.2784
    r_place = client.post(
        "/places",
        json={
            "nombre": "Lugar integración",
            "descripcion": "Sitio de prueba",
            "latitud": lat,
            "longitud": lon,
            "categoria": "museo",
        },
        headers=_auth_headers(token_pyme),
    )
    assert r_place.status_code == 201, r_place.text
    id_lugar = r_place.json()["id_lugar"]

    r_pending = client.get("/admin/places", headers=_auth_headers(token_admin))
    assert r_pending.status_code == 200
    assert any(p["id_lugar"] == id_lugar for p in r_pending.json())

    r_apr = client.put(f"/admin/places/{id_lugar}/approve", headers=_auth_headers(token_admin))
    assert r_apr.status_code == 200
    assert r_apr.json()["aprobado"] is True

    correo_rev, pwd_rev = _register(client, f"rev{suf}")
    token_rev = _login(client, correo_rev, pwd_rev)

    r_review = client.post(
        f"/places/{id_lugar}/reviews",
        json={"comentarios": "Muy bueno", "puntuacion": 5},
        headers=_auth_headers(token_rev),
    )
    assert r_review.status_code == 201, r_review.text
    id_resena = r_review.json()["id_resena"]

    r_list_rev = client.get(f"/places/{id_lugar}/reviews")
    assert r_list_rev.status_code == 200
    assert len(r_list_rev.json()) >= 1

    r_places = client.get("/places")
    assert r_places.status_code == 200
    assert any(p["id_lugar"] == id_lugar for p in r_places.json())

    r_near = client.get(f"/places/nearby?latitud={lat}&longitud={lon}&radio_km=5")
    assert r_near.status_code == 200
    assert any(p["id_lugar"] == id_lugar for p in r_near.json())

    r_pop = client.get("/recommendations/popular")
    assert r_pop.status_code == 200
    assert len(r_pop.json()) >= 1

    r_near_rec = client.get(f"/recommendations/nearby?latitud={lat}&longitud={lon}&radio_km=10")
    assert r_near_rec.status_code == 200
    assert len(r_near_rec.json()) >= 1

    correo_tur, pwd_tur = _register(client, f"tur{suf}", preferencias=["museo"])
    token_tur = _login(client, correo_tur, pwd_tur)

    r_me = client.get("/users/me", headers=_auth_headers(token_tur))
    assert r_me.status_code == 200

    r_put = client.put(
        "/users/me",
        json={"nombre": f"Turista {suf}", "biografia": "Hola"},
        headers=_auth_headers(token_tur),
    )
    assert r_put.status_code == 200

    id_tur = r_me.json()["id_usuario"]
    r_pub_u = client.get(f"/users/{id_tur}")
    assert r_pub_u.status_code == 200

    r_get_place = client.get(f"/places/{id_lugar}")
    assert r_get_place.status_code == 200

    r_upd_place = client.put(
        f"/places/{id_lugar}",
        json={"nombre": "Lugar integración v2"},
        headers=_auth_headers(token_pyme),
    )
    assert r_upd_place.status_code == 200

    r_pers = client.get(
        f"/recommendations?latitud={lat}&longitud={lon}&radio_km=10&limite=5",
        headers=_auth_headers(token_tur),
    )
    assert r_pers.status_code == 200
    body = r_pers.json()
    assert isinstance(body, list)
    if body:
        assert "score_recomendacion" in body[0]
        assert "razones" in body[0]

    r_del_rev = client.delete(f"/reviews/{id_resena}", headers=_auth_headers(token_admin))
    assert r_del_rev.status_code == 200

    r_users_admin = client.get("/admin/users", headers=_auth_headers(token_admin))
    assert r_users_admin.status_code == 200
    assert len(r_users_admin.json()) >= 4

    r_out = client.post("/auth/logout", headers=_auth_headers(token_tur))
    assert r_out.status_code == 200

    r_after = client.get("/users/me", headers=_auth_headers(token_tur))
    assert r_after.status_code == 401

    r_del_place = client.delete(f"/places/{id_lugar}", headers=_auth_headers(token_admin))
    assert r_del_place.status_code == 200
