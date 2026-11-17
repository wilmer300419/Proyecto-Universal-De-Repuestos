"""Pruebas de especificación de las reglas puras (negocio, validación y seguridad).

Nacen del análisis de mutación: cada bloque fija un límite o un contrato que antes ninguna prueba
verificaba (valores frontera, mensajes que ve el usuario, códigos HTTP, mapeos de columnas).
No requieren base de datos.
"""
from datetime import datetime, UTC
from decimal import Decimal

import jwt
import pytest

from app.models import negocio as N
from app.models.errores import ErrorAplicacion, ErrorDeNegocio, ErrorValidacion, NoEncontrado, SinPermiso
from app.models.meta import Campo, Entidad
from app.models.validacion import a_booleano, a_entero, entero_opcional, texto
from Seguridad.configuracion import ConfigSeguridad
from Seguridad.contrasenas import PoliticaContrasena
from Seguridad.limitador import LimitadorPeticiones, Regla
from Seguridad.modelos import PERSONAL, Grupo, Rol, Usuario
from Seguridad.tokens import ServicioJWT, TokenInvalido


# ------------------------------------------------------------------ errores -> códigos HTTP
def test_codigos_http_de_los_errores():
    assert ErrorAplicacion("x").codigo == 400 and ErrorValidacion("x").codigo == 400
    assert (SinPermiso("x").codigo, NoEncontrado("x").codigo, ErrorDeNegocio("x").codigo) == (403, 404, 409)
    e = ErrorValidacion("mensaje", {"campo": "malo"})
    assert (e.mensaje, e.campos, str(e)) == ("mensaje", {"campo": "malo"}, "mensaje")
    assert ErrorValidacion("m").campos == {}


# ------------------------------------------------------------------ validación
@pytest.mark.parametrize("valor", ["1", "true", "T", "si", "sí", "Yes", "on", 1, True])
def test_booleanos_verdaderos(valor):
    assert a_booleano(valor) is True


@pytest.mark.parametrize("valor", ["0", "false", "F", "no", "OFF", 0, False])
def test_booleanos_falsos(valor):
    assert a_booleano(valor) is False


def test_booleano_invalido_y_mensajes():
    for malo in (2, -1, "x", ""):
        with pytest.raises(ErrorValidacion, match="^estado debe ser verdadero o falso$"):
            a_booleano(malo, "estado")
    with pytest.raises(ErrorValidacion, match="^valor debe ser"):
        a_booleano("x")


def test_entero_limites_y_mensajes():
    assert a_entero("5", "n", 5, 5) == 5                                    # los límites son inclusivos
    with pytest.raises(ErrorValidacion, match="^n no puede ser menor que 5$"):
        a_entero(4, "n", 5)
    with pytest.raises(ErrorValidacion, match="^n no puede ser mayor que 5$"):
        a_entero(6, "n", maximo=5)
    with pytest.raises(ErrorValidacion, match="^n debe ser un número entero$"):
        a_entero("x", "n")
    with pytest.raises(ErrorValidacion, match="^n debe ser un número entero$"):
        a_entero(True, "n")
    with pytest.raises(ErrorValidacion, match="^valor debe ser"):
        a_entero("x")
    assert a_entero(-3) == -3


def test_entero_opcional():
    assert entero_opcional(None) is None and entero_opcional("") is None
    assert entero_opcional("2", "x") == 2
    with pytest.raises(ErrorValidacion, match="menor que 1"):
        entero_opcional("0", "x")
    assert entero_opcional("0", "x", minimo=0) == 0
    with pytest.raises(ErrorValidacion, match="^valor no puede"):
        entero_opcional("0")


def test_texto():
    assert texto("  hola  ", "Nombre", 4) == "hola"
    assert texto("", "Nombre", 4) is None and texto(None, "Nombre", 4) is None
    with pytest.raises(ErrorValidacion, match="^Nombre es obligatorio$"):
        texto(" ", "Nombre", 4, requerido=True)
    with pytest.raises(ErrorValidacion, match="^Nombre admite máximo 4 caracteres$"):
        texto("hola!", "Nombre", 4)
    assert texto(0, "N", 3) == "0"


# ------------------------------------------------------------------ negocio
def test_dinero_redondeo_y_mensaje():
    assert N.dinero("2.345") == Decimal("2.35") and N.dinero(0) == Decimal("0.00")
    with pytest.raises(ErrorValidacion, match="^Valor monetario inválido$"):
        N.dinero("x")


def test_estados_y_metodos_de_pago():
    assert (N.EstadoVenta.PAGADA, N.EstadoVenta.CANCELADA) == ("Pagada", "Cancelada")
    assert (N.EstadoEntrega.PENDIENTE, N.EstadoEntrega.CANCELADO) == ("pendiente", "cancelado")
    assert N.METODOS_PAGO == {"tarjeta_credito": "Tarjeta de crédito", "tarjeta_debito": "Tarjeta débito", "pse": "PSE",
                              "transferencia": "Transferencia bancaria", "nequi": "Nequi",
                              "efectivo": "Efectivo contra entrega"}
    assert [N.normalizar_metodo_pago(x) for x in ("credito", "debito", " PSE ", "tarjeta_debito")] == \
        ["tarjeta_credito", "tarjeta_debito", "pse", "tarjeta_debito"]
    with pytest.raises(ErrorValidacion, match="usa uno de: tarjeta_credito, tarjeta_debito, pse"):
        N.normalizar_metodo_pago(None)


def test_linea_con_descuento_igual_al_valor_es_valida():
    assert N.LineaPedido(1, "A", 2, Decimal("10"), Decimal("20")).subtotal == Decimal("0.00")
    with pytest.raises(ErrorValidacion, match="^El descuento de 'A' supera el valor de la línea$"):
        _ = N.LineaPedido(1, "A", 2, Decimal("10"), Decimal("20.01")).subtotal
    assert N.LineaPedido(1, "A", 1, Decimal("10")).descuento == Decimal("0")


def test_unir_items_reglas():
    assert N.unir_items([{"product_id": 1, "quantity": 1, "discount": 2}, {"product_id": 1, "quantity": 1, "discount": "3"}]) == \
        {1: (2, Decimal("5.00"))}
    with pytest.raises(ErrorValidacion, match="^El pedido debe tener al menos un producto$"):
        N.unir_items([])
    with pytest.raises(ErrorValidacion, match="^El pedido debe tener"):
        N.unir_items({"product_id": 1})
    with pytest.raises(ErrorValidacion, match="^Cada producto requiere"):
        N.unir_items([{"product_id": 1, "quantity": 1, "discount": -1}])
    with pytest.raises(ErrorValidacion, match="^Cada producto requiere"):
        N.unir_items(["x"])
    assert len(N.unir_items([{"product_id": i, "quantity": 1} for i in range(50)])) == 50
    with pytest.raises(ErrorValidacion, match="^Un pedido admite máximo 50 productos distintos$"):
        N.unir_items([{"product_id": i, "quantity": 1} for i in range(51)])


def test_totales_y_redondeo_del_iva():
    t = N.calcular_totales([N.LineaPedido(1, "A", 1, Decimal("0.05"))], 0.19)
    assert (t.subtotal, t.impuesto, t.total) == (Decimal("0.05"), Decimal("0.01"), Decimal("0.06"))
    assert N.calcular_totales([], 0.19).total == Decimal("0.00")


def test_stock():
    N.validar_stock(3, 3, "X")                                              # justo lo disponible
    with pytest.raises(ErrorDeNegocio, match=r"^Stock insuficiente para 'X' \(disponible: 2\)$"):
        N.validar_stock(2, 3, "X")
    with pytest.raises(ErrorDeNegocio, match=r"\(disponible: 0\)$"):
        N.validar_stock(None, 1, "X")


def test_pago_cancelacion_preparacion_y_factura():
    with pytest.raises(ErrorDeNegocio, match="^La venta #9 ya está en estado Entregada; no se puede pagar de nuevo$"):
        N.validar_pago("Entregada", 10, None, 9)
    with pytest.raises(ErrorValidacion, match=r"^El pago debe ser por el total de la venta: 10.00$"):
        N.validar_pago("Pendiente", 10, 9, 1)
    assert N.validar_pago("Pendiente", 10, "", 1) == Decimal("10.00")
    N.validar_cancelacion("Pendiente")
    for estado in ("Pagada", "Despachada", "Entregada", "Cancelada"):
        with pytest.raises(ErrorDeNegocio, match="^Solo se pueden cancelar ventas pendientes de pago$"):
            N.validar_cancelacion(estado)
    N.validar_preparacion("Pagada", "pendiente")
    with pytest.raises(ErrorDeNegocio, match="^La entrega ya está empacado$"):
        N.validar_preparacion("Pagada", "empacado")
    with pytest.raises(ErrorDeNegocio, match="^La venta debe estar pagada"):
        N.validar_preparacion("Despachada", "pendiente")
    for estado in ("Pagada", "Despachada", "Entregada"):
        N.validar_facturable(estado)
    for estado in ("Pendiente", "Cancelada"):
        with pytest.raises(ErrorDeNegocio, match="^Solo se factura una venta pagada$"):
            N.validar_facturable(estado)


def test_transicion_invalida_mensaje():
    with pytest.raises(ErrorDeNegocio, match="^Transición inválida: pendiente -> en_camino$"):
        N.transicion_entrega("pendiente", "en_camino")
    with pytest.raises(ErrorDeNegocio):
        N.transicion_entrega("entregado", "en_camino")


def test_qr_con_fecha():
    texto_qr = N.texto_qr("FE-1", "9", datetime(2026, 1, 2, tzinfo=UTC), "1.005", 2)
    assert texto_qr == "FACTURA:FE-1|NIT:9|FECHA:2026-01-02|IVA:1.01|TOTAL:2.00"


# ------------------------------------------------------------------ metadatos de catálogos
def test_metadatos_de_entidad():
    c = Campo("name", "Nombre")
    assert (c.tipo, c.requerido, c.max_len, c.por_defecto) == ("texto", True, None, None)
    e = Entidad("x", "x", "t", "t_id", (c, Campo("state", "Activo", "booleano", requerido=False)))
    assert e.columnas == ["t_id", "name", "state"]
    assert e.campo("name") is c and e.campo("otro") is None
    assert e.borrado_logico and (e.orden, e.lectura_admin, e.ids_protegidos) == ("name", False, ())
    assert not Entidad("y", "y", "t", "id", (c,)).borrado_logico


# ------------------------------------------------------------------ seguridad
def test_politica_frontera_y_mensajes():
    p = PoliticaContrasena()
    assert p.validar("Abcdefg#12") == []                                    # exactamente 10 caracteres
    assert p.validar("Abcdef#12") == ["Debe tener al menos 10 caracteres."]
    assert p.validar("ABCDEFG#12") == ["Debe incluir una letra minúscula."]
    assert p.validar("abcdefg#12") == ["Debe incluir una letra mayúscula."]
    assert p.validar("Abcdefgh#x") == ["Debe incluir un número."]
    assert p.validar("Abcdefgh12") == ["Debe incluir un símbolo (por ejemplo ! # $ %)."]
    assert p.validar("Pedro#2026x", "pedro") == ["No debe contener el nombre de usuario."]


def test_roles_grupos_y_mapeo_de_fila():
    assert [r.value for r in Rol] == ["cliente", "administrador", "empacador", "repartidor"]
    assert PERSONAL == (Rol.ADMINISTRADOR, Rol.EMPACADOR, Rol.REPARTIDOR)
    fila = {"user_id": 3, "username": "ana", "email": "a@b.co", "role": "empacador", "person_id": 7, "status": False,
            "password_hash": "h", "bloqueado_hasta": None}
    u = Usuario.desde_fila(fila)
    assert (u.id, u.nombre_usuario, u.email, u.rol, u.id_persona, u.activo, u.password_hash) == \
        (3, "ana", "a@b.co", Rol.EMPACADOR, 7, False, "h")
    assert u.es_personal and not u.es_admin and u.grupo is Grupo.USER
    admin = Usuario(1, "x", "x@y.co", Rol.ADMINISTRADOR)
    assert admin.es_admin and admin.es_personal and admin.grupo is Grupo.ADMIN and admin.activo
    cliente = Usuario(2, "c", "c@y.co", Rol.CLIENTE)
    assert not cliente.es_personal and not cliente.es_admin and cliente.password_hash == ""
    assert Usuario.desde_fila({k: v for k, v in fila.items() if k not in ("password_hash", "bloqueado_hasta")}).password_hash == ""


def test_jwt_exige_claims_y_valor_por_defecto_de_grupo():
    cfg = ConfigSeguridad(jwt_secreto="s" * 48)
    token, claims = ServicioJWT(cfg).emitir(Usuario(5, "eva", "e@e.co", Rol.CLIENTE))
    assert (claims.sub, claims.usr, claims.rol, claims.grp) == (5, "eva", "cliente", "USER") and len(claims.jti) == 32
    carga = jwt.decode(token, options={"verify_signature": False})
    sin_jti = jwt.encode({k: v for k, v in carga.items() if k != "jti"}, cfg.jwt_secreto, algorithm="HS256")
    with pytest.raises(TokenInvalido, match="^Token inválido o expirado$"):
        ServicioJWT(cfg).verificar(sin_jti)
    sin_grp = jwt.encode({k: v for k, v in carga.items() if k != "grp"}, cfg.jwt_secreto, algorithm="HS256")
    assert ServicioJWT(cfg).verificar(sin_grp).grp == "USER"


def test_limitador_frontera_espera_y_purga():
    t = [100.0]
    lim = LimitadorPeticiones(reloj=lambda: t[0], max_claves=2)
    regla = Regla(2, 10)
    assert lim.permitir("a", regla) == (True, 0)
    t[0] = 104.0
    assert lim.permitir("a", regla) == (True, 0)
    t[0] = 105.0
    assert lim.permitir("a", regla) == (False, 6)                           # 100 + 10 - 105 + 1
    t[0] = 110.0                                                            # el primer intento sale justo al cumplir la ventana
    assert lim.permitir("a", regla) == (True, 0)
    t[0] = 200.0
    lim.permitir("b", regla)
    lim.permitir("c", regla)                                                # 3 claves > máximo 2: se purgan las vencidas
    assert set(lim._eventos) == {"b", "c"}
    lim.reiniciar()
    assert lim._eventos == {}
