"""Pruebas de integración (PostgreSQL real con migraciones y datos de prueba)."""
from ayudas import captcha_resuelto, iniciar_sesion, post
from conftest import CLAVE


# ------------------------------------------------------------------ seguridad
def test_rutas_protegidas(app):
    c = app.test_client()
    assert c.get("/api/sales").status_code == 401
    assert c.get("/api/auth/yo").status_code == 401
    assert c.get("/api/products").status_code == 200                       # catálogo público
    assert c.get("/api/companies").status_code == 401                      # catálogo solo para el administrador


def test_login_exige_captcha_y_no_revela_usuarios(app):
    c = app.test_client()
    token, _ = captcha_resuelto(app)
    r = c.post("/api/auth/sesion", json={"usuario": "admin", "password": CLAVE, "captcha_token": token, "captcha": "MALO1"})
    assert r.status_code == 401 and "verificación" in r.get_json()["error"]
    m1 = iniciar_sesion(app, c, "admin", "incorrecta").get_json()["error"]
    m2 = iniciar_sesion(app, c, "no_existe", "incorrecta").get_json()["error"]
    assert m1 == m2 == "Usuario o contraseña incorrectos."


def test_cookie_httponly_csrf_y_logout_revoca(app):
    c = app.test_client()
    r = iniciar_sesion(app, c, "atorres", CLAVE)
    cookie = r.headers["Set-Cookie"]
    assert r.status_code == 200 and "HttpOnly" in cookie and "SameSite=Strict" in cookie
    assert "access_token" not in r.get_json()                              # el JWT nunca llega al JavaScript
    token, csrf = c.get_cookie("access_token").value, r.get_json()["csrf_token"]
    assert c.post("/api/sales/1/cancel").status_code == 400                 # escritura sin CSRF
    assert c.post("/api/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 200
    r = app.test_client().get("/api/auth/yo", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401                                             # la sesión quedó revocada


def test_bloqueo_por_intentos_fallidos(app):
    c = app.test_client()
    for _ in range(5):
        iniciar_sesion(app, c, "ralvarez", "mala")
    r = iniciar_sesion(app, c, "ralvarez", CLAVE)
    assert r.status_code == 401 and "bloqueada" in r.get_json()["error"]
    app.extensions["db"].execute("UPDATE app_user SET bloqueado_hasta = NULL, intentos_fallidos = 0 WHERE username = 'ralvarez'")


def test_token_bearer_para_api(app):
    c = app.test_client()
    r = iniciar_sesion(app, c, "admin", CLAVE, "/api/auth/token")
    assert r.status_code == 200 and r.get_json()["token_type"] == "Bearer"
    h = {"Authorization": "Bearer " + r.get_json()["access_token"]}
    assert c.get("/api/reports/summary", headers=h).status_code == 200
    assert c.get("/api/auth/sesiones", headers=h).get_json()[0]["actual"] is True


def test_roles(cliente, empacador):
    assert cliente.get("/api/inventory").status_code == 403
    assert cliente.get("/api/usuarios").status_code == 403
    assert empacador.get("/api/inventory").status_code == 200
    assert post(empacador, "/api/products", {"name": "x", "unit_price": 1}).status_code == 403


def test_registro_de_cliente_y_politica(app):
    c = app.test_client()
    base = {"first_name": "Prueba", "last_name": "Registro", "identification": "99887766", "document_type_id": 1,
            "city_id": 1, "email": "prueba.registro@correo.co", "username": "prueba.registro"}
    r = c.post("/api/clientes", json={**base, "password": "corta"})
    assert r.status_code == 400 and "caracteres" in r.get_json()["error"]
    assert c.post("/api/clientes", json={**base, "password": "Segura#Clave2026"}).status_code == 201
    assert c.post("/api/clientes", json={**base, "password": "Segura#Clave2026"}).status_code == 400   # duplicado
    assert iniciar_sesion(app, c, "prueba.registro", "Segura#Clave2026").status_code == 200


# ------------------------------------------------------------------ catálogos y productos
def test_catalogo_generico_y_auditoria(admin):
    assert len(admin.get("/api/car-brands?state=true").get_json()) >= 20
    r = post(admin, "/api/car-brands", {"name": "Marca de prueba"})
    assert r.status_code == 201
    pk = r.get_json()["car_brand_id"]
    assert post(admin, f"/api/car-brands/{pk}", {"description": "editada"}, "put").get_json()["description"] == "editada"
    assert post(admin, "/api/car-brands", {"name": "Marca de prueba"}).status_code == 409              # único
    assert post(admin, "/api/sale-states/1", {"name": "Otro"}, "put").status_code == 409             # protegido
    assert post(admin, f"/api/car-brands/{pk}", metodo="delete").status_code == 204
    acciones = admin.get("/api/auditoria?accion=ELIMINAR").get_json()
    assert acciones["total"] >= 1 and acciones["filas"][0]["entidad"] == "car-brands"


def test_busqueda_de_productos(app):
    c = app.test_client()
    radiadores = c.get("/api/products?type_id=1").get_json()
    assert radiadores and all(p["category"] == "Radiadores" for p in radiadores)
    mazda = c.get("/api/cars/1/products").get_json()
    assert mazda and all(1 in p["fk_car_product"] for p in mazda)
    assert c.get("/api/products?q=radiador").get_json()
    assert c.get("/api/cars/9999/products").status_code == 404


# ------------------------------------------------------------------ flujo completo de venta
def test_flujo_completo(app, admin, cliente, empacador, repartidor):
    p1, p2 = app.test_client().get("/api/products/1").get_json(), app.test_client().get("/api/products/2").get_json()
    r = post(cliente, "/api/sales", {"company_warehouse_id": 1, "address": "Calle 72 #11-30, Bogotá",
                                     "items": [{"product_id": 1, "quantity": 2}, {"product_id": 2, "quantity": 1}]})
    assert r.status_code == 201, r.get_json()
    venta = r.get_json()
    esperado = round((p1["unit_price"] * 2 + p2["unit_price"]) * 1.19, 2)
    assert venta["state"] == "Pendiente" and venta["total"] == esperado and venta["delivery"]["status"] == "pendiente"
    sid, did = venta["sale_id"], venta["delivery"]["delivery_id"]
    assert app.test_client().get("/api/products/1").get_json()["stock_total"] == p1["stock_total"] - 2      # stock reservado

    assert post(cliente, "/api/sales", {"items": [{"product_id": 2, "quantity": 9999}]}).status_code == 409
    assert post(empacador, f"/api/deliveries/{did}/prepare").status_code == 409                          # sin pago
    assert post(cliente, f"/api/sales/{sid}/payments", {"method": "bitcoin"}).status_code == 400
    r = post(cliente, f"/api/sales/{sid}/payments", {"method": "tarjeta_credito", "card_last4": "4111111111111111"})
    assert r.status_code == 201 and r.get_json()["state"] == "Pagada"
    assert r.get_json()["payments"][0]["reference"].endswith("-****1111")
    assert post(cliente, f"/api/sales/{sid}/payments", {"method": "pse"}).status_code == 409             # doble pago
    assert post(cliente, f"/api/sales/{sid}/cancel").status_code == 409

    assert post(cliente, f"/api/sales/{sid}/invoice").status_code == 403
    factura = post(admin, f"/api/sales/{sid}/invoice")
    assert factura.status_code == 201
    pdf = cliente.get(f"/api/invoices/{factura.get_json()['invoice_id']}/pdf")
    assert pdf.mimetype == "application/pdf" and pdf.data[:4] == b"%PDF"

    assert post(empacador, f"/api/deliveries/{did}/prepare").get_json()["status"] == "empacado"
    rep = repartidor.get("/api/auth/yo").get_json()["user_id"]
    assert post(admin, f"/api/deliveries/{did}/assign", {"user_id": 3}).status_code == 400               # no es repartidor
    assert post(admin, f"/api/deliveries/{did}/assign", {"user_id": rep}).status_code == 200
    assert post(repartidor, f"/api/deliveries/{did}/status", {"status": "entregado"}, "patch").status_code == 409
    assert post(repartidor, f"/api/deliveries/{did}/status", {"status": "en_camino"}, "patch").status_code == 200
    assert post(repartidor, f"/api/deliveries/{did}/status", {"status": "entregado"}, "patch").status_code == 200
    assert cliente.get(f"/api/sales/{sid}").get_json()["state"] == "Entregada"


def test_cancelacion_devuelve_stock(app, cliente):
    antes = app.test_client().get("/api/products/5").get_json()["stock_total"]
    sid = post(cliente, "/api/sales", {"address": "Carrera 7 #45-12", "items": [{"product_id": 5, "quantity": 3}]}).get_json()["sale_id"]
    r = post(cliente, f"/api/sales/{sid}/cancel")
    assert r.status_code == 200 and r.get_json()["state"] == "Cancelada" and r.get_json()["delivery"]["status"] == "cancelado"
    assert app.test_client().get("/api/products/5").get_json()["stock_total"] == antes


def test_cliente_no_ve_ventas_ajenas(app, cliente):
    ajenas = app.extensions["db"].fetch_one("SELECT sale_id FROM sale s JOIN app_user u ON u.user_id = s.user_id "
                                            "WHERE u.username <> 'lhernandez' LIMIT 1")["sale_id"]
    assert cliente.get(f"/api/sales/{ajenas}").status_code == 404
    assert all(v["username"] == "lhernandez" for v in cliente.get("/api/sales").get_json())


def test_factura_de_datos_de_prueba_se_regenera(admin):
    inv = admin.get("/api/sales/1/invoice")
    if inv.status_code == 200:
        r = admin.get(f"/api/invoices/{inv.get_json()['invoice_id']}/pdf")
        assert r.status_code == 200 and r.data[:4] == b"%PDF"


# ------------------------------------------------------------------ reportes
def test_resumen_y_reportes_pdf(admin):
    r = admin.get("/api/reports/summary").get_json()
    assert r["sales_count"] > 0 and r["monthly"] and r["top_products"] and len(r["by_state"]) == 5
    lista = admin.get("/api/reportes").get_json()
    assert {x["slug"] for x in lista} == {"ventas", "mas-vendidos", "inventario", "entregas"}
    for x in lista:
        assert admin.get(f"/api/reportes/{x['slug']}").status_code == 200, x["slug"]
        pdf = admin.get(f"/api/reportes/{x['slug']}/pdf")
        assert pdf.mimetype == "application/pdf" and pdf.data[:4] == b"%PDF"
    assert admin.get("/api/reportes/ventas?desde=2026-12-01&hasta=2026-01-01").status_code == 400


def test_admin_gestiona_usuarios_y_revoca_sesiones(app, admin):
    otro = app.test_client()
    assert iniciar_sesion(app, otro, "jramirez", CLAVE).status_code == 200
    u = next(x for x in admin.get("/api/usuarios").get_json() if x["username"] == "jramirez")
    assert u["sesiones_activas"] >= 1
    r = post(admin, f"/api/usuarios/{u['user_id']}", {"role": "repartidor", "status": True}, "put")
    assert r.status_code == 200 and r.get_json()["role"] == "repartidor" and r.get_json()["sesiones_activas"] == 0
    assert otro.get("/api/auth/yo").status_code == 401                     # cambio de rol = sesiones revocadas
    yo = admin.get("/api/auth/yo").get_json()["user_id"]
    assert post(admin, f"/api/usuarios/{yo}", {"role": "cliente"}, "put").status_code == 409


# ------------------------------------------------------------------ administración de productos e inventario
def test_admin_gestiona_producto_e_inventario(app, admin, empacador):
    r = post(admin, "/api/products", {"name": "Producto de prueba", "description": "  ", "unit_price": "1500.5",
                                      "fk_car_product": [1, "2", 1]})
    assert r.status_code == 201, r.get_json()
    p = r.get_json()
    assert p["fk_car_product"] == [1, 2] and p["description"] is None and p["unit_price"] == 1500.5
    pid = p["product_id"]
    assert post(admin, "/api/products", {"name": "", "unit_price": 1}).status_code == 400
    assert post(admin, "/api/products", {"name": "x", "unit_price": -1}).status_code == 400
    assert post(admin, "/api/products", {"name": "x", "unit_price": 1, "fk_car_product": "1"}).status_code == 400
    sp = post(admin, "/api/spare-parts", {"product_id": pid, "name": "Producto de prueba", "spare_part_type_id": 2,
                                          "spare_part_brand_id": 1}).get_json()
    r = post(admin, f"/api/products/{pid}", {"fk_spare_part": sp["spare_part_id"], "unit_price": 2000}, "put")
    assert r.get_json()["category"] == "Filtros" and r.get_json()["unit_price"] == 2000
    assert post(admin, "/api/products/999999", {"name": "x"}, "put").status_code == 404

    inv = post(admin, "/api/inventory", {"product_id": pid, "company_warehouse_id": 1, "quantity_available": 4,
                                         "reorder_stock": 5})
    assert inv.status_code == 201 and inv.get_json()["needs_reorder"] is True
    assert post(admin, "/api/inventory", {"product_id": pid, "company_warehouse_id": 1, "quantity_available": 1}).status_code == 409
    iid = inv.get_json()["inventory_id"]
    assert post(admin, f"/api/inventory/{iid}", {"quantity_available": 30}, "put").get_json()["needs_reorder"] is False
    assert post(admin, f"/api/inventory/{iid}", {"quantity_available": -1}, "put").status_code == 400
    assert post(admin, f"/api/inventory/{iid}", {}, "put").status_code == 400
    assert post(admin, "/api/inventory/999999", {"quantity_available": 1}, "put").status_code == 404
    assert any(i["inventory_id"] == iid for i in empacador.get("/api/inventory?warehouse_id=1").get_json())
    assert all(i["needs_reorder"] for i in empacador.get("/api/inventory?low=1").get_json())
    assert post(empacador, f"/api/inventory/{iid}", {"quantity_available": 1}, "put").status_code == 403

    assert post(admin, f"/api/products/{pid}", metodo="delete").status_code == 204
    assert all(x["product_id"] != pid for x in app.test_client().get("/api/products").get_json())


def test_entregas_y_rastreo(app, admin, empacador, repartidor):
    pendientes = empacador.get("/api/deliveries?status=pendiente").get_json()
    assert pendientes and all(d["status"] == "pendiente" for d in pendientes)
    guia = next(d["tracking_number"] for d in admin.get("/api/deliveries").get_json() if d["tracking_number"])
    r = app.test_client().get(f"/api/deliveries/track/{guia}")
    assert r.status_code == 200 and set(r.get_json()) == {"tracking_number", "status", "address", "delivery_date"}
    assert app.test_client().get("/api/deliveries/track/NO-EXISTE").status_code == 404
    asignadas = repartidor.get("/api/deliveries/assigned").get_json()
    otra = next(d for d in admin.get("/api/deliveries?status=en_camino").get_json()
                if d["delivery_id"] not in {a["delivery_id"] for a in asignadas})
    r = post(repartidor, f"/api/deliveries/{otra['delivery_id']}/status", {"status": "entregado"}, "patch")
    assert r.status_code == 403                                              # no es su entrega
    assert post(admin, "/api/deliveries/999999/prepare").status_code == 404


def test_comandos_de_consola(app):
    runner = app.test_cli_runner()
    r = runner.invoke(args=["estado-migraciones"])
    assert r.exit_code == 0 and "V006" in r.output and "PENDIENTE" not in r.output
    assert "ninguna" in runner.invoke(args=["migrar"]).output
    r = runner.invoke(args=["cargar-datos"])
    assert r.exit_code != 0 and "ya tiene usuarios" in r.output
    import os
    os.environ["USUARIO_PASSWORD"] = "Interno#Seguro2026"
    try:
        r = runner.invoke(args=["crear-usuario", "interno.cli", "--rol", "empacador", "--email", "interno.cli@correo.co",
                                "--nombre", "Interno", "--apellido", "Cli", "--documento", "55443322"])
        assert r.exit_code == 0 and "Usuario creado" in r.output
        r = runner.invoke(args=["crear-usuario", "interno.cli", "--rol", "empacador", "--email", "otro@correo.co",
                                "--nombre", "Interno", "--apellido", "Cli", "--documento", "55443323"])
        assert r.exit_code != 0 and "ya está registrado" in r.output
    finally:
        del os.environ["USUARIO_PASSWORD"]
