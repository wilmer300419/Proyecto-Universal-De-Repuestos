from __future__ import annotations

from ..repositories.reportes import RepositorioReportes
from .base import Reporte
from .tienda import ReporteEntregas, ReporteInventario, ReporteMasVendidos, ReporteVentas

CLASES_REPORTE: tuple[type[Reporte], ...] = (ReporteVentas, ReporteMasVendidos, ReporteInventario, ReporteEntregas)


def construir_reportes(repo: RepositorioReportes, filas_max: int) -> dict[str, Reporte]:
    return {c.slug: c(repo, filas_max) for c in CLASES_REPORTE}
