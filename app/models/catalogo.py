"""Catálogo de entidades administrables mediante el CRUD genérico (/api/<slug>)."""
from __future__ import annotations

from .meta import Campo, Entidad

ESTADO = Campo("state", "Activo", "booleano", requerido=False, por_defecto=True)
NOMBRE = Campo("name", "Nombre", max_len=100)
DESCRIPCION = Campo("description", "Descripción", requerido=False, max_len=255)


def _simple(slug: str, singular: str, tabla: str, pk: str, con_descripcion: bool = True, **kw) -> Entidad:
    campos = (NOMBRE, DESCRIPCION, ESTADO) if con_descripcion else (NOMBRE, ESTADO)
    return Entidad(slug, singular, tabla, pk, campos, **kw)


ENTIDADES: tuple[Entidad, ...] = (
    Entidad("document-types", "tipo de documento", "document_type", "document_type_id",
            (NOMBRE, Campo("acronym", "Sigla", max_len=20), ESTADO)),
    _simple("departments", "departamento", "department", "department_id"),
    Entidad("cities", "ciudad", "city", "city_id",
            (NOMBRE, Campo("department_id", "Departamento", "fk"), ESTADO)),
    _simple("car-brands", "marca de vehículo", "car_brand", "car_brand_id"),
    _simple("car-types", "tipo de vehículo", "car_type", "car_type_id"),
    _simple("cylinder-capacities", "cilindraje", "cylinder_capacity", "cylinder_capacity_id", con_descripcion=False),
    _simple("spare-part-types", "categoría de repuesto", "spare_part_type", "spare_part_type_id"),
    _simple("spare-part-brands", "marca de repuesto", "spare_part_brand", "spare_part_brand_id"),
    _simple("sale-types", "tipo de venta", "sale_type", "sale_type_id", ids_protegidos=(1,)),
    Entidad("sale-states", "estado de venta", "sale_state", "sale_state_id",
            (Campo("name", "Nombre", max_len=50), DESCRIPCION, ESTADO), ids_protegidos=(1, 2, 3, 4, 5)),
    Entidad("companies", "empresa", "company", "company_id",
            (Campo("tax_id", "NIT", max_len=50), Campo("name", "Razón social", max_len=150),
             Campo("address", "Dirección", requerido=False, max_len=255), Campo("phone", "Teléfono", requerido=False, max_len=30),
             Campo("cellphone", "Celular", requerido=False, max_len=30), Campo("email", "Correo", requerido=False, max_len=150),
             ESTADO), lectura_admin=True),
    Entidad("warehouses", "bodega", "company_warehouse", "company_warehouse_id",
            (Campo("company_id", "Empresa", "fk"), Campo("name", "Nombre", max_len=150),
             Campo("address", "Dirección", requerido=False, max_len=255), ESTADO), orden="company_warehouse_id"),
    Entidad("cars", "vehículo", "car", "car_id",
            (Campo("name", "Nombre", max_len=150), Campo("model", "Modelo (año)", requerido=False, max_len=100),
             Campo("chassis_number", "Número de chasis", requerido=False, max_len=100),
             Campo("cylinder_capacity_id", "Cilindraje", "fk"), Campo("car_brand_id", "Marca", "fk"),
             Campo("car_type_id", "Tipo", "fk"), Campo("product_id", "Producto", "fk", requerido=False), ESTADO)),
    Entidad("spare-parts", "repuesto", "spare_part", "spare_part_id",
            (Campo("product_id", "Producto", "fk"), Campo("name", "Nombre", max_len=150),
             Campo("spare_part_type_id", "Categoría", "fk"), Campo("spare_part_brand_id", "Marca", "fk"), ESTADO)),
)

POR_SLUG = {e.slug: e for e in ENTIDADES}
