"""MODELO (MVC): reglas de negocio puras de la tienda (IVA, estados, pagos, entregas, facturas).

No usa Flask ni la base de datos, por eso se prueba de forma aislada (tests/test_unitarias.py).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from .errores import ErrorDeNegocio, ErrorValidacion

CENTAVO = Decimal("0.01")


def dinero(valor) -> Decimal:
    if isinstance(valor, bool):
        raise ErrorValidacion("Valor monetario inválido")
    try:
        resultado = Decimal(str(valor)).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        raise ErrorValidacion("Valor monetario inválido") from None
    if not resultado.is_finite():
        raise ErrorValidacion("Valor monetario inválido")
    return resultado


class EstadoVenta:
    PENDIENTE, PAGADA, DESPACHADA, ENTREGADA, CANCELADA = "Pendiente", "Pagada", "Despachada", "Entregada", "Cancelada"
    FACTURABLES = (PAGADA, DESPACHADA, ENTREGADA)


class EstadoEntrega:
    PENDIENTE, EMPACADO, EN_CAMINO, ENTREGADO, CANCELADO = "pendiente", "empacado", "en_camino", "entregado", "cancelado"
    # transición de la entrega -> estado que toma la venta
    TRANSICIONES = {EMPACADO: {EN_CAMINO: EstadoVenta.DESPACHADA}, EN_CAMINO: {ENTREGADO: EstadoVenta.ENTREGADA}}


METODOS_PAGO = {
    "tarjeta_credito": "Tarjeta de crédito", "tarjeta_debito": "Tarjeta débito", "pse": "PSE",
    "transferencia": "Transferencia bancaria", "nequi": "Nequi", "efectivo": "Efectivo contra entrega",
}
_ALIAS_PAGO = {"tarjeta": "tarjeta_credito", "credito": "tarjeta_credito", "debito": "tarjeta_debito"}


def normalizar_metodo_pago(metodo) -> str:
    clave = str(metodo or "").strip().lower()
    clave = _ALIAS_PAGO.get(clave, clave)
    if clave not in METODOS_PAGO:
        raise ErrorValidacion(f"Método de pago inválido; usa uno de: {', '.join(METODOS_PAGO)}")
    return clave


# ------------------------------------------------------------------ pedidos
@dataclass(frozen=True)
class LineaPedido:
    product_id: int
    nombre: str
    cantidad: int
    precio: Decimal
    descuento: Decimal = Decimal("0")

    @property
    def subtotal(self) -> Decimal:
        valor = dinero(self.precio * self.cantidad - self.descuento)
        if valor < 0:
            raise ErrorValidacion(f"El descuento de '{self.nombre}' supera el valor de la línea")
        return valor


@dataclass(frozen=True)
class Totales:
    subtotal: Decimal
    impuesto: Decimal
    total: Decimal


def unir_items(items) -> dict[int, tuple[int, Decimal]]:
    """[{product_id, quantity, discount?}] -> {product_id: (cantidad, descuento)}; une productos repetidos."""
    if not isinstance(items, list) or not items:
        raise ErrorValidacion("El pedido debe tener al menos un producto")
    unidos: dict[int, tuple[int, Decimal]] = {}
    for it in items:
        try:
            pid, cantidad = int(it.get("product_id")), int(it.get("quantity", 0))
            descuento = dinero(it.get("discount", 0) or 0)
        except (TypeError, ValueError, AttributeError, ErrorValidacion):
            raise ErrorValidacion("Cada producto requiere product_id y quantity mayor que cero") from None
        if cantidad <= 0 or descuento < 0:
            raise ErrorValidacion("Cada producto requiere product_id y quantity mayor que cero")
        c, d = unidos.get(pid, (0, Decimal("0")))
        unidos[pid] = (c + cantidad, d + descuento)
    if len(unidos) > 50:
        raise ErrorValidacion("Un pedido admite máximo 50 productos distintos")
    return unidos


def calcular_totales(lineas: list[LineaPedido], iva) -> Totales:
    subtotal = dinero(sum((linea.subtotal for linea in lineas), Decimal("0")))
    impuesto = dinero(subtotal * Decimal(str(iva)))
    return Totales(subtotal, impuesto, subtotal + impuesto)


def validar_stock(disponible: int | None, cantidad: int, nombre: str) -> None:
    if (disponible or 0) < cantidad:
        raise ErrorDeNegocio(f"Stock insuficiente para '{nombre}' (disponible: {disponible or 0})")


# ------------------------------------------------------------------ pagos y cancelación
def validar_pago(estado_venta: str, total, monto, sale_id: int) -> Decimal:
    if estado_venta != EstadoVenta.PENDIENTE:
        raise ErrorDeNegocio(f"La venta #{sale_id} ya está en estado {estado_venta}; no se puede pagar de nuevo")
    pagado = dinero(total if monto in (None, "") else monto)
    if pagado != dinero(total):
        raise ErrorValidacion(f"El pago debe ser por el total de la venta: {dinero(total)}")
    return pagado


def validar_cancelacion(estado_venta: str) -> None:
    if estado_venta != EstadoVenta.PENDIENTE:
        raise ErrorDeNegocio("Solo se pueden cancelar ventas pendientes de pago")


# ------------------------------------------------------------------ entregas
def validar_preparacion(estado_venta: str, estado_entrega: str) -> None:
    if estado_venta != EstadoVenta.PAGADA:
        raise ErrorDeNegocio("La venta debe estar pagada para preparar el despacho")
    if estado_entrega != EstadoEntrega.PENDIENTE:
        raise ErrorDeNegocio(f"La entrega ya está {estado_entrega}")


def transicion_entrega(actual: str, nuevo: str) -> str:
    """Devuelve el nuevo estado de la VENTA o lanza ErrorDeNegocio si el salto no es válido."""
    destino = EstadoEntrega.TRANSICIONES.get(actual, {}).get(nuevo)
    if destino is None:
        raise ErrorDeNegocio(f"Transición inválida: {actual} -> {nuevo}")
    return destino


# ------------------------------------------------------------------ facturación
def validar_facturable(estado_venta: str) -> None:
    if estado_venta not in EstadoVenta.FACTURABLES:
        raise ErrorDeNegocio("Solo se factura una venta pagada")


def numero_factura(sale_id: int) -> str:
    return f"FE-{sale_id:08d}"


def texto_qr(numero: str, nit: str, fecha: datetime, impuesto, total) -> str:
    return f"FACTURA:{numero}|NIT:{nit}|FECHA:{fecha:%Y-%m-%d}|IVA:{dinero(impuesto)}|TOTAL:{dinero(total)}"
