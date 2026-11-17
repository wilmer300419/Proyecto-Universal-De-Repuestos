# Universal de Repuestos WG · API y tienda web

Aplicación **Flask + PostgreSQL** con arquitectura **MVC, POO y SOLID** (la misma de EntreCOL+):
SQL parametrizado con **psycopg 3**, migraciones versionadas, paquete de **Seguridad** autónomo
(JWT con sesiones en base de datos, CAPTCHA, bloqueo por intentos, CSRF, roles y auditoría),
reportes con **PDF** y una vista web (tienda + panel por rol) que consume la API JSON.

## Requisitos
- Python 3.11+ y PostgreSQL 14+ (probado con PostgreSQL 16)

## Puesta en marcha
```bash
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

createdb repuestos                                        # o créala desde pgAdmin
cp .env.example .env                                      # Windows: copy .env.example .env
#   Edita .env: DATABASE_URL y genera los dos secretos con
#   python -c "import secrets; print(secrets.token_urlsafe(48))"

flask --app run migrar          # crea el esquema automotriz: tablas, índices, restricciones y vistas
flask --app run cargar-datos    # datos de prueba: >= 20 registros en cada una de las 26 tablas
flask --app run run             # http://127.0.0.1:5000
```
**Alternativa rápida:** `psql -d repuestos -f sql/repuestos_bd.sql` (esquema + vistas + datos + estado de migraciones).
Para empezar de cero: `flask --app run reiniciar-bd` (revierte todo, migra y recarga los datos).

### Usuarios de ejemplo (contraseña `Repuestos#2026`)
| Rol | Usuarios |
|---|---|
| administrador | `admin`, `wgomez` |
| empacador | `pmartinez`, `jramirez`, `lpardo` |
| repartidor | `dmoreno`, `crincon`, `squintero`, `ycardenas` |
| cliente | `lhernandez`, `atorres`, `mlopez`, `jrodriguez`… |

Usuario interno nuevo: `flask --app run crear-usuario <usuario> --rol administrador` (la contraseña se pide oculta).

### Variables de entorno
| Variable | Obligatoria | Uso |
|---|---|---|
| `DATABASE_URL` | Sí | Conexión a PostgreSQL |
| `SECRET_KEY`, `JWT_SECRET_KEY` | Sí (≥ 32 caracteres) | Firma de sesiones y JWT; la app no arranca sin ellas |
| `JWT_EXPIRA_MINUTOS` | No (120) | Vida del token |
| `COOKIE_SEGURA` | No (false) | `true` en HTTPS: cookie `Secure` + HSTS |
| `CORS_ORIGENES` | No (vacío = mismo origen) | Lista blanca separada por comas (`https://…`); `*` no se admite |
| `LIMITE_LOGIN_POR_MINUTO`, `LIMITE_REGISTRO_POR_HORA` | No (10 / 10) | Límite de intentos por IP |
| `IVA`, `DIR_FACTURAS` | No (0.19 / `facturas`) | Tarifa de IVA y carpeta de facturas (se convierte en ruta absoluta) |
> Política de contraseñas: ≥ 10 caracteres con mayúscula, minúscula, número y símbolo; no puede contener el usuario.

## Estructura (MVC)
```
app/
  models/          Modelo: reglas de negocio puras (negocio.py), validación de entradas (validacion.py), errores,
                   metadatos de catálogos, estructura de informes
  repositories/    Modelo: SQL parametrizado (CRUD genérico por metadatos, productos, ventas, reportes sobre vistas)
  services/        Modelo: casos de uso con transacción, validación y auditoría (ventas, entregas, facturas, usuarios…)
  controllers/     Controladores: blueprints JSON delgados (sin SQL)
  reportes/        4 reportes (clase base Reporte) + generador PDF (vista PDF)
  documentos/      Factura electrónica: PDF con QR y XML simplificado (vista PDF)
  templates/ static/   Vista web: SPA de tienda y panel (HTML/CSS/JS sin dependencias)
  core/database.py Pool de conexiones psycopg (única clase que conoce el driver)
  utils/           Fechas, formatos, códigos y JSON
Seguridad/         JWT, sesiones, contraseñas, CAPTCHA, RBAC ADMIN/USER, límite por IP, CSRF y auditoría (no importa `app`)
migraciones/       Ejecutor + versions/V00x__*.up.sql / .down.sql
sql/               repuestos_bd.sql (completo), repuestos_esquema.sql (estructura), datos_prueba.sql y su generador
tests/             Unitarias, especificación, regresión, seguridad, arquitectura e integración (100 pruebas)
tools/             mutation_score.py (umbral del Mutation Score en CI)
docs/              Auditoría, seguridad, pruebas y changelog
.github/           CI, CodeQL y Dependabot
```
**Reglas de dependencia** (verificadas en `tests/test_arquitectura.py`): `models/` no importa Flask ni psycopg,
`Seguridad/` no importa `app`, y los controladores no contienen SQL.

## Migraciones
```bash
python -m migraciones estado        # o: flask --app run estado-migraciones
python -m migraciones migrar
python -m migraciones revertir 1    # baja la última versión
```
| Versión | Contenido |
|---|---|
| V001 catalogos | tipos de documento, departamentos, ciudades, marcas, tipos, cilindrajes, categorías, estados y tipos de venta |
| V002 empresa_personas | empresa, bodegas, personas y usuarios (rol con CHECK, campos de bloqueo) |
| V003 productos_inventario | productos, vehículos, repuestos, inventario (CHECK de cantidades, índice GIN de compatibilidad) |
| V004 ventas | ventas, detalle, pagos (un solo pago aprobado por venta), entregas, facturas |
| V005 seguridad | `sesion_jwt` y `auditoria` |
| V006 vistas | `v_producto_detalle`, `v_venta_resumen`, `v_inventario_detalle`, `v_entrega_detalle`, indicadores |

Cada migración corre en una transacción y no se puede modificar una ya aplicada (checksum).
Todas las tablas viven en el esquema `automotriz` (search_path de la conexión).

## Seguridad
| Tema | Implementación |
|---|---|
| Contraseñas | Política + hash scrypt con sal; hash señuelo para no revelar usuarios por tiempo de respuesta |
| CAPTCHA | Propio (SVG + token firmado de un solo uso), obligatorio en el inicio de sesión |
| JWT | Web: cookie HttpOnly/SameSite=Strict (el JavaScript nunca ve el token). API: `Authorization: Bearer`. Claims: `sub, usr, rol, jti, iat, exp, iss, aud` |
| Sesiones | Tabla `sesion_jwt`: el token solo vale si su sesión existe, está activa y coincide con el navegador. Cerrar sesión, cerrar todas y revocación al cambiar rol, estado o contraseña |
| Fuerza bruta | 5 fallos → bloqueo de 15 min |
| CSRF | Cabecera `X-CSRF-Token` (HMAC por sesión) en toda escritura con cookie |
| Roles | RBAC **ADMIN** (`administrador`) / **USER** (`cliente`, `empacador`, `repartidor`) |
| Límite por IP | Login, CAPTCHA y registro → HTTP 429 con `Retry-After` |
| CORS | Lista blanca explícita (`CORS_ORIGENES`) |
| Auditoría | Tabla `auditoria`: inicios de sesión, ventas, pagos, entregas, facturas, cambios de catálogo y reportes |
| Cabeceras | CSP, `nosniff`, `X-Frame-Options`, `Referrer-Policy`, `Cache-Control: no-store` en la API |

### API JWT · endpoints de la Guía 7
```bash
curl -s localhost:5000/api/auth/captcha                    # {"svg": "...", "token": "..."}  → resolver la imagen
curl -s -X POST localhost:5000/api/auth/login -H "Content-Type: application/json" \
     -d '{"usuario":"admin","password":"Repuestos#2026","captcha_token":"…","captcha":"AB3DE"}'
curl -s localhost:5000/api/admin -H "Authorization: Bearer <access_token>"   # solo ADMIN (USER → 403)
curl -s localhost:5000/api/user  -H "Authorization: Bearer <access_token>"   # USER y ADMIN
curl -s -X POST localhost:5000/api/auth/logout -H "Authorization: Bearer <access_token>"   # revoca esta sesión
```
Detalle de JWT, RBAC y los 10 controles OWASP en `docs/SECURITY_REPORT.md`.

## Endpoints principales
| Módulo | Endpoint | Acceso |
|---|---|---|
| Guía 7 | `POST /api/auth/login`, `GET /api/admin` (ADMIN), `GET /api/user` (USER y ADMIN) | público / RBAC |
| Auth | `GET /api/auth/captcha`, `POST /api/auth/sesion` (web), `POST /api/auth/token` (API), `GET /api/auth/yo`, `POST /api/auth/logout`, `/logout-todas`, `GET /api/auth/sesiones` | público / sesión |
| Usuarios | `POST /api/clientes` (registro), `GET/POST /api/usuarios`, `PUT /api/usuarios/{id}`, `POST /api/usuarios/{id}/cerrar-sesiones`, `GET /api/auditoria` | público / admin |
| Catálogos | `GET/POST/PUT/DELETE /api/{document-types, departments, cities, car-brands, car-types, cylinder-capacities, spare-part-types, spare-part-brands, sale-types, sale-states, companies, warehouses, cars, spare-parts}` | lectura pública, escritura admin |
| Productos | `GET /api/products?q=&car_id=&car_brand_id=&type_id=&warehouse_id=`, `GET /api/cars/{id}/products`, `POST/PUT/DELETE /api/products` | lectura pública, escritura admin |
| Inventario | `GET /api/inventory?low=1`, `POST /api/inventory`, `PUT /api/inventory/{id}` | admin / empacador |
| Ventas | `POST /api/sales`, `GET /api/sales`, `GET /api/sales/{id}`, `POST /api/sales/{id}/payments`, `POST /api/sales/{id}/cancel`, `GET /api/sales/payment-methods` | cliente / admin |
| Despacho | `POST /api/deliveries/{id}/prepare`, `POST .../assign`, `GET /api/deliveries/assigned`, `PATCH .../status`, `GET /api/deliveries/track/{guía}` | por rol |
| Facturación | `POST /api/sales/{id}/invoice` (admin), `GET /api/sales/{id}/invoice`, `GET /api/invoices/{id}/pdf` | admin / dueño |
| Reportes | `GET /api/reports/summary`, `GET /api/reportes`, `GET /api/reportes/{slug}`, `GET /api/reportes/{slug}/pdf` | admin |

## Pruebas y calidad
```bash
pip install -r requirements-dev.txt
createdb repuestos_test           # base EXCLUSIVA para pruebas: se borra y se recrea en cada ejecución
TEST_DATABASE_URL=postgresql://usuario:clave@localhost:5432/repuestos_test pytest -q --cov=app --cov=Seguridad
ruff check .                      # estilo, bugs probables, seguridad (bandit) y complejidad
mutmut run && python tools/mutation_score.py --umbral 50     # mutation testing (configuración en setup.cfg)
```
Sin `TEST_DATABASE_URL` solo se ejecutan las pruebas que no usan base de datos (unitarias, arquitectura,
especificación). Resultados reales en `docs/TEST_REPORT.md`.

## CI/CD (GitHub Actions)
| Workflow | Jobs |
|---|---|
| `ci.yml` | `calidad` (ruff, compileall, pip-audit) → `pruebas` (PostgreSQL 16, pytest + cobertura, SonarCloud + Quality Gate) y `mutacion` (mutmut; **falla si el Mutation Score < 50 %**) |
| `codeql.yml` | CodeQL para Python y JavaScript (push, PR y semanal) |
| `dependabot.yml` | Actualizaciones semanales de pip y GitHub Actions |

**Intervención necesaria:** crear el proyecto en SonarCloud, reemplazar `CAMBIAR_ORGANIZACION` en
`sonar-project.properties`, agregar el secreto `SONAR_TOKEN` y activar Code scanning y Dependabot en
Settings → Code security.

## Producción
`gunicorn "run:app"` detrás de HTTPS y `COOKIE_SEGURA=true`. No subas `.env` al repositorio.
La factura es una representación PDF + XML simplificado; no es el XML UBL firmado ni validado por la DIAN.

## Cómo agregar…
- **Un catálogo:** declarar una `Entidad` en `app/models/catalogo.py` (las rutas se generan solas).
- **Un reporte:** subclase de `Reporte` en `app/reportes/` y registrarla en `registro.py`.
- **Un cambio de esquema:** nueva migración `V007__descripcion.up.sql` / `.down.sql` (nunca editar una aplicada).
