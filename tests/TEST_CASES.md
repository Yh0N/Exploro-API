# Tabla de Casos de Prueba – Exploro API
**Proyecto:** Exploro API – Recomendaciones Turísticas Locales  
**Versión:** 1.0 | **Fecha:** 2026-05-22  
**Alcance:** Pruebas Unitarias, Integración, Rendimiento y Seguridad

---

## Leyenda de Estado

| Símbolo | Significado |
|---------|-------------|
| ✅ | Implementado y pasando |
| 🔄 | Implementado, pendiente de ejecutar |
| ❌ | Fallando |
| ⏭️ | Skipped (requiere recursos externos) |

---

## A. PRUEBAS UNITARIAS

### A.1 – Servicio de Autenticación (`tests/unit/test_auth_service.py`, `test_security.py`)

| ID | Descripción | Precondición | Pasos | Resultado Esperado | Archivo | Estado |
|----|-------------|-------------|-------|-------------------|---------|--------|
| U-AUTH-01 | Registro con email duplicado lanza 400 | BD simulada con usuario existente | `registrar_usuario(db, datos_duplicados)` | `HTTPException(400)` | `test_auth_service.py` | ✅ |
| U-AUTH-02 | Login con usuario inexistente lanza 401 | BD simulada sin usuarios | `login_usuario(db, credenciales)` | `HTTPException(401)` | `test_auth_service.py` | ✅ |
| U-AUTH-03 | Login con password incorrecta lanza 401 | Usuario existe, verify_password mockeado a False | `login_usuario(db, credenciales_malas)` | `HTTPException(401)` | `test_auth_service.py` | ✅ |
| U-AUTH-04 | Logout persiste token en lista negra | Token válido, usuario autenticado | `logout_usuario(db, token, usuario)` | `db.add()` y `db.commit()` llamados | `test_auth_service.py` | ✅ |
| U-AUTH-05 | Hash de contraseña produce bcrypt válido | Ninguna | `hash_password("clave")` | Hash distinto al original, verificable | `test_security.py` | ✅ |
| U-AUTH-06 | JWT generado contiene sub y exp | Ninguna | `create_access_token({"sub": "x"})` | Payload con `sub` y `exp` válidos | `test_security.py` | ✅ |
| U-AUTH-07 | JWT inválido lanza 401 | Ninguna | `verify_token("cadena_invalida")` | `HTTPException(401)` | `test_security.py` | ✅ |
| U-AUTH-08 | Token revocado deniega acceso | Token en `tokens_revocados` | `get_current_user()` con token revocado | `HTTPException(401)` | `test_security.py` | ✅ |
| U-AUTH-09 | require_role permite rol correcto | Usuario con rol `administrador` | Acceder a ruta admin con rol correcto | HTTP 200 | `test_security.py` | ✅ |
| U-AUTH-10 | require_role deniega rol incorrecto | Usuario con rol `usuario_regular` | Acceder a ruta admin con rol turista | HTTP 403 | `test_security.py` | ✅ |

### A.2 – Servicio de Reseñas (`tests/unit/test_review_service.py`, `test_review_service_extended.py`)

| ID | Descripción | Precondición | Pasos | Resultado Esperado | Archivo | Estado |
|----|-------------|-------------|-------|-------------------|---------|--------|
| U-REV-01 | Reseña en lugar inexistente lanza 404 | BD sin lugar | `crear_reseña(db, 999, datos, usuario)` | `HTTPException(404)` | `test_review_service.py` | ✅ |
| U-REV-02 | Reseña duplicada lanza 400 | Usuario ya reseñó el lugar | `crear_reseña(db, id_lugar, datos, usuario)` | `HTTPException(400)` | `test_review_service.py` | ✅ |
| U-REV-03 | Calificación promedio se calcula con AVG | 3 reseñas con puntuaciones [3,4,5] | Consultar promedio del lugar | `4.0` (promedio aritmético) | `test_review_service_extended.py` | ✅ |
| U-REV-04 | Eliminar reseña propia funciona | Usuario es autor de la reseña | `eliminar_reseña(db, id, usuario_autor)` | `{"message": "..."}` sin excepción | `test_review_service_extended.py` | ✅ |
| U-REV-05 | Admin puede eliminar cualquier reseña | Usuario tiene rol=3 | `eliminar_reseña(db, id, admin)` | Eliminación exitosa | `test_review_service_extended.py` | ✅ |
| U-REV-06 | Tercero no puede eliminar reseña ajena | Usuario no es autor ni admin | `eliminar_reseña(db, id, otro_usuario)` | `HTTPException(403)` | `test_review_service_extended.py` | ✅ |
| U-REV-07 | Reseña con puntuación 6 rechazada | Ninguna | Crear reseña con `puntuacion=6` | `ValidationError` Pydantic | `test_review_service_extended.py` | ✅ |
| U-REV-08 | Reseña con puntuación 0 rechazada | Ninguna | Crear reseña con `puntuacion=0` | `ValidationError` Pydantic | `test_review_service_extended.py` | ✅ |

### A.3 – Servicio de Lugares (`tests/unit/test_place_service.py`, `test_place_service_update.py`)

| ID | Descripción | Precondición | Pasos | Resultado Esperado | Archivo | Estado |
|----|-------------|-------------|-------|-------------------|---------|--------|
| U-LUG-01 | Crear lugar válido retorna datos completos | Usuario autenticado | `crear_lugar(db, datos, usuario)` | Dict con `id_lugar` y nombre | `test_place_service.py` | ✅ |
| U-LUG-02 | Lugar inexistente lanza 404 | BD sin el lugar | `obtener_lugar(db, 999)` | `HTTPException(404)` | `test_place_service.py` | ✅ |
| U-LUG-03 | Filtrado por categoría retorna solo esa categoría | 3 lugares de distinta categoría | `listar_lugares(db, categoria="museo")` | Solo lugares con `categoria="museo"` | `test_place_service.py` | ✅ |
| U-LUG-04 | Actualizar lugar con datos válidos | Lugar existente, usuario propietario | `actualizar_lugar(db, id, datos, usuario)` | Datos actualizados en la respuesta | `test_place_service_update.py` | ✅ |
| U-LUG-05 | Eliminar lugar inexistente lanza 404 | Ninguna | `eliminar_lugar(db, 999, usuario)` | `HTTPException(404)` | `test_place_service.py` | ✅ |
| U-LUG-06 | Calificación mínima filtra correctamente | Lugares con distintos promedios | `listar_lugares(db, calificacion_min=4)` | Solo lugares con promedio ≥ 4 | `test_place_service.py` | ✅ |

### A.4 – Motor de Recomendaciones (`tests/unit/test_recommendation_service.py`)

| ID | Descripción | Precondición | Pasos | Resultado Esperado | Archivo | Estado |
|----|-------------|-------------|-------|-------------------|---------|--------|
| U-REC-01 | Usuario con preferencias prioriza esas categorías | Usuario con `preferencias=["museo"]` | `obtener_recomendaciones(db, usuario, ...)` | Museos tienen score_preferencia=1.0 | `test_recommendation_service.py` | ✅ |
| U-REC-02 | Usuario sin preferencias retorna más populares | Usuario con `preferencias=[]` | `obtener_recomendaciones(db, usuario, ...)` | Lista ordenada por popularidad | `test_recommendation_service.py` | ✅ |
| U-REC-03 | Lugares ya reseñados no se recomiendan | Usuario reseñó lugar X | `obtener_recomendaciones(db, usuario, ...)` | Lugar X ausente en la lista | `test_recommendation_service.py` | ✅ |
| U-REC-04 | Score de distancia mayor para lugares cercanos | Coordenadas del usuario definidas | Comparar scores de lugares a distintas distancias | Lugar a 0.5 km > lugar a 5 km | `test_recommendation_service.py` | ✅ |
| U-REC-05 | Score bayesiano da menos peso a lugar con 1 reseña | Comparar lugar con 1 reseña vs 10 reseñas | `_score_popularidad(5.0, 1, 10)` vs `_score_popularidad(4.5, 10, 10)` | Score del de 10 reseñas puede ser mayor | `test_recommendation_service.py` | ✅ |
| U-REC-06 | Novedad penaliza lugares ya recomendados | Lugar recomendado 5 veces | `_score_novedad(5)` | `0.0` (penalización máxima) | `test_recommendation_service.py` | ✅ |

### A.5 – Validadores de Schemas (`tests/unit/test_schemas_smoke.py`)

| ID | Descripción | Precondición | Pasos | Resultado Esperado | Archivo | Estado |
|----|-------------|-------------|-------|-------------------|---------|--------|
| U-SCH-01 | UserCreate válido se instancia correctamente | Ninguna | `UserCreate(nombre=..., correo=..., contraseña=...)` | Objeto sin errores | `test_schemas_smoke.py` | ✅ |
| U-SCH-02 | Correo inválido lanza ValidationError | Ninguna | `UserCreate(correo="no-es-email")` | `ValidationError` | `test_schemas_smoke.py` | ✅ |
| U-SCH-03 | PlaceCreate sin latitud/longitud es válido | Ninguna | `PlaceCreate(nombre=..., categoria=...)` | Objeto instanciado (coords opcionales) | `test_schemas_smoke.py` | ✅ |
| U-SCH-04 | ReviewCreate con puntuación fuera de rango lanza error | Ninguna | `ReviewCreate(puntuacion=0)` y `ReviewCreate(puntuacion=6)` | `ValidationError` en ambos | `test_schemas_smoke.py` | ✅ |
| U-SCH-05 | UserUpdate con campos opcionales funciona | Ninguna | `UserUpdate(nombre="Solo nombre")` | Objeto válido sin error | `test_schemas_smoke.py` | ✅ |

---

## B. PRUEBAS DE INTEGRACIÓN

### B.1 – Autenticación (`tests/integration/test_api_postgis.py`)

| ID | Descripción | Precondición | Pasos | Resultado Esperado | Estado |
|----|-------------|-------------|-------|-------------------|--------|
| I-AUTH-01 | Registro exitoso retorna 201 | BD limpia | `POST /auth/register` con datos válidos | HTTP 201, `id_usuario` en respuesta | ✅ |
| I-AUTH-02 | Login con credenciales válidas retorna JWT | Usuario registrado | `POST /auth/login` con form data | HTTP 200, `access_token` en respuesta | ✅ |
| I-AUTH-03 | Login con credenciales inválidas retorna 401 | Ninguna | `POST /auth/login` con password errónea | HTTP 401 | ✅ |
| I-AUTH-04 | Ruta protegida sin JWT retorna 401 | Ninguna | `GET /users/me` sin Authorization header | HTTP 401 o 403 | ✅ |
| I-AUTH-05 | Logout revoca el token (HTTP 200) | Usuario autenticado | `POST /auth/logout` con token válido | HTTP 200 | ✅ |
| I-AUTH-06 | Token revocado deniega acceso posterior | Token en lista negra | `GET /users/me` con token post-logout | HTTP 401 | ✅ |

### B.2 – Usuarios (`tests/integration/test_api_postgis.py`)

| ID | Descripción | Precondición | Pasos | Resultado Esperado | Estado |
|----|-------------|-------------|-------|-------------------|--------|
| I-USR-01 | GET /users/me retorna perfil del usuario | Usuario autenticado | `GET /users/me` con JWT válido | HTTP 200, `id_usuario` y `nombre` | ✅ |
| I-USR-02 | PUT /users/me actualiza nombre y biografía | Usuario autenticado | `PUT /users/me` con `{"nombre": "Nuevo"}` | HTTP 200, datos actualizados | ✅ |
| I-USR-03 | GET /users/{id} retorna perfil público | Usuario existente | `GET /users/{id}` sin autenticación | HTTP 200 con campos públicos | ✅ |

### B.3 – Lugares (`tests/integration/test_api_postgis.py`)

| ID | Descripción | Precondición | Pasos | Resultado Esperado | Estado |
|----|-------------|-------------|-------|-------------------|--------|
| I-LUG-01 | Crear lugar como pyme retorna 201 | Usuario con rol=pyme | `POST /places` con datos válidos | HTTP 201, `id_lugar` retornado | ✅ |
| I-LUG-02 | Coordenadas inválidas retornan 422 | Ninguna | `POST /places` con `latitud=999` | HTTP 422 | 🔄 |
| I-LUG-03 | GET /places retorna lista paginada | Lugar aprobado existe | `GET /places` | HTTP 200, lista JSON | ✅ |
| I-LUG-04 | Filtro por categoría funciona | Lugares de distintas categorías | `GET /places?categoria=museo` | Solo museos en la respuesta | ✅ |
| I-LUG-05 | GET /places/{id} retorna detalle | Lugar existe | `GET /places/{id}` | HTTP 200, datos completos | ✅ |
| I-LUG-06 | PUT /places/{id} actualiza correctamente | Propietario autenticado | `PUT /places/{id}` con datos nuevos | HTTP 200, nombre actualizado | ✅ |
| I-LUG-07 | GET /places/nearby devuelve lugares en radio | Lugar con ubicación PostGIS | `GET /places/nearby?latitud=1.21&longitud=-77.28&radio_km=5` | HTTP 200, lugares dentro del radio | ✅ |
| I-LUG-08 | Admin puede aprobar lugar pendiente | Admin autenticado, lugar con aprobado=False | `PUT /admin/places/{id}/approve` | HTTP 200, `aprobado=true` | ✅ |

### B.4 – Reseñas (`tests/integration/test_api_postgis.py`)

| ID | Descripción | Precondición | Pasos | Resultado Esperado | Estado |
|----|-------------|-------------|-------|-------------------|--------|
| I-REV-01 | Crear reseña retorna 201 | Usuario y lugar existentes | `POST /places/{id}/reviews` | HTTP 201, `id_resena` retornado | ✅ |
| I-REV-02 | Promedio del lugar se actualiza tras reseña | Lugar con 0 reseñas | Crear reseña con puntuación 5 | Promedio calculado con AVG | ✅ |
| I-REV-03 | Listar reseñas de un lugar | Reseñas existentes | `GET /places/{id}/reviews` | HTTP 200, lista con comentarios | ✅ |
| I-REV-04 | Admin elimina reseña ajena | Admin autenticado | `DELETE /reviews/{id}` | HTTP 200 | ✅ |
| I-REV-05 | Usuario elimina propia reseña | Autor de la reseña | `DELETE /reviews/{id_propio}` | HTTP 200 | 🔄 |
| I-REV-06 | Usuario no puede eliminar reseña ajena | Tercero autenticado | `DELETE /reviews/{id_ajeno}` | HTTP 403 | ✅ |

### B.5 – Recomendaciones (`tests/integration/test_api_postgis.py`)

| ID | Descripción | Precondición | Pasos | Resultado Esperado | Estado |
|----|-------------|-------------|-------|-------------------|--------|
| I-REC-01 | Recomendaciones personalizadas requieren JWT | Sin autenticación | `GET /recommendations` sin token | HTTP 401 o lista anónima | ✅ |
| I-REC-02 | Recomendaciones incluyen `score_recomendacion` | Usuario autenticado, lugar existe | `GET /recommendations?latitud=1.21&longitud=-77.28&radio_km=10` | HTTP 200, campo `score_recomendacion` presente | ✅ |
| I-REC-03 | Recomendaciones populares disponibles sin auth | Lugar aprobado con reseñas | `GET /recommendations/popular` | HTTP 200, lista ordenada por popularidad | ✅ |
| I-REC-04 | Recomendaciones cercanas (PostGIS) | Lugar con coordenadas | `GET /recommendations/nearby?latitud=...` | HTTP 200, lugares dentro del radio | ✅ |

### B.6 – Admin (`tests/integration/test_api_postgis.py`)

| ID | Descripción | Precondición | Pasos | Resultado Esperado | Estado |
|----|-------------|-------------|-------|-------------------|--------|
| I-ADM-01 | GET /admin/users retorna todos los usuarios | Admin autenticado, ≥1 usuario | `GET /admin/users` con token admin | HTTP 200, lista de usuarios | ✅ |
| I-ADM-02 | Turista no puede acceder a /admin/users | Turista autenticado | `GET /admin/users` con token de turista | HTTP 403 | ✅ |
| I-ADM-03 | GET /admin/places lista pendientes | Lugar con `aprobado=False` | `GET /admin/places` con token admin | HTTP 200, incluye lugar pendiente | ✅ |

---

## C. PRUEBAS DE RENDIMIENTO

### C.1 – Escenario 1: Listado de lugares (50 VU × 5 min)

| ID | Descripción | Configuración | Métrica | Umbral | Archivo |
|----|-------------|--------------|---------|--------|---------|
| P-E1-01 | Latencia p95 en GET /places | 50 VU, 5 min | p95 latencia | < 500 ms | `locustfile.py` |
| P-E1-02 | Latencia p99 en GET /places | 50 VU, 5 min | p99 latencia | < 2000 ms | `locustfile.py` |
| P-E1-03 | Error rate GET /places | 50 VU, 5 min | % errores | < 1% | `locustfile.py` |
| P-E1-04 | Throughput (RPS) GET /places | 50 VU, 5 min | req/seg | > 20 RPS | `locustfile.py` |

### C.2 – Escenario 2: Login + Recomendaciones (100 VU × 3 min)

| ID | Descripción | Configuración | Métrica | Umbral | Archivo |
|----|-------------|--------------|---------|--------|---------|
| P-E2-01 | Latencia p95 flujo completo | 100 VU, 3 min | p95 total | < 2000 ms (RNF2) | `locustfile.py` |
| P-E2-02 | Latencia p99 flujo completo | 100 VU, 3 min | p99 total | < 3000 ms (RNF2) | `locustfile.py` |
| P-E2-03 | Error rate flujo autenticado | 100 VU, 3 min | % errores | < 1% | `locustfile.py` |
| P-E2-04 | Latencia p95 de POST /auth/login | 100 VU, 3 min | p95 login | < 1000 ms | `locustfile.py` |
| P-E2-05 | Latencia p95 de GET /recommendations | 100 VU, 3 min | p95 recs | < 2000 ms | `locustfile.py` |

### C.3 – Escenario 3: Pico geoespacial (0→200 VU en 2 min)

| ID | Descripción | Configuración | Métrica | Umbral | Archivo |
|----|-------------|--------------|---------|--------|---------|
| P-E3-01 | Latencia p95 GET /places/nearby en pico | 200 VU, ramp-up 2 min | p95 nearby | < 2000 ms | `locustfile.py` |
| P-E3-02 | Latencia p99 GET /places/nearby en pico | 200 VU, meseta 1 min | p99 nearby | < 3000 ms | `locustfile.py` |
| P-E3-03 | Error rate durante pico | 200 VU | % errores | < 1% | `locustfile.py` |
| P-E3-04 | Sistema se estabiliza tras cool-down | Descenso a 0 VU | Error rate vuelve a 0% | < 0.1% | `locustfile.py` |

---

## D. PRUEBAS DE SEGURIDAD

### D.1 – JWT y Tokens (`tests/security/test_security_automated.py`)

| ID | Descripción | Precondición | Pasos | Resultado Esperado | Estado |
|----|-------------|-------------|-------|-------------------|--------|
| S-JWT-01 | Token malformado retorna 401 | Ninguna | `verify_token("cadena.invalida")` | `HTTPException(401)` | ✅ |
| S-JWT-02 | Token expirado retorna 401 | Ninguna | Token con `exp` en el pasado | `HTTPException(401)` | ✅ |
| S-JWT-03 | Payload sin `sub` rechazado | Ninguna | Token sin campo `sub` | Error 401/422 | ✅ |
| S-JWT-04 | Token con firma corrupta retorna 401 | Ninguna | Modificar segmento de payload | `HTTPException(401)` | ✅ |
| S-JWT-05 | Token revocado deniega acceso | Token en DB blacklist | `get_current_user()` | HTTP 401 | ✅ |
| S-JWT-06 | Ruta sin token retorna 401 | Ninguna | GET sin Authorization header | HTTP 401/403 | ✅ |
| S-JWT-07 | Hash bcrypt no es reversible | Ninguna | Comparar `hash_password(x)` con `x` | Hash ≠ plaintext | ✅ |
| S-JWT-08 | Dos hashes de la misma clave son distintos (salt) | Ninguna | `hash_password(x) != hash_password(x)` | True (salt aleatorio) | ✅ |

### D.2 – Exposición de datos sensibles (`tests/security/test_security_automated.py`)

| ID | Descripción | Precondición | Pasos | Resultado Esperado | Estado |
|----|-------------|-------------|-------|-------------------|--------|
| S-RESP-01 | POST /auth/register no expone contraseña | BD disponible | Inspeccionar body de respuesta | Sin campos `contraseña`, `hash`, `password` | ✅ |
| S-RESP-02 | POST /auth/login no expone hash | BD disponible | Inspeccionar body de respuesta | Solo `access_token` y `token_type` | ✅ |
| S-RESP-03 | GET /users/me no expone hash | Usuario autenticado | Inspeccionar respuesta JSON | Sin `hashed_password` ni `contraseña` | ✅ |
| S-RESP-04 | GET /places no expone datos internos de usuario | BD disponible | Inspeccionar cada item de la lista | Sin campos sensibles de usuario | ✅ |

### D.3 – Inyección SQL (`tests/security/test_security_automated.py`)

| ID | Descripción | Precondición | Pasos | Resultado Esperado | Estado |
|----|-------------|-------------|-------|-------------------|--------|
| S-INJ-01 | SQL injection en `?categoria` no rompe API | BD disponible | `GET /places?categoria='; DROP TABLE lugares; --'` | HTTP 200 (lista vacía) o 422, nunca 500 | ✅ |
| S-INJ-02 | Coordenadas malformadas no generan 500 | BD disponible | `GET /places/nearby?latitud='; DROP TABLE` | HTTP 422 o 400 | ✅ |
| S-INJ-03 | Nombre con comillas almacenado de forma segura | Usuario pyme | `POST /places` con nombre `O'Reilly DROP TABLE` | HTTP 201, nombre guardado literalmente | ✅ |
| S-INJ-04 | SQL en campo correo retorna 401/422, no 500 | Ninguna | `POST /auth/login` con `username="' OR 1=1--"` | HTTP 401 o 422 | ✅ |

### D.4 – Rate Limiting (`tests/security/test_security_automated.py`)

| ID | Descripción | Precondición | Pasos | Resultado Esperado | Estado |
|----|-------------|-------------|-------|-------------------|--------|
| S-RATE-01 | 5 intentos de login no son bloqueados | BD disponible | 5 POST /auth/login fallidos | HTTP 401 en todos (no 429) | ✅ |
| S-RATE-02 | 25 intentos rápidos activan rate limit 429 | BD disponible | 25 POST /auth/login en ráfaga | Al menos 1 respuesta HTTP 429 | ✅ |
| S-RATE-03 | Rate limit en /auth/register (10/min) | BD disponible | 13 POST /auth/register en ráfaga | Al menos 1 respuesta HTTP 429 | ✅ |

### D.5 – Control de acceso por rol (`tests/security/test_security_automated.py`)

| ID | Descripción | Precondición | Pasos | Resultado Esperado | Estado |
|----|-------------|-------------|-------|-------------------|--------|
| S-PERM-01 | Turista no accede a /admin/users | Turista autenticado | `GET /admin/users` con token turista | HTTP 403 | ✅ |
| S-PERM-02 | Admin accede a /admin/users | Admin autenticado | `GET /admin/users` con token admin | HTTP 200 | ✅ |
| S-PERM-03 | Usuario no puede modificar perfil ajeno | Dos usuarios distintos | PUT /users/me con token de A afecta solo a A | HTTP 200 (solo propio) o 403 | ✅ |
| S-PERM-04 | Usuario no puede eliminar reseña ajena | Reseña de A, token de B | `DELETE /reviews/{id_de_A}` con token B | HTTP 403 | ✅ |
| S-PERM-05 | Logout invalida token para futuros accesos | Usuario autenticado | Logout → GET /users/me con mismo token | HTTP 401 | ✅ |
| S-PERM-06 | Endpoints protegidos sin token retornan 401 | Ninguna | GET /users/me, POST /auth/logout sin token | HTTP 401 o 403 | ✅ |

---

## Resumen Ejecutivo

| Categoría | Total casos | Implementados | Pendientes | % Cobertura |
|-----------|-------------|---------------|------------|-------------|
| Unitarios – Auth | 10 | 10 | 0 | 100% |
| Unitarios – Reseñas | 8 | 8 | 0 | 100% |
| Unitarios – Lugares | 6 | 6 | 0 | 100% |
| Unitarios – Recomendaciones | 6 | 6 | 0 | 100% |
| Unitarios – Schemas | 5 | 5 | 0 | 100% |
| Integración – Auth | 6 | 6 | 0 | 100% |
| Integración – Usuarios | 3 | 3 | 0 | 100% |
| Integración – Lugares | 8 | 6 | 2 | 75% |
| Integración – Reseñas | 6 | 5 | 1 | 83% |
| Integración – Recomendaciones | 4 | 4 | 0 | 100% |
| Integración – Admin | 3 | 3 | 0 | 100% |
| Rendimiento – E1 | 4 | 4 | 0 | 100% |
| Rendimiento – E2 | 5 | 5 | 0 | 100% |
| Rendimiento – E3 | 4 | 4 | 0 | 100% |
| Seguridad – JWT | 8 | 8 | 0 | 100% |
| Seguridad – Datos sensibles | 4 | 4 | 0 | 100% |
| Seguridad – Inyección SQL | 4 | 4 | 0 | 100% |
| Seguridad – Rate Limiting | 3 | 3 | 0 | 100% |
| Seguridad – RBAC | 6 | 6 | 0 | 100% |
| **TOTAL** | **103** | **100** | **3** | **97%** |

> **Nota Trabajo de Grado:** Los 3 casos pendientes (I-LUG-02, I-LUG-07 validación coords, I-REV-05) 
> requieren ajustes menores en la implementación de validación de coordenadas en el schema 
> `PlaceCreate`. Se recomienda agregar validators de rango para `latitud` (-90..90) y `longitud` 
> (-180..180) con `@field_validator` de Pydantic v2.
