"""Consultas de ventas, pagos, entregas y facturas (SQL parametrizado)."""
from __future__ import annotations

from datetime import datetime

from Seguridad.contratos import EjecutorSQL

_VENTA = """SELECT s.sale_id, s.user_id, s.sale_type_id, ss.name AS state, s.company_warehouse_id, s.customer_name,
                   s.description, s.sale_date, s.subtotal, s.tax, s.total
            FROM sale s JOIN sale_state ss ON ss.sale_state_id = s.sale_state_id"""


class RepositorioVentas:
    def __init__(self, db: EjecutorSQL):
        self._db = db

    def tipo_venta(self, sale_type_id: int | None) -> int | None:
        if sale_type_id:
            f = self._db.fetch_one("SELECT sale_type_id FROM sale_type WHERE sale_type_id = %s AND state", (sale_type_id,))
        else:
            f = self._db.fetch_one("SELECT sale_type_id FROM sale_type WHERE name = 'En línea'")
        return f["sale_type_id"] if f else None

    def crear(self, venta: dict, lineas: list[dict]) -> int:
        sale_id = self._db.fetch_one(
            """INSERT INTO sale (user_id, sale_type_id, sale_state_id, company_warehouse_id, customer_name, description,
                                 subtotal, tax, total)
               VALUES (%(user_id)s, %(sale_type_id)s, (SELECT sale_state_id FROM sale_state WHERE name = %(state)s),
                       %(company_warehouse_id)s, %(customer_name)s, %(description)s, %(subtotal)s, %(tax)s, %(total)s)
               RETURNING sale_id""", venta)["sale_id"]
        for li in lineas:
            self._db.execute("INSERT INTO sale_detail (sale_id, product_id, quantity, unit_price, discount, subtotal) "
                             "VALUES (%s, %s, %s, %s, %s, %s)",
                             (sale_id, li["product_id"], li["quantity"], li["unit_price"], li["discount"], li["subtotal"]))
        return sale_id

    def obtener(self, sale_id: int, bloquear: bool = False) -> dict | None:
        if bloquear:       # se bloquea solo la fila de sale (el catálogo de estados no necesita bloqueo)
            self._db.fetch_one("SELECT sale_id FROM sale WHERE sale_id = %s FOR UPDATE", (sale_id,))
        return self._db.fetch_one(_VENTA + " WHERE s.sale_id = %s", (sale_id,))

    def detalle(self, sale_id: int) -> list[dict]:
        return self._db.fetch_all("SELECT d.*, p.name AS product_name FROM sale_detail d JOIN product p ON p.product_id = d.product_id "
                                  "WHERE d.sale_id = %s ORDER BY d.sale_detail_id", (sale_id,))

    def listar(self, user_id: int | None = None, estado: str | None = None) -> list[dict]:
        return self._db.fetch_all(
            """SELECT * FROM v_venta_resumen
               WHERE (%(u)s::bigint IS NULL OR user_id = %(u)s::bigint) AND (%(e)s::text IS NULL OR state = %(e)s::text)
               ORDER BY sale_id DESC""", {"u": user_id, "e": estado})

    def cambiar_estado(self, sale_id: int, estado: str) -> None:
        self._db.execute("UPDATE sale SET sale_state_id = (SELECT sale_state_id FROM sale_state WHERE name = %s) "
                         "WHERE sale_id = %s", (estado, sale_id))

    # ------------------------------------------------------------ pagos
    def registrar_pago(self, sale_id: int, monto, metodo: str, referencia: str) -> None:
        self._db.execute("INSERT INTO payment (sale_id, amount, method, reference, status, receipt_issued) "
                         "VALUES (%s, %s, %s, %s, 'aprobado', TRUE)", (sale_id, monto, metodo, referencia))

    def pagos(self, sale_id: int) -> list[dict]:
        return self._db.fetch_all("SELECT * FROM payment WHERE sale_id = %s ORDER BY payment_id", (sale_id,))

    def contar_por_estado(self) -> list[dict]:
        return self._db.fetch_all("SELECT state, cantidad, total FROM v_ventas_por_estado ORDER BY sale_state_id")


class RepositorioEntregas:
    def __init__(self, db: EjecutorSQL):
        self._db = db

    def crear(self, sale_id: int, direccion: str) -> int:
        return self._db.fetch_one("INSERT INTO delivery (sale_id, address) VALUES (%s, %s) RETURNING delivery_id",
                                  (sale_id, direccion))["delivery_id"]

    def obtener(self, delivery_id: int, bloquear: bool = False) -> dict | None:
        consulta = "SELECT * FROM delivery WHERE delivery_id = %s FOR UPDATE" if bloquear else \
            "SELECT * FROM delivery WHERE delivery_id = %s"
        return self._db.fetch_one(consulta, (delivery_id,))

    def por_venta(self, sale_id: int) -> dict | None:
        return self._db.fetch_one("SELECT * FROM v_entrega_detalle WHERE sale_id = %s", (sale_id,))

    def por_guia(self, guia: str) -> dict | None:
        return self._db.fetch_one("SELECT tracking_number, status, address, delivery_date FROM delivery WHERE tracking_number = %s",
                                  (guia,))

    def listar(self, estado: str | None = None, repartidor: int | None = None) -> list[dict]:
        return self._db.fetch_all(
            """SELECT * FROM v_entrega_detalle
               WHERE (%(e)s::text IS NULL OR status = %(e)s::text)
                 AND (%(r)s::bigint IS NULL OR assigned_user_id = %(r)s::bigint)
               ORDER BY delivery_id""", {"e": estado, "r": repartidor})

    def actualizar(self, delivery_id: int, *, status: str | None = None, tracking_number: str | None = None,
                   assigned_user_id: int | None = None, delivery_date: datetime | None = None) -> None:
        self._db.execute(
            """UPDATE delivery SET status = COALESCE(%s, status), tracking_number = COALESCE(%s, tracking_number),
                      assigned_user_id = COALESCE(%s, assigned_user_id), delivery_date = COALESCE(%s, delivery_date)
               WHERE delivery_id = %s""", (status, tracking_number, assigned_user_id, delivery_date, delivery_id))


class RepositorioFacturas:
    def __init__(self, db: EjecutorSQL):
        self._db = db

    def crear(self, factura: dict, lineas: list[dict]) -> int:
        invoice_id = self._db.fetch_one(
            """INSERT INTO electronic_invoice (sale_id, invoice_number, issue_date, subtotal, tax, total, qr_code, pdf_path, xml_path)
               VALUES (%(sale_id)s, %(invoice_number)s, %(issue_date)s, %(subtotal)s, %(tax)s, %(total)s, %(qr_code)s,
                       %(pdf_path)s, %(xml_path)s) RETURNING invoice_id""", factura)["invoice_id"]
        for li in lineas:
            self._db.execute("INSERT INTO invoice_detail (invoice_id, product_id, quantity, unit_price, discount, tax, subtotal) "
                             "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                             (invoice_id, li["product_id"], li["quantity"], li["unit_price"], li["discount"], li["tax"],
                              li["subtotal"]))
        return invoice_id

    def obtener(self, invoice_id: int) -> dict | None:
        return self._db.fetch_one("SELECT * FROM electronic_invoice WHERE invoice_id = %s", (invoice_id,))

    def por_venta(self, sale_id: int) -> dict | None:
        return self._db.fetch_one("SELECT * FROM electronic_invoice WHERE sale_id = %s", (sale_id,))

    def lineas(self, invoice_id: int) -> list[dict]:
        return self._db.fetch_all("SELECT d.*, p.name AS product_name FROM invoice_detail d JOIN product p ON p.product_id = d.product_id "
                                  "WHERE d.invoice_id = %s ORDER BY d.invoice_detail_id", (invoice_id,))

    def actualizar_rutas(self, invoice_id: int, pdf: str, xml: str) -> None:
        self._db.execute("UPDATE electronic_invoice SET pdf_path = %s, xml_path = %s WHERE invoice_id = %s", (pdf, xml, invoice_id))

    def contar(self) -> int:
        return self._db.fetch_one("SELECT COUNT(*) AS n FROM electronic_invoice")["n"]


class RepositorioEmpresa:
    def __init__(self, db: EjecutorSQL):
        self._db = db

    def bodega_activa(self, bodega: int) -> bool:
        return self._db.fetch_one("SELECT 1 AS x FROM company_warehouse WHERE company_warehouse_id = %s AND state",
                                  (bodega,)) is not None

    def bodega_principal(self) -> int | None:
        f = self._db.fetch_one("SELECT company_warehouse_id FROM company_warehouse WHERE state ORDER BY company_warehouse_id LIMIT 1")
        return f["company_warehouse_id"] if f else None

    def empresa_de_bodega(self, bodega: int) -> dict | None:
        return self._db.fetch_one("SELECT c.* FROM company c JOIN company_warehouse w ON w.company_id = c.company_id "
                                  "WHERE w.company_warehouse_id = %s", (bodega,))


class RepositorioPersonas:
    def __init__(self, db: EjecutorSQL):
        self._db = db

    def crear(self, datos: dict) -> int:
        return self._db.fetch_one(
            """INSERT INTO person (city_id, document_type_id, first_name, second_name, last_name, second_last_name,
                                   birth_date, identification, email, phone_number)
               VALUES (%(city_id)s, %(document_type_id)s, %(first_name)s, %(second_name)s, %(last_name)s,
                       %(second_last_name)s, %(birth_date)s, %(identification)s, %(email)s, %(phone_number)s)
               RETURNING person_id""", datos)["person_id"]

    def identificacion_existe(self, identificacion: str) -> bool:
        return self._db.fetch_one("SELECT 1 AS x FROM person WHERE identification = %s", (identificacion,)) is not None

    def nombre_de_usuario(self, user_id: int) -> str:
        f = self._db.fetch_one("SELECT p.first_name || ' ' || p.last_name AS n FROM app_user u "
                               "JOIN person p ON p.person_id = u.person_id WHERE u.user_id = %s", (user_id,))
        return f["n"] if f else ""

    def existe(self, tabla: str, id_: int) -> bool:
        consultas = {"city": "SELECT 1 AS x FROM city WHERE city_id = %s AND state",
                     "document_type": "SELECT 1 AS x FROM document_type WHERE document_type_id = %s AND state"}
        return self._db.fetch_one(consultas[tabla], (id_,)) is not None
