# Reporte de seguridad · repuestos_api v3.0.0

## 1. Autenticación JWT

| Aspecto | Implementación | Código |
|---|---|---|
| Login | `POST /api/auth/login` (endpoint de la Guía 7) = `POST /api/auth/token` (misma función, sin duplicar lógica). La vista web usa `POST /api/auth/sesion` (cookie HttpOnly). Todos exigen CAPTCHA (`GET /api/auth/captcha`) | `Seguridad/flask_integracion.py` |
| Emisión | HS256, claims no sensibles `sub, usr, rol, grp, jti, iat, exp, iss, aud`; expiración 120 min (`JWT_EXPIRA_MINUTOS`) | `Seguridad/tokens.py` |
| Validación | Algoritmo fijado (rechaza `alg: none`), firma, `exp`, `iss`, `aud` y claims obligatorios; además la sesión `jti` debe existir en `sesion_jwt`, estar activa y pertenecer al mismo navegador | `ServicioJWT.verificar`, `ServicioAutenticacion.autenticar_token` |
| Revocación | Logout, "cerrar todas", y revocación automática al cambiar rol, estado o contraseña | `Seguridad/servicio.py`, `app/services/usuarios.py` |
| Contraseñas | scrypt con sal (werkzeug); política ≥ 10 caracteres con mayúscula, minúscula, número y símbolo, sin el usuario | `Seguridad/contrasenas.py` |
| Credenciales inválidas | Mismo mensaje para usuario inexistente y clave incorrecta, hash señuelo (mismo tiempo de respuesta), bloqueo de 15 min tras 5 fallos | `ServicioAutenticacion.iniciar_sesion` |

### Flujo de demostración (Guía 7)
```bash
curl -s localhost:5000/api/auth/captcha                                   # {"svg": "...", "token": "..."}
curl -s -X POST localhost:5000/api/auth/login -H "Content-Type: application/json" \
     -d '{"usuario":"admin","password":"Repuestos#2026","captcha_token":"<token>","captcha":"<texto>"}'
# -> {"access_token": "...", "token_type": "Bearer", "expires_in": 7200, "role": "administrador", "rbac": "ADMIN"}
curl -s localhost:5000/api/admin -H "Authorization: Bearer <token ADMIN>"   # 200
curl -s localhost:5000/api/admin -H "Authorization: Bearer <token USER>"    # 403
curl -s localhost:5000/api/user  -H "Authorization: Bearer <token USER>"    # 200 (también ADMIN)
curl -s localhost:5000/api/user                                             # 401
```

## 2. Autorización RBAC

| Grupo RBAC | Roles de negocio | Acceso |
|---|---|---|
| **ADMIN** | `administrador` | `GET /api/admin`, usuarios, auditoría, reportes, escritura de catálogos/productos/inventario, facturación |
| **USER** | `cliente`, `empacador`, `repartidor` | `GET /api/user` y lo propio de su rol: el cliente compra y ve **solo sus** pedidos; el empacador prepara despachos; el repartidor solo actualiza **sus** entregas |

- Decoradores: `grupo_requerido(Grupo.ADMIN | Grupo.USER)` y `rol_requerido(...)` (`Seguridad/decoradores.py`).
- El permiso se decide con el usuario **cargado de la base de datos** en cada petición, no con el claim del token:
  un cambio de rol o una desactivación surte efecto inmediato (`test_cambio_de_rol_surte_efecto_inmediato`).
- Propiedad de los recursos (IDOR): `_visible()` en `app/services/ventas.py` y `ServicioFacturas._autorizado`.

## 3. OWASP Top 10 controls

| # | OWASP category | Control applied | Implementation | Code evidence |
|---|---|---|---|---|
| 1 | A01 Broken Access Control | Role-based access control (ADMIN/USER + business roles) enforced server-side on every endpoint; object-level ownership checks | `grupo_requerido`, `rol_requerido`, `login_requerido` decorators; customers can only read their own sales/invoices; couriers can only update deliveries assigned to them | `Seguridad/decoradores.py`, `app/services/ventas.py` (`_visible`, `avanzar`), tests `test_login_admin_user`, `test_roles`, `test_cliente_no_ve_ventas_ajenas` |
| 2 | A02 Cryptographic Failures | Strong password hashing, signed tokens, secure cookies | scrypt + per-password salt; HS256 JWT with pinned algorithm and a ≥ 32-char secret required at startup; HttpOnly + SameSite=Strict cookie, `Secure` + HSTS when `COOKIE_SEGURA=true`; only the last 4 card digits are stored | `Seguridad/contrasenas.py`, `Seguridad/tokens.py`, `app/config.py`, `app/__init__.py` (`_cabeceras_y_cors`), `app/services/ventas.py` (`pagar`) |
| 3 | A03 Injection | Parameterized SQL only; identifiers from a whitelist; LIKE wildcard escaping; strict input validation | All values travel as psycopg parameters; dynamic column names use `psycopg.sql.Identifier` from the metadata catalog; optional filters are static SQL; `patron_like` escapes `%`/`_`; `validacion.py` rejects malformed numbers/booleans | `app/repositories/*.py`, `app/models/validacion.py`, tests `test_inyeccion_sql_en_busqueda_es_inofensiva`, `test_bug06_*`, ruff rule `S608` = 0 findings |
| 4 | A04 Insecure Design | Business invariants enforced in the database and with row locks | `SELECT … FOR UPDATE` on stock and sales; unique partial index "one approved payment per sale"; CHECK constraints (totals, quantities, states); rate limiting per IP on login/registration | `migraciones/versions/V004__ventas.up.sql`, `app/services/ventas.py`, `Seguridad/limitador.py`, test `test_flujo_completo` (double payment → 409), `test_limite_de_intentos_429` |
| 5 | A05 Security Misconfiguration | Secure defaults and hardened HTTP headers; explicit CORS allowlist | CSP, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, `Cache-Control: no-store` on the API; CORS only for origins listed in `CORS_ORIGENES` (`*` rejected at startup); debug off unless `FLASK_ENV=development`; generic error bodies (no stack traces) | `app/__init__.py`, `app/config.py` (`_origenes`), tests `test_cabeceras_de_seguridad`, `test_cors_solo_lista_blanca`, `test_cors_permite_origen_configurado`, `test_errores_no_filtran_detalles_internos` |
| 6 | A06 Vulnerable and Outdated Components | Automated dependency monitoring and auditing | Dependabot (pip + GitHub Actions, weekly); `pip-audit` step in CI; version ranges with upper bounds in `requirements.txt` | `.github/dependabot.yml`, `.github/workflows/ci.yml` (job `calidad`) |
| 7 | A07 Identification and Authentication Failures | Anti-automation and session management | One-time CAPTCHA; account lockout (5 failures → 15 min); per-IP rate limit (HTTP 429 + `Retry-After`); server-side JWT sessions with revocation; uniform error messages; password policy | `Seguridad/servicio.py`, `Seguridad/captcha.py`, `Seguridad/limitador.py`, tests `test_bloqueo_por_intentos_fallidos`, `test_captcha_reutilizado_se_rechaza`, `test_token_expirado_y_alterado_se_rechazan` |
| 8 | A08 Software and Data Integrity Failures | Integrity of schema changes and of the build pipeline | Migrations are versioned and checksummed (a modified, already-applied migration aborts); CSRF HMAC token on every cookie-authenticated write; CodeQL + CI gates before merge | `migraciones/runner.py`, `Seguridad/flask_integracion.py` (`resolver_usuario`), `.github/workflows/codeql.yml`, test `test_cookie_httponly_csrf_y_logout_revoca` |
| 9 | A09 Security Logging and Monitoring Failures | Audit trail and security event logging without sensitive data | `auditoria` table records logins, failures, lockouts, rate-limit hits, sales, payments, deliveries, invoices, catalog changes and reports; `repuestos.seguridad` logger records every 401/403/429/5xx (method, path, IP, user id — never passwords or tokens) | `Seguridad/repositorio.py` (`RepositorioAuditoria`), `app/__init__.py` (`_registro_de_seguridad`), `GET /api/auditoria`, test `test_catalogo_generico_y_auditoria` |
| 10 | A10 Server-Side Request Forgery | No server-side fetching of user-supplied URLs | The backend performs no outbound HTTP requests; the only external resource (Google Maps iframe) is loaded by the browser and restricted by CSP `frame-src`; `connect-src 'self'` | `app/__init__.py` (`CSP`) |

## 4. Gestión de secretos

- `SECRET_KEY` y `JWT_SECRET_KEY` se leen del entorno (`.env`, ignorado por git) y la app **no arranca** si faltan o
  tienen menos de 32 caracteres. No hay secretos en el repositorio: `.env.example` solo trae los nombres.
- El token de SonarCloud se configura como secreto de GitHub (`SONAR_TOKEN`), nunca en archivos.

## 5. Verificación

Todas las filas con pruebas citadas se ejecutaron (ver `docs/TEST_REPORT.md`). CodeQL, Dependabot y SonarCloud están
**configurados** pero sus resultados solo existen al ejecutarse en GitHub; no se reportan resultados que no se obtuvieron.
