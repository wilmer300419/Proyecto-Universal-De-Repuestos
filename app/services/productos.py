"""Servicio de productos e inventario: validación, reglas y auditoría."""
from __future__ import annotations

from psycopg import errors as pgerr

from Seguridad.repositorio import RepositorioAuditoria

from ..core.database import Database
from ..models.errores import ErrorDeNegocio, ErrorValidacion, NoEncontrado
from ..models.negocio import dinero
from ..models.validacion import a_booleano, a_entero, entero_opcional, texto
from ..repositories.productos import RepositorioInventario, RepositorioProductos


def _entero(valor, nombre: str, minimo: int = 0) -> int:
    return a_entero(valor, nombre, minimo)


class ServicioProductos:
    def __init__(self, db: Database, auditoria: RepositorioAuditoria):
        self._db, self._auditoria = db, auditoria
        self.productos, self.inventario = RepositorioProductos(db), RepositorioInventario(db)

    # ------------------------------------------------------------ productos
    def buscar(self, q=None, car_id=None, car_brand_id=None, type_id=None, warehouse_id=None) -> list[dict]:
        return self.productos.buscar((q or "").strip()[:100] or None, entero_opcional(car_id, "car_id"),
                                     entero_opcional(car_brand_id, "car_brand_id"), entero_opcional(type_id, "type_id"),
                                     bodega=entero_opcional(warehouse_id, "warehouse_id"))

    def obtener(self, product_id: int, warehouse_id=None) -> dict:
        return self.productos.obtener(product_id, entero_opcional(warehouse_id, "warehouse_id")) or self._no_existe()

    def para_vehiculo(self, car_id: int) -> list[dict]:
        if not self.productos.existe_vehiculo(car_id):
            raise NoEncontrado("Vehículo no encontrado")
        return self.productos.buscar(car_id=car_id)

    def _validar(self, d: dict, parcial: bool) -> dict:
        limpio = {}
        if "name" in d or not parcial:
            limpio["name"] = texto(d.get("name"), "El nombre", 150, requerido=True)
        if "description" in d:
            limpio["description"] = texto(d["description"], "La descripción", 255)
        if "unit_price" in d or not parcial:
            limpio["unit_price"] = self._precio(d.get("unit_price"))
        if "fk_car_product" in d:
            limpio["fk_car_product"] = self._vehiculos(d["fk_car_product"])
        if "fk_spare_part" in d:
            limpio["fk_spare_part"] = entero_opcional(d["fk_spare_part"], "fk_spare_part")
        if "state" in d:
            limpio["state"] = a_booleano(d["state"], "state")
        return limpio

    @staticmethod
    def _precio(valor):
        if isinstance(valor, bool) or valor in (None, ""):
            raise ErrorValidacion("El precio es obligatorio")
        precio = dinero(valor)
        if precio < 0:
            raise ErrorValidacion("El precio no puede ser negativo")
        return precio

    def _vehiculos(self, vehiculos) -> list[int]:
        """La compatibilidad se guarda como arreglo (ERD), sin FK: se valida aquí que cada vehículo exista."""
        if not isinstance(vehiculos, list):
            raise ErrorValidacion("fk_car_product debe ser una lista de car_id")
        ids = sorted({_entero(v, "car_id", 1) for v in vehiculos})
        if faltan := self.productos.vehiculos_inexistentes(ids):
            raise ErrorValidacion(f"Vehículos inexistentes: {', '.join(map(str, faltan))}")
        return ids

    def crear(self, d: dict, usuario, ip) -> dict:
        pid = self._proteger(lambda: self.productos.crear(self._validar(d, parcial=False)))
        self._auditoria.registrar(usuario.id, usuario.nombre_usuario, "CREAR", "producto", f"product_id={pid}", ip)
        return self.obtener(pid)

    def actualizar(self, product_id: int, d: dict, usuario, ip) -> dict:
        if not self._proteger(lambda: self.productos.actualizar(product_id, self._validar(d, parcial=True))):
            self._no_existe()
        self._auditoria.registrar(usuario.id, usuario.nombre_usuario, "ACTUALIZAR", "producto", f"product_id={product_id}", ip)
        return self.obtener(product_id)

    def desactivar(self, product_id: int, usuario, ip) -> None:
        if not self.productos.actualizar(product_id, {"state": False}):
            self._no_existe()
        self._auditoria.registrar(usuario.id, usuario.nombre_usuario, "ELIMINAR", "producto", f"product_id={product_id}", ip)

    # ------------------------------------------------------------ inventario
    def listar_inventario(self, bodega=None, solo_bajo: bool = False) -> list[dict]:
        return self.inventario.listar(entero_opcional(bodega, "warehouse_id"), solo_bajo)

    def crear_inventario(self, d: dict, usuario, ip) -> dict:
        datos = {"product_id": _entero(d.get("product_id"), "product_id", 1),
                 "company_warehouse_id": _entero(d.get("company_warehouse_id"), "company_warehouse_id", 1),
                 "quantity_available": _entero(d.get("quantity_available"), "quantity_available")}
        for k in ("minimum_stock", "maximum_stock", "reorder_stock"):
            if k in d:
                datos[k] = _entero(d[k], k)
        if self.inventario.existencia(datos["product_id"], datos["company_warehouse_id"]):
            raise ErrorDeNegocio("Ya existe inventario para ese producto y bodega; usa PUT para modificarlo")
        iid = self._proteger(lambda: self.inventario.crear(datos))
        self._auditoria.registrar(usuario.id, usuario.nombre_usuario, "CREAR", "inventario", f"inventory_id={iid}", ip)
        return self.inventario.obtener(iid)

    def actualizar_inventario(self, inventory_id: int, d: dict, usuario, ip) -> dict:
        datos = {k: _entero(d[k], k) for k in ("quantity_available", "minimum_stock", "maximum_stock", "reorder_stock") if k in d}
        if not datos:
            raise ErrorValidacion("No hay campos para actualizar")
        if not self.inventario.actualizar(inventory_id, datos):
            raise NoEncontrado("Registro de inventario no encontrado")
        self._auditoria.registrar(usuario.id, usuario.nombre_usuario, "ACTUALIZAR", "inventario",
                                  f"inventory_id={inventory_id} {datos}", ip)
        return self.inventario.obtener(inventory_id)

    # ------------------------------------------------------------ internos
    @staticmethod
    def _no_existe():
        raise NoEncontrado("Producto no encontrado")

    @staticmethod
    def _proteger(accion):
        try:
            return accion()
        except pgerr.ForeignKeyViolation:
            raise ErrorDeNegocio("Alguna referencia (vehículo, repuesto, bodega o producto) no existe") from None
        except (pgerr.CheckViolation, pgerr.NumericValueOutOfRange):
            raise ErrorValidacion("Algún valor está fuera del rango permitido") from None
        except pgerr.UniqueViolation:
            raise ErrorDeNegocio("Ya existe un registro con esos datos") from None
