"""Reportes de la tienda: ventas, productos más vendidos, inventario y entregas."""
from __future__ import annotations

from datetime import date, timedelta

from ..models.informe import Grafico, Informe, Parametro, Serie
from ..utils.formatos import moneda
from .base import Reporte

ESTADOS = (("", "Todos"), ("Pendiente", "Pendiente"), ("Pagada", "Pagada"), ("Despachada", "Despachada"),
           ("Entregada", "Entregada"), ("Cancelada", "Cancelada"))


def _hoy() -> date:
    return date.today()


def _rango():
    return [Parametro("desde", "Desde", "fecha", (_hoy() - timedelta(days=180)).isoformat()),
            Parametro("hasta", "Hasta", "fecha", _hoy().isoformat())]


def _validar_rango(v: dict) -> dict[str, str]:
    if v["desde"] and v["hasta"] and v["hasta"] < v["desde"]:
        return {"hasta": "Hasta: no puede ser anterior a la fecha inicial."}
    return {}


class ReporteVentas(Reporte):
    slug, titulo = "ventas", "Reporte de ventas por período"
    descripcion = "Ventas registradas entre dos fechas, con totales por estado."

    def parametros(self):
        return [*_rango(), Parametro("estado", "Estado", "select", "", ESTADOS, requerido=False)]

    def validar_conjunto(self, v):
        return _validar_rango(v)

    def generar(self, p):
        filas = self._repo.ventas(p["desde"], p["hasta"], p["estado"])
        por_estado: dict[str, list] = {}
        for f in filas:
            acum = por_estado.setdefault(f["state"], [0, 0])
            acum[0] += 1
            acum[1] += float(f["total"])
        resumen = [[e, n, moneda(t)] for e, (n, t) in sorted(por_estado.items())]
        validas = [f for f in filas if f["state"] != "Cancelada"]
        return Informe(self.titulo, f"{len(filas)} ventas · {moneda(sum(f['total'] for f in validas))} sin contar canceladas",
                       self.etiquetas_parametros(p), [
                           Grafico("Total vendido por estado", "barh", [r[0] for r in resumen],
                                   [Serie("Total", [por_estado[r[0]][1] for r in resumen])]),
                           self.tabla("Resumen por estado", ["Estado", "Ventas", "Total"], resumen),
                           self.tabla("Detalle de ventas", ["#", "Fecha", "Cliente", "Estado", "Unid.", "Subtotal", "IVA", "Total"],
                                      [[f["sale_id"], f["sale_date"], f["customer_name"], f["state"], f["items"],
                                        moneda(f["subtotal"]), moneda(f["tax"]), moneda(f["total"])] for f in filas])],
                       horizontal=True)


class ReporteMasVendidos(Reporte):
    slug, titulo = "mas-vendidos", "Reporte de productos más vendidos"
    descripcion = "Ranking de productos por unidades vendidas en un período (sin ventas canceladas)."

    def parametros(self):
        return [*_rango(), Parametro("limite", "Cantidad de productos", "entero", "10", minimo=1, maximo=50)]

    def validar_conjunto(self, v):
        return _validar_rango(v)

    def generar(self, p):
        filas = self._repo.mas_vendidos(p["limite"], p["desde"], p["hasta"])
        return Informe(self.titulo, f"Top {p['limite']}", self.etiquetas_parametros(p), [
            Grafico("Unidades vendidas", "barh", [f["name"][:28] for f in filas], [Serie("Unidades", [f["quantity"] for f in filas])]),
            self.tabla("Ranking", ["#", "Producto", "Unidades", "Total sin IVA"],
                       [[i, f["name"], f["quantity"], moneda(f["total"])] for i, f in enumerate(filas, 1)])])


class ReporteInventario(Reporte):
    slug, titulo = "inventario", "Reporte de inventario y reposición"
    descripcion = "Existencias por bodega y productos en o por debajo del punto de reorden."

    def parametros(self):
        return [Parametro("bodega", "Bodega", "select", "", (("", "Todas"), *self._repo.bodegas()), requerido=False),
                Parametro("solo_bajo", "Mostrar", "select", "no", (("no", "Todo el inventario"), ("si", "Solo stock bajo")))]

    def generar(self, p):
        filas = self._repo.inventario(int(p["bodega"]) if p["bodega"] else None, p["solo_bajo"] == "si")
        bajos = sum(1 for f in filas if f["needs_reorder"])
        return Informe(self.titulo, f"{len(filas)} registros · {bajos} por reponer", self.etiquetas_parametros(p), [
            self.tabla("Existencias", ["Producto", "Categoría", "Bodega", "Disponible", "Reorden", "Máximo", "Estado"],
                       [[f["product_name"], f["category"] or "—", f["warehouse_name"], f["quantity_available"], f["reorder_stock"],
                         f["maximum_stock"], ("Agotado" if not f["quantity_available"] else "Reponer") if f["needs_reorder"] else "OK"]
                        for f in filas])], horizontal=True)


class ReporteEntregas(Reporte):
    slug, titulo = "entregas", "Reporte de entregas por repartidor"
    descripcion = "Entregas agrupadas por repartidor y estado, con número de guía."

    def parametros(self):
        return [Parametro("estado", "Estado de la entrega", "select", "", (
            ("", "Todos"), ("pendiente", "Pendiente"), ("empacado", "Empacado"), ("en_camino", "En camino"),
            ("entregado", "Entregado"), ("cancelado", "Cancelado")), requerido=False)]

    def generar(self, p):
        filas = self._repo.entregas(p["estado"])
        conteo: dict[str, int] = {}
        for f in filas:
            conteo[f["courier"]] = conteo.get(f["courier"], 0) + 1
        return Informe(self.titulo, f"{len(filas)} entregas", self.etiquetas_parametros(p), [
            Grafico("Entregas por repartidor", "barh", list(conteo), [Serie("Entregas", list(conteo.values()))]),
            self.tabla("Entregas", ["#", "Venta", "Cliente", "Dirección", "Estado", "Guía", "Repartidor", "Entregada"],
                       [[f["delivery_id"], f["sale_id"], f["customer_name"], f["address"], f["status"],
                         f["tracking_number"] or "—", f["courier"], f["delivery_date"]] for f in filas])], horizontal=True)
