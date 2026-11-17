"""Pruebas de seguridad: JWT, RBAC ADMIN/USER, endpoints de la Guía 7 y controles OWASP."""
import jwt
import pytest
from ayudas import captcha_resuelto, iniciar_sesion, post
from conftest import CLAVE

from Seguridad.configuracion import ConfigSeguridad
from Seguridad.limitador import LimitadorPeticiones, Regla
from Seguridad.modelos import Grupo, Rol, Usuario, grupo_de
from Seguridad.tokens import ServicioJWT, TokenInvalido

CFG = ConfigSeguridad(jwt_secreto="s" * 48)


# ------------------------------------------------------------------ unitarias
def test_grupos_rbac():
    assert grupo_de(Rol.ADMINISTRADOR) is Grupo.ADMIN
    assert {grupo_de(r) for r in (Rol.CLIENTE, Rol.EMPACADOR, Rol.REPARTIDOR)} == {Grupo.USER}


def test_token_expirado_y_alterado_se_rechazan():
    u = Usuario(1, "ana", "a@b.co", Rol.ADMINISTRADOR)
    vencido, _ = ServicioJWT(ConfigSeguridad(jwt_secreto="s" * 48, jwt_expira_min=-1)).emitir(u)
    with pytest.raises(TokenInvalido):
        ServicioJWT(CFG).verificar(vencido)
    token, claims = ServicioJWT(CFG).emitir(u)
    assert claims.grp == "ADMIN"
    carga = jwt.decode(token, options={"verify_signature": False})
    carga["grp"] = carga["rol"] = "x"
    alterado = jwt.encode(carga, "otra-clave-" * 5, algorithm="HS256")
    with pytest.raises(TokenInvalido):
        ServicioJWT(CFG).verificar(alterado)
    otra_audiencia = jwt.encode({**jwt.decode(token, options={"verify_signature": False}), "aud": "otra"},
                                CFG.jwt_secreto, algorithm="HS256")
    with pytest.raises(TokenInvalido):
        ServicioJWT(CFG).verificar(otra_audiencia)


def test_limitador_ventana_deslizante():
    t = [0.0]
    lim = LimitadorPeticiones(reloj=lambda: t[0])
    regla = Regla(3, 60)
    assert [lim.permitir("ip", regla)[0] for _ in range(3)] == [True, True, True]
    permitido, espera = lim.permitir("ip", regla)
    assert not permitido and 1 <= espera <= 61
    assert lim.permitir("otra-ip", regla)[0]                 # el límite es por clave
    t[0] = 61.0
    assert lim.permitir("ip", regla)[0]                      # la ventana se desliza


def test_cors_rechaza_comodin(monkeypatch):
    from app.config import _origenes
    assert _origenes("https://tienda.co, http://localhost:5173/") == ("https://tienda.co", "http://localhost:5173")
    for malo in ("*", "http://sitio-inseguro.co"):
        with pytest.raises(RuntimeError):
            _origenes(malo)


# ------------------------------------------------------------------ endpoints de la Guía 7
def _bearer(app, usuario):
    r = iniciar_sesion(app, app.test_client(), usuario, CLAVE, "/api/auth/login")
    assert r.status_code == 200, r.get_json()
    return {"Authorization": "Bearer " + r.get_json()["access_token"]}, r.get_json()


def test_login_admin_user(app):
    c = app.test_client()
    h_admin, datos = _bearer(app, "admin")
    assert datos["rbac"] == "ADMIN" and datos["token_type"] == "Bearer" and datos["expires_in"] == 7200
    h_user, datos = _bearer(app, "mlopez")
    assert datos["rbac"] == "USER"
    assert c.get("/api/admin", headers=h_admin).status_code == 200
    assert c.get("/api/admin", headers=h_user).status_code == 403
    assert c.get("/api/user", headers=h_user).get_json()["rbac"] == "USER"
    assert c.get("/api/user", headers=h_admin).status_code == 200
    assert c.get("/api/admin").status_code == 401 and c.get("/api/user").status_code == 401
    assert c.get("/api/user", headers={"Authorization": "Bearer basura"}).status_code == 401


def test_credenciales_invalidas_en_login(app):
    c = app.test_client()
    r = iniciar_sesion(app, c, "admin", "mala", "/api/auth/login")
    assert r.status_code == 401 and r.get_json()["error"] == "Usuario o contraseña incorrectos."
    assert c.post("/api/auth/login", json={"usuario": "admin", "password": CLAVE}).status_code == 401   # sin CAPTCHA


def test_cambio_de_rol_surte_efecto_inmediato(app, admin):
    h, _ = _bearer(app, "jrodriguez")
    c = app.test_client()
    assert c.get("/api/user", headers=h).status_code == 200
    uid = next(u["user_id"] for u in admin.get("/api/usuarios").get_json() if u["username"] == "jrodriguez")
    post(admin, f"/api/usuarios/{uid}", {"status": False}, "put")
    assert c.get("/api/user", headers=h).status_code == 401                 # token revocado al desactivar
    post(admin, f"/api/usuarios/{uid}", {"status": True}, "put")


# ------------------------------------------------------------------ OWASP
def test_limite_de_intentos_429(app):
    c = app.test_client()
    codigos = [iniciar_sesion(app, c, "nadie", "x").status_code for _ in range(12)]
    assert codigos[:10] == [401] * 10 and codigos[10] == 429
    r = iniciar_sesion(app, c, "nadie", "x")
    assert r.status_code == 429 and int(r.headers["Retry-After"]) >= 1


def test_cabeceras_de_seguridad(app):
    r = app.test_client().get("/")
    for cabecera in ("Content-Security-Policy", "X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy",
                     "Permissions-Policy"):
        assert cabecera in r.headers
    assert "Strict-Transport-Security" not in r.headers                    # solo con COOKIE_SEGURA=true (HTTPS)
    assert app.test_client().get("/api/products").headers["Cache-Control"] == "no-store"


def test_cors_solo_lista_blanca(app):
    c = app.test_client()
    r = c.get("/api/products", headers={"Origin": "https://atacante.co"})
    assert "Access-Control-Allow-Origin" not in r.headers
    pre = c.options("/api/sales", headers={"Origin": "https://atacante.co", "Access-Control-Request-Method": "POST"})
    assert "Access-Control-Allow-Origin" not in pre.headers


def test_cors_permite_origen_configurado(app):
    from dataclasses import replace

    from app import crear_app
    otra = crear_app(replace(app.config["CFG"], cors_origenes=("https://tienda.example",)))
    r = otra.test_client().get("/api/products", headers={"Origin": "https://tienda.example"})
    assert r.headers["Access-Control-Allow-Origin"] == "https://tienda.example"
    assert r.headers["Access-Control-Allow-Credentials"] == "true"
    otra.extensions["db"].cerrar()


def test_errores_no_filtran_detalles_internos(app):
    r = app.test_client().get("/api/no-existe")
    assert r.status_code == 404 and r.get_json() == {"error": "Recurso no encontrado"}


def test_inyeccion_sql_en_busqueda_es_inofensiva(app):
    c = app.test_client()
    for carga in ("' OR '1'='1", "1; DROP TABLE product;--", "%' OR 1=1 --"):
        r = c.get("/api/products", query_string={"q": carga})
        assert r.status_code == 200 and r.get_json() == []
    assert c.get("/api/products").get_json()                                # la tabla sigue ahí


def test_captcha_reutilizado_se_rechaza(app):
    token, texto = captcha_resuelto(app)
    c = app.test_client()
    datos = {"usuario": "admin", "password": CLAVE, "captcha_token": token, "captcha": texto}
    assert c.post("/api/auth/token", json=datos).status_code == 200
    assert c.post("/api/auth/token", json=datos).status_code == 401
