"""Servicios de ventas, entregas y facturación.

Cada operación de escritura abre UNA transacción (``db.unidad_de_trabajo()``) y le pasa la misma
conexión a todos los repositorios; ante cualquier error se revierte completa.
"""
from __future__ import annotations

import os
from datetime import datetime, UTC

from psycopg import errors as pgerr

from Seguridad import Rol, Usuario
from Seguridad.repositorio import RepositorioAuditoria

from ..core.database import Database
from ..documentos.factura import DocumentosFactura
from ..models import negocio as N
from ..models.errores import ErrorDeNegocio, ErrorValidacion, NoEncontrado, SinPermiso
from ..models.validacion import a_entero
from ..repositories.productos import RepositorioInventario, RepositorioProductos
from ..repositories.ventas import (RepositorioEmpresa, RepositorioEntregas, RepositorioFacturas, RepositorioPersonas,
                                   RepositorioVentas)
from ..utils import codigos


def _visible(venta: dict | None, u: Usuario) -> dict:
    if venta is None or not (u.es_personal or venta["user_id"] == u.id):
        raise NoEncontrado("Venta no encontrada")
    return venta


class ServicioVentas:
    def __init__(self, db: Database, auditoria: RepositorioAuditoria, iva: float):
        self._db, self._auditoria, self._iva = db, auditoria, iva

    # ------------------------------------------------------------ consulta
    def vista(self, sale_id: int, conn=None) -> dict:
        db = conn or self._db
        ventas = RepositorioVentas(db)
        venta = ventas.obtener(sale_id)
        if venta is None:
            raise NoEncontrado("Venta no encontrada")
        venta["items"] = ventas.detalle(sale_id)
        venta["payments"] = ventas.pagos(sale_id)
        venta["delivery"] = RepositorioEntregas(db).por_venta(sale_id)
        return venta

    def obtener(self, sale_id: int, u: Usuario) -> dict:
        _visible(RepositorioVentas(self._db).obtener(sale_id), u)
        return self.vista(sale_id)

    def listar(self, u: Usuario, estado: str | None = None) -> list[dict]:
        return RepositorioVentas(self._db).listar(u.id if u.rol is Rol.CLIENTE else None, estado or None)

    @staticmethod
    def metodos_pago() -> list[dict]:
        return [{"key": k, "label": v} for k, v in N.METODOS_PAGO.items()]

    # ------------------------------------------------------------ crear
    def crear(self, d: dict, u: Usuario, ip: str | None) -> dict:
        unidos = N.unir_items(d.get("items"))
        direccion = str(d.get("address") or "").strip()
        if direccion and not 6 <= len(direccion) <= 255:
            raise ErrorValidacion("La dirección debe tener entre 6 y 255 caracteres")
        descripcion = (str(d.get("description") or "").strip() or None)
        if descripcion and len(descripcion) > 255:
            raise ErrorValidacion("La descripción admite máximo 255 caracteres")
        with self._db.unidad_de_trabajo() as tx:
            ventas, inventario, productos = RepositorioVentas(tx), RepositorioInventario(tx), RepositorioProductos(tx)
            bodega = self._bodega(d.get("company_warehouse_id"), RepositorioEmpresa(tx))
            tipo = ventas.tipo_venta(d.get("sale_type_id"))
            if tipo is None:
                raise ErrorValidacion("sale_type_id inválido")
            catalogo = productos.obtener_varios(list(unidos))
            lineas = []
            for pid, (cantidad, descuento) in sorted(unidos.items()):          # orden fijo de bloqueo: evita interbloqueos
                p = catalogo.get(pid)
                if p is None or not p["state"]:
                    raise ErrorDeNegocio(f"El producto {pid} no existe o está inactivo")
                existencia = inventario.existencia(pid, bodega, bloquear=True)
                N.validar_stock(existencia and existencia["quantity_available"], cantidad, p["name"])
                inventario.mover(existencia["inventory_id"], -cantidad)
                lineas.append(N.LineaPedido(pid, p["name"], cantidad, p["unit_price"], descuento))
            t = N.calcular_totales(lineas, self._iva)
            cliente = d.get("customer_name") if u.es_admin and d.get("customer_name") else RepositorioPersonas(tx).nombre_de_usuario(u.id)
            sale_id = ventas.crear(
                {"user_id": u.id, "sale_type_id": tipo, "state": N.EstadoVenta.PENDIENTE, "company_warehouse_id": bodega,
                 "customer_name": (cliente or u.nombre_usuario)[:200], "description": descripcion,
                 "subtotal": t.subtotal, "tax": t.impuesto, "total": t.total},
                [{"product_id": li.product_id, "quantity": li.cantidad, "unit_price": li.precio,
                  "discount": N.dinero(li.descuento), "subtotal": li.subtotal} for li in lineas])
            if direccion:
                RepositorioEntregas(tx).crear(sale_id, direccion)
            RepositorioAuditoria(tx).registrar(u.id, u.nombre_usuario, "CREAR", "venta", f"sale_id={sale_id} total={t.total}", ip)
            return self.vista(sale_id, tx)

    @staticmethod
    def _bodega(valor, empresa: RepositorioEmpresa) -> int:
        """Antes: int('x') lanzaba ValueError (HTTP 500) y una bodega inexistente se reportaba como
        'stock insuficiente'. Ahora ambos casos son errores de validación claros."""
        if valor in (None, ""):
            bodega = empresa.bodega_principal()
            if bodega is None:
                raise ErrorDeNegocio("No hay bodegas activas para atender el pedido")
            return bodega
        bodega = a_entero(valor, "company_warehouse_id", 1)
        if not empresa.bodega_activa(bodega):
            raise ErrorValidacion(f"La bodega {bodega} no existe o está inactiva")
        return bodega

    # ------------------------------------------------------------ pagar
    def pagar(self, sale_id: int, d: dict, u: Usuario, ip: str | None) -> dict:
        metodo = N.normalizar_metodo_pago(d.get("method"))
        referencia = str(d.get("reference") or codigos.referencia_pago())[:80]
        ultimos4 = "".join(ch for ch in str(d.get("card_last4") or "") if ch.isdigit())[-4:]
        if ultimos4:                    # nunca se guarda el número de tarjeta, solo los 4 últimos dígitos
            referencia = f"{referencia}-****{ultimos4}"
        try:
            with self._db.unidad_de_trabajo() as tx:
                ventas = RepositorioVentas(tx)
                venta = _visible(ventas.obtener(sale_id, bloquear=True), u)        # FOR UPDATE: evita el doble pago
                monto = N.validar_pago(venta["state"], venta["total"], d.get("amount"), sale_id)
                ventas.registrar_pago(sale_id, monto, metodo, referencia)
                ventas.cambiar_estado(sale_id, N.EstadoVenta.PAGADA)
                RepositorioAuditoria(tx).registrar(u.id, u.nombre_usuario, "PAGO", "venta",
                                                   f"sale_id={sale_id} metodo={metodo} monto={monto}", ip)
                return self.vista(sale_id, tx)
        except pgerr.UniqueViolation:        # índice uq_payment_aprobado
            raise ErrorDeNegocio(f"La venta #{sale_id} ya tiene un pago aprobado") from None

    # ------------------------------------------------------------ cancelar
    def cancelar(self, sale_id: int, u: Usuario, ip: str | None) -> dict:
        with self._db.unidad_de_trabajo() as tx:
            ventas, inventario, entregas = RepositorioVentas(tx), RepositorioInventario(tx), RepositorioEntregas(tx)
            venta = _visible(ventas.obtener(sale_id, bloquear=True), u)
            N.validar_cancelacion(venta["state"])
            for item in sorted(ventas.detalle(sale_id), key=lambda i: i["product_id"]):       # devolver stock
                existencia = inventario.existencia(item["product_id"], venta["company_warehouse_id"], bloquear=True)
                if existencia:
                    inventario.mover(existencia["inventory_id"], item["quantity"])
            entrega = entregas.por_venta(sale_id)
            if entrega and entrega["status"] == N.EstadoEntrega.PENDIENTE:
                entregas.actualizar(entrega["delivery_id"], status=N.EstadoEntrega.CANCELADO)
            ventas.cambiar_estado(sale_id, N.EstadoVenta.CANCELADA)
            RepositorioAuditoria(tx).registrar(u.id, u.nombre_usuario, "CANCELAR", "venta", f"sale_id={sale_id}", ip)
            return self.vista(sale_id, tx)


class ServicioEntregas:
    def __init__(self, db: Database):
        self._db = db

    def listar(self, estado: str | None = None) -> list[dict]:
        return RepositorioEntregas(self._db).listar(estado or None)

    def asignadas(self, u: Usuario, estado: str | None = None) -> list[dict]:
        return RepositorioEntregas(self._db).listar(estado or None, u.id)

    def rastrear(self, guia: str) -> dict:
        return RepositorioEntregas(self._db).por_guia(guia) or self._no_existe("Guía no encontrada")

    @staticmethod
    def _no_existe(msg="Entrega no encontrada"):
        raise NoEncontrado(msg)

    def preparar(self, delivery_id: int, u: Usuario, ip) -> dict:
        with self._db.unidad_de_trabajo() as tx:
            entregas = RepositorioEntregas(tx)
            e = entregas.obtener(delivery_id, bloquear=True) or self._no_existe()
            venta = RepositorioVentas(tx).obtener(e["sale_id"])
            N.validar_preparacion(venta["state"], e["status"])
            entregas.actualizar(delivery_id, status=N.EstadoEntrega.EMPACADO, tracking_number=codigos.numero_guia())
            RepositorioAuditoria(tx).registrar(u.id, u.nombre_usuario, "PREPARAR", "entrega", f"delivery_id={delivery_id}", ip)
            return entregas.por_venta(e["sale_id"])

    def asignar(self, delivery_id: int, user_id, u: Usuario, ip) -> dict:
        user_id = a_entero(user_id, "user_id", 1)
        with self._db.unidad_de_trabajo() as tx:
            entregas = RepositorioEntregas(tx)
            e = entregas.obtener(delivery_id, bloquear=True) or self._no_existe()
            repartidor = tx.fetch_one("SELECT role, status FROM app_user WHERE user_id = %s", (user_id,))
            if not repartidor or repartidor["role"] != Rol.REPARTIDOR.value or not repartidor["status"]:
                raise ErrorValidacion("user_id debe pertenecer a un repartidor activo")
            if e["status"] in (N.EstadoEntrega.ENTREGADO, N.EstadoEntrega.CANCELADO):
                raise ErrorDeNegocio(f"No se puede reasignar una entrega en estado {e['status']}")
            entregas.actualizar(delivery_id, assigned_user_id=user_id)
            RepositorioAuditoria(tx).registrar(u.id, u.nombre_usuario, "ASIGNAR", "entrega",
                                               f"delivery_id={delivery_id} repartidor={user_id}", ip)
            return entregas.por_venta(e["sale_id"])

    def avanzar(self, delivery_id: int, nuevo: str, u: Usuario, ip) -> dict:
        with self._db.unidad_de_trabajo() as tx:
            entregas, ventas = RepositorioEntregas(tx), RepositorioVentas(tx)
            e = entregas.obtener(delivery_id, bloquear=True) or self._no_existe()
            if u.rol is Rol.REPARTIDOR and e["assigned_user_id"] != u.id:
                raise SinPermiso("Esta entrega no está asignada a ti")
            estado_venta = N.transicion_entrega(e["status"], str(nuevo or ""))
            fecha = datetime.now(UTC) if nuevo == N.EstadoEntrega.ENTREGADO else None
            entregas.actualizar(delivery_id, status=nuevo, delivery_date=fecha)
            ventas.cambiar_estado(e["sale_id"], estado_venta)
            RepositorioAuditoria(tx).registrar(u.id, u.nombre_usuario, "ESTADO_ENTREGA", "entrega",
                                               f"delivery_id={delivery_id} {e['status']}->{nuevo}", ip)
            return entregas.por_venta(e["sale_id"])


class ServicioFacturas:
    def __init__(self, db: Database, documentos: DocumentosFactura, iva: float):
        self._db, self._docs, self._iva = db, documentos, iva

    def emitir(self, sale_id: int, u: Usuario, ip) -> dict:
        try:
            with self._db.unidad_de_trabajo() as tx:
                facturas = RepositorioFacturas(tx)
                venta = RepositorioVentas(tx).obtener(sale_id, bloquear=True)
                if venta is None:
                    raise NoEncontrado("Venta no encontrada")
                N.validar_facturable(venta["state"])
                if facturas.por_venta(sale_id):
                    raise ErrorDeNegocio("La venta ya tiene factura")
                empresa = RepositorioEmpresa(tx).empresa_de_bodega(venta["company_warehouse_id"])
                ahora, numero = datetime.now(UTC), N.numero_factura(sale_id)
                tasa = N.dinero(self._iva)
                lineas = [{"product_id": i["product_id"], "product_name": i["product_name"], "quantity": i["quantity"],
                           "unit_price": i["unit_price"], "discount": i["discount"], "subtotal": i["subtotal"],
                           "tax": N.dinero(i["subtotal"] * tasa)} for i in RepositorioVentas(tx).detalle(sale_id)]
                factura = {"sale_id": sale_id, "invoice_number": numero, "issue_date": ahora, "subtotal": venta["subtotal"],
                           "tax": venta["tax"], "total": venta["total"], "pdf_path": None, "xml_path": None,
                           "qr_code": N.texto_qr(numero, empresa["tax_id"], ahora, venta["tax"], venta["total"])}
                factura["pdf_path"], factura["xml_path"] = self._docs.generar(factura, lineas, venta["customer_name"], empresa)
                invoice_id = facturas.crear(factura, lineas)
                RepositorioAuditoria(tx).registrar(u.id, u.nombre_usuario, "FACTURAR", "venta", f"sale_id={sale_id} {numero}", ip)
                return facturas.obtener(invoice_id)
        except pgerr.UniqueViolation:
            raise ErrorDeNegocio("La venta ya tiene factura") from None

    def _autorizado(self, sale_id: int, u: Usuario) -> None:
        venta = RepositorioVentas(self._db).obtener(sale_id)
        if venta is None or not (u.es_admin or venta["user_id"] == u.id):
            raise NoEncontrado("Factura no encontrada")

    def por_venta(self, sale_id: int, u: Usuario) -> dict:
        self._autorizado(sale_id, u)
        return RepositorioFacturas(self._db).por_venta(sale_id) or self._no_existe()

    @staticmethod
    def _no_existe():
        raise NoEncontrado("La factura de este pedido aún no ha sido emitida")

    def pdf(self, invoice_id: int, u: Usuario) -> dict:
        facturas = RepositorioFacturas(self._db)
        f = facturas.obtener(invoice_id) or self._no_existe()
        self._autorizado(f["sale_id"], u)
        if not f["pdf_path"] or not os.path.isabs(f["pdf_path"]) or not os.path.exists(f["pdf_path"]):
            # Facturas de los datos de prueba o archivos borrados: se regenera la representación gráfica
            venta = RepositorioVentas(self._db).obtener(f["sale_id"])
            empresa = RepositorioEmpresa(self._db).empresa_de_bodega(venta["company_warehouse_id"])
            f["pdf_path"], f["xml_path"] = self._docs.generar(f, facturas.lineas(invoice_id), venta["customer_name"], empresa)
            facturas.actualizar_rutas(invoice_id, f["pdf_path"], f["xml_path"])
        return f
