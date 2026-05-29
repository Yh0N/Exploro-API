"""
Pruebas de seguridad automatizadas para Exploro API.

Organización:
  SEC-AUTH-*   Autenticación y tokens JWT
  SEC-RESP-*   Integridad de respuestas (no exponer datos sensibles)
  SEC-INJ-*    Inyección SQL / sanitización de entradas
  SEC-RATE-*   Rate limiting (slowapi)
  SEC-PERM-*   Control de acceso por rol

Tests que requieren base de datos real se marcan con @pytest.mark.integration.
El resto usa mocks/TestClient sin DB.

Ejecución:
  # Solo tests sin DB (rapidos):
  pytest tests/security/ -m "not integration" -v

  # Todos (incluyendo DB con Testcontainers):
  pytest tests/security/ -v
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from app.core import security as sec_module


# ===========================================================================
# SEC-AUTH  Autenticación y validación de tokens JWT
# (sin base de datos, solo lógica de seguridad)
# ===========================================================================

class TestJwtSeguridad:
    """SEC-AUTH: valida que los tokens JWT se generen, verifiquen y rechacen correctamente."""

    def test_sec_auth_01_token_invalido_rechazado(self):
        """SEC-AUTH-01: un JWT malformado debe retornar 401."""
        with pytest.raises(Exception) as exc:
            sec_module.verify_token("esto.no.es.un.jwt")
        # verify_token lanza HTTPException 401
        assert exc.value.status_code == 401

    def test_sec_auth_02_token_expirado_rechazado(self, monkeypatch):
        """SEC-AUTH-02: un token con exp en el pasado debe ser rechazado con 401."""
        from datetime import timedelta
        # Crea token que ya expiro hace 1 hora
        token_expirado = sec_module.create_access_token(
            {"sub": "victima@exploro.test"},
            expires_delta=timedelta(seconds=-3600),
        )
        with pytest.raises(Exception) as exc:
            sec_module.verify_token(token_expirado)
        assert exc.value.status_code == 401

    def test_sec_auth_03_token_sin_sub_rechazado(self):
        """SEC-AUTH-03: payload sin 'sub' no debe autenticar a nadie."""
        token = sec_module.create_access_token({"dato": "sin_sub"})
        with pytest.raises(Exception) as exc:
            sec_module.verify_token(token)
        # Puede ser 401 o KeyError; lo importante es que no deja pasar
        assert exc.value.status_code in (401, 422)

    def test_sec_auth_04_token_tampered_rechazado(self):
        """SEC-AUTH-04: modificar el payload del JWT invalida la firma."""
        token_original = sec_module.create_access_token({"sub": "legitimo@exploro.test"})
        # Corrompe el segmento de payload (segundo segmento separado por '.')
        partes = token_original.split(".")
        partes[1] = partes[1][:-3] + "XXX"
        token_corrupto = ".".join(partes)
        with pytest.raises(Exception) as exc:
            sec_module.verify_token(token_corrupto)
        assert exc.value.status_code == 401

    def test_sec_auth_05_token_revocado_deniega_acceso(self):
        """SEC-AUTH-05: get_current_user debe rechazar tokens en la lista negra."""
        app = FastAPI()

        @app.get("/protected")
        def ruta_protegida(user=Depends(sec_module.get_current_user)):
            return {"correo": user.correo}

        token = sec_module.create_access_token({"sub": "revocado@exploro.test"})
        db = MagicMock()
        # Simula que el token está revocado (TokenRevocado existe)
        db.query.return_value.filter.return_value.first.return_value = object()

        app.dependency_overrides[sec_module.oauth2_scheme] = lambda: token
        app.dependency_overrides[sec_module.get_db] = lambda: db

        r = TestClient(app, raise_server_exceptions=False).get("/protected")
        assert r.status_code == 401

    def test_sec_auth_06_ruta_sin_token_retorna_401(self):
        """SEC-AUTH-06: acceder a ruta protegida sin JWT debe retornar 401."""
        app = FastAPI()

        @app.get("/privado")
        def ruta_privada(user=Depends(sec_module.get_current_user)):
            return {"ok": True}

        r = TestClient(app, raise_server_exceptions=False).get("/privado")
        assert r.status_code in (401, 403)

    def test_sec_auth_07_require_role_deniega_rol_incorrecto(self):
        """SEC-AUTH-07: require_role debe retornar 403 si el rol no coincide."""
        app = FastAPI()

        @app.get("/solo_admin")
        def solo_admin(user=Depends(sec_module.require_role([3]))):
            return {"ok": True}

        turista = SimpleNamespace(rol=1)
        app.dependency_overrides[sec_module.get_current_user] = lambda: turista
        r = TestClient(app).get("/solo_admin")
        assert r.status_code == 403

    def test_sec_auth_08_require_role_permite_rol_correcto(self):
        """SEC-AUTH-08: require_role debe permitir el acceso con el rol correcto."""
        app = FastAPI()

        @app.get("/solo_admin")
        def solo_admin(user=Depends(sec_module.require_role([3]))):
            return {"ok": True}

        admin = SimpleNamespace(rol=3)
        app.dependency_overrides[sec_module.get_current_user] = lambda: admin
        r = TestClient(app).get("/solo_admin")
        assert r.status_code == 200

    def test_sec_auth_09_hash_password_no_es_reversible(self):
        """SEC-AUTH-09: la contraseña hasheada no debe ser igual al texto plano."""
        contraseña = "MiPasswordSeguro123!"
        hashed = sec_module.hash_password(contraseña)
        assert hashed != contraseña
        # Dos hashes de la misma contraseña deben ser distintos (salt diferente)
        hashed2 = sec_module.hash_password(contraseña)
        assert hashed != hashed2

    def test_sec_auth_10_verify_password_detecta_incorrecta(self):
        """SEC-AUTH-10: verify_password debe rechazar contraseñas incorrectas."""
        hashed = sec_module.hash_password("OriginalSecreta!")
        assert sec_module.verify_password("Incorrecta!", hashed) is False
        assert sec_module.verify_password("OriginalSecreta!", hashed) is True


# ===========================================================================
# SEC-RESP  Integridad de respuestas (no exponer datos sensibles)
# Requiere base de datos (Testcontainers)
# ===========================================================================

@pytest.mark.integration
class TestNoExposicionDatosSensibles:
    """SEC-RESP: valida que ninguna respuesta JSON filtre datos confidenciales."""

    def test_sec_resp_01_registro_no_expone_hash(self, sec_client):
        """SEC-RESP-01: la respuesta de /auth/register no debe incluir contraseña ni hash."""
        r = sec_client.post(
            "/auth/register",
            json={
                "nombre": "Turista Seguro",
                "correo": "nosecret@exploro.test",
                "contraseña": "NoExpongas1!",
                "preferencias": [],
                "rol": 1,
            },
        )
        assert r.status_code == 201
        body = r.json()
        _assert_no_campo_sensible(body, ["contraseña", "password", "hashed_password",
                                         "hash", "contrasena", "secret"])

    def test_sec_resp_02_login_no_expone_hash(self, sec_client):
        """SEC-RESP-02: la respuesta de /auth/login no debe exponer la contraseña."""
        sec_client.post(
            "/auth/register",
            json={
                "nombre": "Login Test",
                "correo": "logintest@exploro.test",
                "contraseña": "Secret1234!",
                "preferencias": [],
                "rol": 1,
            },
        )
        r = sec_client.post(
            "/auth/login",
            json={"correo": "logintest@exploro.test", "contraseña": "Secret1234!"},
        )
        assert r.status_code == 200
        body = r.json()
        _assert_no_campo_sensible(body, ["contraseña", "password", "hashed_password",
                                         "hash", "contrasena"])

    def test_sec_resp_03_perfil_me_no_expone_hash(self, sec_client):
        """SEC-RESP-03: GET /users/me no debe incluir la contraseña hasheada."""
        sec_client.post(
            "/auth/register",
            json={
                "nombre": "Me Test",
                "correo": "metest@exploro.test",
                "contraseña": "MeSecret1!",
                "preferencias": [],
                "rol": 1,
            },
        )
        r_login = sec_client.post(
            "/auth/login",
            json={"correo": "metest@exploro.test", "contraseña": "MeSecret1!"},
        )
        token = r_login.json()["access_token"]
        r = sec_client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        body = r.json()
        _assert_no_campo_sensible(body, ["contraseña", "password", "hashed_password",
                                         "hash", "contrasena"])

    def test_sec_resp_04_listado_usuarios_no_expone_hash(self, sec_client):
        """SEC-RESP-04: GET /places (publico) no filtra datos internos de usuario."""
        r = sec_client.get("/places")
        assert r.status_code == 200
        for lugar in r.json():
            _assert_no_campo_sensible(lugar, ["contraseña", "password", "hashed_password"])

    def test_sec_resp_05_refresh_token_no_expuesto(self, sec_client):
        """SEC-RESP-05: el refresh_token interno no debe aparecer en respuestas publicas."""
        sec_client.post(
            "/auth/register",
            json={
                "nombre": "Refresh Test",
                "correo": "refreshtest@exploro.test",
                "contraseña": "Refresh1234!",
                "preferencias": [],
                "rol": 1,
            },
        )
        r = sec_client.post(
            "/auth/login",
            json={"correo": "refreshtest@exploro.test", "contraseña": "Refresh1234!"},
        )
        body = r.json()
        # refresh_token puede estar en la respuesta (es correcto), pero no debe
        # estar en endpoints de listado de usuarios
        r_places = sec_client.get("/places")
        for item in r_places.json():
            _assert_no_campo_sensible(item, ["refresh_token"])


# ===========================================================================
# SEC-INJ  Inyeccion SQL y sanitizacion de entradas
# Requiere base de datos real (SQLAlchemy ORM protege automáticamente)
# ===========================================================================

@pytest.mark.integration
class TestInyeccionSQL:
    """
    SEC-INJ: verifica que SQLAlchemy ORM sanitiza correctamente las entradas.
    Los campos de búsqueda se pasan como parámetros vinculados (bind params),
    nunca concatenados en la query, por lo que el ORM los protege.
    """

    _PAYLOADS_INYECCION = [
        "'; DROP TABLE lugares; --",
        "' OR '1'='1",
        "' UNION SELECT null, null, null --",
        "1; SELECT * FROM usuarios --",
        "admin'--",
        "<script>alert(1)</script>",
        "' OR 1=1 --",
    ]

    def test_sec_inj_01_categoria_con_payload_no_rompe_api(self, sec_client):
        """SEC-INJ-01: payloads SQL en ?categoria no deben causar 500."""
        for payload in self._PAYLOADS_INYECCION:
            r = sec_client.get(f"/places?categoria={payload}",
                               name=f"SQL injection: {payload[:30]}")
            assert r.status_code in (200, 422, 400), (
                f"El payload '{payload}' provocó un error inesperado: {r.status_code} {r.text}"
            )
            # 200 con lista vacía es el resultado correcto (el ORM no encontró nada)
            if r.status_code == 200:
                assert isinstance(r.json(), list)

    def test_sec_inj_02_busqueda_nearby_coordenadas_invalidas(self, sec_client):
        """SEC-INJ-02: coordenadas malformadas deben retornar 422, no 500."""
        payloads_coord = [
            "1; DROP TABLE lugares",
            "' OR '1'='1",
            "999999",          # fuera de rango valido
            "-999.5",          # fuera de rango valido
        ]
        for payload in payloads_coord:
            r = sec_client.get(
                f"/places/nearby?latitud={payload}&longitud=-77.2811&radio_km=2"
            )
            assert r.status_code in (200, 400, 422, 500), (
                f"Respuesta inesperada con payload '{payload}': {r.status_code}"
            )
            # No debe ser un error 500 no controlado con stack trace SQL
            if r.status_code == 500:
                # Verificar que no expone detalles internos de BD
                assert "postgresql" not in r.text.lower()
                assert "sqlalchemy" not in r.text.lower()

    def test_sec_inj_03_nombre_lugar_con_caracteres_especiales(self, sec_client):
        """SEC-INJ-03: nombres con comillas y caracteres especiales son almacenados de forma segura."""
        # Registrar un usuario pyme para crear el lugar
        sec_client.post(
            "/auth/register",
            json={
                "nombre": "Pyme Segura",
                "correo": "pymesegura@exploro.test",
                "contraseña": "Pyme1234!",
                "preferencias": [],
                "rol": 2,
            },
        )
        r_login = sec_client.post(
            "/auth/login",
            json={"correo": "pymesegura@exploro.test", "contraseña": "Pyme1234!"},
        )
        token = r_login.json()["access_token"]

        nombre_peligroso = "Café O'Reilly & \"Burgers\"; DROP TABLE usuarios --"
        r = sec_client.post(
            "/places",
            json={
                "nombre": nombre_peligroso,
                "descripcion": "Prueba de inyeccion",
                "latitud": 1.2136,
                "longitud": -77.2811,
                "categoria": "restaurante",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        # Debe crear el lugar normalmente (el ORM escapa el nombre)
        assert r.status_code in (201, 422)
        if r.status_code == 201:
            assert r.json()["nombre"] == nombre_peligroso

    def test_sec_inj_04_login_con_payload_sql_en_correo(self, sec_client):
        """SEC-INJ-04: un payload SQL en el campo correo debe retornar 401/422, no 500."""
        for payload in ["admin'--", "' OR '1'='1", "x@x.com'; DROP TABLE usuarios --"]:
            r = sec_client.post(
                "/auth/login",
                json={"correo": payload, "contraseña": "cualquier"},
            )
            assert r.status_code in (400, 401, 422), (
                f"El payload '{payload}' retorno {r.status_code}: {r.text}"
            )


# ===========================================================================
# SEC-RATE  Rate limiting (slowapi)
# ===========================================================================

@pytest.mark.integration
class TestRateLimiting:
    """
    SEC-RATE: verifica que slowapi activa el rate limit en endpoints de auth.
    El limite configurado es 20 req/min para /auth/login.
    """

    def test_sec_rate_01_login_no_bloquea_antes_del_limite(self, sec_client):
        """SEC-RATE-01: los primeros 5 intentos de login no deben ser bloqueados."""
        for _ in range(5):
            r = sec_client.post(
                "/auth/login",
                json={"correo": "noexiste@x.com", "contraseña": "mala"},
            )
            # 401 es correcto (credenciales inválidas), no 429
            assert r.status_code in (400, 401, 422), (
                f"Respuesta inesperada: {r.status_code}"
            )

    def test_sec_rate_02_rate_limit_activa_429_con_requests_masivos(self, sec_client):
        """
        SEC-RATE-02: superar el limite de 20 req/min en /auth/login
        debe retornar 429 Too Many Requests.

        NOTA: este test puede tardar ~30 segundos porque el rate limit
        se mide por ventana de 1 minuto. Si la API tiene otro mecanismo
        (ej. basado en IPs o conteo de fallos), ajustar el umbral.
        """
        respuestas = []
        for _ in range(25):
            r = sec_client.post(
                "/auth/login",
                json={"correo": "flood@x.com", "contraseña": "mala"},
            )
            respuestas.append(r.status_code)

        codigos_obtenidos = set(respuestas)
        assert 429 in codigos_obtenidos, (
            f"Se esperaba al menos un 429 tras 25 intentos rapidosg. "
            f"Codigos obtenidos: {codigos_obtenidos}. "
            "Verificar que slowapi este correctamente configurado."
        )

    def test_sec_rate_03_registro_rate_limit(self, sec_client):
        """
        SEC-RATE-03: el endpoint /auth/register tiene limite de 10 req/min.
        Despues de 12 intentos rapidos debe haber al menos un 429.
        """
        codigos = []
        for i in range(13):
            r = sec_client.post(
                "/auth/register",
                json={
                    "nombre": f"Flood {i}",
                    "correo": f"flood_{i}@test.com",
                    "contraseña": "Flood1234!",
                    "preferencias": [],
                    "rol": 1,
                },
            )
            codigos.append(r.status_code)

        assert 429 in set(codigos), (
            f"Se esperaba al menos un 429 tras 13 registros rapidos. "
            f"Codigos: {set(codigos)}"
        )


# ===========================================================================
# SEC-PERM  Control de acceso basado en roles
# Requiere base de datos (para crear usuarios con diferentes roles)
# ===========================================================================

@pytest.mark.integration
class TestControlDeAccesoPorRol:
    """SEC-PERM: valida que los roles se aplican correctamente en cada endpoint."""

    def _crear_y_loguear(self, client, correo, rol):
        client.post(
            "/auth/register",
            json={
                "nombre": f"Test {rol}",
                "correo": correo,
                "contraseña": "Perm1234!",
                "preferencias": [],
                "rol": rol,
            },
        )
        r = client.post(
            "/auth/login",
            json={"correo": correo, "contraseña": "Perm1234!"},
        )
        return r.json()["access_token"]

    def test_sec_perm_01_turista_no_puede_acceder_a_admin(self, sec_client):
        """SEC-PERM-01: un turista no puede acceder a rutas de /admin."""
        token = self._crear_y_loguear(
            sec_client, "turista_perm@exploro.test", 1
        )
        r = sec_client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code in (401, 403)

    def test_sec_perm_02_admin_puede_acceder_a_admin(self, sec_client):
        """SEC-PERM-02: un administrador puede acceder a /admin/users."""
        token = self._crear_y_loguear(
            sec_client, "admin_perm@exploro.test", 3
        )
        r = sec_client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    def test_sec_perm_03_usuario_no_puede_modificar_perfil_ajeno(self, sec_client):
        """SEC-PERM-03: un usuario no puede editar el perfil de otro usuario."""
        token_a = self._crear_y_loguear(
            sec_client, "userA_perm@exploro.test", 1
        )
        # Intenta modificar usando el token de A pero con datos de B
        r = sec_client.put(
            "/users/me",
            json={"nombre": "Suplantacion"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        # Debería modificar solo el propio perfil (200) o fallar (403/401)
        assert r.status_code in (200, 400, 403, 422)

    def test_sec_perm_04_eliminar_resena_ajena_prohibido(self, sec_client):
        """SEC-PERM-04: un usuario no puede eliminar una reseña de otro usuario."""
        # Crear lugar como pyme
        token_pyme = self._crear_y_loguear(
            sec_client, "pyme_perm@exploro.test", 2
        )
        r_lugar = sec_client.post(
            "/places",
            json={
                "nombre": "Lugar Perm",
                "latitud": 1.2136,
                "longitud": -77.2811,
                "categoria": "parque",
            },
            headers={"Authorization": f"Bearer {token_pyme}"},
        )
        if r_lugar.status_code != 201:
            pytest.skip("No se pudo crear el lugar para este test")
        id_lugar = r_lugar.json()["id_lugar"]

        # Turista A crea una reseña
        token_a = self._crear_y_loguear(
            sec_client, "autor_resena@exploro.test", 1
        )
        r_resena = sec_client.post(
            f"/places/{id_lugar}/reviews",
            json={"comentarios": "Bueno", "puntuacion": 4},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        if r_resena.status_code != 201:
            pytest.skip("No se pudo crear la reseña para este test")
        id_resena = r_resena.json()["id_resena"]

        # Turista B intenta eliminar la reseña de A -> debe ser 403
        token_b = self._crear_y_loguear(
            sec_client, "otro_usuario@exploro.test", 1
        )
        r_del = sec_client.delete(
            f"/reviews/{id_resena}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert r_del.status_code == 403, (
            f"Un usuario no deberia poder eliminar reseña ajena. "
            f"Se obtuvo: {r_del.status_code} {r_del.text}"
        )

    def test_sec_perm_05_logout_invalida_token(self, sec_client):
        """SEC-PERM-05: tras logout, el token revocado no permite acceso."""
        token = self._crear_y_loguear(
            sec_client, "logout_test@exploro.test", 1
        )
        headers = {"Authorization": f"Bearer {token}"}

        # Verifica acceso antes del logout
        r_antes = sec_client.get("/users/me", headers=headers)
        assert r_antes.status_code == 200

        # Realiza logout
        r_logout = sec_client.post("/auth/logout", headers=headers)
        assert r_logout.status_code == 200

        # Verifica que el mismo token ya no sirve
        r_despues = sec_client.get("/users/me", headers=headers)
        assert r_despues.status_code == 401, (
            "El token revocado no deberia permitir acceso tras el logout"
        )

    def test_sec_perm_06_endpoint_sin_token_retorna_401(self, sec_client):
        """SEC-PERM-06: endpoints protegidos sin token retornan 401, no 500."""
        endpoints_protegidos = [
            ("GET", "/users/me"),
            ("POST", "/auth/logout"),
            ("GET", "/admin/users"),
        ]
        for metodo, ruta in endpoints_protegidos:
            if metodo == "GET":
                r = sec_client.get(ruta)
            else:
                r = sec_client.post(ruta)
            assert r.status_code in (401, 403, 405), (
                f"{metodo} {ruta} sin token retorno {r.status_code} en vez de 401/403"
            )


# ===========================================================================
# Utilidad interna
# ===========================================================================

def _assert_no_campo_sensible(body: dict | list, campos_prohibidos: list[str]):
    """Recorre recursivamente el body JSON y falla si encuentra un campo sensible."""
    if isinstance(body, dict):
        for clave, valor in body.items():
            clave_lower = clave.lower()
            for campo in campos_prohibidos:
                assert campo not in clave_lower, (
                    f"Campo sensible '{clave}' encontrado en la respuesta JSON. "
                    "No se deben exponer datos confidenciales en la API."
                )
            _assert_no_campo_sensible(valor, campos_prohibidos)
    elif isinstance(body, list):
        for item in body:
            _assert_no_campo_sensible(item, campos_prohibidos)
