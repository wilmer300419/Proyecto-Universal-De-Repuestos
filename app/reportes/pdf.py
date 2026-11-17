"""VISTA (MVC) en PDF: convierte un ``Informe`` en un documento con ReportLab."""
from __future__ import annotations

from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..models.informe import Grafico, Informe, Tabla
from ..utils.formatos import celda

VERDE, VERDE_SUAVE, TINTA = colors.HexColor("#188a31"), colors.HexColor("#e7f5ea"), colors.HexColor("#15201a")


def _estilos():
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle("t", parent=base["Title"], fontName="Helvetica-Bold", fontSize=17, textColor=TINTA,
                                 alignment=0, spaceAfter=2),
        "sub": ParagraphStyle("s", parent=base["Normal"], fontSize=9.5, textColor=colors.HexColor("#5b6a61"), spaceAfter=6),
        "h2": ParagraphStyle("h", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=11.5, textColor=VERDE,
                             spaceBefore=8, spaceAfter=4),
        "celda": ParagraphStyle("c", parent=base["Normal"], fontSize=8, leading=10),
        "cab": ParagraphStyle("cab", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.white),
    }


def _p(valor, estilo) -> Paragraph:
    return Paragraph(escape(celda(valor)).replace("\n", "<br/>"), estilo)


def _tabla(t: Tabla, est, ancho: float) -> list:
    partes = [Paragraph(escape(t.titulo), est["h2"])]
    if not t.filas:
        return partes + [Paragraph("Sin datos para los parámetros indicados.", est["sub"])]
    datos = [[_p(c, est["cab"]) for c in t.columnas]] + [[_p(v, est["celda"]) for v in fila] for fila in t.filas]
    tabla = Table(datos, colWidths=[ancho / len(t.columnas)] * len(t.columnas), repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), VERDE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, VERDE_SUAVE]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#dfe6e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    partes.append(tabla)
    if t.nota:
        partes.append(Paragraph(escape(t.nota), est["sub"]))
    return partes


def _grafico(g: Grafico, est, ancho: float) -> list:
    if not g.etiquetas:
        return []
    alto = 26 + 18 * len(g.etiquetas)
    d = Drawing(ancho, alto)
    b = HorizontalBarChart()
    b.x, b.y, b.width, b.height = 150, 10, ancho - 190, alto - 20
    b.data = [list(reversed(s.valores)) for s in g.series]
    b.categoryAxis.categoryNames = list(reversed(g.etiquetas))
    b.categoryAxis.labels.fontSize = 7.5
    b.valueAxis.labels.fontSize = 7
    b.valueAxis.valueMin = 0
    b.valueAxis.labelTextFormat = lambda v: f"{v:,.0f}".replace(",", ".")
    b.bars[0].fillColor = VERDE
    b.bars[0].strokeColor = None
    b.barSpacing = 2
    d.add(b)
    return [KeepTogether([Paragraph(escape(g.titulo), est["h2"]), d])]


def generar_pdf(inf: Informe, autor: str) -> bytes:
    buf = BytesIO()
    tamano = landscape(A4) if inf.horizontal else A4
    doc = SimpleDocTemplate(buf, pagesize=tamano, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=16 * mm,
                            bottomMargin=16 * mm, title=inf.titulo, author="Universal de Repuestos WG")
    est, ancho = _estilos(), tamano[0] - 30 * mm
    historia = [Paragraph(escape(inf.titulo), est["titulo"])]
    if inf.subtitulo:
        historia.append(Paragraph(escape(inf.subtitulo), est["sub"]))
    if inf.parametros:
        historia.append(Paragraph(" · ".join(f"<b>{escape(k)}:</b> {escape(v)}" for k, v in inf.parametros), est["sub"]))
    historia.append(Spacer(1, 4))
    for bloque in inf.bloques:
        historia += _tabla(bloque, est, ancho) if isinstance(bloque, Tabla) else _grafico(bloque, est, ancho)

    pie = f"Universal de Repuestos WG · generado por {autor} el {datetime.now():%d/%m/%Y %H:%M}"

    def decorar(c, d):
        c.saveState()
        c.setFont("Helvetica", 7.5)
        c.setFillColor(colors.HexColor("#5b6a61"))
        c.drawString(15 * mm, 9 * mm, pie)
        c.drawRightString(tamano[0] - 15 * mm, 9 * mm, f"Página {d.page}")
        c.setFillColor(VERDE)
        c.rect(0, tamano[1] - 5, tamano[0], 5, stroke=0, fill=1)
        c.restoreState()

    doc.build(historia, onFirstPage=decorar, onLaterPages=decorar)
    return buf.getvalue()
