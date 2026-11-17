"""CAPTCHA propio, sin servicios externos: imagen SVG + token firmado sin estado.

El token (JWT corto) contiene solo un HMAC de la respuesta, nunca la respuesta.
Cada token se acepta una única vez por proceso (anti-repetición)."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time

import jwt

_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # sin O/0/I/1 para evitar confusiones


class ServicioCaptcha:
    def __init__(self, secreto: str, ttl_s: int = 180, longitud: int = 5):
        self._clave = hmac.new(secreto.encode(), b"captcha", hashlib.sha256).hexdigest()
        self._ttl, self._n = ttl_s, longitud
        self._usados: dict[str, float] = {}
        self._lock = threading.Lock()
        self._azar = secrets.SystemRandom()

    def _firma(self, nonce: str, texto: str) -> str:
        return hmac.new(self._clave.encode(), f"{nonce}:{texto}".encode(), hashlib.sha256).hexdigest()

    def generar(self) -> tuple[str, str]:
        """Devuelve (svg, token)."""
        texto = "".join(secrets.choice(_ALFABETO) for _ in range(self._n))
        nonce = secrets.token_hex(8)
        token = jwt.encode({"n": nonce, "h": self._firma(nonce, texto), "typ": "captcha",
                            "exp": int(time.time()) + self._ttl}, self._clave, algorithm="HS256")
        return self._dibujar(texto), token

    def validar(self, token: str, respuesta: str) -> bool:
        try:
            datos = jwt.decode(token or "", self._clave, algorithms=["HS256"], options={"require": ["exp"]})
        except jwt.PyJWTError:
            return False
        if datos.get("typ") != "captcha":
            return False
        esperado = self._firma(datos["n"], (respuesta or "").strip().upper())
        if not hmac.compare_digest(esperado, datos.get("h", "")):
            return False
        with self._lock:
            ahora = time.time()
            self._usados = {k: v for k, v in self._usados.items() if v > ahora}
            if datos["n"] in self._usados:
                return False
            self._usados[datos["n"]] = ahora + self._ttl
        return True

    def _dibujar(self, texto: str) -> str:
        r, ancho, alto = self._azar, 168, 56
        partes = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}" width="{ancho}" height="{alto}" '
                  f'role="img" aria-label="Imagen de verificación con {self._n} caracteres">'
                  '<rect width="100%" height="100%" rx="8" fill="#f1f6f2"/>']
        for _ in range(6):
            partes.append(f'<line x1="{r.randint(0, ancho)}" y1="{r.randint(0, alto)}" x2="{r.randint(0, ancho)}" '
                          f'y2="{r.randint(0, alto)}" stroke="#7d9a86" stroke-width="1.2" opacity=".55"/>')
        paso = (ancho - 24) / len(texto)
        colores = ("#0d3b1c", "#7a1d1d", "#188a31", "#1f2a44")
        for i, c in enumerate(texto):
            x, y, ang = 16 + i * paso, r.randint(36, 44), r.randint(-22, 22)
            partes.append(f'<text x="{x:.0f}" y="{y}" font-size="{r.randint(28, 34)}" font-weight="700" '
                          f'font-family="DejaVu Sans Mono, Menlo, monospace" fill="{r.choice(colores)}" '
                          f'transform="rotate({ang} {x:.0f} {y})">{c}</text>')
        partes.append("</svg>")
        return "".join(partes)
