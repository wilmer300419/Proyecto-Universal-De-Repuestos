# Reporte de pruebas · repuestos_api v3.0.0

Ejecución: 16/11/2026, Python 3.13, PostgreSQL 16.15 (local), Linux.

> **Condiciones del entorno donde se ejecutaron (transparencia):** el entorno de la auditoría no tenía acceso a
> internet, por lo que no fue posible instalar `psycopg`, `pytest-cov` ni `mutmut`. Por eso:
> - Las pruebas de integración corrieron contra un **PostgreSQL 16 real**, usando un sustituto mínimo del driver
>   (protocolo de PostgreSQL, solo para pruebas, **no incluido** en el proyecto). En CI se usa `psycopg` 3 real.
> - La cobertura se midió con un trazador de líneas basado en `sys.settrace` (biblioteca estándar).
> - El mutation testing se midió con un arnés local que aplica los mismos tipos de mutación que mutmut.
> Los valores **oficiales** de cobertura (pytest-cov) y Mutation Score (mutmut) los produce el pipeline de GitHub
> Actions (`.github/workflows/ci.yml`) en la primera ejecución.

## 1. Resultado de la suite

```
$ TEST_DATABASE_URL=postgresql://…/repuestos_test pytest -q
100 passed in 5.45s

$ pytest -q            # sin base de datos (lo que usa el job de mutación)
61 passed, 39 skipped
```

| Archivo | Tipo | Pruebas | Qué cubre |
|---|---|---|---|
| `tests/test_unitarias.py` | Unitarias | 11 | política de contraseñas, hash, JWT, CAPTCHA, IVA, pagos, transiciones, factura |
| `tests/test_mutacion.py` | Unitarias (especificación) | 35 | fronteras y mensajes de reglas de negocio, validación, roles, limitador, JWT |
| `tests/test_arquitectura.py` | Arquitectura | 3 | el modelo no importa Flask/psycopg; `Seguridad` no importa `app`; controladores sin SQL |
| `tests/test_herramientas.py` | Unitarias (CI) | 3 | cálculo del Mutation Score y umbral que hace fallar el pipeline |
| `tests/test_regresion.py` | Regresión | 16 | un caso por bug corregido (B01–B11) |
| `tests/test_seguridad.py` | Seguridad / integración | 14 | `/api/auth/login`, `/api/admin`, `/api/user`, RBAC, 429, CORS, cabeceras, inyección SQL, CAPTCHA |
| `tests/test_integracion.py` | Integración | 18 | flujo completo de venta → pago → factura → despacho → entrega, catálogos, productos, inventario, CLI |
| **Total** | | **100** | |

Pruebas de regresión contra la versión anterior: 8 de las 10 primeras pruebas de regresión con base de datos
**fallaron en v2** y pasan en v3 (detalle en `docs/INFORME_AUDITORIA.md`).

## 2. Cobertura de líneas (trazador `sys.settrace`, suite completa)

| Capa | Líneas ejecutadas / ejecutables | Cobertura |
|---|---|---|
| `app/models` | 276 / 276 | 100.0 % |
| `app/controllers` | 243 / 248 | 98.0 % |
| `app/repositories` | 261 / 273 | 95.6 % |
| `app/reportes` | 246 / 259 | 95.0 % |
| `Seguridad` | 575 / 605 | 95.0 % |
| `app/services` | 461 / 514 | 89.7 % |
| `migraciones` | 96 / 125 | 76.8 % (`__main__.py`, la CLI alternativa, no se prueba) |
| **Total (app, Seguridad, migraciones)** | **2566 / 2742** | **93.6 %** |

La métrica cuenta las líneas que el intérprete marca como ejecutables (`co_lines`); puede diferir unas décimas de
`coverage.py`. En CI se genera `coverage.xml` con pytest-cov para SonarCloud.

## 3. Mutation testing

Módulos mutados (los mismos de `setup.cfg` → `[mutmut] paths_to_mutate`): `app/models/negocio.py`,
`validacion.py`, `errores.py`, `meta.py`, `Seguridad/contrasenas.py`, `limitador.py`, `modelos.py`, `tokens.py`.
Operadores: comparaciones (`==`↔`!=`, `<`↔`<=`…), aritméticos, `and`↔`or`, eliminación de `not`, constantes
numéricas (+1), booleanas (negación), cadenas (`"XX…XX"`) y `return x` → `return None`. Runner: pruebas sin base de datos.

| Módulo | Antes (v3 sin `test_mutacion.py`) | Después |
|---|---|---|
| `app/models/negocio.py` | 55 / 117 | 112 / 117 |
| `app/models/validacion.py` | 26 / 59 | 58 / 59 |
| `app/models/errores.py` | 0 / 6 | 6 / 6 |
| `app/models/meta.py` | 2 / 13 | 11 / 13 |
| `Seguridad/contrasenas.py` | 13 / 23 | 22 / 23 |
| `Seguridad/limitador.py` | 9 / 24 | 19 / 24 |
| `Seguridad/modelos.py` | 6 / 24 | 22 / 24 |
| `Seguridad/tokens.py` | 23 / 30 | 26 / 30 |
| **Total (arnés local)** | **134 / 296 = 45.3 %** | **276 / 296 = 93.2 %** |

Los 20 sobrevivientes restantes son, en su mayoría, **mutantes equivalentes** que no cambian el comportamiento
observable: `frozen=True` → `False` en dataclasses inmutables por convención, longitud del token aleatorio
(`token_urlsafe(16)` → `17`), tamaño máximo del diccionario del limitador, y mensajes duplicados en ramas de error
que ya están cubiertas por otro mensaje idéntico.

**En CI (oficial):** el job `mutacion` ejecuta `mutmut run`, y `tools/mutation_score.py` calcula
`eliminados / (eliminados + sobrevivientes + sospechosos)` desde `.mutmut-cache`; el job **falla si el score es
menor a 50 %** y emite una advertencia si es menor al objetivo de 60 %. El resultado se publica como artefacto
(`mutation-report.json`). Ese valor oficial aún no existe porque el pipeline no se ha ejecutado en GitHub.

## 4. Análisis estático

```
$ ruff check .      # reglas E, W, F, B, S (bandit), C90 (complejidad ≤ 10), SIM, UP, PLE, PLW
All checks passed!
```

## 5. Pendiente de ejecución en GitHub (requiere intervención)

| Herramienta | Estado | Qué hacer |
|---|---|---|
| SonarCloud | Configurado (`sonar-project.properties`, pasos en `ci.yml`), **no ejecutado** | Crear el proyecto en sonarcloud.io, reemplazar `CAMBIAR_ORGANIZACION` y agregar el secreto `SONAR_TOKEN`. El Quality Gate se verifica con `sonarqube-quality-gate-action` |
| CodeQL | Configurado (`.github/workflows/codeql.yml`, Python + JavaScript), **no ejecutado** | Activar *Code scanning* en Settings → Code security; revisar alertas en Security → Code scanning |
| Dependabot | Configurado (`.github/dependabot.yml`), **sin PR todavía** | Activar *Dependabot alerts/security updates*; revisar y fusionar el primer PR que abra |
| pip-audit | Paso en CI, **no ejecutado** (requiere internet) | Se ejecuta en el job `calidad` |
| mutmut / pytest-cov | Pasos en CI, **no ejecutados** | Se ejecutan en los jobs `mutacion` y `pruebas` |
