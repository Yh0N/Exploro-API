# Checklist de Seguridad – Exploro API
**Proyecto:** Exploro API – Recomendaciones Turísticas Locales  
**Versión:** 1.0 | **Fecha:** 2026-05-22  
**Revisado por:** Equipo de QA / Trabajo de Grado

---

## Instrucciones de uso

Marcar cada ítem como:
- `[x]` – Cumplido y verificado
- `[ ]` – Pendiente de verificar
- `[N/A]` – No aplica al proyecto

Cada sección incluye el **cómo verificar** y el **resultado esperado**.

---

## 1. Transporte y Cifrado (HTTPS)

| # | Control | Cómo verificar | Resultado esperado | Estado |
|---|---------|----------------|--------------------|--------|
| 1.1 | HTTPS obligatorio en producción | Acceder a `http://` y verificar redirección | Redirige a `https://` (301/302) o bloquea | `[ ]` |
| 1.2 | Certificado TLS válido (no expirado, CA reconocida) | `curl -v https://api.exploro.app` | Cadena de certificados válida | `[ ]` |
| 1.3 | HSTS habilitado (`Strict-Transport-Security`) | Revisar headers de respuesta | Header presente con `max-age >= 31536000` | `[ ]` |
| 1.4 | No se transmiten contraseñas en texto plano | Captura con Wireshark en HTTPS | Datos encriptados, ininteligibles | `[ ]` |
| 1.5 | Cookies con flag `Secure` si se usan | Revisar Set-Cookie en respuestas | Flag `Secure` presente | `N/A` |

---

## 2. Headers de Seguridad HTTP

Verificar con: `curl -I https://api.exploro.app/`

| # | Header | Valor esperado | Estado |
|---|--------|----------------|--------|
| 2.1 | `X-Content-Type-Options` | `nosniff` | `[ ]` |
| 2.2 | `X-Frame-Options` | `DENY` o `SAMEORIGIN` | `[ ]` |
| 2.3 | `Content-Security-Policy` | Política restrictiva definida | `[ ]` |
| 2.4 | `Referrer-Policy` | `strict-origin-when-cross-origin` | `[ ]` |
| 2.5 | `Permissions-Policy` | Desactivar geolocalización innecesaria | `[ ]` |
| 2.6 | `Server` header | No expone versión (`Server: nginx` sin versión) | `[ ]` |
| 2.7 | `X-Powered-By` | Ausente (no expone Python/FastAPI) | `[ ]` |

**Cómo agregar headers en FastAPI:**
```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
```

---

## 3. Configuración CORS

| # | Control | Cómo verificar | Resultado esperado | Estado |
|---|---------|----------------|--------------------|--------|
| 3.1 | No se usa `allow_origins=["*"]` | Revisar `app/main.py` | Lista blanca específica de dominios | `[ ]` |
| 3.2 | Métodos permitidos son mínimos | Revisar `allow_methods` | Solo GET, POST, PUT, DELETE, OPTIONS | `[ ]` |
| 3.3 | Headers permitidos son mínimos | Revisar `allow_headers` | Solo Authorization, Content-Type | `[ ]` |
| 3.4 | Preflight OPTIONS retorna 200/204 | `curl -X OPTIONS -H "Origin: http://evil.com"` | 400/403 para orígenes no permitidos | `[ ]` |

---

## 4. Autenticación JWT

| # | Control | Cómo verificar | Resultado esperado | Estado |
|---|---------|----------------|--------------------|--------|
| 4.1 | SECRET_KEY tiene mínimo 32 caracteres | Revisar `app/core/config.py` | Validación lanzada si < 32 chars | `[x]` |
| 4.2 | Tokens tienen expiración corta (≤60 min) | Revisar `ACCESS_TOKEN_EXPIRE_MINUTES` | Configurado en 60 min o menos | `[x]` |
| 4.3 | Logout invalida el token (blacklist) | Ejecutar `test_sec_perm_05` | Token revocado retorna 401 | `[x]` |
| 4.4 | Token expirado retorna 401 | Ejecutar `test_sec_auth_02` | HTTP 401 con mensaje de error | `[x]` |
| 4.5 | Token modificado retorna 401 | Ejecutar `test_sec_auth_04` | HTTP 401 (firma inválida) | `[x]` |
| 4.6 | Algoritmo HS256 (no `none`) | Revisar `ALGORITHM` en config | `HS256` configurado | `[x]` |
| 4.7 | Refresh token no expuesto en logs | Revisar logs de producción | Ausente en stdout/stderr | `[ ]` |

---

## 5. Control de Acceso por Rol (RBAC)

| # | Control | Cómo verificar | Resultado esperado | Estado |
|---|---------|----------------|--------------------|--------|
| 5.1 | Turista no accede a `/admin/*` | Ejecutar `test_sec_perm_01` | HTTP 403 | `[x]` |
| 5.2 | Admin puede acceder a `/admin/users` | Ejecutar `test_sec_perm_02` | HTTP 200 | `[x]` |
| 5.3 | Solo autor/admin puede eliminar reseña | Ejecutar `test_sec_perm_04` | HTTP 403 para terceros | `[x]` |
| 5.4 | Usuario no puede modificar perfil ajeno | Ejecutar `test_sec_perm_03` | HTTP 403/401 | `[x]` |
| 5.5 | Roles definidos: 1=regular, 2=pyme, 3=admin | Revisar `app/models/user.py` | Enteros usados consistentemente | `[x]` |
| 5.6 | `require_role` valida antes de ejecutar lógica | Revisar dependencias en routers | `Depends(require_role([...]))` en cada ruta protegida | `[x]` |

---

## 6. Protección de Datos Sensibles en Respuestas

| # | Control | Cómo verificar | Resultado esperado | Estado |
|---|---------|----------------|--------------------|--------|
| 6.1 | `contraseña` no aparece en ningún response | Ejecutar `TestNoExposicionDatosSensibles` | Ningún campo con nombre de contraseña | `[x]` |
| 6.2 | `hashed_password` no aparece en responses | Ídem | Ausente en JSON | `[x]` |
| 6.3 | Stack traces no expuestos al cliente | Provocar error 500 intencional | JSON genérico sin traceback Python | `[ ]` |
| 6.4 | IDs internos de BD no permiten enumeración | Probar `/users/9999999` | 404, no 500 | `[ ]` |
| 6.5 | Emails no enumerables (registro duplicado) | POST /register con email existente | 400 con mensaje genérico (no "email ya existe") | `[ ]` |

---

## 7. Inyección SQL y Validación de Entradas

| # | Control | Cómo verificar | Resultado esperado | Estado |
|---|---------|----------------|--------------------|--------|
| 7.1 | SQLAlchemy ORM usa bind params | Revisar queries en servicios | No hay `.format()` ni f-strings con input de usuario en queries | `[x]` |
| 7.2 | Payload SQL en `?categoria` no rompe API | Ejecutar `test_sec_inj_01` | HTTP 200 (lista vacía) o 422 | `[x]` |
| 7.3 | Payload SQL en login retorna 401, no 500 | Ejecutar `test_sec_inj_04` | HTTP 401/422 | `[x]` |
| 7.4 | Validación Pydantic en todos los schemas | Revisar `app/schemas/` | Tipos y constraints definidos | `[x]` |
| 7.5 | Coordenadas validadas (lat -90/90, lon -180/180) | POST /places con coords inválidas | HTTP 422 | `[ ]` |
| 7.6 | Longitud máxima en campos de texto | POST con descripción de 100k chars | HTTP 422 | `[ ]` |
| 7.7 | Upload: solo tipos MIME permitidos | POST /upload con .exe | HTTP 400/422 | `[ ]` |
| 7.8 | Upload: límite de tamaño 5MB | POST /upload con archivo de 10MB | HTTP 413 o 422 | `[x]` |

---

## 8. Rate Limiting y Protección contra Fuerza Bruta

| # | Control | Cómo verificar | Resultado esperado | Estado |
|---|---------|----------------|--------------------|--------|
| 8.1 | Rate limit en `/auth/login` (20/min) | Ejecutar `test_sec_rate_02` | HTTP 429 tras 21+ intentos rápidos | `[x]` |
| 8.2 | Rate limit en `/auth/register` (10/min) | Ejecutar `test_sec_rate_03` | HTTP 429 tras 11+ intentos rápidos | `[x]` |
| 8.3 | Mensaje de rate limit no revela info interna | Revisar body del 429 | Solo mensaje genérico, sin detalles de config | `[ ]` |
| 8.4 | IP real capturada con proxy (X-Forwarded-For) | Verificar config de slowapi | `RealIPMiddleware` o configuración equivalente | `[ ]` |

---

## 9. Gestión de Secretos y Variables de Entorno

| # | Control | Cómo verificar | Resultado esperado | Estado |
|---|---------|----------------|--------------------|--------|
| 9.1 | `.env` no está en control de versiones | `git ls-files .env` | Vacío (no trackeado) | `[x]` |
| 9.2 | `.env.example` no contiene valores reales | Revisar `.env.example` | Solo placeholders (`YOUR_SECRET_HERE`) | `[x]` |
| 9.3 | SECRET_KEY no es el valor de ejemplo/default | Revisar producción | Valor largo y aleatorio | `[ ]` |
| 9.4 | Credenciales de BD no hardcodeadas | `grep -r "password" app/` | Solo referencias a `settings.*` | `[x]` |
| 9.5 | Variables de entorno documentadas | Revisar `README.md` | Lista completa con descripción | `[ ]` |

---

## 10. Logging y Auditoría

| # | Control | Cómo verificar | Resultado esperado | Estado |
|---|---------|----------------|--------------------|--------|
| 10.1 | Contraseñas no se loguean | Revisar código de auth_service | No hay `logger.info(contraseña)` | `[ ]` |
| 10.2 | Tokens JWT no se loguean en texto plano | Buscar `logger` en security.py | Tokens ausentes en logs | `[ ]` |
| 10.3 | Intentos de login fallido son registrados | Revisar logs al fallar login | Evento registrado con IP/hora | `[ ]` |
| 10.4 | Accesos a `/admin` son registrados | Revisar middleware de logging | Cada acceso admin tiene registro | `[ ]` |

---

## 11. Dependencias y Vulnerabilidades Conocidas

| # | Control | Cómo verificar | Resultado esperado | Estado |
|---|---------|----------------|--------------------|--------|
| 11.1 | Sin dependencias con CVEs críticos | `pip audit` o `safety check` | 0 vulnerabilidades críticas | `[ ]` |
| 11.2 | `bcrypt==4.0.1` sin vulnerabilidades | Revisar CVE database | Sin CVEs para esta versión | `[x]` |
| 11.3 | `python-jose` actualizado | `pip show python-jose` | Versión ≥ 3.3.0 | `[x]` |
| 11.4 | FastAPI y Pydantic actualizados | `pip list --outdated` | Sin actualizaciones críticas pendientes | `[ ]` |

**Comandos de auditoría:**
```bash
# Instalar pip-audit
pip install pip-audit

# Auditar dependencias
pip-audit -r requirements.txt

# Con safety
pip install safety
safety check -r requirements.txt
```

---

## 12. Pruebas de Penetración Manuales Recomendadas

Los siguientes tests deben ejecutarse manualmente con herramientas como **Burp Suite**, **OWASP ZAP** o **curl**:

| # | Prueba | Herramienta | Descripción |
|---|--------|-------------|-------------|
| P1 | IDOR (Insecure Direct Object Reference) | curl/Burp | Acceder a `/users/{id_otro}` con token propio |
| P2 | JWT `alg: none` bypass | jwt_tool | Modificar header para `"alg":"none"` |
| P3 | Mass assignment | Burp Repeater | Enviar campos extra en PUT (ej. `"rol": 3`) |
| P4 | Path traversal en upload | curl | Subir archivo con nombre `../../etc/passwd` |
| P5 | XSS reflejado en campos de texto | OWASP ZAP | Inyectar `<script>` en nombre/descripción |
| P6 | Bypass de rate limit con X-Forwarded-For | curl | Cambiar cabecera para evadir límite por IP |

---

## Resumen de Estado

| Categoría | Total | Cumplidos | Pendientes | N/A |
|-----------|-------|-----------|------------|-----|
| Transporte/HTTPS | 5 | 0 | 5 | 0 |
| Headers HTTP | 7 | 0 | 7 | 0 |
| CORS | 4 | 0 | 4 | 0 |
| JWT | 7 | 6 | 1 | 0 |
| RBAC | 6 | 6 | 0 | 0 |
| Datos sensibles | 5 | 1 | 4 | 0 |
| Inyección SQL | 8 | 5 | 3 | 0 |
| Rate Limiting | 4 | 2 | 2 | 0 |
| Secretos | 5 | 3 | 2 | 0 |
| Logging | 4 | 0 | 4 | 0 |
| Dependencias | 4 | 2 | 2 | 0 |
| **TOTAL** | **59** | **25** | **34** | **0** |

> **Nota para el Trabajo de Grado:** Los controles marcados como `[x]` han sido verificados mediante las pruebas automatizadas en `test_security_automated.py`. Los controles `[ ]` requieren verificación manual en el entorno de producción/staging y deben completarse antes de la defensa final.
