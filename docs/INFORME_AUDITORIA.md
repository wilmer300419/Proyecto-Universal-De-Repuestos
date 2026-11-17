# Informe de auditoría · repuestos_api v3.0.0

Fecha: 16/11/2026 · Alcance: código del repositorio (backend Flask MVC, paquete `Seguridad`, migraciones, SPA).
La arquitectura (MVC + `Seguridad` autónomo + migraciones SQL) se conservó: no se movieron carpetas ni se
cambiaron rutas, contratos de API ni relaciones de la base de datos.

## Método

1. Lectura del código por capas (controladores → servicios → repositorios → SQL).
2. Reproducción de cada sospecha con peticiones HTTP reales contra PostgreSQL 16 (`app.test_client()`).
3. Corrección mínima en la capa responsable.
4. Prueba de regresión (`tests/test_regresion.py`) que falla con el código anterior y pasa con el nuevo.

**Evidencia de regresión:** las primeras 10 pruebas de regresión que usan la base de datos se ejecutaron también
contra la versión anterior (v2): **8 fallaron** (B01–B07, B09) y 2 pasaron (B08 por la forma en que se configuró el
entorno de prueba, B11 porque era una protección ya existente que ahora queda fijada). La prueba de B10 se agregó
después y no se ejecutó contra v2. El fallo de B08 se
reprodujo por separado con `DIR_FACTURAS=facturas` (ruta relativa por defecto): HTTP 500 `FileNotFoundError`.

## Bugs corregidos

| # | Severidad | Síntoma (reproducido) | Causa | Corrección | Prueba de regresión |
|---|---|---|---|---|---|
| B01 | Media | `GET /api/cities?department_id=abc` → **HTTP 500** | `ValueError` del filtro sin capturar en `ServicioCrud.listar` | Se traduce a `ErrorValidacion` (HTTP 400) | `test_bug01_filtro_no_numerico_en_catalogo_da_400` |
| B02 | Media | `POST /api/car-brands {"state": ""}` → **HTTP 500** (`NotNullViolation`) | Un booleano vacío se guardaba como `NULL` en una columna `NOT NULL`; `NotNullViolation` no se manejaba | Valor vacío → valor por defecto del campo; `NotNullViolation` → HTTP 409 | `test_bug02_state_vacio_usa_valor_por_defecto` |
| B03 | **Alta** | `PUT /api/usuarios/{id} {"status": "false"}` dejaba la cuenta **activa** | `bool("false") == True` | Conversión estricta `a_booleano` (`app/models/validacion.py`) | `test_bug03_status_false_desactiva_usuario`, `test_bug03_booleano_estricto` |
| B04 | Media | `POST /api/sales {"company_warehouse_id": "x"}` → **HTTP 500** | `int("x")` sin validar | `ServicioVentas._bodega` con `a_entero` → HTTP 400 | `test_bug04_bodega_no_numerica_da_400` |
| B05 | Baja | Bodega inexistente respondía "Stock insuficiente" | No se validaba la bodega | Se valida que exista y esté activa → HTTP 400 claro | `test_bug05_bodega_inexistente_no_se_reporta_como_stock` |
| B06 | Media | `GET /api/products?q=%` devolvía **todo** el catálogo | Los comodines `%` y `_` del usuario se pasaban a `ILIKE` | `patron_like` escapa `\`, `%` y `_` | `test_bug06_busqueda_con_comodines_es_literal`, `test_bug06_patron_like_escapa_comodines` |
| B07 | Media | Se aceptaban productos compatibles con vehículos inexistentes (`fk_car_product: [99999]`) | El arreglo del ERD no tiene FK | `ServicioProductos._vehiculos` valida contra `car` | `test_bug07_producto_con_vehiculo_inexistente_da_400` |
| B08 | **Crítica** | Con la configuración por defecto (`DIR_FACTURAS=facturas`) la descarga de facturas daba **HTTP 500** | Los PDF se escribían relativos al directorio de trabajo, pero `send_file` resuelve rutas relativas contra `app/` | `Configuracion` y `DocumentosFactura` usan rutas absolutas; rutas relativas antiguas en la BD se regeneran | `test_bug08_dir_facturas_relativo_se_vuelve_absoluto`, `test_bug08_descarga_de_factura_con_ruta_relativa_guardada` |
| B09 | **Alta** | El cliente veía stock suficiente pero el pedido se rechazaba por "Stock insuficiente" | `stock_total` sumaba **todas** las bodegas y la venta descuenta de **una**; además se había perdido el parámetro `warehouse_id` del contrato original de `GET /api/products` | Se restaura `warehouse_id` en `GET /api/products` y `GET /api/products/{id}`; la SPA consulta el stock de la bodega que atiende | `test_bug09_stock_por_bodega` |
| B10 | Baja | La tabla `sesion_jwt` crecía sin límite | Se había quitado la purga de sesiones vencidas | Purga de sesiones vencidas hace más de un año al crear una sesión | `test_bug10_purga_de_sesiones_antiguas` |
| B11 | Baja | Protección ya existente: `amount: true` en un pago | — | `dinero()` rechaza explícitamente booleanos y valores no finitos | `test_bug11_monto_booleano_en_pago_da_400`, `test_bug11_dinero_rechaza_bool_y_no_finitos` |

## Estabilidad y conexión con PostgreSQL

| Cambio | Archivo | Motivo |
|---|---|---|
| `check=ConnectionPool.check_connection`, `max_idle`, `max_lifetime`, `timeout` en el pool | `app/core/database.py` | Antes, una conexión cortada (reinicio de PostgreSQL, red) se entregaba igual y la petición fallaba. Ahora se verifica antes de usarla y se recicla |
| Error claro al no poder conectar al arrancar | `app/core/database.py` | Antes: traza de `PoolTimeout` sin indicar la causa probable |
| Excepciones encadenadas (`raise … from …`) | servicios, modelos, CLI | Conservan la causa original en los logs (regla B904) |

## Mantenibilidad (code smells)

- **SQL dinámico con f-strings eliminado**: los filtros opcionales ahora son consultas estáticas con parámetros
  (`(%(x)s IS NULL OR col = %(x)s)`); las listas de columnas usan `psycopg.sql.Identifier`. Ruff `S608`: 0.
- **Complejidad**: `inicializar_seguridad`, `registrar_comandos` y `Reporte._convertir` superaban complejidad
  ciclomática 10; se dividieron en funciones pequeñas (ruff `C901` con máximo 10: 0 hallazgos).
- **Duplicación**: la conversión de enteros/booleanos/textos que estaba repetida en 4 servicios se centralizó en
  `app/models/validacion.py`.
- **Nombres ambiguos** (`l`), `str, Enum` → `StrEnum`, constantes de SQL reutilizadas.
- Resultado: `ruff check .` (reglas E, W, F, B, S, C90, SIM, UP, PLE, PLW) → **All checks passed**.

## Limitaciones conocidas (no corregidas en esta versión)

- El limitador de intentos por IP vive en memoria del proceso: con varios workers de gunicorn cada uno cuenta por
  separado. Para un límite global se requiere un almacén compartido (Redis) o el proxy inverso.
- El CAPTCHA SVG es legible por un programa (las letras son texto dentro del SVG); es un segundo factor académico.
- La CSP permite `script-src-attr 'unsafe-inline'` porque la SPA usa manejadores `onclick` en el HTML generado.
- SonarCloud, CodeQL y Dependabot quedaron **configurados pero no ejecutados** (requieren el repositorio en GitHub);
  ver `docs/TEST_REPORT.md`.
