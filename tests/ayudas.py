"""Utilidades de pruebas: resolver el CAPTCHA con la clave interna del servicio y enviar el token CSRF."""
import time

import jwt


def captcha_resuelto(app, texto: str = "ABCDE") -> tuple[str, str]:
    cap = app.extensions["seguridad"].captcha
    nonce = f"n{time.time_ns()}"
    token = jwt.encode({"n": nonce, "h": cap._firma(nonce, texto), "typ": "captcha", "exp": int(time.time()) + 60},
                       cap._clave, algorithm="HS256")
    return token, texto


def iniciar_sesion(app, cliente, usuario: str, clave: str, ruta: str = "/api/auth/sesion"):
    token, texto = captcha_resuelto(app)
    return cliente.post(ruta, json={"usuario": usuario, "password": clave, "captcha_token": token, "captcha": texto})


def post(c, ruta, json=None, metodo="post"):
    return getattr(c, metodo)(ruta, json=json, headers={"X-CSRF-Token": c.csrf})
