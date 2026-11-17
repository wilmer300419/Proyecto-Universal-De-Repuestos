"""Pruebas unitarias (no requieren base de datos)."""
from datetime import datetime, UTC
from decimal import Decimal

import jwt
import pytest

from Seguridad.captcha import ServicioCaptcha
from Seguridad.configuracion import ConfigSeguridad
from Seguridad.contrasenas import HasherContrasena, PoliticaContrasena
from Seguridad.modelos import Rol, Usuario
from Seguridad.tokens import ServicioJWT, TokenInvalido
from app.models import negocio as N
from app.models.catalogo import ENTIDADES
from app.models.errores import ErrorDeNegocio, ErrorValidacion

CFG = ConfigSeguridad(jwt_secreto="s" * 48)
USUARIO = Usuario(7, "ana", "ana@correo.co", Rol.EMPACADOR)


# ------------------------------------------------------------------ seguridad
def test_politica_contrasena():
    p = PoliticaContrasena()
    assert p.validar("Repuestos#2026", "ana") == []
    assert len(p.validar("corta")) >= 4
    assert any("nombre de usuario" in e for e in p.validar("Ana#Clave2026xx", "ana"))


def test_hash_con_sal_y_no_reversible():
    h = HasherContrasena()
    a, b = h.cifrar("Repuestos#2026"), h.cifrar("Repuestos#2026")
    assert a != b and "Repuestos" not in a and h.verificar(a, "Repuestos#2026") and not h.verificar(a, "otra")


def test_jwt_solo_datos_no_sensibles():
    s = ServicioJWT(CFG)
    token, claims = s.emitir(USUARIO)
    carga = jwt.decode(token, CFG.jwt_secreto, algorithms=["HS256"], audience=CFG.jwt_audiencia)
    assert set(carga) == {"sub", "usr", "rol", "grp", "jti", "iat", "exp", "iss", "aud"}
    assert carga["grp"] == "USER"
    assert "ana@correo.co" not in token and s.verificar(token).usr == "ana" and claims.rol == "empacador"


def test_jwt_rechaza_firma_y_algoritmo_none():
    token, _ = ServicioJWT(CFG).emitir(USUARIO)
    with pytest.raises(TokenInvalido):
        ServicioJWT(ConfigSeguridad(jwt_secreto="otro" * 12)).verificar(token)
    sin_firma = jwt.encode({"sub": "1"}, key=None, algorithm="none")
    with pytest.raises(TokenInvalido):
        ServicioJWT(CFG).verificar(sin_firma)


def test_captcha_un_solo_uso():
    c = ServicioCaptcha("k" * 40)
    svg, token = c.generar()
    assert svg.startswith("<svg") and not c.validar(token, "XXXXX")
    nonce = jwt.decode(token, c._clave, algorithms=["HS256"])["n"]
    bueno = jwt.encode({"n": nonce, "h": c._firma(nonce, "ABCDE"), "typ": "captcha", "exp": 9999999999}, c._clave, algorithm="HS256")
    assert c.validar(bueno, "abcde") and not c.validar(bueno, "ABCDE")


# ------------------------------------------------------------------ negocio
P1 = N.LineaPedido(1, "Filtro", 2, Decimal("25000"))
P2 = N.LineaPedido(2, "Empaques", 1, Decimal("180000"))


def test_totales_con_iva():
    t = N.calcular_totales([P1, P2], 0.19)
    assert (t.subtotal, t.impuesto, t.total) == (Decimal("230000.00"), Decimal("43700.00"), Decimal("273700.00"))


def test_descuento_excesivo_y_items_invalidos():
    with pytest.raises(ErrorValidacion):
        N.calcular_totales([N.LineaPedido(1, "Filtro", 1, Decimal("100"), Decimal("200"))], 0.19)
    with pytest.raises(ErrorValidacion):
        N.unir_items([{"product_id": 1, "quantity": 0}])
    assert N.unir_items([{"product_id": 1, "quantity": 2}, {"product_id": "1", "quantity": 1}]) == {1: (3, Decimal("0.00"))}


def test_pago_reglas():
    assert N.normalizar_metodo_pago("Tarjeta") == "tarjeta_credito"
    with pytest.raises(ErrorValidacion):
        N.normalizar_metodo_pago("bitcoin")
    assert N.validar_pago("Pendiente", Decimal("273700.00"), 273700.0, 1) == Decimal("273700.00")
    with pytest.raises(ErrorValidacion):
        N.validar_pago("Pendiente", Decimal("100.00"), 50, 1)
    with pytest.raises(ErrorDeNegocio):
        N.validar_pago("Pagada", Decimal("100.00"), None, 1)


def test_transiciones_de_entrega():
    assert N.transicion_entrega("empacado", "en_camino") == "Despachada"
    assert N.transicion_entrega("en_camino", "entregado") == "Entregada"
    with pytest.raises(ErrorDeNegocio):
        N.transicion_entrega("empacado", "entregado")          # no se puede saltar un paso
    with pytest.raises(ErrorDeNegocio):
        N.validar_preparacion("Pendiente", "pendiente")


def test_factura_numero_y_qr():
    assert N.numero_factura(7) == "FE-00000007"
    qr = N.texto_qr("FE-00000007", "900-1", datetime(2026, 11, 1, tzinfo=UTC), 19, 119)
    assert qr == "FACTURA:FE-00000007|NIT:900-1|FECHA:2026-11-01|IVA:19.00|TOTAL:119.00"


def test_catalogo_bien_formado():
    slugs = [e.slug for e in ENTIDADES]
    assert len(slugs) == len(set(slugs)) == 14
    for e in ENTIDADES:
        assert e.campo(e.orden) or e.orden == e.pk
