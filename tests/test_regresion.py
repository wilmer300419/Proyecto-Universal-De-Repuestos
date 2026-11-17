"""Pruebas de regresión: una por cada bug corregido en la auditoría (ver docs/INFORME_AUDITORIA.md).

Las marcadas con la base de datos usan los fixtures de conftest.py y se omiten sin TEST_DATABASE_URL.
"""
import os
from decimal import Decimal

import pytest
from ayudas import post

from app.config import Configuracion
from app.documentos.factura import DocumentosFactura
from app.models import negocio as N
from app.models.errores import ErrorValidacion
from app.models.validacion import a_booleano, a_entero, patron_like


# ------------------------------------------------------------------ sin base de datos
def test_bug08_dir_facturas_relativo_se_vuelve_absoluto(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql://x/y")
    monkeypatch.setenv("DIR_FACTURAS", "facturas")
    cfg = Configuracion.desde_entorno()
    assert os.path.isabs(cfg.dir_facturas) and cfg.dir_facturas == str(tmp_path / "facturas")
    assert os.path.isabs(DocumentosFactura("facturas")._dir)


def test_bug03_booleano_estricto():
    assert a_booleano("false") is False and a_booleano("0") is False and a_booleano("no") is False
    assert a_booleano("true") is True and a_booleano(1) is True and a_booleano(True) is True
    with pytest.raises(ErrorValidacion):
        a_booleano("tal vez")


def test_bug11_dinero_rechaza_bool_y_no_finitos():
    for malo in (True, "NaN", "Infinity", "abc", None):
        with pytest.raises(ErrorValidacion):
            N.dinero(malo)
    assert N.dinero("10.005") == Decimal("10.01")


def test_bug06_patron_like_escapa_comodines():
    assert patron_like("50%_off") == "%50\\%\\_off%"
    assert patron_like("a\\b") == "%a\\\\b%"


def test_entero_estricto():
    assert a_entero(" 7 ", "x", 1) == 7
    for malo in ("x", "1.5", True, None, 1.5):
        with pytest.raises(ErrorValidacion):
            a_entero(malo, "x")
    with pytest.raises(ErrorValidacion):
        a_entero(0, "x", 1)
    with pytest.raises(ErrorValidacion):
        a_entero(9, "x", maximo=5)


# ------------------------------------------------------------------ con base de datos
def test_bug01_filtro_no_numerico_en_catalogo_da_400(app):
    r = app.test_client().get("/api/cities?department_id=abc")
    assert r.status_code == 400 and "department_id" in r.get_json()["error"]


def test_bug02_state_vacio_usa_valor_por_defecto(admin):
    r = post(admin, "/api/car-brands", {"name": "Regresión state vacío", "state": ""})
    assert r.status_code == 201 and r.get_json()["state"] is True


def test_bug03_status_false_desactiva_usuario(admin):
    u = next(x for x in admin.get("/api/usuarios").get_json() if x["username"] == "lpardo")
    r = post(admin, f"/api/usuarios/{u['user_id']}", {"role": u["role"], "status": "false"}, "put")
    assert r.status_code == 200 and r.get_json()["status"] is False
    assert post(admin, f"/api/usuarios/{u['user_id']}", {"status": "true"}, "put").get_json()["status"] is True


def test_bug04_bodega_no_numerica_da_400(cliente):
    r = post(cliente, "/api/sales", {"company_warehouse_id": "x", "items": [{"product_id": 1, "quantity": 1}]})
    assert r.status_code == 400 and "company_warehouse_id" in r.get_json()["error"]


def test_bug05_bodega_inexistente_no_se_reporta_como_stock(cliente):
    r = post(cliente, "/api/sales", {"company_warehouse_id": 999, "items": [{"product_id": 1, "quantity": 1}]})
    assert r.status_code == 400 and "bodega" in r.get_json()["error"].lower()


def test_bug06_busqueda_con_comodines_es_literal(app):
    c = app.test_client()
    assert c.get("/api/products?q=%25").get_json() == []
    assert c.get("/api/products?q=_").get_json() == []
    assert c.get("/api/products?q=radiador").get_json()


def test_bug07_producto_con_vehiculo_inexistente_da_400(admin):
    r = post(admin, "/api/products", {"name": "Prueba", "unit_price": 10, "fk_car_product": [99999]})
    assert r.status_code == 400 and "99999" in r.get_json()["error"]


def test_bug08_descarga_de_factura_con_ruta_relativa_guardada(app, admin):
    db = app.extensions["db"]
    inv = db.fetch_one("SELECT invoice_id FROM electronic_invoice ORDER BY invoice_id LIMIT 1")["invoice_id"]
    db.execute("UPDATE electronic_invoice SET pdf_path = 'facturas/no-existe.pdf' WHERE invoice_id = %s", (inv,))
    r = admin.get(f"/api/invoices/{inv}/pdf")
    assert r.status_code == 200 and r.data[:4] == b"%PDF"


def test_bug09_stock_por_bodega(app):
    c = app.test_client()
    total = c.get("/api/products/2").get_json()["stock_total"]
    bodega1 = c.get("/api/products/2?warehouse_id=1").get_json()["stock_total"]
    fila = app.extensions["db"].fetch_one("SELECT quantity_available FROM inventory WHERE product_id = 2 AND company_warehouse_id = 1")
    assert bodega1 == fila["quantity_available"] and bodega1 <= total
    listado = {p["product_id"]: p["stock_total"] for p in c.get("/api/products?warehouse_id=1").get_json()}
    assert listado[2] == bodega1


def test_bug11_monto_booleano_en_pago_da_400(cliente):
    sid = post(cliente, "/api/sales", {"items": [{"product_id": 7, "quantity": 1}]}).get_json()["sale_id"]
    assert post(cliente, f"/api/sales/{sid}/payments", {"method": "pse", "amount": True}).status_code == 400
    assert post(cliente, f"/api/sales/{sid}/cancel").status_code == 200


def test_bug10_purga_de_sesiones_antiguas(app):
    db = app.extensions["db"]
    db.execute("""INSERT INTO sesion_jwt (jti, user_id, emitido_en, expira_en, agente_hash)
                  VALUES ('viejisima', 1, now() - INTERVAL '400 days', now() - INTERVAL '399 days', repeat('0', 64))""")
    from ayudas import iniciar_sesion
    from conftest import CLAVE
    assert iniciar_sesion(app, app.test_client(), "admin", CLAVE).status_code == 200
    assert db.fetch_one("SELECT COUNT(*) AS n FROM sesion_jwt WHERE jti = 'viejisima'")["n"] == 0
    assert db.fetch_one("SELECT COUNT(*) AS n FROM sesion_jwt")["n"] >= 20             # el historial reciente se conserva
