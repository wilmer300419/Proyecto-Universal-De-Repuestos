"""VISTA (MVC) de la factura: representación gráfica en PDF (con código QR) y XML simplificado.

El XML no es el UBL 2.1 firmado que exige la DIAN; para producción se requiere un proveedor tecnológico autorizado.
"""
from __future__ import annotations

import os
from datetime import timedelta, timezone
from decimal import Decimal
from xml.sax.saxutils import escape

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

VERDE = colors.HexColor("#188a31")
BOGOTA = timezone(timedelta(hours=-5))          # Colombia no usa horario de verano


def _m(valor) -> str:
    return "$ " + f"{Decimal(valor):,.0f}".replace(",", ".")


class DocumentosFactura:
    def __init__(self, directorio: str):
        self._dir = os.path.abspath(directorio)

    def generar(self, factura: dict, lineas: list[dict], cliente: str, empresa: dict) -> tuple[str, str]:
        os.makedirs(self._dir, exist_ok=True)
        base = os.path.join(self._dir, factura["invoice_number"])
        self._pdf(base + ".pdf", factura, lineas, cliente, empresa)
        self._xml(base + ".xml", factura, lineas, cliente, empresa)
        return base + ".pdf", base + ".xml"

    @staticmethod
    def _pdf(ruta, f, lineas, cliente, empresa) -> None:
        c = canvas.Canvas(ruta, pagesize=A4)
        w, h = A4
        c.setFillColor(VERDE)
        c.rect(0, h - 8, w, 8, stroke=0, fill=1)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, h - 50, empresa["name"])
        c.setFont("Helvetica", 10)
        c.drawString(50, h - 66, f"NIT: {empresa['tax_id']}   Tel: {empresa.get('cellphone') or empresa.get('phone') or ''}")
        c.drawString(50, h - 80, empresa.get("address") or "")
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(w - 50, h - 50, "FACTURA ELECTRÓNICA DE VENTA")
        c.setFont("Helvetica", 10)
        c.drawRightString(w - 50, h - 66, f"N.º {f['invoice_number']}")
        c.drawRightString(w - 50, h - 80, f"Fecha: {f['issue_date'].astimezone(BOGOTA):%Y-%m-%d %H:%M}")
        c.drawString(50, h - 115, f"Cliente: {cliente}")
        y = h - 145
        c.setFont("Helvetica-Bold", 10)
        for x, t in ((50, "Producto"), (300, "Cant."), (345, "V. unit."), (420, "Desc."), (480, "Subtotal")):
            c.drawString(x, y, t)
        c.line(50, y - 4, w - 50, y - 4)
        c.setFont("Helvetica", 10)
        for linea in lineas:
            y -= 16
            if y < 170:
                c.showPage()
                y = h - 60
                c.setFont("Helvetica", 10)
            c.drawString(50, y, str(linea.get("product_name") or linea["product_id"])[:44])
            c.drawString(300, y, str(linea["quantity"]))
            c.drawString(345, y, _m(linea["unit_price"]))
            c.drawString(420, y, _m(linea["discount"]))
            c.drawString(480, y, _m(linea["subtotal"]))
        y -= 30
        c.drawRightString(w - 50, y, f"Subtotal: {_m(f['subtotal'])}")
        c.drawRightString(w - 50, y - 15, f"IVA: {_m(f['tax'])}")
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(w - 50, y - 33, f"TOTAL: {_m(f['total'])}")
        qr = QrCodeWidget(f["qr_code"] or f["invoice_number"])
        x1, y1, x2, y2 = qr.getBounds()
        dibujo = Drawing(110, 110, transform=[110 / (x2 - x1), 0, 0, 110 / (y2 - y1), 0, 0])
        dibujo.add(qr)
        renderPDF.draw(dibujo, c, 50, 45)
        c.setFont("Helvetica", 8)
        c.drawString(170, 60, "Representación gráfica de la factura electrónica. Escanee el QR para validar.")
        c.save()

    @staticmethod
    def _xml(ruta, f, lineas, cliente, empresa) -> None:
        items = "".join(
            f"<Item><Nombre>{escape(str(li.get('product_name') or li['product_id']))}</Nombre><Cantidad>{li['quantity']}</Cantidad>"
            f"<PrecioUnitario>{li['unit_price']}</PrecioUnitario><Descuento>{li['discount']}</Descuento>"
            f"<Subtotal>{li['subtotal']}</Subtotal></Item>" for li in lineas)
        xml = (f'<?xml version="1.0" encoding="UTF-8"?><Factura><Numero>{escape(f["invoice_number"])}</Numero>'
               f"<Fecha>{f['issue_date'].isoformat()}</Fecha><Emisor><NIT>{escape(empresa['tax_id'])}</NIT>"
               f"<Nombre>{escape(empresa['name'])}</Nombre></Emisor><Cliente>{escape(cliente)}</Cliente>"
               f"<Items>{items}</Items><Subtotal>{f['subtotal']}</Subtotal><IVA>{f['tax']}</IVA>"
               f"<Total>{f['total']}</Total></Factura>")
        with open(ruta, "w", encoding="utf-8") as fh:
            fh.write(xml)
