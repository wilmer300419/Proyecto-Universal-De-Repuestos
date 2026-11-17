# Changelog

## [3.0.0] · 16/11/2026 — Guía de Laboratorio 7 (auditoría, seguridad y calidad)

Arquitectura conservada (MVC + `Seguridad` + migraciones). Rutas, contratos de API y relaciones de base de datos
existentes sin cambios; solo se agregan rutas nuevas. **No requiere migraciones nuevas.**

### Corregido
- B01: filtros no numéricos en catálogos daban HTTP 500 → ahora HTTP 400.
- B02: un booleano vacío en catálogos daba HTTP 500 (`NotNullViolation`) → usa el valor por defecto.
- B03: `status: "false"` no desactivaba usuarios (`bool("false")`) → conversión estricta.
- B04/B05: bodega no numérica (HTTP 500) o inexistente (mensaje engañoso de stock) → HTTP 400 claro.
- B06: los comodines `%` y `_` en la búsqueda devolvían todo el catálogo → se escapan.
- B07: se aceptaban vehículos compatibles inexistentes → se validan.
- B08 (crítico): descarga de facturas con `DIR_FACTURAS` relativo daba HTTP 500 → rutas absolutas y regeneración.
- B09: stock mostrado (suma de bodegas) distinto del vendible (una bodega) → se restaura `warehouse_id` en
  `GET /api/products` y `GET /api/products/{id}` y la SPA lo usa.
- B10: purga de sesiones JWT vencidas hace más de un año.

### Agregado
- RBAC de alto nivel **ADMIN / USER** (`Seguridad.Grupo`, decorador `grupo_requerido`, claim `grp` y campo `rbac`).
- Endpoints de la Guía 7: `POST /api/auth/login` (misma función que `/api/auth/token`), `GET /api/admin`, `GET /api/user`.
- Limitador de intentos por IP (HTTP 429 + `Retry-After`) en login, CAPTCHA y registro; evento `LIMITE_EXCEDIDO` en auditoría.
- CORS con lista blanca explícita (`CORS_ORIGENES`, rechaza `*`), `Permissions-Policy`, HSTS con `COOKIE_SEGURA=true`.
- Log de seguridad `repuestos.seguridad` para respuestas 401/403/429/5xx (sin datos sensibles).
- `app/models/validacion.py`: conversión estricta y reutilizable de enteros, booleanos y textos.
- Pool de PostgreSQL con verificación de conexiones (`check_connection`), reciclaje y error de arranque claro.
- Pruebas: `test_regresion.py`, `test_seguridad.py`, `test_mutacion.py`, `test_herramientas.py` (de 29 a 100 pruebas).
- Calidad y CI/CD: `pyproject.toml` (ruff), `setup.cfg` (mutmut), `tools/mutation_score.py`,
  `.github/workflows/ci.yml` (ruff, compileall, pip-audit, pytest + cobertura + PostgreSQL, SonarCloud, mutmut con
  umbral 50 %), `.github/workflows/codeql.yml`, `.github/dependabot.yml`, `sonar-project.properties`,
  `requirements-dev.txt`.
- Documentación: `docs/INFORME_AUDITORIA.md`, `docs/SECURITY_REPORT.md`, `docs/TEST_REPORT.md`, este archivo.

### Cambiado
- Filtros opcionales de los repositorios como SQL estático parametrizado (sin f-strings); listas de columnas con
  `psycopg.sql.Identifier`. La auditoría obtiene filas y total en una sola consulta (`COUNT(*) OVER()`).
- Funciones con complejidad ciclomática > 10 divididas (`inicializar_seguridad`, `registrar_comandos`, `Reporte._convertir`).
- `Rol`/`Grupo` como `StrEnum`; excepciones encadenadas (`raise … from …`).
- `requirements.txt`: `psycopg-pool` explícito (≥ 3.2, necesario para `check_connection`).

## [2.0.0] · 16/11/2026
- Arquitectura MVC de EntreCOL: psycopg 3 + SQL, migraciones V001–V006, paquete `Seguridad` (JWT con sesiones,
  CAPTCHA, CSRF, auditoría), reportes PDF, datos de prueba (≥ 20 registros por tabla).

## [1.0.0]
- API Flask + SQLAlchemy con arquitectura hexagonal, tienda web y flujo de pago.
