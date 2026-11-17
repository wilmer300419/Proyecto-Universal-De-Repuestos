"""Consultas de productos e inventario. Leen de las vistas v_producto_detalle y v_inventario_detalle (V006)."""
from __future__ import annotations

from psycopg import sql

from Seguridad.contratos import EjecutorSQL

from ..models.validacion import patron_like

_EDITABLES = ("name", "description", "unit_price", "state", "fk_car_product", "fk_spare_part")

_BUSCAR = """
SELECT v.product_id, v.name, v.description, v.unit_price, v.state, v.fk_car_product, v.fk_spare_part,
       CASE WHEN %(bodega)s::bigint IS NULL THEN v.stock_total
            ELSE COALESCE((SELECT i.quantity_available FROM inventory i
                           WHERE i.product_id = v.product_id AND i.company_warehouse_id = %(bodega)s::bigint), 0)
       END AS stock_total,
       v.category_id, v.category, v.part_brand
FROM v_producto_detalle v
WHERE (NOT %(activos)s::boolean OR v.state)
  AND (%(patron)s::text IS NULL OR v.name ILIKE %(patron)s::text OR v.description ILIKE %(patron)s::text
       OR v.category ILIKE %(patron)s::text)
  AND (%(car)s::bigint IS NULL OR %(car)s::bigint = ANY(v.fk_car_product))
  AND (%(marca)s::bigint IS NULL
       OR v.fk_car_product && ARRAY(SELECT c.car_id FROM car c WHERE c.car_brand_id = %(marca)s::bigint))
  AND (%(tipo)s::bigint IS NULL OR v.category_id = %(tipo)s::bigint)
ORDER BY v.name, v.product_id"""

_INVENTARIO = """SELECT * FROM v_inventario_detalle
WHERE (%(bodega)s::bigint IS NULL OR company_warehouse_id = %(bodega)s::bigint)
  AND (NOT %(bajo)s::boolean OR needs_reorder)
ORDER BY product_name, inventory_id"""


class RepositorioProductos:
    def __init__(self, db: EjecutorSQL):
        self._db = db

    def buscar(self, q: str | None = None, car_id: int | None = None, car_brand_id: int | None = None,
               type_id: int | None = None, solo_activos: bool = True, bodega: int | None = None) -> list[dict]:
        """SQL estático: cada filtro opcional se anula con NULL (sin concatenar texto en la consulta).
        Con ``bodega`` el stock que se informa es el de esa bodega (la que atiende la venta)."""
        return self._db.fetch_all(_BUSCAR, {
            "activos": solo_activos, "patron": patron_like(q) if q else None, "car": car_id,
            "marca": car_brand_id, "tipo": type_id, "bodega": bodega})

    def obtener(self, product_id: int, bodega: int | None = None) -> dict | None:
        fila = self._db.fetch_one("SELECT * FROM v_producto_detalle WHERE product_id = %s", (product_id,))
        if fila and bodega:
            existencia = self._db.fetch_one("SELECT quantity_available FROM inventory WHERE product_id = %s "
                                            "AND company_warehouse_id = %s", (product_id, bodega))
            fila["stock_total"] = existencia["quantity_available"] if existencia else 0
        return fila

    def obtener_varios(self, ids: list[int]) -> dict[int, dict]:
        filas = self._db.fetch_all("SELECT * FROM v_producto_detalle WHERE product_id = ANY(%s)", (list(ids),))
        return {f["product_id"]: f for f in filas}

    def crear(self, datos: dict) -> int:
        return self._db.fetch_one(
            "INSERT INTO product (name, description, unit_price, fk_car_product, fk_spare_part) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING product_id",
            (datos["name"], datos.get("description"), datos["unit_price"], datos.get("fk_car_product") or [],
             datos.get("fk_spare_part")))["product_id"]

    def actualizar(self, product_id: int, datos: dict) -> bool:
        campos = {k: v for k, v in datos.items() if k in _EDITABLES}       # columnas de una lista blanca fija
        if not campos:
            return self.obtener(product_id) is not None
        consulta = sql.SQL("UPDATE product SET {} WHERE product_id = %s").format(_asignaciones(campos))
        return self._db.execute(consulta, [*campos.values(), product_id]) == 1

    def vehiculos_inexistentes(self, ids: list[int]) -> list[int]:
        if not ids:
            return []
        filas = self._db.fetch_all("SELECT x AS car_id FROM unnest(%s::bigint[]) AS x "
                                   "WHERE NOT EXISTS (SELECT 1 FROM car c WHERE c.car_id = x)", (list(ids),))
        return [f["car_id"] for f in filas]

    def existe_vehiculo(self, car_id: int) -> bool:
        return self._db.fetch_one("SELECT 1 AS x FROM car WHERE car_id = %s", (car_id,)) is not None


_CANTIDADES = ("quantity_available", "minimum_stock", "maximum_stock", "reorder_stock")
_EXISTENCIA = "SELECT * FROM inventory WHERE product_id = %s AND company_warehouse_id = %s"
_EXISTENCIA_BLOQUEO = _EXISTENCIA + " FOR UPDATE"


def _asignaciones(campos: dict) -> sql.Composable:
    return sql.SQL(", ").join(sql.SQL("{} = %s").format(sql.Identifier(c)) for c in campos)


class RepositorioInventario:
    def __init__(self, db: EjecutorSQL):
        self._db = db

    def listar(self, bodega: int | None = None, solo_bajo: bool = False) -> list[dict]:
        return self._db.fetch_all(_INVENTARIO, {"bodega": bodega, "bajo": solo_bajo})

    def obtener(self, inventory_id: int) -> dict | None:
        return self._db.fetch_one("SELECT * FROM v_inventario_detalle WHERE inventory_id = %s", (inventory_id,))

    def existencia(self, product_id: int, bodega: int, bloquear: bool = False) -> dict | None:
        """Fila de inventario; con ``bloquear`` usa SELECT … FOR UPDATE (evita vender dos veces la misma unidad)."""
        consulta = _EXISTENCIA_BLOQUEO if bloquear else _EXISTENCIA
        return self._db.fetch_one(consulta, (product_id, bodega))

    def crear(self, datos: dict) -> int:
        return self._db.fetch_one(
            "INSERT INTO inventory (product_id, company_warehouse_id, quantity_available, minimum_stock, maximum_stock, reorder_stock) "
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING inventory_id",
            (datos["product_id"], datos["company_warehouse_id"], datos["quantity_available"], datos.get("minimum_stock", 0),
             datos.get("maximum_stock", 0), datos.get("reorder_stock", 0)))["inventory_id"]

    def actualizar(self, inventory_id: int, datos: dict) -> bool:
        campos = {k: v for k, v in datos.items() if k in _CANTIDADES}
        if not campos:
            return False
        consulta = sql.SQL("UPDATE inventory SET {} WHERE inventory_id = %s").format(_asignaciones(campos))
        return self._db.execute(consulta, [*campos.values(), inventory_id]) == 1

    def mover(self, inventory_id: int, delta: int) -> None:
        self._db.execute("UPDATE inventory SET quantity_available = quantity_available + %s WHERE inventory_id = %s",
                         (delta, inventory_id))

    def contar_bajo(self) -> int:
        return self._db.fetch_one("SELECT COUNT(*) AS n FROM v_inventario_detalle WHERE needs_reorder")["n"]
